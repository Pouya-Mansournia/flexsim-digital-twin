"""RmsOrchestrator: coordinates the full observe -> decide -> dispatch
flow across MissionManager, TaskManager, FleetManager, and
ResourceScheduler, against whatever adapter is handed to it.

This is the one place in rms/ that talks to an adapter, and it only
talks to the adapter through the two Protocols below (`RobotSource`,
already defined in rms/fleet/manager.py, plus `CommandSender` here) —
never to `adapters.flexsim` (or `adapters.ros2`, later) by name. That
keeps the dependency direction adapters -> rms, matching the "Adapters
protect the core" design principle in the root README: rms/ stays
usable in a unit test with a fake adapter, and swappable to a real ROS 2
fleet later without changing this file's imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from rms.domain import Mission, Robot, Task, Workstation
from rms.fleet import FleetManager
from rms.fleet.manager import RobotSource
from rms.missions import MissionManager
from rms.scheduler import ResourceScheduler
from rms.scheduler.resource_scheduler import NoCandidateRobotError
from rms.tasks import TaskManager
from rms.workstations import WorkstationManager
from rms.workstations.manager import WorkstationSource


class CommandSender(Protocol):
    """Anything that can dispatch a command and return its id, e.g.
    `adapters.flexsim.FlexSimAdapter.send_command`.
    """

    def send_command(
        self, target: str, command_type: str, parameters: dict[str, Any] | None = None
    ) -> str: ...


class IntegrationError(RuntimeError):
    """Raised when the orchestration flow can't complete: the adapter
    is unreachable, there's no fleet data, or no robot can be assigned.
    Deliberately a single exception type so callers (CLI demos, future
    API handlers) can catch one thing instead of every manager's own
    error type.
    """


@dataclass
class OrchestrationResult:
    """Everything a caller needs to report on one run_mission() call."""

    robots: list[Robot]
    mission: Mission
    task: Task
    selected_robot: Robot
    score: float
    used_fallback: bool
    command_id: str


class RmsOrchestrator:
    """Coordinates one adapter (a `RobotSource` + `CommandSender`) with
    an in-memory FleetManager/MissionManager/TaskManager/
    ResourceScheduler to run the full scheduling flow described in the
    root README: FlexSim -> bridge -> adapter -> FleetManager ->
    MissionManager -> TaskManager -> ResourceScheduler -> selected
    Robot -> adapter -> bridge command queue.
    """

    def __init__(
        self,
        adapter: RobotSource | CommandSender | WorkstationSource,
        fleet: FleetManager | None = None,
        workstations: WorkstationManager | None = None,
        task_manager: TaskManager | None = None,
        mission_manager: MissionManager | None = None,
        scheduler: ResourceScheduler | None = None,
    ) -> None:
        self.adapter = adapter
        self.fleet = fleet or FleetManager()
        self.workstations = workstations or WorkstationManager()
        self.task_manager = task_manager or TaskManager()
        self.mission_manager = mission_manager or MissionManager(self.task_manager)
        self.scheduler = scheduler or ResourceScheduler(workstation_manager=self.workstations)

    def sync_fleet(self) -> list[Robot]:
        """Refresh FleetManager from the adapter. Raises
        IntegrationError if the adapter can't be reached; that's the
        adapter's own error type wrapped, not re-raised directly, so
        callers only need to catch IntegrationError from this class.
        """
        try:
            return self.fleet.sync_from_source(self.adapter)  # type: ignore[arg-type]
        except Exception as exc:  # adapter-specific errors vary; we wrap them uniformly
            raise IntegrationError(f"could not sync fleet from adapter: {exc}") from exc

    def sync_workstations(self) -> list[Workstation]:
        """Refresh WorkstationManager from the adapter, feeding the
        scheduler's `queue_cost` term. Optional: if the adapter doesn't
        support `get_workstations()` (e.g. a test fake that only does
        robots), this raises IntegrationError and callers can simply
        not call it, leaving queue_cost at 0 for unknown destinations.
        """
        try:
            return self.workstations.sync_from_source(self.adapter)  # type: ignore[arg-type]
        except Exception as exc:  # adapter-specific errors vary; we wrap them uniformly
            raise IntegrationError(f"could not sync workstations from adapter: {exc}") from exc

    def run_mission(
        self,
        mission_type: str,
        source: str,
        destination: str,
        priority: int = 0,
    ) -> OrchestrationResult:
        """Create a mission, decompose it, pick the best known robot,
        and dispatch a command for it through the adapter.

        Requires sync_fleet() to have been called at least once (and to
        have found robots); this method doesn't sync on its own, so
        callers control exactly when a fresh read happens.
        """
        robots = self.fleet.list_all()
        if not robots:
            raise IntegrationError("no robots known; call sync_fleet() first")

        mission = self.mission_manager.create_mission(mission_type, source, destination, priority)
        task = self.task_manager.get_task(mission.task_ids[0])

        used_fallback = not self.fleet.list_available()
        try:
            chosen = self.scheduler.assign(task, robots)
        except NoCandidateRobotError as exc:
            raise IntegrationError(str(exc)) from exc
        score = self.scheduler.score(chosen, task)

        try:
            command_id = self.adapter.send_command(  # type: ignore[union-attr]
                chosen.robot_id, mission_type, {"destination": destination}
            )
        except Exception as exc:  # adapter-specific errors vary; we wrap them uniformly
            raise IntegrationError(f"could not send command via adapter: {exc}") from exc

        return OrchestrationResult(
            robots=robots,
            mission=mission,
            task=task,
            selected_robot=chosen,
            score=score,
            used_fallback=used_fallback,
            command_id=command_id,
        )
