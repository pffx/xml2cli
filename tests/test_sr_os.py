"""Tests for SR OS profile (831-ihub)."""

from pathlib import Path

import pytest

from xml2cli.engine import convert_cli_to_xml, convert_xml_to_cli

XML_DIR = Path(__file__).resolve().parent.parent / "xml" / "831-ihub"


def test_config_port_xml_to_cli():
    content = (XML_DIR / "Config_port.xml").read_text(encoding="utf-8")
    cli_lines, errors = convert_xml_to_cli(content, "831-ihub")
    assert errors == []
    assert cli_lines == [
        "configure service vpls 4093 sap 1/1/c1/1:0 admin-state enable"
    ]


def test_del_vpls_xml_to_cli():
    content = (XML_DIR / "Del_vpls.xml").read_text(encoding="utf-8")
    cli_lines, errors = convert_xml_to_cli(content, "831-ihub")
    assert errors == []
    assert "configure service vpls 4093 delete" in cli_lines


def test_commit_xml_to_cli():
    content = (Path(__file__).resolve().parent.parent / "xml" / "COMMIT.XML").read_text(
        encoding="utf-8"
    )
    cli_lines, errors = convert_xml_to_cli(content, "831-ihub")
    assert errors == []
    assert cli_lines == ["commit"]


def test_discard_xml_to_cli():
    content = (XML_DIR / "DISCARD.XML").read_text(encoding="utf-8")
    cli_lines, errors = convert_xml_to_cli(content, "831-ihub")
    assert errors == []
    assert cli_lines == ["discard"]


def test_get_port_config_xml_to_cli():
    content = (XML_DIR / "GET_Port_config.xml").read_text(encoding="utf-8")
    cli_lines, errors = convert_xml_to_cli(content, "831-ihub")
    assert errors == []
    assert cli_lines == ["admin display-config configure port 1/2/1"]


def test_get_port_status_xml_to_cli():
    content = (XML_DIR / "GET_Port_status.xml").read_text(encoding="utf-8")
    cli_lines, errors = convert_xml_to_cli(content, "831-ihub")
    assert errors == []
    assert cli_lines == ["show port 1/2/1"]


def test_config_port_cli_to_xml_roundtrip():
    cli = "configure service vpls 4093 sap 1/1/c1/1:0 admin-state enable"
    xml_output, errors = convert_cli_to_xml(cli, "831-ihub")
    assert errors == []
    assert "<rpc" in xml_output
    assert "<edit-config>" in xml_output
    assert "<candidate" in xml_output
    assert "admin-state" in xml_output
    assert "enable" in xml_output

    cli_lines, roundtrip_errors = convert_xml_to_cli(xml_output, "831-ihub")
    assert roundtrip_errors == []
    assert cli_lines == [cli]


def test_save_oam_xml_to_cli():
    content = (XML_DIR / "Save_OAM.xml").read_text(encoding="utf-8")
    cli_lines, errors = convert_xml_to_cli(content, "831-ihub")
    assert errors == []
    assert cli_lines == ["oam-save"]


def test_config_ipv4_dhcp_xml_to_cli():
    content = (XML_DIR / "Config_ipv4_dhcp.xml").read_text(encoding="utf-8")
    cli_lines, errors = convert_xml_to_cli(content, "831-ihub")
    assert errors == []
    assert cli_lines == [
        "configure service ies 2 admin-state enable",
        "configure service ies 2 customer 1",
        "configure service ies 2 interface mgmt_ztp admin-state enable",
        "configure service ies 2 interface mgmt_ztp oamsave true",
        "configure service ies 2 interface mgmt_ztp sap 1/5/1:4093 admin-state enable",
        "configure service ies 2 interface mgmt_ztp ipv4 dhcp admin-state enable",
    ]
    assert not any("ipv6" in line for line in cli_lines)
