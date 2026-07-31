"""CLI entry point for building and saving board YANG schemas."""

from __future__ import annotations

import argparse
import sys

from xml2cli.board_registry import list_boards
from xml2cli.yang.schema_builder import build_board_schema
from xml2cli.yang.schema_store import save_schema
from xml2cli.yang.tree_parser import TreeMode


def build_schemas(board_ids: list[str] | None = None, mode: TreeMode = "standard") -> list[str]:
    targets = board_ids or [board.board_id for board in list_boards()]
    written: list[str] = []
    for board_id in targets:
        schema = build_board_schema(board_id, mode=mode)
        path = save_schema(schema)
        written.append(str(path))
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build YANG board schemas to JSON")
    parser.add_argument("--board", help="Build schema for a single board id")
    parser.add_argument(
        "--yang-tree",
        choices=("standard", "all"),
        default="standard",
        help="YANG tree variant to parse (default: standard)",
    )
    args = parser.parse_args(argv)

    board_ids = [args.board] if args.board else None
    try:
        paths = build_schemas(board_ids=board_ids, mode=args.yang_tree)
    except (KeyError, FileNotFoundError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    for path in paths:
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
