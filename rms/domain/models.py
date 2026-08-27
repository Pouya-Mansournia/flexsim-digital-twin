"""Domain types shared across the RMS core.

These describe the target data model discussed in the root README's RMS
vision section. Nothing in `rms/` currently persists or mutates these;
they exist to give the manager interfaces (`missions/`, `tasks/`,
`scheduler/`, `fleet/`, `traffic/`, `workstations/`) a concrete shape to
build against.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MissionStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class RobotStatus(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    CHARGING = "charging"
    FAULT = "fault"
    OFFLINE = "offline"


class WorkstationStatus(str, Enum):
    READY = "ready"
    BUSY = "busy"
    BLOCKED = "blocked"
    FAULT = "fault"
    STARVED = "starved"
    OFFLINE = "offline"


@dataclass
class Mission:
    """A business-level transport request, e.g. from a WMS."""

    mission_id: str
    mission_type: str
    source: str
    destination: str
    priority: int = 0
    status: MissionStatus = MissionStatus.PENDING
    task_ids: list[str] = field(default_factory=list)


@dataclass
class Task:
    """One executable step derived from a Mission by the Task Manager."""

    task_id: str
    mission_id: str
    action: str
    location: str
    priority: int = 0
    status: TaskStatus = TaskStatus.PENDING
    assigned_robot_id: str | None = None
    failure_reason: str | None = None


@dataclass
class Robot:
    """Fleet Manager's view of one robot's state and capability."""

    robot_id: str
    status: RobotStatus = RobotStatus.OFFLINE
    battery_pct: float = 100.0
    x: float = 0.0
    y: float = 0.0
    current_task_id: str | None = None
    capabilities: tuple[str, ...] = ()


@dataclass
class Workstation:
    """Workstation Manager's view of one station's state."""

    workstation_id: str
    status: WorkstationStatus = WorkstationStatus.OFFLINE
    queue_length: int = 0
    x: float = 0.0
    y: float = 0.0
    capabilities: tuple[str, ...] = ()
