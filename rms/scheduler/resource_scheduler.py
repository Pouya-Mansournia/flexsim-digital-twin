"""Resource Scheduler: assigns tasks to robots.

Phase 3 implementation: a deterministic nearest-available policy,
weighted by battery, destination queue backlog, per-robot assignment
load, and task priority, matching the scoring formula in the root
README's "Vision: toward a Robot Management System (RMS)" section:

    score = w_travel * travel_cost + w_battery * battery_penalty
          + w_queue * queue_cost + w_utilization * utilization_cost
          + w_priority * priority_penalty

`queue_cost` comes from a `WorkstationManager` lookup on the task's
destination (0 if that destination isn't a known workstation, e.g. not
yet synced). `utilization_cost` is this scheduler's own running count of
how many tasks it has assigned to each robot so far, a simple
load-balancing signal: a robot that's already been assigned several
tasks scores worse than an equally-close, equally-charged robot that
hasn't, all else equal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from rms.domain import Robot, RobotStatus, Task
from rms.workstations.manager import WorkstationManager


@dataclass
class ScoreWeights:
    """Weights for the candidate-scoring formula: lower score wins."""

    travel: float = 1.0
    battery: float = 1.0
    queue: float = 1.0
    utilization: float = 1.0
    priority: float = 1.0


@dataclass
class ScoreBreakdown:
    """The individual terms behind one score(), for logging/debugging."""

    travel_cost: float
    battery_penalty: float
    queue_cost: float
    utilization_cost: float
    priority_penalty: float
    total: float


class NoCandidateRobotError(RuntimeError):
    """Raised when a task has no candidate robots to choose from."""


class ResourceScheduler:
    """Chooses the best robot for a task using a weighted score."""

    def __init__(
        self,
        weights: ScoreWeights | None = None,
        workstation_manager: WorkstationManager | None = None,
    ) -> None:
        self.weights = weights or ScoreWeights()
        self.workstation_manager = workstation_manager
        self._assignment_counts: dict[str, int] = {}

    def _queue_cost(self, task: Task) -> float:
        if self.workstation_manager is None:
            return 0.0
        try:
            workstation = self.workstation_manager.get_workstation(task.location)
        except KeyError:
            return 0.0
        return float(workstation.queue_length)

    def breakdown(
        self,
        robot: Robot,
        task: Task,
        target_x: float = 0.0,
        target_y: float = 0.0,
    ) -> ScoreBreakdown:
        """Score one robot as a candidate for one task, with every term
        broken out (see ScoreBreakdown), lower `total` is better.
        `target_x`/`target_y` are the task's destination coordinates
        (from a Workstation lookup, once one has x/y set).
        """
        w = self.weights
        travel_cost = math.hypot(target_x - robot.x, target_y - robot.y)
        battery_penalty = max(0.0, 100.0 - robot.battery_pct) / 100.0
        queue_cost = self._queue_cost(task)
        utilization_cost = float(self._assignment_counts.get(robot.robot_id, 0))
        priority_penalty = -float(task.priority)

        total = (
            w.travel * travel_cost
            + w.battery * battery_penalty
            + w.queue * queue_cost
            + w.utilization * utilization_cost
            + w.priority * priority_penalty
        )
        return ScoreBreakdown(
            travel_cost=travel_cost,
            battery_penalty=battery_penalty,
            queue_cost=queue_cost,
            utilization_cost=utilization_cost,
            priority_penalty=priority_penalty,
            total=total,
        )

    def score(
        self,
        robot: Robot,
        task: Task,
        target_x: float = 0.0,
        target_y: float = 0.0,
    ) -> float:
        """Score one robot as a candidate for one task; lower is
        better. See `breakdown()` for the individual terms.
        """
        return self.breakdown(robot, task, target_x, target_y).total

    def assign(
        self,
        task: Task,
        candidates: list[Robot],
        target_x: float = 0.0,
        target_y: float = 0.0,
    ) -> Robot:
        """Pick the best candidate robot for a task.

        Prefers robots with `RobotStatus.AVAILABLE`; falls back to the
        full candidate list only if none are available, so a caller
        that already filtered by availability doesn't lose robots
        needlessly. Records the pick against `utilization_cost` so a
        robot assigned repeatedly gets progressively deprioritized
        relative to less-used, otherwise-equal robots.
        """
        if not candidates:
            raise NoCandidateRobotError(f"no candidate robots for task {task.task_id}")

        available = [r for r in candidates if r.status == RobotStatus.AVAILABLE]
        pool = available or candidates

        chosen = min(pool, key=lambda r: self.score(r, task, target_x, target_y))
        self._assignment_counts[chosen.robot_id] = self._assignment_counts.get(chosen.robot_id, 0) + 1
        return chosen
