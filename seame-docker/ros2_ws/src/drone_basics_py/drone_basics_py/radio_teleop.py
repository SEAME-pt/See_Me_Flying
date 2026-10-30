"""
RadioMaster Pocket (USB joystick) -> velocity setpoints.

Two switches: arm (deadman) and takeover. The sticks command only while both
are on; then the radio outranks any other source in safety_manager. Arm alone
does nothing, so it can be on, ready, while a mission flies. Taking over arms
fc_bridge (fc/arm), so the radio can fly again after a Land disarmed it.

Sim only. On the real drone the radio talks ELRS straight to INAV, where the
takeover switch is the mode switch between the companion (MSP) and the sticks.
"""
from geometry_msgs.msg import TwistStamped
import rclpy
from rclpy._rclpy_pybind11 import RCLError
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_srvs.srv import SetBool

AXES = ('roll', 'pitch', 'throttle', 'yaw')


class RadioTeleop(Node):
    def __init__(self):
        super().__init__('radio_teleop')
        for i, name in enumerate(AXES):
            self.declare_parameter(f'axis_{name}', i)      # joy axis index
            self.declare_parameter(f'sign_{name}', 1.0)    # flip with -1.0
        self.declare_parameter('axis_arm', 4)
        self.declare_parameter('sign_arm', 1.0)            # sign_arm: -1.0 if armed reads negative
        self.declare_parameter('axis_takeover', -1)        # -1: no takeover switch, arm alone
        self.declare_parameter('sign_takeover', 1.0)
        self.declare_parameter('arm_threshold', 0.5)
        self.declare_parameter('arm_hold_s', 0.1)    # switch must read on this long to engage
        self.declare_parameter('deadband', 0.08)
        self.declare_parameter('max_xy', 0.5)    # m/s at full stick
        self.declare_parameter('max_z', 0.3)     # m/s at full stick
        self.declare_parameter('max_yaw', 1.0)   # rad/s at full stick

        self.pub = self.create_publisher(TwistStamped, 'setpoint_velocity', 10)
        self.create_subscription(Joy, 'joy', self.on_joy, 10)
        self.arm_client = self.create_client(SetBool, 'fc/arm')
        self.engaged = False
        self.on_since = None   # joy stamp when the switch last turned on

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

    def switch(self, msg, name):
        i = self.p(f'axis_{name}')
        return (0 <= i < len(msg.axes)
                and self.p(f'sign_{name}') * msg.axes[i] > self.p('arm_threshold'))

    def request_arm(self):
        # After a Land, fc_bridge is disarmed and would ignore the sticks.
        if not self.arm_client.service_is_ready():
            self.get_logger().warn('fc/arm not available: cannot arm', throttle_duration_sec=2.0)
            return
        self.arm_client.call_async(SetBool.Request(data=True))

    def on_joy(self, msg):
        takeover = self.p('axis_takeover') < 0 or self.switch(msg, 'takeover')
        switch_on = self.switch(msg, 'arm') and takeover

        if not switch_on:
            if self.engaged:
                self.get_logger().info('Released: not sending, the mission or fc_bridge holds')
            self.engaged = False
            self.on_since = None
            return   # silence -> fc_bridge timeout -> zero velocity

        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if self.on_since is None:
            self.on_since = stamp

        throttle = self.axis(msg, 'throttle')
        if not self.engaged:
            # Debounce, both switches together: the Pocket's SA bounces for up to
            # ~35 ms when armed slowly.
            # Only arming waits; off above acts at once, so the deadman stays instant.
            # Needs joy_node autorepeat_rate > 0, or a held switch sends no next message.
            if stamp - self.on_since < self.p('arm_hold_s'):
                return
            # Like a real arming check: refuse to engage with the throttle off centre,
            # or flipping the switch would make the drone jump.
            if throttle != 0.0:
                self.get_logger().warn('Centre the throttle stick to engage',
                                       throttle_duration_sec=2.0)
                return
            self.engaged = True
            self.request_arm()
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
    except RCLError:
        # Ctrl-C can shut the context down between two waits; not a crash then.
        if rclpy.ok():
            raise
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
