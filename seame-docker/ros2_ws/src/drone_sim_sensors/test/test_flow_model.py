# Sign and geometry tests for the ideal flow formula.

import math

from drone_sim_sensors.flow_model import ideal_flow
import pytest


def test_hover_gives_no_flow():
    assert ideal_flow(0.0, 0.0, 0.0, 0.0, 1.0, 1.0) == (0.0, 0.0)


def test_forward_gives_negative_flow_y():
    fx, fy = ideal_flow(0.3, 0.0, 0.0, 0.0, 1.0, 1.0)
    assert fx == pytest.approx(0.0)
    assert fy == pytest.approx(-0.3)


def test_left_gives_positive_flow_x():
    fx, fy = ideal_flow(0.0, 0.3, 0.0, 0.0, 1.0, 1.0)
    assert fx == pytest.approx(0.3)
    assert fy == pytest.approx(0.0)


def test_rotation_in_place_equals_body_rate():
    fx, fy = ideal_flow(0.0, 0.0, 0.5, -0.2, 1.0, 1.0)
    assert (fx, fy) == pytest.approx((0.5, -0.2))


def test_tilt_lengthens_the_distance():
    up_z = math.cos(math.radians(20))
    _, fy = ideal_flow(0.3, 0.0, 0.0, 0.0, 1.0, up_z)
    assert fy == pytest.approx(-0.3 * up_z)


def test_unusable_geometry_gives_none():
    assert ideal_flow(0.3, 0.0, 0.0, 0.0, 0.0, 1.0) is None   # on the floor
    assert ideal_flow(0.3, 0.0, 0.0, 0.0, 1.0, 0.0) is None   # on its side
