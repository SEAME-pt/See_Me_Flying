"""
Gazebo sensor test: the simulated sensors and the estimator against ground truth.

Starts sim.launch.py headless in room_world with the mission, like
test_sim_flight.py, and measures, in one flight:

  1 the sim comes up                5 a 4 m pass at 0.3 m/s: flow speed, estimate drift
  2 takeoff                         6 a creep at 1 cm/s for 60 s: what the estimate misses
  3 into the carpet lane, y = 2.7   7 a creep at 3 cm/s for 30 s
  4 hover 10 s: height and vz       8 (cross the table)
                                    9 land
                                    
Steps 4 to 7 fly over carpet, away from the room's plain tables, where flow is lost.
Every step prints what it measured. The limits are in LIMITS below, and
SIM_Sensors.md explains them. The steps share one flight, so after a failed
step the rest are skipped.

By hand, in the dev container, after colcon build:
    export ROS_DOMAIN_ID=197 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST GZ_PARTITION=sensor_test
    launch_test src/drone_bringup/test/test_sim_sensors.py
"""
import functools
import math
import os
import signal
import threading
import time
import unittest

from ament_index_python.packages import get_package_share_directory
from drone_interfaces.action import Goto, Land, Takeoff
from drone_interfaces.msg import OpticalFlow
from drone_sim import checks
from geometry_msgs.msg import TwistStamped
import launch
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
import launch_testing.actions
from nav_msgs.msg import Odometry
import pytest
import rclpy
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from sensor_msgs.msg import Range
import yaml

SHARE = get_package_share_directory('drone_bringup')
PASS_SPEED = 0.3     # m/s, the 4 m pass
STEADY = 0.03        # m/s: flow is judged only while the true speed is this close to it
LANE_Y = 2.7         # m, room_world: a carpet lane from wall to wall, clear of every table
LANE_MARGIN = 0.2    # m, how far from the lane still counts as in it
with open(os.path.join(SHARE, 'config', 'sim_test_limits.yaml')) as f:
    LIMITS = yaml.safe_load(f)['sensors']


@pytest.mark.launch_test
def generate_test_description():
    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(SHARE, 'launch', 'sim.launch.py')),
        launch_arguments={'headless': 'true', 'radio': 'false', 'source': 'mission'}.items())
    return launch.LaunchDescription([sim, launch_testing.actions.ReadyToTest()])


def step(test):
    """Skip a step once an earlier one failed: they all share one flight."""
    @functools.wraps(test)
    def run(self):
        if TestSimSensors.failed:
            self.skipTest(f'{TestSimSensors.failed} failed')
        try:
            test(self)
        except unittest.SkipTest:
            raise
        except BaseException:
            TestSimSensors.failed = test.__name__
            raise
    return run


def stop_gazebo():
    """Stop the Gazebo server this test started (launch stops only its shell)."""
    mine = []
    for entry in os.listdir('/proc'):
        if not entry.isdigit():
            continue
        try:
            with open(f'/proc/{entry}/cmdline', 'rb') as f:
                cmd = f.read().replace(b'\0', b' ').decode(errors='replace')
            with open(f'/proc/{entry}/stat') as f:
                ppid = int(f.read().rsplit(')', 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            continue
        if cmd.startswith('gz sim') and ppid != 1:
            mine.append(int(entry))
    for pid in mine:
        os.kill(pid, signal.SIGINT)
    end = time.monotonic() + 10.0
    while time.monotonic() < end and any(os.path.exists(f'/proc/{p}') for p in mine):
        time.sleep(0.2)
    for pid in mine:
        if os.path.exists(f'/proc/{pid}'):
            os.kill(pid, signal.SIGKILL)


def xy(odom):
    p = odom.pose.pose.position
    return p.x, p.y


class TestSimSensors(unittest.TestCase):

    failed = None   # name of the first failed step

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('sim_sensor_tester', parameter_overrides=[
            Parameter('use_sim_time', Parameter.Type.BOOL, True)])
        cls.truth = cls.odom = cls.range = None
        cls.flow_errors = None   # a list while the pass collects, else None
        cls.node.create_subscription(Odometry, '/sim/ground_truth',
                                     lambda m: setattr(cls, 'truth', m), 10)
        cls.node.create_subscription(Odometry, '/fc/odom', lambda m: setattr(cls, 'odom', m), 10)
        cls.node.create_subscription(Range, '/fc/range', lambda m: setattr(cls, 'range', m), 10)
        cls.node.create_subscription(OpticalFlow, '/fc/optical_flow', cls.on_flow, 10)
        cls.manual = cls.node.create_publisher(TwistStamped, '/cmd/manual', 10)
        cls.actions = {name: ActionClient(cls.node, kind, f'/mission/{name}')
                       for name, kind in [('takeoff', Takeoff), ('goto', Goto), ('land', Land)]}
        cls.executor = SingleThreadedExecutor()
        cls.executor.add_node(cls.node)
        threading.Thread(target=cls.executor.spin, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.executor.shutdown()
        cls.node.destroy_node()
        rclpy.shutdown()
        stop_gazebo()

    @classmethod
    def on_flow(cls, msg):
        if cls.flow_errors is None or cls.truth is None or cls.range is None:
            return
        v = cls.truth.twist.twist.linear
        if abs(math.hypot(v.x, v.y) - PASS_SPEED) > STEADY:
            return   # speeding up or slowing down: not the steady pass
        err = checks.flow_velocity_error(msg, cls.range.range, v.x, v.y)
        if err is not None:
            cls.flow_errors.append(err)

    # Helpers

    @staticmethod
    def wait(condition, timeout):
        """Wait for condition() for up to timeout wall-clock seconds."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if condition():
                return True
            time.sleep(0.02)
        return condition()

    def sim_now(self):
        return self.node.get_clock().now().nanoseconds * 1e-9

    def sleep_sim(self, seconds):
        """Wait `seconds` of simulated time (the sim may run slower than real time)."""
        end = self.sim_now() + seconds
        self.assertTrue(self.wait(lambda: self.sim_now() >= end, 10.0 + 5.0 * seconds),
                        'simulated time is not advancing')

    def send(self, name, **fields):
        """Send a goal and wait for its result; return the result."""
        kind = {'takeoff': Takeoff, 'goto': Goto, 'land': Land}[name]
        future = self.actions[name].send_goal_async(kind.Goal(**fields))
        self.assertTrue(self.wait(future.done, 10.0), f'{name}: no answer')
        handle = future.result()
        self.assertTrue(handle.accepted, f'{name} rejected')
        result = handle.get_result_async()
        self.assertTrue(self.wait(result.done, 120.0), f'{name}: no result')
        r = result.result().result
        self.assertTrue(r.success, r.message)
        return r

    def creep(self, speed, sim_seconds, limit):
        """Move forward at `speed` on cmd/manual; return the share the estimate missed."""
        self.sleep_sim(2.0)   # settle into a hover first
        drift = checks.Drift(xy(self.truth), xy(self.odom))
        end = self.sim_now() + sim_seconds
        while self.sim_now() < end:
            msg = TwistStamped()
            msg.twist.linear.x = speed
            self.manual.publish(msg)
            time.sleep(0.05)
        moved, err = drift.update(xy(self.truth), xy(self.odom))
        missed = err / moved if moved > 0.0 else 0.0
        lo, hi = LIMITS[limit]
        print(f'creep {speed * 100:.0f} cm/s for {sim_seconds:.0f} s: truly moved '
              f'{moved:.3f} m, estimate off by {err:.3f} m: missed {missed:.0%} '
              f'(expected {lo:.0%}..{hi:.0%})')
        self.assertGreater(moved, 0.5 * speed * sim_seconds, 'the drone did not creep')
        self.assertGreaterEqual(missed, lo)
        self.assertLessEqual(missed, hi)
        self.sleep_sim(2.0)   # the mission takes over again and holds

    # The flight, in order

    @step
    def test_1_sim_comes_up(self):
        # The first run downloads the X3 model from Fuel, hence the long wait.
        self.assertTrue(self.wait(lambda: None not in (self.truth, self.odom, self.range)
                                  and self.sim_now() > 0.0, 180.0),
                        'no ground truth, fc/odom or fc/range: the sim did not come up')
        for name, client in self.actions.items():
            self.assertTrue(client.wait_for_server(timeout_sec=30.0), f'no mission/{name}')

    @step
    def test_2_takeoff(self):
        end = time.monotonic() + 30.0
        while True:   # retried while the mission waits for a steady rangefinder
            try:
                self.send('takeoff', height=0.0)
                break
            except AssertionError:
                if time.monotonic() > end:
                    raise
                time.sleep(0.5)
        self.sleep_sim(3.0)

    @step
    def test_3_carpet_lane(self):
        # The room's tables are plain: flow is lost over them. The steps that follow
        # fly forward along y = 2.7, which is carpet all the way.
        left = LANE_Y - self.truth.pose.pose.position.y
        self.send('goto', forward=0.0, left=left, yaw=0.0, speed=0.0)
        self.sleep_sim(2.0)
        y = self.truth.pose.pose.position.y
        print(f'carpet lane: moved {left:+.2f} m sideways, now at y = {y:.2f} m '
              f'(lane at {LANE_Y:.2f} m)')
        self.assertLess(abs(y - LANE_Y), LANE_MARGIN, 'not in the carpet lane')

    @step
    def test_4_hover(self):
        dz, vz = [], []
        end = self.sim_now() + 10.0
        while self.sim_now() < end:
            dz.append(self.odom.pose.pose.position.z - self.truth.pose.pose.position.z)
            vz.append(self.odom.twist.twist.linear.z)
            self.sleep_sim(0.1)
        dz_mean, dz_std = checks.mean_std(dz)
        _, vz_std = checks.mean_std(vz)
        print(f'hover 10 s: height error {dz_mean:+.3f} m (sd {dz_std:.3f}), '
              f'vertical speed sd {vz_std:.3f} m/s')
        self.assertLess(abs(dz_mean), LIMITS['hover_height_mean'])
        self.assertLess(dz_std, LIMITS['hover_height_std'])
        self.assertLess(vz_std, LIMITS['hover_vz_std'])

    @step
    def test_5_pass(self):
        drift = checks.Drift(xy(self.truth), xy(self.odom))
        cls = type(self)   # launch_test runs a copy of this class: use the copy
        cls.flow_errors = []
        self.send('goto', forward=4.0, left=0.0, yaw=0.0, speed=PASS_SPEED)
        errors, cls.flow_errors = cls.flow_errors, None
        moved, err = drift.update(xy(self.truth), xy(self.odom))
        mean, std = checks.mean_std([e[0] for e in errors])
        print(f'4 m pass: {len(errors)} steady flow samples, speed error {mean:+.3f} m/s '
              f'(sd {std:.3f}); truly moved {moved:.3f} m, estimate off by {err:.3f} m')
        self.assertGreater(len(errors), 20, 'too few steady flow samples')
        self.assertLess(abs(mean), LIMITS['flow_mean'])
        self.assertLess(std, LIMITS['flow_std'])
        self.assertLess(err, LIMITS['pass_error'])

    @step
    def test_6_creep_1cm(self):
        self.creep(0.01, 60.0, 'creep_1cm')

    @step
    def test_7_creep_3cm(self):
        self.creep(0.03, 30.0, 'creep_3cm')

    @step
    def test_8_land(self):
        self.send('land')
