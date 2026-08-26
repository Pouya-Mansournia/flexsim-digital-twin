from fastapi.testclient import TestClient

from app.main import app
from app.services.command_store import command_store

client = TestClient(app)


def setup_function() -> None:
    command_store.__init__()


def test_create_command_returns_pending_status():
    response = client.post(
        "/api/v1/commands",
        json={"target": "AGV1", "command": "stop", "parameters": {}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert "command_id" in body


def test_next_command_returns_oldest_pending():
    first = client.post(
        "/api/v1/commands", json={"target": "AGV1", "command": "stop", "parameters": {}}
    ).json()
    client.post(
        "/api/v1/commands",
        json={"target": "Processor1", "command": "set_processing_time", "parameters": {"value": 12.5}},
    )

    response = client.get("/api/v1/commands/next")
    assert response.status_code == 200
    body = response.json()
    assert body["command"]["command_id"] == first["command_id"]
    assert body["command"]["status"] == "pending"


def test_empty_command_queue_returns_null_command():
    response = client.get("/api/v1/commands/next")
    assert response.status_code == 200
    assert response.json() == {"command": None}


def test_command_acknowledgment_updates_status():
    created = client.post(
        "/api/v1/commands", json={"target": "AGV1", "command": "stop", "parameters": {}}
    ).json()
    command_id = created["command_id"]

    response = client.post(
        f"/api/v1/commands/{command_id}/ack",
        json={"status": "executed", "message": "Command applied successfully"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["command_id"] == command_id
    assert body["status"] == "executed"

    next_response = client.get("/api/v1/commands/next")
    assert next_response.json() == {"command": None}


def test_ack_unknown_command_returns_404():
    response = client.post(
        "/api/v1/commands/does-not-exist/ack",
        json={"status": "failed", "message": "not found"},
    )
    assert response.status_code == 404
