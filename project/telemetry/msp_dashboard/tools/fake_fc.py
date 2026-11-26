#!/usr/bin/env python3
"""Fake INAV flight controller speaking MSP v2 over TCP, for testing the
dashboard (or CI) without the drone.

    python3 tools/fake_fc.py --port 5760
    ./build/msp_dashboard --host 127.0.0.1 --port 5760

MSP_SET_MOTOR is accepted and echoed back by MSP_MOTOR while disarmed, like
INAV's motor test. --no-arm keeps the fake FC disarmed the whole time.
"""
import argparse
import math
import socket
import struct
import time


def crc8_dvb_s2(data):
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0xD5) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def frame(cmd, payload, ok=True, version=2):
    direction = b">" if ok else b"!"
    if version == 1:
        body = bytes([len(payload), cmd & 0xFF]) + payload
        checksum = 0
        for b in body:
            checksum ^= b
        return b"$M" + direction + body + bytes([checksum])
    body = struct.pack("<BHH", 0, cmd, len(payload)) + payload
    return b"$X" + direction + body + bytes([crc8_dvb_s2(body)])


MOTOR_TEST = [1000] * 8      # MSP_SET_MOTOR values (used while disarmed)
NEVER_ARM = False
REPLY_DELAY_S = 0.0           # --delay: simulated link latency

BOXES = "ARM;ANGLE;HORIZON;NAV ALTHOLD;HEADING HOLD;NAV POSHOLD;FAILSAFE;MSP RC OVERRIDE;"


def handle_command(cmd, payload):
    """Commands with a payload. Returns the reply payload, or None for an MSP error."""
    if cmd == 214 and len(payload) >= 16:          # MSP_SET_MOTOR
        MOTOR_TEST[:] = struct.unpack_from("<8H", payload)
        return b""
    return None


def reply(cmd, t):
    s = math.sin(t)
    armed = not NEVER_ARM and int(t) % 20 >= 10
    if cmd == 1:
        return struct.pack("<BBB", 0, 2, 5)
    if cmd == 2:
        return b"INAV"
    if cmd == 3:
        return bytes([9, 1, 0])
    if cmd == 4:
        name = b"ODDITYRCF7AIO"
        return b"ODF7" + struct.pack("<HBBB", 0, 2, 1, len(name)) + name
    if cmd == 5:                                   # MSP_BUILD_INFO: date, time, git rev
        return b"Nov 23 2026" + b"12:00:00" + b"fakefc0"
    if cmd == 10:
        return b"Brook"
    if cmd == 151:                                 # MSP_SENSOR_STATUS: healthy, gyro, acc, mag, baro, gps, rf, pitot, flow
        return bytes([1, 1, 1, 0, 1, 0, 1, 0, 1])  # 1 = OK, 0 = not configured
    if cmd == 116:
        return BOXES.encode()
    if cmd == 108:
        return struct.pack("<hhh", int(150 * s), int(-80 * s), int(t * 10) % 360)
    if cmd == 109:
        return struct.pack("<ihi", int(120 + 30 * s), int(25 * math.cos(t)), 0)
    if cmd == 102:
        return struct.pack("<9h", int(20 * s), -15, 512, int(40 * s), 3, -2, 210, -33, 400)
    if cmd == 105:
        return struct.pack("<16H", 1500 + int(200 * s), 1500, 1000 + (400 if armed else 0), 1500,
                           1800 if armed else 1000, 1000, 1500, 1000, *([1500] * 8))
    if cmd == 104:
        if not armed:
            return struct.pack("<8H", *MOTOR_TEST)
        m = 1350 + int(50 * s)
        return struct.pack("<8H", m, m + 10, m - 5, m + 3, 0, 0, 0, 0)
    if cmd == 0x2000:
        modes = 0b10 | (0b1 if armed else 0) | (0b100000 if armed else 0)
        arming = (1 << 2) | (1 << 3) if armed else (1 << 3) | (1 << 14) | (1 << 8)
        return struct.pack("<HHHHBI", 1000, 0, 0b110001, 23, 0, arming) + struct.pack("<I", modes) + b"\x00"
    if cmd == 0x2002:
        volts = int(1640 - t * 2) % 400 + 1300
        state = 0 if volts > 1450 else 1
        flags = (4 << 4) | (state << 2)
        return struct.pack("<BHhIIIIBH", flags, volts, 1250, volts * 1250 // 100, int(t * 3), int(t * 45),
                           0, 78, 1000)
    if cmd == 0x2001:
        return struct.pack("<Bhhhh", 180 + int(40 * s), int(30 * s), int(-12 * s), 4, -2)
    if cmd == 58:
        return struct.pack("<i", -1 if int(t) % 15 < 3 else int(115 + 30 * s))
    if cmd == 0x2220:
        return struct.pack("<hhh", int(150 * s), int(-80 * s), int(t * 100) % 3600) + \
            struct.pack("<ihihih", int(100 * s), int(50 * math.cos(t)), int(-60 * s), 0, int(120 + 30 * s), 0)
    if cmd == 121:
        return struct.pack("<5Bh", 1 if armed else 0, 3 if armed else 0, 0, 0, 0 if armed else 10, 90)
    if cmd == 0x2103:
        return None  # pretend the receiver isn't CRSF: MSP error reply
    return None


def serve(conn):
    buf = b""
    start = time.monotonic()
    while True:
        data = conn.recv(1024)
        if not data:
            return
        buf += data
        while True:
            i2, i1 = buf.find(b"$X<"), buf.find(b"$M<")
            starts = [i for i in (i1, i2) if i >= 0]
            if not starts:
                break
            i = min(starts)
            buf = buf[i:]
            if buf[1:2] == b"M":                      # MSP v1 (INAV Configurator uses it)
                if len(buf) < 6 or len(buf) < 6 + buf[3]:
                    break
                size, cmd, version = buf[3], buf[4], 1
                request, buf = buf[5:5 + size], buf[6 + size:]
            else:                                     # MSP v2
                if len(buf) < 9:
                    break
                _flag, cmd, size = struct.unpack_from("<BHH", buf, 3)
                if len(buf) < 9 + size:
                    break
                request, buf, version = buf[8:8 + size], buf[9 + size:], 2
            if size:
                payload = handle_command(cmd, request)
            else:
                payload = reply(cmd, time.monotonic() - start)
            if REPLY_DELAY_S:
                time.sleep(REPLY_DELAY_S)
            conn.sendall(frame(cmd, payload or b"", ok=payload is not None, version=version))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=5760)
    ap.add_argument("--no-arm", action="store_true", help="stay disarmed (for motor tests)")
    ap.add_argument("--delay", type=float, default=0, help="milliseconds to wait before each reply")
    args = ap.parse_args()
    global NEVER_ARM, REPLY_DELAY_S
    NEVER_ARM = args.no_arm
    REPLY_DELAY_S = args.delay / 1000
    srv = socket.create_server(("127.0.0.1", args.port), reuse_port=True)
    print(f"fake FC listening on 127.0.0.1:{args.port}")
    while True:
        conn, _ = srv.accept()
        with conn:
            try:
                serve(conn)
            except ConnectionError:
                pass


if __name__ == "__main__":
    main()
