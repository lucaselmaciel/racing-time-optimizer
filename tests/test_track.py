import numpy as np

from engine import build_track, load_track_csv


def test_circle_length(circle_track):
    expected = 2.0 * np.pi * 100.0
    assert abs(circle_track.length - expected) / expected < 0.01


def test_circle_normals_point_outward(circle_track):
    radial_x = circle_track.x / np.hypot(circle_track.x, circle_track.y)
    radial_y = circle_track.y / np.hypot(circle_track.x, circle_track.y)
    dot = circle_track.normal_x * radial_x + circle_track.normal_y * radial_y
    assert np.all(dot > 0.95)


def test_position_at_alpha_offset(circle_track):
    x0, y0 = circle_track.position_at(50.0, 0.0)
    x1, y1 = circle_track.position_at(50.0, 3.0)
    assert np.hypot(x1, y1) > np.hypot(x0, y0)


def test_load_silverstone():
    x, y, w_right, w_left = load_track_csv("data/tracks/silverstone.csv")
    assert len(x) > 100
    track = build_track(x, y, w_right, w_left)
    assert 5500 < track.length < 6300
