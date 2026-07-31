"""Parse pyang tree text into a small AST."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Literal

TreeMode = Literal["standard", "all"]

_MODULE_RE = re.compile(r"^module:\s*(?P<name>\S+)\s*$")
_NODE_RE = re.compile(
    r"^(?P<prefix>[ |]*)(?P<marker>\+---x|\+---n|\+--rw|\+--ro|\+--:|\+--|x--rw|x--ro)(?P<body>.*)$"
)
_KEYS_RE = re.compile(r"\[(?P<keys>[^\]]+)\]")


@dataclass(slots=True)
class TreeLine:
    indent: int
    marker: str
    name: str
    keys: list[str] = field(default_factory=list)
    optional: bool = False
    prefix: str | None = None
    local_name: str | None = None
    is_config: bool = False
    is_state: bool = False
    is_disabled: bool = False
    is_list: bool = False
    is_presence: bool = False
    is_choice: bool = False
    is_case: bool = False


@dataclass(slots=True)
class TreeModule:
    name: str
    lines: list[TreeLine] = field(default_factory=list)


def parse_tree_file(path: Path, mode: TreeMode) -> list[TreeModule]:
    return parse_tree_text(path.read_text(encoding="utf-8"), mode=mode)


def parse_tree_text(text: str, mode: TreeMode) -> list[TreeModule]:
    modules: list[TreeModule] = []
    current: TreeModule | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        module_match = _MODULE_RE.match(line.strip())
        if module_match:
            current = TreeModule(name=module_match.group("name"))
            modules.append(current)
            continue

        if current is None:
            continue

        node = _parse_tree_line(line, mode=mode)
        if node is not None:
            current.lines.append(node)

    return modules


def _parse_tree_line(line: str, mode: TreeMode) -> TreeLine | None:
    match = _NODE_RE.match(line)
    if match is None:
        return None

    marker = match.group("marker")
    is_disabled = marker.startswith("x--") or marker in {"+---x", "+---n"}
    if is_disabled and mode == "standard":
        return None

    prefix = match.group("prefix")
    body = match.group("body").strip()
    if not body:
        return None

    token, _, remainder = body.partition(" ")
    token = token.strip()
    name, optional, local_name, node_prefix, is_list, is_presence, is_choice = _normalize_node_name(token)
    keys = _parse_keys(remainder)
    is_case = marker == "+--:"

    return TreeLine(
        indent=prefix.count(" "),
        marker=marker,
        name=name,
        keys=keys,
        optional=optional,
        prefix=node_prefix,
        local_name=local_name,
        is_config=marker in {"+--rw", "x--rw"},
        is_state=marker in {"+--ro", "x--ro"},
        is_disabled=is_disabled,
        is_list=is_list,
        is_presence=is_presence,
        is_choice=is_choice,
        is_case=is_case,
    )


def _normalize_node_name(token: str) -> tuple[str, bool, str, str | None, bool, bool, bool]:
    optional = False
    is_list = False
    is_presence = False
    is_choice = False

    if token.startswith("(") and ")" in token:
        is_choice = True

    while token and token[-1] in "?!*":
        if token[-1] == "?":
            optional = True
        elif token[-1] == "*":
            is_list = True
        elif token[-1] == "!":
            is_presence = True
        token = token[:-1]

    if token.startswith("(") and token.endswith(")"):
        token = token[1:-1]

    prefix: str | None = None
    local_name = token
    if ":" in token:
        prefix, local_name = token.split(":", 1)

    return token, optional, local_name, prefix, is_list, is_presence, is_choice


def _parse_keys(remainder: str) -> list[str]:
    match = _KEYS_RE.search(remainder)
    if match is None:
        return []
    return [key for key in match.group("keys").split() if key]
