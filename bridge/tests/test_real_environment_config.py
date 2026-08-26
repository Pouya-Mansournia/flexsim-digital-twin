from fastapi.testclient import TestClient

from app.main import app
from app.services.real_environment_config_store import real_environment_config_store

client = TestClient(app)


def setup_function() -> None:
    real_environment_config_store.__init__()


def test_get_config_returns_default():
    response = client.get("/api/v1/real/config")
    assert response.status_code == 200
    assert response.json() == {"robot_count": 2}


def test_set_config_updates_robot_count():
    response = client.post("/api/v1/real/config", json={"robot_count": 5})
    assert response.status_code == 200
    assert response.json() == {"robot_count": 5}

    assert client.get("/api/v1/real/config").json() == {"robot_count": 5}


def test_set_config_rejects_out_of_range_count():
    response = client.post("/api/v1/real/config", json={"robot_count": 999})
    assert response.status_code == 422
