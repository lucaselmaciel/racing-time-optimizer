import numpy as np

from engine import Vehicle, raceline_from_alphas, solve


def make_vehicle(**overrides):
    params = dict(
        name="test",
        mass=750.0,
        power=520_000.0,
        a_accel_max=13.0,
        a_brake_max=20.0,
        a_lat_max=17.0,
        cd_a=1.2,
        cl_a=0.0,
        crr=0.012,
        v_max=95.0,
    )
    params.update(overrides)
    return Vehicle(**params)


def test_no_downforce_is_constant_gg():
    v = make_vehicle(cl_a=0.0)
    speeds = np.array([10.0, 50.0, 90.0])
    assert np.allclose(v.load_factor(speeds), 1.0)
    assert np.allclose(v.a_lat_at(speeds), v.a_lat_max)


def test_load_factor_grows_with_speed():
    v = make_vehicle(cl_a=3.5)
    assert v.load_factor(0.0) == 1.0
    lf_70 = float(v.load_factor(70.0))
    assert lf_70 > 2.0  # em ~250 km/h o downforce mais que dobra o grip
    assert float(v.a_lat_at(70.0)) > 2.0 * v.a_lat_max


def test_downforce_faster_in_corners(circle_track):
    s_ctrl = np.linspace(0.0, circle_track.length, 24, endpoint=False)
    raceline = raceline_from_alphas(circle_track, s_ctrl, np.zeros(24))
    no_wing = solve(make_vehicle(cl_a=0.0), raceline)
    winged = solve(make_vehicle(cl_a=3.5), raceline)
    assert winged.lap_time < no_wing.lap_time
    assert winged.v.mean() > no_wing.v.mean()


def test_grip_speed_fixed_point_converges(circle_track):
    """v em curva com downforce satisfaz v²·|κ| ≈ a_lat(v) (regime permanente)."""
    s_ctrl = np.linspace(0.0, circle_track.length, 24, endpoint=False)
    raceline = raceline_from_alphas(circle_track, s_ctrl, np.zeros(24))
    vehicle = make_vehicle(cl_a=2.0, v_max=200.0)
    result = solve(vehicle, raceline)
    mid = len(result.v) // 2
    v = result.v[mid]
    kappa = abs(raceline.kappa[mid])
    assert abs(v**2 * kappa - float(vehicle.a_lat_at(v))) / float(vehicle.a_lat_at(v)) < 0.05
