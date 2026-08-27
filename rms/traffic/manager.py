"""Traffic Manager interface.

Scaffolding only (Phase 5, not implemented). See rms/README.md.
"""

from __future__ import annotations


class TrafficManager:
    """Coordinates shared-space traffic: zone reservations, congestion
    metrics, and (eventually) deadlock prevention between robots.
    """

    def reserve_zone(self, robot_id: str, zone_id: str) -> bool:
        """Attempt to reserve a zone for a robot; False if contested."""
        raise NotImplementedError

    def release_zone(self, robot_id: str, zone_id: str) -> None:
        """Release a zone reservation held by a robot."""
        raise NotImplementedError

    def congestion_level(self, zone_id: str) -> float:
        """Return a 0-1 congestion estimate for a zone."""
        raise NotImplementedError
