"""Live end-to-end demo: rms/ scheduling and dispatching a task against
the real, running bridge/ service.

    FlexSim -> bridge -> FlexSimAdapter.get_robots() -> FleetManager
        -> MissionManager.create_mission() -> TaskManager
        -> ResourceScheduler -> selected Robot
        -> FlexSimAdapter.send_command() -> bridge /api/v1/commands
        -> command_id

Requires bridge/ already running (`bridge\\start.bat` or `.\\run.ps1`
from bridge/) with some robot telemetry flowing, from FlexSim itself or
from `bridge\\start_ros2_sim.bat`. See the root README's "Connecting
FlexSim" section.

Run from the repository root:

    python examples/live_flexsim_rms_demo.py

This is a demonstration, not a service: it runs one scheduling cycle,
prints its result, and exits. It also posts the decision to
POST /api/v1/rms/decision (best-effort) so it shows up on the live
dashboard's "RMS Scheduling Decision" panel at
http://127.0.0.1:8000/dashboard. It shows the current wiring, not a
claim that the RMS is deployable: most of adapters/ (ros2/, plc/,
external/) is still interface-only (see rms/README.md).
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Run directly (not via pytest, which has conftest.py for this): put the
# repository root on sys.path so `adapters`/`rms` import regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters.flexsim import FlexSimAdapter  # noqa: E402
from rms.scheduler.resource_scheduler import ScoreBreakdown  # noqa: E402
from rms.services import IntegrationError, OrchestrationResult, RmsOrchestrator  # noqa: E402


def post_decision_to_dashboard(
    bridge_url: str, mission_type: str, source: str, result: OrchestrationResult, breakdown: ScoreBreakdown
) -> None:
    """Best-effort: the demo's own console output already told the
    story, so a bridge that's unreachable or running an older version
    without this endpoint shouldn't fail the whole run.
    """
    body = {
        "mission_type": mission_type,
        "source": source,
        "destination": result.task.location,
        "priority": result.task.priority,
        "selected_robot": result.selected_robot.robot_id,
        "score": result.score,
        "travel_cost": breakdown.travel_cost,
        "battery_penalty": breakdown.battery_penalty,
        "queue_cost": breakdown.queue_cost,
        "utilization_cost": breakdown.utilization_cost,
        "priority_penalty": breakdown.priority_penalty,
        "used_fallback": result.used_fallback,
        "command_id": result.command_id,
    }
    request = urllib.request.Request(
        f"{bridge_url}/api/v1/rms/decision",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=3.0)
    except (urllib.error.URLError, TimeoutError):
        pass


def main() -> int:
    adapter = FlexSimAdapter()
    orchestrator = RmsOrchestrator(adapter)

    try:
        robots = orchestrator.sync_fleet()
    except IntegrationError as exc:
        print(f"[FlexSim] Could not reach bridge: {exc}")
        print("Start it first: bridge\\start.bat (see the root README).")
        print("\nRMS live integration: FAIL")
        return 1

    if not robots:
        print("[FlexSim] Bridge is reachable, but no robot telemetry has arrived yet.")
        print("Start FlexSim, or bridge\\start_ros2_sim.bat, then rerun this.")
        print("\nRMS live integration: FAIL")
        return 1

    print(f"[FlexSim] {len(robots)} robot(s) received\n")
    for robot in robots:
        print(f"{robot.robot_id:<12} {robot.status.value.upper():<10} battery={robot.battery_pct:.0f}%")

    try:
        workstations = orchestrator.sync_workstations()
    except IntegrationError:
        workstations = []
    if workstations:
        print(f"\n[FlexSim] {len(workstations)} workstation(s)/queue(s) received\n")
        for ws in workstations:
            print(f"{ws.workstation_id:<12} {ws.status.value.upper():<10} queue={ws.queue_length}")
        destination = workstations[0].workstation_id
    else:
        destination = "workstation_03"

    mission_type, source = "move_tote", "inbound"
    try:
        result = orchestrator.run_mission(mission_type, source, destination, priority=5)
    except IntegrationError as exc:
        print(f"\nScheduling/dispatch failed: {exc}")
        print("\nRMS live integration: FAIL")
        return 1

    print(f"\nMission created:\n  {mission_type} {source} -> {destination}")

    breakdown = orchestrator.scheduler.breakdown(result.selected_robot, result.task)
    print("\nScheduler decision:")
    print(f"  selected_robot = {result.selected_robot.robot_id}")
    print(f"  score = {result.score:.2f}")
    print(
        f"  (travel={breakdown.travel_cost:.2f}, battery_penalty={breakdown.battery_penalty:.2f}, "
        f"queue_cost={breakdown.queue_cost:.2f}, utilization_cost={breakdown.utilization_cost:.2f}, "
        f"priority_penalty={breakdown.priority_penalty:.2f})"
    )
    if result.used_fallback:
        print("  (fallback: no AVAILABLE robot found; assigned from the full candidate pool)")

    print("\nCommand sent:")
    print(f"  command_id = {result.command_id}")

    post_decision_to_dashboard(adapter.bridge_url, mission_type, source, result, breakdown)
    print(f"\nPosted decision to {adapter.bridge_url}/dashboard")

    print("\nRMS live integration: PASS")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except IntegrationError as exc:
        # Belt-and-suspenders: every expected failure above already returns
        # cleanly, so this only catches something unanticipated in
        # IntegrationError itself, never a raw adapter/network traceback.
        print(f"\nUnexpected integration error: {exc}")
        print("\nRMS live integration: FAIL")
        sys.exit(1)
