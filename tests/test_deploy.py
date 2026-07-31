"""Tests for configuration deployment."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from xml2cli.api import create_app
from xml2cli.deploy import (
    DeviceTarget,
    deploy_to_device,
    prepare_deploy_payload,
    split_rpc_documents,
)


COMMIT_XML = """<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
  <commit />
</rpc>"""

MULTI_RPC_XML = COMMIT_XML + "\n\n" + COMMIT_XML


def test_split_rpc_documents_single():
    documents = split_rpc_documents(COMMIT_XML)
    assert len(documents) == 1
    assert documents[0].startswith("<rpc")


def test_split_rpc_documents_multiple():
    documents = split_rpc_documents(MULTI_RPC_XML)
    assert len(documents) == 2


def test_prepare_deploy_payload_cli_to_netconf():
    _, payload = prepare_deploy_payload(
        "commit",
        content_format="cli",
        transport="netconf",
        board="IHUB-LMNT-A",
    )
    assert "<commit" in payload


def test_prepare_deploy_payload_xml_to_cli():
    _, payload = prepare_deploy_payload(
        COMMIT_XML,
        content_format="xml",
        transport="cli",
        board="IHUB-LMNT-A",
    )
    assert payload.strip() == "commit"


def test_prepare_deploy_payload_requires_board_for_cross_format():
    with pytest.raises(ValueError, match="板卡"):
        prepare_deploy_payload(
            "commit",
            content_format="cli",
            transport="netconf",
            board=None,
        )


@patch("ncclient.manager.connect")
def test_deploy_netconf_success(mock_connect):
    session = MagicMock()
    session.dispatch.return_value = "<ok/>"
    mock_connect.return_value.__enter__.return_value = session

    result = deploy_to_device(
        COMMIT_XML,
        content_format="xml",
        target=DeviceTarget(
            host="10.0.0.1",
            port=830,
            username="admin",
            password="secret",
            transport="netconf",
        ),
    )

    assert result.success is True
    assert "NETCONF" in result.message
    session.dispatch.assert_called_once()


@patch("paramiko.SSHClient")
def test_deploy_cli_success(mock_ssh_client):
    pytest.importorskip("paramiko")
    client = MagicMock()
    channel = MagicMock()
    channel.recv_ready.side_effect = [False, True, False, True]
    channel.recv.side_effect = [
        b"Welcome\n# ",
        b"OK\n# ",
    ]
    client.invoke_shell.return_value = channel
    mock_ssh_client.return_value = client

    result = deploy_to_device(
        "show version",
        content_format="cli",
        target=DeviceTarget(
            host="10.0.0.1",
            port=22,
            username="admin",
            password="secret",
            transport="cli",
        ),
    )

    assert result.success is True
    assert "SSH" in result.message


def test_deploy_api_endpoint():
    client = TestClient(create_app())
    with patch("xml2cli.api.deploy_to_device") as mock_deploy:
        mock_deploy.return_value = MagicMock(
            success=True,
            message="ok",
            details=("RPC 1: ok",),
        )
        response = client.post(
            "/api/deploy",
            json={
                "content": COMMIT_XML,
                "content_format": "xml",
                "host": "10.0.0.1",
                "port": 830,
                "username": "admin",
                "password": "secret",
                "transport": "netconf",
                "board": "IHUB-LMNT-A",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "ok"
    mock_deploy.assert_called_once()
