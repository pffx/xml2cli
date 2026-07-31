"""Tests for LT family conversion."""

from xml2cli.families.lt import LtFamily
from xml2cli.yang.schema_store import load_schema

USER_QOS_CLI = """
xpongemtcont traffic-descriptor-profiles traffic-descriptor-profile TDP_gpon assured-bandwidth 7800000 fixed-bandwidth 1000000 maximum-bandwidth 1250000000
classifiers classifier-entry classifier_eg0 filter-operation match-all-filter match-criteria pbit-marking-list 0 pbit-value 0
classifiers classifier-entry classifier_eg0 classifier-action-entry-cfg scheduling-traffic-class scheduling-traffic-class 0
policies policy policy0 classifiers classifier_eg0
qos-policy-profiles policy-profile EQPP policy-list policy0
""".strip()


def _family() -> LtFamily:
    return LtFamily("LWLT-C")


def test_lt_qos_cli_lines_merge_without_onus_wrapper():
    family = _family()
    schema = load_schema("LWLT-C")
    elems = [family.parse_cli_line(line.split(), schema) for line in USER_QOS_CLI.splitlines()]
    xml = family.wrap_edit_config(elems)
    assert "<onus" not in xml
    assert "<xpongemtcont" in xml
    assert "<classifiers" in xml
    assert "<policies" in xml
    assert "<qos-policy-profiles" in xml
    assert "<scheduling-traffic-class>0</scheduling-traffic-class>" in xml
    policy_section = xml.split("<policy>", 1)[1]
    assert '<classifiers xmlns="urn:bbf:yang:bbf-qos-classifiers-mounted">' not in policy_section


def test_onus_fromroot_path():
    family = _family()
    schema = load_schema("LWLT-C")
    tokens = "onus onu PON1/ONT1 fromroot interfaces interface UNI_LAN enabled true".split()
    elem = family.parse_cli_line(tokens, schema)
    xml = family.wrap_edit_config([elem])
    assert "<onus" in xml
    assert "<name>PON1/ONT1</name>" in xml
    assert "<fromroot>" in xml
