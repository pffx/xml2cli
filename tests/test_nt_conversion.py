"""Tests for NT family schema-driven conversion."""

import xml.etree.ElementTree as ET

import pytest

from xml2cli.board_registry import FAMILY_NT, list_boards
from xml2cli.families.nt import NtFamily
from xml2cli.profiles.ietf_nt import IETF_SYSTEM_NS, NOKIA_SYSTEM_AUG_NS
from xml2cli.xml_parser import local_name
from xml2cli.yang.schema_store import load_schema

NT_CLI = "system management debug ip_itf enable true"

NT_BOARDS = [
    board.board_id
    for board in list_boards()
    if board.family == FAMILY_NT
]


def test_parse_system_management_debug_ip_itf():
    schema = load_schema("NT-LMNT-A")
    family = NtFamily("NT-LMNT-A")
    tokens = NT_CLI.split()

    system = family.parse_cli_line(tokens, schema)

    assert local_name(system.tag) == "system"
    assert system.get("xmlns") == IETF_SYSTEM_NS

    management = system.find("management")
    assert management is not None
    assert management.get("xmlns") == NOKIA_SYSTEM_AUG_NS

    debug = management.find("debug")
    assert debug is not None

    ip_itf = debug.find("ip_itf")
    assert ip_itf is not None

    enable = ip_itf.find("enable")
    assert enable is not None
    assert enable.text == "true"


def test_xml_to_cli_roundtrip_system_management_debug_ip_itf():
    schema = load_schema("NT-LMNT-A")
    family = NtFamily("NT-LMNT-A")
    system = family.parse_cli_line(NT_CLI.split(), schema)

    lines = family.xml_to_cli_lines(system, schema, path=[])
    assert lines == [NT_CLI]


def test_edit_config_targets_running():
    schema = load_schema("NT-LMNT-A")
    family = NtFamily("NT-LMNT-A")
    system = family.parse_cli_line(NT_CLI.split(), schema)

    rpc_xml = family.wrap_edit_config([system])
    root = ET.fromstring(rpc_xml)

    assert local_name(root.tag) == "rpc"
    assert "<running" in rpc_xml
    assert "system" in rpc_xml
    assert "management" in rpc_xml
    assert "ip_itf" in rpc_xml
    assert "enable" in rpc_xml


@pytest.mark.parametrize("board_id", NT_BOARDS)
def test_nt_boards_load_schema_and_have_system_root(board_id: str):
    family = NtFamily(board_id)
    schema = family.schema

    assert schema.board_id == board_id
    assert schema.family == FAMILY_NT
    assert "system" in schema.config_roots
    assert "system" in schema.roots
