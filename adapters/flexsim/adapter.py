"""FlexSim Adapter: talks to bridge/'s existing REST API.

Phase 3 first implementation. The endpoints it sits in front of already
exist and work today (bridge/app/api/telemetry.py,
bridge/app/api/real_environment.py, bridge/app/api/commands.py); this
adapter just translates between bridge/'s wire format and rms/domain's
Robot/Workstation types, and issues commands, so the Fleet Manager and
Resource Scheduler don't talk HTTP directly.

Uses only the standard library (urllib), matching the rest of rms/: no
extra dependency beyond pytest is needed to run rms/'s tests, even
though bridge/ itself uses httpx.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Literal

from rms.domain import Robot, RobotStatus, Workstation, WorkstationStatus

IDLE_STATE_NAMES = {"idle", "available", "waiting"}

# Both channels are served by bridge/ behind the same wire shape
# (has_data / telemetry.robots / telemetry.queues), just under different
# path prefixes and with a differently-named status field
# (model_status vs status). See channel= on __init__.
_STATE_PATH_BY_CHANNEL = {"flexsim": "/api/v1/state", "real": "/api/v1/real/state"}
_STATUS_FIELD_BY_CHANNEL = {"flexsim": "model_status", "real": "status"}
_RUNNING_STATUS_VALUES = {"running"}

Channel = Literal["flexsim", "real"]


class FlexSimAdapterError(RuntimeError):
    """Raised when the bridge can't be reached or returns unexpected data."""


class FlexSimAdapter:
    """Reads robot/queue state from the bridge and forwards RMS commands
    to it via POST /api/v1/commands.

    Reads from FlexSim's own telemetry channel by default (`channel=
    "flexsim"`, the model itself). Pass `channel="real"` to instead read
    the real/ROS2-side channel that `bridge/ros2_sim/simulator.py` (or a
    future real ROS2 node) posts to: useful for exercising the scheduler
    against continuously-changing telemetry without a real FlexSim model
    running, since the two channels are otherwise kept deliberately
    separate for the dashboard's FlexSim-vs-real comparison.
    """

    def __init__(
        self,
        bridge_url: str = "http://127.0.0.1:8000",
        timeout: float = 5.0,
        channel: Channel = "flexsim",
    ) -> None:
        if channel not in _STATE_PATH_BY_CHANNEL:
            raise ValueError(f"unknown channel: {channel!r} (expected 'flexsim' or 'real')")
        self.bridge_url = bridge_url.rstrip("/")
        self.timeout = timeout
        self.channel = channel
        self._state_path = _STATE_PATH_BY_CHANNEL[channel]
        self._status_field = _STATUS_FIELD_BY_CHANNEL[channel]

    def _get_json(self, path: str) -> dict[str, Any]:
        url = f"{self.bridge_url}{path}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                return json.loads(response.read())
        except (urllib.error.URLError, TimeoutError) as exc:
            raise FlexSimAdapterError(f"could not reach bridge at {url}: {exc}") from exc

    def _post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.bridge_url}{path}"
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except (urllib.error.URLError, TimeoutError) as exc:
            raise FlexSimAdapterError(f"could not reach bridge at {url}: {exc}") from exc

    def get_robots(self) -> list[Robot]:
        """Fetch the configured channel's state and map its robots into
        rms/domain Robot objects. Returns an empty list if that channel
        hasn't received telemetry yet (`has_data: false`).
        """
        state = self._get_json(self._state_path)
        if not state.get("has_data"):
            return []

        telemetry = state.get("telemetry") or {}
        robots = telemetry.get("robots", {})

        result: list[Robot] = []
        for robot_id, robot_data in robots.items():
            flex_state = str(robot_data.get("state", "")).lower()
            status = RobotStatus.AVAILABLE if flex_state in IDLE_STATE_NAMES else RobotStatus.BUSY
            result.append(
                Robot(
                    robot_id=robot_id,
                    status=status,
                    battery_pct=float(robot_data.get("battery", 100.0)),
                    x=float(robot_data.get("x", 0.0)),
                    y=float(robot_data.get("y", 0.0)),
                )
            )
        return result

    def get_workstations(self) -> list[Workstation]:
        """Fetch the configured channel's state and map its queues into
        rms/domain Workstation objects, one per named queue, so the
        Resource Scheduler has real backlog data to feed `queue_cost`.
        Neither FlexSim nor the mock fleet has a notion of a
        "workstation" as such; a queue is the closest analog either
        reports today. Returns an empty list if no telemetry has
        arrived yet.
        """
        state = self._get_json(self._state_path)
        if not state.get("has_data"):
            return []

        telemetry = state.get("telemetry") or {}
        queues = telemetry.get("queues", {})
        run_status = str(telemetry.get(self._status_field, "")).lower()
        status = (
            WorkstationStatus.READY if run_status in _RUNNING_STATUS_VALUES else WorkstationStatus.OFFLINE
        )

        return [
            Workstation(workstation_id=name, status=status, queue_length=int(count))
            for name, count in queues.items()
        ]

    def send_command(self, target: str, command_type: str, parameters: dict[str, Any] | None = None) -> str:
        """POST /api/v1/commands and return the command id for the RMS
        to track through /api/v1/commands/next and /{id}/ack. Shared by
        both channels: the command queue isn't itself channel-specific.
        """
        body = {"target": target, "command": command_type, "parameters": parameters or {}}
        response = self._post_json("/api/v1/commands", body)
        return response["command_id"]
