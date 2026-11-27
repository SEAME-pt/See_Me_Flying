"""Tests for distance ahead from the depth model: geometry and scaling, no ROS."""
import math
import os

from drone_sim import depth as dp
import numpy as np
import pytest

SHAPE = (480, 640)
CAM = dp.Camera()
MODEL = os.path.expanduser('~/project/models/depth_anything_v2_small.onnx')


class FakeModel:
    """Stands in for the AI model: returns 2 / true depth + 0.5 (a scale and an offset)."""

    def __init__(self, true_depth):
        self.true = true_depth

    def relative(self, bgr):
        return 2.0 / self.true + 0.5


def scene(height=1.2, wall=None):
    """Return true depth: floor below the horizon, nothing above, a wall in the centre."""
    d = np.nan_to_num(dp.floor_depth(SHAPE, height, CAM), nan=dp.FAR)
    if wall is not None:
        dp.centre(d, 0.5)[:] = wall
    return np.minimum(d, dp.FAR)


def test_floor_straight_down_the_bottom_row():
    # Bottom row (479) is 239 px below the centre row (240); f = 320 / tan(hfov / 2).
    f = 320 / math.tan(2.09 / 2)
    k = 239 / f * math.cos(0.35) - math.sin(0.35)
    assert dp.floor_depth(SHAPE, 1.2, CAM)[-1, 0] == pytest.approx(1.23 / k, rel=1e-3)


def test_no_floor_above_the_horizon():
    assert np.isnan(dp.floor_depth(SHAPE, 1.2, CAM)[0]).all()


def test_higher_drone_sees_the_floor_further_away():
    assert dp.floor_depth(SHAPE, 2.0, CAM)[-1, 0] > dp.floor_depth(SHAPE, 1.0, CAM)[-1, 0]


def test_fit_recovers_scale_and_offset():
    true = scene()
    s, t = dp.fit_scale(2.0 / true + 0.5, true, dp.floor_mask(SHAPE))
    assert (s, t) == pytest.approx((2.0, 0.5), rel=1e-3)


def test_fit_refuses_too_few_pixels():
    assert dp.fit_scale(np.ones(SHAPE), scene(), np.zeros(SHAPE, bool)) is None


def test_metres_round_trip():
    true = scene(wall=1.5)
    assert dp.to_metres(2.0 / true + 0.5, 2.0, 0.5) == pytest.approx(true, rel=1e-3)


def test_ahead_finds_a_wall_in_the_centre():
    assert dp.ahead(scene(wall=1.5)) == pytest.approx(1.5)


def test_ahead_ignores_a_few_odd_pixels():
    d = scene()
    dp.centre(d, 0.4)[:5, :5] = 0.3
    assert dp.ahead(d) > 10


def test_distance_ahead_scales_from_the_floor():
    true = scene(height=1.2, wall=1.5)
    est = dp.DistanceAhead(FakeModel(true))
    depth, distance = est.update(np.zeros(SHAPE + (3,), np.uint8), 1.2)
    assert distance == pytest.approx(1.5, rel=0.01)


def test_no_answer_on_the_ground_until_a_scale_was_found():
    est = dp.DistanceAhead(FakeModel(scene(height=0.05)))
    assert est.update(np.zeros(SHAPE + (3,), np.uint8), 0.05) == (None, None)


def test_keeps_the_last_scale_when_landing():
    true = scene(height=1.2, wall=1.5)
    est = dp.DistanceAhead(FakeModel(true))
    est.update(np.zeros(SHAPE + (3,), np.uint8), 1.2)
    _, distance = est.update(np.zeros(SHAPE + (3,), np.uint8), 0.1)
    assert distance == pytest.approx(1.5, rel=0.01)


@pytest.mark.skipif(not os.path.isfile(MODEL), reason='model file not downloaded')
def test_real_model_runs_on_a_camera_sized_image():
    img = (np.random.default_rng(0).random(SHAPE + (3,)) * 255).astype(np.uint8)
    rel = dp.DepthModel(MODEL).relative(img)
    assert rel.shape == img.shape[:2]
    assert np.isfinite(rel).all()
