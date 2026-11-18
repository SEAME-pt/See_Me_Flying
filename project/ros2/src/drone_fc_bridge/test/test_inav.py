"""
fc_bridge with backend:=inav, the stub for the real drone.

Starts fc_bridge alone on the wall clock. ROS must not be able to arm it, and
none of the sim's topics may appear: nothing reaches Gazebo or its enable topic.
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
        package='drone_fc_bridge', executable='fc_bridge', output='screen',
        parameters=[{'backend': 'inav', 'armed_at_start': True}])
    return launch.LaunchDescription([fc_bridge, launch_testing.actions.ReadyToTest()])


class TestInav(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('fc_bridge_inav_tester')
        cls.pub = cls.node.create_publisher(TwistStamped, '/fc/setpoint_velocity', 10)
        cls.seen = {}
        for topic, kind in [('/X3/gazebo/command/twist', Twist), ('/X3/enable', Bool),
                            ('/fc/status', FcStatus)]:
            cls.node.create_subscription(
                kind, topic, lambda m, t=topic: cls.seen.setdefault(t, []).append(m), 10)
        cls.arm = cls.node.create_client(SetBool, '/fc/arm')
        assert cls.arm.wait_for_service(timeout_sec=10.0)
        # Setpoints for 2 s: the sim backend would forward them to Gazebo.
        end = time.monotonic() + 2.0
        while time.monotonic() < end:
            msg = TwistStamped()
            msg.twist.linear.x = 0.2
            cls.pub.publish(msg)
            rclpy.spin_once(cls.node, timeout_sec=0.05)

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def test_status_says_inav_and_disarmed(self):
        status = self.seen['/fc/status'][-1]
        self.assertEqual(status.backend, 'inav')
        self.assertFalse(status.armed, 'armed_at_start must not apply to the real drone')

    def test_arm_is_refused(self):
        for value in (True, False):
            future = self.arm.call_async(SetBool.Request(data=value))
            rclpy.spin_until_future_complete(self.node, future, timeout_sec=5.0)
            self.assertFalse(future.result().success)
            self.assertIn('radio', future.result().message)

    def test_nothing_reaches_the_sim(self):
        self.assertNotIn('/X3/gazebo/command/twist', self.seen)
        self.assertNotIn('/X3/enable', self.seen)
        self.assertEqual(self.node.count_publishers('/X3/enable'), 0)
        self.assertEqual(self.node.count_publishers('/X3/gazebo/command/twist'), 0)
