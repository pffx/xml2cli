"""Tests for IETF NT profile (832-nt)."""

from pathlib import Path

from xml2cli.engine import convert_cli_to_xml, convert_xml_to_cli

XML_DIR = Path(__file__).resolve().parent.parent / "xml" / "832-nt"


def test_debug_lemi_xml_to_cli():
    content = (XML_DIR / "debug_lemi.xml").read_text(encoding="utf-8")
    cli_lines, errors = convert_xml_to_cli(content, "832-nt")
    assert errors == []
    assert cli_lines == ["system management debug lemi enable true"]


def test_debug_lemi_cli_to_xml():
    cli = "system management debug lemi enable true"
    xml_output, errors = convert_cli_to_xml(cli, "832-nt")
    assert errors == []
    assert "<rpc" in xml_output
    assert "<running" in xml_output
    assert "system" in xml_output
    assert "lemi" in xml_output
