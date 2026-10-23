"""MCP transport security: /mcp answers only requests addressed to this service (DNS-rebinding protection)."""

from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import offline_settings

PROTOCOL = "2026-07-28"


def discover(client: TestClient, **headers: str):
    meta = {
        "io.modelcontextprotocol/protocolVersion": PROTOCOL,
        "io.modelcontextprotocol/clientInfo": {"name": "test", "version": "1"},
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    return client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": meta}},
        headers={
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL,
            "Mcp-Method": "server/discover",
            **headers,
        },
    )


def test_local_requests_are_served(client):
    assert discover(client).status_code == 200
    assert discover(client, Host="127.0.0.1:8000").status_code == 200


def test_foreign_host_is_rejected(client):
    assert discover(client, Host="attacker.example").status_code == 421


def test_foreign_origin_is_rejected(client):
    assert discover(client, Origin="http://attacker.example").status_code == 403


def test_public_hostname_is_served():
    public = "ca-test.example.eastus2.azurecontainerapps.io"
    with TestClient(create_app(offline_settings(public_hostname=public))) as c:
        assert discover(c, Host=public).status_code == 200
