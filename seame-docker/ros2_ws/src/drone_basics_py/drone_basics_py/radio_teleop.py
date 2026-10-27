"""
RadioMaster Pocket (USB joystick) -> velocity setpoints, arm switch as deadman.

Sim only. On the real drone the radio talks ELRS straight to INAV.

"""
from geometry_msgs.msg import TwistStamped
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Joy

AXES = ('roll', 'pitch', 'throttle', 'yaw')


class RadioTeleop(Node):
    def __init__(self):
        super().__init__('radio_teleop')
        for i, name in enumerate(AXES):
            self.declare_parameter(f'axis_{name}', i)      # joy axis index
            self.declare_parameter(f'sign_{name}', 1.0)    # flip with -1.0
        self.declare_parameter('axis_arm', 4)
        self.declare_parameter('sign_arm', 1.0)            # sign_arm: -1.0 if armed reads negative
        self.declare_parameter('arm_threshold', 0.5)
        self.declare_parameter('deadband', 0.08)
        self.declare_parameter('max_xy', 0.5)    # m/s at full stick
        self.declare_parameter('max_z', 0.3)     # m/s at full stick
        self.declare_parameter('max_yaw', 1.0)   # rad/s at full stick

        self.pub = self.create_publisher(TwistStamped, 'setpoint_velocity', 10)
        self.create_subscription(Joy, 'joy', self.on_joy, 10)
        self.engaged = False

    def p(self, name):
        return self.get_parameter(name).value

    def axis(self, msg, name):
        i = self.p(f'axis_{name}')
        if not 0 <= i < len(msg.axes):
            return 0.0
        v = self.p(f'sign_{name}') * msg.axes[i]
        if abs(v) < self.p('deadband'):
            return 0.0
        return max(-1.0, min(1.0, v))

    def on_joy(self, msg):
        i = self.p('axis_arm')
        switch_on = (0 <= i < len(msg.axes)
                     and self.p('sign_arm') * msg.axes[i] > self.p('arm_threshold'))  # sign_arm

        if not switch_on:
            if self.engaged:
                self.get_logger().info('Arm switch off: not sending, fc_bridge will hold')
            self.engaged = False
            return   # silence -> fc_bridge timeout -> zero velocity

        throttle = self.axis(msg, 'throttle')
        if not self.engaged:
            # Like a real arming check: refuse to engage with the throttle off centre,
            # or flipping the switch would make the drone jump.
            if throttle != 0.0:
                self.get_logger().warn('Centre the throttle stick to engage',
                                       throttle_duration_sec=2.0)
                return
            self.engaged = True
            self.get_logger().info('Engaged: sticks command velocity')

        out = TwistStamped()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = 'base_link'
        out.twist.linear.x = self.p('max_xy') * self.axis(msg, 'pitch')
        out.twist.linear.y = self.p('max_xy') * self.axis(msg, 'roll')
        out.twist.linear.z = self.p('max_z') * throttle
        out.twist.angular.z = self.p('max_yaw') * self.axis(msg, 'yaw')
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = RadioTeleop()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
