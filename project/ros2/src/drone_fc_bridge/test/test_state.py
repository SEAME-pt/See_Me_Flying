"""
State tests for fc_bridge: sim odometry in, fc/odom, fc/attitude, fc/range out.

Starts fc_bridge with all noise set to 0, so the outputs are exact. The test
node plays Gazebo: it publishes odometry on /X3/odom at 50 Hz and records
what fc_bridge publishes. Position is checked as a change over a run, since
fc_bridge integrates it across the whole test.
"""
import math
import time
import unittest

from geometry_msgs.msg import QuaternionStamped
import launch
import launch_ros.actions
import launch_testing.actions
from nav_msgs.msg import Odometry
import pytest
import rclpy
from sensor_msgs.msg import Range

LEVEL = (0.0, 0.0, 0.0, 1.0)                                # x, y, z, w
YAW_90 = (0.0, 0.0, math.sin(math.pi / 4), math.cos(math.pi / 4))
ROLL_60 = (math.sin(math.pi / 6), 0.0, 0.0, math.cos(math.pi / 6))
UPSIDE_DOWN = (1.0, 0.0, 0.0, 0.0)


@pytest.mark.launch_test
def generate_test_description():
    fc_bridge = launch_ros.actions.Node(
        package='drone_fc_bridge', executable='fc_bridge', output='screen',
        parameters=[{'flow_vel_noise': 0.0, 'flow_drift': 0.0, 'range_noise': 0.0}])
    return launch.LaunchDescription([fc_bridge, launch_testing.actions.ReadyToTest()])


class TestState(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('fc_bridge_state_tester')
        cls.pub = cls.node.create_publisher(Odometry, '/X3/odom', 10)
        cls.last = {}
        for topic, kind in [('/fc/odom', Odometry), ('/fc/attitude', QuaternionStamped),
                            ('/fc/range', Range)]:
            cls.node.create_subscription(
                kind, topic, lambda m, t=topic: cls.last.__setitem__(t, m), 10)
        cls.feed(10.0, until=lambda: len(cls.last) == 3)

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    @classmethod
    def feed(cls, duration, x=5.0, y=5.0, z=1.0, q=LEVEL, vx=0.0, vy=0.0, until=None):
        """Publish sim odometry at 50 Hz for duration seconds, stamped with the wall clock."""
        end = time.monotonic() + duration
        next_pub = time.monotonic()
        while time.monotonic() < end:
            if time.monotonic() >= next_pub:
                msg = Odometry()
                msg.header.stamp = cls.node.get_clock().now().to_msg()
                p = msg.pose.pose
                p.position.x, p.position.y, p.position.z = x, y, z
                p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w = q
                msg.twist.twist.linear.x, msg.twist.twist.linear.y = vx, vy
                cls.pub.publish(msg)
                next_pub += 0.02
            rclpy.spin_once(cls.node, timeout_sec=0.005)
            if until is not None and until():
                return
        # Let the last outputs arrive.
        for _ in range(20):
            rclpy.spin_once(cls.node, timeout_sec=0.005)

    def odom(self):
        return self.last['/fc/odom']

    def odom_xyt(self):
        o = self.odom()
        return (o.pose.pose.position.x, o.pose.pose.position.y,
                o.header.stamp.sec + o.header.stamp.nanosec * 1e-9)

    def test_velocity_passes_through(self):
        self.feed(0.5, vx=0.4, vy=-0.2)
        t = self.odom().twist.twist.linear
        self.assertAlmostEqual(t.x, 0.4)
        self.assertAlmostEqual(t.y, -0.2)

    def test_position_is_integrated_not_copied(self):
        # The sim says x = y = 5; fc/odom must ignore that and integrate velocity.
        self.feed(0.3)
        x0, y0, t0 = self.odom_xyt()
        self.assertLess(math.hypot(x0, y0), 4.0, 'fc/odom copied the sim position')
        self.feed(1.0, vx=0.5)
        x1, y1, t1 = self.odom_xyt()
        self.assertAlmostEqual(x1 - x0, 0.5 * (t1 - t0), delta=0.01)
        self.assertAlmostEqual(y1 - y0, 0.0, delta=0.001)

    def test_body_velocity_rotated_by_heading(self):
        # Facing +y (yaw 90 deg), forward body velocity moves the drone along world +y.
        self.feed(0.3, q=YAW_90)
        x0, y0, t0 = self.odom_xyt()
        self.feed(1.0, q=YAW_90, vx=0.5)
        x1, y1, t1 = self.odom_xyt()
        self.assertAlmostEqual(x1 - x0, 0.0, delta=0.001)
        self.assertAlmostEqual(y1 - y0, 0.5 * (t1 - t0), delta=0.01)

    def test_height_and_orientation_from_sim(self):
        self.feed(0.3, z=1.3, q=YAW_90)
        p = self.odom().pose.pose
        self.assertAlmostEqual(p.position.z, 1.3)
        self.assertAlmostEqual(p.orientation.z, YAW_90[2])
        a = self.last['/fc/attitude'].quaternion
        self.assertAlmostEqual(a.z, YAW_90[2])
        self.assertAlmostEqual(a.w, YAW_90[3])

    def test_range_level(self):
        self.feed(0.3, z=1.2)
        r = self.last['/fc/range']
        self.assertAlmostEqual(r.range, 1.2, places=5)
        self.assertAlmostEqual(r.min_range, 0.04, places=5)
        self.assertAlmostEqual(r.max_range, 4.0, places=5)

    def test_range_reads_longer_when_tilted(self):
        self.feed(0.3, z=1.0, q=ROLL_60)
        self.assertAlmostEqual(self.last['/fc/range'].range, 2.0, places=4)

    def test_range_out_of_range_is_inf(self):
        self.feed(0.3, z=5.0)
        self.assertEqual(self.last['/fc/range'].range, math.inf)
        self.feed(0.3, z=0.01)
        self.assertEqual(self.last['/fc/range'].range, -math.inf)
        self.feed(0.3, z=1.0, q=UPSIDE_DOWN)
        self.assertEqual(self.last['/fc/range'].range, math.inf)
