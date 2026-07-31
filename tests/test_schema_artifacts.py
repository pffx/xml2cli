"""Verify prebuilt YANG schema artifacts exist for all boards."""

import pytest

from xml2cli.board_registry import list_boards
from xml2cli.yang.schema_store import load_schema


@pytest.mark.parametrize("board", [b.board_id for b in list_boards()], ids=lambda x: x)
def test_schema_artifact_exists(board: str):
    schema = load_schema(board)
    assert schema.board_id == board
    assert schema.config_roots


@pytest.mark.parametrize("board", [b.board_id for b in list_boards()], ids=lambda x: x)
def test_schema_all_artifact_exists(board: str):
    board_info = next(b for b in list_boards() if b.board_id == board)
    if board_info.tree_all_path is None:
        pytest.skip(f"{board} has no _all YANG tree")
    schema = load_schema(board, mode="all")
    assert schema.board_id == board
    assert schema.config_roots
