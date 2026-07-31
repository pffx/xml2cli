"""Persist BoardSchema as JSON under yang_schema/{family}/{board_id}.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xml2cli.board_registry import PROJECT_ROOT, get_board
from xml2cli.yang.schema import BoardSchema, SchemaNode
from xml2cli.yang.tree_parser import TreeMode

SCHEMA_ROOT = PROJECT_ROOT / "yang_schema"


def schema_path(board_id: str, family: str | None = None) -> Path:
    if family is None:
        family = get_board(board_id).family
    return SCHEMA_ROOT / family / f"{board_id}.json"


def save_schema(schema: BoardSchema, path: Path | None = None) -> Path:
    target = path or schema_path(schema.board_id, schema.family)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_schema_to_dict(schema), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def load_schema(board_id: str, mode: TreeMode = "standard") -> BoardSchema:
    board = get_board(board_id)
    path = schema_path(board_id, board.family)
    if not path.is_file():
        raise FileNotFoundError(f"Schema file not found: {path}")
    return _schema_from_dict(json.loads(path.read_text(encoding="utf-8")))


def _schema_to_dict(schema: BoardSchema) -> dict[str, Any]:
    return {
        "board_id": schema.board_id,
        "family": schema.family,
        "config_roots": list(schema.config_roots),
        "modules": list(schema.modules),
        "roots": {name: _node_to_dict(node) for name, node in schema.roots.items()},
    }


def _node_to_dict(node: SchemaNode) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": node.name,
        "kind": node.kind,
        "keys": list(node.keys),
        "optional": node.optional,
        "children": {name: _node_to_dict(child) for name, child in node.children.items()},
    }
    if node.prefix is not None:
        payload["prefix"] = node.prefix
    return payload


def _schema_from_dict(payload: dict[str, Any]) -> BoardSchema:
    roots = {
        name: _node_from_dict(node_payload)
        for name, node_payload in payload.get("roots", {}).items()
    }
    return BoardSchema(
        board_id=payload["board_id"],
        family=payload["family"],
        config_roots=list(payload.get("config_roots", [])),
        modules=list(payload.get("modules", [])),
        roots=roots,
    )


def _node_from_dict(payload: dict[str, Any]) -> SchemaNode:
    children = {
        name: _node_from_dict(child_payload)
        for name, child_payload in payload.get("children", {}).items()
    }
    return SchemaNode(
        name=payload["name"],
        kind=payload["kind"],
        keys=list(payload.get("keys", [])),
        prefix=payload.get("prefix"),
        children=children,
        optional=bool(payload.get("optional", False)),
    )
