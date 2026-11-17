"""
Estimator v1: fc/odom from optical flow, rangefinder and attitude.

In the sim it stands in for INAV's estimate, or it becomes the first version
of our own estimator if ROS ends up fusing the sensors. No IMU fusion yet:
velocity is flow times distance, height comes from the rangefinder, and
position is integrated from velocity.
"""

from collections import deque
import math


# flow to speed
def body_velocity(flow_x, flow_y, body_x, body_y, distance):
    """Return body-frame (vx, vy) in m/s, per the OpticalFlow sign convention."""
    return -(flow_y - body_y) * distance, (flow_x - body_x) * distance


# how level the drone is
def up_z(q):
    """Return the world z component of the body z axis (1 when level)."""
    return 1.0 - 2.0 * (q.x * q.x + q.y * q.y)


# which way the drone faces, in radians
def yaw(q):
    """Return the heading in rad from a quaternion."""
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                      1.0 - 2.0 * (q.y * q.y + q.z * q.z))


# drone directions to room directions
def to_world(vx, vy, heading):
    """Rotate a body-frame horizontal velocity into the world frame."""
    c, s = math.cos(heading), math.sin(heading)
    return c * vx - s * vy, s * vx + c * vy


# fits a line through the recent heights (0.6 s, about 30 readings) to find
# the trend (up, down or level) with the noise flattened out
def slope(points):
    """Return the least-squares slope of (t, value) points, or 0.0 if too few."""
    n = len(points)
    if n < 3:
        return 0.0
    mt = sum(p[0] for p in points) / n
    mv = sum(p[1] for p in points) / n
    den = sum((p[0] - mt) ** 2 for p in points)
    if den <= 0.0:
        return 0.0
    return sum((p[0] - mt) * (p[1] - mv) for p in points) / den


class Estimator:
    """Estimator state in plain Python; the ROS node only feeds it."""

    def __init__(self, hold_s=0.3, vz_window=0.6, max_dt=0.5):
        self.hold_s = hold_s  # (s) how long to keep the last speed after flow is lost
        self.vz_window = vz_window  # (s) heights used for vertical speed (0.6 s = 30)
        self.max_dt = max_dt  # (s) longer than this between updates counts as a gap
        self.t = None  # time of the last update
        self.x = 0.0  # position in the room
        self.y = 0.0
        self.z = None  # height, None until the first valid reading
        self.vx = 0.0  # speed along each axis
        self.vy = 0.0
        self.vz = 0.0
        self.last_good_flow = None  # time of the last usable flow
        self.heights = deque()  # recent (time, height) readings within vz_window

    def update(self, t, flow, rng, q):
        """
        Advance the estimate to time t (seconds).

        flow: OpticalFlow-like (quality, flow_rate_x/y, body_rate_x/y).
        rng: range in m; +inf means nothing in range, -inf too close.
        q: attitude quaternion with x, y, z, w.
        """
        gap = self.t is not None and not (0.0 < t - self.t <= self.max_dt)
        dt = 0.0 if self.t is None or gap else t - self.t
        if gap:
            self.heights.clear()  # sim reset or a long gap: start over
        self.t = t
        self._update_height(t, rng, up_z(q))
        self._update_velocity(t, flow, rng)
        wx, wy = to_world(self.vx, self.vy, yaw(q))
        self.x += wx * dt
        self.y += wy * dt

    # keeps self.heights to the readings within vz_window, refits vertical speed
    def _update_height(self, t, rng, uz):
        if rng == -math.inf:
            h = 0.0  # closer than the sensor can measure: on the ground
        elif math.isfinite(rng) and uz > 0.1:
            h = rng * uz
        else:
            return  # nothing in range, or upside down: keep the last height
        self.z = h
        self.heights.append((t, h))
        while self.heights and t - self.heights[0][0] > self.vz_window:
            self.heights.popleft()
        self.vz = slope(self.heights)

    def _update_velocity(self, t, flow, rng):
        if flow.quality > 0 and math.isfinite(rng) and rng > 0.0:
            self.vx, self.vy = body_velocity(
                flow.flow_rate_x, flow.flow_rate_y,
                flow.body_rate_x, flow.body_rate_y, rng)
            self.last_good_flow = t
        elif self.last_good_flow is None or t - self.last_good_flow > self.hold_s:
            self.vx = self.vy = 0.0  # flow lost for too long: assume stopped
