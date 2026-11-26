"""Compare fc/odom (the estimator) with sim ground truth."""

from drone_sim import checks
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
        # set when both the estimate and the truth have arrived
        self.drift = None
        self.create_subscription(Odometry, 'fc/odom', self.on_est, 10)
        self.create_subscription(Odometry, '/sim/ground_truth', self.on_truth, 10)
        self.create_timer(2.0, self.report)

    def on_est(self, msg):
        self.est = msg

    def on_truth(self, msg):
        self.truth = msg
        if self.drift is None and self.est is not None:
            self.drift = checks.Drift(pos(msg)[:2], pos(self.est)[:2])

    # comparison between ground truth and estimator, every 2s
    def report(self):
        if self.drift is None:
            self.get_logger().info('waiting for fc/odom and ground truth')
            return
        t, e = pos(self.truth), pos(self.est)
        moved, err = self.drift.update(t[:2], e[:2])
        dz = e[2] - t[2]
        dvx = self.est.twist.twist.linear.x - self.truth.twist.twist.linear.x
        self.get_logger().info(
            f'truly moved {moved:.2f} m, position error {err:.3f} m '
            f'(max {self.drift.max_err:.3f}), height error {dz:+.3f} m, '
            f'vx error {dvx:+.3f} m/s')


def main():
    rclpy.init()
    rclpy.spin(OdomCheck())
