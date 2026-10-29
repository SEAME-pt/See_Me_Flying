"""
Mission state machine against a toy drone, no ROS.

The plant: height follows the commanded vertical speed (plus an optional sag),
stops at the ground and can't climb above a ceiling. The rangefinder reads the
height (0.04-4.0 m, -inf below, +inf above) unless it is switched off. A whole
flight runs in milliseconds.
"""
import math

from drone_mission.logic import (CIRCLE, DONE, HOLD, LAND, Mission, Params, RANGE_LOST,
                                 TAKEOFF, WAIT, YAW)

DT = 0.05


class Plant:
    def __init__(self, h=0.0, sag=0.0, ceiling=math.inf):
        self.h = h
        self.vz = 0.0
        self.sag = sag              # m/s added to every command, e.g. -0.002
        self.ceiling = ceiling
        self.range_on = True        # False: no range messages at all
        self.range_override = None  # e.g. math.inf: messages arrive but say this

    def apply(self, cmd):
        vz = (cmd.vz if cmd is not None else 0.0) + self.sag
        new_h = min(self.ceiling, max(0.0, self.h + vz * DT))
        self.vz = (new_h - self.h) / DT
        self.h = new_h

    def reading(self):
        if self.range_override is not None:
            return self.range_override
        if self.h < 0.04:
            return -math.inf
        return self.h if self.h <= 4.0 else math.inf


def fly(m, plant, t0, duration, stop_at=None):
    """Run the loop; return the time reached and the last command."""
    t, cmd = t0, None
    while t < t0 + duration:
        if plant.range_on:
            m.on_range(t, plant.reading())
        m.on_odom(t, plant.vz, 1.0)
        cmd = m.step(t)
        plant.apply(cmd)
        t += DT
        if stop_at is not None and m.state == stop_at:
            break
    return t, cmd


def states(m):
    return [new for _, _, new in m.transitions]


def test_full_flight():
    m, plant = Mission(Params()), Plant()
    t, cmd = fly(m, plant, 0.0, 120.0, stop_at=DONE)
    assert states(m) == [TAKEOFF, HOLD, CIRCLE, YAW, LAND, DONE]
    assert cmd is None, 'done: publish nothing'
    assert plant.h < 0.04


def test_takeoff_reaches_target():
    m, plant = Mission(Params()), Plant()
    fly(m, plant, 0.0, 60.0, stop_at=HOLD)
    assert abs(plant.h - 1.2) <= 0.05
    fly(m, plant, 100.0, 2.5)
    assert abs(plant.h - 1.2) <= 0.01, 'hold converges on the target'


def test_waits_without_range():
    m, plant = Mission(Params()), Plant()
    plant.range_on = False
    _, cmd = fly(m, plant, 0.0, 10.0)
    assert m.state == WAIT
    assert cmd is None
    assert plant.h == 0.0


def test_start_delay_needs_continuous_range():
    m, plant = Mission(Params(start_delay_s=2.0)), Plant()
    fly(m, plant, 0.0, 1.5)
    plant.range_on = False
    fly(m, plant, 1.5, 1.0)       # range gone: the delay starts again
    plant.range_on = True
    fly(m, plant, 2.5, 1.5)
    assert m.state == WAIT
    fly(m, plant, 4.0, 1.0)
    assert m.state == TAKEOFF


def test_takeoff_from_minus_inf():
    m = Mission(Params())
    m.on_range(0.0, -math.inf)
    assert m.height(0.0) == 0.0


def test_tilt_correction():
    m = Mission(Params())
    m.on_range(0.0, 2.0)
    m.on_odom(0.0, 0.0, 0.5)      # 60 degrees of tilt
    assert m.height(0.0) == 1.0


def test_hold_corrects_sag():
    m, plant = Mission(Params(hold_s=30.0)), Plant(sag=-0.01)
    fly(m, plant, 0.0, 60.0, stop_at=HOLD)
    fly(m, plant, 100.0, 25.0)
    assert abs(plant.h - 1.2) <= 0.02


def test_range_lost_hovers_then_resumes():
    m, plant = Mission(Params(hold_s=30.0)), Plant()
    t, _ = fly(m, plant, 0.0, 60.0, stop_at=HOLD)
    plant.range_on = False
    t, cmd = fly(m, plant, t, 1.0)
    assert m.state == RANGE_LOST
    assert (cmd.vx, cmd.vy, cmd.vz, cmd.yaw_rate) == (0.0, 0.0, 0.0, 0.0)
    plant.range_on = True
    fly(m, plant, t, 0.2)
    assert m.state == HOLD


def test_range_lost_too_long_lands_blind():
    m, plant = Mission(Params(hold_s=30.0)), Plant()
    t, _ = fly(m, plant, 0.0, 60.0, stop_at=HOLD)
    plant.range_on = False
    t, _ = fly(m, plant, t, 30.0, stop_at=DONE)
    assert states(m)[-3:] == [RANGE_LOST, LAND, DONE]
    assert plant.h == 0.0, 'touchdown seen from odometry: commanding down, not moving'


def test_plus_inf_in_the_air_is_range_lost():
    m, plant = Mission(Params(hold_s=30.0)), Plant()
    t, _ = fly(m, plant, 0.0, 60.0, stop_at=HOLD)
    plant.range_override = math.inf
    fly(m, plant, t, 0.2)
    assert m.state == RANGE_LOST


def test_takeoff_timeout_lands():
    m, plant = Mission(Params(takeoff_timeout_s=10.0)), Plant(ceiling=0.6)
    fly(m, plant, 0.0, 60.0, stop_at=DONE)
    assert states(m) == [TAKEOFF, LAND, DONE]


def test_yaw_phase_skipped_when_zero_turns():
    m, plant = Mission(Params(yaw_turns=0.0)), Plant()
    fly(m, plant, 0.0, 120.0, stop_at=DONE)
    assert YAW not in states(m)


def test_circle_commands():
    m, plant = Mission(Params()), Plant()
    t, _ = fly(m, plant, 0.0, 60.0, stop_at=CIRCLE)
    _, cmd = fly(m, plant, t, 0.05)
    assert math.hypot(cmd.vx, cmd.vy) == 0.3
    assert m.state == CIRCLE


def test_yaw_commands_and_holds_height():
    m, plant = Mission(Params()), Plant(sag=-0.01)
    t, _ = fly(m, plant, 0.0, 120.0, stop_at=YAW)
    _, cmd = fly(m, plant, t, 5.0)
    assert cmd.yaw_rate == 0.5
    assert abs(plant.h - 1.2) <= 0.03
    assert m.state == YAW


def test_landing_descends_at_land_speed():
    m, plant = Mission(Params(yaw_turns=0.0)), Plant()
    t, _ = fly(m, plant, 0.0, 120.0, stop_at=LAND)
    _, cmd = fly(m, plant, t, 1.0)
    assert cmd.vz == -0.15
