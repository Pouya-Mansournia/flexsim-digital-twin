# rms

Scaffolding for the Robot Management System (RMS) core described in the
root README's
["Vision: toward a Robot Management System (RMS)"](../README.md#vision-toward-a-robot-management-system-rms)
section.

**Status: Phase 3, first closed loop working.** `domain/`, `fleet/`,
`workstations/`, `tasks/`, `missions/`, and `scheduler/` have real,
unit-tested implementations. `services/orchestrator.py` ties them
together with `adapters/flexsim/` into a full, verified, live
end-to-end path against the real `bridge/`:

```text
FlexSim -> bridge -> FlexSimAdapter.get_robots() -> FleetManager
    -> MissionManager.create_mission() -> TaskManager
    -> ResourceScheduler -> selected Robot
    -> FlexSimAdapter.send_command() -> bridge /api/v1/commands
    -> command_id
```

Run it yourself with `bridge/` up:
[`examples/live_flexsim_rms_demo.py`](../examples/live_flexsim_rms_demo.py).

`queue_cost` and `utilization_cost` are wired now too:
`FlexSimAdapter.get_workstations()` maps FlexSim's queues into
`WorkstationManager`, so `queue_cost` reflects a destination's real
backlog (0 if the destination isn't a known workstation yet), and the
scheduler tracks its own per-run assignment counts as `utilization_cost`,
a simple load-balancing signal between otherwise-equal robots.

`ResourceScheduler.assign()` also now refuses outright, with
`WorkstationUnavailableError`, when a task's destination is a known
workstation that can't accept new work (`BLOCKED`/`FAULT`/`STARVED`/
`OFFLINE`; an unknown destination stays permissive, same default as
`queue_cost`). Verified live: stopping FlexSim (`model_status: "stopped"`
in telemetry) marks its queues `OFFLINE`, and the orchestrator refuses
to dispatch there instead of sending a robot toward a queue that isn't
moving.

`traffic/` is now implemented too: an in-memory `TrafficManager` for
zone reservations (`reserve_zone`/`release_zone`, idempotent for the
holder, refused for anyone else) and a simple congestion estimate that
rises with contested reservations. It isn't wired into the scheduler
yet (no zone concept exists on `Task`/`Robot` today) — that's the next
step for `queue_cost`'s sibling, a `zone_cost` term.

Every RMS run also posts its decision to the live dashboard: see
[Dashboard integration](#dashboard-integration) below.

### Dashboard integration

`examples/live_flexsim_rms_demo.py` posts each decision (best-effort) to
`bridge/`'s new `POST /api/v1/rms/decision` endpoint after dispatching
it, and `bridge/`'s dashboard (`http://127.0.0.1:8000/dashboard`) has an
"RMS Scheduling Decision" panel that polls
`GET /api/v1/rms/decision` every second and renders the selected robot,
score, and full cost breakdown. This is a read-only observability
channel: the bridge stores the latest decision but never acts on it.
See `bridge/app/models/rms_decision.py`, `bridge/app/api/rms_decision.py`,
and `bridge/tests/test_rms_decision.py`.

## Layout

```text
rms/
├── domain/         Shared dataclasses and enums: Mission, Task, Robot,
│                     Workstation, and their states.
├── missions/        Mission Manager: turns external requests into
│                     missions.
├── tasks/           Task Manager: decomposes missions into tasks and
│                     tracks their lifecycle.
├── scheduler/        Resource Scheduler: assigns tasks to robots and
│                     workstations.
├── fleet/            Fleet Manager: robot availability, capability,
│                     battery, state.
├── traffic/          Traffic Manager: zones, congestion, coordination.
├── workstations/      Workstation Manager: station availability, queues,
│                     readiness.
└── services/          RmsOrchestrator: coordinates the managers above
                       into one end-to-end scheduling flow.
```

See [`../examples/live_flexsim_rms_demo.py`](../examples/live_flexsim_rms_demo.py)
for the orchestrator run against a real `bridge/`, and
[`../tests/test_orchestrator.py`](../tests/test_orchestrator.py) for it
run against a fake adapter (no bridge needed).

`missions/`, `tasks/`, `fleet/`, `workstations/`, `scheduler/`, and
`services/` (the orchestrator) have working, unit-tested
implementations. `traffic/` still only exposes its intended interface
(method signatures with docstrings); method bodies there raise
`NotImplementedError` on purpose, as a shape to build against.

`services/orchestrator.py` is the only file in `rms/` that talks to an
adapter, and it does so only through two `typing.Protocol`s
(`RobotSource`, `CommandSender`), never by importing `adapters.flexsim`
directly. That keeps the dependency direction `adapters -> rms`, not
the reverse: `rms/` stays testable with a fake adapter (see
`../tests/test_orchestrator.py`) and swappable to `adapters/ros2/`
later without changing this file.

## Why this exists before the logic does

Each manager's dependencies are meant to mirror the architecture
diagram in the root README (`Mission Manager -> Task Manager -> Resource
Scheduler <-> {Fleet, Traffic, Workstation} Manager`). Having the module
boundaries in place first is what lets `adapters/` be built against a
stable interface, and lets FlexSim stay the validation environment for
whatever scheduling logic eventually lands in `scheduler/`.

## Next steps

See Phase 3 in the root README's roadmap: a domain model (this
directory), an initial deterministic scheduling policy in
`scheduler/resource_scheduler.py`, and a mission/task state machine in
`tasks/manager.py`, instrumented with the KPIs listed there.
