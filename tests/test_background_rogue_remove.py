"""XML→CLI for NETCONF remove on background-rogue-test list entries."""

from xml2cli.conversion import convert_xml_to_cli_auto

ROGUE_REMOVE_XML = """<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
  <edit-config>
    <target>
      <running/>
    </target>
    <config>
      <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface>
          <name>xpon-1-1-primary-ctermination</name>
          <channel-termination xmlns="urn:bbf:yang:bbf-xpon">
            <background-rogue-test xmlns="urn:broadband-forum-org:yang:bbf-fiber-rogue-nodes" xmlns:ns0="urn:ietf:params:xml:ns:netconf:base:1.0" ns0:operation="remove">
              <name>background-test</name>
            </background-rogue-test>
          </channel-termination>
        </interface>
      </interfaces>
    </config>
  </edit-config>
</rpc>"""


def test_background_rogue_test_remove_to_cli():
    cli, errors, board = convert_xml_to_cli_auto(ROGUE_REMOVE_XML)
    assert errors == []
    assert board == "LWLT-C"
    assert cli == [
        "interfaces interface xpon-1-1-primary-ctermination channel-termination "
        "background-rogue-test background-test delete"
    ]
