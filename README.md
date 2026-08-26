# flexsim-digital-twin

Local integration project connecting a FlexSim 2027 model to a Python
digital-twin bridge, with ROS 2 reserved as a future phase.

```text
FlexSim (flexsim-model/)
    ↕ HTTP/JSON
Python Bridge (flexsim-digital-twin-bridge/)
    ↕
ROS 2 — future phase
```

## Repository layout

```text
flexsim-digital-twin/
├── flexsim-model/                 FlexSim 2027 model files
│   └── DG-FT-01.fsm
│
└── flexsim-digital-twin-bridge/   Python middleware (FastAPI bridge)
    ├── app/                        Application source (see its own README)
    ├── flexsim/                    FlexSim-side integration docs & pseudo-code
    ├── tests/                      pytest suite
    ├── run.ps1                     one-command setup + launch (Windows)
    └── README.md                   full bridge documentation
```

## Where to start

- To run the middleware service: see
  [`flexsim-digital-twin-bridge/README.md`](flexsim-digital-twin-bridge/README.md)
  for setup, running, testing, and the full API reference.
- To connect an actual FlexSim model to the bridge: see
  [`flexsim-digital-twin-bridge/flexsim/README.md`](flexsim-digital-twin-bridge/flexsim/README.md).
- The FlexSim model itself lives in [`flexsim-model/`](flexsim-model/).

## Status

**Phase 1 (complete and verified live against `DG-FT-01.fsm`):** FlexSim ↔
Python bridge over local HTTP/JSON, with in-memory state and command
queues, a live auto-refreshing dashboard, and a Process Flow loop inside
FlexSim that continuously POSTs real queue/processor/throughput data
every 5 simulated seconds. See
[`flexsim-digital-twin-bridge/README.md`](flexsim-digital-twin-bridge/README.md)
for what's working end to end and
[`flexsim-digital-twin-bridge/flexsim/verified_scripts/`](flexsim-digital-twin-bridge/flexsim/verified_scripts/)
for the exact FlexScript used.

**Phase 2 (not started):** ROS 2 topic bridging, reserved for a future
`app/ros/` package inside the bridge project.
