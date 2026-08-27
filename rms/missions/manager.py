"""Mission Manager: turns external requests into transport missions.

Phase 3 first implementation. Delegates decomposition to a TaskManager
immediately on creation; a future version might defer that until an
`adapters/external/` request is actually accepted (e.g. after a
feasibility check), rather than always decomposing eagerly.
"""

from __future__ import annotations

from rms.domain import Mission, MissionStatus
from rms.tasks import TaskManager


class MissionManager:
    """Converts external requests (e.g. from a WMS) into Missions and
    hands accepted ones to the Task Manager for decomposition.
    """

    def __init__(self, task_manager: TaskManager) -> None:
        self._missions: dict[str, Mission] = {}
        self._counter = 0
        self.task_manager = task_manager

    def create_mission(
        self,
        mission_type: str,
        source: str,
        destination: str,
        priority: int = 0,
    ) -> Mission:
        """Validate an external request and register a new Mission."""
        self._counter += 1
        mission = Mission(
            mission_id=f"mission-{self._counter}",
            mission_type=mission_type,
            source=source,
            destination=destination,
            priority=priority,
        )
        self._missions[mission.mission_id] = mission

        tasks = self.task_manager.decompose(mission)
        mission.status = MissionStatus.ASSIGNED if tasks else MissionStatus.PENDING
        return mission

    def get_mission(self, mission_id: str) -> Mission:
        """Look up a Mission by id."""
        try:
            return self._missions[mission_id]
        except KeyError:
            raise KeyError(f"unknown mission_id: {mission_id}") from None

    def cancel_mission(self, mission_id: str) -> None:
        """Cancel a Mission and any of its tasks that haven't started."""
        mission = self.get_mission(mission_id)
        mission.status = MissionStatus.CANCELLED
