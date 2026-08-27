# rms

Scaffolding for the Robot Management System (RMS) core described in the
root README's
["Vision: toward a Robot Management System (RMS)"](../README.md#vision-toward-a-robot-management-system-rms)
section.

**Status: Phase 3 scaffolding.** Nothing here is wired into the running
`bridge/` service yet, and none of it is exercised by tests. It exists
so the target domain model and module boundaries are visible in code,
not just in a diagram, before the actual scheduling logic is built.

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
└── workstations/      Workstation Manager: station availability, queues,
                       readiness.
```

Every manager module currently exposes only its intended interface
(method signatures with docstrings, dataclasses for its inputs/outputs).
Method bodies raise `NotImplementedError` on purpose: this is a shape to
build against, not a working scheduler.

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
