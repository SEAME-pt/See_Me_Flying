"""
Gazebo flight test: the whole sim, headless, flown with real Takeoff, Goto and Land.

Starts sim.launch.py headless:=true radio:=false (no window; no radio, so the
mission arms on Takeoff and disarms after Land) and flies it step by step. Every
check uses Gazebo's ground truth (/sim/ground_truth), not the drone's own estimate:

  1 the sim comes up             5 a square: 1 m forward and a quarter turn left, 4 times
  2 on the ground at the start   6 a Goto asking for 2 m/s is capped at max_speed_xy
  3 takeoff to target_h          7 land; the mission disarms
  4 hover 10 s with little drift 8 the mission node dies mid-Goto: fc_bridge stops the
                                   drone; then it is landed by hand on cmd/manual
Speeds are watched for the whole flight: never above the fc_bridge limits.
The steps share one flight, so after a failed step the rest are skipped.

Too slow for every PR (about 2 min, plus Gazebo), so colcon test does not run it:
the nightly workflow does (.github/workflows/nightly.yml), through
seame-docker/scripts/sim_flight_test.sh, which you can run on the host too.
By hand, in the dev container, after colcon build:
    export ROS_DOMAIN_ID=196 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST GZ_PARTITION=flight_test
    launch_test src/drone_bringup/test/test_sim_flight.py
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
from drone_interfaces.msg import FcStatus
from geometry_msgs.msg import Twist, TwistStamped
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
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import Range
from std_msgs.msg import String
from std_srvs.srv import SetBool
import yaml

SHARE = get_package_share_directory('drone_bringup')
with open(os.path.join(SHARE, 'config', 'sim.yaml')) as f:
    CONFIG = {node: v['ros__parameters'] for node, v in yaml.safe_load(f).items()}
FC = CONFIG['fc_bridge']
MISSION = CONFIG['mission']
TARGET_H = MISSION['target_h']
SIDE = CONFIG['demo_flight']['side']    # the demo's square
SPEED_MARGIN = 1.10                     # Gazebo's true speed may overshoot a command by 10 %


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
        if TestSimFlight.failed:
            self.skipTest(f'{TestSimFlight.failed} failed')
        try:
            test(self)
        except unittest.SkipTest:
            raise
        except BaseException:
            TestSimFlight.failed = test.__name__
            raise
    return run


def started_here():
    """Return {pid: command line} of every process this test started, at any depth."""
    parent, cmdline = {}, {}
    for entry in os.listdir('/proc'):
        if not entry.isdigit():
            continue
        try:
            with open(f'/proc/{entry}/stat') as f:
                parent[int(entry)] = int(f.read().rsplit(')', 1)[1].split()[1])
            with open(f'/proc/{entry}/cmdline', 'rb') as f:
                cmdline[int(entry)] = f.read().replace(b'\0', b' ').decode(errors='replace')
        except (OSError, ValueError, IndexError):
            continue                                # exited meanwhile
    mine = {}
    for pid in parent:
        p = parent[pid]
        while p in parent and p != os.getpid():
            p = parent[p]
        if p == os.getpid():
            mine[pid] = cmdline.get(pid, '')
    return mine


def stop_gazebo():
    """
    Stop the Gazebo server this test started.

    ros_gz_sim runs it through a shell, and launch stops only that shell: the
    server would outlive the test, and the next run would refuse to start.
    """
    pids = [pid for pid, cmd in started_here().items() if cmd.startswith('gz sim')]
    for pid in pids:
        os.kill(pid, signal.SIGINT)
    end = time.monotonic() + 10.0
    while time.monotonic() < end and any(os.path.exists(f'/proc/{p}') for p in pids):
        time.sleep(0.2)
    for pid in pids:
        if os.path.exists(f'/proc/{pid}'):
            os.kill(pid, signal.SIGKILL)


class TestSimFlight(unittest.TestCase):

    failed = None   # name of the first failed step

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('sim_flight_tester', parameter_overrides=[
            Parameter('use_sim_time', Parameter.Type.BOOL, True)])
        cls.truth = cls.status = cls.range = cls.active = None
        cls.max_true = [0.0, 0.0, 0.0]          # whole flight: xy speed, |vz|, |yaw rate|
        cls.max_step = [0.0, 0.0, 0.0]          # the same, since reset_step_max()
        cls.max_cmd = [0.0, 0.0, 0.0]           # what fc_bridge sent the X3
        cls.node.create_subscription(Odometry, '/sim/ground_truth', cls.on_truth, 10)
        cls.node.create_subscription(Twist, '/X3/gazebo/command/twist', cls.on_cmd, 10)
        cls.node.create_subscription(FcStatus, '/fc/status',
                                     lambda m: setattr(cls, 'status', m), 10)
        cls.node.create_subscription(Range, '/fc/range', lambda m: setattr(cls, 'range', m), 10)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        cls.node.create_subscription(String, '/safety/active_source',
                                     lambda m: setattr(cls, 'active', m.data), latched)
        cls.manual = cls.node.create_publisher(TwistStamped, '/cmd/manual', 10)
        cls.arm_client = cls.node.create_client(SetBool, '/fc/arm')
        cls.actions = {name: ActionClient(cls.node, kind, f'/mission/{name}')
                       for name, kind in [('takeoff', Takeoff), ('goto', Goto), ('land', Land)]}
        # Single-threaded: rclpy's multi-threaded executor can stall for a second.
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
    def on_truth(cls, msg):
        cls.truth = msg
        v, w = msg.twist.twist.linear, msg.twist.twist.angular
        if abs(v.z) > cls.max_true[1]:            # where the fastest climb or descent was
            cls.max_vz_at = (cls.node.get_clock().now().nanoseconds * 1e-9,
                             msg.pose.pose.position.z)
        for m in (cls.max_true, cls.max_step):
            m[0] = max(m[0], math.hypot(v.x, v.y))
            m[1] = max(m[1], abs(v.z))
            m[2] = max(m[2], abs(w.z))

    @classmethod
    def on_cmd(cls, msg):
        m = cls.max_cmd
        m[0] = max(m[0], math.hypot(msg.linear.x, msg.linear.y))
        m[1] = max(m[1], abs(msg.linear.z))
        m[2] = max(m[2], abs(msg.angular.z))

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

    def pose(self):
        """Return the true (x, y, z, roll, pitch, yaw) from Gazebo."""
        p, q = self.truth.pose.pose.position, self.truth.pose.pose.orientation
        roll = math.atan2(2 * (q.w * q.x + q.y * q.z), 1 - 2 * (q.x * q.x + q.y * q.y))
        pitch = math.asin(max(-1.0, min(1.0, 2 * (q.w * q.y - q.z * q.x))))
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        return p.x, p.y, p.z, roll, pitch, yaw

    def speed(self):
        v = self.truth.twist.twist.linear
        return math.hypot(v.x, v.y)

    def moved(self, start):
        """
        Return (forward, left, turned) since `start`, in the heading it had at `start`.

        Goto is relative to the drone's heading, so this is what it promises.
        """
        x0, y0, _, _, _, yaw0 = start
        x, y, _, _, _, yaw = self.pose()
        c, s = math.cos(yaw0), math.sin(yaw0)
        turned = (yaw - yaw0 + math.pi) % (2 * math.pi) - math.pi
        return c * (x - x0) + s * (y - y0), -s * (x - x0) + c * (y - y0), turned

    def assert_upright(self):
        _, _, _, roll, pitch, _ = self.pose()
        self.assertLess(abs(roll), 0.1, 'not upright')
        self.assertLess(abs(pitch), 0.1, 'not upright')

    def reset_step_max(self):
        self.max_step[:] = [0.0, 0.0, 0.0]

    def send(self, name, **fields):
        """Send a goal; return (accepted, result future)."""
        kind = {'takeoff': Takeoff, 'goto': Goto, 'land': Land}[name]
        future = self.actions[name].send_goal_async(kind.Goal(**fields))
        self.assertTrue(self.wait(future.done, 10.0), f'{name}: no answer')
        handle = future.result()
        return handle.accepted, (handle.get_result_async() if handle.accepted else None)

    def finish(self, result_future, sim_seconds):
        """Wait for a goal's result, allowing `sim_seconds` of simulated time."""
        end = self.sim_now() + sim_seconds
        self.assertTrue(self.wait(lambda: result_future.done() or self.sim_now() > end,
                                  10.0 + 5.0 * sim_seconds))
        self.assertTrue(result_future.done(), f'no result after {sim_seconds} s of sim time')
        return result_future.result().result

    def goto(self, **fields):
        goal = {'forward': 0.0, 'left': 0.0, 'yaw': 0.0, 'speed': 0.0, **fields}
        accepted, result = self.send('goto', **goal)
        self.assertTrue(accepted, 'Goto rejected while hovering')
        r = self.finish(result, 40.0)
        self.assertTrue(r.success, r.message)
        return r

    def take_off(self):
        """Takeoff to target_h, retried while the mission waits for a steady rangefinder."""
        end = time.monotonic() + 30.0
        while True:
            accepted, result = self.send('takeoff', height=0.0)
            if accepted or time.monotonic() > end:
                break
            time.sleep(0.5)
        self.assertTrue(accepted, 'Takeoff rejected on the ground')
        r = self.finish(result, 30.0)
        self.assertTrue(r.success, r.message)
        return r

    # The flight, in order

    @step
    def test_1_sim_comes_up(self):
        # The first run downloads the X3 model from Fuel, hence the long wait.
        self.assertTrue(self.wait(lambda: None not in (self.truth, self.status, self.range)
                                  and self.sim_now() > 0.0, 180.0),
                        'no ground truth, fc/status or fc/range: Gazebo did not come up')
        for name, client in self.actions.items():
            self.assertTrue(client.wait_for_server(timeout_sec=30.0), f'no mission/{name}')
        self.assertTrue(self.arm_client.wait_for_service(timeout_sec=30.0))
        self.assertEqual(self.status.backend, 'sim')
        t = self.sim_now()
        self.sleep_sim(1.0)
        self.assertGreater(self.sim_now(), t)

    @step
    def test_2_on_the_ground_at_start(self):
        _, _, z, _, _, _ = self.pose()
        self.assertLess(z, MISSION['ground_h'], 'not on the ground')
        self.assertLess(self.range.range, MISSION['ground_h'])   # -inf counts: below min range
        self.assertLess(self.speed(), 0.02)
        self.assert_upright()
        TestSimFlight.ground_z = z
        print(f'on the ground: z {z:.3f} m, range {self.range.range:.3f} m')

    @step
    def test_3_takeoff(self):
        # Speeds count from here: the model settling onto the ground when Gazebo
        # starts is not flying.
        self.max_true[:] = [0.0, 0.0, 0.0]
        TestSimFlight.takeoff_at = self.sim_now()
        r = self.take_off()
        _, _, z, _, _, _ = self.pose()
        print(f'takeoff: true height {z:.3f} m, rangefinder {r.height:.3f} m')
        self.assertAlmostEqual(z, TARGET_H, delta=0.1)
        self.assertAlmostEqual(r.height, TARGET_H, delta=0.1)
        self.assertTrue(self.status.armed)
        self.assert_upright()

    @step
    def test_4_hover_drift(self):
        # Takeoff ends within `tolerance` of the target; hold then finishes the climb.
        settle = self.heights(3.0)
        self.assertLess(max(settle), TARGET_H + 0.1, 'overshoots the target height')
        start = self.pose()
        hover = self.heights(10.0)
        forward, left, turned = self.moved(start)
        drift = math.hypot(forward, left)
        print(f'hover 10 s: drift {drift:.3f} m, height {min(hover):.3f}..{max(hover):.3f} m '
              f'(after the climb: up to {max(settle):.3f} m), '
              f'turned {math.degrees(turned):.1f} deg')
        self.assertLess(drift, 0.1)
        self.assertLess(abs(turned), 0.05)
        self.assertGreater(min(hover), TARGET_H - 0.05)
        self.assertLess(max(hover), TARGET_H + 0.05)

    def heights(self, sim_seconds):
        """Sample the true height every 0.1 s of sim time, for `sim_seconds`."""
        samples = [self.pose()[2]]
        end = self.sim_now() + sim_seconds
        while self.sim_now() < end:
            self.sleep_sim(0.1)
            samples.append(self.pose()[2])
        return samples

    @step
    def test_5_square(self):
        # A Goto ends within pos_tolerance / yaw_tolerance of its target, and each one
        # starts from where the last ended, so four quarter turns may add up to four
        # yaw_tolerances. Sides get 0.1 m more for the flow estimate's drift.
        side_tol = MISSION['pos_tolerance'] + 0.1
        turn_tol = MISSION['yaw_tolerance'] + 0.02
        corner = square_start = self.pose()
        for leg in range(4):
            self.goto(forward=SIDE)
            forward, left, _ = self.moved(corner)
            before = self.pose()
            self.goto(yaw=math.pi / 2)
            turned = self.moved(before)[2]
            print(f'side {leg + 1}: forward {forward:.3f} m, left {left:.3f} m, height '
                  f'{before[2]:.3f} m, then turned {math.degrees(turned):.1f} deg')
            self.assertAlmostEqual(forward, SIDE, delta=side_tol, msg=f'side {leg + 1}')
            self.assertAlmostEqual(left, 0.0, delta=side_tol, msg=f'side {leg + 1}')
            self.assertAlmostEqual(before[2], TARGET_H, delta=0.1, msg=f'side {leg + 1}')
            self.assertAlmostEqual(turned, math.pi / 2, delta=turn_tol, msg=f'turn {leg + 1}')
            corner = self.pose()
        forward, left, turned = self.moved(square_start)
        gap = math.hypot(forward, left)
        print(f'square closes within {gap:.3f} m, heading {math.degrees(turned):.1f} deg')
        self.assertLess(gap, 0.3, 'the square does not close')
        self.assertLess(abs(turned), 4 * turn_tol, 'heading after the square')

    @step
    def test_6_speed_capped_at_the_limit(self):
        # Ask for 2 m/s: the mission passes it on, fc_bridge caps it at max_speed_xy.
        self.reset_step_max()
        self.goto(forward=1.5, speed=2.0)
        fastest = self.max_step[0]
        xy, z, yaw = self.max_true
        at, height = self.max_vz_at
        print(f'2 m/s asked: fastest {fastest:.3f} m/s (limit {FC["max_speed_xy"]}); '
              f'whole flight: xy {xy:.3f}, z {z:.3f} (at {at - self.takeoff_at:.1f} s after '
              f'takeoff, height {height:.2f} m), yaw rate {yaw:.3f}; '
              f'commanded {[round(c, 3) for c in self.max_cmd]}')
        self.assertGreater(fastest, 0.8 * FC['max_speed_xy'], 'not even near the limit')
        self.assertLessEqual(fastest, FC['max_speed_xy'] * SPEED_MARGIN)
        self.assertLessEqual(xy, FC['max_speed_xy'] * SPEED_MARGIN)
        self.assertLessEqual(z, FC['max_speed_z'] * SPEED_MARGIN)
        self.assertLessEqual(yaw, FC['max_yaw_rate'] * SPEED_MARGIN)
        for sent, limit in zip(self.max_cmd, ['max_speed_xy', 'max_speed_z', 'max_yaw_rate']):
            self.assertLessEqual(sent, FC[limit] + 1e-6, f'fc_bridge sent over {limit}')

    @step
    def test_7_land(self):
        accepted, result = self.send('land')
        self.assertTrue(accepted)
        r = self.finish(result, 40.0)
        self.assertTrue(r.success, r.message)
        _, _, z, _, _, _ = self.pose()
        print(f'landed: z {z:.3f} m (started at {self.ground_z:.3f} m)')
        self.assertLess(z, self.ground_z + 0.03)
        self.assert_upright()
        # radio:=false: the mission disarms after a Land, as nothing else would.
        self.assertTrue(self.wait(lambda: not self.status.armed, 5.0), 'still armed')

    @step
    def test_8_mission_dies_and_the_drone_stops(self):
        self.take_off()
        accepted, _ = self.send('goto', forward=3.0, left=0.0, yaw=0.0, speed=0.0)
        self.assertTrue(accepted)
        self.sleep_sim(2.0)
        self.assertGreater(self.speed(), 0.2, 'not moving before the kill')

        # The mission crashes mid-Goto: no more setpoints. fc_bridge must time out
        # (setpoint_timeout_s) and send zero, and the drone must stop and hover.
        pids = [pid for pid, cmd in started_here().items() if 'lib/drone_mission/mission' in cmd]
        self.assertEqual(len(pids), 1, f'mission processes found: {pids}')
        os.kill(pids[0], signal.SIGKILL)
        killed, at_kill = self.sim_now(), self.pose()
        z = at_kill[2]
        self.assertTrue(self.wait(lambda: self.speed() < 0.05 or self.sim_now() > killed + 5.0,
                                  30.0))
        stopped_after = self.sim_now() - killed
        coasted = math.hypot(*self.moved(at_kill)[:2])
        # fc_bridge waits setpoint_timeout_s, then the X3's velocity control brakes.
        limit = FC['setpoint_timeout_s'] + 1.0
        print(f'mission killed: stopped after {stopped_after:.2f} s of sim time '
              f'(limit {limit:.1f} s), coasted {coasted:.3f} m')
        self.assertLess(stopped_after, limit, 'did not stop in time')
        self.assertLess(coasted, 0.5, 'coasted too far')
        self.assertTrue(self.wait(lambda: not self.status.following_setpoints, 5.0))
        self.sleep_sim(3.0)
        self.assertLess(self.speed(), 0.05, 'drifting off')
        self.assertAlmostEqual(self.pose()[2], z, delta=0.1, msg='lost height')

        # Landed by hand: descend on cmd/manual, as an operator would, until it has
        # been down for 1 s, then disarm.
        start = self.sim_now()
        down_since = None
        while self.sim_now() < start + 30.0:
            if self.pose()[2] < self.ground_z + 0.03:
                down_since = down_since or self.sim_now()
                if self.sim_now() - down_since > 1.0:
                    break
            msg = TwistStamped()
            msg.twist.linear.z = -MISSION['land_speed']
            self.manual.publish(msg)
            time.sleep(0.05)
        self.assertEqual(self.active, 'manual')
        self.assertIsNotNone(down_since, 'manual landing did not reach the ground')
        future = self.arm_client.call_async(SetBool.Request(data=False))
        self.assertTrue(self.wait(future.done, 10.0) and future.result().success)
        self.assertTrue(self.wait(lambda: not self.status.armed, 5.0))
        self.assert_upright()
