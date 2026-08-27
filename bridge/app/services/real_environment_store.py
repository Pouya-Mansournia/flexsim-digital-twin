"""Thread-safe in-memory store for the latest real/ROS2-side environment
snapshot. Mirrors state_store.py but kept as a separate store so the
FlexSim simulation side and the real-environment side never overwrite
each other; the dashboard reads both independently to compare them.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from app.models.real_environment import RealEnvironmentPayload, RealEnvironmentState


class RealEnvironmentStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._telemetry: RealEnvironmentPayload | None = None
        self._received_at: str | None = None

    def set_telemetry(self, telemetry: RealEnvironmentPayload) -> None:
        with self._lock:
            self._telemetry = telemetry
            self._received_at = datetime.now(timezone.utc).isoformat()

    def get_state(self) -> RealEnvironmentState:
        with self._lock:
            if self._telemetry is None:
                return RealEnvironmentState(has_data=False)
            return RealEnvironmentState(
                has_data=True,
                telemetry=self._telemetry,
                received_at=self._received_at,
            )

    def reset(self) -> None:
        with self._lock:
            self._telemetry = None
            self._received_at = None


real_environment_store = RealEnvironmentStore()
