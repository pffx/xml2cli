"""NETCONF action RPC: manual-rogue-test-start on LT."""

from xml2cli.conversion import convert_xml_to_cli_auto

MANUAL_ROGUE_ACTION_XML = """<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
  <action xmlns="urn:ietf:params:xml:ns:yang:1">
    <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
      <interface>
        <name>xpon-1-1-primary-ctermination</name>
        <channel-termination xmlns="urn:bbf:yang:bbf-xpon">
          <manual-rogue-test-start xmlns="urn:broadband-forum-org:yang:bbf-fiber-rogue-nodes">
            <manual-test-name>manual-test</manual-test-name>
            <rogue-test-profile-ref>rogue-test-profile1</rogue-test-profile-ref>
          </manual-rogue-test-start>
        </channel-termination>
      </interface>
    </interfaces>
  </action>
</rpc>"""


def test_manual_rogue_test_start_action_to_cli():
    cli, errors, board = convert_xml_to_cli_auto(MANUAL_ROGUE_ACTION_XML)
    assert errors == []
    assert board == "LWLT-C"
    assert cli == [
        "interfaces interface xpon-1-1-primary-ctermination channel-termination "
        "manual-rogue-test-start -w manual-test-name manual-test "
        "-w rogue-test-profile-ref rogue-test-profile1"
    ]
