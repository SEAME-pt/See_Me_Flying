"""
Mission state machine, without ROS: feed it measurements and times, ask for a command.

Phases: wait -> takeoff -> hold -> circle -> yaw -> land -> done, plus range_lost.
Height is the rangefinder (fc/range), tilt-corrected, like INAV's SURFACE mode.
Horizontal motion is open-loop velocity: flow position drifts, so nothing here
flies to an absolute x, y.
"""
from dataclasses import dataclass
import math
from typing import Optional

WAIT = 'wait'
TAKEOFF = 'takeoff'
HOLD = 'hold'
CIRCLE = 'circle'
YAW = 'yaw'
LAND = 'land'
DONE = 'done'
RANGE_LOST = 'range_lost'


@dataclass
class Params:
    target_h: float = 1.2         # m above the ground, must be below the rangefinder's max
    tolerance: float = 0.05       # m: takeoff ends within this of target_h
    kp_z: float = 1.0             # (m/s) per m of height error
    max_vz: float = 0.3           # m/s, matches fc_bridge max_speed_z
    land_speed: float = 0.15      # m/s down
    ground_h: float = 0.12        # m: below this the drone is on (or at) the ground
    touchdown_s: float = 1.0      # s on the ground (or not descending) to call it landed
    hold_s: float = 3.0           # s hovering before the pattern
    speed: float = 0.3            # m/s around the circle
    omega: float = 0.5            # rad/s turn rate of the circle's direction
    circle_laps: float = 1.0
    yaw_rate: float = 0.5         # rad/s
    yaw_turns: float = 1.0        # full turns on the spot; 0 skips the yaw phase
    range_timeout_s: float = 0.5  # no range message for this long = range lost
    lost_hold_s: float = 2.0      # hover this long waiting for the range, then land
    takeoff_timeout_s: float = 20.0
    start_delay_s: float = 2.0    # s of good range before taking off


@dataclass
class Command:
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    yaw_rate: float = 0.0


class Mission:
    def __init__(self, params: Params):
        self.p = params
        self.state = WAIT
        self.phase_start: Optional[float] = None
        self.resume_state = HOLD
        self.range_t: Optional[float] = None
        self.range_m = math.nan
        self.up_z = 1.0                     # world z of the body z axis; 1 when level
        self.vz_t: Optional[float] = None
        self.vz_meas = 0.0
        self.below_since: Optional[float] = None
        self.stopped_since: Optional[float] = None
        self.transitions: list = []          # (time, from, to), for logs and tests

    # Inputs

    def on_range(self, t: float, r: float) -> None:
        self.range_t = t
        self.range_m = r

    def on_odom(self, t: float, vz_body: float, up_z: float) -> None:
        self.vz_t = t
        self.vz_meas = vz_body
        self.up_z = up_z

    def height(self, t: float) -> Optional[float]:
        """Height above the ground, or None when the rangefinder can't tell."""
        if self.range_t is None or t - self.range_t > self.p.range_timeout_s:
            return None                     # no messages
        r = self.range_m
        if r == -math.inf:
            return 0.0                      # below min range: at the ground
        if not math.isfinite(r) or self.up_z <= 0.0:
            return None                     # beyond max range, or upside down
        return r * self.up_z                # tilt-corrected

    # Output

    def step(self, t: float) -> Optional[Command]:
        """Advance the state machine; None means publish nothing (fc_bridge holds)."""
        if self.phase_start is None:
            self.phase_start = t
        h = self.height(t)
        elapsed = t - self.phase_start
        p = self.p

        if self.state == WAIT:
            if h is None:
                self.phase_start = t        # need start_delay_s of continuous range
            elif elapsed >= p.start_delay_s:
                self.go(t, TAKEOFF)
            return None

        if self.state in (TAKEOFF, HOLD, CIRCLE, YAW) and h is None:
            self.resume_state = self.state
            self.go(t, RANGE_LOST)
            return Command()

        if self.state == TAKEOFF:
            if h is not None and h >= p.target_h - p.tolerance:
                self.go(t, HOLD)
            elif elapsed > p.takeoff_timeout_s:
                self.go(t, LAND)
                return self.land(t, h)
            return Command(vz=self.hold_z(h))

        if self.state == HOLD:
            if elapsed >= p.hold_s:
                self.go(t, CIRCLE)
            return Command(vz=self.hold_z(h))

        if self.state == CIRCLE:
            if elapsed >= p.circle_laps * 2.0 * math.pi / p.omega:
                self.go(t, YAW if p.yaw_turns > 0.0 else LAND)
                return Command(vz=self.hold_z(h))
            return Command(vx=p.speed * math.cos(p.omega * elapsed),
                           vy=p.speed * math.sin(p.omega * elapsed),
                           vz=self.hold_z(h))

        if self.state == YAW:
            if elapsed >= p.yaw_turns * 2.0 * math.pi / abs(p.yaw_rate):
                self.go(t, LAND)
                return self.land(t, h)
            return Command(vz=self.hold_z(h), yaw_rate=p.yaw_rate)

        if self.state == RANGE_LOST:
            if h is not None:
                self.go(t, self.resume_state)   # restarts that phase
                return Command(vz=self.hold_z(h))
            if elapsed >= p.lost_hold_s:
                self.go(t, LAND)
                return self.land(t, h)
            return Command()                    # hover where we are

        if self.state == LAND:
            return self.land(t, h)

        return None                             # DONE

    # Helpers

    def go(self, t: float, new: str) -> None:
        self.transitions.append((t, self.state, new))
        self.state = new
        self.phase_start = t
        self.below_since = None
        self.stopped_since = None

    def hold_z(self, h: Optional[float]) -> float:
        if h is None:
            return 0.0
        vz = self.p.kp_z * (self.p.target_h - h)
        return max(-self.p.max_vz, min(self.p.max_vz, vz))

    def land(self, t: float, h: Optional[float]) -> Optional[Command]:
        """Descend at land_speed until the ground is seen, or descent has stopped."""
        p = self.p
        # Seen on the rangefinder: low for touchdown_s.
        if h is not None and h < p.ground_h:
            self.below_since = t if self.below_since is None else self.below_since
        else:
            self.below_since = None
        # Without a rangefinder: commanding down but not moving down for touchdown_s.
        # Only after 1.5 s in LAND, so the start of the descent doesn't count.
        odom_fresh = self.vz_t is not None and t - self.vz_t <= p.range_timeout_s
        if (odom_fresh and t - self.phase_start >= 1.5  # type: ignore[operator]
                and self.vz_meas > -0.03):
            self.stopped_since = t if self.stopped_since is None else self.stopped_since
        else:
            self.stopped_since = None

        for since in (self.below_since, self.stopped_since):
            if since is not None and t - since >= p.touchdown_s:
                self.go(t, DONE)
                return None
        return Command(vz=-p.land_speed)
