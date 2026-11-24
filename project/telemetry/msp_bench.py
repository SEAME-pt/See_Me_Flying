#!/usr/bin/env python3
"""
msp_bench.py - unified INAV / MSP bench test for the See_Me_Flying drone.
 
Runs on the Raspberry Pi 5 ground station and on personal machines (Linux,
macOS, Windows). Pure standard library; pyserial is only needed for --serial.
 
What it tests
  1. info         FC variant/version, board, build, craft name, MSP API
  2. sensor_status gyro / acc / mag / baro / gps / rangefinder / pitot / opflow
                  health (start and end of the run, so mid-run dropouts show up)
  3. sensors      median / mean / std / p05 / p95 of every value over N seconds
                  (std = sensor noise for the sim), plus sample rate per command
  4. derived      gyro bias, accel norm, yaw drift, altitude drift,
                  I2C error delta, cell voltage
  4b. MTF-02P     (rangefinder + optical flow, on by default)
                  setup: rangefinder_hardware / opflow_hardware = MSP, the sensor
                  UART has MSP and nothing else, opflow_scale, align_opflow,
                  rangefinder filter and estimator weights (read from the FC);
                  still: rangefinder valid %, states (out of range / hardware
                  failure / no new data), noise, flow quality, flow at rest;
                  --flow-motion: guided slide forward/back/right/left that checks
                  the flow responds and which axis/sign each direction gives
  5. latency      sequential RTT per command (link delay for the sim),
                  pipelined load at several in-flight windows (heavy MSP traffic),
                  burst test (buffer overflow / drop behaviour)
  6. link         CRC errors, garbage bytes, error frames, bytes in/out
 
Output: one tidy CSV (one row per measurement, same columns on every machine,
so CSVs from the Pi and laptops can simply be concatenated). Optional --raw CSV
with every individual sample, for fitting noise / delay models in Gazebo.
 
Exit code: 0 = no FAIL rows, 1 = at least one FAIL, 2 = could not talk to FC.
 
It also replaces the older tools:
  --logbook NOTE    keep the run in project/logs/measurements/<name>/ with a line in
                    history.csv (was measure_wifi_rtt.py + latency_test.py, `make wifi-rtt`)
  --capture STATE   record raw replies of every message into inav/msp/captures/STATE.jsonl
                    for the tests, and refresh the copies in project/ros2 (was msp_inventory.py)
 
IMPORTANT: the link must be free. Stop the MSP gateway on the Pi first
(esp-link forwards serial data to every TCP client, so two clients mix replies).
Bench only, props off. Heavy-load tests are skipped automatically if armed.
 
Examples
  python3 msp_bench.py                                   # esp-link AP default
  python3 msp_bench.py --tcp 192.168.4.1:23
  python3 msp_bench.py --serial /dev/ttyUSB0 --baud 115200
  python3 msp_bench.py --serial COM5 --expect gyro,acc        # without the MTF-02P
  python3 msp_bench.py --serial /dev/ttyUSB0 --flow-motion     # + guided motion test
  python3 msp_bench.py --quick --raw raw.csv
  python3 msp_bench.py --serial /dev/ttyUSB0 --logbook "Pi, USB bridge, bench"
  python3 msp_bench.py --capture flat_still
"""
from __future__ import annotations
 
import argparse
import csv
import json
import math
import os
import platform
import shutil
import socket
import statistics
import struct
import sys
import time
import uuid
from collections import deque, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
 
# --------------------------------------------------------------------------- #
# MSP command ids (INAV)
# --------------------------------------------------------------------------- #
MSP_API_VERSION = 1
MSP_FC_VARIANT = 2
MSP_FC_VERSION = 3
MSP_BOARD_INFO = 4
MSP_BUILD_INFO = 5
MSP_NAME = 10
MSP_SONAR_ALTITUDE = 58
MSP_RAW_IMU = 102
MSP_MOTOR = 104
MSP_RC = 105
MSP_ATTITUDE = 108
MSP_ALTITUDE = 109
MSP_BOXNAMES = 116
MSP_NAV_STATUS = 121
MSP_SENSOR_STATUS = 151
MSP2_COMMON_SETTING_INFO = 0x1007
MSP2_CF_SERIAL_CONFIG = 0x1009
MSP2_INAV_STATUS = 0x2000
MSP2_INAV_OPTICAL_FLOW = 0x2001
MSP2_INAV_ANALOG = 0x2002
MSP2_INAV_GET_LINK_STATS = 0x2103
MSP2_INAV_FULL_LOCAL_POSE = 0x2220
 
CMD_NAMES = {
    MSP_API_VERSION: "API_VERSION", MSP_FC_VARIANT: "FC_VARIANT",
    MSP_FC_VERSION: "FC_VERSION", MSP_BOARD_INFO: "BOARD_INFO",
    MSP_BUILD_INFO: "BUILD_INFO", MSP_NAME: "NAME",
    MSP_SONAR_ALTITUDE: "SONAR_ALTITUDE", MSP_RAW_IMU: "RAW_IMU",
    MSP_RC: "RC", MSP_ATTITUDE: "ATTITUDE", MSP_ALTITUDE: "ALTITUDE",
    MSP_SENSOR_STATUS: "SENSOR_STATUS", MSP2_INAV_STATUS: "INAV_STATUS",
    MSP2_INAV_OPTICAL_FLOW: "INAV_OPTICAL_FLOW", MSP2_INAV_ANALOG: "INAV_ANALOG",
    MSP2_INAV_GET_LINK_STATS: "INAV_LINK_STATS", MSP2_INAV_FULL_LOCAL_POSE: "INAV_LOCAL_POSE",
    MSP_MOTOR: "MOTOR", MSP_BOXNAMES: "BOXNAMES", MSP_NAV_STATUS: "NAV_STATUS",
    MSP2_COMMON_SETTING_INFO: "SETTING_INFO", MSP2_CF_SERIAL_CONFIG: "SERIAL_CONFIG",
}
CMD_BY_NAME = {name: cmd for cmd, name in CMD_NAMES.items()}
 
# --capture: every message, in this order, with the names the recordings use
# (the same list msp_inventory.py recorded, so old and new captures line up).
CAPTURE_MSGS = [
    ("MSP_API_VERSION", MSP_API_VERSION), ("MSP_FC_VARIANT", MSP_FC_VARIANT),
    ("MSP_FC_VERSION", MSP_FC_VERSION), ("MSP_BOARD_INFO", MSP_BOARD_INFO),
    ("MSP_NAME", MSP_NAME), ("MSP_BOXNAMES", MSP_BOXNAMES),
    ("MSP2_INAV_STATUS", MSP2_INAV_STATUS), ("MSP_ATTITUDE", MSP_ATTITUDE),
    ("MSP_ALTITUDE", MSP_ALTITUDE), ("MSP_RAW_IMU", MSP_RAW_IMU),
    ("MSP2_INAV_ANALOG", MSP2_INAV_ANALOG), ("MSP2_INAV_OPTICAL_FLOW", MSP2_INAV_OPTICAL_FLOW),
    ("MSP_RC", MSP_RC), ("MSP_SONAR_ALTITUDE", MSP_SONAR_ALTITUDE),
    ("MSP2_INAV_FULL_LOCAL_POSE", MSP2_INAV_FULL_LOCAL_POSE),
    ("MSP_NAV_STATUS", MSP_NAV_STATUS), ("MSP2_INAV_GET_LINK_STATS", MSP2_INAV_GET_LINK_STATS),
    ("MSP_MOTOR", MSP_MOTOR),
]
 
TELEMETRY_DIR = Path(__file__).resolve().parent
CAPTURE_DIR = TELEMETRY_DIR / "inav" / "msp" / "captures"
SCRIPTS_DIR = TELEMETRY_DIR.parent / "scripts"           # project/scripts: logbook.py
ROS_SRC = TELEMETRY_DIR.parent / "ros2" / "src"          # copies of the captures for the C++ tests
 
SENSOR_NAMES = ["gyro", "acc", "mag", "baro", "gps", "rangefinder", "pitot", "opflow"]
HW_STATUS = {0: "NONE", 1: "OK", 2: "UNAVAILABLE", 3: "UNHEALTHY"}
ARMED_BIT = 1 << 2  # INAV armingFlag ARMED
ARMING_BLOCKERS = {  # INAV armingFlag_e, bit -> name
    6: "GEOZONE", 7: "FAILSAFE_SYSTEM", 8: "NOT_LEVEL", 9: "SENSORS_CALIBRATING",
    10: "SYSTEM_OVERLOADED", 11: "NAVIGATION_UNSAFE", 12: "COMPASS_NOT_CALIBRATED",
    13: "ACCELEROMETER_NOT_CALIBRATED", 14: "ARM_SWITCH", 15: "HARDWARE_FAILURE",
    16: "BOXFAILSAFE", 17: "BOXKILLSWITCH", 18: "RC_LINK", 19: "THROTTLE", 20: "CLI",
    21: "CMS_MENU", 22: "OSD_MENU", 23: "ROLLPITCH_NOT_CENTERED", 24: "SERVO_AUTOTRIM",
    25: "OOM", 26: "INVALID_SETTING", 27: "PWM_OUTPUT_ERROR", 28: "NO_PREARM",
    29: "DSHOT_BEEPER", 30: "LANDING_DETECTED",
}
 
 
# blockers that are normal on the bench (radio off, no arm switch): shown faded
BENCH_OK_BLOCKERS = {"RC_LINK", "NO_PREARM", "ARM_SWITCH", "THROTTLE", "FAILSAFE_SYSTEM",
                     "BOXFAILSAFE", "ROLLPITCH_NOT_CENTERED", "CLI", "CMS_MENU", "OSD_MENU",
                     "NAVIGATION_UNSAFE", "LANDING_DETECTED", "DSHOT_BEEPER"}
 
 
def arming_blockers(flags):
    return [n for b, n in ARMING_BLOCKERS.items() if flags & (1 << b)]
 
 
def blocker_status(names):
    if not names:
        return "PASS", ""
    serious = [n for n in names if n not in BENCH_OK_BLOCKERS]
    if serious:
        return "FAIL", "must fix before flight: " + " ".join(serious)
    return "WARN", "normal on the bench (radio off / no arm switch)"
 
 
# --------------------------------------------------------------------------- #
# MSP v2 framing
# --------------------------------------------------------------------------- #
def crc8_dvb_s2(data: bytes, crc: int = 0) -> int:
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0xD5) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc
 
 
def encode_v2(cmd: int, payload: bytes = b"", direction: bytes = b"<") -> bytes:
    body = struct.pack("<BHH", 0, cmd, len(payload)) + payload
    return b"$X" + direction + body + bytes([crc8_dvb_s2(body)])
 
 
@dataclass
class Frame:
    cmd: int
    payload: bytes
    error: bool
    direction: str
 
 
class MspParser:
    """Streaming MSP v2 parser. Counts CRC errors and skipped bytes."""
 
    def __init__(self, accept=(b">", b"!")):
        self.buf = bytearray()
        self.accept = {a[0] for a in accept}
        self.crc_errors = 0
        self.garbage_bytes = 0
 
    def feed(self, data: bytes) -> list[Frame]:
        self.buf += data
        out: list[Frame] = []
        while True:
            i = self.buf.find(b"$X")
            if i < 0:
                keep = 1 if self.buf.endswith(b"$") else 0
                self.garbage_bytes += len(self.buf) - keep
                del self.buf[: len(self.buf) - keep]
                break
            if i > 0:
                self.garbage_bytes += i
                del self.buf[:i]
            if len(self.buf) < 8:
                break
            d = self.buf[2]
            _flag, cmd, size = struct.unpack_from("<BHH", self.buf, 3)
            if d not in (ord(">"), ord("!"), ord("<")) or size > 4096:
                self.garbage_bytes += 2
                del self.buf[:2]
                continue
            total = 8 + size + 1
            if len(self.buf) < total:
                break
            if crc8_dvb_s2(self.buf[3: 8 + size]) != self.buf[8 + size]:
                self.crc_errors += 1
                del self.buf[:2]
                continue
            payload = bytes(self.buf[8: 8 + size])
            del self.buf[:total]
            if d in self.accept:
                out.append(Frame(cmd, payload, d == ord("!"), chr(d)))
        return out
 
 
# --------------------------------------------------------------------------- #
# Transports
# --------------------------------------------------------------------------- #
class TcpLink:
    def __init__(self, host: str, port: int, connect_timeout: float = 3.0):
        self.name = f"tcp://{host}:{port}"
        self.sock = socket.create_connection((host, port), timeout=connect_timeout)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
 
    def write(self, data: bytes) -> None:
        self.sock.sendall(data)
 
    def read(self, timeout: float) -> bytes:
        self.sock.settimeout(max(timeout, 1e-4))
        try:
            data = self.sock.recv(4096)
        except socket.timeout:
            return b""
        if not data:
            raise ConnectionError("link closed by remote end")
        return data
 
    def close(self) -> None:
        self.sock.close()
 
 
def processes_using(path):
    """(pid, name) of other processes that have `path` open. Linux only (reads /proc);
    elsewhere returns []. Two programs on one serial port steal each other's replies."""
    proc = Path("/proc")
    if not proc.is_dir():
        return []
    target = os.path.realpath(path)
    users = []
    for d in proc.iterdir():
        if not d.name.isdigit() or int(d.name) == os.getpid():
            continue
        try:
            fds = list((d / "fd").iterdir())
        except OSError:
            continue
        for fd in fds:
            try:
                if os.readlink(fd) == target:
                    users.append((int(d.name), (d / "comm").read_text().strip()))
                    break
            except OSError:
                continue
    return users
 
 
class SerialLink:
    def __init__(self, port: str, baud: int, settle: float = 0.2):
        try:
            import serial  # type: ignore
        except ImportError:
            sys.exit("pyserial is missing: pip install pyserial  "
                     "(Pi OS: sudo apt install python3-serial)")
        self.name = f"serial://{port}@{baud}"
        # Open without asserting DTR/RTS: on ESP8266 boards (D1 Mini, NodeMCU)
        # those lines are wired to RESET/GPIO0 and opening the port reboots the ESP.
        self.ser = serial.Serial()
        self.ser.port, self.ser.baudrate, self.ser.timeout = port, baud, 0.002
        self.ser.dtr = False
        self.ser.rts = False
        self.ser.open()
        time.sleep(settle)
        self.ser.reset_input_buffer()
 
    def write(self, data: bytes) -> None:
        self.ser.write(data)
 
    def read(self, timeout: float) -> bytes:
        deadline = time.perf_counter() + timeout
        while True:
            n = self.ser.in_waiting
            if n:
                return self.ser.read(n)
            b = self.ser.read(1)  # blocks up to 2 ms
            if b:
                return b + self.ser.read(self.ser.in_waiting)
            if time.perf_counter() >= deadline:
                return b""
 
    def close(self) -> None:
        self.ser.close()
 
 
# --------------------------------------------------------------------------- #
# MSP client
# --------------------------------------------------------------------------- #
class MspTimeout(Exception):
    pass
 
 
class MspError(Exception):
    pass
 
 
class MspClient:
    def __init__(self, link):
        self.link = link
        self.parser = MspParser()
        self.tx_bytes = 0
        self.rx_bytes = 0
        self.error_frames = 0
        self.late_frames = 0       # replies that arrived for an earlier request
        self.pending = deque()     # frames read but not handed out yet
        self.raw_rx = bytearray()  # first bytes received, for diagnosis
 
    def send(self, cmd: int, payload: bytes = b"") -> None:
        frame = encode_v2(cmd, payload)
        self.link.write(frame)
        self.tx_bytes += len(frame)
 
    def send_many(self, cmd: int, count: int) -> None:
        frame = encode_v2(cmd)
        self.link.write(frame * count)
        self.tx_bytes += len(frame) * count
 
    def poll(self, timeout: float) -> list[Frame]:
        if self.pending:
            out = list(self.pending)
            self.pending.clear()
            return out
        data = self.link.read(timeout)
        if not data:
            return []
        self.rx_bytes += len(data)
        if len(self.raw_rx) < 256:
            self.raw_rx += data[: 256 - len(self.raw_rx)]
        frames = self.parser.feed(data)
        self.error_frames += sum(f.error for f in frames)
        return frames
 
    def drain(self, quiet: float = 0.08, max_time: float = 2.0) -> None:
        self.pending.clear()
        end = time.perf_counter() + max_time
        while time.perf_counter() < end and self.poll(quiet):
            pass
 
    def exchange(self, cmd: int, payload: bytes = b"", timeout: float = 0.5):
        """Send one request; return (Frame, rtt_s), or (None, None) on timeout.
        Error replies ('!') are returned too. Other frames that arrive meanwhile are
        late replies to earlier requests: counted and dropped."""
        t0 = time.perf_counter()
        self.send(cmd, payload)
        deadline = t0 + timeout
        while True:
            rem = deadline - time.perf_counter()
            if rem <= 0:
                return None, None
            frames = self.poll(min(rem, 0.05))
            for i, f in enumerate(frames):
                if f.cmd == cmd:
                    self.pending.extend(frames[i + 1:])
                    return f, time.perf_counter() - t0
                self.late_frames += 1
 
    def request(self, cmd: int, payload: bytes = b"", timeout: float = 0.5):
        """Send one request and wait for its reply. Returns (payload, rtt_s)."""
        f, rtt = self.exchange(cmd, payload, timeout)
        if f is None:
            raise MspTimeout(CMD_NAMES.get(cmd, cmd))
        if f.error:
            raise MspError(f"FC rejected {CMD_NAMES.get(cmd, cmd)}")
        return f.payload, rtt
 
 
# --------------------------------------------------------------------------- #
# Decoders: payload -> {metric: value}
# --------------------------------------------------------------------------- #
def dec_raw_imu(p):
    ax, ay, az, gx, gy, gz, mx, my, mz = struct.unpack_from("<9h", p)
    ax, ay, az = ax / 512.0, ay / 512.0, az / 512.0  # INAV: 512 = 1 g
    out = {"acc_x_g": ax, "acc_y_g": ay, "acc_z_g": az,
           "acc_norm_g": math.sqrt(ax * ax + ay * ay + az * az),
           "gyro_x_dps": gx, "gyro_y_dps": gy, "gyro_z_dps": gz}
    if mx or my or mz:
        out.update({"mag_x": mx, "mag_y": my, "mag_z": mz})
    return out
 
 
def dec_attitude(p):
    r, pi, y = struct.unpack_from("<3h", p)
    return {"roll_deg": r / 10.0, "pitch_deg": pi / 10.0, "yaw_deg": float(y)}
 
 
def dec_altitude(p):
    alt, vario = struct.unpack_from("<ih", p)
    out = {"est_alt_cm": alt, "est_vario_cms": vario}
    if len(p) >= 10:
        out["baro_alt_cm"] = struct.unpack_from("<i", p, 6)[0]
    return out
 
 
# INAV rangefinder.h: values <= 0 are states, not distances
RF_STATES = {0: "zero", -1: "out_of_range", -2: "hw_failure", -3: "no_new_data"}
 
 
def dec_sonar(p):
    (cm,) = struct.unpack_from("<i", p)
    out = {"rangefinder_valid": 1.0 if cm > 0 else 0.0, "_rf_code": cm}
    if cm > 0:
        out["rangefinder_cm"] = cm
    return out
 
 
def dec_opflow(p):
    q, fx, fy, bx, by = struct.unpack_from("<B4h", p)
    return {"flow_quality": q, "flow_rate_x_dps": fx, "flow_rate_y_dps": fy,
            "flow_body_x_dps": bx, "flow_body_y_dps": by}
 
 
def dec_analog(p):
    flags, vbat, amp = struct.unpack_from("<BHh", p)
    out = {"vbat_v": vbat / 100.0, "current_a": amp / 100.0}
    cells = flags >> 4
    if cells:
        out["cell_v"] = vbat / 100.0 / cells
    if len(p) >= 24:
        out["mah_drawn"] = struct.unpack_from("<I", p, 9)[0]
        out["battery_pct"] = p[21]
        out["rssi_raw"] = struct.unpack_from("<H", p, 22)[0]
    return out
 
 
def dec_local_pose(p):
    """INAV's own position/velocity estimate: drift at rest matters for autonomy and the sim."""
    x, vx, y, vy, z, vz = struct.unpack_from("<ihihih", p, 6)
    return {"pose_x_cm": x, "pose_y_cm": y, "pose_z_cm": z,
            "pose_vx_cms": vx, "pose_vy_cms": vy, "pose_vz_cms": vz}
 
 
def dec_link_stats(p):
    rssi, lq, snr = struct.unpack_from("<BBb", p)
    return {"elrs_rssi_dbm": -rssi, "elrs_lq_pct": lq, "elrs_snr_db": snr}
 
 
def dec_rc(p):
    n = min(len(p) // 2, 8)
    return {f"rc_ch{i + 1}_us": v for i, v in enumerate(struct.unpack_from(f"<{n}H", p))}
 
 
def dec_status(p):
    cycle, i2c, _sens, load = struct.unpack_from("<4H", p)
    return {"cycle_time_us": cycle, "i2c_errors": i2c, "cpu_load_pct": load}
 
 
SENSOR_CMDS = [
    (MSP_RAW_IMU, dec_raw_imu),
    (MSP_ATTITUDE, dec_attitude),
    (MSP_ALTITUDE, dec_altitude),
    (MSP_SONAR_ALTITUDE, dec_sonar),
    (MSP2_INAV_OPTICAL_FLOW, dec_opflow),
    (MSP2_INAV_ANALOG, dec_analog),
    (MSP2_INAV_FULL_LOCAL_POSE, dec_local_pose),
    (MSP_RC, dec_rc),
    (MSP2_INAV_GET_LINK_STATS, dec_link_stats),
    (MSP2_INAV_STATUS, dec_status),
]
 
 
def unit_of(metric: str) -> str:
    for suffix, unit in (("_dbm", "dBm"), ("_db", "dB"), ("_g", "g"), ("_dps", "deg/s"), ("_deg", "deg"),
                         ("_cms", "cm/s"), ("_cm", "cm"), ("_us", "us"),
                         ("_pct", "%"), ("_v", "V"), ("_a", "A"), ("_ms", "ms"),
                         ("_hz", "Hz")):
        if metric.endswith(suffix):
            return unit
    return {"mah_drawn": "mAh", "flow_quality": "0-255", "rssi_raw": "0-1023",
            "rangefinder_valid": "ratio"}.get(metric, "")
 
 
# --------------------------------------------------------------------------- #
# Stats helpers
# --------------------------------------------------------------------------- #
def percentile(sorted_vals, p):
    if not sorted_vals:
        return math.nan
    k = (len(sorted_vals) - 1) * p / 100.0
    f = math.floor(k)
    c = min(f + 1, len(sorted_vals) - 1)
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)
 
 
def summarize(vals):
    v = sorted(vals)
    if not v:
        return None
    return {"n": len(v), "median": statistics.median(v), "mean": statistics.fmean(v),
            "std": statistics.pstdev(v) if len(v) > 1 else 0.0,
            "min": v[0], "max": v[-1], "p05": percentile(v, 5),
            "p95": percentile(v, 95), "p99": percentile(v, 99)}
 
 
def slope_per_min(ts, vs):
    if len(ts) < 3:
        return math.nan
    mt, mv = statistics.fmean(ts), statistics.fmean(vs)
    den = sum((t - mt) ** 2 for t in ts)
    return 60.0 * sum((t - mt) * (v - mv) for t, v in zip(ts, vs)) / den if den else math.nan
 
 
def unwrap_deg(vals):
    out, offset = [], 0.0
    for i, v in enumerate(vals):
        if i:
            d = v - vals[i - 1]
            if d > 180:
                offset -= 360
            elif d < -180:
                offset += 360
        out.append(v + offset)
    return out
 
 
# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
FIELDS = ["run_id", "timestamp_utc", "host", "link", "section", "item", "value",
          "unit", "status", "n", "mean", "std", "min", "max", "p05", "p95", "p99",
          "notes"]
 
 
def _fmt(x):
    if isinstance(x, float):
        return "" if math.isnan(x) else f"{x:.6g}"
    return x
 
 
class Report:
    def __init__(self, run_id, host, link):
        self.run_id, self.host, self.link = run_id, host, link
        self.rows = []
        self.raw = []  # (section, item, t_s, value)
 
    def add(self, section, item, value="", unit="", status="INFO", notes="", stats=None):
        row = {k: "" for k in FIELDS}
        row.update(run_id=self.run_id, host=self.host, link=self.link,
                   timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   section=section, item=item, value=_fmt(value), unit=unit,
                   status=status, notes=notes)
        if stats:
            for k in ("n", "mean", "std", "min", "max", "p05", "p95", "p99"):
                row[k] = _fmt(stats[k])
        self.rows.append(row)
        return row
 
    @property
    def worst(self):
        s = {r["status"] for r in self.rows}
        return "FAIL" if "FAIL" in s else "WARN" if "WARN" in s else "PASS"
 
    def write(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(self.rows)
 
    def write_raw(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["run_id", "host", "link", "section", "item", "t_s", "value"])
            for sec, item, t, v in self.raw:
                w.writerow([self.run_id, self.host, self.link, sec, item, f"{t:.6f}", _fmt(v)])
 
    def print_summary(self, ui, brief=False):
        Printer(ui).report(self, brief)
 
 
# --------------------------------------------------------------------------- #
# Terminal output
# --------------------------------------------------------------------------- #
class UI:
    """ANSI colors. red = needs attention, green = important pass,
    faded yellow = failed/warned but no action needed."""
 
    def __init__(self, mode="auto"):
        if mode == "always":
            self.on = True
        elif mode == "never" or os.environ.get("NO_COLOR"):
            self.on = False
        else:
            self.on = sys.stdout.isatty()
        if self.on and os.name == "nt":
            os.system("")  # enables ANSI escape codes on Windows 10+
        enc = (getattr(sys.stdout, "encoding", "") or "").lower()
        uni = "utf" in enc
        self.ok, self.bad, self.dot, self.rule = (("✔", "✖", "•", "─") if uni else ("+", "x", "-", "-"))
 
    def _c(self, code, t):
        return f"\033[{code}m{t}\033[0m" if self.on else t
 
    def red(self, t): return self._c("1;31", t)
    def green(self, t): return self._c("32", t)
    def faded(self, t): return self._c("38;5;144", t)  # muted yellow
    def bold(self, t): return self._c("1", t)
    def dim(self, t): return self._c("2", t)
    def cyan(self, t): return self._c("36", t)
 
    def step(self, text):
        print(self.dim(f"  › {text}"), flush=True)
 
 
SECTION_TITLES = {
    "info": "Flight controller", "sensor_status": "Sensor status",
    "sensor_rate": "Sample rate per MSP command", "sensors": "Sensor values",
    "derived": "Checks", "latency": "Link latency & heavy MSP load",
    "link": "Link health", "diagnose": "Diagnosis", "run": "Run",
    "capture": "Capture (recording for the tests)",
    "mtf_config": "MTF-02P setup (INAV settings & port)",
    "mtf": "MTF-02P at rest",
    "flow_motion": "MTF-02P motion test",
}
 
 
def nice(v):
    """Readable number formatting for the terminal (CSV keeps full precision)."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return str(v)
    if math.isnan(x):
        return "-"
    if x.is_integer() and abs(x) < 1e9:
        return str(int(x))
    if abs(x) >= 1e4:
        return f"{x:.0f}"
    return f"{x:.4g}"
 
 
class Printer:
    W = 74
 
    def __init__(self, ui):
        self.ui = ui
 
    def title(self, text):
        u = self.ui
        print("\n" + u.bold(u.cyan(f"{u.rule * 2} {text} ")) + u.cyan(u.rule * max(0, self.W - len(text) - 4)))
 
    def badge(self, status):
        u = self.ui
        if status == "PASS":
            return u.green(f"{u.ok} PASS")
        if status == "FAIL":
            return u.red(f"{u.bad} FAIL")
        if status == "WARN":
            return u.faded(f"{u.dot} note")
        return "      "
 
    def line(self, r, value_w=14):
        u = self.ui
        item, val, unit, note = r["item"], nice(r["value"]), r["unit"], r["notes"]
        text = f"{item:<28}{val:>{value_w}} {unit:<8}"
        if r["status"] == "FAIL":
            text = u.red(text)
            note = u.red(note)
        elif r["status"] == "WARN":
            text, note = u.faded(text), u.faded(note)
        else:
            note = u.dim(note)
        print(f"  {self.badge(r['status'])}  {text} {note}".rstrip())
 
    def header(self, rep):
        u = self.ui
        env = {r["item"]: r["value"] for r in rep.rows if r["section"] == "env"}
        info = {r["item"]: r for r in rep.rows if r["section"] == "info"}
        print(u.bold(f"MSP bench  ·  run {rep.run_id}"))
        print(u.dim(f"{rep.host} ({env.get('machine', '?')}, Python {env.get('python', '?')})  ·  {rep.link}"))
        if "fc_variant" in info:
            fc = (f"{info['fc_variant']['value']} {info.get('fc_version', {}).get('value', '')}  ·  "
                  f"board {info.get('board_id', {}).get('value', '?')}  ·  "
                  f"{info.get('craft_name', {}).get('value', '')}  ·  "
                  f"MSP {info.get('msp_api', {}).get('value', '?')}")
            print(u.dim(fc))
 
    def sensors_table(self, rows):
        u = self.ui
        print(u.dim(f"  {'value':<22}{'median':>11}{'std (noise)':>13}{'min':>10}{'max':>10}  unit"))
        for r in rows:
            name = f"{r['item']:<22}"
            nums = f"{nice(r['value']):>11}{nice(r['std']):>13}{nice(r['min']):>10}{nice(r['max']):>10}"
            print(f"  {name}{u.bold(nums[:11])}{nums[11:]}  {u.dim(r['unit'])}")
 
    def latency_table(self, rows):
        u = self.ui
        stat_rows = [r for r in rows if r["p95"]]
        other = [r for r in rows if not r["p95"]]
        if stat_rows:
            print(u.dim(f"  {'':6}  {'test':<24}{'median':>9}{'p95':>9}{'p99':>9}{'max':>9}  ms   notes"))
            for r in stat_rows:
                nums = f"{nice(r['value']):>9}{nice(r['p95']):>9}{nice(r['p99']):>9}{nice(r['max']):>9}"
                text = f"{r['item']:<24}{nums}"
                note = r["notes"]
                if r["status"] == "FAIL":
                    text, note = u.red(text), u.red(note)
                elif r["status"] == "WARN":
                    text, note = u.faded(text), u.faded(note)
                else:
                    note = u.dim(note)
                print(f"  {self.badge(r['status'])}  {text}       {note}")
        if other:
            print()
            for r in other:
                self.line(r)
 
    def report(self, rep, brief=False):
        print()
        self.header(rep)
        order, by_sec = [], defaultdict(list)
        for r in rep.rows:
            if r["section"] == "env":
                continue
            if r["section"] not in by_sec:
                order.append(r["section"])
            by_sec[r["section"]].append(r)
        for sec in order:
            rows = by_sec[sec]
            if sec == "info":
                keep = ("armed", "arming_blockers", "msp_api", "first_reply_after_s")
                rows = [r for r in rows
                        if r["item"] in keep and (r["item"] != "msp_api" or r["status"] != "INFO")]
            if brief and sec in ("sensors", "sensor_rate"):
                rows = [r for r in rows if r["status"] not in ("INFO", "PASS")]
            if not rows:
                continue
            title = SECTION_TITLES.get(sec, sec)
            if sec == "sensors" and rows[0]["notes"].startswith("median over"):
                title += f" ({rows[0]['notes'].split(';')[0]}, drone still)"
            self.title(title)
            if sec == "sensors" and not brief:
                self.sensors_table(rows)
            elif sec == "latency":
                self.latency_table(rows)
            else:
                for r in rows:
                    self.line(r)
        self.summary(rep)
 
    def summary(self, rep):
        u = self.ui
        fails = [r for r in rep.rows if r["status"] == "FAIL"]
        warns = [r for r in rep.rows if r["status"] == "WARN"]
        passes = [r for r in rep.rows if r["status"] == "PASS"]
        verdict = "FAIL" if fails else "PASS"  # notes never fail a run
        head = u.red if fails else u.green
        print("\n" + head(u.rule * self.W))
        print(head(u.bold(f"  RESULT: {verdict}")) +
              f"   {u.red(str(len(fails)) + ' need attention') if fails else '0 need attention'}"
              f"  ·  {u.faded(str(len(warns)) + ' noted')}  ·  {u.green(str(len(passes)) + ' passed')}")
        if fails:
            print(u.red("\n  Needs attention:"))
            for r in fails:
                print(u.red(f"    {u.bad} {r['item']}: {nice(r['value'])} {r['unit']}".rstrip()
                            + (f"  - {r['notes']}" if r["notes"] else "")))
        if warns:
            print(u.faded("\n  Noted, no action needed:"))
            for r in warns:
                print(u.faded(f"    {u.dot} {r['item']}: {nice(r['value'])} {r['unit']}".rstrip()
                              + (f"  - {r['notes']}" if r["notes"] else "")))
        print(head(u.rule * self.W))
 
 
# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def env_rows(rep, args):
    rep.add("env", "python", platform.python_version())
    rep.add("env", "os", platform.platform())
    model = ""
    try:
        with open("/proc/device-tree/model", "rb") as f:
            model = f.read().rstrip(b"\x00").decode(errors="replace")
    except OSError:
        pass
    rep.add("env", "machine", model or platform.machine())
    rep.add("env", "is_raspberry_pi", int("Raspberry Pi" in model))
    rep.add("env", "args", " ".join(sys.argv[1:]) or "(defaults)")
 
 
def test_info(c, rep, timeout, connect_wait=0.0):
    def get(cmd):
        try:
            return c.request(cmd, timeout=timeout)[0]
        except (MspTimeout, MspError):
            return None
 
    p, tries, t_start = None, 0, time.perf_counter()
    while True:
        tries += 1
        p = get(MSP_API_VERSION)
        if p is not None or time.perf_counter() - t_start >= connect_wait:
            break
        c.drain(0.05, 0.3)
    if p is not None and tries > 1:
        rep.add("info", "first_reply_after_s", time.perf_counter() - t_start, "s", "WARN",
                f"{tries} tries; link was not ready at open (ESP rebooting / Wi-Fi joining?)")
    if p is None or len(p) < 3:
        rep.add("info", "msp_api", "no reply", status="FAIL",
                notes=f"{tries} tries over {time.perf_counter() - t_start:.1f}s")
        diagnose_no_reply(c, rep)
        return False
    rep.add("info", "msp_api", f"{p[1]}.{p[2]}", notes=f"protocol {p[0]}")
    if (p := get(MSP_FC_VARIANT)):
        rep.add("info", "fc_variant", p[:4].decode(errors="replace"))
    if (p := get(MSP_FC_VERSION)) and len(p) >= 3:
        rep.add("info", "fc_version", f"{p[0]}.{p[1]}.{p[2]}")
    if (p := get(MSP_BOARD_INFO)):
        rep.add("info", "board_id", p[:4].decode(errors="replace"))
    if (p := get(MSP_BUILD_INFO)) and len(p) >= 26:
        rep.add("info", "build", f"{p[:11].decode(errors='replace')} {p[11:19].decode(errors='replace')}",
                notes=f"git {p[19:26].decode(errors='replace')}")
    if (p := get(MSP_NAME)) is not None:
        rep.add("info", "craft_name", p.decode(errors="replace") or "(empty)")
    return True
 
 
def diagnose_no_reply(c, rep):
    p = c.parser
    rx, garbage = c.rx_bytes, p.garbage_bytes
    sample = bytes(c.raw_rx[:48])
    rep.add("diagnose", "rx_bytes", rx, "B")
    rep.add("diagnose", "garbage_bytes", garbage, "B")
    rep.add("diagnose", "crc_errors", p.crc_errors)
    if sample:
        rep.add("diagnose", "first_rx_bytes", sample.hex(" "),
                notes=repr(sample.decode("ascii", errors="replace"))[:80])
    if rx == 0:
        hint = ("nothing came back: bridge not forwarding (Pi ESP not linked to drone AP?), "
                "another process holds the port, or FC UART not set to MSP")
    elif "$M" in sample.decode("latin1") or "$X" in sample.decode("latin1"):
        hint = "MSP-looking bytes but no valid reply: CRC/baud problem or replies to another client"
    else:
        hint = "non-MSP bytes: wrong baud, ESP boot log, CLI mode, or bridge firmware chatter"
    rep.add("diagnose", "hint", hint, status="FAIL")
 
 
def read_armed(c, timeout):
    try:
        p, _ = c.request(MSP2_INAV_STATUS, timeout=timeout)
        flags = struct.unpack_from("<I", p, 9)[0] if len(p) >= 13 else None
    except (MspTimeout, MspError, struct.error):
        return None, None
    return (None if flags is None else bool(flags & ARMED_BIT)), flags
 
 
def read_sensor_status(c, timeout):
    p, _ = c.request(MSP_SENSOR_STATUS, timeout=timeout)
    st = {"hardware_healthy": "OK" if p and p[0] else "NO"}
    for i, name in enumerate(SENSOR_NAMES):
        if 1 + i < len(p):
            st[name] = HW_STATUS.get(p[1 + i], f"?{p[1 + i]}")
    return st
 
 
def test_sensor_status(c, rep, expect, timeout):
    try:
        st = read_sensor_status(c, timeout)
    except (MspTimeout, MspError) as e:
        rep.add("sensor_status", "read", "failed", status="FAIL", notes=str(e))
        return None
    rep.add("sensor_status", "hardware_healthy", st["hardware_healthy"],
            status="PASS" if st["hardware_healthy"] == "OK" else "FAIL")
    for name in SENSOR_NAMES:
        if name not in st:
            continue
        v = st[name]
        if name in expect:
            status, note = ("PASS" if v == "OK" else "FAIL"), "expected"
        else:
            status, note = ("WARN" if v == "UNHEALTHY" else "INFO"), ""
        rep.add("sensor_status", name, v, status=status, notes=note)
    for name in expect - set(st):
        rep.add("sensor_status", name, "not reported", status="FAIL", notes="expected")
    return st
 
 
NEEDS_SENSOR = {MSP_SONAR_ALTITUDE: "rangefinder", MSP2_INAV_OPTICAL_FLOW: "opflow"}
 
 
def test_sensors(c, rep, duration, timeout, status=None):
    # probe which commands this firmware/config answers
    active = []
    for cmd, dec in SENSOR_CMDS:
        need = NEEDS_SENSOR.get(cmd)
        if need and status and status.get(need) != "OK":
            rep.add("sensor_rate", CMD_NAMES[cmd], "skipped",
                    notes=f"{need} is {status.get(need)} (FC replies with zeros)")
            continue
        try:
            p, _ = c.request(cmd, timeout=timeout)
            dec(p)
            active.append((cmd, dec))
        except (MspTimeout, MspError, struct.error) as e:
            rep.add("sensor_rate", CMD_NAMES[cmd], "unsupported", status="INFO", notes=str(e) or type(e).__name__)
 
    samples = defaultdict(list)  # metric -> [(t, v)]
    counts = defaultdict(int)
    timeouts = defaultdict(int)
    t0 = time.perf_counter()
    while active and time.perf_counter() - t0 < duration:
        for cmd, dec in active:
            try:
                p, _ = c.request(cmd, timeout=timeout)
            except MspTimeout:
                timeouts[cmd] += 1
                c.drain(0.02, 0.2)
                continue
            except MspError:
                continue
            t = time.perf_counter() - t0
            try:
                vals = dec(p)
            except struct.error:
                continue
            counts[cmd] += 1
            for k, v in vals.items():
                samples[k].append((t, float(v)))
    elapsed = time.perf_counter() - t0
 
    for cmd, _ in active:
        rate = counts[cmd] / elapsed if elapsed else 0
        rep.add("sensor_rate", CMD_NAMES[cmd], rate, "Hz",
                status="WARN" if timeouts[cmd] else "INFO",
                notes=f"{counts[cmd]} samples, {timeouts[cmd]} timeouts")
 
    for metric, tv in samples.items():
        if metric.startswith("_"):
            continue
        vals = [v for _, v in tv]
        s = summarize(vals)
        note = f"median over {elapsed:.1f}s"
        if metric.startswith("gyro_") or metric == "yaw_deg":
            note += "; MSP gives 1 deg/s (gyro) / 1 deg (yaw) steps, use blackbox for real noise"
        rep.add("sensors", metric, s["median"], unit_of(metric), stats=s, notes=note)
        rep.raw.extend(("sensors", metric, t, v) for t, v in tv)
    return samples, elapsed
 
 
def derived_checks(rep, samples, args):
    def med(k):
        return statistics.median([v for _, v in samples[k]]) if samples.get(k) else None
 
    if (m := med("acc_norm_g")) is not None:
        ok = abs(m - 1.0) <= args.acc_tol
        rep.add("derived", "acc_norm_error_g", m - 1.0, "g", "PASS" if ok else "FAIL",
                "" if ok else "drone moving or accelerometer not calibrated")
    for ax in "xyz":
        if (m := med(f"gyro_{ax}_dps")) is not None:
            ok = abs(m) <= args.gyro_bias_tol
            rep.add("derived", f"gyro_bias_{ax}_dps", m, "deg/s", "PASS" if ok else "FAIL",
                    "" if ok else "drone moving or gyro needs calibration")
    if samples.get("roll_deg") and samples.get("pitch_deg"):
        rep.add("derived", "level_tilt_deg",
                math.hypot(med("roll_deg"), med("pitch_deg")), "deg",
                notes="tilt at rest (bench level reference)")
    if samples.get("yaw_deg"):
        ts = [t for t, _ in samples["yaw_deg"]]
        ys = unwrap_deg([v for _, v in samples["yaw_deg"]])
        rep.add("derived", "yaw_drift_deg_per_min", slope_per_min(ts, ys), "deg/min",
                notes="heading drift at rest (no mag = gyro-only)")
    for k in ("est_alt_cm", "baro_alt_cm"):
        if samples.get(k):
            ts, vs = zip(*samples[k])
            rep.add("derived", f"{k[:-3]}_drift_cm_per_min", slope_per_min(ts, vs), "cm/min",
                    notes="altitude drift at rest")
    for ax in ("x", "y", "z"):
        k = f"pose_{ax}_cm"
        if samples.get(k):
            ts, vs = zip(*samples[k])
            rep.add("derived", f"pose_{ax}_drift_cm_per_min", slope_per_min(ts, vs), "cm/min",
                    notes="INAV position estimate drift at rest")
    if samples.get("i2c_errors"):
        d = samples["i2c_errors"][-1][1] - samples["i2c_errors"][0][1]
        rep.add("derived", "i2c_errors_delta", d, "", "PASS" if d == 0 else "FAIL",
                "new I2C errors during the run" if d else "")
        total = samples["i2c_errors"][-1][1]
        if total and not d:
            rep.add("derived", "i2c_errors_since_boot", total, "", "WARN",
                    "old errors from boot (sensor probing), none during this run")
    mtf_still_checks(rep, samples, args)
    if (m := med("cell_v")) is not None:
        if med("vbat_v") is not None and med("vbat_v") < 3.0:
            rep.add("derived", "cell_voltage_v", "no battery", "", "WARN", "USB-powered")
        else:
            rep.add("derived", "cell_voltage_v", m, "V", "PASS" if m >= 3.5 else "FAIL",
                    "" if m >= 3.5 else "battery low, charge before flight tests")
    if (m := med("cycle_time_us")) is not None:
        rep.add("derived", "fc_loop_hz", 1e6 / m if m else math.nan, "Hz")
 
 
# --------------------------------------------------------------------------- #
# MTF-02P (MSP rangefinder + optical flow)
# --------------------------------------------------------------------------- #
# INAV setting types (settings.h, low 3 bits of the type byte)
SETTING_FMT = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<f"}
BAUD_RATES = [0, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 250000,
              460800, 921600, 1000000, 1500000, 2000000, 2470000]
FUNCTION_MSP = 1 << 0
 
# (setting, required value or None, note)
MTF_SETTINGS = [
    ("rangefinder_hardware", "MSP", "MTF-02P sends MSP2_SENSOR_RANGEFINDER", "rangefinder"),
    ("opflow_hardware", "MSP", "MTF-02P sends MSP2_SENSOR_OPTIC_FLOW", "opflow"),
    ("opflow_scale", None, "calibrate in flight (default until then)", "opflow"),
    ("align_opflow", None, "must match how the sensor is mounted", "opflow"),
    ("rangefinder_median_filter", None, "smoothing of the distance", "rangefinder"),
    ("inav_max_surface_altitude", None, "above this the rangefinder is ignored (cm)", "rangefinder"),
    ("inav_w_z_surface_p", None, "estimator weight: rangefinder -> altitude", "rangefinder"),
    ("inav_w_z_surface_v", None, "estimator weight: rangefinder -> climb rate", "rangefinder"),
    ("inav_w_xy_flow_p", None, "estimator weight: flow -> position", "opflow"),
    ("inav_w_xy_flow_v", None, "estimator weight: flow -> velocity", "opflow"),
]
 
 
def read_setting(c, name, timeout):
    """MSP2_COMMON_SETTING_INFO: returns the value as text (lookup name for enums).
    Layout: name\\0, pg u16, type u8, section u8, mode u8, min i32, max u32, index u16,
    profile u8, profile count u8, [lookup names \\0 ...], value. The value is read from
    the end (its size follows from the type), so the mode byte need not be decoded."""
    p, _ = c.request(MSP2_COMMON_SETTING_INFO, name.encode() + b"\0", timeout=timeout)
    pos = p.index(0) + 1
    _pg, typ, _sec, _mode, vmin, _vmax = struct.unpack_from("<HBBBiI", p, pos)
    pos += 2 + 3 + 8 + 2 + 2
    vtype = typ & 0x07
    if vtype not in SETTING_FMT:              # string setting
        return p[pos:].split(b"\0")[0].decode(errors="replace")
    fmt = SETTING_FMT[vtype]
    size = struct.calcsize(fmt)
    (value,) = struct.unpack_from(fmt, p, len(p) - size)
    names = p[pos:len(p) - size]
    if names:                                 # lookup table -> enum name
        table = names.rstrip(b"\0").split(b"\0")
        i = int(value) - vmin
        if 0 <= i < len(table):
            return table[i].decode(errors="replace")
    return f"{value:.4g}" if isinstance(value, float) else str(value)
 
 
def test_mtf_config(c, rep, a):
    for name, want, note, sensor in MTF_SETTINGS:
        if sensor not in a.expect:
            continue
        try:
            v = read_setting(c, name, a.timeout)
        except MspError:
            rep.add("mtf_config", name, "n/a", notes="not in this firmware")
            continue
        except (MspTimeout, ValueError, struct.error) as e:
            rep.add("mtf_config", name, "unreadable", status="WARN", notes=str(e) or type(e).__name__)
            continue
        if want is None:
            rep.add("mtf_config", name, v, notes=note)
        else:
            ok = v.upper() == want
            rep.add("mtf_config", name, v, status="PASS" if ok else "FAIL",
                    notes=note if ok else f"set {name} = {want}")
 
    # the sensor's UART: MSP on, nothing else (a serial 'Rangefinder' function on the
    # same port grabs it and the MSP sensor packets are never decoded)
    item = f"uart{a.sensor_uart}_functions"
    try:
        p, _ = c.request(MSP2_CF_SERIAL_CONFIG, timeout=a.timeout)
    except (MspTimeout, MspError) as e:
        rep.add("mtf_config", item, "unreadable", status="WARN", notes=str(e))
        return
    ports = {}
    for off in range(0, len(p) - 8, 9):
        ident, mask, msp_b, _gps, _tel, _per = struct.unpack_from("<BIBBBB", p, off)
        ports[ident] = (mask, msp_b)
    ident = a.sensor_uart - 1                 # INAV: UART1 = identifier 0
    if ident not in ports:
        rep.add("mtf_config", item, "no such port", status="FAIL",
                notes=f"ports on this board: {', '.join(f'UART{i + 1}' for i in sorted(ports) if i < 20)}")
        return
    mask, msp_b = ports[ident]
    if not mask & FUNCTION_MSP:
        rep.add("mtf_config", item, f"0x{mask:x}", status="FAIL",
                notes="MSP is off on the sensor port (Ports tab: enable MSP)")
    elif mask & ~FUNCTION_MSP:
        rep.add("mtf_config", item, f"0x{mask:x}", status="FAIL",
                notes="other functions on the sensor port too: leave only MSP "
                      "(Sensors/Telemetry/Peripherals = Disabled)")
    else:
        rep.add("mtf_config", item, "MSP only", status="PASS")
    baud = BAUD_RATES[msp_b] if msp_b < len(BAUD_RATES) else f"index {msp_b}"
    rep.add("mtf_config", f"uart{a.sensor_uart}_msp_baud", baud,
            notes="must match the MTF-02P's output baud")
    others = [f"UART{i + 1}" for i, (m, _) in ports.items()
              if i != ident and i < 20 and m & FUNCTION_MSP]
    if others:
        rep.add("mtf_config", "other_msp_ports", " ".join(others),
                notes="fine (e.g. the ESP bridge); just not the sensor's")
 
 
def mtf_still_checks(rep, samples, args):
    """Rangefinder and flow at rest (from the normal sampling run)."""
    rf_exp, fl_exp = "rangefinder" in args.expect, "opflow" in args.expect
    codes = [int(v) for _, v in samples.get("_rf_code", [])]
    if codes:
        n = len(codes)
        valid = sum(c > 0 for c in codes)
        pct = 100 * valid / n
        rep.add("mtf", "rangefinder_valid_pct", pct, "%",
                ("PASS" if pct >= 95 else "WARN") if rf_exp else "INFO",
                "share of readings with a distance"
                + ("; tilted/upside down or out of range counts as invalid" if rf_exp
                   else " (rangefinder not expected)"))
        states = defaultdict(int)
        for c in codes:
            if c <= 0:
                states[RF_STATES.get(c, f"code_{c}")] += 1
        if states:
            text = ", ".join(f"{k} {v}" for k, v in sorted(states.items()))
            bad = states.get("hw_failure", 0)
            rep.add("mtf", "rangefinder_invalid_states", text, "",
                    "FAIL" if bad and rf_exp else "INFO",
                    "hardware failure reported by INAV" if bad else
                    "out_of_range = too close/far or no surface; no_new_data = sensor stopped sending")
        dist = [v for _, v in samples.get("rangefinder_cm", [])]
        if len(dist) >= 3:
            sd = statistics.pstdev(dist)
            ok = sd <= args.rf_noise_max
            rep.add("mtf", "rangefinder_noise_cm", sd, "cm",
                    ("PASS" if ok else "WARN") if rf_exp else "INFO",
                    f"std at rest, limit {args.rf_noise_max:g} cm" + ("" if ok else
                    "; hand-held or shiny/soft surface adds noise"))
            rep.add("mtf", "rangefinder_distance_cm", statistics.median(dist), "cm",
                    notes=f"{min(dist):.0f}-{max(dist):.0f} cm")
            changes = sum(1 for x, y in zip(dist, dist[1:]) if x != y)
            rep.add("mtf", "rangefinder_value_changes_pct", 100 * changes / (len(dist) - 1), "%",
                    notes="share of polls with a new value; ~0% with the drone still "
                          "can mean a frozen sensor")
 
    q = [v for _, v in samples.get("flow_quality", [])]
    if q:
        good = 100 * sum(v >= args.flow_quality_min for v in q) / len(q)
        med_q = statistics.median(q)
        if not fl_exp:
            st = "INFO"
        elif max(q) == 0:
            st = "FAIL"
        else:
            st = "PASS" if good >= 50 else "WARN"
        rep.add("mtf", "flow_quality_median", med_q, "0-255", st,
                "quality always 0: no flow data from the sensor" if st == "FAIL" else
                "depends on surface texture, light and height")
        rep.add("mtf", "flow_quality_good_pct", good, "%",
                notes=f"quality >= {args.flow_quality_min}")
        peaks = [abs(v) for k in ("flow_rate_x_dps", "flow_rate_y_dps")
                 for _, v in samples.get(k, [])]
        if peaks:
            rep.add("mtf", "flow_rate_at_rest_peak_dps", max(peaks), "deg/s",
                    notes="should stay near 0 with the drone still; "
                          "use --flow-motion to see it respond")
 
 
MOTION_PHASES = [
    ("still", "hold it still"),
    ("forward", "slide it FORWARD (nose direction)"),
    ("back", "slide it BACK"),
    ("right", "slide it RIGHT"),
    ("left", "slide it LEFT"),
]
 
 
def test_flow_motion(c, rep, ui, a):
    """Guided motion: each phase polls only flow + rangefinder (much faster than the
    round-robin sampling) and records mean/peak flow per axis."""
    cmds = [(MSP2_INAV_OPTICAL_FLOW, dec_opflow), (MSP_SONAR_ALTITUDE, dec_sonar)]
    ui.step("flow motion test: level, ~0.3-1 m over a textured surface, slow and steady")
    t_start = time.perf_counter()
    got = {}
    for key, text in MOTION_PHASES:
        ui.step(f"next: {text} - in 3 s")
        time.sleep(3.0)
        ui.step(f"  now: {text} ({a.flow_phase:g} s)")
        smp = defaultdict(list)
        polls = 0
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < a.flow_phase:
            for cmd, dec in cmds:
                try:
                    p, _ = c.request(cmd, timeout=a.timeout)
                    vals = dec(p)
                except MspTimeout:
                    c.drain(0.02, 0.2)
                    continue
                except (MspError, struct.error):
                    continue
                t = time.perf_counter() - t_start
                for k, v in vals.items():
                    smp[k].append(float(v))
                    rep.raw.append(("flow_motion", f"{key}.{k}", t, float(v)))
            polls += 1
        dt = time.perf_counter() - t0
        fx, fy = smp.get("flow_rate_x_dps", []), smp.get("flow_rate_y_dps", [])
        if not fx:
            rep.add("flow_motion", key, "no data", status="FAIL", notes="no flow replies")
            continue
        mx, my = statistics.fmean(fx), statistics.fmean(fy)
        peak = max(max(map(abs, fx)), max(map(abs, fy)))
        q = statistics.median(smp["flow_quality"])
        codes = smp.get("_rf_code", [])
        rfv = 100 * sum(v > 0 for v in codes) / len(codes) if codes else 0
        dist = smp.get("rangefinder_cm", [])
        rf = f"{statistics.median(dist):.0f} cm" if dist else "no distance"
        rep.add("flow_motion", key, f"x {mx:+.1f} y {my:+.1f}", "deg/s",
                notes=f"mean flow; peak {peak:.0f}, quality {q:.0f}, "
                      f"rangefinder {rf} ({rfv:.0f}% valid), {polls / dt:.0f} polls/s")
        got[key] = dict(mx=mx, my=my, peak=peak, q=q, rfv=rfv)
 
    if "still" not in got or len(got) < len(MOTION_PHASES):
        return
    moving = [k for k, _ in MOTION_PHASES if k != "still"]
    floor = max(a.flow_min_dps, 2 * got["still"]["peak"])
    dead = [k for k in moving if got[k]["peak"] < floor]
    rep.add("flow_motion", "flow_responds", "no: " + ", ".join(dead) if dead else "yes", "",
            "FAIL" if dead else "PASS",
            f"peak must reach {floor:.0f} deg/s in every direction" +
            ("; check surface texture, light, height and the jumper/protocol" if dead else ""))
 
    def axis(k):
        mx, my = got[k]["mx"], got[k]["my"]
        return ("X", mx) if abs(mx) >= abs(my) else ("Y", my)
 
    def label(k):
        ax, v = axis(k)
        return f"{'+' if v >= 0 else '-'}{ax}"
 
    if not dead:
        f_ax, f_v = axis("forward")
        b_ax, b_v = axis("back")
        r_ax, r_v = axis("right")
        l_ax, l_v = axis("left")
        consistent = (f_ax == b_ax and r_ax == l_ax and f_ax != r_ax
                      and f_v * b_v < 0 and r_v * l_v < 0)
        mapping = f"fwd {label('forward')}, back {label('back')}, right {label('right')}, left {label('left')}"
        rep.add("flow_motion", "axis_mapping", mapping, "",
                "PASS" if consistent else "WARN",
                "opposite moves give opposite signs on one axis; compare with INAV's "
                "convention and fix align_opflow if mirrored or rotated" if consistent else
                "directions don't separate cleanly: moved diagonally or rotated while sliding? "
                "repeat; if it persists check align_opflow")
    q_move = statistics.median(got[k]["q"] for k in moving)
    rep.add("flow_motion", "quality_while_moving", q_move, "0-255",
            "PASS" if q_move >= a.flow_quality_min else "WARN",
            f"median over the moving phases, want >= {a.flow_quality_min}")
    rfv = statistics.fmean(got[k]["rfv"] for k in moving)
    rep.add("flow_motion", "rangefinder_valid_while_moving", rfv, "%",
            "PASS" if rfv >= 95 else "WARN", "rangefinder kept a distance while sliding")
 
 
def latency_sequential(c, rep, count, timeout, warn_ms, commands, interval=0.0):
    """One request at a time. Returns the totals the logbook keeps (see summary_values)."""
    c.drain()
    all_rtts = []
    seq = {"sent": 0, "lost": 0, "rtts": [], "late": 0, "corrupted": 0, "duration_s": 0.0}
    late0, crc0, t_start = c.late_frames, c.parser.crc_errors, time.perf_counter()
    for cmd in commands:
        rtts, lost, plen = [], 0, 0
        for _ in range(count):
            try:
                p, rtt = c.request(cmd, timeout=timeout)
                plen = len(p)
                rtts.append(rtt * 1000)
            except MspTimeout:
                lost += 1
            except MspError:
                lost = -1
                break
            if interval:
                time.sleep(interval)
        if lost < 0:
            rep.add("latency", f"rtt_{CMD_NAMES[cmd]}", "unsupported")
            continue
        seq["sent"] += len(rtts) + lost
        seq["lost"] += lost
        seq["rtts"] += rtts
        s = summarize(rtts)
        if not s:
            rep.add("latency", f"rtt_{CMD_NAMES[cmd]}", "no replies", status="FAIL")
            continue
        loss = 100 * lost / count
        status = "FAIL" if loss > 5 else "WARN" if (loss or s["p95"] > warn_ms) else "PASS"
        rep.add("latency", f"rtt_{CMD_NAMES[cmd]}", s["median"], "ms", status,
                f"seq, reply {plen}B, loss {loss:.1f}%", s)
        rep.raw.extend(("latency", f"rtt_{CMD_NAMES[cmd]}", i, v) for i, v in enumerate(rtts))
        all_rtts += rtts
    if all_rtts:
        s = summarize(all_rtts)
        rep.add("latency", "rtt_all_sequential", s["median"], "ms",
                notes="link delay model for the sim (one-way ~ RTT/2)", stats=s)
        rep.add("latency", "jitter_ms", s["std"], "ms", notes="std of sequential RTT")
    seq["late"] = c.late_frames - late0
    seq["corrupted"] = c.parser.crc_errors - crc0
    seq["duration_s"] = time.perf_counter() - t_start
    if seq["late"]:
        rep.add("latency", "late_replies", seq["late"], "", "WARN",
                "replies that came after their request had timed out")
    return seq
 
 
def latency_load(c, rep, windows, duration, timeout, cmd=MSP_ATTITUDE):
    """Keep `window` requests in flight for `duration` seconds."""
    best_clean = 0.0
    for w in windows:
        c.drain()
        inflight = deque()
        rtts, sent, lost, errs = [], 0, 0, 0
        t0 = time.perf_counter()
        t_end = t0 + duration
        while True:
            now = time.perf_counter()
            if now < t_end:
                need = w - len(inflight)
                if need > 0:
                    c.send_many(cmd, need)
                    inflight.extend([time.perf_counter()] * need)
                    sent += need
            elif not inflight:
                break
            now = time.perf_counter()
            while inflight and now - inflight[0] > timeout:
                inflight.popleft()
                lost += 1
            for f in c.poll(0.005):
                if f.cmd != cmd or not inflight:
                    continue
                ts = inflight.popleft()
                if f.error:
                    errs += 1
                else:
                    rtts.append((time.perf_counter() - ts) * 1000)
        thr = len(rtts) / duration
        loss = 100 * (lost + errs) / sent if sent else 0
        if loss == 0:
            best_clean = max(best_clean, thr)
        status = ("FAIL" if (w == 1 and loss) else "WARN" if loss else "PASS")
        s = summarize(rtts)
        rep.add("latency", f"load_w{w}_throughput", thr, "Hz", status,
                f"{w} in flight, sent {sent}, ok {len(rtts)}, lost {lost}, err {errs}, loss {loss:.2f}%")
        if s:
            rep.add("latency", f"load_w{w}_rtt", s["median"], "ms", stats=s,
                    notes="RTT under load (includes queueing)")
            rep.raw.extend(("latency", f"load_w{w}_rtt", i, v) for i, v in enumerate(rtts))
    rep.add("latency", "max_clean_throughput", best_clean, "Hz",
            notes=f"best {CMD_NAMES[cmd]} replies/s with zero loss = MSP budget for the gateway")
 
 
def latency_burst(c, rep, n, timeout, cmd=MSP_ATTITUDE):
    c.drain()
    t0 = time.perf_counter()
    c.send_many(cmd, n)  # one big write
    got, last = 0, t0
    deadline = t0 + timeout + n * 0.01
    while got < n and time.perf_counter() < deadline:
        for f in c.poll(0.02):
            if f.cmd == cmd and not f.error:
                got += 1
                last = time.perf_counter()
    pct = 100 * got / n
    rep.add("latency", f"burst_{n}_received", pct, "%", "PASS" if got == n else "WARN",
            f"{got}/{n} replies to {n} requests sent at once (FC RX buffer overflow if <100%)")
    if got:
        rep.add("latency", f"burst_{n}_drain_ms", (last - t0) * 1000, "ms",
                notes=f"{got / (last - t0):.0f} replies/s")
 
 
def link_health(c, rep):
    p = c.parser
    rep.add("link", "crc_errors", p.crc_errors, "", "PASS" if p.crc_errors == 0 else "WARN")
    rep.add("link", "garbage_bytes", p.garbage_bytes, "B",
            "PASS" if p.garbage_bytes == 0 else "WARN",
            "non-MSP bytes on link (other client? CLI? wrong baud?)" if p.garbage_bytes else "")
    rep.add("link", "error_frames", c.error_frames, "", notes="FC '!' replies (unsupported cmds count here)")
    rep.add("link", "late_frames", c.late_frames, "", notes="replies that arrived after their request timed out")
    rep.add("link", "tx_bytes", c.tx_bytes, "B")
    rep.add("link", "rx_bytes", c.rx_bytes, "B")
 
 
# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# Capture (was msp_inventory.py capture)
# --------------------------------------------------------------------------- #
def run_capture(c, rep, state, count, timeout, out_dir, fc, link_name):
    """Ask every message in CAPTURE_MSGS `count` times and save each raw reply, in the
    format the tests read: a header line, then one JSON object per request."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{state}.jsonl"
    c.drain()
    with open(path, "w") as f:
        f.write(json.dumps({"setup": {"fc": fc, "link": link_name}, "state": state,
                            "host": link_name, "time": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")
        for name, cmd in CAPTURE_MSGS:
            got = errors = 0
            for i in range(count):
                frame, rtt = c.exchange(cmd, timeout=timeout)
                rec = {"name": name, "cmd": cmd, "i": i}
                if frame is None:
                    rec["error"] = "timeout"
                else:
                    # INAV replies with flag 0, so re-encoding gives the bytes that came in.
                    raw = encode_v2(cmd, frame.payload, b"!" if frame.error else b">")
                    rec.update({"ok": not frame.error, "rtt_ms": round(rtt * 1000, 2), "hex": raw.hex()})
                    got += not frame.error
                    errors += frame.error
                f.write(json.dumps(rec) + "\n")
            status = "PASS" if got == count else "WARN" if got or errors else "FAIL"
            note = f"{got}/{count} replies" + (f", {errors} error replies (not supported)" if errors else "")
            rep.add("capture", name, got, "", status, note)
    rep.add("capture", "file", str(path), notes="the tests replay it (tests/test_captures.py)")
    return path
 
 
def refresh_capture_copies(rep, path, ros_src=ROS_SRC):
    """fc_bridge's C++ tests keep copies of the captures (test_capture_copies.py checks
    they match): overwrite every copy with the same name, so both suites test the new data."""
    if not ros_src.is_dir():
        return []
    copies = sorted(p for p in ros_src.rglob(path.name) if p.resolve() != path.resolve())
    for dst in copies:
        shutil.copyfile(path, dst)
        rep.add("capture", "copy", str(dst.relative_to(ros_src.parents[1])), notes="updated")
    if not copies:
        rep.add("capture", "copy", "none", status="WARN",
                notes="new state: add it to test_capture_copies.py and copy it into "
                      "drone_fc_bridge/test/data/ if the C++ tests should use it")
    return copies
 
 
# --------------------------------------------------------------------------- #
# Logbook (was measure_wifi_rtt.py): project/logs/measurements/<name>/
# --------------------------------------------------------------------------- #
def pct_index(sorted_vals, p):
    """Same percentile as measure_wifi_rtt.py used, so history.csv stays comparable."""
    return sorted_vals[min(len(sorted_vals) - 1, int(len(sorted_vals) * p))]
 
 
def summary_values(rep, seq, link_name):
    """The numbers one line of history.csv keeps. The first block has exactly the keys
    the old wifi_rtt history used; the rest are the bench's own headline numbers."""
    rows = {(r["section"], r["item"]): r for r in rep.rows}
 
    def num(section, item, field="value"):
        r = rows.get((section, item))
        try:
            return round(float(r[field]), 4) if r and r[field] != "" else None
        except ValueError:
            return None
 
    fails = sum(r["status"] == "FAIL" for r in rep.rows)
    values = {"host": link_name, "result": "FAIL" if fails else "PASS", "fails": fails,
              "notes": sum(r["status"] == "WARN" for r in rep.rows)}
    if seq and seq["sent"]:
        rtts = sorted(seq["rtts"])
        dur = seq["duration_s"]
        values.update({
            "duration_s": round(dur, 1),
            "rate_hz": round((seq["sent"] - 1) / dur, 1) if dur > 0 else None,
            "sent": seq["sent"], "answered": len(rtts), "lost": seq["lost"],
            "lost_pct": round(seq["lost"] / seq["sent"] * 100, 1),
            "late": seq["late"], "corrupted": seq["corrupted"],
        })
        if rtts:
            values.update({
                "min_ms": round(rtts[0], 2), "median_ms": round(statistics.median(rtts), 2),
                "p90_ms": round(pct_index(rtts, 0.9), 2), "p99_ms": round(pct_index(rtts, 0.99), 2),
                "max_ms": round(rtts[-1], 2), "jitter_ms": round(statistics.pstdev(rtts), 2),
            })
    picks = {
        "max_clean_hz": ("latency", "max_clean_throughput"),
        "burst_received_pct": ("latency", f"burst_{BURST_FOR_SUMMARY[0]}_received"),
        "first_reply_s": ("info", "first_reply_after_s"),
        "acc_norm_error_g": ("derived", "acc_norm_error_g"),
        "tilt_deg": ("derived", "level_tilt_deg"),
        "yaw_drift_deg_min": ("derived", "yaw_drift_deg_per_min"),
        "baro_drift_cm_min": ("derived", "baro_alt_drift_cm_per_min"),
        "i2c_errors_delta": ("derived", "i2c_errors_delta"),
        "cell_v": ("derived", "cell_voltage_v"),
        "rf_valid_pct": ("mtf", "rangefinder_valid_pct"),
        "rf_noise_cm": ("mtf", "rangefinder_noise_cm"),
        "flow_quality_median": ("mtf", "flow_quality_median"),
    }
    for key, (section, item) in picks.items():
        v = num(section, item)
        if v is not None:
            values[key] = v
    for key, item in (("acc_z_noise_g", "acc_z_g"), ("baro_noise_cm", "baro_alt_cm")):
        v = num("sensors", item, "std")
        if v is not None:
            values[key] = v
    for key, item in (("cycle_time_us", "cycle_time_us"), ("cpu_load_pct", "cpu_load_pct")):
        v = num("sensors", item)
        if v is not None:
            values[key] = v
    return values
 
 
BURST_FOR_SUMMARY = [64]   # set from --burst in main()
 
 
def record_logbook(rep, values, note, name, link_name, extra_files=()):
    """New run folder via project/scripts/logbook.py, with the CSVs, values.json and a
    line in history.csv. Returns the folder."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    import logbook   # noqa: E402  (project/scripts/logbook.py, only needed here)
    run = logbook.new_run("measurements", name, {
        "note": note, "tool": "project/telemetry/msp_bench.py", "args": sys.argv[1:],
        "machine": platform.node(), "link": link_name, "bench_run_id": rep.run_id})
    rep.write(os.path.join(run, "bench.csv"))
    rep.write_raw(os.path.join(run, "samples.csv"))
    for f in extra_files:
        shutil.copy(f, run)
    logbook.write_json(os.path.join(run, "values.json"), values)
    logbook.append_history(run, {**values, "args": " ".join(sys.argv[1:]), "note": note})
    return run
 
 
# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
RTT_DEFAULT = "API_VERSION,ATTITUDE,RAW_IMU,INAV_ANALOG,INAV_STATUS"
 
 
def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Unified INAV/MSP bench test -> CSV",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    link = ap.add_mutually_exclusive_group()
    link.add_argument("--tcp", default=None, help="HOST[:PORT] (esp-link), default 192.168.4.1:23")
    link.add_argument("--serial", default=None, help="serial port, e.g. /dev/ttyUSB0, /dev/ttyACM0, COM5")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--settle", type=float, default=0.2,
                    help="seconds to wait after opening a serial port (raise if the bridge rebooted)")
    ap.add_argument("--connect-wait", type=float, default=15.0,
                    help="keep retrying the first MSP request this long (bridge boot / Wi-Fi join)")
    ap.add_argument("--force", action="store_true",
                    help="open the serial port even if another program (msp_gateway?) has it open")
    ap.add_argument("--duration", type=float, default=10.0, help="sensor sampling seconds")
    ap.add_argument("--expect", default="gyro,acc,rangefinder,opflow",
                    help="sensors that must be OK (rangefinder,opflow = the MTF-02P; "
                         "drop them to bench without it)")
    ap.add_argument("--timeout", type=float, default=0.5, help="per-request timeout (s)")
    ap.add_argument("--rtt-count", type=int, default=200, help="sequential requests per command")
    ap.add_argument("--rtt-commands", default=RTT_DEFAULT,
                    help="messages for the sequential round-trip test, by name: " + ", ".join(sorted(CMD_BY_NAME)))
    ap.add_argument("--rtt-interval", type=float, default=0.0,
                    help="pause between sequential requests, seconds (latency_test.py used 0.05)")
    ap.add_argument("--rtt-warn-ms", type=float, default=20.0, help="WARN if p95 RTT above this")
    ap.add_argument("--load-windows", default="1,2,4,8,16", help="in-flight requests for the load test")
    ap.add_argument("--load-duration", type=float, default=5.0, help="seconds per load window")
    ap.add_argument("--burst", type=int, default=64, help="requests in the burst test (0 = skip)")
    ap.add_argument("--acc-tol", type=float, default=0.05, help="|acc_norm - 1g| tolerance")
    ap.add_argument("--gyro-bias-tol", type=float, default=1.0, help="deg/s")
    ap.add_argument("--flow-quality-min", type=int, default=50)
    mtf = ap.add_argument_group("MTF-02P (rangefinder + optical flow)")
    mtf.add_argument("--sensor-uart", type=int, default=4,
                     help="UART number the MTF-02P is wired to (checked for MSP-only)")
    mtf.add_argument("--rf-noise-max", type=float, default=2.0,
                     help="note if rangefinder std at rest is above this (cm)")
    mtf.add_argument("--flow-motion", action="store_true",
                     help="guided motion test: hold still, then slide forward/back/right/left "
                          "over a textured surface at ~0.3-1 m")
    mtf.add_argument("--flow-phase", type=float, default=4.0, help="seconds per motion phase")
    mtf.add_argument("--flow-min-dps", type=float, default=5.0,
                     help="flow peak (deg/s) that counts as 'responded' in the motion test")
    ap.add_argument("--skip", default="",
                    help="comma list: sensors, latency (all of it), load (load + burst only), "
                         "config (MTF-02P settings/port check)")
    ap.add_argument("--allow-armed", action="store_true", help="run load tests even if armed")
    ap.add_argument("--quick", action="store_true", help="short run (~15 s)")
    ap.add_argument("--color", choices=["auto", "always", "never"], default="auto",
                    help="colored output (auto = only on a terminal; NO_COLOR env disables)")
    ap.add_argument("--brief", action="store_true",
                    help="hide the per-value sensor table, show checks and problems only")
    ap.add_argument("--out", default=None,
                    help="CSV path (default results/msp_bench_<host>_<time>.csv; with --logbook, the run folder)")
    ap.add_argument("--raw", default=None, help="also write every sample to this CSV")
    book = ap.add_argument_group("logbook (project/logs/measurements/)")
    book.add_argument("--logbook", metavar="NOTE", default=None,
                      help="keep the run: the conditions, e.g. \"Pi, USB bridge, bench, radio on\"")
    book.add_argument("--logbook-name", default="msp_bench",
                      help="measurement folder: msp_bench, or wifi_rtt to continue that history")
    cap = ap.add_argument_group("capture (recordings for the tests)")
    cap.add_argument("--capture", metavar="STATE", default=None,
                     help="record every message into inav/msp/captures/STATE.jsonl instead of the bench, "
                          "e.g. flat_still, tilted, radio_off, flow_moving")
    cap.add_argument("--capture-count", type=int, default=20, help="replies recorded per message")
    cap.add_argument("--capture-dir", default=str(CAPTURE_DIR), help="where the recording goes")
    cap.add_argument("--no-copy", action="store_true",
                     help="don't refresh the copies in project/ros2 (drone_fc_bridge/test/data/)")
    a = ap.parse_args(argv)
    if a.quick:
        a.duration, a.rtt_count, a.load_duration = 5.0, 50, 2.0
        a.load_windows = "1,8"
    a.expect = {s.strip() for s in a.expect.split(",") if s.strip()}
    a.skip = {s.strip() for s in a.skip.split(",") if s.strip()}
    unknown = a.skip - {"sensors", "latency", "load", "config"}
    if unknown:
        ap.error(f"--skip: unknown part(s) {', '.join(sorted(unknown))}")
    a.load_windows = [int(x) for x in str(a.load_windows).split(",") if x.strip()]
    try:
        a.rtt_commands = [CMD_BY_NAME[n.strip().upper()] for n in a.rtt_commands.split(",") if n.strip()]
    except KeyError as e:
        ap.error(f"--rtt-commands: unknown message {e}")
    if a.capture and not all(ch.isalnum() or ch in "_-" for ch in a.capture):
        ap.error("--capture: use letters, digits, _ and - only (it becomes a file name)")
    return a
 
 
def open_link(a):
    if a.serial:
        users = processes_using(a.serial)
        if users and not a.force:
            names = ", ".join(f"{n} (pid {p})" for p, n in users)
            raise OSError(f"{a.serial} is already open by {names}. Two programs on one port steal "
                          "each other's replies: stop it (e.g. msp_gateway) or pass --force")
        return SerialLink(a.serial, a.baud, a.settle)
    host, _, port = (a.tcp or "192.168.4.1:23").partition(":")
    return TcpLink(host, int(port or 23))
 
 
def info_value(rep, item):
    for r in rep.rows:
        if r["section"] == "info" and r["item"] == item:
            return r["value"]
    return ""
 
 
def main(argv=None):
    a = parse_args(argv)
    BURST_FOR_SUMMARY[0] = a.burst
    host = platform.node() or "unknown"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = a.out or (None if a.logbook else os.path.join("results", f"msp_bench_{host}_{stamp}.csv"))
 
    ui = UI(a.color)
    try:
        link = open_link(a)
    except (OSError, ValueError) as e:
        print(ui.red(f"Could not open link: {e}"), file=sys.stderr)
        return 2
 
    c = MspClient(link)
    rep = Report(uuid.uuid4().hex[:8], host, link.name)
    code = 0
    seq = None
    capture_path = None
    print(ui.bold("MSP bench") + ui.dim(f"  run {rep.run_id} on {host} via {link.name}"))
    ui.step("connecting to the flight controller")
    try:
        env_rows(rep, a)
        c.drain()
        if not test_info(c, rep, a.timeout, a.connect_wait):
            code = 2
            return code
        armed, flags = read_armed(c, a.timeout)
        rep.add("info", "armed", "unknown" if armed is None else ("YES" if armed else "no"),
                status="FAIL" if armed else "INFO",
                notes=("props off! " if armed else "")
                + (f"arming_flags=0x{flags:08x}" if flags is not None else ""))
        if flags is not None:
            names = arming_blockers(flags)
            bst, bnote = blocker_status(names)
            rep.add("info", "arming_blockers", " ".join(names) or "none", status=bst, notes=bnote)
 
        ui.step("reading sensor status")
        st0 = test_sensor_status(c, rep, a.expect, a.timeout)
        mtf_expected = bool({"rangefinder", "opflow"} & a.expect)
        if mtf_expected and "config" not in a.skip and not a.capture:
            ui.step("reading MTF-02P setup (settings, UART)")
            test_mtf_config(c, rep, a)
 
        if a.capture:
            ui.step(f"capturing {a.capture_count} replies of {len(CAPTURE_MSGS)} messages "
                    f"as '{a.capture}' - keep the drone in that state")
            fc = f"{info_value(rep, 'fc_variant')} {info_value(rep, 'fc_version')}".strip()
            capture_path = run_capture(c, rep, a.capture, a.capture_count, a.timeout,
                                       a.capture_dir, fc, link.name)
            if not a.no_copy:
                refresh_capture_copies(rep, capture_path)
        else:
            if "sensors" not in a.skip:
                ui.step(f"sampling sensors for {a.duration:.0f} s - keep the drone still")
                samples, _ = test_sensors(c, rep, a.duration, a.timeout, st0)
                derived_checks(rep, samples, a)
                if st0:
                    try:
                        st1 = read_sensor_status(c, a.timeout)
                        for k, v in st1.items():
                            if st0.get(k) != v:
                                rep.add("sensor_status", f"{k}_changed", f"{st0.get(k)}->{v}",
                                        status="FAIL", notes="changed during the run")
                    except (MspTimeout, MspError):
                        pass
            if a.flow_motion:
                test_flow_motion(c, rep, ui, a)
 
            if "latency" not in a.skip:
                ui.step(f"latency: {a.rtt_count} sequential requests x {len(a.rtt_commands)} messages")
                seq = latency_sequential(c, rep, a.rtt_count, a.timeout, a.rtt_warn_ms,
                                         a.rtt_commands, a.rtt_interval)
                if "load" in a.skip:
                    pass
                elif armed and not a.allow_armed:
                    rep.add("latency", "load_skipped", "armed", status="WARN",
                            notes="disarm or pass --allow-armed")
                else:
                    ui.step(f"latency: heavy load, windows {a.load_windows}, "
                            f"{a.load_duration:.0f} s each")
                    latency_load(c, rep, a.load_windows, a.load_duration, max(a.timeout, 1.0))
                    if a.burst:
                        latency_burst(c, rep, a.burst, max(a.timeout, 1.0))
        link_health(c, rep)
    except KeyboardInterrupt:
        rep.add("run", "interrupted", 1, status="WARN", notes="stopped with Ctrl-C, results so far")
    except ConnectionError as e:
        rep.add("run", "link_lost", str(e), status="FAIL")
    finally:
        link.close()
        if out:
            rep.write(out)
        if a.raw:
            rep.write_raw(a.raw)
        run_dir = None
        if a.logbook and code != 2:   # a run that never reached the FC records nothing
            extra = [capture_path] if capture_path else []
            run_dir = record_logbook(rep, summary_values(rep, seq, link.name), a.logbook,
                                     a.logbook_name, link.name, extra)
        rep.print_summary(ui, a.brief)
        saved = [f"CSV: {out}"] if out else []
        if a.raw:
            saved.append(f"raw: {a.raw}")
        if run_dir:
            saved.append(f"logbook: {os.path.relpath(run_dir)}")
        if saved:
            print(ui.dim("  " + "\n  ".join(saved)))
    if code == 0 and rep.worst == "FAIL":
        code = 1
    return code
 
 
if __name__ == "__main__":
    sys.exit(main())
 
