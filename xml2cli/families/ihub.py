"""IHUB family: SR OS configure-style CLI and candidate RPC target."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Sequence

from xml2cli.families.base import Family
from xml2cli.profiles.sr_os import (
    SR_CONF_NS,
    build_commit_rpc,
    build_discard_rpc,
    build_oamsave_rpc,
)
from xml2cli.xml_parser import NETCONF_NS, local_name
from xml2cli.yang.schema import BoardSchema, SchemaNode

SPECIAL_RPCS = {"commit", "discard", "oam-save"}
STRUCTURE_KINDS = {"container", "list", "presence-container", "choice", "case"}


class IhubFamily(Family):
    def cli_prefix(self) -> list[str]:
        return ["configure"]

    def parse_cli_line(self, tokens: Sequence[str], schema: BoardSchema) -> ET.Element:
        token_list = list(tokens)
        if not token_list:
            raise ValueError("Empty CLI line")

        if token_list[0] in SPECIAL_RPCS:
            raise ValueError(
                f"Use wrap_special_rpc for '{token_list[0]}'; not supported via config tree"
            )

        if token_list[0] == "configure":
            token_list = token_list[1:]

        configure = ET.Element("configure")
        configure.set("xmlns", SR_CONF_NS)

        root_name = schema.config_roots[0]
        root_node = schema.roots[root_name]
        self._parse_tokens(configure, token_list, 0, root_node)
        return configure

    def xml_to_cli_lines(
        self,
        elem: ET.Element,
        schema: BoardSchema,
        path: list[str],
    ) -> list[str]:
        lines: list[str] = []
        root_name = schema.config_roots[0]
        root_node = schema.roots[root_name]
        self._emit_element(elem, root_node, [*self.cli_prefix(), *path], lines)
        return lines

    def wrap_edit_config(self, config_elems: Sequence[ET.Element]) -> str:
        return self.wrap_rpc(config_elems, rpc_kind="edit-config")

    def wrap_rpc(
        self,
        config_elems: Sequence[ET.Element],
        rpc_kind: str = "edit-config",
    ) -> str:
        if rpc_kind != "edit-config":
            raise ValueError(f"Unsupported RPC kind: {rpc_kind}")

        rpc = ET.Element("rpc", {"xmlns": NETCONF_NS, "message-id": "1"})
        edit_config = ET.SubElement(rpc, "edit-config")
        target = ET.SubElement(edit_config, "target")
        ET.SubElement(target, "candidate")
        config = ET.SubElement(edit_config, "config")
        for elem in config_elems:
            config.append(elem)
        return _pretty_xml(rpc)

    def wrap_special_rpc(self, rpc_kind: str) -> str:
        if rpc_kind == "commit":
            return build_commit_rpc()
        if rpc_kind == "discard":
            return build_discard_rpc()
        if rpc_kind == "oam-save":
            return build_oamsave_rpc()
        raise ValueError(f"Unsupported special RPC: {rpc_kind}")

    def special_rpc_to_cli(self, rpc_kind: str, payload: ET.Element | None = None) -> list[str] | None:
        if rpc_kind == "commit":
            return ["commit"]
        if rpc_kind == "discard-changes":
            return ["discard"]
        if rpc_kind == "action" and payload is not None:
            for elem in payload.iter():
                if local_name(elem.tag) == "oamsave" and (elem.text or "").strip().lower() == "true":
                    return ["oam-save"]
        return None

    def _parse_tokens(
        self,
        parent: ET.Element,
        tokens: list[str],
        index: int,
        schema_node: SchemaNode,
    ) -> int:
        while index < len(tokens):
            token = tokens[index]
            child_schema = schema_node.children.get(token)
            if child_schema is None:
                raise ValueError(
                    f"Unknown token '{token}' under '{schema_node.name}'"
                )

            if child_schema.kind in STRUCTURE_KINDS:
                child_elem = ET.SubElement(parent, child_schema.name)
                index += 1
                if child_schema.kind == "list":
                    index = self._consume_list_keys(child_elem, tokens, index, child_schema)
                index = self._parse_tokens(child_elem, tokens, index, child_schema)
            else:
                if index + 1 >= len(tokens):
                    raise ValueError(f"Expected value after leaf '{token}'")
                leaf = ET.SubElement(parent, child_schema.name)
                leaf.text = tokens[index + 1]
                index += 2
        return index

    def _consume_list_keys(
        self,
        list_elem: ET.Element,
        tokens: list[str],
        index: int,
        schema_node: SchemaNode,
    ) -> int:
        for key_name in schema_node.keys:
            if index >= len(tokens):
                raise ValueError(f"Expected list key '{key_name}' for '{schema_node.name}'")
            key_schema = schema_node.children.get(key_name)
            key_elem = ET.SubElement(list_elem, key_name)
            key_elem.text = tokens[index]
            index += 1
            if key_schema is not None and key_schema.kind in STRUCTURE_KINDS:
                index = self._parse_tokens(key_elem, tokens, index, key_schema)
        return index

    def _emit_element(
        self,
        elem: ET.Element,
        schema_node: SchemaNode,
        prefix: list[str],
        lines: list[str],
        skip_names: set[str] | None = None,
    ) -> None:
        skip = skip_names or set()
        for child in list(elem):
            name = local_name(child.tag)
            if name in skip:
                continue
            child_schema = schema_node.children.get(name)
            if child_schema is None:
                continue

            if child_schema.kind == "list":
                line_prefix = [*prefix, name]
                for key_name in child_schema.keys:
                    key_elem = _find_child_by_local_name(child, key_name)
                    if key_elem is not None and (key_elem.text or "").strip():
                        line_prefix.append((key_elem.text or "").strip())
                self._emit_element(
                    child,
                    child_schema,
                    line_prefix,
                    lines,
                    skip_names=set(child_schema.keys),
                )
            elif child_schema.kind in STRUCTURE_KINDS:
                self._emit_element(child, child_schema, [*prefix, name], lines)
            elif (child.text or "").strip():
                lines.append(" ".join([*prefix, name, (child.text or "").strip()]))


def _pretty_xml(elem: ET.Element) -> str:
    ET.indent(elem, space="  ")
    xml_str = ET.tostring(elem, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str + "\n"


def _find_child_by_local_name(parent: ET.Element, name: str) -> ET.Element | None:
    for child in parent:
        if local_name(child.tag) == name:
            return child
    return None
