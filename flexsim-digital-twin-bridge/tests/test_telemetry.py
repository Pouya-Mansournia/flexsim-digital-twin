from fastapi.testclient import TestClient

from app.main import app
from app.services.state_store import state_store

client = TestClient(app)


VALID_TELEMETRY = {
    "simulation_time": 120.5,
    "model_status": "running",
    "queues": {"Queue1": 8, "Queue2": 3},
    "processors": {"Processor1": {"state": "processing", "utilization": 0.82}},
    "robots": {
        "AGV1": {"x": 10.2, "y": 4.1, "speed": 1.2, "state": "moving", "battery": 87}
    },
}


def setup_function() -> None:
    state_store.__init__()


def test_post_telemetry_accepts_valid_payload():
    response = client.post("/api/v1/telemetry", json=VALID_TELEMETRY)
    assert response.status_code == 200
    assert response.json() == {"accepted": True}


def test_state_returns_latest_telemetry():
    client.post("/api/v1/telemetry", json=VALID_TELEMETRY)
    response = client.get("/api/v1/state")
    assert response.status_code == 200
    body = response.json()
    assert body["has_data"] is True
    assert body["telemetry"]["simulation_time"] == 120.5
    assert body["telemetry"]["robots"]["AGV1"]["battery"] == 87


def test_state_without_telemetry_returns_structured_response():
    state_store.__init__()
    response = client.get("/api/v1/state")
    assert response.status_code == 200
    body = response.json()
    assert body["has_data"] is False
    assert body["telemetry"] is None


def test_invalid_telemetry_is_rejected():
    invalid_payload = {"simulation_time": "not-a-number", "model_status": "running"}
    response = client.post("/api/v1/telemetry", json=invalid_payload)
    assert response.status_code == 422


def test_reset_clears_state():
    client.post("/api/v1/telemetry", json=VALID_TELEMETRY)
    assert client.get("/api/v1/state").json()["has_data"] is True

    response = client.post("/api/v1/state/reset")
    assert response.status_code == 200
    assert response.json()["has_data"] is False

    assert client.get("/api/v1/state").json()["has_data"] is False


def test_invalid_processor_utilization_is_rejected():
    payload = dict(VALID_TELEMETRY)
    payload["processors"] = {"Processor1": {"state": "processing", "utilization": 5.0}}
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422
