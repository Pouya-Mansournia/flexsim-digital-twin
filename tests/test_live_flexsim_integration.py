"""Integration test for the full rms/ + adapters/flexsim/ scheduling
flow against a real, running bridge/.

Separate from the unit tests: everything else in tests/ uses mocked
HTTP and needs nothing running. This one talks to a real bridge on
127.0.0.1:8000, so it self-skips (not fails) when the bridge isn't up,
keeping the rest of the suite green with no setup required. Run
bridge\\start.bat first to actually exercise this test.
"""

from __future__ import annotations

import urllib.error

import pytest

from adapters.flexsim import FlexSimAdapter
from adapters.flexsim.adapter import FlexSimAdapterError
from rms.services import IntegrationError, RmsOrchestrator

pytestmark = pytest.mark.live


def _bridge_is_reachable(adapter: FlexSimAdapter) -> bool:
    try:
        adapter._get_json("/health")  # noqa: SLF001 - cheapest reachability probe available
        return True
    except (FlexSimAdapterError, urllib.error.URLError):
        return False


def test_live_orchestration_against_running_bridge():
    adapter = FlexSimAdapter(timeout=1.5)
    if not _bridge_is_reachable(adapter):
        pytest.skip("bridge not reachable at 127.0.0.1:8000; start bridge\\start.bat to run this")

    orchestrator = RmsOrchestrator(adapter)
    robots = orchestrator.sync_fleet()
    if not robots:
        pytest.skip("bridge reachable but has no robot telemetry yet")

    try:
        result = orchestrator.run_mission("move_tote", "inbound", "workstation_03", priority=5)
    except IntegrationError as exc:
        pytest.fail(f"orchestration failed against a reachable bridge: {exc}")

    assert result.command_id
    assert result.selected_robot.robot_id in {r.robot_id for r in robots}
    assert isinstance(result.score, float)
