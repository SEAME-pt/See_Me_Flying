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
                  I2C error delta, rangefinder valid %, flow quality, cell voltage
  5. latency      sequential RTT per command (link delay for the sim),
                  pipelined load at several in-flight windows (heavy MSP traffic),
                  burst test (buffer overflow / drop behaviour)
  6. link         CRC errors, garbage bytes, error frames, bytes in/out

Output: one tidy CSV (one row per measurement, same columns on every machine,
so CSVs from the Pi and laptops can simply be concatenated). Optional --raw CSV
with every individual sample, for fitting noise / delay models in Gazebo.

Exit code: 0 = no FAIL rows, 1 = at least one FAIL, 2 = could not talk to FC.

IMPORTANT: the link must be free. Stop the MSP gateway on the Pi first
(esp-link forwards serial data to every TCP client, so two clients mix replies).
Bench only, props off. Heavy-load tests are skipped automatically if armed.

Examples
  python3 msp_bench.py                                   # esp-link AP default
  python3 msp_bench.py --tcp 192.168.4.1:23
  python3 msp_bench.py --serial /dev/ttyUSB0 --baud 115200
  python3 msp_bench.py --serial COM5 --expect gyro,acc,opflow,rangefinder
  python3 msp_bench.py --quick --raw raw.csv
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import platform
import socket
import statistics
import struct
import sys
import time
import uuid
from collections import deque, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

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
MSP_RC = 105
MSP_ATTITUDE = 108
MSP_ALTITUDE = 109
MSP_SENSOR_STATUS = 151
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
}

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
        end = time.perf_counter() + max_time
        while time.perf_counter() < end and self.poll(quiet):
            pass

    def request(self, cmd: int, payload: bytes = b"", timeout: float = 0.5):
        """Send one request and wait for its reply. Returns (payload, rtt_s)."""
        t0 = time.perf_counter()
        self.send(cmd, payload)
        deadline = t0 + timeout
        while True:
            rem = deadline - time.perf_counter()
            if rem <= 0:
                raise MspTimeout(CMD_NAMES.get(cmd, cmd))
            for f in self.poll(min(rem, 0.05)):
                if f.cmd == cmd:
                    if f.error:
                        raise MspError(f"FC rejected {CMD_NAMES.get(cmd, cmd)}")
                    return f.payload, time.perf_counter() - t0


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


def dec_sonar(p):
    (cm,) = struct.unpack_from("<i", p)
    out = {"rangefinder_valid": 1.0 if cm > 0 else 0.0}  # 0 = not running, -1 = out of range
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
    if samples.get("rangefinder_valid"):
        pct = 100 * statistics.fmean(v for _, v in samples["rangefinder_valid"])
        expected = "rangefinder" in args.expect
        rep.add("derived", "rangefinder_valid_pct", pct, "%",
                ("PASS" if pct >= 95 else "WARN") if expected else "INFO",
                "share of readings in range" + ("" if expected else " (rangefinder not expected)"))
    if samples.get("flow_quality"):
        q = [v for _, v in samples["flow_quality"]]
        good = 100 * sum(v >= args.flow_quality_min for v in q) / len(q)
        rep.add("derived", "flow_quality_good_pct", good, "%",
                notes=f"quality >= {args.flow_quality_min}; depends on surface texture/light")
    if (m := med("cell_v")) is not None:
        if med("vbat_v") is not None and med("vbat_v") < 3.0:
            rep.add("derived", "cell_voltage_v", "no battery", "", "WARN", "USB-powered")
        else:
            rep.add("derived", "cell_voltage_v", m, "V", "PASS" if m >= 3.5 else "FAIL",
                    "" if m >= 3.5 else "battery low, charge before flight tests")
    if (m := med("cycle_time_us")) is not None:
        rep.add("derived", "fc_loop_hz", 1e6 / m if m else math.nan, "Hz")


def latency_sequential(c, rep, count, timeout, warn_ms):
    c.drain()
    all_rtts = []
    for cmd in (MSP_API_VERSION, MSP_ATTITUDE, MSP_RAW_IMU, MSP2_INAV_ANALOG, MSP2_INAV_STATUS):
        rtts, lost, plen = [], 0, 0
        for _ in range(count):
            try:
                p, rtt = c.request(cmd, timeout=timeout)
                plen = len(p)
                rtts.append(rtt * 1000)
            except MspTimeout:
                lost += 1
                c.drain(0.02, 0.2)
            except MspError:
                lost = -1
                break
        if lost < 0:
            rep.add("latency", f"rtt_{CMD_NAMES[cmd]}", "unsupported")
            continue
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
    rep.add("link", "tx_bytes", c.tx_bytes, "B")
    rep.add("link", "rx_bytes", c.rx_bytes, "B")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def parse_args():
    ap = argparse.ArgumentParser(description="Unified INAV/MSP bench test -> CSV",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    link = ap.add_mutually_exclusive_group()
    link.add_argument("--tcp", default=None, help="HOST[:PORT] (esp-link), default 192.168.4.1:23")
    link.add_argument("--serial", default=None, help="serial port, e.g. /dev/ttyUSB0, /dev/ttyACM0, COM5")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--settle", type=float, default=0.2,
                    help="seconds to wait after opening a serial port (raise if the bridge rebooted)")
    ap.add_argument("--connect-wait", type=float, default=8.0,
                    help="keep retrying the first MSP request this long (bridge boot / Wi-Fi join)")
    ap.add_argument("--duration", type=float, default=10.0, help="sensor sampling seconds")
    ap.add_argument("--expect", default="gyro,acc",
                    help="sensors that must be OK (add opflow,rangefinder once the MTF-02P is in)")
    ap.add_argument("--timeout", type=float, default=0.5, help="per-request timeout (s)")
    ap.add_argument("--rtt-count", type=int, default=200, help="sequential requests per command")
    ap.add_argument("--rtt-warn-ms", type=float, default=20.0, help="WARN if p95 RTT above this")
    ap.add_argument("--load-windows", default="1,2,4,8,16", help="in-flight requests for the load test")
    ap.add_argument("--load-duration", type=float, default=5.0, help="seconds per load window")
    ap.add_argument("--burst", type=int, default=64, help="requests in the burst test (0 = skip)")
    ap.add_argument("--acc-tol", type=float, default=0.05, help="|acc_norm - 1g| tolerance")
    ap.add_argument("--gyro-bias-tol", type=float, default=1.0, help="deg/s")
    ap.add_argument("--flow-quality-min", type=int, default=50)
    ap.add_argument("--skip", default="", help="comma list: sensors,latency")
    ap.add_argument("--allow-armed", action="store_true", help="run load tests even if armed")
    ap.add_argument("--quick", action="store_true", help="short run (~15 s)")
    ap.add_argument("--color", choices=["auto", "always", "never"], default="auto",
                    help="colored output (auto = only on a terminal; NO_COLOR env disables)")
    ap.add_argument("--brief", action="store_true",
                    help="hide the per-value sensor table, show checks and problems only")
    ap.add_argument("--out", default=None, help="CSV path (default results/msp_bench_<host>_<time>.csv)")
    ap.add_argument("--raw", default=None, help="also write every sample to this CSV")
    a = ap.parse_args()
    if a.quick:
        a.duration, a.rtt_count, a.load_duration = 5.0, 50, 2.0
        a.load_windows = "1,8"
    a.expect = {s.strip() for s in a.expect.split(",") if s.strip()}
    a.skip = {s.strip() for s in a.skip.split(",") if s.strip()}
    a.load_windows = [int(x) for x in str(a.load_windows).split(",") if x.strip()]
    return a


def open_link(a):
    if a.serial:
        return SerialLink(a.serial, a.baud, a.settle)
    host, _, port = (a.tcp or "192.168.4.1:23").partition(":")
    return TcpLink(host, int(port or 23))


def main():
    a = parse_args()
    host = platform.node() or "unknown"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = a.out or os.path.join("results", f"msp_bench_{host}_{stamp}.csv")

    try:
        link = open_link(a)
    except (OSError, ValueError) as e:
        print(f"Could not open link: {e}", file=sys.stderr)
        return 2

    ui = UI(a.color)
    c = MspClient(link)
    rep = Report(uuid.uuid4().hex[:8], host, link.name)
    code = 0
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

        if "latency" not in a.skip:
            if armed and not a.allow_armed:
                rep.add("latency", "skipped", "armed", status="WARN",
                        notes="disarm or pass --allow-armed")
            else:
                ui.step(f"latency: {a.rtt_count} sequential requests x 5 commands")
                latency_sequential(c, rep, a.rtt_count, a.timeout, a.rtt_warn_ms)
                ui.step(f"latency: heavy load, windows {a.load_windows}, "
                        f"{a.load_duration:.0f} s each")
                latency_load(c, rep, a.load_windows, a.load_duration, max(a.timeout, 1.0))
                if a.burst:
                    latency_burst(c, rep, a.burst, max(a.timeout, 1.0))
        link_health(c, rep)
    except KeyboardInterrupt:
        rep.add("run", "interrupted", 1, status="WARN")
    except ConnectionError as e:
        rep.add("run", "link_lost", str(e), status="FAIL")
    finally:
        link.close()
        rep.write(out)
        if a.raw:
            rep.write_raw(a.raw)
        rep.print_summary(ui, a.brief)
        print(ui.dim(f"  CSV: {out}" + (f"\n  raw: {a.raw}" if a.raw else "")))
    if code == 0 and rep.worst == "FAIL":
        code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
