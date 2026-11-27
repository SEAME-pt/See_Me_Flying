"""
Tests for time to contact: synthetic frames, no ROS or Gazebo needed.

A random texture zoomed in by a factor s every frame looks like flying
straight at a wall. Each point moves out by (s - 1) * x per frame, so the
time to contact is 1 / (s - 1) frames: s = 1.05 at 10 frames/s is 2.0 s.
"""
import math

import cv2
from drone_sim import ttc
import numpy as np
import pytest

DT = 0.1  # 10 frames per second


def wall(h=240, w=320, seed=0):
    """Return a random grey texture, blurred so it has blobs, like a real surface."""
    noise = np.random.default_rng(seed).random((h, w)).astype(np.float32)
    blob = cv2.GaussianBlur(noise, (0, 0), 3)
    return cv2.normalize(blob, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def zoom(img, s, dx=0.0):
    """Return img zoomed by s about its centre and shifted dx pixels sideways."""
    h, w = img.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), 0, s)
    m[0, 2] += dx
    return cv2.warpAffine(img, m, (w, h), borderMode=cv2.BORDER_REFLECT)


def run(s, frames=12, dx=0.0, image=None):
    """Feed frames zoomed by s per frame; return the last time to contact."""
    est = ttc.TimeToContact(width=320)
    img = wall() if image is None else image
    result = None
    for k in range(frames):
        result = est.update(zoom(img, s ** k, dx * k), k * DT)
    return result


def test_growth_of_a_known_flow_field():
    h, w = 40, 60
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    flow = np.dstack([0.1 * (x - 30) + 2.0, 0.1 * (y - 20) - 1.0])  # grow 0.1 + drift
    assert ttc.growth(flow) == pytest.approx(0.2, rel=1e-3)


def test_approaching_a_wall():
    assert run(1.05) == pytest.approx(2.0, rel=0.2)


def test_closer_wall_gives_shorter_time():
    assert run(1.10) < run(1.03)


def test_hovering_is_never():
    assert run(1.0) == math.inf


def test_backing_away_is_never():
    assert run(0.97) == math.inf


def test_sideways_drift_is_not_an_obstacle():
    assert run(1.0, dx=2.0) == math.inf


def test_plain_wall_gives_no_answer():
    assert run(1.05, image=np.full((240, 320), 200, np.uint8)) is None


def test_first_frame_gives_no_answer():
    assert ttc.TimeToContact().update(wall(), 0.0) is None
