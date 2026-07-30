"""API tests for xml2cli web server."""

from fastapi.testclient import TestClient

from xml2cli.api import create_app


def test_profiles_endpoint():
    client = TestClient(create_app())
    response = client.get("/api/profiles")
    assert response.status_code == 200
    data = response.json()
    assert "831-ihub" in data["profiles"]


def test_xml2cli_endpoint():
    client = TestClient(create_app())
    xml = """<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
  <commit />
</rpc>"""
    response = client.post("/api/xml2cli", json={"content": xml})
    assert response.status_code == 200
    data = response.json()
    assert data["cli"] == ["commit"]
    assert data["profile"] == "831-ihub"


def test_cli2xml_endpoint():
    client = TestClient(create_app())
    response = client.post(
        "/api/cli2xml",
        json={
            "content": "configure service vpls 4093 sap 1/1/c1/1:0 admin-state enable",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "<rpc" in data["xml"]
    assert data["errors"] == []
    assert data["profile"] == "831-ihub"
