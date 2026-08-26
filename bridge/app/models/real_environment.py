"""Pydantic models for telemetry coming from the "real" (ROS2-side)
environment, as opposed to the FlexSim simulation.

Kept intentionally small and separate from app.models.telemetry: this is a
different data source (a physical/simulated robot fleet moving totes
between queues), not FlexSim, and the two are compared side by side on
the dashboard rather than merged into one payload.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.telemetry import RobotState


class RealEnvironmentPayload(BaseModel):
    """A snapshot of queue levels and robot state reported by the
    real/ROS2-side system.

    Reuses RobotState from app.models.telemetry (same x/y/speed/state/
    battery shape as FlexSim's robots) so the dashboard can render both
    sides with the same table-rendering code.
    """

    simulation_time: float
    status: str
    queues: dict[str, int] = Field(default_factory=dict)
    robots: dict[str, RobotState] = Field(default_factory=dict)


class RealEnvironmentAck(BaseModel):
    accepted: bool


class RealEnvironmentState(BaseModel):
    """Wrapper returned by GET /api/v1/real/state."""

    has_data: bool
    telemetry: RealEnvironmentPayload | None = None
    received_at: str | None = None
