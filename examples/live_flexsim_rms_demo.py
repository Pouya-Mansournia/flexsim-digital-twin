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

    python examples/live_flexsim_rms_demo.py                     one cycle against FlexSim's telemetry, then exit
    python examples/live_flexsim_rms_demo.py --loop               repeat every 5s until Ctrl+C
    python examples/live_flexsim_rms_demo.py --loop --interval 2
    python examples/live_flexsim_rms_demo.py --source real --loop schedule against the mock fleet instead

By default this reads FlexSim's own telemetry channel
(`/api/v1/state`), which only changes when an actual FlexSim model is
running and posting to it. `--source real` points it at the separate
mock/real-environment channel (`/api/v1/real/state`) that
`bridge\\start_ros2_sim.bat` posts to instead, so decisions have
something continuously changing to react to even without FlexSim
running; the two channels are otherwise kept deliberately separate for
the dashboard's FlexSim-vs-real comparison.

By default this runs one scheduling cycle and exits: it's a
demonstration of the wiring, not a service. Nothing else in this
repository re-schedules on its own, so the dashboard's "RMS Scheduling
Decision" panel only updates when this script (or something else
posting to POST /api/v1/rms/decision) runs, and only *changes* if the
underlying telemetry it's reading is actually changing; a decision
isn't produced on a timer unless you ask for one with --loop. It shows
the current wiring, not a claim that the RMS is deployable: most of
adapters/ (ros2/, plc/, external/) is still interface-only (see
rms/README.md).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
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


def run_once(orchestrator: RmsOrchestrator) -> int:
    """Sync fleet/workstation state, schedule and dispatch one mission,
    print the result, and post it to the dashboard. Returns a process
    exit code (0 success, 1 failure) so callers can use it either way.
    """
    label = "Real/ROS2" if getattr(orchestrator.adapter, "channel", "flexsim") == "real" else "FlexSim"

    try:
        robots = orchestrator.sync_fleet()
    except IntegrationError as exc:
        print(f"[{label}] Could not reach bridge: {exc}")
        print("Start it first: bridge\\start.bat (see the root README).")
        print("\nRMS live integration: FAIL")
        return 1

    if not robots:
        print(f"[{label}] Bridge is reachable, but no robot telemetry has arrived yet.")
        if label == "Real/ROS2":
            print("Start the mock fleet with bridge\\start_ros2_sim.bat, then rerun this.")
        else:
            print("Start FlexSim, or rerun with --source real to use the mock fleet instead.")
        print("\nRMS live integration: FAIL")
        return 1

    print(f"[{label}] {len(robots)} robot(s) received\n")
    for robot in robots:
        print(f"{robot.robot_id:<12} {robot.status.value.upper():<10} battery={robot.battery_pct:.0f}%")

    try:
        workstations = orchestrator.sync_workstations()
    except IntegrationError:
        workstations = []
    if workstations:
        print(f"\n[{label}] {len(workstations)} workstation(s)/queue(s) received\n")
        for ws in workstations:
            print(f"{ws.workstation_id:<12} {ws.status.value.upper():<10} queue={ws.queue_length}")
        # Send each cycle toward whichever queue currently has the
        # biggest backlog, so a --loop run visibly reacts to changing
        # telemetry instead of always scheduling toward the same queue.
        destination = max(workstations, key=lambda w: w.queue_length).workstation_id
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

    post_decision_to_dashboard(orchestrator.adapter.bridge_url, mission_type, source, result, breakdown)
    print(f"\nPosted decision to {orchestrator.adapter.bridge_url}/dashboard")

    print("\nRMS live integration: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--loop",
        action="store_true",
        help="keep scheduling repeatedly instead of running once (Ctrl+C to stop)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="seconds between cycles in --loop mode (default: 5)",
    )
    parser.add_argument(
        "--source",
        choices=("flexsim", "real"),
        default="flexsim",
        help=(
            "which telemetry channel to schedule against: 'flexsim' (default, needs a "
            "running FlexSim model) or 'real' (the mock fleet from start_ros2_sim.bat)"
        ),
    )
    args = parser.parse_args()

    adapter = FlexSimAdapter(channel=args.source)
    # One orchestrator reused across cycles in --loop mode, so
    # ResourceScheduler's per-robot assignment counts (utilization_cost)
    # keep accumulating across cycles instead of resetting each time.
    orchestrator = RmsOrchestrator(adapter)

    if not args.loop:
        return run_once(orchestrator)

    print(f"Looping every {args.interval:.0f}s. Press Ctrl+C to stop.\n")
    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"=== Cycle {cycle} ===")
            run_once(orchestrator)
            print()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
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
