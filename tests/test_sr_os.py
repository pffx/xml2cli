"""Legacy IHUB tests — use schema-driven ihub family."""

from xml2cli.engine import convert_cli_to_xml, convert_xml_to_cli

COMMIT_XML = """<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
  <commit />
</rpc>"""

DISCARD_XML = """<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
  <discard-changes />
</rpc>"""


def test_commit_xml_to_cli():
    cli_lines, errors = convert_xml_to_cli(COMMIT_XML, "IHUB-LMNT-A")
    assert errors == []
    assert cli_lines == ["commit"]


def test_discard_xml_to_cli():
    cli_lines, errors = convert_xml_to_cli(DISCARD_XML, "IHUB-LMNT-A")
    assert errors == []
    assert cli_lines == ["discard"]


def test_configure_card_cli_to_xml_roundtrip():
    cli = "configure card 1 admin-state enable"
    xml_output, errors = convert_cli_to_xml(cli, "IHUB-LMNT-A")
    assert errors == []
    assert "<configure" in xml_output
    cli_lines, errors = convert_xml_to_cli(xml_output, "IHUB-LMNT-A")
    assert errors == []
    assert cli_lines == ["configure card 1 admin-state enable"]
