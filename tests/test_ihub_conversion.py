"""Tests for IHUB family schema-driven conversion."""

import xml.etree.ElementTree as ET

from xml2cli.families.ihub import IhubFamily
from xml2cli.xml_parser import local_name
from xml2cli.yang.schema_store import load_schema

IHUB_CLI = "configure card 1 admin-state enable"


def test_parse_configure_card_admin_state():
    schema = load_schema("IHUB-LMNT-A")
    family = IhubFamily()
    tokens = IHUB_CLI.split()

    configure = family.parse_cli_line(tokens, schema)

    assert local_name(configure.tag) == "configure"
    card = configure.find("card")
    assert card is not None
    slot = card.find("slot-number")
    assert slot is not None
    assert slot.text == "1"
    admin_state = card.find("admin-state")
    assert admin_state is not None
    assert admin_state.text == "enable"


def test_xml_to_cli_roundtrip_configure_card():
    schema = load_schema("IHUB-LMNT-A")
    family = IhubFamily()
    tokens = IHUB_CLI.split()
    configure = family.parse_cli_line(tokens, schema)

    lines = family.xml_to_cli_lines(configure, schema, path=[])
    assert lines == [IHUB_CLI]


def test_commit_wraps_commit_rpc():
    family = IhubFamily()
    rpc_xml = family.wrap_special_rpc("commit")

    root = ET.fromstring(rpc_xml)
    assert local_name(root.tag) == "rpc"
    assert local_name(root[0].tag) == "commit"


def test_discard_wraps_discard_rpc():
    family = IhubFamily()
    rpc_xml = family.wrap_special_rpc("discard")

    root = ET.fromstring(rpc_xml)
    assert local_name(root.tag) == "rpc"
    assert local_name(root[0].tag) == "discard-changes"


def test_edit_config_targets_candidate():
    schema = load_schema("IHUB-LMNT-A")
    family = IhubFamily()
    configure = family.parse_cli_line(IHUB_CLI.split(), schema)

    rpc_xml = family.wrap_edit_config([configure])
    assert "<candidate" in rpc_xml
    assert "slot-number" in rpc_xml
    assert "admin-state" in rpc_xml
