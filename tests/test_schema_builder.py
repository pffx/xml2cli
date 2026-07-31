import pytest

from xml2cli.board_registry import list_boards
from xml2cli.yang.schema import BoardSchema
from xml2cli.yang.schema_builder import build_board_schema
from xml2cli.yang.schema_store import _schema_from_dict, _schema_to_dict, save_schema


def test_lwlt_c_config_roots_include_classifiers_and_onus():
    schema = build_board_schema("LWLT-C", mode="standard")
    assert "classifiers" in schema.config_roots
    assert "onus" in schema.config_roots
    assert "xpongemtcont" in schema.config_roots


def test_ihub_lmnt_a_has_configure_root():
    schema = build_board_schema("IHUB-LMNT-A", mode="standard")
    assert "configure" in schema.config_roots
    assert "action-rpc" not in schema.config_roots


def test_board_schema_round_trip_via_schema_store(tmp_path):
    schema = build_board_schema("LWLT-C", mode="standard")
    path = tmp_path / "LWLT-C.json"
    save_schema(schema, path=path)
    restored = _schema_from_dict(_schema_to_dict(schema))
    assert restored == schema


@pytest.mark.parametrize("board_id", [board.board_id for board in list_boards()])
def test_build_board_schema_for_all_boards(board_id: str):
    schema = build_board_schema(board_id, mode="standard")
    assert isinstance(schema, BoardSchema)
    assert schema.board_id == board_id
    assert schema.modules
