"""LT board conversion tests."""

from xml2cli.engine import convert_cli_to_xml_auto, detect_profile_from_cli

USER_QOS_CLI = """
xpongemtcont traffic-descriptor-profiles traffic-descriptor-profile TDP_gpon assured-bandwidth 7800000
classifiers classifier-entry classifier_eg0 filter-operation match-all-filter match-criteria pbit-marking-list 0 pbit-value 0
policies policy policy0 classifiers classifier_eg0
qos-policy-profiles policy-profile EQPP policy-list policy0
""".strip()


def test_detect_board_from_lt_level_qos_cli():
    assert detect_profile_from_cli("classifiers classifier-entry classifier_eg0") == "LWLT-C"
    assert detect_profile_from_cli("xpongemtcont traffic-descriptor-profiles") == "LWLT-C"


def test_lt_level_qos_cli_to_xml_is_not_under_onus():
    xml_output, errors, board = convert_cli_to_xml_auto(USER_QOS_CLI)
    assert errors == []
    assert board == "LWLT-C"
    assert "<onus" not in xml_output
    assert "<xpongemtcont" in xml_output
    assert "<classifiers" in xml_output
