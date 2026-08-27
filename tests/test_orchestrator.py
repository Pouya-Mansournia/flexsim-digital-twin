"""Unit tests for RmsOrchestrator using a fake adapter: no network, no
bridge, no adapters/flexsim import needed for the orchestrator's own
logic (only the test's fake stands in for a RobotSource+CommandSender).
"""

from __future__ import annotations

import pytest

from rms.domain import Robot, RobotStatus, Workstation, WorkstationStatus
from rms.services import IntegrationError, RmsOrchestrator


class FakeAdapter:
    """Minimal stand-in for adapters.flexsim.FlexSimAdapter."""

    def __init__(
        self,
        robots: list[Robot],
        workstations: list[Workstation] | None = None,
        fail_get: bool = False,
        fail_send: bool = False,
    ) -> None:
        self._robots = robots
        self._workstations = workstations or []
        self.fail_get = fail_get
        self.fail_send = fail_send
        self.sent_commands: list[tuple[str, str, dict]] = []

    def get_robots(self) -> list[Robot]:
        if self.fail_get:
            raise ConnectionError("simulated bridge outage")
        return self._robots

    def get_workstations(self) -> list[Workstation]:
        if self.fail_get:
            raise ConnectionError("simulated bridge outage")
        return self._workstations

    def send_command(self, target: str, command_type: str, parameters=None) -> str:
        if self.fail_send:
            raise ConnectionError("simulated send failure")
        self.sent_commands.append((target, command_type, parameters or {}))
        return f"cmd-{len(self.sent_commands)}"


def test_sync_fleet_raises_integration_error_when_adapter_unreachable():
    orchestrator = RmsOrchestrator(FakeAdapter([], fail_get=True))
    with pytest.raises(IntegrationError):
        orchestrator.sync_fleet()


def test_run_mission_requires_sync_fleet_first():
    orchestrator = RmsOrchestrator(FakeAdapter([]))
    with pytest.raises(IntegrationError, match="call sync_fleet"):
        orchestrator.run_mission("move_tote", "Inbound", "Workstation-03")


def test_run_mission_picks_nearest_available_and_dispatches():
    robots = [
        Robot(robot_id="AGV1", status=RobotStatus.AVAILABLE, battery_pct=84.0, x=1.0, y=0.0),
        Robot(robot_id="AGV2", status=RobotStatus.BUSY, battery_pct=71.0, x=0.0, y=0.0),
        Robot(robot_id="AGV3", status=RobotStatus.AVAILABLE, battery_pct=42.0, x=20.0, y=0.0),
    ]
    adapter = FakeAdapter(robots)
    orchestrator = RmsOrchestrator(adapter)
    orchestrator.sync_fleet()

    result = orchestrator.run_mission("move_tote", "inbound", "workstation_03", priority=5)

    assert result.selected_robot.robot_id == "AGV1"
    assert result.used_fallback is False
    assert result.command_id == "cmd-1"
    assert adapter.sent_commands == [("AGV1", "move_tote", {"destination": "workstation_03"})]


def test_run_mission_falls_back_and_flags_it_when_no_robot_available():
    robots = [Robot(robot_id="AGV1", status=RobotStatus.BUSY, x=0.0, y=0.0)]
    orchestrator = RmsOrchestrator(FakeAdapter(robots))
    orchestrator.sync_fleet()

    result = orchestrator.run_mission("move_tote", "inbound", "workstation_03")

    assert result.selected_robot.robot_id == "AGV1"
    assert result.used_fallback is True


def test_run_mission_wraps_send_command_failure_as_integration_error():
    robots = [Robot(robot_id="AGV1", status=RobotStatus.AVAILABLE)]
    adapter = FakeAdapter(robots, fail_send=True)
    orchestrator = RmsOrchestrator(adapter)
    orchestrator.sync_fleet()

    with pytest.raises(IntegrationError):
        orchestrator.run_mission("move_tote", "inbound", "workstation_03")


def test_sync_workstations_feeds_queue_cost_into_scheduling():
    # Two otherwise-identical robots; only the destination's queue
    # backlog should be able to break the tie between them.
    robots = [
        Robot(robot_id="AGV1", status=RobotStatus.AVAILABLE),
        Robot(robot_id="AGV2", status=RobotStatus.AVAILABLE),
    ]
    workstations = [
        Workstation(workstation_id="Queue1", status=WorkstationStatus.READY, queue_length=20)
    ]
    orchestrator = RmsOrchestrator(FakeAdapter(robots, workstations))
    orchestrator.sync_fleet()
    orchestrator.sync_workstations()

    result = orchestrator.run_mission("move_tote", "inbound", "Queue1")

    assert result.selected_robot.robot_id in {"AGV1", "AGV2"}
    # queue_cost is the same for both robots (same destination), so this
    # mainly proves the sync path runs end to end without error and the
    # scheduler had a workstation_manager wired to it from construction.
    breakdown = orchestrator.scheduler.breakdown(result.selected_robot, result.task)
    assert breakdown.queue_cost == 20.0


def test_run_mission_refuses_a_blocked_destination():
    robots = [Robot(robot_id="AGV1", status=RobotStatus.AVAILABLE)]
    workstations = [
        Workstation(workstation_id="Queue1", status=WorkstationStatus.BLOCKED, queue_length=99)
    ]
    orchestrator = RmsOrchestrator(FakeAdapter(robots, workstations))
    orchestrator.sync_fleet()
    orchestrator.sync_workstations()

    with pytest.raises(IntegrationError, match="Queue1"):
        orchestrator.run_mission("move_tote", "inbound", "Queue1")

    # No command should have been sent for a mission that never scheduled.
    assert orchestrator.adapter.sent_commands == []
