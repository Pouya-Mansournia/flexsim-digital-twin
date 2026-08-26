![Digital Twin: FlexSim + ROS2](assets/digital-twin-overview.png)

# FlexSim Digital Twin

A local, working digital-twin integration: a real **FlexSim 2027** warehouse
model, a **Python bridge** that exposes its live state over HTTP/JSON, a
**live dashboard**, and a physics-based **mock robot fleet** standing in
for a future ROS2-connected real system — compared side by side, so
operational questions ("how many robots before this queue backs up?")
have a testable answer today.

## Quick start — no coding experience needed

Two files, two double-clicks, no commands to type.

1. **Install Python** (only once, if you don't have it):
   [python.org/downloads](https://www.python.org/downloads/) → download →
   run the installer → check **"Add python.exe to PATH"** → Install.
2. Download or `git clone` this repository, then open the `bridge` folder.
3. **Double-click `start.bat`.**
   A black window opens, sets things up the first time (takes a minute),
   starts the server, and your browser opens automatically to the live
   dashboard. Leave that black window open — closing it stops the server.
4. *(Optional, to see the "real robots" side of the comparison)* **also
   double-click `start_ros2_sim.bat`** — a second window opens showing a
   simulated robot fleet moving totes, and the dashboard's "Digital Twin
   Comparison" section comes alive. Use the number box on the dashboard
   to change how many robots there are and watch the effect immediately.

That's it — `http://127.0.0.1:8000/dashboard` is now live in your browser.
To connect the actual FlexSim 2027 model instead of just the mock
simulation, see [Connecting FlexSim](#connecting-flexsim) below.

<details>
<summary><b>Quick start for developers (command line)</b></summary>

```powershell
git clone https://github.com/Pouya-Mansournia/flexsim-digital-twin.git
cd flexsim-digital-twin\bridge
.\run.ps1
```

This creates a `.venv`, installs dependencies, and starts the bridge on
`http://127.0.0.1:8000`. In a second terminal, to run the mock real
environment too:

```powershell
cd flexsim-digital-twin\bridge
.venv\Scripts\python.exe ros2_sim\simulator.py --robots 2
```

Run the test suite:

```powershell
cd flexsim-digital-twin\bridge
.venv\Scripts\Activate.ps1
pytest
```

</details>

## What this is

```text
FlexSim 2027 (simulation)
        ↕ HTTP/JSON
     bridge/  (FastAPI + live dashboard)
        ↕ HTTP/JSON
ros2_sim/  (mock "real" robot fleet today — real ROS2 in Phase 2)
```

- **FlexSim side**: a Process Flow loop inside the model POSTs real queue
  contents, processor utilization, robot position/speed, and throughput
  counters to the bridge every 5 simulated seconds — no manual steps once
  wired up.
- **Bridge**: a small FastAPI service that stores the latest telemetry
  from *both* sides (FlexSim and the "real" environment) independently,
  serves them over REST, and renders a live comparison dashboard.
- **ros2_sim**: a standalone Python simulation of a robot fleet with
  realistic acceleration/deceleration, a steady tote arrival rate, and a
  fleet size controllable live from the dashboard — so you can literally
  watch backlog grow or drain as you add/remove robots, before any real
  hardware or ROS2 stack is involved. Phase 2 swaps this for a real ROS2
  node behind the exact same API, with no bridge changes required.

![FlexSim model — Inbound and Outbound sections](assets/flexsim-3d-model-view.png)

<sub>The actual FlexSim 2027 model (`flexsim-model/DG-FT-01.fsm`) this project is built against — an Inbound sortation cell feeding an Outbound put-wall/rack area.</sub>

## Repository layout

```text
flexsim-digital-twin/
├── flexsim-model/            FlexSim 2027 model
│   └── DG-FT-01.fsm
│
├── bridge/                    Python middleware (FastAPI + dashboard)
│   ├── app/                    Application source
│   │   ├── api/                  telemetry, real-environment, commands, dashboard
│   │   ├── models/                Pydantic schemas
│   │   ├── services/              in-memory state stores
│   │   └── core/                   config, logging
│   ├── flexsim/                 FlexSim-side integration docs
│   │   └── verified_scripts/       tested FlexScript + every gotcha found
│   ├── ros2_sim/                 mock real-environment robot fleet
│   ├── tests/                    pytest suite (19 tests)
│   ├── start.bat                  double-click to set up + run (Windows)
│   ├── start_ros2_sim.bat          double-click to run the mock fleet
│   ├── run.ps1                     what start.bat calls under the hood
│   └── README.md                   full bridge documentation
│
├── assets/                    Images used in this README
├── LICENSE
└── README.md                  you are here
```

## The dashboard

The single most useful entry point once everything is running:
`http://127.0.0.1:8000/dashboard`.

- **FlexSim section**: queue levels (current + peak), processor
  state/utilization, entry/exit throughput counters, robot position/speed.
- **Digital Twin Comparison section**: FlexSim's queues plotted next to
  the real/ROS2-side environment's queues, a **live fleet-size control**
  for the real environment, a **backlog** metric with a smoothed trend
  indicator, and the real side's robot table.
- Light/dark theme, a Reset button, auto-refresh every second — no
  external JS/CSS dependencies, it's a single self-contained HTML page
  served by FastAPI.

## Connecting FlexSim

`start.bat`/`.\run.ps1` give you the bridge and the mock real-environment
side — no FlexSim installation required for that. To also see live
telemetry from the actual model:

1. Install FlexSim 2027 and open `flexsim-model\DG-FT-01.fsm`.
2. Follow [`bridge/flexsim/verified_scripts/README.md`](bridge/flexsim/verified_scripts/README.md)
   — it has the exact, tested FlexScript
   ([`final_telemetry_custom_code.fsc`](bridge/flexsim/verified_scripts/final_telemetry_custom_code.fsc))
   to paste in, and every gotcha discovered getting it working (a
   Windows Firewall rule that silently blocks FlexSim, a case-sensitive
   API that fails without any visible error, object paths that aren't
   where you'd expect).
3. Run the model — its queues, processors, and robots start appearing on
   the dashboard next to the mock real environment.

## What we actually learned building this

This project's value isn't just the code — it's the trail of concrete,
verified findings from getting a real FlexSim 2027 model talking to
external software, none of which were obvious from the documentation
alone:

- FlexSim 2027 has a real `Http.Request`/`Http.Response` FlexScript API,
  but the method enum (`Http.Method.Post`) is case-sensitive in a way
  that fails *silently* — a wrong-case value compiles, runs, and quietly
  sends a `GET` instead of a `POST`, with no error anywhere in FlexSim.
- Windows Firewall can block FlexSim's outbound traffic — even to
  `127.0.0.1` — with zero error surfaced in FlexSim.
- `Model.find("ObjectName")` fails silently (returns an unusable node,
  not an error) if the object is nested inside a group/plane rather than
  at the model root — four of this model's most important queues
  (`Queue1`–`Queue4`) were nested this way, so telemetry silently read 0
  for them until this was found by checking the object's real path in
  FlexSim's status bar.
- Model Parameters used as counters/accumulators need `Continuous` type
  and explicit, wide bounds — `Integer` type silently rounds fractional
  values, and the default `Lower Bound = 1` silently clamps any attempt
  to reset a value to `0`.
- FlexSim has no single built-in "items in/out" counter for an arbitrary
  point in a line — this project wires it up using existing Photo Eye
  objects' `On Cover` trigger incrementing a named Model Parameter.

The full, detailed trail — including the exact FlexScript that works and
why — is in
[`bridge/flexsim/verified_scripts/README.md`](bridge/flexsim/verified_scripts/README.md).

## A finding from the model itself

Running this integration surfaced a real bottleneck in `DG-FT-01.fsm`,
not just a software one: `Queue1` (Inbound) was observed with 172 totes
in / 35 out, 137 sitting in the queue, and an average wait time of over
12 minutes — a genuine capacity mismatch downstream, visible precisely
*because* the telemetry was flowing correctly. That's the actual point of
a digital twin: it surfaces real problems, not just simulated ones.

## Roadmap

**Phase 1 — done, working end to end:**
- FlexSim ↔ bridge over local HTTP/JSON.
- Live dashboard with FlexSim-vs-real comparison.
- Mock real-environment robot fleet with live-configurable size.
- Command interface (`POST /api/v1/commands`, poll, ack) — implemented
  and unit-tested; not yet exercised against a real FlexSim consumer.

**Phase 2 — not started:**
- A ROS2 node replacing `ros2_sim/simulator.py`, publishing to real
  topics (`/warehouse/state`, `/amr/state`, `/flexsim/events`) and
  consuming commands — behind the same `/api/v1/real/*` API, no bridge
  changes required.
- FlexSim executing commands the bridge hands it (the reverse direction:
  bridge → FlexSim), currently implemented server-side but not yet
  wired into the model.

## Contributing

Issues and PRs welcome. If you're extending this to a different FlexSim
model: don't assume object paths — click each object once in FlexSim and
read the status bar for its real path before wiring it into the Custom
Code block (see `bridge/flexsim/verified_scripts/README.md` for why).

## License

[MIT](LICENSE)
