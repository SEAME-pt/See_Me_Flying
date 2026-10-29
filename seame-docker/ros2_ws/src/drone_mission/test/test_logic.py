"""
Mission state machine against a toy drone, no ROS.

The plant: height follows the commanded vertical speed (plus an optional sag),
stops at the ground and can't climb above a ceiling; body velocity and yaw rate
move it in x, y, yaw exactly. The rangefinder reads the height (0.04-4.0 m,
-inf below, +inf above) unless switched off. Whole flights run in milliseconds.
"""
import math

from drone_mission.logic import (ABORTED, CANCELED, GOTO, GROUNDED, HOLD, LAND, Mission,
                                 Params, RANGE_LOST, SUCCEEDED, TAKEOFF)

DT = 0.05


class Plant:
    def __init__(self, sag=0.0, ceiling=math.inf):
        self.h = 0.0
        self.x = self.y = self.yaw = 0.0
        self.vz = 0.0
        self.sag = sag              # m/s added to every vertical command
        self.ceiling = ceiling
        self.range_on = True        # False: no range messages at all
        self.range_override = None  # e.g. math.inf: messages arrive but say this
        self.odom_on = True

    def apply(self, cmd):
        cmd = cmd if cmd is not None else type('Zero', (), {
            'vx': 0.0, 'vy': 0.0, 'vz': 0.0, 'yaw_rate': 0.0})()
        new_h = min(self.ceiling, max(0.0, self.h + (cmd.vz + self.sag) * DT))
        self.vz = (new_h - self.h) / DT
        self.h = new_h
        if self.h > 0.0:            # on the ground it doesn't slide or turn
            c, s = math.cos(self.yaw), math.sin(self.yaw)
            self.x += (c * cmd.vx - s * cmd.vy) * DT
            self.y += (s * cmd.vx + c * cmd.vy) * DT
            self.yaw += cmd.yaw_rate * DT

    def reading(self):
        if self.range_override is not None:
            return self.range_override
        if self.h < 0.04:
            return -math.inf
        return self.h if self.h <= 4.0 else math.inf


class Flight:
    """A mission, a toy drone and a clock."""

    def __init__(self, **params):
        self.m = Mission(Params(**params))
        self.plant = Plant()
        self.t = 0.0
        self.cmd = None
        self.run(1.5)               # readings for longer than ready_s before the first goal

    def run(self, duration, until=None):
        end = self.t + duration
        while self.t < end:
            if self.plant.range_on:
                self.m.on_range(self.t, self.plant.reading(), 4.0)
            if self.plant.odom_on:
                p = self.plant
                self.m.on_odom(self.t, p.x, p.y, p.yaw, p.vz, 1.0)
            self.cmd = self.m.step(self.t)
            self.plant.apply(self.cmd)
            self.t += DT
            if until is not None and until():
                return

    def finish(self, goal, limit=120.0):
        """Run until the goal is no longer active."""
        self.run(limit, until=lambda: goal.status != 'active')
        return goal

    def takeoff(self, height=0.0):
        ok, why = self.m.request_takeoff(self.t, height)
        assert ok, why
        return self.finish(self.m.goal)

    def goto(self, forward, left, yaw=0.0, speed=0.0):
        ok, why = self.m.request_goto(self.t, forward, left, yaw, speed)
        assert ok, why
        return self.finish(self.m.goal)

    def land(self):
        ok, why = self.m.request_land(self.t)
        assert ok, why
        return self.finish(self.m.goal)


def states(m):
    return [new for _, _, new in m.transitions]


def test_starts_grounded_and_silent():
    f = Flight()
    assert f.m.state == GROUNDED
    assert f.cmd is None


def test_takeoff_hold_land():
    f = Flight()
    assert f.takeoff().status == SUCCEEDED
    assert abs(f.plant.h - 1.2) <= 0.05
    f.run(3.0)
    assert f.m.state == HOLD
    assert abs(f.plant.h - 1.2) <= 0.01, 'hold converges on the target'
    assert f.cmd is not None, 'hold keeps publishing, so fc_bridge never times out'
    assert f.land().status == SUCCEEDED
    assert f.m.state == GROUNDED
    assert f.cmd is None
    assert f.plant.h < 0.04
    assert states(f.m) == [TAKEOFF, HOLD, LAND, GROUNDED]


def test_takeoff_to_a_given_height():
    f = Flight()
    goal = f.takeoff(0.8)
    assert goal.status == SUCCEEDED
    assert abs(goal.result['height'] - 0.8) <= 0.05


def test_takeoff_refused_without_range():
    f = Flight()
    f.plant.range_on = False
    f.run(1.0)
    ok, why = f.m.request_takeoff(f.t)
    assert not ok and 'rangefinder' in why
    assert f.m.state == GROUNDED


def test_takeoff_refused_above_range_max():
    f = Flight()
    ok, why = f.m.request_takeoff(f.t, 5.0)
    assert not ok and 'beyond' in why


def test_takeoff_refused_in_the_air():
    f = Flight()
    f.takeoff()
    ok, _ = f.m.request_takeoff(f.t)
    assert not ok


def test_takeoff_timeout_lands():
    f = Flight(takeoff_timeout_s=10.0)
    f.plant.ceiling = 0.6
    f.m.request_takeoff(f.t)
    goal = f.finish(f.m.goal)
    assert goal.status == ABORTED
    f.run(60.0, until=lambda: f.m.state == GROUNDED)
    assert states(f.m) == [TAKEOFF, LAND, GROUNDED]


def test_cancel_takeoff_holds_where_it_is():
    f = Flight()
    f.m.request_takeoff(f.t)
    goal = f.m.goal
    f.run(2.0)
    h = f.plant.h
    assert f.m.cancel(f.t)
    assert goal.status == CANCELED
    f.run(3.0)
    assert f.m.state == HOLD
    assert abs(f.plant.h - h) <= 0.05


def test_goto_forward():
    f = Flight()
    f.takeoff()
    goal = f.goto(1.0, 0.0)
    assert goal.status == SUCCEEDED
    assert abs(f.plant.x - 1.0) <= 0.1 and abs(f.plant.y) <= 0.05
    assert f.m.state == HOLD
    assert abs(f.plant.h - 1.2) <= 0.03, 'height held during the move'


def test_goto_is_relative_to_heading():
    f = Flight()
    f.takeoff()
    assert f.goto(0.0, 0.0, math.pi / 2).status == SUCCEEDED
    assert abs(f.plant.yaw - math.pi / 2) <= 0.05
    assert f.goto(1.0, 0.0).status == SUCCEEDED
    assert abs(f.plant.x) <= 0.1 and abs(f.plant.y - 1.0) <= 0.1, 'forward is now +y'


def test_goto_square_comes_back():
    f = Flight()
    f.takeoff()
    for _ in range(4):
        assert f.goto(1.0, 0.0).status == SUCCEEDED
        assert f.goto(0.0, 0.0, math.pi / 2).status == SUCCEEDED
    assert math.hypot(f.plant.x, f.plant.y) <= 0.2


def test_goto_refused_on_the_ground_and_during_takeoff():
    f = Flight()
    assert not f.m.request_goto(f.t, 1.0, 0.0)[0]
    f.m.request_takeoff(f.t)
    assert not f.m.request_goto(f.t, 1.0, 0.0)[0]


def test_goto_refused_without_odometry():
    f = Flight()
    f.takeoff()
    f.plant.odom_on = False
    f.run(1.0)
    ok, why = f.m.request_goto(f.t, 1.0, 0.0)
    assert not ok and 'odometry' in why


def test_goto_aborts_when_odometry_stops():
    f = Flight()
    f.takeoff()
    f.m.request_goto(f.t, 2.0, 0.0)
    goal = f.m.goal
    f.run(1.0)
    f.plant.odom_on = False
    f.finish(goal, limit=5.0)
    assert goal.status == ABORTED and 'odometry' in goal.message
    assert f.m.state == HOLD


def test_goto_timeout():
    f = Flight(goto_margin_s=1.0, kp_xy=0.01)   # too weak to arrive in time
    f.takeoff()
    goal = f.goto(1.0, 0.0)
    assert goal.status == ABORTED
    assert f.m.state == HOLD


def test_cancel_goto_holds():
    f = Flight()
    f.takeoff()
    f.m.request_goto(f.t, 2.0, 0.0)
    goal = f.m.goal
    f.run(1.0)
    assert f.m.cancel(f.t)
    assert goal.status == CANCELED
    assert f.m.state == HOLD


def test_land_preempts_goto():
    f = Flight()
    f.takeoff()
    f.m.request_goto(f.t, 2.0, 0.0)
    goto = f.m.goal
    f.run(1.0)
    land = f.land()
    assert goto.status == ABORTED and 'Land' in goto.message
    assert land.status == SUCCEEDED
    assert f.m.state == GROUNDED


def test_land_cannot_be_cancelled():
    f = Flight()
    f.takeoff()
    f.m.request_land(f.t)
    assert not f.m.cancel(f.t)
    assert f.m.state == LAND


def test_land_refused_on_the_ground():
    f = Flight()
    assert not f.m.request_land(f.t)[0]


def test_hold_corrects_sag():
    f = Flight()
    f.plant.sag = -0.01
    f.takeoff()
    f.run(25.0)
    assert abs(f.plant.h - 1.2) <= 0.02


def test_tilt_correction():
    m = Mission(Params())
    m.on_range(0.0, 2.0)
    m.on_odom(0.0, 0.0, 0.0, 0.0, 0.0, 0.5)   # 60 degrees of tilt
    assert m.height(0.0) == 1.0


def test_minus_inf_is_the_ground():
    m = Mission(Params())
    m.on_range(0.0, -math.inf)
    assert m.height(0.0) == 0.0


def test_range_lost_hovers_then_resumes_hold():
    f = Flight()
    f.takeoff()
    f.plant.range_on = False
    f.run(1.0)
    assert f.m.state == RANGE_LOST
    assert (f.cmd.vx, f.cmd.vy, f.cmd.vz, f.cmd.yaw_rate) == (0.0, 0.0, 0.0, 0.0)
    f.plant.range_on = True
    f.run(0.2)
    assert f.m.state == HOLD


def test_range_lost_aborts_goto():
    f = Flight()
    f.takeoff()
    f.m.request_goto(f.t, 2.0, 0.0)
    goal = f.m.goal
    f.run(1.0)
    f.plant.range_override = math.inf
    f.run(0.2)
    assert goal.status == ABORTED and 'rangefinder' in goal.message
    assert f.m.state == RANGE_LOST


def test_range_lost_too_long_lands_blind():
    f = Flight()
    f.takeoff()
    f.plant.range_on = False
    f.run(30.0, until=lambda: f.m.state == GROUNDED)
    assert states(f.m)[-3:] == [RANGE_LOST, LAND, GROUNDED]
    assert f.plant.h == 0.0, 'touchdown seen from odometry: commanding down, not moving'


def test_land_goal_during_autonomous_landing():
    f = Flight()
    f.takeoff()
    f.plant.range_on = False
    f.run(3.0)
    assert f.m.state == LAND
    assert f.land().status == SUCCEEDED


def test_goto_feedback():
    f = Flight()
    f.takeoff()
    f.m.request_goto(f.t, 1.0, 0.0)
    goal = f.m.goal
    f.run(1.0)
    assert 0.0 < goal.feedback['distance_remaining'] < 1.0
    assert f.m.state == GOTO


def test_takeoff_refused_until_range_is_steady():
    f = Flight()
    f.plant.range_on = False
    f.run(1.0)
    f.plant.range_on = True
    f.run(0.5)
    ok, why = f.m.request_takeoff(f.t)
    assert not ok and 'steady' in why
    f.run(0.6)
    assert f.m.request_takeoff(f.t)[0]


def test_range_gap_restarts_the_steady_time():
    f = Flight()
    f.plant.range_on = False
    f.run(0.6)                  # longer than range_timeout_s
    f.plant.range_on = True
    f.run(0.5)
    assert not f.m.request_takeoff(f.t)[0]


def test_range_lost_on_the_ground_during_takeoff_stays_grounded():
    f = Flight()
    f.m.request_takeoff(f.t)
    goal = f.m.goal
    f.plant.range_on = False    # gone before the drone leaves the ground
    f.plant.ceiling = 0.0
    f.run(1.0)
    assert goal.status == ABORTED
    f.plant.range_on = True
    f.plant.ceiling = math.inf
    f.run(3.0)
    assert f.m.state == GROUNDED, 'must not climb with no goal'
    assert f.plant.h == 0.0
    assert f.cmd is None


def test_range_lost_mid_takeoff_holds_the_height_reached():
    f = Flight()
    f.m.request_takeoff(f.t)
    f.run(1.0, until=lambda: f.plant.h > 0.5)
    f.plant.range_on = False
    f.run(0.8)
    h = f.plant.h
    f.plant.range_on = True
    f.run(5.0)
    assert f.m.state == HOLD
    assert abs(f.plant.h - h) <= 0.05, 'holds where the takeoff was interrupted, no further climb'
