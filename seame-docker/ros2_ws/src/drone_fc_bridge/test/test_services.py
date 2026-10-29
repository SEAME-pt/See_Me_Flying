"""
fc/arm, fc/hold and fc/status of fc_bridge.

Starts fc_bridge alone on the wall clock. The test node calls the services,
publishes setpoints and records the Gazebo twist, the enable topic and fc/status.
"""
import time
import unittest

from drone_interfaces.msg import FcStatus
from geometry_msgs.msg import Twist, TwistStamped
import launch
import launch_ros.actions
import launch_testing.actions
import pytest
import rclpy
from std_msgs.msg import Bool
from std_srvs.srv import SetBool


@pytest.mark.launch_test
def generate_test_description():
    fc_bridge = launch_ros.actions.Node(
        package='drone_fc_bridge', executable='fc_bridge', output='screen')
    return launch.LaunchDescription([fc_bridge, launch_testing.actions.ReadyToTest()])


class TestServices(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('fc_bridge_services_tester')
        cls.pub = cls.node.create_publisher(TwistStamped, '/fc/setpoint_velocity', 10)
        cls.last = {}
        for topic, kind in [('/X3/gazebo/command/twist', Twist), ('/X3/enable', Bool),
                            ('/fc/status', FcStatus)]:
            cls.node.create_subscription(
                kind, topic, lambda m, t=topic: cls.last.__setitem__(t, m), 10)
        cls.arm = cls.node.create_client(SetBool, '/fc/arm')
        cls.hold = cls.node.create_client(SetBool, '/fc/hold')
        assert cls.arm.wait_for_service(timeout_sec=10.0)
        assert cls.hold.wait_for_service(timeout_sec=10.0)
        cls.spin(3.0, until=lambda: len(cls.last) == 3)

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    @classmethod
    def spin(cls, duration, x=None, until=None):
        """Spin for duration s, publishing a setpoint with linear.x = x at 20 Hz if given."""
        end = time.monotonic() + duration
        next_pub = time.monotonic()
        while time.monotonic() < end:
            if x is not None and time.monotonic() >= next_pub:
                msg = TwistStamped()
                msg.twist.linear.x = x
                cls.pub.publish(msg)
                next_pub += 0.05
            rclpy.spin_once(cls.node, timeout_sec=0.01)
            if until is not None and until():
                return

    def call(self, client, value):
        future = client.call_async(SetBool.Request(data=value))
        rclpy.spin_until_future_complete(self.node, future, timeout_sec=5.0)
        self.assertTrue(future.result().success)
        return future.result()

    def status(self):
        return self.last['/fc/status']

    def test_starts_armed(self):
        self.assertTrue(self.status().armed)
        self.assertTrue(self.last['/X3/enable'].data)
        self.assertEqual(self.status().backend, 'sim')

    def test_disarm_and_rearm(self):
        self.call(self.arm, False)
        self.spin(1.5)
        self.assertFalse(self.last['/X3/enable'].data)
        self.assertFalse(self.status().armed)
        self.call(self.arm, True)
        self.spin(1.5)
        self.assertTrue(self.last['/X3/enable'].data)
        self.assertTrue(self.status().armed)

    def test_hold_sends_zero_despite_setpoints(self):
        self.spin(0.5, x=0.2)
        self.assertAlmostEqual(self.last['/X3/gazebo/command/twist'].linear.x, 0.2)
        self.assertTrue(self.status().following_setpoints)
        self.call(self.hold, True)
        self.spin(0.5, x=0.2)
        self.assertEqual(self.last['/X3/gazebo/command/twist'].linear.x, 0.0)
        self.assertTrue(self.status().holding)
        self.assertFalse(self.status().following_setpoints)
        self.call(self.hold, False)
        self.spin(0.5, x=0.2)
        self.assertAlmostEqual(self.last['/X3/gazebo/command/twist'].linear.x, 0.2)
        self.assertFalse(self.status().holding)

    def test_status_reports_setpoint_age(self):
        self.spin(0.3, x=0.1)
        self.spin(0.6)
        self.spin(1.2, until=lambda: self.status().setpoint_age_s > 0.5)
        self.assertGreater(self.status().setpoint_age_s, 0.5)
        self.assertFalse(self.status().following_setpoints)
