"""Conversion engine — delegates to YANG schema-driven conversion."""

from __future__ import annotations

from typing import Optional

from xml2cli import conversion
from xml2cli.netconf_ports import resolve_legacy_profile_name


def _resolve_board_id(name: str) -> str:
    legacy = resolve_legacy_profile_name(name)
    if legacy is not None:
        return legacy
    return name


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
