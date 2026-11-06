# Synthetic optical flow sensor: fc/optical_flow from sim ground truth.

from drone_interfaces.msg import OpticalFlow
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node


def ideal_flow(vx, vy, wx, wy, z, up_z):
    # Return (flow_rate_x, flow_rate_y) in rad/s, or None if unusable.
    if z <= 0.0 or up_z <= 0.1:
        return None
    d = z / up_z  # distance to a flat floor along the sensor axis
    return wx + vy / d, wy - vx / d


class FlowModel(Node):
    # Publish what a downward flow sensor would report.

    def __init__(self):
        super().__init__('flow_model')
        self.min_height = self.declare_parameter('min_height', 0.08).value
        self.pub = self.create_publisher(OpticalFlow, 'fc/optical_flow', 10)
        self.create_subscription(
            Odometry, '/sim/ground_truth', self.on_truth, 10)

    def on_truth(self, msg):
        q = msg.pose.pose.orientation
        up_z = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
        v = msg.twist.twist.linear
        w = msg.twist.twist.angular
        z = msg.pose.pose.position.z
        out = OpticalFlow()
        out.header.stamp = msg.header.stamp
        out.header.frame_id = 'optical_flow'
        out.body_rate_x = w.x
        out.body_rate_y = w.y
        flow = ideal_flow(v.x, v.y, w.x, w.y, z, up_z)
        if flow is None or z < self.min_height:
            out.quality = 0
        else:
            out.quality = 255
            out.flow_rate_x, out.flow_rate_y = flow
        self.pub.publish(out)


def main():
    rclpy.init()
    rclpy.spin(FlowModel())
