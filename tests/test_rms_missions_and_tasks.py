from rms.domain import MissionStatus, TaskStatus
from rms.missions import MissionManager
from rms.tasks import TaskManager


def test_create_mission_decomposes_into_one_task():
    task_manager = TaskManager()
    mission_manager = MissionManager(task_manager)

    mission = mission_manager.create_mission(
        mission_type="move_tote",
        source="Inbound",
        destination="Workstation-03",
        priority=7,
    )

    assert mission.status == MissionStatus.ASSIGNED
    assert len(mission.task_ids) == 1

    task = task_manager.get_task(mission.task_ids[0])
    assert task.mission_id == mission.mission_id
    assert task.location == "Workstation-03"
    assert task.status == TaskStatus.PENDING


def test_cancel_mission_sets_cancelled_status():
    task_manager = TaskManager()
    mission_manager = MissionManager(task_manager)
    mission = mission_manager.create_mission("move_tote", "Inbound", "Workstation-03")

    mission_manager.cancel_mission(mission.mission_id)

    assert mission_manager.get_mission(mission.mission_id).status == MissionStatus.CANCELLED


def test_task_mark_completed_and_failed():
    task_manager = TaskManager()
    mission_manager = MissionManager(task_manager)
    mission = mission_manager.create_mission("move_tote", "Inbound", "Workstation-03")
    task_id = mission.task_ids[0]

    task_manager.mark_completed(task_id)
    assert task_manager.get_task(task_id).status == TaskStatus.COMPLETED

    task_manager.mark_failed(task_id, reason="robot fault")
    task = task_manager.get_task(task_id)
    assert task.status == TaskStatus.FAILED
    assert task.failure_reason == "robot fault"
