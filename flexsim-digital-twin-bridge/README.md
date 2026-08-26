# flexsim-digital-twin-bridge

A local integration bridge connecting FlexSim 2027 to a Python middleware
service over HTTP/JSON, structured so ROS 2 can be added later without
rewriting the API layer.

```text
FlexSim
    ↕ HTTP/JSON
Python Digital Twin Bridge (this project)
    ↕
ROS 2 — future phase
```

## What this project is

**Phase 1** (this repository, current state — implemented and verified
against a real FlexSim 2027 model): a FastAPI service that:

- Receives simulation telemetry from FlexSim (`POST /api/v1/telemetry`)
  and validates it with Pydantic.
- Holds the latest telemetry snapshot in thread-safe in-memory storage,
  exposed via `GET /api/v1/state`.
- Lets you clear that snapshot on demand (`POST /api/v1/state/reset`) —
  useful when re-running the model and you want to confirm you're seeing
  fresh data, not a stale value from a previous run.
- Serves a live, auto-refreshing dashboard (`GET /dashboard`) that charts
  queue levels, processor state/utilization, and robot data as it arrives
  — no external JS/CSS dependencies, just static HTML served by FastAPI.
- Accepts commands intended for FlexSim (`POST /api/v1/commands`), lets
  FlexSim poll for the next pending one (`GET /api/v1/commands/next`),
  and records execution results (`POST /api/v1/commands/{id}/ack`).
- Logs all telemetry, commands, acknowledgments, and validation errors to
  console and to `logs/bridge.log`.

**Phase 2** (not implemented yet): a ROS 2 layer under `app/ros/` that
republishes bridge state onto ROS 2 topics (e.g. `/warehouse/state`,
`/amr/state`, `/flexsim/events`) and routes ROS 2 commands back through
the bridge into FlexSim. See "Phase 2: ROS 2" below for the intended
design.

## Architecture

```text
app/
├── main.py            FastAPI app wiring, startup logging, error handling
├── api/                HTTP endpoints (thin — validation + delegation only)
│   ├── health.py
│   ├── telemetry.py     POST /telemetry, GET /state, POST /state/reset
│   ├── commands.py
│   └── dashboard.py      GET /dashboard (self-contained HTML/JS/canvas)
├── models/              Pydantic schemas (request/response contracts)
│   ├── telemetry.py
│   └── command.py
├── services/           In-memory state, isolated behind get/set interfaces
│   ├── state_store.py
│   └── command_store.py
└── core/
    ├── config.py        Settings (host, port, log paths)
    └── logging.py        Logging setup
```

The `services/` layer is the only place that knows storage is in-memory.
A later persistent-storage implementation (e.g. SQLite) can implement the
same `state_store` / `command_store` interfaces without touching `api/`.

## Installation

Requires Python 3.11+ on Windows.

```powershell
git clone <this-repo>
cd flexsim-digital-twin-bridge
.\run.ps1
```

`run.ps1` creates `.venv` if it doesn't exist, installs/updates
dependencies from `requirements.txt`, and starts the server.

## Running

```powershell
.\run.ps1
```

The API starts on `http://127.0.0.1:8000`.

## Testing

```powershell
.venv\Scripts\Activate.ps1
pytest
```

## Swagger / interactive docs

Once the server is running, open:

```text
http://127.0.0.1:8000/docs
```

to manually exercise every endpoint from the browser.

## Live dashboard

```text
http://127.0.0.1:8000/dashboard
```

Auto-refreshes every second by polling `GET /api/v1/state`. Shows:

- Simulation time, model status, and when the last telemetry arrived.
- **Baskets In / Baskets Out** — cumulative throughput counters (see
  "Counting throughput" below).
- A bar chart of queue levels. Each bar shows both the **current** live
  value (solid) and the **peak** value seen since the last Reset (faint,
  persists) — so a brief spike (an item arrives and immediately leaves a
  queue) stays visible instead of the bar collapsing back to 0 before
  anyone can see it happened.
- A table of processor state/utilization.
- A table of robot/AGV position, speed, state, and battery.

The **Reset** button calls `POST /api/v1/state/reset` and clears the
dashboard's local peak-tracking, so you get a clean slate before the next
model run.

## API reference

| Method | Path                              | Purpose                              |
|--------|-----------------------------------|---------------------------------------|
| GET    | `/health`                         | Liveness check                        |
| GET    | `/dashboard`                      | Live auto-refreshing dashboard (HTML) |
| POST   | `/api/v1/telemetry`               | Submit a telemetry snapshot           |
| GET    | `/api/v1/state`                   | Read the latest telemetry snapshot    |
| POST   | `/api/v1/state/reset`             | Clear the stored telemetry snapshot   |
| POST   | `/api/v1/commands`                | Queue a command for FlexSim           |
| GET    | `/api/v1/commands/next`           | Poll the oldest pending command       |
| POST   | `/api/v1/commands/{id}/ack`       | Report command execution result       |

### Example: curl

```bash
# Health check
curl http://127.0.0.1:8000/health

# Submit telemetry
curl -X POST http://127.0.0.1:8000/api/v1/telemetry \
  -H "Content-Type: application/json" \
  -d '{
        "simulation_time": 120.5,
        "model_status": "running",
        "queues": {"Queue1": 8, "Queue2": 3},
        "processors": {"Processor1": {"state": "processing", "utilization": 0.82}},
        "robots": {"AGV1": {"x": 10.2, "y": 4.1, "speed": 1.2, "state": "moving", "battery": 87}}
      }'

# Read current state
curl http://127.0.0.1:8000/api/v1/state

# Clear stored telemetry
curl -X POST http://127.0.0.1:8000/api/v1/state/reset

# Queue a command
curl -X POST http://127.0.0.1:8000/api/v1/commands \
  -H "Content-Type: application/json" \
  -d '{"target": "AGV1", "command": "stop", "parameters": {}}'

# Poll the next pending command
curl http://127.0.0.1:8000/api/v1/commands/next
```

### Example: PowerShell (`Invoke-RestMethod`)

```powershell
# Health check
Invoke-RestMethod -Uri http://127.0.0.1:8000/health

# Submit telemetry
$telemetry = @{
    simulation_time = 120.5
    model_status    = "running"
    queues          = @{ Queue1 = 8; Queue2 = 3 }
    processors      = @{ Processor1 = @{ state = "processing"; utilization = 0.82 } }
    robots          = @{ AGV1 = @{ x = 10.2; y = 4.1; speed = 1.2; state = "moving"; battery = 87 } }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/telemetry `
    -Method Post -Body $telemetry -ContentType "application/json"

# Read current state
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/state

# Clear stored telemetry
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/state/reset -Method Post

# Queue a command
$command = @{ target = "AGV1"; command = "stop"; parameters = @{} } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/commands `
    -Method Post -Body $command -ContentType "application/json"

# Poll the next pending command
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/commands/next
```

## FlexSim integration

See [`flexsim/README.md`](flexsim/README.md) for the general integration
guide (conceptual pseudo-code, since it predates having a real FlexSim
instance to test against), and
[`flexsim/verified_scripts/README.md`](flexsim/verified_scripts/README.md)
for FlexScript that has actually been run inside FlexSim 2027 and
confirmed working end-to-end against this bridge — this is the one to
follow first.

### What's working right now, end to end

Verified against `flexsim-model/DG-FT-01.fsm`:

1. **Windows Firewall** had two rules (`FlexSIM`, Inbound + Outbound,
   Action = Block) silently dropping all of FlexSim's network traffic,
   including to `127.0.0.1`. Disabled via
   `Disable-NetFirewallRule -DisplayName 'FlexSIM'` (elevated PowerShell).
   Without this, HTTP calls from FlexScript fail with no error at all —
   see the verified-scripts README for the full troubleshooting story.
2. A **Process Flow** (`Source` → `Custom Code` → `Delay(5s)` → loop back
   to `Custom Code`) runs continuously while the model is running,
   POSTing real model state to `/api/v1/telemetry` every 5 simulated
   seconds — no manual intervention needed once wired up.
3. The Custom Code block reads real queue contents
   (`content(Model.find("Queue1"))` etc.), real processor busy/idle state,
   and `Model.time` for simulation time, and serializes them to JSON by
   hand (FlexScript has no built-in JSON serializer we've found yet).
4. **Throughput counting**: FlexSim doesn't have a built-in "items in /
   items out" counter readily accessible from FlexScript, so we added two
   entries to the model's own **Model Parameter Table** (`Parameters`):
   `BasketsIn` and `BasketsOut`, both integers starting at 0. A subset of
   the model's existing `PhotoEyes` group (`PE1`–`PE13` at entry points,
   `PE14`–`PE16` at exit points) increments the relevant parameter by 1 in
   their `On Block` trigger:
   ```
   Model.parameters.BasketsIn = Model.parameters.BasketsIn + 1;
   ```
   The Custom Code block reads `Model.parameters.BasketsIn` /
   `Model.parameters.BasketsOut` each cycle and sends them under the
   telemetry payload's existing `sources`/`sinks` fields (which are
   free-form `dict[str, Any]`, so no schema change was needed):
   ```json
   "sources": {"BasketsIn": {"count": 42}},
   "sinks": {"BasketsOut": {"count": 39}}
   ```
   The dashboard reads these into the "Baskets In" / "Baskets Out" tiles.

## Initial FlexSim Data Scope

The bridge is written generically for queues, processors, conveyors,
AGVs/mobile robots, sources, and sinks — object names are always
dictionary keys, never hard-coded, so it isn't tied to any one model's
naming scheme. `DG-FT-01.fsm` is the model actually exercised so far;
extending the FlexScript to cover conveyors and real AGV
position/battery (rather than just queues/processors/basket counts) is
the natural next step and just means identifying the right FlexScript
read functions the same way (FlexSim's own autocomplete in the Script
Console, not guesswork) and adding them to the same Custom Code block.

## Phase 2: ROS 2 (not implemented)

The architecture reserves a future `app/ros/` package for a ROS 2 layer:

```text
FlexSim Telemetry → Python Bridge → ROS 2 Topics
                                      /warehouse/state
                                      /amr/state
                                      /flexsim/events

ROS 2 Commands → Python Bridge → FlexSim
```

This is intentionally out of scope for Phase 1. No ROS 2 dependencies are
installed. When Phase 2 begins, `app/ros/` publishers/subscribers would
read from and write to the existing `state_store` / `command_store`
services, without changes to the HTTP API.

## Assumptions

- FlexSim 2027 provides HTTP request capability via the `Http.Request` /
  `Http.Response` FlexScript classes (confirmed live, not guessed — see
  `flexsim/verified_scripts/README.md`).
- Single FlexSim model instance communicating with a single local bridge
  instance (no multi-tenant routing in Phase 1).
- Localhost-only communication; no authentication/TLS in Phase 1.
- Windows Firewall must allow FlexSim outbound traffic to localhost (see
  above) — this is a machine-specific setup step, not something the
  bridge or model can work around on their own.
