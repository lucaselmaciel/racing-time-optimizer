"""Ponte entre o banco e o engine, com cache das Tracks construídas."""
from __future__ import annotations

import numpy as np

from engine import Track, Vehicle, build_track, raceline_from_alphas, solve
from engine.geometry import clamp_alphas
from app import models

_track_cache: dict[int, Track] = {}


def get_engine_track(row: models.Track) -> Track:
    cached = _track_cache.get(row.id)
    if cached is not None:
        return cached
    pts = np.asarray(row.points, dtype=float)
    track = build_track(pts[:, 0], pts[:, 1], pts[:, 2], pts[:, 3])
    _track_cache[row.id] = track
    return track


def invalidate_track(track_id: int) -> None:
    _track_cache.pop(track_id, None)


def vehicle_from_row(row: models.Vehicle) -> Vehicle:
    return Vehicle(
        name=row.name,
        mass=row.mass,
        power=row.power,
        a_accel_max=row.a_accel_max,
        a_brake_max=row.a_brake_max,
        a_lat_max=row.a_lat_max,
        cd_a=row.cd_a,
        cl_a=row.cl_a,
        crr=row.crr,
        v_max=row.v_max,
    )


def compute_lap(track: Track, vehicle: Vehicle, control_points: list, n_samples: int = 600):
    """control_points: lista de objetos com .s e .alpha, ordenada por s."""
    pairs = sorted((float(cp.s) % track.length, float(cp.alpha)) for cp in control_points)
    s_list: list[float] = []
    a_list: list[float] = []
    for s, a in pairs:
        if s_list and s - s_list[-1] < 1e-6:
            continue  # descarta pontos coincidentes em s
        s_list.append(s)
        a_list.append(a)
    s_ctrl = np.array(s_list)
    alphas = np.array(a_list)
    alphas = clamp_alphas(track, s_ctrl, alphas)
    raceline = raceline_from_alphas(track, s_ctrl, alphas, n_samples=n_samples)
    result = solve(vehicle, raceline)
    return raceline, result
