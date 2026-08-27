"""Config the dashboard can push to the running ros2_sim simulator.
Right now that's just the desired fleet size, polled by the simulator
each tick so the robot count can change live without restarting it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RealEnvironmentConfig(BaseModel):
    robot_count: int = Field(default=2, ge=0, le=20)
