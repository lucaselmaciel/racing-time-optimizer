import numpy as np

from engine import (
    Vehicle,
    build_track,
    load_track_csv,
    optimize_min_curvature,
    raceline_from_alphas,
    solve,
)


def test_circle_pushes_outward(circle_track):
    s_ctrl, alphas = optimize_min_curvature(circle_track, n_stations=200, n_ctrl=24)
    assert np.all(alphas > 3.0)


def test_respects_track_bounds(circle_track):
    s_ctrl, alphas = optimize_min_curvature(circle_track, margin=1.0)
    w_right, w_left = circle_track.widths_at(s_ctrl)
    assert np.all(alphas <= w_right - 1.0 + 1e-6)
    assert np.all(alphas >= -(w_left - 1.0) - 1e-6)


def test_optimized_lap_beats_centerline():
    x, y, w_right, w_left = load_track_csv("data/tracks/silverstone.csv")
    track = build_track(x, y, w_right, w_left)
    vehicle = Vehicle(
        name="test", mass=1300.0, power=370_000.0, a_accel_max=9.0,
        a_brake_max=16.0, a_lat_max=14.0, cd_a=1.0, crr=0.012, v_max=85.0,
    )
    n = 48
    s_center = np.linspace(0.0, track.length, n, endpoint=False)
    center = solve(vehicle, raceline_from_alphas(track, s_center, np.zeros(n)))

    s_ctrl, alphas = optimize_min_curvature(track)
    optimized = solve(vehicle, raceline_from_alphas(track, s_ctrl, alphas))

    assert optimized.lap_time < center.lap_time
