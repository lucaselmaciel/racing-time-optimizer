import numpy as np
import pytest

from engine import raceline_from_alphas
from engine.geometry import clamp_alphas


def test_circle_curvature(circle_track):
    s_ctrl = np.linspace(0.0, circle_track.length, 12, endpoint=False)
    raceline = raceline_from_alphas(circle_track, s_ctrl, np.zeros(12))
    assert np.all(np.abs(raceline.kappa - 0.01) < 0.002)


def test_alpha_changes_radius(circle_track):
    s_ctrl = np.linspace(0.0, circle_track.length, 16, endpoint=False)
    inner = raceline_from_alphas(circle_track, s_ctrl, np.full(16, -4.0))
    outer = raceline_from_alphas(circle_track, s_ctrl, np.full(16, 4.0))
    assert inner.length < outer.length


def test_clamp_alphas(circle_track):
    s_ctrl = np.array([0.0, 100.0, 200.0])
    alphas = np.array([-10.0, 0.0, 10.0])
    clamped = clamp_alphas(circle_track, s_ctrl, alphas, margin=0.5)
    assert np.all(clamped >= -4.5 - 1e-9)
    assert np.all(clamped <= 4.5 + 1e-9)


def test_requires_three_points(circle_track):
    with pytest.raises(ValueError):
        raceline_from_alphas(circle_track, np.array([0.0, 100.0]), np.zeros(2))
