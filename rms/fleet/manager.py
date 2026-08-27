"""Fleet Manager interface.

Scaffolding only (Phase 3/4, not implemented). See rms/README.md.

Intended to be backed by `adapters/flexsim/` during simulation and
`adapters/ros2/` once a real fleet is connected (Phase 4), without the
Resource Scheduler needing to know which one is live.
"""

from __future__ import annotations

from rms.domain import Robot, RobotStatus


class FleetManager:
    """Maintains the current known state of every robot in the fleet."""

    def get_robot(self, robot_id: str) -> Robot:
        """Look up a robot's current state."""
        raise NotImplementedError

    def list_available(self) -> list[Robot]:
        """List robots currently able to accept a new task."""
        raise NotImplementedError

    def update_state(
        self,
        robot_id: str,
        status: RobotStatus | None = None,
        battery_pct: float | None = None,
        x: float | None = None,
        y: float | None = None,
    ) -> None:
        """Apply an incoming state update for one robot."""
        raise NotImplementedError
