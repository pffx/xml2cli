"""Conversion engine shared by CLI and web API."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from copy import deepcopy
from typing import Optional

from xml2cli.profiles.base import Profile, resolve_profile_name
from xml2cli.xml_parser import (
    RpcDocument,
    child_elements,
    element_text,
    find_config_root,
    get_operation,
    local_name,
    parse_rpc,
)

KEY_PRIORITY: dict[str, list[str]] = {
    "vpls": ["service-name", "service-id"],
    "ies": ["service-name"],
    "sap": ["sap-id"],
    "port": ["port-id"],
    "interface": ["interface-name", "name"],
    "router": ["router-name"],
    "route": ["ip-prefix"],
    "lag": ["lag-index"],
    "card": ["slot-number"],
    "mda": ["mda-slot"],
    "sub-group": ["sub-group-id"],
    "onu": ["name"],
    "interface-entry": ["name"],
    "server": ["name"],
    "classifier-entry": ["name"],
    "control-plane-protocol": ["name"],
}


def detect_profile_from_xml(xml_content: str) -> Optional[str]:
    """Guess profile folder name from XML namespaces or root elements."""
    content = xml_content
    lowered = content.lower()

    if "<commit" in lowered or "<discard-changes" in lowered:
        return "831-ihub"
    if "urn:nokia.com:sros:ns:yang:sr:action" in content:
        return "831-ihub"
    if "urn:nokia.com:sros:ns:yang:sr:conf" in content or "urn:nokia.com:sros:ns:yang:sr:state" in content:
        return "831-ihub"
    if "bbf-fiber-onu-emulated-mount" in content or "<onus" in lowered:
        return "833-LT-1"
    if (
        "urn:ietf:params:xml:ns:yang:ietf-system" in content
        or "nokia-ietf-system-aug" in content
    ):
        return "832-nt"
    return None


def detect_profile_from_cli(cli_content: str) -> Optional[str]:
    """Guess profile folder name from CLI command prefix."""
    lines = [line.strip() for line in cli_content.splitlines() if line.strip()]
    if not lines:
        return None

    profiles = {_detect_profile_from_cli_line(line) for line in lines}
    profiles.discard(None)
    if len(profiles) == 1:
        return profiles.pop()
    if len(profiles) > 1:
        return None
    return _detect_profile_from_cli_line(lines[0])


def _detect_profile_from_cli_line(line: str) -> Optional[str]:
    token = line.split()[0] if line.split() else ""
    if token == "onus":
        return "833-LT-1"
    if token == "system":
        return "832-nt"
    if token in {"configure", "commit", "discard", "oam-save", "admin", "show"}:
        return "831-ihub"
    return None


def convert_xml_to_cli_auto(xml_content: str) -> tuple[list[str], list[str], Optional[str]]:
    profile_name = detect_profile_from_xml(xml_content)
    if profile_name is None:
        return [], ["无法根据 XML 内容自动识别设备类型"], None
    cli_lines, errors = convert_xml_to_cli(xml_content, profile_name)
    return cli_lines, errors, profile_name


def convert_cli_to_xml_auto(cli_content: str) -> tuple[str, list[str], Optional[str]]:
    xml_output, errors, profiles_used = _convert_cli_lines_to_xml(cli_content)
    profile = profiles_used.pop() if len(profiles_used) == 1 else None
    return xml_output, errors, profile


def convert_xml_to_cli(xml_content: str, profile_name: str) -> tuple[list[str], list[str]]:
    profile = resolve_profile_name(profile_name)
    warnings: list[str] = []

    try:
        rpc = parse_rpc(xml_content)
    except ValueError as exc:
        return [], [str(exc)]

    special = getattr(profile, "special_rpc_to_cli", lambda _t, _p: None)(rpc.rpc_type, rpc.payload)
    if special is not None:
        return special, warnings

    if rpc.rpc_type not in {"edit-config", "get-config", "get"}:
        warnings.append(f"Unknown RPC type '{rpc.rpc_type}'; attempting edit-config handling")

    try:
        if rpc.rpc_type == "get-config":
            return _convert_get_config(rpc, profile), warnings
        if rpc.rpc_type == "get":
            return _convert_get(rpc, profile), warnings
        return _convert_edit_config(rpc, profile), warnings
    except ValueError as exc:
        message = str(exc)
        detected = detect_profile_from_xml(xml_content)
        if detected and detected != profile_name:
            message += f"。检测到该 XML 可能属于 Profile「{detected}」"
        return [], [message]


def convert_cli_to_xml(cli_content: str, profile_name: str) -> tuple[str, list[str]]:
    lines = [line.strip() for line in cli_content.splitlines() if line.strip()]
    if not lines:
        return "", ["No CLI content provided"]

    xml_output, errors, _ = _convert_cli_lines_to_xml(cli_content, default_profile=profile_name)
    return xml_output, errors


def _convert_cli_lines_to_xml(
    cli_content: str,
    default_profile: Optional[str] = None,
) -> tuple[str, list[str], set[str]]:
    lines = [line.strip() for line in cli_content.splitlines() if line.strip()]
    if not lines:
        return "", ["No CLI content provided"], set()

    xml_parts: list[str] = []
    errors: list[str] = []
    profiles_used: set[str] = set()

    for batch in _batch_cli_lines(lines, default_profile=default_profile):
        batch_type = batch[0]
        if batch_type == "error":
            _, index, message = batch
            errors.append(f"第 {index} 行：{message}")
            continue

        profile_name = batch[1]
        indexed_lines = batch[2]
        profiles_used.add(profile_name)
        profile = resolve_profile_name(profile_name)

        if batch_type == "special":
            for index, line in indexed_lines:
                try:
                    xml_parts.append(_convert_special_cli_line(line, profile_name))
                except ValueError as exc:
                    errors.append(f"第 {index} 行：{exc}")
            continue

        config_trees: list[ET.Element] = []
        for index, line in indexed_lines:
            try:
                config_trees.append(profile.parse_cli_line(line))
            except ValueError as exc:
                errors.append(f"第 {index} 行：{exc}")

        if not config_trees:
            continue

        merged_config = _merge_config_trees(config_trees, profile)
        xml_parts.append(profile.wrap_config_in_rpc(merged_config).strip())

    if not xml_parts:
        return "", errors, profiles_used

    return _join_rpc_documents(xml_parts), errors, profiles_used


def _batch_cli_lines(
    lines: list[str],
    default_profile: Optional[str] = None,
) -> list[tuple]:
    batches: list[tuple] = []
    current_batch: Optional[tuple] = None

    for index, line in enumerate(lines, start=1):
        profile_name = _detect_profile_from_cli_line(line) or default_profile
        if profile_name is None:
            if current_batch is not None:
                batches.append(current_batch)
                current_batch = None
            batches.append(("error", index, "无法自动识别设备类型"))
            continue

        if _is_special_cli_line(line):
            if current_batch is not None:
                batches.append(current_batch)
                current_batch = None
            batches.append(("special", profile_name, [(index, line)]))
            continue

        if (
            current_batch is not None
            and current_batch[0] == "config"
            and current_batch[1] == profile_name
        ):
            current_batch[2].append((index, line))
        else:
            if current_batch is not None:
                batches.append(current_batch)
            current_batch = ("config", profile_name, [(index, line)])

    if current_batch is not None:
        batches.append(current_batch)

    return batches


def _is_special_cli_line(line: str) -> bool:
    token = line.split()[0] if line.split() else ""
    return token in {"commit", "discard", "oam-save"}


def _convert_special_cli_line(line: str, profile_name: str) -> str:
    special_xml = _convert_special_cli(line, profile_name)
    if special_xml is not None:
        return special_xml.strip()
    raise ValueError(f"Unsupported special CLI command: {line.split()[0]}")


def _merge_config_trees(trees: list[ET.Element], profile: Profile) -> ET.Element:
    merged = deepcopy(trees[0])
    for tree in trees[1:]:
        _merge_elements(merged, tree, profile)
    return merged


def _merge_elements(target: ET.Element, source: ET.Element, profile: Profile) -> None:
    if local_name(target.tag) != local_name(source.tag):
        raise ValueError(
            f"Cannot merge <{local_name(source.tag)}> into <{local_name(target.tag)}>"
        )

    for key, value in source.attrib.items():
        target.set(key, value)

    if not child_elements(source) and element_text(source) and not child_elements(target):
        target.text = source.text
        return

    for src_child in child_elements(source):
        identity = _element_identity(src_child, profile)
        matched = False
        for tgt_child in child_elements(target):
            if _element_identity(tgt_child, profile) == identity:
                _merge_elements(tgt_child, src_child, profile)
                matched = True
                break
        if not matched:
            target.append(deepcopy(src_child))


def _element_identity(elem: ET.Element, profile: Profile) -> tuple:
    tag = local_name(elem.tag)
    key_parts = []
    for child in child_elements(elem):
        child_name = local_name(child.tag)
        if child_name in profile.list_keys and not child_elements(child):
            key_parts.append((child_name, element_text(child)))
    if key_parts:
        return (tag, tuple(key_parts))
    return (tag,)


def _join_rpc_documents(documents: list[str]) -> str:
    if not documents:
        return ""
    if len(documents) == 1:
        return documents[0] + "\n"

    parts = [documents[0]]
    for document in documents[1:]:
        if document.startswith("<?xml"):
            document = document.split("?>", 1)[1].lstrip("\n")
        parts.append(document)
    return "\n\n".join(parts) + "\n"


def _convert_special_cli(line: str, profile_name: str) -> Optional[str]:
    if profile_name not in {"831-ihub", "sr_os"}:
        return None

    token = line.split()[0] if line.split() else ""
    if token == "commit":
        from xml2cli.profiles.sr_os import build_commit_rpc

        return build_commit_rpc()
    if token == "discard":
        from xml2cli.profiles.sr_os import build_discard_rpc

        return build_discard_rpc()
    if token == "oam-save":
        from xml2cli.profiles.sr_os import build_oamsave_rpc

        return build_oamsave_rpc()
    return None


def _convert_edit_config(rpc: RpcDocument, profile: Profile) -> list[str]:
    config_parent = _find_child(rpc.payload, "config")
    if config_parent is None:
        raise ValueError("Missing <config> in edit-config RPC")

    config_root = find_config_root(config_parent, profile.config_root_tags)
    results: list[str] = []
    prefix = _initial_path(profile, config_root)

    for child in child_elements(config_root):
        _traverse_element(child, prefix, profile, results)

    return results


def _convert_get_config(rpc: RpcDocument, profile: Profile) -> list[str]:
    filter_elem = _find_child(rpc.payload, "filter")
    if filter_elem is None:
        raise ValueError("Missing <filter> in get-config RPC")

    config_root = find_config_root(filter_elem, profile.config_root_tags)
    path = ["admin", "display-config", *_initial_path(profile, config_root)]
    for child in child_elements(config_root):
        _collect_path(child, path, profile)
    return [" ".join(path)]


def _convert_get(rpc: RpcDocument, profile: Profile) -> list[str]:
    filter_elem = _find_child(rpc.payload, "filter")
    if filter_elem is None:
        raise ValueError("Missing <filter> in get RPC")

    state_root = None
    for elem in filter_elem.iter():
        if local_name(elem.tag) == "state":
            state_root = elem
            break
    if state_root is None:
        raise ValueError("Missing <state> in get filter")

    path = ["show"]
    for child in child_elements(state_root):
        _collect_path(child, path, profile)
        break
    return [" ".join(path)]


def _collect_path(elem: ET.Element, path: list[str], profile: Profile) -> None:
    tag = local_name(elem.tag)
    path.append(tag)

    keys: dict[str, str] = {}
    for child in child_elements(elem):
        child_name = local_name(child.tag)
        if child_name in profile.list_keys and not child_elements(child):
            keys[child_name] = element_text(child)

    key_value = _get_key_for_container(tag, keys, profile)
    if key_value:
        path.append(key_value)


def _traverse_element(
    elem: ET.Element,
    parent_path: list[str],
    profile: Profile,
    results: list[str],
    inherited_op: Optional[str] = None,
) -> None:
    op = get_operation(elem) or inherited_op
    tag = local_name(elem.tag)
    children = child_elements(elem)

    keys: dict[str, str] = {}
    other_children: list[ET.Element] = []
    for child in children:
        child_name = local_name(child.tag)
        if child_name in profile.list_keys and not child_elements(child):
            keys[child_name] = element_text(child)
        else:
            other_children.append(child)

    path = parent_path + [tag]
    key_value = _get_key_for_container(tag, keys, profile)
    if key_value:
        path.append(key_value)

    if op == "delete" and not other_children:
        results.append(" ".join(path + ["delete"]))
        return

    for child in other_children:
        child_name = local_name(child.tag)
        child_op = get_operation(child) or op
        if not child_elements(child):
            if child_name in profile.list_keys:
                continue
            leaf_val = element_text(child)
            if child_op == "delete":
                results.append(" ".join(path + [child_name, "delete"]))
                continue
            if not leaf_val:
                continue
            cmd = path + [child_name, leaf_val]
            results.append(" ".join(cmd))
        else:
            _traverse_element(child, path, profile, results, inherited_op=child_op)


def _get_key_for_container(container: str, keys: dict[str, str], profile: Profile) -> Optional[str]:
    profile_key = profile.get_key_for_container(container, keys)
    if profile_key:
        return profile_key

    priority = KEY_PRIORITY.get(container, [])
    for key_name in priority:
        if key_name in keys and keys[key_name]:
            return keys[key_name]

    for key_name, value in keys.items():
        if value:
            return value
    return None


def _initial_path(profile: Profile, config_root: ET.Element) -> list[str]:
    prefix = list(profile.cli_prefix)
    root_tag = local_name(config_root.tag)
    if not prefix or prefix[-1] != root_tag:
        prefix.append(root_tag)
    return prefix


def _find_child(parent: Optional[ET.Element], name: str) -> Optional[ET.Element]:
    if parent is None:
        return None
    for child in parent:
        if local_name(child.tag) == name:
            return child
    return None
