"""
The whole ROS stack without Gazebo: mission, safety_manager and fc_bridge.

The three real nodes start as sim.launch.py starts them, with config/sim.yaml,
on the wall clock. fake_drone.py plays Gazebo: it flies at what fc_bridge sends
the X3 and publishes /X3/odom, from which fc_bridge makes fc/odom and fc/range
as it does in the sim. This test flies with real Takeoff, Goto and Land actions,
plays the radio on cmd/radio, and disarms through fc/arm as the arm switch would.
/X3/odom is the true pose, so the test checks where the drone really went.

  test: actions ---> mission --cmd/mission--> safety_manager --> fc_bridge --> fake_drone
                       ^                          ^                  |  ^          |
  test: radio ---------|--------- cmd/radio ------+                  |  +- /X3/odom+
                       +------------ fc/range, fc/odom, fc/status ---+
"""
import math
import os
import sys
import threading
import time
import unittest

from ament_index_python.packages import get_package_share_directory
from drone_interfaces.action import Goto, Land, Takeoff
from drone_interfaces.msg import FcStatus
from geometry_msgs.msg import Twist, TwistStamped
import launch
import launch_ros.actions
import launch_testing.actions
from nav_msgs.msg import Odometry
import pytest
import rclpy
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import String
from std_srvs.srv import SetBool
import yaml

PARAMS = os.path.join(get_package_share_directory('drone_bringup'), 'config', 'sim.yaml')
with open(PARAMS) as f:
    CONFIG = {node: v['ros__parameters'] for node, v in yaml.safe_load(f).items()}
FC = CONFIG['fc_bridge']
TARGET_H = CONFIG['mission']['target_h']
REST_Z = 0.05       # m: the X3 on its legs (the sim reads about 0.05 on the ground)


@pytest.mark.launch_test
def generate_test_description():
    clock = {'use_sim_time': False}
    fake_drone = launch.actions.ExecuteProcess(
        cmd=[sys.executable, os.path.join(os.path.dirname(__file__), 'fake_drone.py'),
             '--ros-args', '-p', f'rest_z:={REST_Z}'],
        output='screen')
    nodes = [
        # armed_at_start false and radio_arms true: like the real drone, only the
        # radio arms (here the test, through fc/arm).
        launch_ros.actions.Node(
            package='drone_fc_bridge', executable='fc_bridge', output='screen',
            parameters=[PARAMS, clock, {'backend': 'sim', 'armed_at_start': False}]),
        launch_ros.actions.Node(
            package='drone_safety', executable='safety_manager', output='screen',
            parameters=[PARAMS, clock]),
        launch_ros.actions.Node(
            package='drone_mission', executable='mission', output='screen',
            remappings=[('setpoint_velocity', '/cmd/mission')],
            parameters=[PARAMS, clock, {'radio_arms': True}]),
    ]
    return launch.LaunchDescription(
        [fake_drone] + nodes + [launch_testing.actions.ReadyToTest()])


class TestStack(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('stack_tester')
        cls.radio = cls.node.create_publisher(TwistStamped, '/cmd/radio', 10)
        cls.arm_client = cls.node.create_client(SetBool, '/fc/arm')
        cls.actions = {name: ActionClient(cls.node, kind, f'/mission/{name}')
                       for name, kind in [('takeoff', Takeoff), ('goto', Goto), ('land', Land)]}
        cls.truth = None                        # last /X3/odom: where the drone really is
        cls.status = None
        cls.active = None
        cls.mission_msgs = 0                    # commands the mission has sent so far
        cls.max_cmd = [0.0, 0.0, 0.0]           # largest xy, |z|, |yaw rate| sent to the X3
        cls.node.create_subscription(Odometry, '/X3/odom',
                                     lambda m: setattr(cls, 'truth', m), 10)
        cls.node.create_subscription(Twist, '/X3/gazebo/command/twist', cls.on_x3_cmd, 10)
        cls.node.create_subscription(FcStatus, '/fc/status',
                                     lambda m: setattr(cls, 'status', m), 10)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        cls.node.create_subscription(String, '/safety/active_source',
                                     lambda m: setattr(cls, 'active', m.data), latched)
        cls.node.create_subscription(TwistStamped, '/cmd/mission', cls.on_mission_cmd, 10)

        cls.executor = MultiThreadedExecutor()
        cls.executor.add_node(cls.node)
        cls.spinner = threading.Thread(target=cls.executor.spin, daemon=True)
        cls.spinner.start()

        assert cls.arm_client.wait_for_service(timeout_sec=15.0), 'fc_bridge did not start'
        for name, client in cls.actions.items():
            assert client.wait_for_server(timeout_sec=15.0), f'mission/{name} did not start'
        assert cls.wait(lambda: None not in (cls.truth, cls.status, cls.active), 10.0)

    @classmethod
    def tearDownClass(cls):
        cls.executor.shutdown()
        cls.node.destroy_node()
        rclpy.shutdown()

    @classmethod
    def on_x3_cmd(cls, msg):
        m = cls.max_cmd
        m[0] = max(m[0], math.hypot(msg.linear.x, msg.linear.y))
        m[1] = max(m[1], abs(msg.linear.z))
        m[2] = max(m[2], abs(msg.angular.z))

    @classmethod
    def on_mission_cmd(cls, _msg):
        cls.mission_msgs += 1

    @staticmethod
    def wait(condition, timeout):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if condition():
                return True
            time.sleep(0.02)
        return condition()

    # Helpers

    def setUp(self):
        # Every test starts on the ground, disarmed, nothing commanding.
        self.set_armed(False)
        self.assertTrue(self.wait(self.on_ground, 10.0))
        self.assertTrue(self.wait(lambda: self.active == 'none', 5.0))

    def tearDown(self):
        self.set_armed(False)                   # whatever happened, it comes down

    def pose(self):
        """Return the true (x, y, z, yaw) of the drone, from /X3/odom."""
        p = self.truth.pose.pose
        return (p.position.x, p.position.y, p.position.z,
                2.0 * math.atan2(p.orientation.z, p.orientation.w))

    def moved(self, start):
        """
        Return (forward, left, turned) since `start`, in the heading it had at `start`.

        The fake drone keeps its pose from test to test, so never compare world x, y.
        """
        x0, y0, _, yaw0 = start
        x, y, _, yaw = self.pose()
        c, s = math.cos(yaw0), math.sin(yaw0)
        turned = (yaw - yaw0 + math.pi) % (2 * math.pi) - math.pi
        return c * (x - x0) + s * (y - y0), -s * (x - x0) + c * (y - y0), turned

    def on_ground(self):
        return self.pose()[2] <= REST_Z + 1e-6

    def set_armed(self, armed):
        future = self.arm_client.call_async(SetBool.Request(data=armed))
        self.assertTrue(self.wait(future.done, 5.0))
        self.assertTrue(future.result().success)
        self.assertTrue(self.wait(lambda: self.status.armed == armed, 3.0))

    def send(self, name, **fields):
        """Send a goal; return (accepted, result future)."""
        kind = {'takeoff': Takeoff, 'goto': Goto, 'land': Land}[name]
        future = self.actions[name].send_goal_async(kind.Goal(**fields))
        self.assertTrue(self.wait(future.done, 5.0), f'{name}: no answer')
        handle = future.result()
        return handle.accepted, (handle.get_result_async() if handle.accepted else None)

    def finish(self, result_future, timeout):
        self.assertTrue(self.wait(result_future.done, timeout), 'goal did not finish in time')
        return result_future.result().result

    def goto(self, forward=0.0, left=0.0, yaw=0.0, speed=0.0):
        accepted, result = self.send('goto', forward=forward, left=left, yaw=yaw, speed=speed)
        self.assertTrue(accepted, 'Goto rejected while hovering')
        return result

    def take_off(self):
        """Arm as the radio does, then Takeoff (retried while the rangefinder settles)."""
        self.set_armed(True)
        end = time.monotonic() + 5.0
        while True:
            accepted, result = self.send('takeoff', height=0.0)
            if accepted or time.monotonic() > end:
                break
            time.sleep(0.2)
        self.assertTrue(accepted, 'Takeoff rejected while armed on the ground')
        r = self.finish(result, 30.0)
        self.assertTrue(r.success, r.message)
        return r

    def land(self):
        accepted, result = self.send('land')
        self.assertTrue(accepted)
        r = self.finish(result, 30.0)
        self.assertTrue(r.success, r.message)
        self.assertTrue(self.wait(self.on_ground, 2.0))

    def play_radio(self, seconds, vx=0.0):
        """Stick commands on cmd/radio at 20 Hz, as radio_teleop sends them."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            msg = TwistStamped()
            msg.header.stamp = self.node.get_clock().now().to_msg()
            msg.twist.linear.x = vx
            self.radio.publish(msg)
            time.sleep(0.05)

    def assert_within_limits(self):
        xy, z, yaw = self.max_cmd
        self.assertLessEqual(xy, FC['max_speed_xy'] + 1e-6)
        self.assertLessEqual(z, FC['max_speed_z'] + 1e-6)
        self.assertLessEqual(yaw, FC['max_yaw_rate'] + 1e-6)

    # Tests

    def test_takeoff_refused_until_armed(self):
        # radio_arms: the mission never arms the drone itself.
        accepted, _ = self.send('takeoff', height=0.0)
        self.assertFalse(accepted)
        time.sleep(1.0)
        self.assertTrue(self.on_ground())

    def test_full_flight(self):
        r = self.take_off()
        start = self.pose()
        self.assertAlmostEqual(start[2], TARGET_H, delta=0.1)
        self.assertAlmostEqual(r.height, TARGET_H, delta=0.1)
        self.assertEqual(self.active, 'mission')

        # 1 m forward: the drone really moves 1 m ahead and keeps its height.
        r = self.finish(self.goto(forward=1.0), 20.0)
        self.assertTrue(r.success, r.message)
        forward, left, _ = self.moved(start)
        self.assertAlmostEqual(forward, 1.0, delta=0.2)
        self.assertAlmostEqual(left, 0.0, delta=0.2)
        self.assertAlmostEqual(self.pose()[2], TARGET_H, delta=0.1)

        # Turn left 90 deg, then 1 m forward: it goes to the old left (body frame to world).
        start = self.pose()
        self.assertTrue(self.finish(self.goto(yaw=math.pi / 2), 20.0).success)
        self.assertAlmostEqual(self.moved(start)[2], math.pi / 2, delta=0.1)
        self.assertTrue(self.finish(self.goto(forward=1.0), 20.0).success)
        forward, left, _ = self.moved(start)
        self.assertAlmostEqual(forward, 0.0, delta=0.2)
        self.assertAlmostEqual(left, 1.0, delta=0.2)

        # Asking for 2 m/s: it still arrives, and fc_bridge caps the speed.
        self.assertTrue(self.finish(self.goto(forward=1.0, speed=2.0), 20.0).success)

        self.land()
        self.assert_within_limits()

    def test_radio_takes_over_and_gives_back(self):
        self.take_off()
        result = self.goto(forward=3.0)
        time.sleep(1.0)

        # Takeover: the radio flies backwards; the Goto stops, the mission goes quiet.
        # The sticks play in the background; every check below runs while they do.
        start = self.pose()
        sticks = threading.Thread(target=self.play_radio, args=(3.0, -0.3))
        sticks.start()
        try:
            self.assertTrue(self.wait(lambda: self.active == 'radio', 1.0))
            r = self.finish(result, 2.0)
            self.assertFalse(r.success)
            self.assertIn('overridden', r.message)
            sent = self.mission_msgs
            accepted, _ = self.send('goto', forward=1.0, left=0.0, yaw=0.0, speed=0.0)
            self.assertFalse(accepted, 'Goto accepted while the radio has control')
            time.sleep(1.5)
            self.assertEqual(self.mission_msgs, sent, 'mission kept publishing under the radio')
            self.assertEqual(self.active, 'radio')
        finally:
            sticks.join()
        self.assertLess(self.moved(start)[0], -0.4, 'the drone did not follow the radio')

        # Sticks released: control comes back, the mission holds where the radio left it.
        self.assertTrue(self.wait(lambda: self.active == 'mission', 2.0))
        z = self.pose()[2]
        time.sleep(1.0)
        self.assertAlmostEqual(self.pose()[2], z, delta=0.05)
        self.land()
        self.assert_within_limits()

    def test_disarm_mid_flight(self):
        self.take_off()
        result = self.goto(forward=3.0)
        time.sleep(1.0)

        # The kill switch: the motors stop, the drone drops, the mission gives up.
        self.set_armed(False)
        r = self.finish(result, 2.0)
        self.assertFalse(r.success)
        self.assertIn('disarmed', r.message)
        self.assertTrue(self.wait(self.on_ground, 3.0))
        self.assertTrue(self.wait(lambda: self.active == 'none', 2.0))
        sent = self.mission_msgs
        time.sleep(1.0)
        self.assertEqual(self.mission_msgs, sent, 'mission still commanding after disarm')
        accepted, _ = self.send('takeoff', height=0.0)
        self.assertFalse(accepted, 'Takeoff accepted while disarmed')

    @unittest.skip('Known bug in drone_mission/logic.py, tracked as a strict xfail in '
                   'drone_mission/test/test_logic.py (test_disarm_while_overridden_is_not_'
                   'forgotten). Fix it, then remove this skip.')
    def test_disarm_while_the_radio_flies(self):
        # on_armed ignores a disarm while the mission is overridden. If control comes
        # back while the drone is still falling, the mission goes to hold and keeps
        # commanding a climb, disarmed on the ground; re-armed, it would climb alone.
        # A skip, not expectedFailure: launch_testing reports that as a failure.
        self.take_off()
        try:
            self.play_radio(0.5)                # the pilot takes over...
            self.set_armed(False)               # ...and hits the kill switch
            self.assertTrue(self.wait(self.on_ground, 3.0))
            time.sleep(0.5)
            sent = self.mission_msgs
            time.sleep(1.0)
            self.assertEqual(self.mission_msgs, sent, 'mission commanding a disarmed drone')
        finally:
            # Leave the mission grounded for the next test: Land ends its bogus hold.
            accepted, result = self.send('land')
            if accepted:
                self.finish(result, 10.0)
