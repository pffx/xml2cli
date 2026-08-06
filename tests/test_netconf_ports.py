"""Tests for NETCONF port mapping."""

import pytest

from xml2cli.board_registry import get_board
from xml2cli.netconf_ports import (
    NETCONF_PORT_IHUB,
    NETCONF_PORT_LT_BASE,
    NETCONF_PORT_LT_MAX,
    NETCONF_PORT_NT,
    lt_slot_to_port,
    netconf_port_for_board,
    port_to_lt_slot,
    resolve_legacy_profile_name,
)


def test_family_ports():
    assert netconf_port_for_board("IHUB-LMNT-A") == NETCONF_PORT_IHUB
    assert netconf_port_for_board("NT-LMNT-A") == NETCONF_PORT_NT


def test_lt_slot_ports():
    assert lt_slot_to_port(1) == 833
    assert lt_slot_to_port(2) == 834
    assert lt_slot_to_port(16) == 848
    assert port_to_lt_slot(833) == 1
    assert port_to_lt_slot(848) == 16


def test_lt_board_slots():
    assert netconf_port_for_board("LWLT-C") == 833
    assert netconf_port_for_board("LLLT-A") == 834
    assert netconf_port_for_board("LGLT-D") == 835


def test_lt_slot_bounds():
    with pytest.raises(ValueError):
        lt_slot_to_port(0)
    with pytest.raises(ValueError):
        lt_slot_to_port(17)


def test_legacy_profile_names():
    assert resolve_legacy_profile_name("831-ihub") == "IHUB-LMNT-A"
    assert resolve_legacy_profile_name("832-nt") == "NT-LMNT-A"
    assert resolve_legacy_profile_name("833-LT-1") == "LWLT-C"
    assert resolve_legacy_profile_name("834-LT-2") == "LLLT-A"
    assert resolve_legacy_profile_name("835-LT-3") == "LGLT-D"
    assert resolve_legacy_profile_name("848-LT-16") == "LWLT-C"


def test_board_registry_lt_slot():
    assert get_board("LWLT-C").lt_slot == 1
