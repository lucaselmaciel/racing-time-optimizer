from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.optimize import lsq_linear

from engine.track import Track


def optimize_min_curvature(
    track: Track,
    n_stations: int = 400,
    n_ctrl: int = 96,
    margin: float = 1.0,
    smooth_weight: float = 0.01,
) -> tuple[np.ndarray, np.ndarray]:
    n = track.n_points
    stride_idx = np.linspace(0, n, n_stations, endpoint=False).astype(int)

    kc = track.kappa[stride_idx]
    w_right = track.w_right[stride_idx]
    w_left = track.w_left[stride_idx]
    s_stations = track.s[stride_idx]

    m = n_stations
    ds = track.length / m
    prev = np.arange(-1, m - 1) % m
    nxt = np.arange(1, m + 1) % m

    inv_ds2 = 1.0 / ds**2
    rows = np.concatenate([np.arange(m)] * 3)
    cols = np.concatenate([np.arange(m), prev, nxt])
    vals = np.concatenate([
        -(kc**2) + 2.0 * inv_ds2,
        np.full(m, -inv_ds2),
        np.full(m, -inv_ds2),
    ])
    curv_block = sparse.csr_matrix((vals, (rows, cols)), shape=(m, m))

    w = smooth_weight / ds
    smooth_rows = np.concatenate([np.arange(m)] * 2)
    smooth_cols = np.concatenate([np.arange(m), nxt])
    smooth_vals = np.concatenate([np.full(m, -w), np.full(m, w)])
    smooth_block = sparse.csr_matrix((smooth_vals, (smooth_rows, smooth_cols)), shape=(m, m))

    M = sparse.vstack([curv_block, smooth_block], format="csr")
    target = np.concatenate([-kc, np.zeros(m)])

    lb = -np.maximum(w_left - margin, 0.1)
    ub = np.maximum(w_right - margin, 0.1)
    result = lsq_linear(M, target, bounds=(lb, ub), max_iter=200)
    alpha = result.x

    ctrl_idx = np.linspace(0, m, n_ctrl, endpoint=False).astype(int)
    return s_stations[ctrl_idx], alpha[ctrl_idx]
