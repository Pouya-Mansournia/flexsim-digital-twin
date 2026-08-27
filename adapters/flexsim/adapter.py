"""FlexSim Adapter: talks to bridge/'s existing REST API.

Phase 3 first implementation. The endpoints it sits in front of already
exist and work today (bridge/app/api/telemetry.py,
bridge/app/api/commands.py); this adapter just translates between
bridge/'s wire format and rms/domain's Robot type, and issues commands,
so the Fleet Manager and Resource Scheduler don't talk HTTP directly.

Uses only the standard library (urllib), matching the rest of rms/: no
extra dependency beyond pytest is needed to run rms/'s tests, even
though bridge/ itself uses httpx.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from rms.domain import Robot, RobotStatus, Workstation, WorkstationStatus

IDLE_STATE_NAMES = {"idle", "available", "waiting"}


class FlexSimAdapterError(RuntimeError):
    """Raised when the bridge can't be reached or returns unexpected data."""


class FlexSimAdapter:
    """Reads FlexSim state from the bridge and forwards RMS commands to
    it via POST /api/v1/commands.
    """

    def __init__(self, bridge_url: str = "http://127.0.0.1:8000", timeout: float = 5.0) -> None:
        self.bridge_url = bridge_url.rstrip("/")
        self.timeout = timeout

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
        """Fetch GET /api/v1/state and map its robots into rms/domain
        Robot objects. Returns an empty list if FlexSim hasn't sent
        telemetry yet (`has_data: false`).
        """
        state = self._get_json("/api/v1/state")
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
        """Fetch GET /api/v1/state and map FlexSim's queues into
        rms/domain Workstation objects, one per named queue, so the
        Resource Scheduler has real backlog data to feed `queue_cost`.
        FlexSim has no notion of a "workstation" as such; a queue is
        the closest analog it reports today. Returns an empty list if
        no telemetry has arrived yet.
        """
        state = self._get_json("/api/v1/state")
        if not state.get("has_data"):
            return []

        telemetry = state.get("telemetry") or {}
        queues = telemetry.get("queues", {})
        model_status = str(telemetry.get("model_status", "")).lower()
        status = WorkstationStatus.READY if model_status == "running" else WorkstationStatus.OFFLINE

        return [
            Workstation(workstation_id=name, status=status, queue_length=int(count))
            for name, count in queues.items()
        ]

    def send_command(self, target: str, command_type: str, parameters: dict[str, Any] | None = None) -> str:
        """POST /api/v1/commands and return the command id for the RMS
        to track through /api/v1/commands/next and /{id}/ack.
        """
        body = {"target": target, "command": command_type, "parameters": parameters or {}}
        response = self._post_json("/api/v1/commands", body)
        return response["command_id"]
