"""Workstation Manager interface.

Scaffolding only (Phase 3/6, not implemented). See rms/README.md.
"""

from __future__ import annotations

from rms.domain import Workstation, WorkstationStatus


class WorkstationManager:
    """Tracks workstation availability, queue depth, and readiness, so
    the Resource Scheduler doesn't dispatch a robot to a station that
    can't accept the load.
    """

    def get_workstation(self, workstation_id: str) -> Workstation:
        """Look up a workstation's current state."""
        raise NotImplementedError

    def list_ready(self) -> list[Workstation]:
        """List workstations currently able to accept new work."""
        raise NotImplementedError

    def update_state(
        self,
        workstation_id: str,
        status: WorkstationStatus | None = None,
        queue_length: int | None = None,
    ) -> None:
        """Apply an incoming state update for one workstation."""
        raise NotImplementedError
