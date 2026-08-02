import numpy as np

from engine import Vehicle, build_track, load_track_csv, raceline_from_alphas, solve


def make_vehicle(**overrides):
    params = dict(
        name="test",
        mass=1000.0,
        power=300_000.0,
        a_accel_max=10.0,
        a_brake_max=15.0,
        a_lat_max=15.0,
        cd_a=0.0,
        crr=0.0,
        v_max=90.0,
    )
    params.update(overrides)
    return Vehicle(**params)


def centerline_raceline(track, n_ctrl=24):
    s_ctrl = np.linspace(0.0, track.length, n_ctrl, endpoint=False)
    return raceline_from_alphas(track, s_ctrl, np.zeros(n_ctrl))


def test_circle_steady_state(circle_track):
    raceline = centerline_raceline(circle_track)
    vehicle = make_vehicle()
    result = solve(vehicle, raceline)
    v_expected = np.sqrt(vehicle.a_lat_max * 100.0)
    assert np.all(np.abs(result.v - v_expected) / v_expected < 0.1)
    t_expected = raceline.length / v_expected
    assert abs(result.lap_time - t_expected) / t_expected < 0.1


def test_speed_never_exceeds_grip(circle_track):
    raceline = centerline_raceline(circle_track)
    result = solve(make_vehicle(), raceline)
    assert np.all(result.v <= result.v_grip + 1e-6)


def test_more_grip_is_faster(circle_track):
    raceline = centerline_raceline(circle_track)
    slow = solve(make_vehicle(a_lat_max=10.0), raceline)
    fast = solve(make_vehicle(a_lat_max=20.0), raceline)
    assert fast.lap_time < slow.lap_time


def test_more_power_is_faster_on_real_track():
    x, y, w_right, w_left = load_track_csv("data/tracks/silverstone.csv")
    track = build_track(x, y, w_right, w_left)
    s_ctrl = np.linspace(0.0, track.length, 40, endpoint=False)
    raceline = raceline_from_alphas(track, s_ctrl, np.zeros(40), n_samples=800)
    weak = solve(make_vehicle(power=150_000.0), raceline)
    strong = solve(make_vehicle(power=450_000.0), raceline)
    assert strong.lap_time < weak.lap_time


def test_silverstone_laptime_plausible():
    x, y, w_right, w_left = load_track_csv("data/tracks/silverstone.csv")
    track = build_track(x, y, w_right, w_left)
    s_ctrl = np.linspace(0.0, track.length, 60, endpoint=False)
    raceline = raceline_from_alphas(track, s_ctrl, np.zeros(60), n_samples=1000)
    vehicle = make_vehicle(mass=1300.0, power=370_000.0, a_lat_max=14.0, cd_a=1.0, crr=0.012, v_max=85.0)
    result = solve(vehicle, raceline)
    assert 90.0 < result.lap_time < 200.0
