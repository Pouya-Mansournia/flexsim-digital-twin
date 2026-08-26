from fastapi.testclient import TestClient

from app.main import app
from app.services.real_environment_store import real_environment_store

client = TestClient(app)


def setup_function() -> None:
    real_environment_store.__init__()


def test_post_real_telemetry_accepts_valid_payload():
    response = client.post(
        "/api/v1/real/telemetry",
        json={"simulation_time": 12.0, "status": "running", "queues": {"Queue1": 5, "Queue3": 2}},
    )
    assert response.status_code == 200
    assert response.json() == {"accepted": True}


def test_real_state_returns_latest_telemetry():
    client.post(
        "/api/v1/real/telemetry",
        json={"simulation_time": 12.0, "status": "running", "queues": {"Queue1": 5}},
    )
    response = client.get("/api/v1/real/state")
    assert response.status_code == 200
    body = response.json()
    assert body["has_data"] is True
    assert body["telemetry"]["queues"]["Queue1"] == 5


def test_real_state_without_telemetry_returns_structured_response():
    response = client.get("/api/v1/real/state")
    assert response.status_code == 200
    body = response.json()
    assert body["has_data"] is False
    assert body["telemetry"] is None


def test_real_state_reset_clears_state():
    client.post(
        "/api/v1/real/telemetry",
        json={"simulation_time": 1.0, "status": "running", "queues": {}},
    )
    assert client.get("/api/v1/real/state").json()["has_data"] is True

    response = client.post("/api/v1/real/state/reset")
    assert response.status_code == 200
    assert response.json()["has_data"] is False
