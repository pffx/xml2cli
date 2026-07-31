"""API tests for xml2cli web server."""

from fastapi.testclient import TestClient

from xml2cli.api import create_app


def test_boards_endpoint():
    client = TestClient(create_app())
    response = client.get("/api/boards")
    assert response.status_code == 200
    data = response.json()
    board_ids = {board["id"] for board in data["boards"]}
    assert "LWLT-C" in board_ids
    assert "IHUB-LMNT-A" in board_ids
    assert "NT-LMNT-A" in board_ids


def test_profiles_endpoint_alias():
    client = TestClient(create_app())
    response = client.get("/api/profiles")
    assert response.status_code == 200
    assert "boards" in response.json()


def test_xml2cli_endpoint():
    client = TestClient(create_app())
    xml = """<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
  <commit />
</rpc>"""
    response = client.post("/api/xml2cli", json={"content": xml})
    assert response.status_code == 200
    data = response.json()
    assert data["cli"] == ["commit"]
    assert data["board"] == "IHUB-LMNT-A"


def test_cli2xml_endpoint():
    client = TestClient(create_app())
    response = client.post(
        "/api/cli2xml",
        json={
            "content": "configure card 1 admin-state enable",
            "board": "IHUB-LMNT-A",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "<rpc" in data["xml"]
    assert data["errors"] == []
    assert data["board"] == "IHUB-LMNT-A"
