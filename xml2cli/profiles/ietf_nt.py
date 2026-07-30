"""IETF System profile (832-nt)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Optional

from xml2cli.xml_parser import NETCONF_NS

IETF_SYSTEM_NS = "urn:ietf:params:xml:ns:yang:ietf-system"
NOKIA_SYSTEM_AUG_NS = "http://www.nokia.com/Fixed-Networks/BBA/yang/nokia-ietf-system-aug"

CONTAINERS = {"management", "debug", "lemi", "ip_itf"}
CONTAINER_KEYS: dict[str, str] = {}


class IetfNtProfile:
    name = "ietf_nt"
    folder_names = ["832-nt"]
    list_keys = {"name"}
    config_root_tags = {"system"}
    cli_prefix: list[str] = []

    def get_key_for_container(self, container: str, keys: dict[str, str]) -> Optional[str]:
        if "name" in keys:
            return keys["name"]
        return None

    def parse_cli_line(self, line: str) -> ET.Element:
        tokens = line.split()
        if not tokens or tokens[0] != "system":
            raise ValueError("832-nt CLI lines must start with 'system'")

        system = ET.Element("system")
        system.set("xmlns", IETF_SYSTEM_NS)

        index = 1
        current = system
        ns_stack = [IETF_SYSTEM_NS]

        while index < len(tokens):
            token = tokens[index]
            if token in CONTAINERS:
                child = ET.SubElement(current, token)
                if token == "management":
                    child.set("xmlns", NOKIA_SYSTEM_AUG_NS)
                    ns_stack.append(NOKIA_SYSTEM_AUG_NS)
                index += 1
                current = child
                continue

            if index + 1 >= len(tokens):
                raise ValueError(f"Expected value after '{token}'")
            leaf = ET.SubElement(current, token)
            leaf.text = tokens[index + 1]
            index += 2

        return system

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
