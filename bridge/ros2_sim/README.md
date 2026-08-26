# ros2_sim — mock "real environment" for digital-twin comparison

This is **not ROS2** — no ROS2 packages are installed, consistent with
Phase 1's scope (see the root README's "Phase 2: ROS2" section). It's a
small standalone Python discrete-time simulation standing in for a real
robot fleet, so we can demonstrate and test the actual point of a digital
twin: comparing what the simulation (FlexSim) predicts against what "the
real system" reports, side by side — and answering operational questions
("how many robots before the queue backs up?") before touching real
hardware or a real ROS2 stack.

## What it does

`simulator.py` models a fleet of robots picking up totes from
`Queue1`/`Queue2` and dropping them off at `Queue3`/`Queue4`:

- **Realistic motion**: each robot accelerates from 0 to a 2 m/s max
  speed and decelerates to a stop on arrival (a trapezoidal velocity
  profile), instead of teleporting or jumping speed instantly.
- **A steady arrival rate** of new totes into `Queue1`/`Queue2`, so a
  backlog can actually form if the fleet can't keep up.
- **Weighted, backlog-aware dispatch**: an idle robot doesn't always
  chase whichever queue happens to be strictly larger — it picks
  probabilistically, weighted by each queue's current size, so a 3x
  bigger backlog is 3x more likely to get serviced next without starving
  the smaller queue entirely.
- **A live-configurable fleet size**: the number of robots isn't fixed at
  startup. Every tick, the simulator polls `GET /api/v1/real/config` and
  adds or removes robots to match — so the dashboard's fleet-size input
  changes the simulation in real time, no restart needed.
- **A computed `backlog` metric** (`Queue1 + Queue2`) with a printed
  growing/shrinking/stable trend each tick, so you can literally watch
  whether a given robot count keeps up.

Every tick it POSTs the full snapshot to the bridge:

```
POST http://127.0.0.1:8000/api/v1/real/telemetry
{
  "simulation_time": 21.0,
  "status": "running",
  "queues": {"Queue1": 37, "Queue2": 38, "Queue3": 0, "Queue4": 5},
  "robots": {
    "RealRobot1": {"x": 0.0, "y": 13.0, "speed": 1.5, "state": "to_dropoff", "battery": 100.0}
  }
}
```

This is a **separate channel** from FlexSim's own telemetry
(`/api/v1/telemetry`) — the two are never merged. The dashboard's
"Digital Twin Comparison" panel reads both and draws them as grouped bars
per queue name, plus separate robot tables, so you can see where the
simulated and real sides agree or diverge. FlexSim's own model also has
real `Queue1`–`Queue4` (nested under `Plane1` — see
`../flexsim/verified_scripts/README.md`), so all four queues are
genuinely comparable between the two sides, not just `Queue1`.

## Running it

With the bridge already running (`.\run.ps1` from `bridge/`):

```powershell
.venv\Scripts\python.exe ros2_sim\simulator.py --robots 2
```

Leave it running in its own terminal; it loops until Ctrl+C. `--robots`
just sets the *starting* fleet size — change it live afterward from the
dashboard's "Real-environment fleet size" control instead of restarting.

Watch `http://127.0.0.1:8000/dashboard` update live, or read the
console output directly:

```
[04:07:27] t=332s backlog(Q1+Q2)= 77 -- stable      RealRobot1=to_pickup(2.0m/s), RealRobot2=to_pickup(2.0m/s)
```

## Answering "how many robots do we need?"

With the default arrival rate (`ARRIVAL_RATE_PER_QUEUE` in
`simulator.py`), one full pickup→dropoff robot cycle takes roughly 14s
(travel + load + travel + unload). Two robots in parallel service about
one tote every 7s (~0.14 totes/sec), while arrivals average ~0.24
totes/sec across both queues — so with 2 robots, backlog grows slowly but
steadily. Try setting the fleet size to 1, then 3, then 5 from the
dashboard and watch the **Trend** indicator and the backlog chart to find
the number where growth stops.

## Configuration

Constants at the top of `simulator.py`:

| Name | Meaning |
|---|---|
| `MAX_SPEED`, `ACCEL` | Robot top speed and acceleration/deceleration |
| `PICKUP_LEG_M`, `DROPOFF_LEG_M` | One-way travel distance for each leg |
| `LOAD_SECONDS`, `UNLOAD_SECONDS` | Dwell time at pickup/dropoff |
| `ARRIVAL_RATE_PER_QUEUE` | Average totes/sec arriving into each pickup queue |

## Replacing this with real ROS2 later (Phase 2)

When Phase 2 starts, this script's role — periodically reporting
real-world queue/robot state to `/api/v1/real/telemetry` — would be taken
over by an actual ROS2 node subscribing to real topics (`/warehouse/state`,
`/amr/state`, etc., per the root README's Phase 2 section) instead of a
simulation. The bridge-side API (`/api/v1/real/telemetry`,
`/api/v1/real/state`, `/api/v1/real/config`) doesn't need to change.
