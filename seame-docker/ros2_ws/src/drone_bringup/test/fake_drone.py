"""
fake_drone: plays Gazebo's X3 for test_stack.py, in its own process like Gazebo.

Reads what fc_bridge sends the X3 (/X3/gazebo/command/twist, /X3/enable) and
publishes /X3/odom at 50 Hz: true pose in the world, velocity in the body frame,
as the bridged Gazebo odometry does. Enabled, it flies at the commanded velocity;
disabled in the air, the motors stop and it drops. On its legs it rests at rest_z.
Its own process so the test's waiting can never delay the odometry: a gap of
0.5 s already counts as a lost rangefinder in the mission.
"""
import math
import time

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool


class FakeDrone(Node):

    def __init__(self):
        super().__init__('fake_drone')
        self.rest_z = self.declare_parameter('rest_z', 0.05).value
        self.fall_speed = self.declare_parameter('fall_speed', 1.0).value
        self.x = self.y = self.yaw = 0.0
        self.z = self.rest_z
        self.cmd = Twist()
        self.enabled = False
        self.pub = self.create_publisher(Odometry, '/X3/odom', 10)
        self.truth_pub = self.create_publisher(Odometry, '/sim/ground_truth', 10)
        self.create_subscription(Twist, '/X3/gazebo/command/twist', self.on_cmd, 10)
        self.create_subscription(Bool, '/X3/enable', self.on_enable, 10)
        self.last = time.monotonic()
        self.create_timer(0.02, self.step)

    def on_cmd(self, msg):
        self.cmd = msg

    def on_enable(self, msg):
        self.enabled = msg.data

    def step(self):
        now = time.monotonic()
        dt, self.last = now - self.last, now
        if self.enabled:
            c = self.cmd
            vx, vy, vz, wz = c.linear.x, c.linear.y, c.linear.z, c.angular.z
        else:
            vx = vy = wz = 0.0
            vz = -self.fall_speed if self.z > self.rest_z else 0.0
        cos, sin = math.cos(self.yaw), math.sin(self.yaw)
        self.x += (cos * vx - sin * vy) * dt
        self.y += (sin * vx + cos * vy) * dt
        self.z = max(self.rest_z, self.z + vz * dt)
        if self.z == self.rest_z:
            vx = vy = wz = 0.0                  # on its legs: it doesn't slide or spin
            vz = max(vz, 0.0)
        self.yaw += wz * dt

        odom = Odometry()
        odom.header.stamp = self.get_clock().now().to_msg()
        odom.header.frame_id = 'world'
        odom.child_frame_id = 'X3'
        p = odom.pose.pose
        p.position.x, p.position.y, p.position.z = self.x, self.y, self.z
        p.orientation.z, p.orientation.w = math.sin(self.yaw / 2), math.cos(self.yaw / 2)
        v = odom.twist.twist
        v.linear.x, v.linear.y, v.linear.z = vx, vy, vz   # body frame, like Gazebo's
        v.angular.z = wz
        self.pub.publish(odom)
        self.truth_pub.publish(odom)



def main():
    rclpy.init()
    node = FakeDrone()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
