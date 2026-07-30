"""XML parsing helpers for NETCONF RPC documents."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

NETCONF_NS = "urn:ietf:params:xml:ns:netconf:base:1.0"


def local_name(tag: str) -> str:
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def get_namespace(tag: str) -> Optional[str]:
    if tag.startswith("{"):
        return tag[1:].split("}", 1)[0]
    return None


def get_operation(elem: ET.Element) -> Optional[str]:
    for key, value in elem.attrib.items():
        if local_name(key) == "operation":
            return value
    return None


@dataclass
class RpcDocument:
    rpc_type: str
    root: ET.Element
    payload: Optional[ET.Element] = None


def parse_rpc(xml_content: str) -> RpcDocument:
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        raise ValueError(f"XML parse error: {exc}") from exc

    if local_name(root.tag) == "rpc-reply":
        raise ValueError("rpc-reply documents are not supported in v1")

    if local_name(root.tag) != "rpc":
        raise ValueError("Expected root element <rpc>")

    for child in root:
        name = local_name(child.tag)
        if name == "edit-config":
            return RpcDocument("edit-config", root, child)
        if name == "get-config":
            return RpcDocument("get-config", root, child)
        if name == "get":
            return RpcDocument("get", root, child)
        if name == "commit":
            return RpcDocument("commit", root, child)
        if name == "discard-changes":
            return RpcDocument("discard-changes", root, child)
        if name == "action":
            return RpcDocument("action", root, child)

    raise ValueError("Unsupported or missing RPC operation")


def find_config_root(config_parent: ET.Element, root_tags: set[str]) -> ET.Element:
    for elem in config_parent.iter():
        if local_name(elem.tag) in root_tags:
            return elem
    raise ValueError(f"Config root not found; expected one of: {sorted(root_tags)}")


def element_text(elem: ET.Element) -> str:
    return (elem.text or "").strip()


def child_elements(elem: ET.Element) -> list[ET.Element]:
    return [child for child in elem if isinstance(child, ET.Element)]
