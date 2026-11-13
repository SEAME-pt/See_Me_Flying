"""Estimator v1 node: fc/odom from fc/optical_flow, fc/range and fc/attitude."""

import math

from drone_interfaces.msg import OpticalFlow
from drone_sim_sensors.estimator import Estimator
from geometry_msgs.msg import QuaternionStamped
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range


class EstimatorNode(Node):
    """Feed the plain-Python estimator and publish fc/odom."""

    def __init__(self):
        super().__init__('estimator')
        self.est = Estimator(
            hold_s=self.declare_parameter('hold_s', 0.3).value,
            vz_window=self.declare_parameter('vz_window', 0.6).value)
        self.range = math.inf
        self.q = None
        self.pub = self.create_publisher(Odometry, 'fc/odom', 10)
        self.create_subscription(Range, 'fc/range', self.on_range, 10)
        self.create_subscription(
            QuaternionStamped, 'fc/attitude', self.on_attitude, 10)
        self.create_subscription(OpticalFlow, 'fc/optical_flow', self.on_flow, 10)
        self.get_logger().info('estimator running: flow + range + attitude -> fc/odom')

    def on_range(self, msg):
        self.range = msg.range

    def on_attitude(self, msg):
        self.q = msg.quaternion

    def on_flow(self, msg):
        if self.q is None:
            return
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        e = self.est
        e.update(t, msg, self.range, self.q)
        out = Odometry()
        out.header.stamp = msg.header.stamp
        out.header.frame_id = 'odom'
        out.child_frame_id = 'base_link'
        out.pose.pose.position.x = e.x
        out.pose.pose.position.y = e.y
        out.pose.pose.position.z = e.z if e.z is not None else 0.0
        out.pose.pose.orientation = self.q
        out.twist.twist.linear.x = e.vx
        out.twist.twist.linear.y = e.vy
        out.twist.twist.linear.z = e.vz
        out.twist.twist.angular.x = msg.body_rate_x
        out.twist.twist.angular.y = msg.body_rate_y
        self.pub.publish(out)


def main():
    rclpy.init()
    rclpy.spin(EstimatorNode())
