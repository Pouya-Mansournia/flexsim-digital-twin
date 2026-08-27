"""Pydantic models describing FlexSim telemetry payloads.

Object identifiers (queue names, processor names, robot names, etc.) are
intentionally free-form dictionary keys rather than hard-coded fields, since
every FlexSim model defines its own object names.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ProcessorState(BaseModel):
    state: str
    utilization: float = Field(ge=0.0)

    @field_validator("utilization")
    @classmethod
    def clamp_utilization(cls, value: float) -> float:
        """Clamp instead of reject.

        `utilization` is meant to be a 0.0-1.0 ratio, but it's computed
        by the FlexSim model itself (accumulated busy-time / elapsed
        time; see bridge/flexsim/verified_scripts/README.md), and a
        transient double-count there (e.g. a leftover Process Flow
        token surviving a Reset) can briefly push it above 1.0. Erroring
        on that used to reject the *entire* telemetry payload for that
        tick — queues and robots included, not just the one processor —
        which is a worse failure mode than a clamped number. The
        FlexScript should still fix its own computation; see the
        gotcha in verified_scripts/README.md.
        """
        return min(value, 1.0)


class RobotState(BaseModel):
    x: float
    y: float
    speed: float
    state: str
    battery: float = Field(ge=0.0, le=100.0)


class TelemetryPayload(BaseModel):
    """Telemetry snapshot sent by FlexSim."""

    simulation_time: float
    model_status: str
    queues: dict[str, int] = Field(default_factory=dict)
    processors: dict[str, ProcessorState] = Field(default_factory=dict)
    robots: dict[str, RobotState] = Field(default_factory=dict)
    conveyors: dict[str, Any] = Field(default_factory=dict)
    sources: dict[str, Any] = Field(default_factory=dict)
    sinks: dict[str, Any] = Field(default_factory=dict)


class TelemetryAck(BaseModel):
    accepted: bool


class SimulationState(BaseModel):
    """Wrapper returned by GET /api/v1/state.

    `has_data` distinguishes "no telemetry received yet" from an empty
    telemetry snapshot, so clients never have to guess from missing fields.
    """

    has_data: bool
    telemetry: TelemetryPayload | None = None
    received_at: str | None = None
