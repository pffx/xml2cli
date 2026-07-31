"""Board detection and auto-conversion tests."""

from xml2cli.engine import (
    convert_cli_to_xml_auto,
    convert_xml_to_cli,
    convert_xml_to_cli_auto,
    detect_profile_from_cli,
    detect_profile_from_xml,
)

USER_XML = """<rpc message-id="1" xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <edit-config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
    <target>
      <running/>
    </target>
    <config>
      <system xmlns="urn:ietf:params:xml:ns:yang:ietf-system">
        <management xmlns="http://www.nokia.com/Fixed-Networks/BBA/yang/nokia-ietf-system-aug">
          <debug>
            <ip_itf xmlns:ns0="urn:ietf:params:xml:ns:netconf:base:1.0" ns0:operation="merge">
              <enable>true</enable>
            </ip_itf>
          </debug>
        </management>
      </system>
    </config>
  </edit-config>
</rpc>"""


def test_detect_board_ip_itf_xml():
    assert detect_profile_from_xml(USER_XML) == "NT-LMNT-A"


def test_convert_ip_itf_xml_with_explicit_board():
    cli_lines, errors = convert_xml_to_cli(USER_XML, "NT-LMNT-A")
    assert errors == []
    assert cli_lines == ["system management debug ip_itf enable true"]


def test_convert_ip_itf_xml_auto():
    cli_lines, errors, board = convert_xml_to_cli_auto(USER_XML)
    assert errors == []
    assert board == "NT-LMNT-A"
    assert cli_lines == ["system management debug ip_itf enable true"]


def test_detect_board_from_cli():
    assert detect_profile_from_cli("system management debug lemi enable true") == "NT-LMNT-A"
    assert detect_profile_from_cli("configure card 1 admin-state enable") == "IHUB-LMNT-A"
    assert detect_profile_from_cli("onus onu PON1/ONT1 fromroot") == "LWLT-C"
    assert detect_profile_from_cli("classifiers classifier-entry eg0") == "LWLT-C"


def test_cli_to_xml_auto_nt():
    xml_output, errors, board = convert_cli_to_xml_auto(
        "system management debug lemi enable true"
    )
    assert errors == []
    assert board == "NT-LMNT-A"
    assert "<system" in xml_output


def test_cli_to_xml_ihub_configure_plus_commit():
    cli = "\n".join(
        [
            "configure card 1 admin-state enable",
            "configure card 2 admin-state enable",
            "commit",
        ]
    )
    xml_output, errors, board = convert_cli_to_xml_auto(cli)
    assert errors == []
    assert board == "IHUB-LMNT-A"
    assert xml_output.count("<rpc") == 2
    assert xml_output.count("<card>") == 2
    assert "<commit" in xml_output


def test_lt_qos_cli_auto():
    cli = "classifiers classifier-entry classifier_eg0 filter-operation match-all-filter"
    xml_output, errors, board = convert_cli_to_xml_auto(cli)
    assert errors == []
    assert board == "LWLT-C"
    assert "<classifiers" in xml_output
    assert "<onus" not in xml_output
