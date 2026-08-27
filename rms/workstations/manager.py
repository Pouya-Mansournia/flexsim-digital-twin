"""Workstation Manager: an in-memory registry of workstation state.

Phase 3 first implementation, same pattern as rms/fleet/manager.py: a
deterministic in-memory store today, replaceable later by an
`adapters/plc/`-backed version without changing the interface.
"""

from __future__ import annotations

from rms.domain import Workstation, WorkstationStatus


class WorkstationManager:
    """Tracks workstation availability, queue depth, and readiness, so
    the Resource Scheduler doesn't dispatch a robot to a station that
    can't accept the load.
    """

    def __init__(self) -> None:
        self._workstations: dict[str, Workstation] = {}

    def register(self, workstation: Workstation) -> None:
        """Add or replace a workstation's record."""
        self._workstations[workstation.workstation_id] = workstation

    def get_workstation(self, workstation_id: str) -> Workstation:
        """Look up a workstation's current state."""
        try:
            return self._workstations[workstation_id]
        except KeyError:
            raise KeyError(f"unknown workstation_id: {workstation_id}") from None

    def list_ready(self) -> list[Workstation]:
        """List workstations currently able to accept new work."""
        return [
            w for w in self._workstations.values() if w.status == WorkstationStatus.READY
        ]

    def update_state(
        self,
        workstation_id: str,
        status: WorkstationStatus | None = None,
        queue_length: int | None = None,
    ) -> None:
        """Apply an incoming state update for one workstation."""
        workstation = self.get_workstation(workstation_id)
        if status is not None:
            workstation.status = status
        if queue_length is not None:
            workstation.queue_length = queue_length
