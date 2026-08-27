# adapters

Scaffolding for the Device & Integration Layer described in the root
README's
["Vision: toward a Robot Management System (RMS)"](../README.md#vision-toward-a-robot-management-system-rms)
section: the boundary that keeps `rms/` free of FlexScript, ROS message,
PLC protocol, or WMS-specific details.

**Status: scaffolding.** Nothing here is wired into `rms/` or `bridge/`
yet.

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
