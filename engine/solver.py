from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from engine.geometry import Raceline
from engine.vehicle import Vehicle


@dataclass
class LapResult:
    lap_time: float
    v: np.ndarray
    v_grip: np.ndarray
    a_lat: np.ndarray
    s: np.ndarray
    length: float


def _grip_speed(vehicle: Vehicle, kappa: np.ndarray) -> np.ndarray:
    abs_k = np.abs(kappa)
    mask = abs_k > 1e-9
    v = np.full_like(abs_k, vehicle.v_max)
    v[mask] = np.minimum(np.sqrt(vehicle.a_lat_max / abs_k[mask]), vehicle.v_max)
    if vehicle.cl_a > 0.0:
        for _ in range(20):
            v[mask] = np.minimum(
                np.sqrt(vehicle.a_lat_at(v[mask]) / abs_k[mask]), vehicle.v_max
            )
    return v


def solve(vehicle: Vehicle, raceline: Raceline) -> LapResult:
    kappa = raceline.kappa
    ds = raceline.ds
    n = len(kappa)

    v_grip = _grip_speed(vehicle, kappa)
    v = v_grip.copy()

    for _ in range(2):
        for i in range(n):
            j = (i + 1) % n
            a_y = v[i] ** 2 * abs(kappa[i])
            a_x = vehicle.accel_available(v[i], a_y)
            v_reach = np.sqrt(v[i] ** 2 + 2.0 * a_x * ds[i])
            if v_reach < v[j]:
                v[j] = v_reach

    for _ in range(2):
        for i in range(n - 1, -1, -1):
            j = (i + 1) % n
            a_y = v[j] ** 2 * abs(kappa[j])
            a_x = vehicle.brake_available(v[j], a_y)
            v_reach = np.sqrt(v[j] ** 2 + 2.0 * a_x * ds[i])
            if v_reach < v[i]:
                v[i] = v_reach

    v_next = np.roll(v, -1)
    v_avg = np.maximum(0.5 * (v + v_next), 1e-3)
    lap_time = float(np.sum(ds / v_avg))

    return LapResult(
        lap_time=lap_time,
        v=v,
        v_grip=v_grip,
        a_lat=v**2 * np.abs(kappa),
        s=raceline.s,
        length=raceline.length,
    )
