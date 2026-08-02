"""Otimização de traçado por curvatura mínima.

Linearização clássica da curvatura de uma curva offset da center line:

    κ(α) ≈ κ_c − κ_c²·α − α''

onde ``κ_c`` é a curvatura da center line, ``α`` o offset lateral ao longo da
normal (positivo para a direita) e ``α''`` a segunda derivada em s (aproximada
por diferenças finitas nas estações uniformes). Minimizar ``Σ κ(α)²`` com
bounds ``α ∈ [-w_left + margem, w_right - margem]`` vira um problema de
mínimos quadrados com caixa — resolvido por ``scipy.optimize.lsq_linear``.

Sanidade da convenção de sinais: num círculo CCW (κ_c = +1/R) a normal direita
aponta para fora, então α > 0 aumenta o raio e reduz κ — e de fato
κ_c − κ_c²·α = (1/R)(1 − α/R). O simétrico vale para κ_c < 0.
"""
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
    """Retorna ``(s_ctrl, alpha_ctrl)``: pontos de controle do traçado ótimo.

    O problema roda denso em ``n_stations`` estações; o resultado é subamostrado
    em ``n_ctrl`` pontos de controle para continuar editável na UI.

    ``smooth_weight`` penaliza α' (resíduos extras ``w·(α_next − α_i)/ds``):
    sem isso a linearização explora spikes locais de α — onde ela não vale —
    e o traçado real sai com curvatura enorme nos kinks.
    """
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

    # resíduo_i = κ_c,i − κ_c,i²·α_i − (α_prev − 2α_i + α_next)/ds²  =  κ_c + M·α
    inv_ds2 = 1.0 / ds**2
    rows = np.concatenate([np.arange(m)] * 3)
    cols = np.concatenate([np.arange(m), prev, nxt])
    vals = np.concatenate([
        -(kc**2) + 2.0 * inv_ds2,
        np.full(m, -inv_ds2),
        np.full(m, -inv_ds2),
    ])
    curv_block = sparse.csr_matrix((vals, (rows, cols)), shape=(m, m))

    # Bloco de suavidade: w·(α_next − α_i)/ds, alvo 0.
    w = smooth_weight / ds
    smooth_rows = np.concatenate([np.arange(m)] * 2)
    smooth_cols = np.concatenate([np.arange(m), nxt])
    smooth_vals = np.concatenate([np.full(m, -w), np.full(m, w)])
    smooth_block = sparse.csr_matrix((smooth_vals, (smooth_rows, smooth_cols)), shape=(m, m))

    M = sparse.vstack([curv_block, smooth_block], format="csr")
    target = np.concatenate([-kc, np.zeros(m)])

    # Margem não pode exceder a meia-largura; garante bounds válidos.
    lb = -np.maximum(w_left - margin, 0.1)
    ub = np.maximum(w_right - margin, 0.1)
    result = lsq_linear(M, target, bounds=(lb, ub), max_iter=200)
    alpha = result.x

    ctrl_idx = np.linspace(0, m, n_ctrl, endpoint=False).astype(int)
    return s_stations[ctrl_idx], alpha[ctrl_idx]
