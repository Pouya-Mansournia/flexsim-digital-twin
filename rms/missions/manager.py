"""Mission Manager interface.

Scaffolding only (Phase 3, not implemented). See rms/README.md.
"""

from __future__ import annotations

from rms.domain import Mission


class MissionManager:
    """Converts external requests (e.g. from a WMS) into Missions and
    hands accepted ones to the Task Manager for decomposition.
    """

    def create_mission(
        self,
        mission_type: str,
        source: str,
        destination: str,
        priority: int = 0,
    ) -> Mission:
        """Validate an external request and register a new Mission."""
        raise NotImplementedError

    def get_mission(self, mission_id: str) -> Mission:
        """Look up a Mission by id."""
        raise NotImplementedError

    def cancel_mission(self, mission_id: str) -> None:
        """Cancel a Mission and any of its tasks that haven't started."""
        raise NotImplementedError
