"""Task Manager: mission decomposition and task lifecycle tracking.

Phase 3 first implementation. `decompose` currently produces exactly one
Task per Mission (a single move from source to destination); splitting a
Mission into multiple Tasks (e.g. pick-then-drop as separate tasks) is
future work once the Resource Scheduler needs that granularity.
"""

from __future__ import annotations

from rms.domain import Mission, Task, TaskStatus


class TaskManager:
    """Breaks a Mission into one or more executable Tasks and tracks
    each task's lifecycle (pending -> scheduled -> dispatched ->
    in_progress -> completed/failed).
    """

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._counter = 0

    def decompose(self, mission: Mission) -> list[Task]:
        """Split a Mission into the Tasks needed to fulfil it."""
        self._counter += 1
        task = Task(
            task_id=f"{mission.mission_id}-task{self._counter}",
            mission_id=mission.mission_id,
            action=mission.mission_type,
            location=mission.destination,
            priority=mission.priority,
        )
        self._tasks[task.task_id] = task
        mission.task_ids.append(task.task_id)
        return [task]

    def get_task(self, task_id: str) -> Task:
        """Look up a Task by id."""
        try:
            return self._tasks[task_id]
        except KeyError:
            raise KeyError(f"unknown task_id: {task_id}") from None

    def mark_completed(self, task_id: str) -> None:
        """Record that a Task finished successfully."""
        self.get_task(task_id).status = TaskStatus.COMPLETED

    def mark_failed(self, task_id: str, reason: str) -> None:
        """Record that a Task failed, with a reason for diagnosis."""
        task = self.get_task(task_id)
        task.status = TaskStatus.FAILED
        task.failure_reason = reason
