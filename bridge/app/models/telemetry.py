"""Pydantic models describing FlexSim telemetry payloads.

Object identifiers (queue names, processor names, robot names, etc.) are
intentionally free-form dictionary keys rather than hard-coded fields, since
every FlexSim model defines its own object names.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProcessorState(BaseModel):
    state: str
    utilization: float = Field(ge=0.0, le=1.0)


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
