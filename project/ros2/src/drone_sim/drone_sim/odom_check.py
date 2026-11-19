"""Compare fc/odom (the estimator) with sim ground truth."""

import math

from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node


def pos(msg):
    """Return (x, y, z) of an Odometry message."""
    p = msg.pose.pose.position
    return p.x, p.y, p.z


class OdomCheck(Node):
    """Every 2 s, print how far fc/odom is from the truth since the check started."""

    def __init__(self):
        super().__init__('odom_check')
        self.est = None
        self.truth = None
        # (truth, estimate) positions when the check started
        self.start = None
        # captures the worst snapshot of the whole test
        self.max_err = 0.0
        self.create_subscription(Odometry, 'fc/odom', self.on_est, 10)
        self.create_subscription(Odometry, '/sim/ground_truth', self.on_truth, 10)
        self.create_timer(2.0, self.report)

    def on_est(self, msg):
        self.est = msg

    def on_truth(self, msg):
        self.truth = msg
        if self.start is None and self.est is not None:
            self.start = (pos(msg), pos(self.est))

    # comparison between ground truth and estimator, every 2s
    def report(self):
        if self.start is None:
            self.get_logger().info('waiting for fc/odom and ground truth')
            return
        (tx0, ty0, _), (ex0, ey0, _) = self.start
        # ground truth position update
        t = pos(self.truth)
        # estimator position update
        e = pos(self.est)
        """estimator's and truth's starting position differ, it is their change
        that is compared"""
        dx = (e[0] - ex0) - (t[0] - tx0)
        dy = (e[1] - ey0) - (t[1] - ty0)
        err = math.hypot(dx, dy)
        self.max_err = max(self.max_err, err)
        moved = math.hypot(t[0] - tx0, t[1] - ty0)
        dz = e[2] - t[2]
        dvx = self.est.twist.twist.linear.x - self.truth.twist.twist.linear.x
        self.get_logger().info(
            f'truly moved {moved:.2f} m, position error {err:.3f} m '
            f'(max {self.max_err:.3f}), height error {dz:+.3f} m, vx error {dvx:+.3f} m/s')


def main():
    rclpy.init()
    rclpy.spin(OdomCheck())
