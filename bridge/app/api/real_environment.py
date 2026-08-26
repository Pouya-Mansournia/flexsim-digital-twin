"""Endpoints for the real/ROS2-side environment telemetry (separate from
the FlexSim simulation telemetry in api/telemetry.py), so the two can be
compared on the dashboard as a digital-twin validation view.
"""

from fastapi import APIRouter

from app.core.logging import get_logger
from app.models.real_environment import (
    RealEnvironmentAck,
    RealEnvironmentPayload,
    RealEnvironmentState,
)
from app.models.real_environment_config import RealEnvironmentConfig
from app.services.real_environment_config_store import real_environment_config_store
from app.services.real_environment_store import real_environment_store

router = APIRouter(prefix="/api/v1/real", tags=["real-environment"])
logger = get_logger(__name__)


@router.post("/telemetry", response_model=RealEnvironmentAck)
def post_real_telemetry(payload: RealEnvironmentPayload) -> RealEnvironmentAck:
    real_environment_store.set_telemetry(payload)
    logger.info(
        "Real-environment telemetry received: sim_time=%.2f status=%s queues=%d",
        payload.simulation_time,
        payload.status,
        len(payload.queues),
    )
    return RealEnvironmentAck(accepted=True)


@router.get("/state", response_model=RealEnvironmentState)
def get_real_state() -> RealEnvironmentState:
    return real_environment_store.get_state()


@router.post("/state/reset", response_model=RealEnvironmentState)
def reset_real_state() -> RealEnvironmentState:
    real_environment_store.reset()
    logger.info("Real-environment state store reset")
    return real_environment_store.get_state()


@router.get("/config", response_model=RealEnvironmentConfig)
def get_real_config() -> RealEnvironmentConfig:
    return real_environment_config_store.get()


@router.post("/config", response_model=RealEnvironmentConfig)
def set_real_config(config: RealEnvironmentConfig) -> RealEnvironmentConfig:
    updated = real_environment_config_store.set_robot_count(config.robot_count)
    logger.info("Real-environment fleet size set to %d", updated.robot_count)
    return updated
