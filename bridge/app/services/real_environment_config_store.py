"""Thread-safe in-memory store for the desired ros2_sim fleet size."""

from __future__ import annotations

import threading

from app.models.real_environment_config import RealEnvironmentConfig


class RealEnvironmentConfigStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._config = RealEnvironmentConfig()

    def get(self) -> RealEnvironmentConfig:
        with self._lock:
            return self._config

    def set_robot_count(self, robot_count: int) -> RealEnvironmentConfig:
        with self._lock:
            self._config = RealEnvironmentConfig(robot_count=robot_count)
            return self._config


real_environment_config_store = RealEnvironmentConfigStore()
