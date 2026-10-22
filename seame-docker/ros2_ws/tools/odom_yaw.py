"""Print position and heading from /fc/odom twice a second."""
import math

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry


class OdomYaw(Node):
    def __init__(self):
        super().__init__('odom_yaw')
        self.last = None
        self.create_subscription(Odometry, '/fc/odom', self.on_odom, 10)
        self.create_timer(0.5, self.show)

    def on_odom(self, msg):
        self.last = msg

    def show(self):
        if self.last is None:
            return
        p = self.last.pose.pose.position
        q = self.last.pose.pose.orientation
        yaw = math.degrees(math.atan2(2 * (q.w * q.z + q.x * q.y),
                                      1 - 2 * (q.y * q.y + q.z * q.z)))
        print(f'x={p.x:6.2f}  y={p.y:6.2f}  z={p.z:5.2f}  yaw={yaw:7.1f} deg', flush=True)


def main():
    rclpy.init()
    rclpy.spin(OdomYaw())


if __name__ == '__main__':
    main()