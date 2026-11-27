"""Tests for flying forward until something gets in the way: plain Python, no ROS."""

import math

from drone_mission.forward import BLIND, Forward, OBSTACLE, Params

P = Params(stop_m=1.5, confirm=3, blind_s=1.0, start_s=3.0)
DT = 0.1


def fly(distances, t0=0.0):
    """Feed one distance every DT; return (index, reason) of the stop, or None."""
    f = Forward(P)
    f.begin(t0)
    for i, d in enumerate(distances):
        t = t0 + i * DT
        if d is not None:                      # None: no message at all
            f.on_distance(t, d)
        why = f.why_stop(t)
        if why:
            return i, why
    return None


def test_clear_way_never_stops():
    assert fly([math.inf] * 200) is None


def test_far_things_do_not_stop():
    assert fly([4.0, 3.0, 2.0, 1.6] * 20) is None


def test_stops_for_an_obstacle():
    assert fly([math.inf] * 50 + [1.4] * 5) == (52, OBSTACLE)


def test_one_or_two_wrong_results_do_not_stop():
    assert fly([math.inf, 1.0, math.inf, math.inf, 1.0, 1.0, math.inf] * 20) is None


def test_mostly_near_results_stop_even_if_never_three_in_a_row():
    assert fly([math.inf, 1.0, math.inf, 1.0, 1.0] * 20)[1] == OBSTACLE


def test_unknown_between_near_results_does_not_hide_the_obstacle():
    assert fly([math.inf] * 50 + [1.4, math.nan, 1.3, math.nan, 1.2]) == (54, OBSTACLE)


def test_obstacle_counts_from_the_start():
    assert fly([1.0] * 5) == (2, OBSTACLE)


def test_unknown_at_the_start_is_excused():
    assert fly([math.nan] * 25 + [math.inf] * 50) is None


def test_unknown_from_start_to_end_stops():
    i, why = fly([math.nan] * 100)
    assert why == BLIND and i * DT <= 3.2


def test_going_blind_in_flight_stops():
    i, why = fly([math.inf] * 60 + [math.nan] * 40)
    assert why == BLIND and (i - 59) * DT <= 1.2


def test_silence_stops_too():
    i, why = fly([math.inf] * 60 + [None] * 40)
    assert why == BLIND and (i - 59) * DT <= 1.2


def test_nothing_happens_before_the_start():
    f = Forward(P)
    for i in range(50):
        f.on_distance(i * DT, 0.5)
        assert f.why_stop(i * DT) is None


def test_results_from_before_the_start_do_not_count():
    f = Forward(P)
    for i in range(5):
        f.on_distance(i * DT, 0.5)
    f.begin(1.0)
    assert f.why_stop(1.0) is None


def approach(readings, stop_m, speed=0.4, start=6.0):
    """Fly at a wall; readings(true distance, i) is what the camera says. Return where it stops."""
    f = Forward(Params(stop_m=stop_m))
    f.begin(0.0)
    for i in range(400):
        true = start - speed * i * DT
        f.on_flown(speed * i * DT)
        f.on_distance(i * DT, readings(true, i))
        if f.why_stop(i * DT):
            return true
        assert true > 0, 'flew into the wall'
    return None


def test_remembers_the_wall_when_the_camera_goes_blind():
    left = approach(lambda true, i: true if true > 1.0 else math.nan, stop_m=0.8)
    assert 0.7 < left <= 0.8


def test_remembers_the_wall_when_near_readings_are_wrong():
    # The worst seen in the sim: below 0.85 m, jumping between too near and too far.
    left = approach(lambda true, i: true + (0.4 * (i % 2) if true < 0.85 else 0.0), stop_m=0.5)
    assert 0.35 < left < 0.6


def test_a_few_wrong_results_do_not_make_a_memory():
    assert approach(lambda true, i: 0.7 if i % 5 < 2 else true, stop_m=0.8) < 1.0


def test_something_that_goes_away_is_forgotten():
    f = Forward(P)
    f.begin(0.0)
    for i in range(100):
        f.on_flown(0.04 * i)
        f.on_distance(i * DT, 4.0 if i < 30 else math.inf)
        assert f.why_stop(i * DT) is None


def test_memory_is_cleared_at_the_start():
    f = Forward(P)
    f.begin(0.0)
    for i in range(20):
        f.on_distance(i * DT, 2.0)
    f.begin(5.0)
    f.on_flown(1.0)
    assert math.isinf(f.left()) and f.why_stop(5.0) is None
