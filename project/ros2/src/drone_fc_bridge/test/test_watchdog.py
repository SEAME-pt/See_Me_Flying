"""
watchdog: notices when the setpoint stream into fc_bridge stops, and when it is back.

Starts the watchdog as sim.launch.py does (listening to /fc/setpoint_velocity),
on the wall clock, with its default timeout_s 0.5. The test publishes setpoints,
stops, starts again, and reads what the watchdog says on /rosout.
"""
import time
import unittest

from geometry_msgs.msg import TwistStamped
import launch
import launch_ros.actions
import launch_testing.actions
import pytest
from rcl_interfaces.msg import Log
import rclpy

TIMEOUT_S = 0.5
MARGIN_S = 0.4   # the 100 ms check, DDS delivery and a slow CI machine
LOST = 'No setpoint for'
BACK = 'Setpoints are back'


@pytest.mark.launch_test
def generate_test_description():
    watchdog = launch_ros.actions.Node(
        package='drone_fc_bridge', executable='watchdog', output='screen',
        remappings=[('setpoint_velocity', '/fc/setpoint_velocity')])
    return launch.LaunchDescription([watchdog, launch_testing.actions.ReadyToTest()])


class TestWatchdog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('watchdog_tester')
        cls.pub = cls.node.create_publisher(TwistStamped, '/fc/setpoint_velocity', 10)
        cls.said = []   # (receive time, text) of the watchdog's log lines
        cls.node.create_subscription(
            Log, '/rosout',
            lambda m: cls.said.append((time.monotonic(), m.msg)) if m.name == 'watchdog'
            else None, 100)

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def spin(self, duration, publish=False, until=None):
        end = time.monotonic() + duration
        next_pub = time.monotonic()
        while time.monotonic() < end:
            if publish and time.monotonic() >= next_pub:
                self.pub.publish(TwistStamped())
                next_pub += 0.05   # 20 Hz, like the sources
            rclpy.spin_once(self.node, timeout_sec=0.01)
            if until is not None and until():
                return True
        return False

    def said_since(self, start, text):
        return [t for t, msg in self.said if t >= start and text in msg]

    def test_warns_when_the_stream_stops_and_when_it_is_back(self):
        # Nothing published yet: the watchdog has to say so.
        self.assertTrue(self.spin(10.0, until=lambda: self.said_since(0, LOST)),
                        'no warning while nothing was published')

        start = time.monotonic()
        self.assertTrue(self.spin(3.0, publish=True,
                                  until=lambda: self.said_since(start, BACK)),
                        'did not notice the setpoints coming back')
        self.spin(1.0, publish=True)   # a steady stream: no warning
        self.assertEqual(self.said_since(start, LOST), [], 'warned during a steady stream')

        stop = time.monotonic()
        self.assertTrue(self.spin(TIMEOUT_S + MARGIN_S + 1.0,
                                  until=lambda: self.said_since(stop, LOST)),
                        'did not notice the stream stopping')
        delay = self.said_since(stop, LOST)[0] - stop
        self.assertGreaterEqual(delay, TIMEOUT_S - 0.1, 'warned before timeout_s')
        self.assertLessEqual(delay, TIMEOUT_S + MARGIN_S, 'warned too late')
