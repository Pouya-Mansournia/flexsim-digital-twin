from fastapi.testclient import TestClient

from app.main import app
from app.services.rms_decision_store import rms_decision_store

client = TestClient(app)


def setup_function() -> None:
    rms_decision_store.reset()


def make_decision_payload(**overrides) -> dict:
    payload = {
        "mission_type": "move_tote",
        "source": "inbound",
        "destination": "Queue1",
        "priority": 5,
        "selected_robot": "AGV1",
        "score": 19.16,
        "travel_cost": 1.0,
        "battery_penalty": 0.16,
        "queue_cost": 22.0,
        "utilization_cost": 1.0,
        "priority_penalty": -5.0,
        "used_fallback": False,
        "command_id": "cmd-123",
    }
    payload.update(overrides)
    return payload


def test_get_decision_before_any_posted():
    response = client.get("/api/v1/rms/decision")
    assert response.status_code == 200
    assert response.json() == {"has_data": False, "decision": None}


def test_post_decision_then_get_returns_it():
    response = client.post("/api/v1/rms/decision", json=make_decision_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["has_data"] is True
    assert body["decision"]["selected_robot"] == "AGV1"
    assert body["decision"]["queue_cost"] == 22.0
    assert "received_at" in body["decision"]

    assert client.get("/api/v1/rms/decision").json()["decision"]["command_id"] == "cmd-123"


def test_post_decision_replaces_the_previous_one():
    client.post("/api/v1/rms/decision", json=make_decision_payload(selected_robot="AGV1"))
    client.post("/api/v1/rms/decision", json=make_decision_payload(selected_robot="AGV2"))

    assert client.get("/api/v1/rms/decision").json()["decision"]["selected_robot"] == "AGV2"


def test_reset_clears_the_decision():
    client.post("/api/v1/rms/decision", json=make_decision_payload())
    client.post("/api/v1/rms/decision/reset")

    assert client.get("/api/v1/rms/decision").json() == {"has_data": False, "decision": None}


def test_post_decision_rejects_missing_field():
    payload = make_decision_payload()
    del payload["selected_robot"]

    response = client.post("/api/v1/rms/decision", json=payload)
    assert response.status_code == 422
