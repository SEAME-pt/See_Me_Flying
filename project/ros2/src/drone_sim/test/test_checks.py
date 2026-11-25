"""Tests for the shared check maths: plain Python, no ROS needed."""

from types import SimpleNamespace

from drone_sim import checks
import pytest


def flow(fx=0.0, fy=0.0, bx=0.0, by=0.0, quality=255):
    """Build an OpticalFlow-like object."""
    return SimpleNamespace(quality=quality, flow_rate_x=fx, flow_rate_y=fy,
                           body_rate_x=bx, body_rate_y=by)


def test_mean_std():
    assert checks.mean_std([1.0, 3.0]) == pytest.approx((2.0, 1.0))
    assert checks.mean_std([]) == (0.0, 0.0)


def test_perfect_flow_has_no_error():
    err = checks.flow_velocity_error(flow(fy=-0.3), 1.0, 0.3, 0.0)
    assert err == pytest.approx((0.0, 0.0))


def test_flow_reading_low_gives_negative_error():
    ex, ey = checks.flow_velocity_error(flow(fy=-0.29), 1.0, 0.3, 0.0)
    assert ex == pytest.approx(-0.01)
    assert ey == pytest.approx(0.0)


def test_unusable_flow_is_skipped():
    assert checks.flow_velocity_error(flow(quality=0), 1.0, 0.3, 0.0) is None
    assert checks.flow_velocity_error(flow(), None, 0.3, 0.0) is None
    assert checks.flow_velocity_error(flow(), float('inf'), 0.3, 0.0) is None


def test_drift_compares_movement_not_positions():
    d = checks.Drift((-5.5, 4.0), (0.0, 0.0))
    moved, err = d.update((-1.5, 4.0), (3.9, 0.0))
    assert moved == pytest.approx(4.0)
    assert err == pytest.approx(0.1)


def test_drift_keeps_the_largest_error():
    d = checks.Drift((0.0, 0.0), (0.0, 0.0))
    d.update((1.0, 0.0), (0.5, 0.0))
    d.update((2.0, 0.0), (1.9, 0.0))
    assert d.max_err == pytest.approx(0.5)
