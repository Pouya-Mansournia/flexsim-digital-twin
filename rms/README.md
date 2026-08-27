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
a simple load-balancing signal between otherwise-equal robots. `traffic/`
is still interface only; congestion-aware scheduling is the next step
beyond this.

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
