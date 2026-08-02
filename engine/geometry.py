"""Geometria do traçado (raceline) definido por pontos de controle.

Cada ponto de controle é um par ``(s, alpha)``: posição na center line por
comprimento de arco e deslocamento lateral ao longo da normal (positivo para a
direita, limitado pelas larguras da pista).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.interpolate import CubicSpline

from engine.track import Track


@dataclass
class Raceline:
    """Traçado fechado discretizado, com curvatura por ponto."""

    x: np.ndarray
    y: np.ndarray
    s: np.ndarray       # comprimento de arco acumulado do traçado
    ds: np.ndarray      # ds[i] = distância do ponto i ao ponto i+1 (fechado)
    kappa: np.ndarray   # curvatura com sinal
    length: float

    @property
    def n_points(self) -> int:
        return len(self.x)


def clamp_alphas(track: Track, s_ctrl: np.ndarray, alphas: np.ndarray, margin: float = 0.5) -> np.ndarray:
    """Restringe os alphas aos limites da pista, com margem para a largura do carro."""
    w_right, w_left = track.widths_at(s_ctrl)
    return np.clip(alphas, -(w_left - margin), w_right - margin)


def _clamp_samples_to_track(track: Track, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, bool]:
    """Projeta amostras que saíram dos limites da pista de volta para a borda.

    Sem isso, uma spline com poucos pontos de controle "corta" as curvas por
    fora dos limites e o lap time fica irrealisticamente rápido.
    """
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
    """Constrói o traçado: spline cúbica periódica pelos pontos de controle.

    ``s_ctrl`` deve estar em ordem crescente dentro de ``[0, track.length)``.
    Com ``clamp_to_track`` (padrão), amostras fora dos limites da pista são
    projetadas de volta e a spline é reconstruída por elas.
    """
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
        # Fecha o loop e parametriza por comprimento de corda.
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
            # Amostras projetadas podem coincidir (mesmo ponto da borda) —
            # remove duplicatas consecutivas para a corda ser estritamente
            # crescente, inclusive na emenda do loop.
            keep = np.ones(len(x2), dtype=bool)
            keep[1:] = np.hypot(np.diff(x2), np.diff(y2)) > 1e-6
            x2, y2 = x2[keep], y2[keep]
            if np.hypot(x2[-1] - x2[0], y2[-1] - y2[0]) < 1e-6:
                x2, y2 = x2[:-1], y2[:-1]
            # Reconstrói a spline pelas amostras projetadas para manter a
            # curvatura bem definida (derivadas de spline, não da polilinha).
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
