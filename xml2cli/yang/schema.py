"""Schema data models used by YANG-driven conversion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

NodeKind = Literal["container", "list", "leaf", "choice", "case", "presence-container"]


@dataclass(slots=True)
class SchemaNode:
    name: str
    kind: NodeKind
    keys: list[str] = field(default_factory=list)
    prefix: str | None = None
    children: dict[str, "SchemaNode"] = field(default_factory=dict)
    optional: bool = False


@dataclass(slots=True)
class BoardSchema:
    board_id: str
    family: str
    config_roots: list[str]
    modules: list[str]
    roots: dict[str, SchemaNode]
