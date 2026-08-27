from rms.traffic import TrafficManager


def test_reserve_zone_succeeds_when_free():
    manager = TrafficManager()
    assert manager.reserve_zone("AGV1", "Zone-A") is True
    assert manager.holder("Zone-A") == "AGV1"


def test_reserve_zone_is_idempotent_for_the_same_robot():
    manager = TrafficManager()
    manager.reserve_zone("AGV1", "Zone-A")
    assert manager.reserve_zone("AGV1", "Zone-A") is True


def test_reserve_zone_fails_for_a_different_robot_and_counts_contention():
    manager = TrafficManager()
    manager.reserve_zone("AGV1", "Zone-A")

    assert manager.reserve_zone("AGV2", "Zone-A") is False
    assert manager.contention_count("Zone-A") == 1
    assert manager.holder("Zone-A") == "AGV1"  # unchanged


def test_release_zone_frees_it_for_others():
    manager = TrafficManager()
    manager.reserve_zone("AGV1", "Zone-A")
    manager.release_zone("AGV1", "Zone-A")

    assert manager.is_reserved("Zone-A") is False
    assert manager.reserve_zone("AGV2", "Zone-A") is True


def test_release_zone_by_non_holder_is_a_no_op():
    manager = TrafficManager()
    manager.reserve_zone("AGV1", "Zone-A")
    manager.release_zone("AGV2", "Zone-A")  # AGV2 never held it

    assert manager.holder("Zone-A") == "AGV1"


def test_congestion_level_zero_when_free_and_rises_with_contention():
    manager = TrafficManager()
    assert manager.congestion_level("Zone-A") == 0.0

    manager.reserve_zone("AGV1", "Zone-A")
    baseline = manager.congestion_level("Zone-A")
    assert baseline == 0.5

    manager.reserve_zone("AGV2", "Zone-A")  # refused, contention +1
    assert manager.congestion_level("Zone-A") > baseline
