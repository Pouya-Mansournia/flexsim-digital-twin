"""Thread-safe in-memory store for the latest RMS scheduling decision."""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from app.models.rms_decision import RmsDecision, RmsDecisionRequest, RmsDecisionState


class RmsDecisionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._decision: RmsDecision | None = None

    def set_decision(self, request: RmsDecisionRequest) -> RmsDecision:
        decision = RmsDecision(
            **request.model_dump(), received_at=datetime.now(timezone.utc).isoformat()
        )
        with self._lock:
            self._decision = decision
        return decision

    def get_state(self) -> RmsDecisionState:
        with self._lock:
            if self._decision is None:
                return RmsDecisionState(has_data=False)
            return RmsDecisionState(has_data=True, decision=self._decision)

    def reset(self) -> None:
        with self._lock:
            self._decision = None


rms_decision_store = RmsDecisionStore()
