import pytest

from rms.domain import Robot, RobotStatus
from rms.fleet import FleetManager


def make_manager_with_robots() -> FleetManager:
    manager = FleetManager()
    manager.register(Robot(robot_id="AMR-01", status=RobotStatus.AVAILABLE))
    manager.register(Robot(robot_id="AMR-02", status=RobotStatus.BUSY))
    return manager


def test_get_robot_returns_registered_robot():
    manager = make_manager_with_robots()
    assert manager.get_robot("AMR-01").robot_id == "AMR-01"


def test_get_robot_raises_for_unknown_id():
    manager = make_manager_with_robots()
    with pytest.raises(KeyError):
        manager.get_robot("does-not-exist")


def test_list_available_excludes_busy_robots():
    manager = make_manager_with_robots()
    available_ids = {r.robot_id for r in manager.list_available()}
    assert available_ids == {"AMR-01"}


def test_update_state_applies_partial_update():
    manager = make_manager_with_robots()
    manager.update_state("AMR-02", status=RobotStatus.AVAILABLE, battery_pct=42.0)

    robot = manager.get_robot("AMR-02")
    assert robot.status == RobotStatus.AVAILABLE
    assert robot.battery_pct == 42.0
