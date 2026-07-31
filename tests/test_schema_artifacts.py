"""Verify prebuilt YANG schema artifacts exist for all boards."""

import pytest

from xml2cli.board_registry import list_boards
from xml2cli.yang.schema_store import load_schema


@pytest.mark.parametrize("board", [b.board_id for b in list_boards()], ids=lambda x: x)
def test_schema_artifact_exists(board: str):
    schema = load_schema(board)
    assert schema.board_id == board
    assert schema.config_roots
