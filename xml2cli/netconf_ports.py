"""NETCONF SSH port layout for chassis board slots."""

from __future__ import annotations

import re

from xml2cli.board_registry import FAMILY_IHUB, FAMILY_LT, FAMILY_NT, get_board, list_boards

NETCONF_PORT_IHUB = 831
NETCONF_PORT_NT = 832
NETCONF_PORT_LT_BASE = 833
NETCONF_PORT_LT_MAX = 848
LT_SLOT_MIN = 1
LT_SLOT_MAX = 16
CLI_SSH_PORT = 22

_LT_PROFILE_RE = re.compile(r"^(\d+)-LT-(\d+)$", re.IGNORECASE)


def lt_slot_to_port(slot: int) -> int:
    if slot < LT_SLOT_MIN or slot > LT_SLOT_MAX:
        raise ValueError(
            f"LT slot must be between {LT_SLOT_MIN} and {LT_SLOT_MAX}, got {slot}"
        )
    return NETCONF_PORT_LT_BASE + slot - 1


def port_to_lt_slot(port: int) -> int | None:
    if port < NETCONF_PORT_LT_BASE or port > NETCONF_PORT_LT_MAX:
        return None
    return port - NETCONF_PORT_LT_BASE + 1


def netconf_port_for_family(family: str) -> int | None:
    if family == FAMILY_IHUB:
        return NETCONF_PORT_IHUB
    if family == FAMILY_NT:
        return NETCONF_PORT_NT
    return None


def netconf_port_for_lt_slot(slot: int) -> int:
    return lt_slot_to_port(slot)


def netconf_port_for_board(board_id: str) -> int:
    board = get_board(board_id)
    if board.family == FAMILY_IHUB:
        return NETCONF_PORT_IHUB
    if board.family == FAMILY_NT:
        return NETCONF_PORT_NT
    if board.lt_slot is not None:
        return lt_slot_to_port(board.lt_slot)
    return NETCONF_PORT_LT_BASE


def get_board_by_lt_slot(slot: int) -> str | None:
    for board in list_boards():
        if board.family == FAMILY_LT and board.lt_slot == slot:
            return board.board_id
    return None


def resolve_legacy_profile_name(name: str) -> str | None:
    """Map legacy folder names like 833-LT-1 or 834-LT-2 to board_id."""
    lowered = name.lower()
    static = {
        "831-ihub": "IHUB-LMNT-A",
        "832-nt": "NT-LMNT-A",
        "833-lt-1": "LWLT-C",
        "sr_os": "IHUB-LMNT-A",
        "ietf_nt": "NT-LMNT-A",
        "onu_lt": "LWLT-C",
    }
    if lowered in static:
        return static[lowered]

    match = _LT_PROFILE_RE.match(name)
    if match is None:
        return None

    port = int(match.group(1))
    slot = int(match.group(2))
    expected_port = lt_slot_to_port(slot)
    if port != expected_port:
        return None

    board_id = get_board_by_lt_slot(slot)
    if board_id is not None:
        return board_id
    return "LWLT-C"


__all__ = [
    "CLI_SSH_PORT",
    "LT_SLOT_MAX",
    "LT_SLOT_MIN",
    "NETCONF_PORT_IHUB",
    "NETCONF_PORT_LT_BASE",
    "NETCONF_PORT_LT_MAX",
    "NETCONF_PORT_NT",
    "get_board_by_lt_slot",
    "lt_slot_to_port",
    "netconf_port_for_board",
    "netconf_port_for_family",
    "netconf_port_for_lt_slot",
    "port_to_lt_slot",
    "resolve_legacy_profile_name",
]
