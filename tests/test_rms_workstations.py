from rms.domain import Workstation, WorkstationStatus
from rms.workstations import WorkstationManager


def test_can_accept_true_for_ready_and_busy():
    manager = WorkstationManager()
    manager.register(Workstation(workstation_id="W1", status=WorkstationStatus.READY))
    manager.register(Workstation(workstation_id="W2", status=WorkstationStatus.BUSY))

    assert manager.can_accept("W1") is True
    assert manager.can_accept("W2") is True


def test_can_accept_false_for_blocked_fault_starved_offline():
    manager = WorkstationManager()
    for status in (
        WorkstationStatus.BLOCKED,
        WorkstationStatus.FAULT,
        WorkstationStatus.STARVED,
        WorkstationStatus.OFFLINE,
    ):
        manager.register(Workstation(workstation_id=status.value, status=status))
        assert manager.can_accept(status.value) is False


def test_can_accept_true_for_unknown_workstation():
    manager = WorkstationManager()
    assert manager.can_accept("never-registered") is True
