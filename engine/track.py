from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline


@dataclass
class Track:
    x: np.ndarray
    y: np.ndarray
    w_right: np.ndarray
    w_left: np.ndarray
    s: np.ndarray
    normal_x: np.ndarray
    normal_y: np.ndarray
    kappa: np.ndarray
    length: float

    @property
    def n_points(self) -> int:
        return len(self.x)

    def position_at(self, s: float | np.ndarray, alpha: float | np.ndarray = 0.0):
        s = np.asarray(s) % self.length
        x = np.interp(s, self.s, self.x, period=self.length)
        y = np.interp(s, self.s, self.y, period=self.length)
        nx = np.interp(s, self.s, self.normal_x, period=self.length)
        ny = np.interp(s, self.s, self.normal_y, period=self.length)
        return x + alpha * nx, y + alpha * ny

    def widths_at(self, s: float | np.ndarray):
        s = np.asarray(s) % self.length
        wr = np.interp(s, self.s, self.w_right, period=self.length)
        wl = np.interp(s, self.s, self.w_left, period=self.length)
        return wr, wl


def load_track_csv(path: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    data = np.genfromtxt(path, delimiter=",", comments="#")
    if data.ndim != 2 or data.shape[1] < 4:
        raise ValueError(f"CSV de pista inválido: esperado 4 colunas, obtido {data.shape}")
    x, y, w_right, w_left = data[:, 0], data[:, 1], data[:, 2], data[:, 3]
    if np.hypot(x[0] - x[-1], y[0] - y[-1]) < 1e-6:
        x, y, w_right, w_left = x[:-1], y[:-1], w_right[:-1], w_left[:-1]
    return x, y, w_right, w_left


def build_track(
    x: np.ndarray,
    y: np.ndarray,
    w_right: np.ndarray,
    w_left: np.ndarray,
    n_samples: int = 1000,
) -> Track:
    xc = np.append(x, x[0])
    yc = np.append(y, y[0])

    chord = np.concatenate(([0.0], np.cumsum(np.hypot(np.diff(xc), np.diff(yc)))))
    spline_x = CubicSpline(chord, xc, bc_type="periodic")
    spline_y = CubicSpline(chord, yc, bc_type="periodic")

    t_dense = np.linspace(0.0, chord[-1], 20 * len(xc))
    dx = spline_x(t_dense, 1)
    dy = spline_y(t_dense, 1)
    arc_dense = np.concatenate(([0.0], np.cumsum(np.hypot(np.diff(spline_x(t_dense)), np.diff(spline_y(t_dense))))))
    length = float(arc_dense[-1])

    s_uniform = np.linspace(0.0, length, n_samples, endpoint=False)
    t_uniform = np.interp(s_uniform, arc_dense, t_dense)

    xs = spline_x(t_uniform)
    ys = spline_y(t_uniform)
    dxs = spline_x(t_uniform, 1)
    dys = spline_y(t_uniform, 1)
    norm = np.hypot(dxs, dys)
    tx, ty = dxs / norm, dys / norm
    nx, ny = ty, -tx

    ddxs = spline_x(t_uniform, 2)
    ddys = spline_y(t_uniform, 2)
    kappa = (dxs * ddys - dys * ddxs) / np.maximum(norm**3, 1e-12)

    wr = np.interp(t_uniform, chord[:-1], w_right, period=chord[-1])
    wl = np.interp(t_uniform, chord[:-1], w_left, period=chord[-1])

    return Track(
        x=xs,
        y=ys,
        w_right=wr,
        w_left=wl,
        s=s_uniform,
        normal_x=nx,
        normal_y=ny,
        kappa=kappa,
        length=length,
    )
