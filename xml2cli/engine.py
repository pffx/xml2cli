"""Conversion engine — delegates to YANG schema-driven conversion."""

from __future__ import annotations

from typing import Optional

from xml2cli import conversion

_LEGACY_PROFILE_TO_BOARD = {
    "831-ihub": "IHUB-LMNT-A",
    "832-nt": "NT-LMNT-A",
    "833-LT-1": "LWLT-C",
    "sr_os": "IHUB-LMNT-A",
    "ietf_nt": "NT-LMNT-A",
    "onu_lt": "LWLT-C",
}


def _resolve_board_id(name: str) -> str:
    return _LEGACY_PROFILE_TO_BOARD.get(name, name)


def detect_profile_from_xml(xml_content: str) -> Optional[str]:
    return conversion.detect_board_from_xml(xml_content)


def detect_profile_from_cli(cli_content: str) -> Optional[str]:
    return conversion.detect_board_from_cli(cli_content)


def convert_xml_to_cli_auto(xml_content: str) -> tuple[list[str], list[str], Optional[str]]:
    return conversion.convert_xml_to_cli_auto(xml_content)


def convert_cli_to_xml_auto(cli_content: str) -> tuple[str, list[str], Optional[str]]:
    return conversion.convert_cli_to_xml_auto(cli_content)


def convert_xml_to_cli(xml_content: str, profile_name: str) -> tuple[list[str], list[str]]:
    return conversion.convert_xml_to_cli(xml_content, _resolve_board_id(profile_name))


def convert_cli_to_xml(cli_content: str, profile_name: str) -> tuple[str, list[str]]:
    return conversion.convert_cli_to_xml(cli_content, _resolve_board_id(profile_name))
