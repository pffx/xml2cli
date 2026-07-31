"""Regression tests for LT PON XML using docserver startup fixtures."""

from pathlib import Path

import pytest

from tests.conftest import FIXTURES_DIR, wrap_edit_config
from xml2cli.conversion import convert_xml_to_cli, detect_board_from_xml

PON_FIXTURE = FIXTURES_DIR / "pon" / "lwlt_c_channel_termination.xml"
STARTUP_DIR = FIXTURES_DIR / "startup" / "lwlt-c"


@pytest.fixture(scope="module")
def pon_rpc_xml() -> str:
    return PON_FIXTURE.read_text(encoding="utf-8")


def test_detect_board_from_pon_xml(pon_rpc_xml: str):
    assert detect_board_from_xml(pon_rpc_xml) == "LWLT-C"


def test_pon_channel_termination_xml_to_cli(pon_rpc_xml: str):
    cli_lines, errors = convert_xml_to_cli(pon_rpc_xml, "LWLT-C")
    assert errors == []
    joined = "\n".join(cli_lines)
    assert "hardware component PORT1_2:xgs" in joined
    assert "interfaces interface ct_cp_pon1_2 type channel-termination" in joined
    assert "port-layer-if PORT1_2:xgs" in joined
    assert "xgs-pon-id 1 pon-tag 1111111111111111" in joined
    assert "ber-calc-period 10" in joined


def test_pon_channel_termination_xml_to_cli_all_tree(pon_rpc_xml: str):
    cli_lines, errors = convert_xml_to_cli(pon_rpc_xml, "LWLT-C", yang_tree="all")
    assert errors == []
    assert any("port-layer-if PORT1_2:xgs" in line for line in cli_lines)


@pytest.mark.parametrize(
    "fixture_name,expected_tokens",
    [
        (
            "hardware_default.xml",
            [
                "hardware component Board",
                "model-name LWLT-C",
            ],
        ),
        (
            "wavelength_profile.xml",
            [
                "xpon wavelength-profiles wavelength-profile xgspon-wave",
            ],
        ),
    ],
)
def test_startup_fixture_xml_to_cli(fixture_name: str, expected_tokens: list[str]):
    raw = (STARTUP_DIR / fixture_name).read_text(encoding="utf-8")
    rpc_xml = wrap_edit_config(raw)
    cli_lines, errors = convert_xml_to_cli(rpc_xml, "LWLT-C")
    assert errors == []
    joined = "\n".join(cli_lines)
    for token in expected_tokens:
        assert token in joined
