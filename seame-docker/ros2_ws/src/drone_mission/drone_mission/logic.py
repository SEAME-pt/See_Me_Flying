"""
Mission state machine, without ROS: feed it measurements, goals and times; ask for a command.

States: grounded -> takeoff -> hold <-> goto -> land -> grounded, plus range_lost
and overridden (another source, such as the radio, has control: see safety_manager).
One goal at a time (Takeoff, Goto or Land); hold is where it rests in the air,
publishing altitude hold so fc_bridge never times out between goals.
Height is the rangefinder (fc/range), tilt-corrected, like INAV's SURFACE mode.
Goto is relative to where the drone is when it starts: flow position drifts, so
nothing here flies to an absolute x, y.
"""
from dataclasses import dataclass, field
import math
from typing import Dict, Optional, Tuple

GROUNDED = 'grounded'
TAKEOFF = 'takeoff'
HOLD = 'hold'
GOTO = 'goto'
LAND = 'land'
RANGE_LOST = 'range_lost'
OVERRIDDEN = 'overridden'
AIRBORNE = (TAKEOFF, HOLD, GOTO, LAND, RANGE_LOST)

ACTIVE = 'active'
SUCCEEDED = 'succeeded'
ABORTED = 'aborted'
CANCELED = 'canceled'


@dataclass
class Params:
    target_h: float = 1.2         # m, default takeoff height; must be below the rangefinder's max
    tolerance: float = 0.05       # m: takeoff ends within this of the target
    kp_z: float = 1.0             # (m/s) per m of height error
    max_vz: float = 0.3           # m/s, matches fc_bridge max_speed_z
    land_speed: float = 0.15      # m/s down
    ground_h: float = 0.12        # m: below this the drone is on (or at) the ground
    touchdown_s: float = 1.0      # s on the ground (or not descending) to call it landed
    speed: float = 0.3            # m/s, default Goto speed
    kp_xy: float = 1.0            # (m/s) per m of position error
    pos_tolerance: float = 0.10   # m: Goto ends within this
    kp_yaw: float = 1.5           # (rad/s) per rad of heading error
    yaw_rate: float = 0.5         # rad/s, max
    yaw_tolerance: float = 0.05   # rad: Goto ends within this
    goto_margin_s: float = 10.0   # Goto gives up after twice the ideal time plus this
    range_timeout_s: float = 0.5  # no range message for this long = range lost
    ready_s: float = 1.0          # Takeoff needs this long of range readings without a gap
    odom_timeout_s: float = 0.5   # no odometry for this long: Goto can't steer
    lost_hold_s: float = 2.0      # hover this long waiting for the range, then land
    takeoff_timeout_s: float = 20.0


@dataclass
class Command:
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    yaw_rate: float = 0.0


@dataclass
class Goal:
    kind: str                     # TAKEOFF, GOTO or LAND
    status: str = ACTIVE
    message: str = ''
    result: Dict[str, float] = field(default_factory=dict)
    feedback: Dict[str, float] = field(default_factory=dict)


def wrap(a: float) -> float:
    """Angle to [-pi, pi)."""
    return (a + math.pi) % (2.0 * math.pi) - math.pi


class Mission:
    def __init__(self, params: Params):
        self.p = params
        self.state = GROUNDED
        self.phase_start = 0.0
        self.goal: Optional[Goal] = None
        self.hold_h = params.target_h          # height held in hold, goto and takeoff
        self.range_t: Optional[float] = None
        self.range_m = math.nan
        self.range_max = math.inf
        self.range_ok_since: Optional[float] = None   # start of the current run of readings
        self.odom_t: Optional[float] = None
        self.x = self.y = self.yaw = 0.0
        self.vz_meas = 0.0
        self.up_z = 1.0                        # world z of the body z axis; 1 when level
        self.target: Tuple[float, float, float] = (0.0, 0.0, 0.0)   # goto x, y, yaw
        self.goto_limit_s = 0.0
        self.goto_speed = params.speed
        self.lost_from = HOLD                  # state range_lost interrupted
        self.in_control = True                 # False while another source commands the drone
        self.below_since: Optional[float] = None
        self.stopped_since: Optional[float] = None
        self.transitions: list = []            # (time, from, to), for logs and tests

    # Inputs

    def on_range(self, t: float, r: float, max_range: float = math.inf) -> None:
        valid = r == -math.inf or math.isfinite(r)
        gap = self.range_t is None or t - self.range_t > self.p.range_timeout_s
        if not valid:
            self.range_ok_since = None
        elif gap or self.range_ok_since is None:
            self.range_ok_since = t
        self.range_t = t
        self.range_m = r
        self.range_max = max_range

    def on_odom(self, t: float, x: float, y: float, yaw: float,
                vz_body: float, up_z: float) -> None:
        self.odom_t = t
        self.x, self.y, self.yaw = x, y, yaw
        self.vz_meas = vz_body
        self.up_z = up_z

    def height(self, t: float) -> Optional[float]:
        """Height above the ground, or None when the rangefinder can't tell."""
        if self.range_t is None or t - self.range_t > self.p.range_timeout_s:
            return None                        # no messages
        r = self.range_m
        if r == -math.inf:
            return 0.0                         # below min range: at the ground
        if not math.isfinite(r) or self.up_z <= 0.0:
            return None                        # beyond max range, or upside down
        return r * self.up_z                   # tilt-corrected

    def odom_fresh(self, t: float) -> bool:
        return self.odom_t is not None and t - self.odom_t <= self.p.odom_timeout_s

    def set_control(self, t: float, in_control: bool, by: str = '') -> None:
        """Another source took over (False), or control came back (True)."""
        if in_control == self.in_control:
            return
        self.in_control = in_control
        if not in_control:
            if self.goal is not None:
                self.finish(ABORTED, f'overridden by {by}')
            self.go(t, OVERRIDDEN)
            return
        # Back in control: never resume a goal or climb on its own. The other
        # source may have moved or landed the drone, so start from where it is.
        h = self.height(t)
        if h is None:
            self.lost_from = HOLD
            self.go(t, RANGE_LOST)
        elif h < self.p.ground_h:
            self.go(t, GROUNDED)
        else:
            self.hold_h = h
            self.go(t, HOLD)

    # Goals: each returns (accepted, reason)

    def request_takeoff(self, t: float, height: float = 0.0) -> Tuple[bool, str]:
        target = height if height > 0.0 else self.p.target_h
        if not self.in_control:
            return False, 'another source has control'
        if self.state != GROUNDED:
            return False, f'not on the ground ({self.state})'
        if self.height(t) is None or self.range_ok_since is None:
            return False, 'no rangefinder reading'
        if t - self.range_ok_since < self.p.ready_s:
            return False, 'rangefinder not steady yet'
        if target >= self.range_max:
            return False, f'{target:.2f} m is beyond the rangefinder ({self.range_max:.2f} m)'
        self.hold_h = target
        self.goal = Goal(TAKEOFF)
        self.go(t, TAKEOFF)
        return True, ''

    def request_goto(self, t: float, forward: float, left: float, yaw: float = 0.0,
                     speed: float = 0.0) -> Tuple[bool, str]:
        if not self.in_control:
            return False, 'another source has control'
        if self.state != HOLD or self.goal is not None:
            return False, f'only from hold, with no other goal ({self.state})'
        if not self.odom_fresh(t):
            return False, 'no odometry'
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        self.target = (self.x + c * forward - s * left,
                       self.y + s * forward + c * left,
                       wrap(self.yaw + yaw))
        self.goto_speed = speed if speed > 0.0 else self.p.speed
        ideal = math.hypot(forward, left) / self.goto_speed + abs(yaw) / self.p.yaw_rate
        self.goto_limit_s = 2.0 * ideal + self.p.goto_margin_s
        self.goal = Goal(GOTO)
        self.go(t, GOTO)
        return True, ''

    def request_land(self, t: float) -> Tuple[bool, str]:
        if not self.in_control:
            return False, 'another source has control'
        if self.state not in AIRBORNE:
            return False, 'already on the ground'
        if self.goal is not None and self.goal.kind != LAND:
            self.finish(ABORTED, 'preempted by Land')
        self.goal = Goal(LAND)
        if self.state != LAND:
            self.go(t, LAND)
        return True, ''

    def cancel(self, t: float) -> bool:
        """Cancel Takeoff or Goto: hover where it is. Land can't be cancelled."""
        if self.goal is None or self.goal.kind == LAND:
            return False
        h = self.height(t)
        if self.state == TAKEOFF and h is not None:
            self.hold_h = h
        self.finish(CANCELED, 'canceled')
        if self.state in (TAKEOFF, GOTO):
            self.go(t, HOLD)
        return True

    # Output

    def step(self, t: float) -> Optional[Command]:
        """Advance the state machine; None means publish nothing (fc_bridge holds)."""
        h = self.height(t)
        elapsed = t - self.phase_start
        p = self.p

        if self.state in (GROUNDED, OVERRIDDEN):
            return None                        # silent: fc_bridge or the other source rules

        if self.state in (TAKEOFF, HOLD, GOTO) and h is None:
            if self.goal is not None:
                self.finish(ABORTED, 'rangefinder lost')
            self.lost_from = self.state
            self.go(t, RANGE_LOST)
            return Command()

        if self.state == TAKEOFF:
            assert h is not None                # lost range was handled above
            self.feedback(height=h)
            if h >= self.hold_h - p.tolerance:
                self.finish(SUCCEEDED, '', height=h)
                self.go(t, HOLD)
            elif elapsed > p.takeoff_timeout_s:
                self.finish(ABORTED, f'no {self.hold_h:.2f} m after {p.takeoff_timeout_s:.0f} s',
                            height=h)
                self.go(t, LAND)
                return self.land(t, h)
            return Command(vz=self.hold_z(h))

        if self.state == HOLD:
            return Command(vz=self.hold_z(h))

        if self.state == GOTO:
            return self.goto(t, h, elapsed)

        if self.state == RANGE_LOST:
            if h is not None:
                # Never climb on its own: on the ground it stays there, and an
                # interrupted takeoff holds the height it reached.
                if h < p.ground_h:
                    self.go(t, GROUNDED)
                    return None
                if self.lost_from == TAKEOFF:
                    self.hold_h = h
                self.go(t, HOLD)
                return Command(vz=self.hold_z(h))
            if elapsed >= p.lost_hold_s:
                self.go(t, LAND)
                return self.land(t, h)
            return Command()                   # hover where we are

        return self.land(t, h)                 # LAND

    # Helpers

    def go(self, t: float, new: str) -> None:
        self.transitions.append((t, self.state, new))
        self.state = new
        self.phase_start = t
        self.below_since = None
        self.stopped_since = None

    def finish(self, status: str, message: str, **result: float) -> None:
        if self.goal is not None:
            self.goal.status = status
            self.goal.message = message
            self.goal.result.update(result)
            self.goal = None

    def feedback(self, **values: Optional[float]) -> None:
        if self.goal is not None:
            self.goal.feedback.update({k: v for k, v in values.items() if v is not None})

    def hold_z(self, h: Optional[float]) -> float:
        if h is None:
            return 0.0
        vz = self.p.kp_z * (self.hold_h - h)
        return max(-self.p.max_vz, min(self.p.max_vz, vz))

    def goto(self, t: float, h: Optional[float], elapsed: float) -> Command:
        p = self.p
        if not self.odom_fresh(t):
            self.finish(ABORTED, 'odometry lost')
            self.go(t, HOLD)
            return Command(vz=self.hold_z(h))
        ex, ey = self.target[0] - self.x, self.target[1] - self.y
        eyaw = wrap(self.target[2] - self.yaw)
        dist = math.hypot(ex, ey)
        self.feedback(distance_remaining=dist, yaw_remaining=eyaw)
        if dist <= p.pos_tolerance and abs(eyaw) <= p.yaw_tolerance:
            self.finish(SUCCEEDED, '', distance_error=dist)
            self.go(t, HOLD)
            return Command(vz=self.hold_z(h))
        if elapsed > self.goto_limit_s:
            self.finish(ABORTED, f'not there after {self.goto_limit_s:.0f} s',
                        distance_error=dist)
            self.go(t, HOLD)
            return Command(vz=self.hold_z(h))
        # World velocity towards the target, capped at the goal's speed, in the body frame.
        v = min(self.goto_speed, p.kp_xy * dist)
        wx, wy = (ex / dist * v, ey / dist * v) if dist > 1e-6 else (0.0, 0.0)
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        yaw_rate = max(-p.yaw_rate, min(p.yaw_rate, p.kp_yaw * eyaw))
        return Command(vx=c * wx + s * wy, vy=-s * wx + c * wy,
                       vz=self.hold_z(h), yaw_rate=yaw_rate)

    def land(self, t: float, h: Optional[float]) -> Optional[Command]:
        """Descend at land_speed until the ground is seen, or descent has stopped."""
        p = self.p
        self.feedback(height=h if h is not None else -1.0)
        # Seen on the rangefinder: low for touchdown_s.
        if h is not None and h < p.ground_h:
            self.below_since = t if self.below_since is None else self.below_since
        else:
            self.below_since = None
        # Without a rangefinder: commanding down but not moving down for touchdown_s.
        # Only after 1.5 s in LAND, so the start of the descent doesn't count.
        if self.odom_fresh(t) and t - self.phase_start >= 1.5 and self.vz_meas > -0.03:
            self.stopped_since = t if self.stopped_since is None else self.stopped_since
        else:
            self.stopped_since = None

        for since in (self.below_since, self.stopped_since):
            if since is not None and t - since >= p.touchdown_s:
                self.finish(SUCCEEDED, '')
                self.go(t, GROUNDED)
                return None
        return Command(vz=-p.land_speed)
