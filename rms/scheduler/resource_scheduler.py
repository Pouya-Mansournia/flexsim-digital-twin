"""Resource Scheduler: assigns tasks to robots.

Phase 3 first implementation: a deterministic nearest-available policy,
weighted by battery and task priority, matching the scoring formula in
the root README's "Vision: toward a Robot Management System (RMS)"
section. Congestion-aware (`queue_cost`) and utilization-aware
(`utilization_cost`) terms are placeholders (always 0) until the
Traffic Manager and Fleet Manager have the data to feed them; they're
kept in the formula now so wiring them in later doesn't change the
interface.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from rms.domain import Robot, RobotStatus, Task


@dataclass
class ScoreWeights:
    """Weights for the candidate-scoring formula: lower score wins.

    score = w_travel * travel_cost + w_battery * battery_penalty
          + w_queue * queue_cost + w_utilization * utilization_cost
          + w_priority * priority_penalty
    """

    travel: float = 1.0
    battery: float = 1.0
    queue: float = 1.0
    utilization: float = 1.0
    priority: float = 1.0


class NoCandidateRobotError(RuntimeError):
    """Raised when a task has no candidate robots to choose from."""


class ResourceScheduler:
    """Chooses the best robot for a task using a simple weighted score.

    `queue_cost` and `utilization_cost` are 0.0 until the Traffic
    Manager and Fleet Manager expose that data; only `travel_cost`,
    `battery_penalty`, and `priority_penalty` currently vary.
    """

    def __init__(self, weights: ScoreWeights | None = None) -> None:
        self.weights = weights or ScoreWeights()

    def score(
        self,
        robot: Robot,
        task: Task,
        target_x: float = 0.0,
        target_y: float = 0.0,
    ) -> float:
        """Score one robot as a candidate for one task; lower is
        better. `target_x`/`target_y` are the task's destination
        coordinates (from a Workstation lookup, once one exists).
        """
        w = self.weights
        travel_cost = math.hypot(target_x - robot.x, target_y - robot.y)
        battery_penalty = max(0.0, 100.0 - robot.battery_pct) / 100.0
        queue_cost = 0.0
        utilization_cost = 0.0
        priority_penalty = -float(task.priority)

        return (
            w.travel * travel_cost
            + w.battery * battery_penalty
            + w.queue * queue_cost
            + w.utilization * utilization_cost
            + w.priority * priority_penalty
        )

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
        needlessly.
        """
        if not candidates:
            raise NoCandidateRobotError(f"no candidate robots for task {task.task_id}")

        available = [r for r in candidates if r.status == RobotStatus.AVAILABLE]
        pool = available or candidates

        return min(pool, key=lambda r: self.score(r, task, target_x, target_y))
