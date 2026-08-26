"""Pydantic models for the FlexSim command interface."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CommandStatus(str, Enum):
    PENDING = "pending"
    RECEIVED = "received"
    EXECUTED = "executed"
    FAILED = "failed"


class CommandRequest(BaseModel):
    """Command submitted by an external client, to be executed in FlexSim."""

    target: str
    command: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class Command(CommandRequest):
    """A command as stored server-side, with tracking metadata."""

    command_id: str
    status: CommandStatus = CommandStatus.PENDING
    created_at: str
    updated_at: str
    message: str | None = None


class CommandCreatedResponse(BaseModel):
    command_id: str
    status: CommandStatus


class NextCommandResponse(BaseModel):
    command: Command | None = None


class CommandAckRequest(BaseModel):
    status: CommandStatus
    message: str | None = None


class CommandAckResponse(BaseModel):
    command_id: str
    status: CommandStatus
