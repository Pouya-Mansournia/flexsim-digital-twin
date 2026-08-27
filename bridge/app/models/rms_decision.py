"""Pydantic models for RMS scheduling decisions posted to the bridge.

This is a display/observability channel, not a control one: the bridge
doesn't act on these, it just stores the latest one so the dashboard can
show what rms/'s ResourceScheduler decided, alongside FlexSim's own
telemetry. See rms/services/orchestrator.py (the producer) and
examples/live_flexsim_rms_demo.py (posts one after each run).
"""

from __future__ import annotations

from pydantic import BaseModel


class RmsDecisionRequest(BaseModel):
    """One scheduling decision, as reported by an RmsOrchestrator run."""

    mission_type: str
    source: str
    destination: str
    priority: int
    selected_robot: str
    score: float
    travel_cost: float
    battery_penalty: float
    queue_cost: float
    utilization_cost: float
    priority_penalty: float
    used_fallback: bool
    command_id: str


class RmsDecision(RmsDecisionRequest):
    """As stored server-side, with a received-at timestamp."""

    received_at: str


class RmsDecisionState(BaseModel):
    """Wrapper returned by GET /api/v1/rms/decision."""

    has_data: bool
    decision: RmsDecision | None = None
