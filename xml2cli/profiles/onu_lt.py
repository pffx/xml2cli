"""BBF ONU profile (833-LT-1)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Optional

from xml2cli.xml_parser import NETCONF_NS

ONU_NS = "urn:bbf:params:xml:ns:yang:bbf-fiber-onu-emulated-mount"
INTERFACES_NS = "urn:ietf:params:xml:ns:yang:ietf-interfaces-mounted"
IANAIFT_NS = "urn:ietf:params:xml:ns:yang:iana-if-type-mounted"
IP_NS = "urn:ietf:params:xml:ns:yang:ietf-ip-mounted"
NOKIA_IP_AUG_NS = "urn:ietf:params:xml:ns:yang:nokia-ip-aug-mounted"
SYSTEM_MOUNTED_NS = "urn:ietf:params:xml:ns:yang:ietf-system-mounted"
ROUTING_NS = "urn:ietf:params:xml:ns:yang:ietf-routing-mounted"
IPV4_ROUTING_NS = "urn:ietf:params:xml:ns:yang:ietf-ipv4-unicast-routing-mounted"

CONTAINERS = {
    "onu",
    "root",
    "interfaces",
    "interface",
    "ipv4",
    "address",
    "ip-address-acquisition-method",
    "ipif-lower-layer",
    "ip-diagnose-control",
    "system",
    "dns-resolver",
    "server",
    "udp-and-tcp",
    "routing",
    "control-plane-protocols",
    "control-plane-protocol",
    "static-routes",
    "ipv4",
    "route",
    "next-hop",
}

CONTAINER_KEYS = {
    "onu": "name",
    "interface": "name",
    "server": "name",
    "control-plane-protocol": "name",
}

NS_FOR_CONTAINER = {
    "interfaces": INTERFACES_NS,
    "ipv4": IP_NS,
    "ip-address-acquisition-method": NOKIA_IP_AUG_NS,
    "ipif-lower-layer": NOKIA_IP_AUG_NS,
    "ip-diagnose-control": NOKIA_IP_AUG_NS,
    "system": SYSTEM_MOUNTED_NS,
    "routing": ROUTING_NS,
    "static-routes": ROUTING_NS,
    "control-plane-protocol": ROUTING_NS,
}


class OnuLtProfile:
    name = "onu_lt"
    folder_names = ["833-LT-1"]
    list_keys = {"name"}
    config_root_tags = {"onus"}
    cli_prefix = ["onus"]

    def get_key_for_container(self, container: str, keys: dict[str, str]) -> Optional[str]:
        key_name = CONTAINER_KEYS.get(container)
        if key_name and key_name in keys:
            return keys[key_name]
        return None

    def parse_cli_line(self, line: str) -> ET.Element:
        tokens = line.split()
        if not tokens or tokens[0] != "onus":
            raise ValueError("833-LT-1 CLI lines must start with 'onus'")

        onus = ET.Element("onus")
        onus.set("xmlns", ONU_NS)
        index = 1

        if index >= len(tokens) or tokens[index] != "onu":
            raise ValueError("Expected 'onu' after 'onus'")
        index += 1

        onu = ET.SubElement(onus, "onu")
        if index >= len(tokens):
            raise ValueError("Expected ONU name")
        name_elem = ET.SubElement(onu, "name")
        name_elem.text = tokens[index]
        index += 1

        current = onu
        while index < len(tokens):
            token = tokens[index]
            if token in CONTAINERS:
                child = ET.SubElement(current, token)
                ns = NS_FOR_CONTAINER.get(token)
                if ns:
                    child.set("xmlns", ns)
                index += 1
                key_name = CONTAINER_KEYS.get(token)
                if key_name:
                    if index >= len(tokens):
                        raise ValueError(f"Expected value after '{token}'")
                    key_elem = ET.SubElement(child, key_name)
                    key_elem.text = tokens[index]
                    index += 1
                current = child
                continue

            if index + 1 >= len(tokens):
                raise ValueError(f"Expected value after '{token}'")
            leaf = ET.SubElement(current, token)
            leaf.text = tokens[index + 1]
            index += 2

        return onus

    def wrap_config_in_rpc(self, config_elem: ET.Element) -> str:
        rpc = ET.Element("rpc", {"xmlns": NETCONF_NS, "message-id": "1"})
        edit_config = ET.SubElement(rpc, "edit-config")
        target = ET.SubElement(edit_config, "target")
        ET.SubElement(target, "running")
        config = ET.SubElement(edit_config, "config")
        config.append(config_elem)
        ET.indent(rpc, space="  ")
        xml_str = ET.tostring(rpc, encoding="unicode")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str + "\n"
