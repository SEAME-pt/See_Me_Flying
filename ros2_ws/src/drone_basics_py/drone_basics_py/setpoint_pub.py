import math

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped


class SetpointPub(Node):
    def __init__(self):
        super().__init__('setpoint_pub')
        self.declare_parameter('rate_hz', 10.0)
        self.declare_parameter('speed', 0.3)  # m/s
        rate = self.get_parameter('rate_hz').value
        self.pub = self.create_publisher(TwistStamped, 'setpoint_velocity', 10)
        self.t0 = self.get_clock().now()
        self.timer = self.create_timer(1.0 / rate, self.tick)

    def tick(self):
        now = self.get_clock().now()
        t = (now - self.t0).nanoseconds * 1e-9
        speed = self.get_parameter('speed').value  # read each tick: tunable live
        msg = TwistStamped()
        msg.header.stamp = now.to_msg()
        msg.header.frame_id = 'base_link'
        msg.twist.linear.x = speed * math.cos(0.5 * t)
        msg.twist.linear.y = speed * math.sin(0.5 * t)
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SetpointPub()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()