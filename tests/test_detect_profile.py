"""Profile detection tests."""

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


def test_detect_profile_ip_itf_xml():
    assert detect_profile_from_xml(USER_XML) == "832-nt"


def test_convert_ip_itf_xml_with_wrong_profile_hint():
    cli_lines, errors = convert_xml_to_cli(USER_XML, "831-ihub")
    assert cli_lines == []
    assert "832-nt" in errors[0]


def test_convert_ip_itf_xml_with_correct_profile():
    cli_lines, errors, profile = convert_xml_to_cli_auto(USER_XML)
    assert errors == []
    assert profile == "832-nt"
    assert cli_lines == ["system management debug ip_itf enable true"]


def test_detect_profile_from_cli():
    assert detect_profile_from_cli("system management debug lemi enable true") == "832-nt"
    assert detect_profile_from_cli("configure service vpls 4093 delete") == "831-ihub"
    assert detect_profile_from_cli("onus onu PON1/ONT1 root") == "833-LT-1"


def test_cli_to_xml_auto():
    xml_output, errors, profile = convert_cli_to_xml_auto(
        "system management debug lemi enable true"
    )
    assert errors == []
    assert profile == "832-nt"
    assert "<system" in xml_output


def test_cli_to_xml_multiple_lines():
    cli = "\n".join(
        [
            "configure service vpls 4093 sap 1/1/c1/1:0 admin-state enable",
            "configure service vpls 4093 sap 1/1/c1/2:0 admin-state enable",
        ]
    )
    xml_output, errors, profile = convert_cli_to_xml_auto(cli)
    assert errors == []
    assert profile == "831-ihub"
    assert xml_output.count("<rpc") == 1
    assert xml_output.count("<sap>") == 2
    assert "1/1/c1/1:0" in xml_output
    assert "1/1/c1/2:0" in xml_output


def test_cli_to_xml_configure_plus_commit():
    cli = "\n".join(
        [
            "configure service vpls 4093 sap 1/1/c1/1:0 admin-state enable",
            "configure service vpls 4093 sap 1/1/c1/2:0 admin-state enable",
            "commit",
        ]
    )
    xml_output, errors, profile = convert_cli_to_xml_auto(cli)
    assert errors == []
    assert profile == "831-ihub"
    assert xml_output.count("<rpc") == 2
    assert xml_output.count("<sap>") == 2
    assert "<commit" in xml_output
