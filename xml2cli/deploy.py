"""Deploy generated CLI or NETCONF XML to a remote device."""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Literal

from xml2cli.conversion import convert_cli_to_xml, convert_xml_to_cli
from xml2cli.xml_parser import parse_rpc

ContentFormat = Literal["cli", "xml"]
Transport = Literal["netconf", "cli"]

_RPC_PATTERN = re.compile(r"<rpc\b[^>]*>.*?</rpc>", re.DOTALL | re.IGNORECASE)

# Older confd/Nokia peers often offer only ssh-rsa host keys; paramiko 3+ drops it by default.
_LEGACY_SSH_KEY_ALGORITHMS = (
    "ssh-rsa",
    "rsa-sha2-512",
    "rsa-sha2-256",
    "ssh-ed25519",
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
)


def _configure_legacy_ssh() -> None:
    """Allow ssh-rsa host keys for older NETCONF/SSH peers (e.g. confd)."""
    import paramiko
    from cryptography.hazmat.primitives import hashes
    from paramiko.rsakey import RSAKey

    paramiko.Transport._preferred_keys = _LEGACY_SSH_KEY_ALGORITHMS
    paramiko.Transport._preferred_pubkeys = _LEGACY_SSH_KEY_ALGORITHMS

    # paramiko 5 removed ssh-rsa from _key_info; without this, host-key verify
    # raises KeyError('ssh-rsa') after KEX when the peer only offers ssh-rsa.
    key_info = dict(paramiko.Transport._key_info)
    key_info["ssh-rsa"] = RSAKey
    key_info["ssh-rsa-cert-v01@openssh.com"] = RSAKey
    paramiko.Transport._key_info = key_info

    # paramiko 5 dropped SHA-1 from RSAKey.HASHES; legacy peers sign KEX with
    # algorithm name "ssh-rsa" (PKCS1v15 + SHA-1), causing verify_ssh_sig to fail.
    rsa_hashes = dict(RSAKey.HASHES)
    rsa_hashes["ssh-rsa"] = hashes.SHA1
    rsa_hashes["ssh-rsa-cert-v01@openssh.com"] = hashes.SHA1
    RSAKey.HASHES = rsa_hashes


@dataclass(frozen=True, slots=True)
class DeviceTarget:
    host: str
    port: int
    username: str
    password: str
    transport: Transport = "netconf"


@dataclass(frozen=True, slots=True)
class DeployResult:
    success: bool
    message: str
    details: tuple[str, ...] = ()


def split_rpc_documents(xml_content: str) -> list[str]:
    matches = _RPC_PATTERN.findall(xml_content.strip())
    if matches:
        return matches
    stripped = xml_content.strip()
    return [stripped] if stripped else []


def rpc_operation_xml(rpc_xml: str) -> str:
    document = parse_rpc(rpc_xml)
    for child in document.root:
        return ET.tostring(child, encoding="unicode")
    raise ValueError("RPC document has no operation element")


def prepare_deploy_payload(
    content: str,
    *,
    content_format: ContentFormat,
    transport: Transport,
    board: str | None,
    yang_tree: Literal["standard", "all"] = "standard",
) -> tuple[ContentFormat, str]:
    if transport == "netconf":
        if content_format == "xml":
            return "xml", content
        if not board:
            raise ValueError("NETCONF 下发 CLI 时需要指定板卡")
        xml_output, errors = convert_cli_to_xml(content, board, yang_tree=yang_tree)
        if not xml_output:
            detail = "; ".join(errors) if errors else "CLI 转 XML 失败"
            raise ValueError(detail)
        return "xml", xml_output

    if content_format == "cli":
        return "cli", content
    if not board:
        raise ValueError("CLI 下发 XML 时需要指定板卡")
    cli_lines, errors = convert_xml_to_cli(content, board, yang_tree=yang_tree)
    if not cli_lines:
        detail = "; ".join(errors) if errors else "XML 转 CLI 失败"
        raise ValueError(detail)
    return "cli", "\n".join(cli_lines)


def deploy_to_device(
    content: str,
    *,
    content_format: ContentFormat,
    target: DeviceTarget,
    board: str | None = None,
    yang_tree: Literal["standard", "all"] = "standard",
) -> DeployResult:
    try:
        payload_format, payload = prepare_deploy_payload(
            content,
            content_format=content_format,
            transport=target.transport,
            board=board,
            yang_tree=yang_tree,
        )
    except ValueError as exc:
        return DeployResult(False, str(exc))

    if target.transport == "netconf":
        return _deploy_netconf(payload, target)
    return _deploy_cli(payload, target)


def _deploy_netconf(xml_content: str, target: DeviceTarget) -> DeployResult:
    try:
        from ncclient import manager
        from ncclient.xml_ import to_ele
    except ImportError:
        return DeployResult(
            False,
            "缺少 NETCONF 依赖，请执行: pip install ncclient paramiko",
        )

    rpc_documents = split_rpc_documents(xml_content)
    if not rpc_documents:
        return DeployResult(False, "没有可下发的 NETCONF RPC")

    _configure_legacy_ssh()
    details: list[str] = []
    try:
        with manager.connect(
            host=target.host,
            port=target.port,
            username=target.username,
            password=target.password,
            hostkey_verify=False,
            allow_agent=False,
            look_for_keys=False,
            timeout=30,
        ) as session:
            for index, rpc_xml in enumerate(rpc_documents, start=1):
                operation_xml = rpc_operation_xml(rpc_xml)
                response = session.dispatch(to_ele(operation_xml))
                details.append(f"RPC {index}: {response}")
    except Exception as exc:  # noqa: BLE001 - surface connection errors to UI
        return DeployResult(False, f"NETCONF 下发失败: {exc}", tuple(details))

    return DeployResult(
        True,
        f"已通过 NETCONF 下发 {len(rpc_documents)} 条 RPC 到 {target.host}:{target.port}",
        tuple(details),
    )


def _deploy_cli(cli_content: str, target: DeviceTarget) -> DeployResult:
    try:
        import paramiko
    except ImportError:
        return DeployResult(
            False,
            "缺少 SSH 依赖，请执行: pip install paramiko",
        )

    lines = [line.strip() for line in cli_content.splitlines() if line.strip()]
    if not lines:
        return DeployResult(False, "没有可下发的 CLI 命令")

    _configure_legacy_ssh()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    channel = None
    details: list[str] = []

    try:
        client.connect(
            hostname=target.host,
            port=target.port,
            username=target.username,
            password=target.password,
            look_for_keys=False,
            allow_agent=False,
            timeout=30,
        )
        channel = client.invoke_shell(width=200, height=48)
        channel.settimeout(30)
        _read_until_prompt(channel, timeout=15)

        for index, line in enumerate(lines, start=1):
            channel.send(line + "\n")
            output = _read_until_prompt(channel, timeout=30)
            details.append(f"命令 {index}: {line}")
            if _looks_like_cli_error(output):
                return DeployResult(
                    False,
                    f"CLI 下发失败（第 {index} 条）: {line}",
                    tuple(details),
                )
    except Exception as exc:  # noqa: BLE001 - surface connection errors to UI
        return DeployResult(False, f"SSH 下发失败: {exc}", tuple(details))
    finally:
        if channel is not None:
            channel.close()
        client.close()

    return DeployResult(
        True,
        f"已通过 SSH 下发 {len(lines)} 条 CLI 到 {target.host}:{target.port}",
        tuple(details),
    )


def _read_until_prompt(channel, *, timeout: float) -> str:
    deadline = time.time() + timeout
    chunks: list[str] = []
    while time.time() < deadline:
        if channel.recv_ready():
            chunks.append(channel.recv(65535).decode("utf-8", errors="replace"))
            text = "".join(chunks)
            if _has_prompt(text):
                return text
        time.sleep(0.1)
    return "".join(chunks)


def _has_prompt(text: str) -> bool:
    stripped = text.rstrip()
    return bool(
        stripped.endswith(">") or stripped.endswith("#") or stripped.endswith("$")
    )


def _looks_like_cli_error(output: str) -> bool:
    lowered = output.lower()
    markers = (
        "error",
        "invalid",
        "unknown command",
        "syntax error",
        "failed",
        "failure",
    )
    return any(marker in lowered for marker in markers)
