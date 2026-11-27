"""Tests for path_viz's path building: plain Python, no ROS needed."""

from drone_sim.path_viz import Paths, Trail
import pytest


def test_trail_skips_points_closer_than_a_step():
    t = Trail(step=0.05)
    assert t.add((0.0, 0.0, 0.0))
    assert not t.add((0.03, 0.0, 0.0))
    assert t.add((0.06, 0.0, 0.0))
    assert list(t.points) == [(0.0, 0.0, 0.0), (0.06, 0.0, 0.0)]


def test_trail_keeps_the_newest_points():
    t = Trail(step=0.01, max_points=3)
    for x in range(5):
        t.add((float(x), 0.0, 0.0))
    assert [p[0] for p in t.points] == [2.0, 3.0, 4.0]


def test_estimate_waits_for_the_truth():
    paths = Paths()
    assert not paths.add_estimate((0.0, 0.0, 0.0))
    assert paths.shift is None
    assert not paths.lines['estimated'].points


def test_estimate_starts_where_the_truth_starts():
    paths = Paths()
    paths.add_truth((-5.5, 4.0, 0.05))
    paths.add_estimate((0.0, 0.0, 0.0))
    paths.add_estimate((3.9, 0.1, 1.0))
    start, end = paths.lines['estimated'].points
    assert start == pytest.approx((-5.5, 4.0, 0.05))
    assert end == pytest.approx((-1.6, 4.1, 1.05))


def test_shift_is_set_once():
    paths = Paths()
    paths.add_truth((-5.5, 4.0, 0.0))
    paths.add_estimate((0.0, 0.0, 0.0))
    paths.add_truth((-1.5, 4.0, 1.0))
    paths.add_estimate((3.0, 0.0, 1.0))
    assert paths.shift == pytest.approx((-5.5, 4.0, 0.0))


def test_planned_line_joins_the_targets():
    paths = Paths()
    paths.add_truth((-5.5, 4.0, 0.0))
    paths.add_estimate((0.0, 0.0, 0.0))
    assert paths.add_target((0.0, 0.0, 1.2))   # takeoff: straight up
    assert paths.add_target((1.0, 0.0, 1.2))   # goto: 1 m forward
    assert list(paths.lines['planned'].points) == [
        (-5.5, 4.0, 0.0), (-5.5, 4.0, 1.2), (-4.5, 4.0, 1.2)]


def test_target_waits_for_the_line_up():
    paths = Paths()
    assert not paths.add_target((1.0, 0.0, 1.2))
    assert not paths.lines['planned'].points
