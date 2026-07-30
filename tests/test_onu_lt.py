"""Tests for ONU LT profile (833-LT-1)."""

from pathlib import Path

from xml2cli.engine import convert_xml_to_cli

XML_DIR = Path(__file__).resolve().parent.parent / "xml" / "833-LT-1"


def test_static_ip_xml_to_cli():
    content = (XML_DIR / "rpc-staticip-g080gea.xml").read_text(encoding="utf-8")
    cli_lines, errors = convert_xml_to_cli(content, "833-LT-1")
    assert errors == []
    assert any("onus onu PON1/ONT1" in line for line in cli_lines)
    assert any("enabled true" in line for line in cli_lines)


def test_change_dhcp_xml_to_cli():
    content = (XML_DIR / "Change_DHCP to Static.xml").read_text(encoding="utf-8")
    cli_lines, errors = convert_xml_to_cli(content, "833-LT-1")
    assert errors == []
    assert any("onus onu PON5/ONT5" in line for line in cli_lines)
