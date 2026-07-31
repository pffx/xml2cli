"""LT family: multi-root BBF xPON/QoS CLI and onus/onu/fromroot paths."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Sequence

from xml2cli.families.base import Family
from xml2cli.xml_parser import NETCONF_NS, local_name
from xml2cli.yang.schema import BoardSchema, SchemaNode
from xml2cli.yang.schema_store import load_schema

ONU_NS = "urn:bbf:params:xml:ns:yang:bbf-fiber-onu-emulated-mount"

STRUCTURE_KINDS = {"container", "list", "presence-container", "choice", "case"}

_LT_ROOT_NS: dict[str, str] = {
    "classifiers": "urn:bbf:yang:bbf-qos-classifiers-mounted",
    "policies": "urn:bbf:yang:bbf-qos-policies-mounted",
    "qos-policy-profiles": "urn:bbf:yang:bbf-qos-policies-mounted",
    "xpongemtcont": "urn:bbf:yang:bbf-xpongemtcont-mounted",
    "onus": ONU_NS,
}

_PREFIX_TO_NS: dict[str, str] = {
    "bbf-qos-cls-mounted": "urn:bbf:yang:bbf-qos-classifiers-mounted",
    "bbf-qos-pol-mounted": "urn:bbf:yang:bbf-qos-policies-mounted",
    "bbf-qos-plc-mounted": "urn:bbf:yang:bbf-qos-policing-mounted",
    "bbf-xpongemtcont-frommounted": "urn:bbf:yang:bbf-xpongemtcont-mounted",
    "if-frommounted": "urn:ietf:params:xml:ns:yang:ietf-interfaces-mounted",
}

_SKIP_XMLNS: set[tuple[str, str]] = {("policy", "classifiers")}


class LtFamily(Family):
    def __init__(self, board_id: str) -> None:
        self.board_id = board_id
        self.schema = load_schema(board_id)

    def cli_prefix(self) -> list[str]:
        return []

    def parse_cli_line(self, tokens: Sequence[str], schema: BoardSchema) -> ET.Element:
        token_list = list(tokens)
        if not token_list:
            raise ValueError("Empty CLI line")

        if token_list[0] == "onus":
            return self._parse_onus_line(token_list, schema)

        root_name = token_list[0]
        if root_name not in schema.roots:
            raise ValueError(f"Unknown LT config root '{root_name}'")

        root_elem = ET.Element(root_name)
        root_ns = _namespace_for_root(root_name)
        if root_ns:
            root_elem.set("xmlns", root_ns)

        self._parse_tokens(
            root_elem,
            token_list[1:],
            0,
            schema.roots[root_name],
            parent_tag=root_name,
            current_ns=root_ns,
        )
        return root_elem

    def xml_to_cli_lines(
        self,
        elem: ET.Element,
        schema: BoardSchema,
        path: list[str],
    ) -> list[str]:
        root_name = local_name(elem.tag)
        if root_name not in schema.roots:
            raise ValueError(f"Unknown LT config root '{root_name}'")

        lines: list[str] = []
        root_node = schema.roots[root_name]
        self._emit_element(elem, root_node, [*path, root_name], lines)
        return lines

    def wrap_edit_config(self, config_elems: Sequence[ET.Element]) -> str:
        rpc = ET.Element("rpc", {"xmlns": NETCONF_NS, "message-id": "1"})
        edit_config = ET.SubElement(rpc, "edit-config")
        target = ET.SubElement(edit_config, "target")
        ET.SubElement(target, "running")
        config = ET.SubElement(edit_config, "config")
        for elem in config_elems:
            config.append(elem)
        return _pretty_xml(rpc)

    def wrap_special_rpc(self, rpc_kind: str) -> str:
        raise ValueError(f"Unsupported special RPC: {rpc_kind}")

    def _parse_onus_line(self, tokens: list[str], schema: BoardSchema) -> ET.Element:
        if len(tokens) < 3 or tokens[1] != "onu":
            raise ValueError("Expected 'onus onu <name>'")

        onus = ET.Element("onus")
        onus.set("xmlns", ONU_NS)
        onu = ET.SubElement(onus, "onu")
        name_elem = ET.SubElement(onu, "name")
        name_elem.text = tokens[2]

        index = 3
        if index < len(tokens) and tokens[index] == "fromroot":
            container = ET.SubElement(onu, "fromroot")
            index += 1
            onu_schema = schema.roots["onus"].children["onu"]
            fromroot_schema = onu_schema.children.get("fromroot") or _passthrough_schema("fromroot")
            self._parse_tokens(
                container,
                tokens[index:],
                0,
                fromroot_schema,
                parent_tag="fromroot",
                current_ns=None,
            )
            return onus

        if index < len(tokens):
            raise ValueError("ONU CLI paths must use 'fromroot' after ONU name")
        return onus

    def _parse_tokens(
        self,
        parent: ET.Element,
        tokens: list[str],
        index: int,
        schema_node: SchemaNode,
        parent_tag: str,
        current_ns: str | None,
    ) -> int:
        while index < len(tokens):
            token = tokens[index]

            if (
                index + 2 < len(tokens)
                and tokens[index + 1] == token
                and schema_node.children.get(token) is not None
                and schema_node.children[token].kind == "leaf"
            ):
                leaf = ET.SubElement(parent, token)
                leaf.text = tokens[index + 2]
                index += 3
                continue

            child_schema = _resolve_child(schema_node, token) or _passthrough_schema(token)

            if child_schema.kind in STRUCTURE_KINDS:
                child_elem = ET.SubElement(parent, child_schema.name)
                current_ns = _apply_xmlns(
                    child_elem,
                    child_schema,
                    parent_tag,
                    local_name(parent.tag),
                    current_ns,
                )
                index += 1
                if child_schema.kind == "list":
                    index = self._consume_list_keys(
                        child_elem,
                        tokens,
                        index,
                        child_schema,
                        parent_tag=child_schema.name,
                        current_ns=current_ns,
                    )
                index = self._parse_tokens(
                    child_elem,
                    tokens,
                    index,
                    child_schema,
                    parent_tag=child_schema.name,
                    current_ns=current_ns,
                )
            else:
                if index + 1 >= len(tokens):
                    raise ValueError(f"Expected value after leaf '{token}'")
                leaf = ET.SubElement(parent, child_schema.name)
                _apply_xmlns(leaf, child_schema, parent_tag, local_name(parent.tag), current_ns)
                leaf.text = tokens[index + 1]
                index += 2
        return index

    def _consume_list_keys(
        self,
        list_elem: ET.Element,
        tokens: list[str],
        index: int,
        schema_node: SchemaNode,
        parent_tag: str,
        current_ns: str | None,
    ) -> int:
        for key_name in schema_node.keys:
            if index >= len(tokens):
                raise ValueError(
                    f"Expected list key '{key_name}' for '{schema_node.name}'"
                )
            key_schema = schema_node.children.get(key_name) or _passthrough_schema(key_name)
            key_elem = ET.SubElement(list_elem, key_name)
            key_elem.text = tokens[index]
            index += 1
            if key_schema.kind in STRUCTURE_KINDS:
                index = self._parse_tokens(
                    key_elem,
                    tokens,
                    index,
                    key_schema,
                    parent_tag=key_name,
                    current_ns=current_ns,
                )
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
            child_schema = schema_node.children.get(name) or _passthrough_schema(name)

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


def _resolve_child(schema_node: SchemaNode, token: str) -> SchemaNode | None:
    if token in schema_node.children:
        return schema_node.children[token]
    for child in schema_node.children.values():
        if child.kind == "choice":
            for case in child.children.values():
                if token in case.children:
                    return case.children[token]
    return None


def _passthrough_schema(name: str) -> SchemaNode:
    return SchemaNode(name=name, kind="container", children={})


def _namespace_for_root(root_name: str) -> str | None:
    return _LT_ROOT_NS.get(root_name)


def _namespace_for_prefix(prefix: str) -> str | None:
    if prefix in _PREFIX_TO_NS:
        return _PREFIX_TO_NS[prefix]
    if prefix.startswith("bbf-"):
        return f"urn:bbf:yang:{prefix.replace('-frommounted', '').replace('-mounted', '')}-mounted"
    return None


def _apply_xmlns(
    elem: ET.Element,
    schema_node: SchemaNode,
    parent_tag: str,
    grandparent_tag: str,
    current_ns: str | None,
) -> str | None:
    if (grandparent_tag, schema_node.name) in _SKIP_XMLNS:
        return current_ns
    if schema_node.prefix is None:
        return current_ns
    new_ns = _namespace_for_prefix(schema_node.prefix)
    if new_ns is not None and new_ns != current_ns:
        elem.set("xmlns", new_ns)
        return new_ns
    return current_ns


def _pretty_xml(elem: ET.Element) -> str:
    ET.indent(elem, space="  ")
    xml_str = ET.tostring(elem, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str + "\n"


def _find_child_by_local_name(parent: ET.Element, name: str) -> ET.Element | None:
    for child in parent:
        if local_name(child.tag) == name:
            return child
    return None
