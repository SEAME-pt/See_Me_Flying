"""
fc_bridge with backend:=inav and rc_override:=true against a fake INAV.

The fake acts like INAV's MSP RC override: while its switch is on, MSP_RC
reads back the last sticks it was sent (in INAV's order), otherwise the
radio's. Checks: setpoints become sticks with the right signs and order,
stale setpoints and fc/hold send centred sticks, fc/rc and fc/status report
what INAV uses.
"""
import socket
import struct
import threading
import time
import unittest

from drone_interfaces.msg import FcStatus, RcChannels
from geometry_msgs.msg import TwistStamped
import launch
import launch_ros.actions
import launch_testing.actions
import pytest
import rclpy
from std_srvs.srv import SetBool

READS = {2, 3, 58, 104, 105, 116, 0x2000, 0x2001, 0x2002, 0x2220}
SET_RAW_RC = 200
BOXES = b'ARM;ANGLE;MSP RC OVERRIDE;'
OVERRIDE_BIT = 2
RADIO = (1500, 1500, 1500, 885, 1000, 1000, 2000)   # roll, pitch, yaw, throttle, AUX1-3


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
    """MSP v2 requests of any size, one connection at a time."""

    def __init__(self):
        self.override_on = False
        self.lock = threading.Lock()
        self.seen = set()
        self.sticks = []        # (time, (roll, pitch, throttle, yaw)) as received: AETR
        self.sock = socket.socket()
        self.sock.bind(('127.0.0.1', 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self.serve, daemon=True).start()

    def last_sticks(self):
        with self.lock:
            return self.sticks[-1][1] if self.sticks else None

    def sticks_since(self, t):
        with self.lock:
            return [s for when, s in self.sticks if when >= t]

    def reply(self, cmd, payload):
        if cmd == 2:
            return b'INAV'
        if cmd == 3:
            return bytes([9, 1, 0])
        if cmd == 116:
            return BOXES
        if cmd == 0x2000:
            modes = (1 << OVERRIDE_BIT) if self.override_on else 0
            return struct.pack('<HHHHBIQB', 1000, 0, 0x01, 10, 0, 0, modes, 0)
        if cmd == 105:
            channels = list(RADIO)
            last = self.last_sticks()
            if self.override_on and last:
                roll, pitch, throttle, yaw = last
                channels[:4] = [roll, pitch, yaw, throttle]   # INAV's internal order
            return struct.pack(f'<{len(channels)}H', *channels)
        if cmd == SET_RAW_RC:
            with self.lock:
                self.sticks.append((time.monotonic(), struct.unpack('<4H', payload)))
            return b''   # INAV's ack
        return bytes(24)   # the other reads: zeros, long enough for any decoder

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
                    cmd, size = struct.unpack_from('<HH', buf, 4)
                    if len(buf) < 9 + size:
                        break
                    payload = buf[8:8 + size]
                    buf = buf[9 + size:]
                    self.seen.add(cmd)
                    conn.sendall(frame(cmd, self.reply(cmd, payload)))
            conn.close()


FAKE = FakeInav()


@pytest.mark.launch_test
def generate_test_description():
    fc_bridge = launch_ros.actions.Node(
        package='drone_fc_bridge', executable='fc_bridge', output='screen',
        parameters=[{'backend': 'inav', 'msp_host': '127.0.0.1', 'msp_port': FAKE.port,
                     'rc_override': True}])   # max speeds at their defaults: 0.5, 0.3, 1.0
    return launch.LaunchDescription([fc_bridge, launch_testing.actions.ReadyToTest()])


class TestInavRc(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('fc_bridge_inav_rc_tester')
        cls.pub = cls.node.create_publisher(TwistStamped, '/fc/setpoint_velocity', 10)
        cls.hold = cls.node.create_client(SetBool, '/fc/hold')
        cls.seen = {}
        for topic, kind in [('/fc/status', FcStatus), ('/fc/rc', RcChannels)]:
            cls.node.create_subscription(
                kind, topic, lambda m, t=topic: cls.seen.setdefault(t, []).append(m), 10)
        assert cls.hold.wait_for_service(timeout_sec=10.0)
        cls.spin(2.0)

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    @classmethod
    def spin(cls, seconds, setpoint=None):
        """Spins, publishing the setpoint (x, y, z, yaw rate) at 20 Hz if given."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if setpoint:
                msg = TwistStamped()
                (msg.twist.linear.x, msg.twist.linear.y, msg.twist.linear.z,
                 msg.twist.angular.z) = (float(v) for v in setpoint)
                cls.pub.publish(msg)
            rclpy.spin_once(cls.node, timeout_sec=0.05)

    def set_hold(self, on):
        future = self.hold.call_async(SetBool.Request(data=on))
        rclpy.spin_until_future_complete(self.node, future, timeout_sec=5.0)
        self.assertTrue(future.result().success)

    def last(self, topic):
        self.assertIn(topic, self.seen, f'nothing on {topic}')
        return self.seen[topic][-1]

    def sticks_during(self, seconds, setpoint=None):
        start = time.monotonic()
        self.spin(seconds, setpoint)
        got = FAKE.sticks_since(start + 0.5)   # after the change has gone through
        self.assertGreater(len(got), 3, 'no sticks sent')
        return got

    def test_a_no_setpoint_sends_centred_sticks(self):
        for s in self.sticks_during(1.0):
            self.assertEqual(s, (1500, 1500, 1500, 1500))
        self.assertTrue(self.last('/fc/status').rc_sent)

    def test_b_each_axis_in_aetr_order_with_ros_signs(self):
        # (setpoint), then what arrives: roll, pitch, throttle, yaw (AETR).
        for setpoint, want in [
                ((0.25, 0, 0, 0), (1500, 1750, 1500, 1500)),    # forward: pitch up
                ((0, 0.25, 0, 0), (1250, 1500, 1500, 1500)),    # left: roll left
                ((0, 0, 0.15, 0), (1500, 1500, 1750, 1500)),    # up: throttle up
                ((0, 0, 0, 0.5), (1500, 1500, 1500, 1250))]:    # yaw left: yaw left
            with self.subTest(setpoint=setpoint):
                for s in self.sticks_during(1.0, setpoint):
                    self.assertEqual(s, want)

    def test_c_clamped_to_the_speed_limits(self):
        # 2 m/s forward is clamped to max_speed_xy 0.5: full stick, no further.
        for s in self.sticks_during(1.0, (2.0, 0, -5.0, -9.0)):
            self.assertEqual(s, (1500, 2000, 1000, 2000))

    def test_d_setpoint_timeout_centres(self):
        self.spin(1.0, (0.25, 0, 0, 0))
        self.assertEqual(FAKE.last_sticks(), (1500, 1750, 1500, 1500))
        for s in self.sticks_during(1.0):   # setpoint_timeout_s 0.3
            self.assertEqual(s, (1500, 1500, 1500, 1500))

    def test_e_hold_centres(self):
        self.set_hold(True)
        try:
            for s in self.sticks_during(1.0, (0.25, 0, 0, 0)):
                self.assertEqual(s, (1500, 1500, 1500, 1500))
            self.assertTrue(self.last('/fc/status').holding)
        finally:
            self.set_hold(False)

    def test_f_fc_rc_and_status_follow_the_override_switch(self):
        FAKE.override_on = False
        self.spin(1.0, (0.25, 0, 0, 0))
        rc = self.last('/fc/rc')
        self.assertEqual((rc.roll, rc.pitch, rc.yaw, rc.throttle), RADIO[:4])
        self.assertEqual(tuple(rc.channels), RADIO)
        self.assertFalse(self.last('/fc/status').rc_override_active)

        FAKE.override_on = True
        try:
            self.spin(1.0, (0.25, 0, 0, 0))
            rc = self.last('/fc/rc')
            self.assertEqual((rc.roll, rc.pitch, rc.yaw, rc.throttle), (1500, 1750, 1500, 1500))
            self.assertEqual(tuple(rc.channels[4:]), RADIO[4:])
            st = self.last('/fc/status')
            self.assertTrue(st.rc_override_active)
            self.assertTrue(st.rc_sent)
        finally:
            FAKE.override_on = False

    def test_g_only_reads_and_sticks(self):
        self.assertIn(SET_RAW_RC, FAKE.seen)
        self.assertLessEqual(FAKE.seen, READS | {SET_RAW_RC})
