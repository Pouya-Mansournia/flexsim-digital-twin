"""Thread-safe in-memory store for FlexSim commands.

Commands are kept in insertion order so "oldest pending command" is a cheap
linear scan. A future persistent-storage implementation can satisfy the same
interface without changes to the API layer.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from app.models.command import Command, CommandRequest, CommandStatus


class CommandStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._commands: dict[str, Command] = {}
        self._order: list[str] = []

    def create(self, request: CommandRequest) -> Command:
        now = datetime.now(timezone.utc).isoformat()
        command = Command(
            command_id=str(uuid.uuid4()),
            target=request.target,
            command=request.command,
            parameters=request.parameters,
            status=CommandStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._commands[command.command_id] = command
            self._order.append(command.command_id)
        return command

    def get_next_pending(self) -> Command | None:
        with self._lock:
            for command_id in self._order:
                command = self._commands[command_id]
                if command.status == CommandStatus.PENDING:
                    return command
        return None

    def get(self, command_id: str) -> Command | None:
        with self._lock:
            return self._commands.get(command_id)

    def update_status(
        self, command_id: str, status: CommandStatus, message: str | None
    ) -> Command | None:
        with self._lock:
            command = self._commands.get(command_id)
            if command is None:
                return None
            command.status = status
            command.message = message
            command.updated_at = datetime.now(timezone.utc).isoformat()
            return command


command_store = CommandStore()
