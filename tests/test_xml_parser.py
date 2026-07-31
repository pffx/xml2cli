"""Tests for NETCONF XML parsing edge cases."""

from xml2cli.xml_parser import local_name, parse_rpc, sanitize_netconf_xml

USER_PON_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
  <edit-config>
    <target>
      <running />
    </target>
    <config>
      <hardware>
        <component>
          <name>PORT1_2:xgs</name>
          <class>transceiver-link-ngpon</class>
          <parent>PON_SFP1</parent>
          <parent-rel-pos>1</parent-rel-pos>
          <admin-state>unlocked</admin-state>
        </component>
      </hardware>
      <interfaces>
        <interface>
          <name>ct_cp_pon1_2</name>
          <type>channel-termination</type>
          <port-layer-if xmlns="urn:bbf:yang:bbf-if-port-ref-mounted">
            <PORT1_2:xgs>
              <channel-termination>
                <location>
                  <inside-olt>
                    <channel-pair-ref>
                      <cp_pon1_2>
                        <channel-termination-type>
                          <xgs>
                            <xgs-pon-id>
                              <1>
                                <pon-tag>
                                  <1111111111111111>
                                    <ber-calc-period>
                                      <10 />
                                    </ber-calc-period>
                                  </1111111111111111>
                                </pon-tag>
                              </1>
                            </xgs-pon-id>
                          </xgs>
                        </channel-termination-type>
                      </cp_pon1_2>
                    </channel-pair-ref>
                  </inside-olt>
                </location>
              </channel-termination>
            </PORT1_2:xgs>
          </port-layer-if>
        </interface>
      </interfaces>
    </config>
  </edit-config>
</rpc>"""


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
    from xml2cli.conversion import convert_xml_to_cli

    cli_lines, errors = convert_xml_to_cli(USER_PON_XML, "LWLT-C")
    assert errors == []
    assert cli_lines
