# Compare velocity from fc/optical_flow and fc/range with sim ground truth.

import math

from drone_interfaces.msg import OpticalFlow
from drone_sim import checks
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range


class FlowCheck(Node):
    # Print how well flow and range reproduce the true body velocity.

    def __init__(self):
        super().__init__('flow_check')
        self.range = None
        self.truth = None
        self.errors = []
        self.speeds = []
        self.create_subscription(Range, 'fc/range', self.on_range, 10)
        self.create_subscription(Odometry, '/sim/ground_truth', self.on_truth, 10)
        self.create_subscription(OpticalFlow, 'fc/optical_flow', self.on_flow, 10)
        self.create_timer(2.0, self.report)

    def on_range(self, msg):
        self.range = msg.range if math.isfinite(msg.range) else None

    def on_truth(self, msg):
        self.truth = msg.twist.twist.linear

    def on_flow(self, msg):
        if self.truth is None:
            return
        err = checks.flow_velocity_error(msg, self.range, self.truth.x, self.truth.y)
        if err is None:
            return
        self.errors.append(err)
        self.speeds.append(math.hypot(self.truth.x, self.truth.y))

    def report(self):
        n = len(self.errors)
        if n == 0:
            self.get_logger().info('no usable flow yet')
            return
        for axis, name in ((0, 'x'), (1, 'y')):
            mean, std = checks.mean_std([err[axis] for err in self.errors])
            self.get_logger().info(f'v_{name} error: mean {mean:+.3f} m/s, std {std:.3f} m/s')
        self.get_logger().info(f'{n} samples, mean true speed {sum(self.speeds) / n:.2f} m/s')
        self.errors.clear()
        self.speeds.clear()


def main():
    rclpy.init()
    rclpy.spin(FlowCheck())
