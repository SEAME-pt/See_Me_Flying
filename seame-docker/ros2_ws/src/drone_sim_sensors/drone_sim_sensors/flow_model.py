# Synthetic optical flow sensor: fc/optical_flow from sim ground truth.

import math
import random

from drone_interfaces.msg import OpticalFlow
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node

GOOD_QUALITY = 255


def ideal_flow(vx, vy, wx, wy, z, up_z):
    # Return (flow_rate_x, flow_rate_y) in rad/s, or None if unusable.
    if z <= 0.0 or up_z <= 0.1:
        return None
    d = z / up_z  # distance to a flat floor along the sensor axis
    return wx + vy / d, wy - vx / d


def to_whole_degrees(rate):
    # Cut a rate in rad/s to whole degrees per second, as INAV's MSP does.
    return math.radians(int(math.degrees(rate)))


def measure(flow, z, min_height, max_rate, noise, quantize, rng):
    # Return (quality, flow_rate_x, flow_rate_y) as the sensor would report.
    if flow is None or z < min_height:
        return 0, 0.0, 0.0
    fx, fy = flow
    if max(abs(fx), abs(fy)) > max_rate:
        return 0, 0.0, 0.0  # too fast: the sensor loses tracking
    fx += rng.gauss(0.0, noise)
    fy += rng.gauss(0.0, noise)
    if quantize:
        fx, fy = to_whole_degrees(fx), to_whole_degrees(fy)
    return GOOD_QUALITY, fx, fy


class FlowModel(Node):
    # Publish what a downward flow sensor would report.

    def __init__(self):
        super().__init__('flow_model')
        self.min_height = self.declare_parameter('min_height', 0.08).value
        self.max_rate = self.declare_parameter('max_flow_rate', 7.0).value
        self.noise = self.declare_parameter('flow_noise', 0.0).value
        self.quantize = self.declare_parameter('quantize', False).value
        seed = self.declare_parameter('seed', -1).value
        self.rng = random.Random(None if seed < 0 else seed)
        self.pub = self.create_publisher(OpticalFlow, 'fc/optical_flow', 10)
        self.create_subscription(
            Odometry, '/sim/ground_truth', self.on_truth, 10)
        self.get_logger().info(
            'flow_model running: /sim/ground_truth -> fc/optical_flow')

    def on_truth(self, msg):
        q = msg.pose.pose.orientation
        up_z = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
        v = msg.twist.twist.linear
        w = msg.twist.twist.angular
        z = msg.pose.pose.position.z
        flow = ideal_flow(v.x, v.y, w.x, w.y, z, up_z)
        quality, fx, fy = measure(flow, z, self.min_height, self.max_rate,
                                  self.noise, self.quantize, self.rng)
        bx, by = w.x, w.y
        if self.quantize:
            bx, by = to_whole_degrees(bx), to_whole_degrees(by)
        out = OpticalFlow()
        out.header.stamp = msg.header.stamp
        out.header.frame_id = 'optical_flow'
        out.quality = quality
        out.flow_rate_x, out.flow_rate_y = fx, fy
        out.body_rate_x, out.body_rate_y = bx, by
        self.pub.publish(out)


def main():
    rclpy.init()
    rclpy.spin(FlowModel())
