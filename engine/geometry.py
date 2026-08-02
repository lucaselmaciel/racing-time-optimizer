from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.interpolate import CubicSpline

from engine.track import Track


@dataclass
class Raceline:
    x: np.ndarray
    y: np.ndarray
    s: np.ndarray
    ds: np.ndarray
    kappa: np.ndarray
    length: float

    @property
    def n_points(self) -> int:
        return len(self.x)


def clamp_alphas(track: Track, s_ctrl: np.ndarray, alphas: np.ndarray, margin: float = 0.5) -> np.ndarray:
    w_right, w_left = track.widths_at(s_ctrl)
    return np.clip(alphas, -(w_left - margin), w_right - margin)


def _clamp_samples_to_track(track: Track, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, bool]:
    d2 = (x[:, None] - track.x[None, :]) ** 2 + (y[:, None] - track.y[None, :]) ** 2
    j = d2.argmin(axis=1)
    dx = x - track.x[j]
    dy = y - track.y[j]
    alpha = dx * track.normal_x[j] + dy * track.normal_y[j]
    clamped = np.clip(alpha, -track.w_left[j], track.w_right[j])
    moved = clamped != alpha
    if not np.any(moved):
        return x, y, False
    x2 = np.where(moved, track.x[j] + clamped * track.normal_x[j], x)
    y2 = np.where(moved, track.y[j] + clamped * track.normal_y[j], y)
    return x2, y2, True


def raceline_from_alphas(
    track: Track,
    s_ctrl: np.ndarray,
    alphas: np.ndarray,
    n_samples: int = 600,
    clamp_to_track: bool = True,
) -> Raceline:
    s_ctrl = np.asarray(s_ctrl, dtype=float)
    alphas = np.asarray(alphas, dtype=float)
    if len(s_ctrl) != len(alphas):
        raise ValueError("s_ctrl e alphas devem ter o mesmo tamanho")
    if len(s_ctrl) < 3:
        raise ValueError("são necessários ao menos 3 pontos de controle")
    if np.any(np.diff(s_ctrl) <= 0):
        raise ValueError("s_ctrl deve ser estritamente crescente")

    px, py = track.position_at(s_ctrl, alphas)

    def _spline_through(points_x: np.ndarray, points_y: np.ndarray):
        pxc = np.append(points_x, points_x[0])
        pyc = np.append(points_y, points_y[0])
        chord = np.concatenate(([0.0], np.cumsum(np.hypot(np.diff(pxc), np.diff(pyc)))))
        sx = CubicSpline(chord, pxc, bc_type="periodic")
        sy = CubicSpline(chord, pyc, bc_type="periodic")
        t = np.linspace(0.0, chord[-1], n_samples, endpoint=False)
        return sx, sy, t

    spline_x, spline_y, t = _spline_through(px, py)
    x = spline_x(t)
    y = spline_y(t)

    if clamp_to_track:
        x2, y2, moved = _clamp_samples_to_track(track, x, y)
        if moved:
            keep = np.ones(len(x2), dtype=bool)
            keep[1:] = np.hypot(np.diff(x2), np.diff(y2)) > 1e-6
            x2, y2 = x2[keep], y2[keep]
            if np.hypot(x2[-1] - x2[0], y2[-1] - y2[0]) < 1e-6:
                x2, y2 = x2[:-1], y2[:-1]
            spline_x, spline_y, t = _spline_through(x2, y2)
            x = spline_x(t)
            y = spline_y(t)

    dx = spline_x(t, 1)
    dy = spline_y(t, 1)
    ddx = spline_x(t, 2)
    ddy = spline_y(t, 2)

    denom = (dx**2 + dy**2) ** 1.5
    kappa = (dx * ddy - dy * ddx) / np.maximum(denom, 1e-12)

    seg = np.hypot(np.diff(np.append(x, x[0])), np.diff(np.append(y, y[0])))
    s = np.concatenate(([0.0], np.cumsum(seg[:-1])))
    length = float(seg.sum())

    return Raceline(x=x, y=y, s=s, ds=seg, kappa=kappa, length=length)
