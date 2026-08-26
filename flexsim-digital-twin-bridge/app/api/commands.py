"""Endpoints for issuing commands to FlexSim and tracking their status."""

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.models.command import (
    CommandAckRequest,
    CommandAckResponse,
    CommandCreatedResponse,
    CommandRequest,
    NextCommandResponse,
)
from app.services.command_store import command_store

router = APIRouter(prefix="/api/v1", tags=["commands"])
logger = get_logger(__name__)


@router.post("/commands", response_model=CommandCreatedResponse)
def post_command(request: CommandRequest) -> CommandCreatedResponse:
    command = command_store.create(request)
    logger.info(
        "Command created: id=%s target=%s command=%s",
        command.command_id,
        command.target,
        command.command,
    )
    return CommandCreatedResponse(command_id=command.command_id, status=command.status)


@router.get("/commands/next", response_model=NextCommandResponse)
def get_next_command() -> NextCommandResponse:
    command = command_store.get_next_pending()
    return NextCommandResponse(command=command)


@router.post("/commands/{command_id}/ack", response_model=CommandAckResponse)
def ack_command(command_id: str, request: CommandAckRequest) -> CommandAckResponse:
    command = command_store.update_status(command_id, request.status, request.message)
    if command is None:
        raise HTTPException(status_code=404, detail=f"Unknown command_id: {command_id}")
    logger.info(
        "Command acknowledged: id=%s status=%s message=%s",
        command.command_id,
        command.status,
        request.message,
    )
    return CommandAckResponse(command_id=command.command_id, status=command.status)
