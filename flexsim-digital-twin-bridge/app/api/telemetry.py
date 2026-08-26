"""Endpoints for receiving FlexSim telemetry and exposing simulation state."""

from fastapi import APIRouter

from app.core.logging import get_logger
from app.models.telemetry import SimulationState, TelemetryAck, TelemetryPayload
from app.services.state_store import state_store

router = APIRouter(prefix="/api/v1", tags=["telemetry"])
logger = get_logger(__name__)


@router.post("/telemetry", response_model=TelemetryAck)
def post_telemetry(payload: TelemetryPayload) -> TelemetryAck:
    state_store.set_telemetry(payload)
    logger.info(
        "Telemetry received: sim_time=%.2f status=%s queues=%d processors=%d robots=%d",
        payload.simulation_time,
        payload.model_status,
        len(payload.queues),
        len(payload.processors),
        len(payload.robots),
    )
    return TelemetryAck(accepted=True)


@router.get("/state", response_model=SimulationState)
def get_state() -> SimulationState:
    return state_store.get_state()


@router.post("/state/reset", response_model=SimulationState)
def reset_state() -> SimulationState:
    state_store.reset()
    logger.info("State store reset")
    return state_store.get_state()
