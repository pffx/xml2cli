"""Board-aware conversion orchestration using YANG schemas and families."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from copy import deepcopy
from typing import Literal, Optional

from xml2cli.board_registry import (
    FAMILY_IHUB,
    FAMILY_LT,
    FAMILY_NT,
    BoardInfo,
    get_board,
    list_boards,
)
from xml2cli.families.base import Family
from xml2cli.families.ihub import IhubFamily
from xml2cli.families.lt import LtFamily
from xml2cli.families.nt import NtFamily
from xml2cli.xml_parser import (
    RpcDocument,
    child_elements,
    local_name,
    parse_rpc,
)
from xml2cli.yang.schema import BoardSchema
from xml2cli.yang.schema_store import load_schema

YangTreeMode = Literal["standard", "all"]

_LT_ROOT_TOKENS = frozenset(
    {
        "xpongemtcont",
        "classifiers",
        "policies",
        "qos-policy-profiles",
        "onus",
        "forwarding",
        "l2-dhcpv4-relay-profiles",
    }
)

_DEFAULT_BOARD_BY_FAMILY = {
    FAMILY_IHUB: "IHUB-LMNT-A",
    FAMILY_NT: "NT-LMNT-A",
    FAMILY_LT: "LWLT-C",
}

_SPECIAL_CLI = {"commit", "discard", "oam-save"}


def list_board_ids() -> list[str]:
    return [board.board_id for board in list_boards()]


def get_family(board_id: str) -> Family:
    board = get_board(board_id)
    if board.family == FAMILY_IHUB:
        return IhubFamily()
    if board.family == FAMILY_NT:
        return NtFamily(board_id)
    if board.family == FAMILY_LT:
        return LtFamily(board_id)
    raise ValueError(f"Unsupported family for board {board_id}")


def load_board_schema(board_id: str, yang_tree: YangTreeMode = "standard") -> BoardSchema:
    return load_schema(board_id, mode=yang_tree)


def detect_board_from_xml(xml_content: str) -> Optional[str]:
    lowered = xml_content.lower()
    if "<commit" in lowered or "<discard-changes" in lowered:
        return _DEFAULT_BOARD_BY_FAMILY[FAMILY_IHUB]
    if "urn:nokia.com:sros:ns:yang:sr:conf" in xml_content or "<configure" in lowered:
        return _DEFAULT_BOARD_BY_FAMILY[FAMILY_IHUB]
    if "bbf-fiber-onu-emulated-mount" in xml_content or "<onus" in lowered:
        return _DEFAULT_BOARD_BY_FAMILY[FAMILY_LT]
    if (
        "bbf-qos-classifiers-mounted" in xml_content
        or "bbf-xpongemtcont" in xml_content
        or "bbf-qos-policies-mounted" in xml_content
    ):
        return _DEFAULT_BOARD_BY_FAMILY[FAMILY_LT]
    if (
        "urn:ietf:params:xml:ns:yang:ietf-system" in xml_content
        or "nokia-ietf-system-aug" in xml_content
    ):
        return _DEFAULT_BOARD_BY_FAMILY[FAMILY_NT]
    return None


def detect_board_from_cli(cli_content: str) -> Optional[str]:
    lines = [line.strip() for line in cli_content.splitlines() if line.strip()]
    if not lines:
        return None
    boards = {_detect_board_from_cli_line(line) for line in lines}
    boards.discard(None)
    if len(boards) == 1:
        return boards.pop()
    if len(boards) > 1:
        return None
    return _detect_board_from_cli_line(lines[0])


def _detect_board_from_cli_line(line: str) -> Optional[str]:
    token = line.split()[0] if line.split() else ""
    if token in {"configure", "commit", "discard", "oam-save"}:
        return _DEFAULT_BOARD_BY_FAMILY[FAMILY_IHUB]
    if token == "onus" or token in _LT_ROOT_TOKENS:
        return _DEFAULT_BOARD_BY_FAMILY[FAMILY_LT]
    if token in {"system", "nokia-debug"}:
        return _DEFAULT_BOARD_BY_FAMILY[FAMILY_NT]
    return None


def convert_xml_to_cli(
    xml_content: str,
    board_id: str,
    yang_tree: YangTreeMode = "standard",
) -> tuple[list[str], list[str]]:
    family = get_family(board_id)
    schema = load_board_schema(board_id, yang_tree=yang_tree)
    try:
        rpc = parse_rpc(xml_content)
    except ValueError as exc:
        return [], [str(exc)]

    special = None
    if isinstance(family, IhubFamily):
        special = family.special_rpc_to_cli(rpc.rpc_type, rpc.payload)
    if special is not None:
        return special, []

    if rpc.rpc_type == "commit":
        if isinstance(family, IhubFamily):
            return ["commit"], []
        return [], [f"commit RPC not supported for board {board_id}"]
    if rpc.rpc_type == "discard-changes":
        if isinstance(family, IhubFamily):
            return ["discard"], []
        return [], [f"discard-changes RPC not supported for board {board_id}"]

    if rpc.rpc_type != "edit-config":
        return [], [f"Unsupported RPC type '{rpc.rpc_type}' for board {board_id}"]

    config_parent = _find_child(rpc.payload, "config")
    if config_parent is None:
        return [], ["Missing <config> in edit-config RPC"]

    results: list[str] = []
    for child in child_elements(config_parent):
        root_name = local_name(child.tag)
        if root_name not in schema.roots:
            continue
        results.extend(family.xml_to_cli_lines(child, schema, []))

    return results, []


def convert_cli_to_xml(
    cli_content: str,
    board_id: str,
    yang_tree: YangTreeMode = "standard",
) -> tuple[str, list[str]]:
    family = get_family(board_id)
    schema = load_board_schema(board_id, yang_tree=yang_tree)
    lines = [line.strip() for line in cli_content.splitlines() if line.strip()]
    if not lines:
        return "", ["No CLI content provided"]

    xml_parts: list[str] = []
    errors: list[str] = []
    config_batch: list[ET.Element] = []

    for index, line in enumerate(lines, start=1):
        token = line.split()[0] if line.split() else ""
        if token in _SPECIAL_CLI:
            if config_batch:
                xml_parts.append(family.wrap_edit_config(_merge_elements(config_batch)).strip())
                config_batch = []
            if not isinstance(family, IhubFamily):
                errors.append(f"第 {index} 行：{token} 仅适用于 IHUB 板卡")
                continue
            try:
                xml_parts.append(family.wrap_special_rpc(token).strip())
            except ValueError as exc:
                errors.append(f"第 {index} 行：{exc}")
            continue

        try:
            config_batch.append(family.parse_cli_line(line.split(), schema))
        except ValueError as exc:
            errors.append(f"第 {index} 行：{exc}")

    if config_batch:
        xml_parts.append(family.wrap_edit_config(_merge_elements(config_batch)).strip())

    if not xml_parts:
        return "", errors
    return _join_rpc_documents(xml_parts), errors


def convert_xml_to_cli_auto(
    xml_content: str,
    yang_tree: YangTreeMode = "standard",
) -> tuple[list[str], list[str], Optional[str]]:
    board_id = detect_board_from_xml(xml_content)
    if board_id is None:
        return [], ["无法根据 XML 内容自动识别板卡类型"], None
    cli_lines, errors = convert_xml_to_cli(xml_content, board_id, yang_tree=yang_tree)
    return cli_lines, errors, board_id


def convert_cli_to_xml_auto(
    cli_content: str,
    yang_tree: YangTreeMode = "standard",
) -> tuple[str, list[str], Optional[str]]:
    board_id = detect_board_from_cli(cli_content)
    if board_id is None:
        return "", ["无法自动识别板卡类型"], None
    xml_output, errors = convert_cli_to_xml(cli_content, board_id, yang_tree=yang_tree)
    return xml_output, errors, board_id


def _merge_elements(trees: list[ET.Element]) -> list[ET.Element]:
    groups: dict[str, ET.Element] = {}
    order: list[str] = []
    for tree in trees:
        tag = local_name(tree.tag)
        if tag not in groups:
            groups[tag] = deepcopy(tree)
            order.append(tag)
            continue
        _merge_element(groups[tag], tree)
    return [groups[tag] for tag in order]


def _merge_element(target: ET.Element, source: ET.Element) -> None:
    for key, value in source.attrib.items():
        target.set(key, value)

    source_children = child_elements(source)
    if not source_children and (source.text or "").strip() and not child_elements(target):
        target.text = source.text
        return

    for src_child in source_children:
        identity = _element_identity(src_child)
        matched = False
        for tgt_child in child_elements(target):
            if _element_identity(tgt_child) == identity:
                _merge_element(tgt_child, src_child)
                matched = True
                break
        if not matched:
            target.append(deepcopy(src_child))


def _element_identity(elem: ET.Element) -> tuple:
    tag = local_name(elem.tag)
    keys = []
    for child in child_elements(elem):
        name = local_name(child.tag)
        if name in {"name", "index", "slot-number"} and not child_elements(child):
            keys.append((name, (child.text or "").strip()))
    if keys:
        return (tag, tuple(keys))
    return (tag,)


def _join_rpc_documents(documents: list[str]) -> str:
    if len(documents) == 1:
        return documents[0] + "\n"
    parts = [documents[0]]
    for document in documents[1:]:
        if document.startswith("<?xml"):
            document = document.split("?>", 1)[1].lstrip("\n")
        parts.append(document)
    return "\n\n".join(parts) + "\n"


def _find_child(parent: ET.Element | None, name: str) -> ET.Element | None:
    if parent is None:
        return None
    for child in parent:
        if local_name(child.tag) == name:
            return child
    return None


def board_info_dict(board: BoardInfo) -> dict[str, str]:
    return {
        "id": board.board_id,
        "family": board.family,
        "tree_path": str(board.tree_path),
    }
