# bridge

The Python middleware at the center of this project: a FastAPI service
that receives telemetry from FlexSim, exposes it over REST, serves a live
comparison dashboard, and accepts commands FlexSim can poll and
acknowledge, structured so a ROS2 layer can be added later without
rewriting the API.

```text
FlexSim
    ↕ HTTP/JSON
bridge (this project)
    ↕
ROS2 (future phase)
```

See the [repository root README](../README.md) for the full project
overview, screenshots, and how this fits together with `flexsim-model/`
and `ros2_sim/`.

## What this service does

- Receives simulation telemetry from FlexSim (`POST /api/v1/telemetry`),
  validated with Pydantic, held in thread-safe in-memory storage
  (`GET /api/v1/state`, `POST /api/v1/state/reset`).
- Receives telemetry from a separate "real/ROS2-side" environment
  (`POST /api/v1/real/telemetry`, `GET /api/v1/real/state`): a distinct
  channel from FlexSim's, so the two can be compared rather than merged.
- Lets that real-environment fleet size be controlled live from the
  dashboard (`GET`/`POST /api/v1/real/config`) without restarting the
  simulator process.
- Serves a live, auto-refreshing dashboard (`GET /dashboard`): queue
  levels, processor utilization, throughput counters, robot state, and a
  side-by-side FlexSim-vs-real comparison chart. Pure HTML/CSS/JS, no
  external dependencies, no build step.
- Accepts commands for FlexSim (`POST /api/v1/commands`), lets FlexSim
  poll for the next pending one (`GET /api/v1/commands/next`), and
  records execution results (`POST /api/v1/commands/{id}/ack`).
- Logs telemetry, commands, acknowledgments, and validation errors to
  console and `logs/bridge.log`.

## Architecture

```text
app/
├── main.py              FastAPI app wiring, startup logging, error handling
├── api/                  HTTP endpoints (thin: validation + delegation only)
│   ├── health.py
│   ├── telemetry.py       POST /telemetry, GET /state, POST /state/reset
│   ├── commands.py
│   ├── real_environment.py   POST/GET /real/telemetry, /real/state, /real/config
│   └── dashboard.py        GET /dashboard (self-contained HTML/JS/canvas)
├── models/                Pydantic schemas (request/response contracts)
│   ├── telemetry.py
│   ├── command.py
│   ├── real_environment.py
│   └── real_environment_config.py
├── services/             In-memory state, isolated behind get/set interfaces
│   ├── state_store.py
│   ├── command_store.py
│   ├── real_environment_store.py
│   └── real_environment_config_store.py
└── core/
    ├── config.py           Settings (host, port, log paths)
    └── logging.py           Logging setup
```

Every `services/*_store.py` is the only place that knows its data lives
in memory. A later persistent-storage implementation (SQLite, etc.) can
implement the same interface without touching `api/`.

## Installation & running

Requires Python 3.11+ on Windows.

**No command line needed:** double-click `start.bat` in this folder. It
sets up `.venv` on first run, starts the server, and opens the dashboard
in your browser automatically.

**Or from PowerShell:**

```powershell
cd bridge
.\run.ps1
```

`run.ps1` (what `start.bat` calls) creates `.venv` if missing,
installs/updates dependencies, and starts the server on
`http://127.0.0.1:8000`.

## Testing

```powershell
.venv\Scripts\Activate.ps1
pytest
```

24 tests covering health, telemetry validation, state retrieval/reset,
commands (create/poll/ack/empty-queue), the real-environment +
fleet-config endpoints, and the RMS decision endpoint.

## Swagger

```text
http://127.0.0.1:8000/docs
```

## Live dashboard

```text
http://127.0.0.1:8000/dashboard
```

- Auto-refreshes every second.
- **Queue Levels**: solid bar = current value, faint bar = peak value
  since the last Reset (so a brief spike doesn't vanish before you see it).
- **Processors**: live state + computed utilization.
- **Entry/Exit Points**: throughput counters per point, as live bar charts.
- **Robots / AGVs**: position, speed, state, battery.
- **Digital Twin Comparison**: FlexSim's queues plotted next to the
  real/ROS2-side environment's queues, a **fleet-size control** (change
  the number of real-environment robots and watch the result live, no
  restart needed), a **backlog** metric (`Queue1 + Queue2` on the real
  side) with a smoothed growing/shrinking/stable trend indicator, and a
  table of the real-side robots.
- **RMS Scheduling Decision**: the selected robot, score, and full cost
  breakdown (travel/battery/queue/utilization/priority) from the latest
  `rms/` orchestration run, read-only (the bridge stores it but never
  acts on it). See `../rms/README.md`.
- Light/dark theme toggle (persisted in the browser).
- **Reset** clears both FlexSim's and the real environment's stored
  telemetry. Useful before a fresh run, though independent processes
  (FlexSim, `ros2_sim/simulator.py`) keep running regardless: Reset only
  clears what the bridge remembers, by design (see the root README's
  digital twin note on why that's correct behavior).

## API reference

| Method | Path                          | Purpose                                        |
|--------|-------------------------------|-------------------------------------------------|
| GET    | `/health`                     | Liveness check                                   |
| GET    | `/dashboard`                  | Live dashboard (HTML)                            |
| POST   | `/api/v1/telemetry`           | Submit FlexSim telemetry                         |
| GET    | `/api/v1/state`                | Read latest FlexSim telemetry                    |
| POST   | `/api/v1/state/reset`          | Clear stored FlexSim telemetry                   |
| POST   | `/api/v1/real/telemetry`       | Submit real/ROS2-side telemetry                  |
| GET    | `/api/v1/real/state`           | Read latest real-side telemetry                  |
| POST   | `/api/v1/real/state/reset`     | Clear stored real-side telemetry                 |
| GET    | `/api/v1/real/config`          | Read desired real-environment fleet size         |
| POST   | `/api/v1/real/config`          | Set desired real-environment fleet size          |
| POST   | `/api/v1/rms/decision`         | Post an RMS scheduling decision (read-only display)|
| GET    | `/api/v1/rms/decision`         | Read the latest RMS scheduling decision          |
| POST   | `/api/v1/rms/decision/reset`   | Clear the stored RMS decision                    |
| POST   | `/api/v1/commands`              | Queue a command for FlexSim                      |
| GET    | `/api/v1/commands/next`         | Poll the oldest pending command                  |
| POST   | `/api/v1/commands/{id}/ack`     | Report command execution result                  |

### curl

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/api/v1/telemetry -H "Content-Type: application/json" -d '{
  "simulation_time": 120.5, "model_status": "running",
  "queues": {"Queue1": 8}, "processors": {}, "robots": {}
}'
curl http://127.0.0.1:8000/api/v1/state
curl -X POST http://127.0.0.1:8000/api/v1/real/config -H "Content-Type: application/json" -d '{"robot_count": 3}'
```

### PowerShell

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/state
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/real/config -Method Post `
    -Body (@{robot_count = 3} | ConvertTo-Json) -ContentType "application/json"
```

## FlexSim integration

See [`flexsim/README.md`](flexsim/README.md) for the general integration
guide, and (this is the one to actually follow)
[`flexsim/verified_scripts/README.md`](flexsim/verified_scripts/README.md)
plus [`flexsim/verified_scripts/final_telemetry_custom_code.fsc`](flexsim/verified_scripts/final_telemetry_custom_code.fsc)
for the exact, tested FlexScript running against `DG-FT-01.fsm` today,
including every gotcha discovered along the way (case-sensitive
`Http.Method` enum, nested object paths, Model Parameter type/bounds
quirks, Photo Eye trigger throughput counting).

## The real/ROS2-side environment

See [`ros2_sim/README.md`](ros2_sim/README.md). Short version: it's
not real ROS2 (no ROS2 dependencies installed, that's Phase 2). It's a
small physics-based mock robot fleet with realistic speed ramping and a
steady tote arrival rate, so the "how many robots before backlog stops
growing" question has a real, testable answer today, and Phase 2 can drop
in a real ROS2 node behind the same `/api/v1/real/telemetry` contract
without changing the bridge or dashboard.

## Phase 2: ROS2 (not implemented)

```text
FlexSim Telemetry → bridge → ROS2 Topics
                               /warehouse/state
                               /amr/state
                               /flexsim/events

ROS2 Commands → bridge → FlexSim
```

No ROS2 dependencies are installed. When Phase 2 begins, an `app/ros/`
package would read/write the existing `state_store`/`command_store`/
`real_environment_store` services without changing the HTTP API, and
would take over from `ros2_sim/simulator.py` as the source of
`/api/v1/real/telemetry` data.

## Assumptions

- FlexSim 2027 provides HTTP request capability via the `Http.Request`/
  `Http.Response` FlexScript classes (confirmed against a running model,
  not assumed from documentation).
- Single FlexSim model instance, single bridge instance: no
  multi-tenant routing.
- Localhost-only; no authentication/TLS.
- Windows Firewall must allow FlexSim's outbound traffic to localhost
  (see `flexsim/verified_scripts/README.md`), a machine-specific setup
  step, not something the bridge can work around on its own.
