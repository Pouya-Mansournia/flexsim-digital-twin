"""Resource Scheduler interface.

Scaffolding only (Phase 3, not implemented). See rms/README.md and the
root README's scoring formula in "Vision: toward a Robot Management
System (RMS)".

The intent is to start with a deterministic policy (nearest-available,
then battery-aware, then congestion-aware) before anything
optimization- or learning-based, so results stay reproducible and easy
to validate against FlexSim.
"""

from __future__ import annotations

from dataclasses import dataclass

from rms.domain import Robot, Task


@dataclass
class ScoreWeights:
    """Weights for the candidate-scoring formula documented in the root
    README: lower score wins.

    score = w_travel * travel_cost + w_battery * battery_penalty
          + w_queue * queue_cost + w_utilization * utilization_cost
          + w_priority * priority_penalty
    """

    travel: float = 1.0
    battery: float = 1.0
    queue: float = 1.0
    utilization: float = 1.0
    priority: float = 1.0


class ResourceScheduler:
    """Chooses the best robot (and, later, workstation) for a task."""

    def __init__(self, weights: ScoreWeights | None = None) -> None:
        self.weights = weights or ScoreWeights()

    def score(self, robot: Robot, task: Task) -> float:
        """Score one robot as a candidate for one task; lower is
        better. Not implemented: needs travel-cost and utilization
        inputs from FleetManager/TrafficManager/WorkstationManager.
        """
        raise NotImplementedError

    def assign(self, task: Task, candidates: list[Robot]) -> Robot:
        """Pick the best candidate robot for a task."""
        raise NotImplementedError
