"""Tests for NETCONF XML parsing edge cases."""

from pathlib import Path

from tests.conftest import FIXTURES_DIR
from xml2cli.conversion import convert_xml_to_cli
from xml2cli.xml_parser import local_name, parse_rpc, sanitize_netconf_xml

USER_PON_XML = (FIXTURES_DIR / "pon" / "lwlt_c_channel_termination.xml").read_text(encoding="utf-8")


def test_sanitize_unbound_colon_and_numeric_tags():
    sanitized = sanitize_netconf_xml(USER_PON_XML)
    assert "PORT1_2__COLON__xgs" in sanitized
    assert "<__key__1>" in sanitized
    assert "<__key__1111111111111111>" in sanitized
    assert "<__key__10 />" in sanitized


def test_parse_rpc_with_yang_key_style_tags():
    rpc = parse_rpc(USER_PON_XML)
    assert rpc.rpc_type == "edit-config"


def test_local_name_decodes_sanitized_tags():
    assert local_name("PORT1_2__COLON__xgs") == "PORT1_2:xgs"
    assert local_name("__key__1") == "1"
    assert local_name("__key__10") == "10"


def test_convert_user_pon_xml_to_cli():
    cli_lines, errors = convert_xml_to_cli(USER_PON_XML, "LWLT-C")
    assert errors == []
    assert any("port-layer-if PORT1_2:xgs" in line for line in cli_lines)
