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
prints its result, and exits. It shows the current wiring, not a claim
that the RMS is deployable: rms/traffic and most of adapters/ are still
interface-only (see rms/README.md), and queue_cost/utilization_cost in
the scheduler's score are still placeholders.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Run directly (not via pytest, which has conftest.py for this): put the
# repository root on sys.path so `adapters`/`rms` import regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters.flexsim import FlexSimAdapter  # noqa: E402
from rms.services import IntegrationError, RmsOrchestrator  # noqa: E402


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
