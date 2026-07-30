"""Nokia SR OS profile (831-ihub)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Optional

from xml2cli.xml_parser import NETCONF_NS, child_elements, local_name

SR_CONF_NS = "urn:nokia.com:sros:ns:yang:sr:conf"
SR_ACTION_NS = "urn:nokia.com:sros:ns:yang:sr:action"
YANG_NS = "urn:ietf:params:xml:ns:yang:1"

CONTAINERS = {
    "service",
    "vpls",
    "sap",
    "port",
    "router",
    "static-routes",
    "route",
    "next-hop",
    "ies",
    "interface",
    "ipv4",
    "dhcp",
    "primary",
    "lag",
    "card",
    "mda",
    "connector",
    "system",
    "customer",
    "ipv6",
    "link-local-address",
    "dhcpv4-client",
    "dhcpv6-client",
    "node-ip",
}

CONTAINER_KEYS = {
    "vpls": "service-name",
    "sap": "sap-id",
    "port": "port-id",
    "interface": "interface-name",
    "router": "router-name",
    "route": "ip-prefix",
    "lag": "lag-index",
    "card": "slot-number",
    "mda": "mda-slot",
    "sub-group": "sub-group-id",
    "ies": "service-name",
}


class SrOsProfile:
    name = "sr_os"
    folder_names = ["831-ihub"]
    list_keys = set(CONTAINER_KEYS.values()) | {"sub-group-id", "service-id"}
    config_root_tags = {"configure"}
    cli_prefix = ["configure"]

    def get_key_for_container(self, container: str, keys: dict[str, str]) -> Optional[str]:
        key_name = CONTAINER_KEYS.get(container)
        if key_name and key_name in keys:
            return keys[key_name]
        if container == "vpls" and "service-id" in keys:
            return keys["service-id"]
        return None

    def special_rpc_to_cli(self, rpc_type: str, payload) -> Optional[list[str]]:
        if rpc_type == "commit":
            return ["commit"]
        if rpc_type == "discard-changes":
            return ["discard"]
        if rpc_type == "action":
            for elem in payload.iter():
                if local_name(elem.tag) == "oamsave" and (elem.text or "").strip().lower() == "true":
                    return ["oam-save"]
            return ["action"]
        return None

    def parse_cli_line(self, line: str) -> ET.Element:
        tokens = line.split()
        if not tokens:
            raise ValueError("Empty CLI line")

        if tokens[0] == "commit":
            raise ValueError("Use special RPC template for 'commit'; not supported via config tree")
        if tokens[0] == "discard":
            raise ValueError("Use special RPC template for 'discard'; not supported via config tree")
        if tokens[0] == "oam-save":
            raise ValueError("Use special RPC template for 'oam-save'; not supported via config tree")

        delete = False
        if tokens[-1] == "delete":
            delete = True
            tokens = tokens[:-1]

        if tokens and tokens[0] == "configure":
            tokens = tokens[1:]

        configure = ET.Element("configure")
        configure.set("xmlns", SR_CONF_NS)

        self._parse_children(configure, tokens, 0)
        if delete:
            vpls = configure.find(".//vpls")
            if vpls is not None:
                vpls.set(f"{{{NETCONF_NS}}}operation", "delete")
            else:
                deepest = self._deepest_container(configure)
                if deepest is not None:
                    deepest.set(f"{{{NETCONF_NS}}}operation", "delete")

        return configure

    def _deepest_container(self, parent: ET.Element) -> Optional[ET.Element]:
        containers = [child for child in parent if local_name(child.tag) in CONTAINERS]
        if not containers:
            return None
        child = containers[-1]
        deeper = self._deepest_container(child)
        return deeper or child

    def _parse_children(self, parent: ET.Element, tokens: list[str], index: int) -> int:
        while index < len(tokens):
            token = tokens[index]
            if token in CONTAINERS:
                child = ET.SubElement(parent, token)
                index += 1
                key_name = CONTAINER_KEYS.get(token)
                if key_name:
                    if index >= len(tokens):
                        raise ValueError(f"Expected value after '{token}'")
                    key_elem = ET.SubElement(child, key_name)
                    key_elem.text = tokens[index]
                    index += 1
                index = self._parse_children(child, tokens, index)
            else:
                if index + 1 >= len(tokens):
                    raise ValueError(f"Expected value after leaf '{token}'")
                leaf = ET.SubElement(parent, token)
                leaf.text = tokens[index + 1]
                index += 2
        return index

    def wrap_config_in_rpc(self, config_elem: ET.Element) -> str:
        rpc = ET.Element("rpc", {"xmlns": NETCONF_NS, "message-id": "1"})
        edit_config = ET.SubElement(rpc, "edit-config")
        target = ET.SubElement(edit_config, "target")
        ET.SubElement(target, "candidate")
        config = ET.SubElement(edit_config, "config")
        config.append(config_elem)
        return _pretty_xml(rpc)


def build_commit_rpc() -> str:
    rpc = ET.Element("rpc", {"message-id": "commit", "xmlns": NETCONF_NS})
    ET.SubElement(rpc, "commit")
    return _pretty_xml(rpc)


def build_discard_rpc() -> str:
    rpc = ET.Element("rpc", {"message-id": "discard", "xmlns": NETCONF_NS})
    ET.SubElement(rpc, "discard-changes")
    return _pretty_xml(rpc)


def build_oamsave_rpc() -> str:
    rpc = ET.Element("rpc", {"xmlns": NETCONF_NS, "message-id": "1"})
    action = ET.SubElement(rpc, "action", {"xmlns": YANG_NS})
    action_rpc = ET.SubElement(action, "action-rpc", {"xmlns": SR_ACTION_NS})
    ihub_db = ET.SubElement(action_rpc, "ihub-database")
    oamsave = ET.SubElement(ihub_db, "oamsave")
    oamsave.text = "true"
    return _pretty_xml(rpc)


def _pretty_xml(elem: ET.Element) -> str:
    ET.indent(elem, space="  ")
    xml_str = ET.tostring(elem, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str + "\n"
