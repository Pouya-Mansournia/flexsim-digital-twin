"""Fleet Manager: an in-memory registry of robot state.

Phase 3 first implementation: deterministic and dependency-free, so it
can be exercised by unit tests and by the Resource Scheduler without
needing a real fleet or ROS 2 connected yet. A later
`adapters/ros2/`-backed version can replace this without changing the
interface (see rms/README.md).
"""

from __future__ import annotations

from rms.domain import Robot, RobotStatus


class FleetManager:
    """Maintains the current known state of every robot in the fleet."""

    def __init__(self) -> None:
        self._robots: dict[str, Robot] = {}

    def register(self, robot: Robot) -> None:
        """Add or replace a robot's record."""
        self._robots[robot.robot_id] = robot

    def get_robot(self, robot_id: str) -> Robot:
        """Look up a robot's current state."""
        try:
            return self._robots[robot_id]
        except KeyError:
            raise KeyError(f"unknown robot_id: {robot_id}") from None

    def list_available(self) -> list[Robot]:
        """List robots currently able to accept a new task."""
        return [r for r in self._robots.values() if r.status == RobotStatus.AVAILABLE]

    def list_all(self) -> list[Robot]:
        """List every known robot, regardless of status."""
        return list(self._robots.values())

    def update_state(
        self,
        robot_id: str,
        status: RobotStatus | None = None,
        battery_pct: float | None = None,
        x: float | None = None,
        y: float | None = None,
    ) -> None:
        """Apply an incoming state update for one robot."""
        robot = self.get_robot(robot_id)
        if status is not None:
            robot.status = status
        if battery_pct is not None:
            robot.battery_pct = battery_pct
        if x is not None:
            robot.x = x
        if y is not None:
            robot.y = y
