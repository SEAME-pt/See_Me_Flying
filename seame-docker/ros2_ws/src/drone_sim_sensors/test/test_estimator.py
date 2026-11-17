"""Tests for estimator v1: plain Python, no ROS needed."""

import math
import random
from types import SimpleNamespace

from drone_sim_sensors import estimator as est
import pytest

LEVEL = SimpleNamespace(x=0.0, y=0.0, z=0.0, w=1.0)
DT = 0.02  # 50 Hz, like fc/optical_flow


def flow(fx=0.0, fy=0.0, bx=0.0, by=0.0, quality=255):
    """Build an OpticalFlow-like object."""
    return SimpleNamespace(quality=quality, flow_rate_x=fx, flow_rate_y=fy,
                           body_rate_x=bx, body_rate_y=by)


def rotated(axis, angle):
    """Return a quaternion for a rotation of angle rad about 'x' or 'z'."""
    s, c = math.sin(angle / 2), math.cos(angle / 2)
    if axis == 'x':
        return SimpleNamespace(x=s, y=0.0, z=0.0, w=c)
    return SimpleNamespace(x=0.0, y=0.0, z=s, w=c)


def test_forward_flow_gives_forward_velocity():
    assert est.body_velocity(0.0, -0.3, 0.0, 0.0, 1.0) == pytest.approx((0.3, 0.0))


def test_left_flow_gives_left_velocity():
    assert est.body_velocity(0.3, 0.0, 0.0, 0.0, 1.0) == pytest.approx((0.0, 0.3))


def test_rotation_in_place_gives_no_velocity():
    assert est.body_velocity(0.5, -0.2, 0.5, -0.2, 1.0) == pytest.approx((0.0, 0.0))


def test_yaw_turns_body_forward_into_world_left():
    heading = est.yaw(rotated('z', math.pi / 2))
    assert heading == pytest.approx(math.pi / 2)
    assert est.to_world(1.0, 0.0, heading) == pytest.approx((0.0, 1.0), abs=1e-9)


def test_integrates_position():
    e = est.Estimator()
    for i in range(101):
        e.update(i * DT, flow(fy=-0.3), 1.0, LEVEL)
    assert e.x == pytest.approx(0.6)
    assert e.y == pytest.approx(0.0)


def test_height_corrects_for_tilt():
    e = est.Estimator()
    e.update(0.0, flow(), 1.0, rotated('x', math.radians(30)))
    assert e.z == pytest.approx(math.cos(math.radians(30)))


def test_too_close_reads_as_ground():
    e = est.Estimator()
    e.update(0.0, flow(quality=0), -math.inf, LEVEL)
    assert e.z == 0.0


def test_out_of_range_keeps_last_height():
    e = est.Estimator()
    e.update(0.0, flow(), 1.0, LEVEL)
    e.update(DT, flow(), math.inf, LEVEL)
    assert e.z == pytest.approx(1.0)


def test_lost_flow_holds_briefly_then_stops():
    e = est.Estimator(hold_s=0.3)
    e.update(0.0, flow(fy=-0.3), 1.0, LEVEL)
    e.update(0.1, flow(quality=0), 1.0, LEVEL)
    assert e.vx == pytest.approx(0.3)
    e.update(0.5, flow(quality=0), 1.0, LEVEL)
    assert e.vx == 0.0


def test_vertical_speed_follows_a_climb():
    e = est.Estimator()
    for i in range(150):
        e.update(i * DT, flow(), 1.0 + 0.2 * i * DT, LEVEL)
    assert e.vz == pytest.approx(0.2)


def test_vertical_speed_stays_calm_in_noisy_hover():
    rng = random.Random(0)
    e = est.Estimator()
    speeds = []
    for i in range(500):
        e.update(i * DT, flow(), 1.0 + rng.gauss(0.0, 0.01), LEVEL)
        if i * DT > 1.0:
            speeds.append(e.vz)
    mean = sum(speeds) / len(speeds)
    std = math.sqrt(sum((v - mean) ** 2 for v in speeds) / len(speeds))
    assert std < 0.015
