"""BBF ONU / LT profile (833-LT-1)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from copy import deepcopy
from typing import Optional, Union

from xml2cli.xml_parser import NETCONF_NS, child_elements, local_name

ONU_NS = "urn:bbf:params:xml:ns:yang:bbf-fiber-onu-emulated-mount"
INTERFACES_NS = "urn:ietf:params:xml:ns:yang:ietf-interfaces-mounted"
IP_NS = "urn:ietf:params:xml:ns:yang:ietf-ip-mounted"
NOKIA_IP_AUG_NS = "urn:ietf:params:xml:ns:yang:nokia-ip-aug-mounted"
SYSTEM_MOUNTED_NS = "urn:ietf:params:xml:ns:yang:ietf-system-mounted"
ROUTING_NS = "urn:ietf:params:xml:ns:yang:ietf-routing-mounted"
QOS_CLASSIFIERS_NS = "urn:bbf:yang:bbf-qos-classifiers-mounted"
QOS_POLICIES_NS = "urn:bbf:yang:bbf-qos-policies-mounted"
QOS_POLICING_NS = "urn:bbf:yang:bbf-qos-policing-mounted"
XPONGEMTCONT_NS = "urn:bbf:yang:bbf-xpongemtcont-mounted"

# LT-level CLI roots: map directly to <config> children (not under onus/onu).
LT_ROOT_CLI_TOKENS = frozenset(
    {
        "xpongemtcont",
        "classifiers",
        "policies",
        "qos-policy-profiles",
    }
)

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
    "route",
    "next-hop",
    "xpongemtcont",
    "traffic-descriptor-profiles",
    "traffic-descriptor-profile",
    "classifiers",
    "classifier-entry",
    "match-criteria",
    "pbit-marking-list",
    "classifier-action-entry-cfg",
    "policies",
    "policy",
    "qos-policy-profiles",
    "policy-profile",
    "policy-list",
}

CONTAINER_KEYS = {
    "onu": "name",
    "interface": "name",
    "server": "name",
    "control-plane-protocol": "name",
    "traffic-descriptor-profile": "name",
    "classifier-entry": "name",
    "pbit-marking-list": "index",
    "policy": "name",
    "policy-profile": "name",
    "policy-list": "name",
}

PARENT_CONTAINER_KEYS = {
    ("policy", "classifiers"): "name",
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
    "xpongemtcont": XPONGEMTCONT_NS,
    "traffic-descriptor-profiles": XPONGEMTCONT_NS,
    "classifiers": QOS_CLASSIFIERS_NS,
    "policies": QOS_POLICIES_NS,
    "qos-policy-profiles": QOS_POLICIES_NS,
    "pbit-marking-list": QOS_POLICING_NS,
}

ConfigTree = Union[ET.Element, list[ET.Element]]


class OnuLtProfile:
    name = "onu_lt"
    folder_names = ["833-LT-1"]
    list_keys = {"name", "index"}
    config_root_tags = {"onus", *LT_ROOT_CLI_TOKENS}
    cli_prefix: list[str] = []

    def get_key_for_container(self, container: str, keys: dict[str, str]) -> Optional[str]:
        key_name = CONTAINER_KEYS.get(container)
        if key_name and key_name in keys:
            return keys[key_name]
        return None

    def iter_config_roots(self, config_parent: ET.Element) -> list[ET.Element]:
        roots = [
            child
            for child in child_elements(config_parent)
            if local_name(child.tag) in self.config_root_tags
        ]
        if roots:
            return roots
        raise ValueError(
            f"Config root not found; expected one of: {sorted(self.config_root_tags)}"
        )

    def merge_cli_config_trees(self, trees: list[ET.Element]) -> ConfigTree:
        from xml2cli.engine import _merge_elements

        groups: dict[str, ET.Element] = {}
        order: list[str] = []
        for tree in trees:
            tag = local_name(tree.tag)
            if tag not in groups:
                groups[tag] = deepcopy(tree)
                order.append(tag)
                continue
            _merge_elements(groups[tag], tree, self)
        if len(order) == 1:
            return groups[order[0]]
        return [groups[tag] for tag in order]

    def parse_cli_line(self, line: str) -> ET.Element:
        tokens = line.split()
        if not tokens:
            raise ValueError("Empty CLI line")

        if tokens[0] == "onus":
            return self._parse_onus_prefixed_line(tokens)

        if tokens[0] in LT_ROOT_CLI_TOKENS:
            return self._parse_lt_root_line(tokens)

        raise ValueError(
            "833-LT-1 CLI lines must start with 'onus' or an LT root path "
            f"({', '.join(sorted(LT_ROOT_CLI_TOKENS))})"
        )

    def _parse_onus_prefixed_line(self, tokens: list[str]) -> ET.Element:
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
        if index < len(tokens) and tokens[index] == "root":
            root = ET.SubElement(onu, "root")
            index += 1
            current = root

        self._parse_tokens(tokens, index, current)
        return onus

    def _parse_lt_root_line(self, tokens: list[str]) -> ET.Element:
        root_tag = tokens[0]
        root = ET.Element(root_tag)
        ns = NS_FOR_CONTAINER.get(root_tag)
        if ns:
            root.set("xmlns", ns)
        self._parse_tokens(tokens, 1, root)
        return root

    def _parse_tokens(self, tokens: list[str], index: int, current: ET.Element) -> None:
        while index < len(tokens):
            token = tokens[index]

            if token in CONTAINERS:
                child = ET.SubElement(current, token)
                ns = NS_FOR_CONTAINER.get(token)
                if ns and not _should_skip_namespace(local_name(current.tag), token):
                    child.set("xmlns", ns)
                index += 1

                key_name = PARENT_CONTAINER_KEYS.get((local_name(current.tag), token))
                if key_name is None:
                    key_name = CONTAINER_KEYS.get(token)
                    if key_name and index < len(tokens) and tokens[index] in CONTAINERS:
                        key_name = None

                if key_name:
                    if index >= len(tokens):
                        raise ValueError(f"Expected value after '{token}'")
                    key_elem = ET.SubElement(child, key_name)
                    key_elem.text = tokens[index]
                    index += 1

                current = child
                continue

            if index + 1 < len(tokens) and tokens[index + 1] == token:
                if index + 2 >= len(tokens):
                    raise ValueError(f"Expected value after '{token}'")
                leaf = ET.SubElement(current, token)
                leaf.text = tokens[index + 2]
                index += 3
                continue

            if index + 1 >= len(tokens):
                raise ValueError(f"Expected value after '{token}'")
            leaf = ET.SubElement(current, token)
            leaf.text = tokens[index + 1]
            index += 2

    def wrap_config_in_rpc(self, config_elem: ConfigTree) -> str:
        rpc = ET.Element("rpc", {"xmlns": NETCONF_NS, "message-id": "1"})
        edit_config = ET.SubElement(rpc, "edit-config")
        target = ET.SubElement(edit_config, "target")
        ET.SubElement(target, "running")
        config = ET.SubElement(edit_config, "config")

        elements = config_elem if isinstance(config_elem, list) else [config_elem]
        for elem in elements:
            config.append(elem)

        ET.indent(rpc, space="  ")
        xml_str = ET.tostring(rpc, encoding="unicode")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str + "\n"


def _should_skip_namespace(parent_tag: str, child_tag: str) -> bool:
    if parent_tag == "policy" and child_tag == "classifiers":
        return True
    if parent_tag == "xpongemtcont" and child_tag == "traffic-descriptor-profiles":
        return True
    return False
