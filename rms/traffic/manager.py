"""Traffic Manager: in-memory zone reservations and congestion tracking.

Phase 5 first implementation: deterministic and dependency-free, same
pattern as fleet/ and workstations/. A zone is any shared-space id the
caller defines (an aisle, an intersection, a rack face); this module
doesn't know or care what one represents physically.
"""

from __future__ import annotations


class TrafficManager:
    """Coordinates shared-space traffic: which robot (if any) currently
    holds each zone, and how often a zone has been contested.
    """

    def __init__(self) -> None:
        self._reservations: dict[str, str] = {}  # zone_id -> robot_id
        self._contention_counts: dict[str, int] = {}  # zone_id -> refused attempts

    def reserve_zone(self, robot_id: str, zone_id: str) -> bool:
        """Attempt to reserve a zone for a robot.

        Returns True if the zone was free or already held by this same
        robot (idempotent re-reservation). Returns False, and records
        one contention event against the zone, if another robot
        already holds it.
        """
        holder = self._reservations.get(zone_id)
        if holder is None or holder == robot_id:
            self._reservations[zone_id] = robot_id
            return True

        self._contention_counts[zone_id] = self._contention_counts.get(zone_id, 0) + 1
        return False

    def release_zone(self, robot_id: str, zone_id: str) -> None:
        """Release a zone reservation held by a robot.

        A no-op if the zone isn't reserved, or is reserved by a
        different robot: releasing a zone you don't hold shouldn't be
        able to free another robot's reservation.
        """
        if self._reservations.get(zone_id) == robot_id:
            del self._reservations[zone_id]

    def is_reserved(self, zone_id: str) -> bool:
        """Whether any robot currently holds this zone."""
        return zone_id in self._reservations

    def holder(self, zone_id: str) -> str | None:
        """The robot_id currently holding this zone, if any."""
        return self._reservations.get(zone_id)

    def congestion_level(self, zone_id: str) -> float:
        """A 0-1 congestion estimate for a zone: 1.0 if currently
        reserved by another robot's perspective is not distinguished
        here (this manager has no caller identity), 0.0 if free, plus
        an additional signal from how often it's been contested. See
        `contention_count()` for the raw count behind this.
        """
        if not self.is_reserved(zone_id):
            return 0.0
        # Reserved zones start at a 0.5 baseline; repeated contention
        # pushes toward 1.0 without a magic threshold to tune later.
        contention = self._contention_counts.get(zone_id, 0)
        return min(1.0, 0.5 + contention * 0.1)

    def contention_count(self, zone_id: str) -> int:
        """How many times reserve_zone() has been refused for this zone."""
        return self._contention_counts.get(zone_id, 0)
