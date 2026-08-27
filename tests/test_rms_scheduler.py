import pytest

from rms.domain import Robot, RobotStatus, Task, TaskStatus
from rms.scheduler import ResourceScheduler
from rms.scheduler.resource_scheduler import NoCandidateRobotError


def make_task() -> Task:
    return Task(
        task_id="mission-1-task1",
        mission_id="mission-1",
        action="move_tote",
        location="Workstation-03",
        status=TaskStatus.PENDING,
    )


def test_assign_picks_nearest_available_robot():
    scheduler = ResourceScheduler()
    task = make_task()
    near = Robot(robot_id="AMR-near", status=RobotStatus.AVAILABLE, x=1.0, y=0.0)
    far = Robot(robot_id="AMR-far", status=RobotStatus.AVAILABLE, x=50.0, y=0.0)

    chosen = scheduler.assign(task, [far, near], target_x=0.0, target_y=0.0)

    assert chosen.robot_id == "AMR-near"


def test_assign_prefers_available_over_busy_even_if_closer():
    scheduler = ResourceScheduler()
    task = make_task()
    busy_but_close = Robot(robot_id="AMR-busy", status=RobotStatus.BUSY, x=0.0, y=0.0)
    available_but_far = Robot(
        robot_id="AMR-available", status=RobotStatus.AVAILABLE, x=10.0, y=0.0
    )

    chosen = scheduler.assign(
        task, [busy_but_close, available_but_far], target_x=0.0, target_y=0.0
    )

    assert chosen.robot_id == "AMR-available"


def test_assign_falls_back_to_any_candidate_if_none_available():
    scheduler = ResourceScheduler()
    task = make_task()
    only_busy = Robot(robot_id="AMR-busy", status=RobotStatus.BUSY, x=0.0, y=0.0)

    chosen = scheduler.assign(task, [only_busy])

    assert chosen.robot_id == "AMR-busy"


def test_assign_raises_with_no_candidates():
    scheduler = ResourceScheduler()
    with pytest.raises(NoCandidateRobotError):
        scheduler.assign(make_task(), [])


def test_lower_battery_increases_score():
    scheduler = ResourceScheduler()
    task = make_task()
    full_battery = Robot(robot_id="AMR-full", status=RobotStatus.AVAILABLE, battery_pct=100.0)
    low_battery = Robot(robot_id="AMR-low", status=RobotStatus.AVAILABLE, battery_pct=10.0)

    assert scheduler.score(low_battery, task) > scheduler.score(full_battery, task)
