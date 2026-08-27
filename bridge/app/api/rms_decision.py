"""Endpoints for RMS scheduling decisions: a display channel the
dashboard reads, not one the bridge acts on. See
app/models/rms_decision.py for why this exists.
"""

from fastapi import APIRouter

from app.core.logging import get_logger
from app.models.rms_decision import RmsDecisionRequest, RmsDecisionState
from app.services.rms_decision_store import rms_decision_store

router = APIRouter(prefix="/api/v1", tags=["rms"])
logger = get_logger(__name__)


@router.post("/rms/decision", response_model=RmsDecisionState)
def post_rms_decision(request: RmsDecisionRequest) -> RmsDecisionState:
    rms_decision_store.set_decision(request)
    logger.info(
        "RMS decision received: %s %s -> %s, robot=%s score=%.2f command_id=%s",
        request.mission_type,
        request.source,
        request.destination,
        request.selected_robot,
        request.score,
        request.command_id,
    )
    return rms_decision_store.get_state()


@router.get("/rms/decision", response_model=RmsDecisionState)
def get_rms_decision() -> RmsDecisionState:
    return rms_decision_store.get_state()


@router.post("/rms/decision/reset", response_model=RmsDecisionState)
def reset_rms_decision() -> RmsDecisionState:
    rms_decision_store.reset()
    return rms_decision_store.get_state()
