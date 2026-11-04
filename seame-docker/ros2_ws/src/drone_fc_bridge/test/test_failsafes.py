"""
Failsafe tests for fc_bridge: timeout, NaN guard, clamp and sim enable.

Starts fc_bridge on its own, on the wall clock (no Gazebo), with its default
parameters: timeout 0.3 s, max_speed_xy 0.5, max_speed_z 0.3, max_yaw_rate 1.0.
The test node plays both sides: it publishes setpoints on fc/setpoint_velocity
and records what fc_bridge sends on the Gazebo twist topic.
"""
import math
import time
import unittest

from geometry_msgs.msg import Twist, TwistStamped
import launch
import launch_ros.actions
import launch_testing.actions
import pytest
import rclpy
from std_msgs.msg import Bool

TIMEOUT_S = 0.3
TICK_S = 0.05   # fc_bridge rate_hz 20
MARGIN_S = 0.15  # tick, DDS delivery and a slow CI machine


@pytest.mark.launch_test
def generate_test_description():
    fc_bridge = launch_ros.actions.Node(
        package='drone_fc_bridge', executable='fc_bridge', output='screen')
    return launch.LaunchDescription([fc_bridge, launch_testing.actions.ReadyToTest()])


def setpoint(x=0.0, y=0.0, z=0.0, ax=0.0, ay=0.0, yaw=0.0):
    msg = TwistStamped()
    msg.header.frame_id = 'base_link'
    t = msg.twist
    t.linear.x, t.linear.y, t.linear.z = x, y, z
    t.angular.x, t.angular.y, t.angular.z = ax, ay, yaw
    return msg


def is_zero(t: Twist):
    return all(v == 0.0 for v in (t.linear.x, t.linear.y, t.linear.z,
                                  t.angular.x, t.angular.y, t.angular.z))


class TestFailsafes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('fc_bridge_tester')
        cls.pub = cls.node.create_publisher(TwistStamped, '/fc/setpoint_velocity', 10)
        cls.cmds = []      # (receive time, Twist)
        cls.enables = []
        cls.node.create_subscription(
            Twist, '/X3/gazebo/command/twist',
            lambda m: cls.cmds.append((time.monotonic(), m)), 10)
        cls.node.create_subscription(Bool, '/X3/enable', cls.enables.append, 10)
        # Wait until fc_bridge is up and both sides are matched.
        cls.spin(10.0, until=lambda: cls.cmds and cls.pub.get_subscription_count() > 0)

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    @classmethod
    def spin(cls, duration, msg=None, until=None):
        """Spin for duration seconds, publishing msg at 20 Hz if given."""
        end = time.monotonic() + duration
        next_pub = time.monotonic()
        while time.monotonic() < end:
            if msg is not None and time.monotonic() >= next_pub:
                cls.pub.publish(msg)
                next_pub += 0.05
            rclpy.spin_once(cls.node, timeout_sec=0.01)
            if until is not None and until():
                return

    def setUp(self):
        # Every test starts from the failsafe state: no setpoint for well past the timeout.
        self.spin(TIMEOUT_S + 0.5)
        self.cmds.clear()

    def cmds_between(self, start, end):
        return [t for (rx, t) in self.cmds if start <= rx <= end]

    def test_zero_without_setpoints(self):
        self.spin(1.0)
        self.assertGreaterEqual(len(self.cmds), 10, 'fc_bridge must publish every tick')
        self.assertTrue(all(is_zero(t) for _, t in self.cmds))

    def test_fresh_setpoint_is_forwarded(self):
        self.spin(1.0, setpoint(x=0.2, y=-0.1, z=0.1, yaw=0.5))
        t = self.cmds[-1][1]
        self.assertAlmostEqual(t.linear.x, 0.2)
        self.assertAlmostEqual(t.linear.y, -0.1)
        self.assertAlmostEqual(t.linear.z, 0.1)
        self.assertAlmostEqual(t.angular.z, 0.5)

    def test_timeout_sends_zero(self):
        self.spin(1.0, setpoint(x=0.3))
        stop = time.monotonic()
        self.spin(1.0)
        self.assertFalse(is_zero(self.cmds_between(stop - 0.3, stop)[-1]),
                         'setpoint must be followed while fresh')
        early = self.cmds_between(stop, stop + TIMEOUT_S - MARGIN_S)
        self.assertTrue(early and not any(is_zero(t) for t in early),
                        'must not time out before setpoint_timeout_s')
        late = self.cmds_between(stop + TIMEOUT_S + MARGIN_S, stop + 1.0)
        self.assertTrue(late and all(is_zero(t) for t in late),
                        'must send zero after setpoint_timeout_s')

    def test_nan_is_rejected_and_times_out(self):
        self.spin(0.5, setpoint(x=0.3))
        start = time.monotonic()
        self.spin(1.0, setpoint(x=math.nan, z=0.3))
        for _, t in self.cmds:
            self.assertTrue(all(math.isfinite(v) for v in (
                t.linear.x, t.linear.y, t.linear.z, t.angular.x, t.angular.y, t.angular.z)))
        late = self.cmds_between(start + TIMEOUT_S + MARGIN_S, start + 1.0)
        self.assertTrue(late and all(is_zero(t) for t in late),
                        'NaN setpoints must not keep the last good one fresh')

    def test_inf_is_rejected(self):
        self.spin(1.0, setpoint(yaw=math.inf))
        self.assertTrue(all(is_zero(t) for _, t in self.cmds))

    def test_horizontal_clamp_keeps_direction(self):
        self.spin(1.0, setpoint(x=3.0, y=4.0))
        t = self.cmds[-1][1]
        self.assertAlmostEqual(t.linear.x, 0.3)
        self.assertAlmostEqual(t.linear.y, 0.4)

    def test_vertical_and_yaw_clamp(self):
        self.spin(1.0, setpoint(z=2.0, yaw=-5.0))
        t = self.cmds[-1][1]
        self.assertAlmostEqual(t.linear.z, 0.3)
        self.assertAlmostEqual(t.angular.z, -1.0)
        self.spin(1.0, setpoint(z=-2.0, yaw=5.0))
        t = self.cmds[-1][1]
        self.assertAlmostEqual(t.linear.z, -0.3)
        self.assertAlmostEqual(t.angular.z, 1.0)

    def test_roll_and_pitch_rates_are_zeroed(self):
        self.spin(1.0, setpoint(x=0.1, ax=1.0, ay=-1.0))
        t = self.cmds[-1][1]
        self.assertEqual((t.angular.x, t.angular.y), (0.0, 0.0))
        self.assertAlmostEqual(t.linear.x, 0.1)

    def test_sim_enable_is_published(self):
        self.spin(1.5)
        self.assertTrue(self.enables and all(m.data for m in self.enables))
