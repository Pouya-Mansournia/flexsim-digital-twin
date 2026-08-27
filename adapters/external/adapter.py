"""External System Adapter interface.

Scaffolding only (Phase 6, not implemented). See adapters/README.md.

Meant to be the single stable boundary between enterprise systems
(WMS/ERP/OMS/MES) and the Mission Manager, so RMS-internal changes
never leak into WMS-specific request/response schemas.
"""

from __future__ import annotations

from rms.domain import Mission


class ExternalSystemAdapter:
    """Translates an external system's request format into a Mission
    the Mission Manager can accept.
    """

    def parse_request(self, payload: dict) -> Mission:
        """Validate and translate an inbound request into a Mission."""
        raise NotImplementedError

    def notify_status(self, mission: Mission) -> None:
        """Report mission status back to the originating system."""
        raise NotImplementedError
