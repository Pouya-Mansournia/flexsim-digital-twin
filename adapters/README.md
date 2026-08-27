# adapters

Scaffolding for the Device & Integration Layer described in the root
README's
["Vision: toward a Robot Management System (RMS)"](../README.md#vision-toward-a-robot-management-system-rms)
section: the boundary that keeps `rms/` free of FlexScript, ROS message,
PLC protocol, or WMS-specific details.

**Status:** `flexsim/` has a working implementation, talking to the
real, already-running `bridge/` REST API over the standard library's
`urllib` (no extra dependency): `get_robots()` reads
`GET /api/v1/state` and maps it into `rms.domain.Robot` objects,
`send_command()` posts to `POST /api/v1/commands`. See
`../tests/test_flexsim_adapter.py`.

It's also wired end to end: `rms/services/orchestrator.py` uses a
`FlexSimAdapter` to sync `FleetManager`, run the scheduler, and dispatch
a command, verified live against a running `bridge/` in
[`../examples/live_flexsim_rms_demo.py`](../examples/live_flexsim_rms_demo.py).
`ros2/`, `plc/`, and `external/` are still interfaces only.

## Layout

```text
adapters/
├── flexsim/    Talks to bridge/'s existing /api/v1/telemetry and
│                 /api/v1/commands endpoints on behalf of the RMS
│                 (Digital Twin Adapter in the architecture diagram).
├── ros2/        Future: talks to a real ROS 2 fleet (Robot Adapter),
│                 replacing bridge/ros2_sim/simulator.py (Phase 4).
├── plc/         Future: workstation/PLC integration (Workstation
│                 Adapter), OPC UA or vendor-specific (Phase 6).
└── external/     Future: WMS/ERP/OMS/MES integration (External
                   Interface), behind a stable API contract (Phase 6).
```

Each adapter exposes the same shape regardless of what's behind it, so
the RMS core can be developed and tested against `flexsim/` (talking to
the existing bridge, which is already working) long before `ros2/` or
`plc/` have anything real to connect to.
