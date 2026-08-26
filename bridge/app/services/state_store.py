"""Thread-safe in-memory store for the latest FlexSim telemetry snapshot.

This is intentionally the only place that knows telemetry is currently kept
in memory. A future persistent-storage implementation (e.g. SQLite) can
satisfy the same get/set interface without changes to the API layer.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from app.models.telemetry import SimulationState, TelemetryPayload


class StateStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._telemetry: TelemetryPayload | None = None
        self._received_at: str | None = None

    def set_telemetry(self, telemetry: TelemetryPayload) -> None:
        with self._lock:
            self._telemetry = telemetry
            self._received_at = datetime.now(timezone.utc).isoformat()

    def get_state(self) -> SimulationState:
        with self._lock:
            if self._telemetry is None:
                return SimulationState(has_data=False)
            return SimulationState(
                has_data=True,
                telemetry=self._telemetry,
                received_at=self._received_at,
            )

    def reset(self) -> None:
        with self._lock:
            self._telemetry = None
            self._received_at = None


state_store = StateStore()
