"""XML parsing helpers for NETCONF RPC documents."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

NETCONF_NS = "urn:ietf:params:xml:ns:netconf:base:1.0"

_LITERAL_COLON = "__COLON__"
_NUMERIC_KEY_PREFIX = "__key__"

_TAG_WITH_COLON_RE = re.compile(
    r"(</?)([A-Za-z_][\w.-]*):([A-Za-z_][\w.-]*)((?:\s[^>]*)?>)"
)
_NUMERIC_TAG_RE = re.compile(r"(</?)(\d+)((?:\s[^>]*)?>)")
_XMLNS_PREFIX_RE = re.compile(r"\bxmlns:([A-Za-z_][\w.-]*)\s*=")


def local_name(tag: str) -> str:
    if tag.startswith("{"):
        name = tag.split("}", 1)[1]
    else:
        name = tag
    return _decode_sanitized_tag_name(name)


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


def sanitize_netconf_xml(xml_content: str) -> str:
    """Normalize device XML that uses YANG list keys as invalid XML tag names."""
    declared_prefixes = set(_XMLNS_PREFIX_RE.findall(xml_content))
    sanitized = _TAG_WITH_COLON_RE.sub(
        lambda match: _replace_unbound_colon_tag(match, declared_prefixes),
        xml_content,
    )
    return _NUMERIC_TAG_RE.sub(_replace_numeric_tag, sanitized)


def parse_rpc(xml_content: str) -> RpcDocument:
    sanitized = sanitize_netconf_xml(xml_content)
    try:
        root = ET.fromstring(sanitized)
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


def _decode_sanitized_tag_name(name: str) -> str:
    if name.startswith(_NUMERIC_KEY_PREFIX):
        return name[len(_NUMERIC_KEY_PREFIX) :]
    return name.replace(_LITERAL_COLON, ":")


def _replace_unbound_colon_tag(match: re.Match[str], declared_prefixes: set[str]) -> str:
    closing, prefix, local, suffix = match.groups()
    if prefix in declared_prefixes:
        return match.group(0)
    safe_name = f"{prefix}{_LITERAL_COLON}{local}"
    return f"{closing}{safe_name}{suffix}"


def _replace_numeric_tag(match: re.Match[str]) -> str:
    closing, digits, suffix = match.groups()
    return f"{closing}{_NUMERIC_KEY_PREFIX}{digits}{suffix}"
