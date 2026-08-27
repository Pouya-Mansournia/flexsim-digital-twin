"""Workstation Manager: an in-memory registry of workstation state.

Phase 3 first implementation, same pattern as rms/fleet/manager.py:
`sync_from_source` refreshes state from anything exposing
`get_workstations()` (today, `adapters/flexsim/` mapping FlexSim's
queues; later, `adapters/plc/`) without this module importing
`adapters/` directly.
"""

from __future__ import annotations

from typing import Protocol

from rms.domain import Workstation, WorkstationStatus


class WorkstationSource(Protocol):
    """Anything that can report a list of current Workstation states,
    e.g. `adapters.flexsim.FlexSimAdapter.get_workstations`.
    """

    def get_workstations(self) -> list[Workstation]: ...


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

    def sync_from_source(self, source: WorkstationSource) -> list[Workstation]:
        """Refresh workstation state from an adapter's
        `get_workstations()` and return what was synced.
        """
        workstations = source.get_workstations()
        for workstation in workstations:
            self.register(workstation)
        return workstations

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
