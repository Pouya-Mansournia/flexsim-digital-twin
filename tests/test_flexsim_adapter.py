import io
import json
from unittest.mock import patch

import pytest

from adapters.flexsim import FlexSimAdapter
from adapters.flexsim.adapter import FlexSimAdapterError
from rms.domain import RobotStatus, WorkstationStatus


def fake_response(payload: dict) -> io.BytesIO:
    response = io.BytesIO(json.dumps(payload).encode("utf-8"))
    response.__enter__ = lambda self=response: response  # type: ignore[method-assign]
    response.__exit__ = lambda *a, **k: False  # type: ignore[method-assign]
    return response


def test_get_robots_returns_empty_list_when_no_telemetry_yet():
    adapter = FlexSimAdapter()
    with patch("urllib.request.urlopen", return_value=fake_response({"has_data": False})):
        assert adapter.get_robots() == []


def test_get_robots_maps_telemetry_into_domain_robots():
    adapter = FlexSimAdapter()
    payload = {
        "has_data": True,
        "telemetry": {
            "robots": {
                "TaskExecuter3": {"x": 1.0, "y": 2.0, "speed": 0.0, "state": "idle", "battery": 88.0},
                "TaskExecuter4": {"x": 5.0, "y": 6.0, "speed": 1.5, "state": "moving", "battery": 40.0},
            }
        },
    }
    with patch("urllib.request.urlopen", return_value=fake_response(payload)):
        robots = {r.robot_id: r for r in adapter.get_robots()}

    assert robots["TaskExecuter3"].status == RobotStatus.AVAILABLE
    assert robots["TaskExecuter3"].battery_pct == 88.0
    assert robots["TaskExecuter4"].status == RobotStatus.BUSY
    assert robots["TaskExecuter4"].x == 5.0


def test_get_robots_raises_adapter_error_on_connection_failure():
    import urllib.error

    adapter = FlexSimAdapter()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        with pytest.raises(FlexSimAdapterError):
            adapter.get_robots()


def test_get_workstations_maps_queues_when_model_running():
    adapter = FlexSimAdapter()
    payload = {
        "has_data": True,
        "telemetry": {
            "model_status": "running",
            "queues": {"Queue1": 12, "Queue2": 0},
        },
    }
    with patch("urllib.request.urlopen", return_value=fake_response(payload)):
        workstations = {w.workstation_id: w for w in adapter.get_workstations()}

    assert workstations["Queue1"].queue_length == 12
    assert workstations["Queue1"].status == WorkstationStatus.READY
    assert workstations["Queue2"].queue_length == 0


def test_get_workstations_marks_offline_when_model_not_running():
    adapter = FlexSimAdapter()
    payload = {
        "has_data": True,
        "telemetry": {"model_status": "stopped", "queues": {"Queue1": 3}},
    }
    with patch("urllib.request.urlopen", return_value=fake_response(payload)):
        workstations = adapter.get_workstations()

    assert workstations[0].status == WorkstationStatus.OFFLINE


def test_get_workstations_returns_empty_list_when_no_telemetry_yet():
    adapter = FlexSimAdapter()
    with patch("urllib.request.urlopen", return_value=fake_response({"has_data": False})):
        assert adapter.get_workstations() == []


def test_send_command_returns_command_id():
    adapter = FlexSimAdapter()
    response = {"command_id": "cmd-123", "status": "pending"}
    with patch("urllib.request.urlopen", return_value=fake_response(response)):
        command_id = adapter.send_command("TaskExecuter3", "move_to", {"x": 10, "y": 5})

    assert command_id == "cmd-123"
