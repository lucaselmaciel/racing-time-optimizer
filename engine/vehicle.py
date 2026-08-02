from __future__ import annotations

from dataclasses import dataclass

import numpy as np

RHO_AIR = 1.225
G = 9.81


@dataclass
class Vehicle:
    name: str
    mass: float
    power: float
    a_accel_max: float
    a_brake_max: float
    a_lat_max: float
    cd_a: float = 0.0
    cl_a: float = 0.0
    crr: float = 0.0
    v_max: float = 100.0

    def load_factor(self, v: np.ndarray) -> np.ndarray:
        return 1.0 + 0.5 * RHO_AIR * self.cl_a * np.asarray(v) ** 2 / (self.mass * G)

    def a_lat_at(self, v: np.ndarray) -> np.ndarray:
        return self.a_lat_max * self.load_factor(v)

    def _ellipse_factor(self, v: np.ndarray, a_y: np.ndarray) -> np.ndarray:
        ratio = np.clip(np.abs(a_y) / self.a_lat_at(v), 0.0, 1.0)
        return np.sqrt(1.0 - ratio**2)

    def drag_decel(self, v: np.ndarray) -> np.ndarray:
        v = np.asarray(v)
        return 0.5 * RHO_AIR * self.cd_a * v**2 / self.mass + self.crr * G * self.load_factor(v)

    def accel_available(self, v: np.ndarray, a_y: np.ndarray) -> np.ndarray:
        v = np.maximum(v, 1.0)
        a_grip = self.a_accel_max * self.load_factor(v) * self._ellipse_factor(v, a_y)
        a_power = self.power / (self.mass * v)
        return np.maximum(np.minimum(a_grip, a_power) - self.drag_decel(v), 0.0)

    def brake_available(self, v: np.ndarray, a_y: np.ndarray) -> np.ndarray:
        return self.a_brake_max * self.load_factor(v) * self._ellipse_factor(v, a_y) + self.drag_decel(v)
