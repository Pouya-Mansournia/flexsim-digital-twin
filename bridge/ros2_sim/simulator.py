"""Mock "real environment" simulator standing in for a real ROS2-driven
robot fleet, for digital-twin comparison against the FlexSim simulation.

This is NOT ROS2 / NOT Gazebo — no such dependencies are installed
(Phase 1 scope). It's a small standalone discrete-time simulation with:

- A configurable number of robots (default 2), each with a realistic
  trapezoidal speed profile (accelerates 0 -> MAX_SPEED, cruises,
  decelerates to 0 on arrival) instead of teleporting or jumping speed
  instantly.
- A steady arrival rate of new totes into Queue1/Queue2, so a backlog can
  actually form if the fleet can't keep up — the whole point of being
  able to answer "how many robots do we need so Q1/Q2 don't pile up".
- A computed `backlog` (Queue1 + Queue2) and trend (growing/shrinking/
  stable) printed each tick and included in the POSTed payload, so you
  can literally watch whether a given robot count keeps up.

Run with the bridge already running:
    ..\\.venv\\Scripts\\python.exe ros2_sim\\simulator.py --robots 2

Try --robots 1 to watch backlog grow, then --robots 3 to watch it drain,
to answer "how many robots before backlog stops building up".
"""

from __future__ import annotations

import argparse
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

BRIDGE_URL = "http://127.0.0.1:8000/api/v1/real/telemetry"
CONFIG_URL = "http://127.0.0.1:8000/api/v1/real/config"
TICK_SECONDS = 1.0

MAX_SPEED = 2.0  # m/s
ACCEL = 0.5  # m/s^2, used for both accelerating and decelerating
PICKUP_LEG_M = 15.0  # distance from home to the pickup queues
DROPOFF_LEG_M = 15.0  # distance from pickup to the dropoff queues
LOAD_SECONDS = 2.0
UNLOAD_SECONDS = 2.0

PICKUP_QUEUES = ["Queue1", "Queue2"]
DROPOFF_QUEUES = ["Queue3", "Queue4"]
ARRIVAL_RATE_PER_QUEUE = 0.12  # totes/sec added to each pickup queue on average


@dataclass
class Robot:
    name: str
    x: float = 0.0
    y: float = 0.0
    speed: float = 0.0
    state: str = "idle"  # idle | to_pickup | loading | to_dropoff | unloading
    leg_distance: float = 0.0
    leg_traveled: float = 0.0
    dwell_remaining: float = 0.0
    reserved_source: str | None = None
    chosen_destination: str | None = None

    def step(self, dt: float, queues: dict[str, int]) -> None:
        if self.state == "idle":
            self._try_start_pickup(queues)
        elif self.state in ("to_pickup", "to_dropoff"):
            self._travel(dt)
        elif self.state in ("loading", "unloading"):
            self._dwell(dt, queues)

    def _try_start_pickup(self, queues: dict[str, int]) -> None:
        candidates = [q for q in PICKUP_QUEUES if queues.get(q, 0) > 0]
        if not candidates:
            self.speed = 0.0
            return
        # Weighted by backlog size rather than a hard argmax: a queue with
        # 3x the backlog of another is 3x as likely to get serviced next,
        # but the smaller one still gets attention instead of starving
        # whenever the bigger queue happens to be non-empty.
        weights = [queues[q] for q in candidates]
        source = random.choices(candidates, weights=weights, k=1)[0]
        queues[source] -= 1  # reserve the tote so two robots don't grab it
        self.reserved_source = source
        self.state = "to_pickup"
        self.leg_distance = PICKUP_LEG_M
        self.leg_traveled = 0.0

    def _travel(self, dt: float) -> None:
        remaining = self.leg_distance - self.leg_traveled
        decel_distance = (self.speed * self.speed) / (2 * ACCEL) if ACCEL > 0 else 0.0
        if remaining <= decel_distance:
            self.speed = max(0.0, self.speed - ACCEL * dt)
        else:
            self.speed = min(MAX_SPEED, self.speed + ACCEL * dt)
        self.leg_traveled += self.speed * dt
        self.y += self.speed * dt if self.state == "to_pickup" else -self.speed * dt

        if self.leg_traveled >= self.leg_distance:
            self.speed = 0.0
            if self.state == "to_pickup":
                self.state = "loading"
                self.dwell_remaining = LOAD_SECONDS
            else:
                self.state = "unloading"
                self.dwell_remaining = UNLOAD_SECONDS

    def _dwell(self, dt: float, queues: dict[str, int]) -> None:
        self.dwell_remaining -= dt
        if self.dwell_remaining > 0:
            return
        if self.state == "loading":
            self.state = "to_dropoff"
            self.leg_distance = DROPOFF_LEG_M
            self.leg_traveled = 0.0
            self.chosen_destination = random.choice(DROPOFF_QUEUES)
        else:
            queues[self.chosen_destination] = queues.get(self.chosen_destination, 0) + 1
            self.reserved_source = None
            self.chosen_destination = None
            self.state = "idle"


def trend_arrow(previous: int | None, current: int) -> str:
    if previous is None or current == previous:
        return "-- stable"
    return "UP growing" if current > previous else "DOWN shrinking"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--robots", type=int, default=2, help="number of robots in the fleet (default: 2)"
    )
    args = parser.parse_args()

    queues = {name: 20 for name in PICKUP_QUEUES}
    queues.update({name: 0 for name in DROPOFF_QUEUES})
    robots = [Robot(name=f"RealRobot{i + 1}", x=float(i * 5)) for i in range(args.robots)]
    next_robot_index = args.robots

    sim_time = 0.0
    prev_backlog: int | None = None
    arrival_accumulator = 0.0

    print(f"ROS2-side simulator starting with {args.robots} robot(s).")
    print(f"Posting to {BRIDGE_URL} every {TICK_SECONDS}s. Press Ctrl+C to stop.")
    print("Fleet size can be changed live from the dashboard control panel.\n")

    with httpx.Client(timeout=5.0) as client:
        try:
            client.post(CONFIG_URL, json={"robot_count": len(robots)})
        except httpx.HTTPError:
            pass

        while True:
            # Reconcile fleet size against whatever the dashboard last set.
            try:
                config_resp = client.get(CONFIG_URL)
                config_resp.raise_for_status()
                desired = config_resp.json()["robot_count"]
            except httpx.HTTPError:
                desired = len(robots)

            while len(robots) < desired:
                robots.append(Robot(name=f"RealRobot{next_robot_index + 1}", x=float(next_robot_index * 5)))
                next_robot_index += 1
            while len(robots) > desired:
                # Prefer removing an idle robot so we don't strand a tote mid-trip.
                idle = [r for r in robots if r.state == "idle"]
                victim = idle[-1] if idle else robots[-1]
                robots.remove(victim)

            # Poisson-ish arrivals into the pickup queues.
            arrival_accumulator += ARRIVAL_RATE_PER_QUEUE * len(PICKUP_QUEUES) * TICK_SECONDS
            while arrival_accumulator >= 1.0:
                queues[random.choice(PICKUP_QUEUES)] += 1
                arrival_accumulator -= 1.0

            for robot in robots:
                robot.step(TICK_SECONDS, queues)

            sim_time += TICK_SECONDS
            backlog = queues["Queue1"] + queues["Queue2"]

            payload = {
                "simulation_time": sim_time,
                "status": "running",
                "queues": dict(queues),
                "robots": {
                    r.name: {
                        "x": round(r.x, 2),
                        "y": round(r.y, 2),
                        "speed": round(r.speed, 2),
                        "state": r.state,
                        "battery": 100.0,
                    }
                    for r in robots
                },
            }

            try:
                response = client.post(BRIDGE_URL, json=payload)
                response.raise_for_status()
                timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
                trend = trend_arrow(prev_backlog, backlog)
                states = ", ".join(f"{r.name}={r.state}({r.speed:.1f}m/s)" for r in robots)
                print(f"[{timestamp}] t={sim_time:.0f}s backlog(Q1+Q2)={backlog:3d} {trend:14s} {states}", flush=True)
            except httpx.HTTPError as exc:
                print(f"Failed to reach bridge: {exc}", flush=True)

            prev_backlog = backlog
            time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
