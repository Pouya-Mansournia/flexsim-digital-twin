"""ROS 2 Adapter interface.

Scaffolding only (Phase 4, not implemented). See adapters/README.md.

Meant to eventually replace bridge/ros2_sim/simulator.py as the source
of /api/v1/real/telemetry, subscribing to real ROS 2 topics
(/warehouse/state, /amr/state) and dispatching RMS tasks to a real AMR
fleet via Nav2. No ROS 2 dependencies are installed in this repository
yet.
"""

from __future__ import annotations

from rms.domain import Robot, Task


class Ros2Adapter:
    """Bridges the RMS to a real ROS 2-connected robot fleet."""

    def get_robots(self) -> list[Robot]:
        """Read current robot state from ROS 2 topics."""
        raise NotImplementedError

    def dispatch_task(self, task: Task, robot_id: str) -> None:
        """Send a task to a robot via ROS 2 (e.g. a Nav2 goal)."""
        raise NotImplementedError
