"""NT board conversion tests (inline fixtures)."""

from xml2cli.engine import convert_cli_to_xml, convert_xml_to_cli

DEBUG_XML = """<rpc message-id="1" xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <edit-config>
    <target><running/></target>
    <config>
      <system xmlns="urn:ietf:params:xml:ns:yang:ietf-system">
        <management xmlns="http://www.nokia.com/Fixed-Networks/BBA/yang/nokia-ietf-system-aug">
          <debug>
            <lemi><enable>true</enable></lemi>
          </debug>
        </management>
      </system>
    </config>
  </edit-config>
</rpc>"""


def test_debug_lemi_xml_to_cli():
    cli_lines, errors = convert_xml_to_cli(DEBUG_XML, "NT-LMNT-A")
    assert errors == []
    assert "system management debug lemi enable true" in cli_lines


def test_debug_lemi_cli_to_xml():
    cli = "system management debug lemi enable true"
    xml_output, errors = convert_cli_to_xml(cli, "NT-LMNT-A")
    assert errors == []
    assert "<system" in xml_output
    assert "<lemi>" in xml_output
