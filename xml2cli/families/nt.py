"""NT family: IETF-style CLI with config-root paths and running RPC target."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Sequence

from xml2cli.families.base import Family
from xml2cli.profiles.ietf_nt import IETF_SYSTEM_NS, NOKIA_SYSTEM_AUG_NS
from xml2cli.xml_parser import NETCONF_NS, local_name
from xml2cli.yang.schema import BoardSchema, SchemaNode
from xml2cli.yang.schema_store import load_schema

STRUCTURE_KINDS = {"container", "list", "presence-container", "choice", "case"}

_PREFIX_TO_NS: dict[str, str] = {
    "nokia-ietf-system-aug": NOKIA_SYSTEM_AUG_NS,
}

_ROOT_MODULE_OVERRIDES: dict[str, str] = {
    "confdConfig": "confd_dyncfg",
}


class NtFamily(Family):
    def __init__(self, board_id: str) -> None:
        self.board_id = board_id
        self.schema = load_schema(board_id)

    def cli_prefix(self) -> list[str]:
        return []

    def parse_cli_line(self, tokens: Sequence[str], schema: BoardSchema) -> ET.Element:
        token_list = list(tokens)
        if not token_list:
            raise ValueError("Empty CLI line")

        root_name = token_list[0]
        if root_name not in schema.roots:
            raise ValueError(f"Unknown config root '{root_name}'")

        root_node = schema.roots[root_name]
        root_elem = ET.Element(root_name)
        root_ns = _namespace_for_root(root_name, schema)
        if root_ns is not None:
            root_elem.set("xmlns", root_ns)

        self._parse_tokens(
            root_elem,
            token_list[1:],
            0,
            root_node,
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
            raise ValueError(f"Unknown config root element '{root_name}'")

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

    def _parse_tokens(
        self,
        parent: ET.Element,
        tokens: list[str],
        index: int,
        schema_node: SchemaNode,
        current_ns: str | None,
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
                current_ns = _apply_xmlns(child_elem, child_schema, current_ns)
                index += 1
                if child_schema.kind == "list":
                    index = self._consume_list_keys(
                        child_elem, tokens, index, child_schema, current_ns
                    )
                index = self._parse_tokens(
                    child_elem, tokens, index, child_schema, current_ns
                )
            else:
                if index + 1 >= len(tokens):
                    raise ValueError(f"Expected value after leaf '{token}'")
                leaf = ET.SubElement(parent, child_schema.name)
                _apply_xmlns(leaf, child_schema, current_ns)
                leaf.text = tokens[index + 1]
                index += 2
        return index

    def _consume_list_keys(
        self,
        list_elem: ET.Element,
        tokens: list[str],
        index: int,
        schema_node: SchemaNode,
        current_ns: str | None,
    ) -> int:
        for key_name in schema_node.keys:
            if index >= len(tokens):
                raise ValueError(
                    f"Expected list key '{key_name}' for '{schema_node.name}'"
                )
            key_schema = schema_node.children.get(key_name)
            key_elem = ET.SubElement(list_elem, key_name)
            key_elem.text = tokens[index]
            index += 1
            if key_schema is not None and key_schema.kind in STRUCTURE_KINDS:
                index = self._parse_tokens(
                    key_elem, tokens, index, key_schema, current_ns
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


def _namespace_for_prefix(prefix: str) -> str | None:
    if prefix in _PREFIX_TO_NS:
        return _PREFIX_TO_NS[prefix]
    if prefix.startswith(("ietf-", "iana-")):
        return f"urn:ietf:params:xml:ns:yang:{prefix}"
    if prefix.startswith("nokia-"):
        return f"http://www.nokia.com/Fixed-Networks/BBA/yang/{prefix}"
    return None


def _module_for_root(root_name: str, schema: BoardSchema) -> str | None:
    if root_name in _ROOT_MODULE_OVERRIDES:
        module = _ROOT_MODULE_OVERRIDES[root_name]
        if module in schema.modules:
            return module

    if root_name in schema.modules:
        return root_name

    ietf_module = f"ietf-{root_name}"
    if ietf_module in schema.modules:
        return ietf_module

    return None


def _namespace_for_root(root_name: str, schema: BoardSchema) -> str | None:
    if root_name == "system":
        return IETF_SYSTEM_NS
    module = _module_for_root(root_name, schema)
    if module is None:
        return None
    return _namespace_for_prefix(module)


def _apply_xmlns(
    elem: ET.Element,
    schema_node: SchemaNode,
    current_ns: str | None,
) -> str | None:
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
