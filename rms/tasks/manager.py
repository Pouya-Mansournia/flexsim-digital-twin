"""Task Manager interface.

Scaffolding only (Phase 3, not implemented). See rms/README.md.
"""

from __future__ import annotations

from rms.domain import Mission, Task


class TaskManager:
    """Breaks a Mission into one or more executable Tasks and tracks
    each task's lifecycle (pending -> scheduled -> dispatched ->
    in_progress -> completed/failed).
    """

    def decompose(self, mission: Mission) -> list[Task]:
        """Split a Mission into the Tasks needed to fulfil it."""
        raise NotImplementedError

    def get_task(self, task_id: str) -> Task:
        """Look up a Task by id."""
        raise NotImplementedError

    def mark_completed(self, task_id: str) -> None:
        """Record that a Task finished successfully."""
        raise NotImplementedError

    def mark_failed(self, task_id: str, reason: str) -> None:
        """Record that a Task failed, with a reason for diagnosis."""
        raise NotImplementedError
