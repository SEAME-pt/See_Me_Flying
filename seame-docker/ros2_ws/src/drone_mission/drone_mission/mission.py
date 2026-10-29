"""
mission: takeoff, hold, circle, yaw and land, with height from the rangefinder.

Replaces setpoint_pub. The flight logic lives in logic.py; this node only reads
parameters, feeds it fc/range and fc/odom, and publishes its commands at rate_hz.
Times are the node clock, so with use_sim_time everything follows Gazebo.
"""
from dataclasses import fields

from drone_mission.logic import Mission, Params
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Range


class MissionNode(Node):
    def __init__(self):
        super().__init__('mission')
        rate = self.declare_parameter('rate_hz', 20.0).value
        defaults = Params()
        values = {f.name: self.declare_parameter(f.name, getattr(defaults, f.name)).value
                  for f in fields(Params)}
        self.mission = Mission(Params(**values))   # read once at start

        self.pub = self.create_publisher(TwistStamped, 'setpoint_velocity', 10)
        self.create_subscription(Range, 'fc/range', self.on_range, 10)
        self.create_subscription(Odometry, 'fc/odom', self.on_odom, 10)
        self.create_timer(1.0 / rate, self.tick)
        self.logged = 0
        self.get_logger().info(
            f'Waiting for fc/range; target height {self.mission.p.target_h:.2f} m')

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def on_range(self, msg):
        self.mission.on_range(self.now(), msg.range)

    def on_odom(self, msg):
        q = msg.pose.pose.orientation
        up_z = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
        self.mission.on_odom(self.now(), msg.twist.twist.linear.z, up_z)

    def tick(self):
        cmd = self.mission.step(self.now())
        for _, old, new in self.mission.transitions[self.logged:]:
            h = self.mission.height(self.now())
            where = 'no range' if h is None else f'height {h:.2f} m'
            self.get_logger().info(f'Phase: {old} -> {new} ({where})')
        self.logged = len(self.mission.transitions)
        if cmd is None:
            return   # wait or done: silence, so fc_bridge times out and holds

        out = TwistStamped()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = 'base_link'
        out.twist.linear.x = cmd.vx
        out.twist.linear.y = cmd.vy
        out.twist.linear.z = cmd.vz
        out.twist.angular.z = cmd.yaw_rate
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = MissionNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
