"""
Shared maths for the sim checks: flow_check, odom_check and the flight test.

No ROS here, so the same functions run in the check nodes, in the automated
flight test and in unit tests.
"""

import math

from drone_sim.estimator import body_velocity


def mean_std(values):
    """Return (mean, population standard deviation), or (0.0, 0.0) if empty."""
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    mean = sum(values) / n
    return mean, math.sqrt(sum((v - mean) ** 2 for v in values) / n)


def flow_velocity_error(flow, distance, true_vx, true_vy):
    """
    Return (ex, ey): the error of the speed that flow and range give.

    Returns None when the flow has no quality or the distance is unusable.
    """
    if flow.quality == 0 or distance is None or not math.isfinite(distance):
        return None
    vx, vy = body_velocity(flow.flow_rate_x, flow.flow_rate_y,
                           flow.body_rate_x, flow.body_rate_y, distance)
    return vx - true_vx, vy - true_vy


class Drift:
    """Compare how far the estimate and the truth have moved since a start point."""

    def __init__(self, truth_xy, est_xy):
        self.t0 = truth_xy
        self.e0 = est_xy
        self.max_err = 0.0

    def update(self, truth_xy, est_xy):
        """Return (truly moved, position error), and track the largest error."""
        dx = (est_xy[0] - self.e0[0]) - (truth_xy[0] - self.t0[0])
        dy = (est_xy[1] - self.e0[1]) - (truth_xy[1] - self.t0[1])
        err = math.hypot(dx, dy)
        self.max_err = max(self.max_err, err)
        moved = math.hypot(truth_xy[0] - self.t0[0], truth_xy[1] - self.t0[1])
        return moved, err
