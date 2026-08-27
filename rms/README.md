# rms

Scaffolding for the Robot Management System (RMS) core described in the
root README's
["Vision: toward a Robot Management System (RMS)"](../README.md#vision-toward-a-robot-management-system-rms)
section.

**Status: Phase 3, in progress.** `domain/`, `fleet/`, `workstations/`,
`tasks/`, `missions/`, and `scheduler/` have real, unit-tested
implementations now (see `../tests/`): an in-memory Mission -> Task ->
robot-assignment flow with a deterministic nearest-available scheduler.
`traffic/` is still interface only, and the scheduler's `queue_cost`
and `utilization_cost` terms are placeholders (always 0) until it's
wired in. None of this is connected to the running `bridge/` service
yet.

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

`missions/`, `tasks/`, `fleet/`, `workstations/`, and `scheduler/` have
working, in-memory, unit-tested implementations. `traffic/` still only
exposes its intended interface (method signatures with docstrings);
method bodies there raise `NotImplementedError` on purpose, as a shape
to build against.

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
