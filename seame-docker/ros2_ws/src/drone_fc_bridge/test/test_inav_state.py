"""
fc_bridge with backend:=inav against a fake INAV on localhost.

The fake answers MSP requests with hand-built replies whose values make each
conversion checkable: armed, roll 10, pitch 20, heading 90 (east), position
1 m north, 2 m east, 0.5 m up, moving 0.5 m/s north and 0.3 m/s east, rangefinder 120 cm,
16.2 V on 4 cells. The checks then compare with ROS conventions (x north,
y west, z up; yaw counter-clockwise; twist in the body frame).
"""
import math
import socket
import struct
import threading
import time
import unittest

from drone_interfaces.msg import FcStatus, OpticalFlow
from geometry_msgs.msg import QuaternionStamped
import launch
import launch_ros.actions
import launch_testing.actions
from nav_msgs.msg import Odometry
import pytest
import rclpy
from sensor_msgs.msg import BatteryState, Range

READS = {1, 2, 3, 58, 108, 0x2000, 0x2001, 0x2002, 0x2220}
SENSORS = 0x01 | 0x02 | 0x10 | 0x20        # acc, baro, rangefinder, optical flow


def crc8_dvb_s2(data):
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0xD5) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def frame(cmd, payload):
    body = struct.pack('<BHH', 0, cmd, len(payload)) + payload
    return b'$X>' + body + bytes([crc8_dvb_s2(body)])


class FakeInav:
    """Answers 9-byte MSP v2 requests, one connection at a time."""

    def __init__(self):
        self.sensors = SENSORS
        self.silent = False
        self.seen = set()
        self.sock = socket.socket()
        self.sock.bind(('127.0.0.1', 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self.serve, daemon=True).start()

    def reply(self, cmd):
        if cmd == 2:
            return b'INAV'
        if cmd == 3:
            return bytes([9, 1, 0])
        if cmd == 0x2000:   # status: cycle, i2c, sensors, load, profiles, arming, modes, mixer
            return struct.pack('<HHHHBI', 1000, 0, self.sensors, 10, 0, 1 << 2) + bytes(9)
        if cmd == 0x2220:   # roll, pitch, yaw in 0.1 deg; then x pos, x vel, y ..., z ...
            return struct.pack('<hhh', 100, 200, 900) + struct.pack(
                '<ihihih', 100, 50, 200, 30, 50, 0)
        if cmd == 0x2001:   # quality, flow x, y, body x, y in deg/s
            return struct.pack('<Bhhhh', 100, 30, 12, 5, 0)
        if cmd == 58:
            return struct.pack('<i', 120)
        if cmd == 0x2002:   # flags (4 cells, ok), V, A, W, mAh, mWh, remaining, %, rssi
            return struct.pack('<BHhiiiIBH', 4 << 4, 1620, 250, 4050, 100, 1600, 0, 80, 0)
        return b''

    def serve(self):
        while True:
            conn, _ = self.sock.accept()
            buf = b''
            while True:
                data = conn.recv(256)
                if not data:
                    break
                buf += data
                while len(buf) >= 9:
                    cmd = struct.unpack_from('<H', buf, 4)[0]
                    buf = buf[9:]
                    self.seen.add(cmd)
                    if not self.silent:
                        conn.sendall(frame(cmd, self.reply(cmd)))
            conn.close()


FAKE = FakeInav()


@pytest.mark.launch_test
def generate_test_description():
    fc_bridge = launch_ros.actions.Node(
        package='drone_fc_bridge', executable='fc_bridge', output='screen',
        parameters=[{'backend': 'inav', 'msp_host': '127.0.0.1', 'msp_port': FAKE.port}])
    return launch.LaunchDescription([fc_bridge, launch_testing.actions.ReadyToTest()])


def rotation(roll, pitch, yaw):
    """Body-to-world rotation matrix, ZYX order, written out independently."""
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return [[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr]]


def rpy(q):
    roll = math.atan2(2 * (q.w * q.x + q.y * q.z), 1 - 2 * (q.x * q.x + q.y * q.y))
    pitch = math.asin(max(-1.0, min(1.0, 2 * (q.w * q.y - q.z * q.x))))
    yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
    return roll, pitch, yaw


class TestInavState(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('fc_bridge_inav_state_tester')
        cls.seen = {}
        for topic, kind in [('/fc/status', FcStatus), ('/fc/attitude', QuaternionStamped),
                            ('/fc/odom', Odometry), ('/fc/range', Range),
                            ('/fc/optical_flow', OpticalFlow), ('/fc/battery', BatteryState)]:
            cls.node.create_subscription(
                kind, topic, lambda m, t=topic: cls.seen.setdefault(t, []).append(m), 10)
        cls.spin(3.0)

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    @classmethod
    def spin(cls, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            rclpy.spin_once(cls.node, timeout_sec=0.05)

    def last(self, topic):
        self.assertIn(topic, self.seen, f'nothing on {topic}')
        return self.seen[topic][-1]

    def test_a_status_armed_and_link_ok(self):
        st = self.last('/fc/status')
        self.assertEqual(st.backend, 'inav')
        self.assertTrue(st.armed, 'the armed bit in MSP2_INAV_STATUS')
        self.assertTrue(st.link_ok)
        self.assertGreaterEqual(st.state_age_s, 0.0)
        self.assertLess(st.state_age_s, 1.0)
        self.assertTrue(st.range_valid)

    def test_b_attitude_in_ros_convention(self):
        roll, pitch, yaw = rpy(self.last('/fc/attitude').quaternion)
        self.assertAlmostEqual(math.degrees(roll), 10.0, places=3)
        self.assertAlmostEqual(math.degrees(pitch), 20.0, places=3)
        # Heading 90 (east, clockwise from north) is yaw -90 in ROS.
        self.assertAlmostEqual(math.degrees(yaw), -90.0, places=3)

    def test_c_odom_position_north_west_up(self):
        p = self.last('/fc/odom').pose.pose.position
        self.assertAlmostEqual(p.x, 1.0, places=6)    # north
        self.assertAlmostEqual(p.y, -2.0, places=6)   # 2 m east is -2 m west
        self.assertAlmostEqual(p.z, 0.5, places=6)

    def test_d_odom_velocity_in_the_body_frame(self):
        odom = self.last('/fc/odom')
        r = rotation(math.radians(10), math.radians(20), math.radians(-90))
        world = (0.5, -0.3, 0.0)                        # 0.5 m/s north, 0.3 m/s east
        body = [sum(r[i][j] * world[i] for i in range(3)) for j in range(3)]   # R^T v
        v = odom.twist.twist.linear
        for got, want in zip((v.x, v.y, v.z), body):
            self.assertAlmostEqual(got, want, places=4)
        # Facing east, north is on the drone's left and east straight ahead.
        self.assertGreater(v.y, 0.3)
        self.assertGreater(v.x, 0.1)

    def test_e_range(self):
        r = self.last('/fc/range')
        self.assertAlmostEqual(r.range, 1.2, places=5)

    def test_f_optical_flow_passes_through(self):
        f = self.last('/fc/optical_flow')
        self.assertEqual(f.quality, 100)
        self.assertAlmostEqual(f.flow_rate_x, math.radians(30), places=5)
        self.assertAlmostEqual(f.flow_rate_y, math.radians(12), places=5)
        self.assertAlmostEqual(f.body_rate_x, math.radians(5), places=5)
        self.assertAlmostEqual(f.body_rate_y, 0.0, places=5)

    def test_g_battery(self):
        b = self.last('/fc/battery')
        self.assertAlmostEqual(b.voltage, 16.2, places=4)
        self.assertAlmostEqual(b.current, -2.5, places=4)   # discharging
        self.assertAlmostEqual(b.percentage, 0.8, places=4)
        self.assertTrue(b.present)
        self.assertEqual(len(b.cell_voltage), 4)

    def test_h_only_reads_were_asked(self):
        self.assertTrue(FAKE.seen, 'the fake got no requests')
        self.assertLessEqual(FAKE.seen, READS)

    def test_y_no_rangefinder_bit_means_no_range(self):
        # 120 cm keeps coming, but without the sensor bit it isn't trusted.
        FAKE.sensors = SENSORS & ~0x10
        self.spin(0.5)
        self.seen.pop('/fc/range', None)
        self.spin(1.0)
        self.assertNotIn('/fc/range', self.seen)
        self.assertFalse(self.last('/fc/status').range_valid)
        FAKE.sensors = SENSORS

    def test_z_silence_marks_the_link_down(self):
        FAKE.silent = True
        self.spin(2.0)
        st = self.last('/fc/status')
        self.assertFalse(st.link_ok)
        self.assertGreater(st.state_age_s, 0.5)
