"""
RadioMaster Pocket (USB joystick) -> velocity setpoints.

Two switches, as on the real drone with INAV:
- Arm (SA) arms and disarms fc_bridge (fc/arm). Off is a kill switch, even in
  flight. Like INAV, it won't arm with the throttle off centre, or when the
  switch was already on at start: flip it off and on again.
- Takeover: while armed, the sticks command and outrank any other source in
  safety_manager. Off hands control back to the mission. Arm alone flies
  nothing, so the radio can be armed and ready while a mission flies.

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
        self.declare_parameter('arm_hold_s', 0.1)    # a switch must read on this long to count
        self.declare_parameter('deadband', 0.08)
        self.declare_parameter('max_xy', 0.5)    # m/s at full stick
        self.declare_parameter('max_z', 0.3)     # m/s at full stick
        self.declare_parameter('max_yaw', 1.0)   # rad/s at full stick

        self.pub = self.create_publisher(TwistStamped, 'setpoint_velocity', 10)
        self.create_subscription(Joy, 'joy', self.on_joy, 10)
        self.arm_client = self.create_client(SetBool, 'fc/arm')
        self.armed = False       # what we asked fc_bridge for
        self.engaged = False     # sticks in command
        self.seen_off = False    # arm switch seen off since start (INAV's arming check)
        self.arm_since = None    # joy stamp when the arm switch last turned on
        self.take_since = None   # same, takeover switch

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

    def set_fc_armed(self, armed):
        if not self.arm_client.service_is_ready():
            self.get_logger().error('fc/arm not available: cannot ' +
                                    ('arm' if armed else 'disarm'))
            return
        self.arm_client.call_async(SetBool.Request(data=armed))

    def on_joy(self, msg):
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        hold = self.p('arm_hold_s')
        throttle = self.axis(msg, 'throttle')
        arm_on = self.switch(msg, 'arm')
        take_on = arm_on if self.p('axis_takeover') < 0 else self.switch(msg, 'takeover')
        # Debounce: a switch counts once it has read on for arm_hold_s without a
        # break (the Pocket's SA bounces for up to ~35 ms). Off acts at once.
        # Needs joy_node autorepeat_rate > 0, or a held switch sends no next message.
        if not arm_on:
            self.arm_since = None
        elif self.arm_since is None:
            self.arm_since = t
        if not take_on:
            self.take_since = None
        elif self.take_since is None:
            self.take_since = t

        if not arm_on:
            self.seen_off = True
            if self.armed:
                self.set_fc_armed(False)
                self.get_logger().warn('Arm switch off: disarmed')
            self.armed = False
        elif not self.armed and t - self.arm_since >= hold:
            if not self.seen_off:
                self.get_logger().warn('Arm switch was on at start: flip it off and on to arm',
                                       throttle_duration_sec=2.0)
            elif throttle != 0.0:
                # Like INAV's arming check: or arming would make the drone jump.
                self.get_logger().warn('Centre the throttle stick to arm',
                                       throttle_duration_sec=2.0)
            else:
                self.armed = True
                self.set_fc_armed(True)
                self.get_logger().info('Armed (arm switch)')

        if not (self.armed and take_on):
            if self.engaged:
                self.get_logger().info('Released: not sending, the mission or fc_bridge holds')
            self.engaged = False
            return   # silence -> the mission keeps control, or fc_bridge times out and holds

        if not self.engaged:
            if t - max(self.arm_since, self.take_since) < hold:
                return
            if throttle != 0.0:
                self.get_logger().warn('Centre the throttle stick to take over',
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
    except RCLError:
        # Ctrl-C can shut the context down between two waits; not a crash then.
        if rclpy.ok():
            raise
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
