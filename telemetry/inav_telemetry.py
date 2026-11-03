#!/usr/bin/env python3
"""Poll INAV telemetry over MSP (v2 framing) through the ESP's TCP bridge.

Prints one JSON object per polling cycle. Messages the flight controller
rejects (MSP error reply) are dropped from the poll list automatically.

    python3 inav_telemetry.py                      # print to terminal
    python3 inav_telemetry.py --log flight.jsonl   # also log to a file
    python3 inav_telemetry.py --info               # plain JSON lines instead

--read (the default) prints one value per line, names in bright blue and
values in white, with raw payloads shown as decimal byte values. --info prints
one JSON object per cycle. The --log file is always JSON.

Press q (or Ctrl-C) to stop.
"""
import argparse
import contextlib
import json
import select
import socket
import struct
import sys
import termios
import time
import tty


# ---------- MSP v2 framing ----------

def crc8_dvb_s2(data):
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0xD5) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def build_frame(cmd, payload=b""):
    body = struct.pack("<BHH", 0, cmd, len(payload)) + payload
    return b"$X<" + body + bytes([crc8_dvb_s2(body)])


class MSPClient:
    def __init__(self, host, port, timeout=0.4):
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.settimeout(0.05)
        self.timeout = timeout
        self.buf = b""

    def _next_frame(self):
        """Return (cmd, ok, payload) for the next valid frame in buf, or None."""
        while True:
            i = self.buf.find(b"$X")
            if i < 0:
                self.buf = self.buf[-1:]
                return None
            self.buf = self.buf[i:]
            if len(self.buf) < 8:
                return None
            direction = self.buf[2:3]
            _flag, cmd, size = struct.unpack_from("<BHH", self.buf, 3)
            if direction not in (b">", b"!") or size > 4096:
                self.buf = self.buf[2:]          # not a reply frame, skip
                continue
            total = 8 + size + 1
            if len(self.buf) < total:
                return None
            body, crc = self.buf[3:8 + size], self.buf[8 + size]
            self.buf = self.buf[total:]
            if crc8_dvb_s2(body) == crc:
                return cmd, direction == b">", body[5:]

    def request(self, cmd, payload=b""):
        """Send one request; return (ok, payload) or (None, None) on timeout."""
        self.sock.sendall(build_frame(cmd, payload))
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            frame = self._next_frame()
            if frame:
                rcmd, ok, data = frame
                if rcmd == cmd:
                    return ok, data
                continue
            try:
                chunk = self.sock.recv(1024)
            except socket.timeout:
                continue
            if not chunk:
                raise ConnectionError("bridge closed the connection")
            self.buf += chunk
        return None, None


# ---------- decoders (layouts from INAV's MSP; verify against your version) ----------

def u16_list(p):
    return list(struct.unpack("<%dH" % (len(p) // 2), p[: len(p) // 2 * 2]))


def d_api_version(p):
    return {"protocol": p[0], "api": "%d.%d" % (p[1], p[2])}


def d_text(p):
    return p.decode("ascii", errors="replace").strip("\x00")


def d_fc_version(p):
    return ".".join(str(b) for b in p[:3])


def d_attitude(p):
    roll, pitch, yaw = struct.unpack_from("<hhh", p)
    return {"roll_deg": roll / 10, "pitch_deg": pitch / 10, "heading_deg": yaw}


def d_altitude(p):
    alt, vario = struct.unpack_from("<ih", p)
    return {"alt_m": alt / 100, "vario_ms": vario / 100}


def d_raw_gps(p):
    fix, sats, lat, lon, alt, speed, course = struct.unpack_from("<BBiihHH", p)
    d = {"fix": fix, "sats": sats, "lat": lat / 1e7, "lon": lon / 1e7,
         "alt_m": alt, "speed_ms": speed / 100, "course_deg": course / 10}
    if len(p) >= 18:
        d["hdop"] = struct.unpack_from("<H", p, 16)[0] / 100
    return d


def d_comp_gps(p):
    dist, direction, _ = struct.unpack_from("<HhB", p)
    return {"home_dist_m": dist, "home_dir_deg": direction}


def d_analog(p):
    vbat, mah, rssi, amps = struct.unpack_from("<BHHh", p)
    return {"vbat_v": vbat / 10, "mah_drawn": mah,
            "rssi_pct": round(rssi / 1023 * 100, 1), "current_a": amps / 100}


def d_raw_imu(p):
    v = struct.unpack_from("<9h", p)
    return {"acc": v[0:3], "gyro": v[3:6], "mag": v[6:9]}


# ---------- status and battery decoders ----------

SENSOR_BITS = ["acc", "baro", "mag", "gps", "rangefinder", "opflow", "pitot", "temp"]

# INAV armingFlag_e (runtime_config.h). Bit numbers can change between INAV
# versions; unknown bits are shown as flag_bit_N.
ARMING_BITS = {
    2: "armed", 3: "was_ever_armed", 4: "simulator_hitl", 5: "simulator_sitl",
    6: "geozone", 7: "failsafe_system", 8: "not_level",
    9: "sensors_calibrating", 10: "system_overloaded", 11: "navigation_unsafe",
    12: "compass_not_calibrated", 13: "accelerometer_not_calibrated",
    14: "arm_switch", 15: "hardware_failure", 16: "boxfailsafe",
    18: "rc_link", 19: "throttle", 20: "cli", 21: "cms_menu", 22: "osd_menu",
    23: "rollpitch_not_centered", 24: "servo_autotrim", 25: "out_of_memory",
    26: "invalid_setting", 27: "pwm_output_error", 28: "no_prearm",
    29: "dshot_beeper", 30: "landing_detected",
}

BATTERY_STATES = ["ok", "warning", "critical", "not_present"]

MODE_NAMES = []   # filled at startup from MSP_BOXNAMES, in flag-bit order


def d_box_names(p):
    return [n for n in p.decode("ascii", errors="replace").split(";") if n]


def sensor_fields(bits):
    return {"sensors": [n for i, n in enumerate(SENSOR_BITS) if bits >> i & 1],
            "hardware_ok": not bits >> 15 & 1}


def arming_fields(flags):
    blockers = [ARMING_BITS.get(i, f"flag_bit_{i}")
                for i in range(32) if flags >> i & 1 and i not in (2, 3)]
    return {"armed": bool(flags >> 2 & 1), "was_ever_armed": bool(flags >> 3 & 1),
            "arming_blockers": blockers}


def flight_modes(flag_bytes):
    value = int.from_bytes(flag_bytes, "little")
    return [MODE_NAMES[i] if i < len(MODE_NAMES) else f"mode_bit_{i}"
            for i in range(len(flag_bytes) * 8) if value >> i & 1]


def d_status(p):                                  # MSP_STATUS (101)
    cycle, i2c, sens = struct.unpack_from("<HHH", p)
    return {"cycle_time_us": cycle, "i2c_errors": i2c, **sensor_fields(sens),
            "flight_modes": flight_modes(p[6:10]), "profile": p[10] + 1}


def d_status_ex(p):                               # MSP_STATUS_EX (150)
    d = d_status(p)
    load, arming = struct.unpack_from("<HH", p, 11)
    d["cpu_load_pct"] = load
    d.update(arming_fields(arming))               # only 16 bits in this message
    return d


def d_inav_status(p):                             # MSP2_INAV_STATUS (0x2000)
    cycle, i2c, sens, load, prof, arming = struct.unpack_from("<HHHHBI", p)
    rest = p[13:]
    nbox = len(rest) // 4 * 4                      # mode bitmask: whole 32-bit words
    d = {"cycle_time_us": cycle, "i2c_errors": i2c, **sensor_fields(sens),
         "cpu_load_pct": load, "pid_profile": (prof & 0x0F) + 1,
         "battery_profile": (prof >> 4) + 1, **arming_fields(arming),
         "flight_modes": flight_modes(rest[:nbox])}
    if len(rest) > nbox:
        d["mixer_profile"] = rest[nbox] + 1
    return d


def d_inav_analog(p):                             # MSP2_INAV_ANALOG (0x2002)
    flags, volt, amps, power, mah, mwh, remaining, pct, rssi = \
        struct.unpack_from("<BHhIIIIBH", p)
    return {"voltage_v": volt / 100, "current_a": amps / 100,
            "power_w": power / 100, "mah_drawn": mah, "mwh_drawn": mwh,
            "remaining_capacity": remaining, "battery_pct": pct,
            "cell_count": flags >> 4,
            "battery_state": BATTERY_STATES[flags >> 2 & 3],
            "full_when_plugged_in": bool(flags & 1),
            "uses_capacity_thresholds": bool(flags >> 1 & 1),
            "rssi_pct": round(rssi / 1023 * 100, 1)}


class Raw(bytes):
    """Undecoded payload: hex in JSON, decimal bytes in --read mode."""


def d_raw(p):
    return Raw(p)


# Polled once at start-up.
STATIC = {
    "api_version": (1, d_api_version),
    "fc_variant": (2, d_text),
    "fc_version": (3, d_fc_version),
    "board_info": (4, lambda p: d_text(p[:4])),
    "craft_name": (10, d_text),
    "mode_names": (116, d_box_names),             # used for flight_modes, not printed
}

# Polled every cycle. Raw-hex entries are there so nothing is missed; add a
# decoder when you need one of them.
LIVE = {
    "attitude": (108, d_attitude),
    "altitude": (109, d_altitude),
    "gps": (106, d_raw_gps),
    "gps_home": (107, d_comp_gps),
    "analog": (110, d_analog),
    "imu_raw": (102, d_raw_imu),
    "rc_channels": (105, u16_list),
    "motors": (104, u16_list),
    "servos": (103, u16_list),
    "status": (101, d_status),
    "status_ex": (150, d_status_ex),
    "inav_status": (0x2000, d_inav_status),
    "inav_analog": (0x2002, d_inav_analog),
    "inav_airspeed": (0x2009, d_raw),
}


def poll(msp, table):
    out, rejected = {}, []
    for name, (cmd, decode) in table.items():
        check_quit(0)
        ok, data = msp.request(cmd)
        if ok is None:
            out[name] = None                     # timeout
        elif not ok:
            rejected.append(name)                # FC doesn't support it
        else:
            try:
                out[name] = decode(data)
            except (struct.error, IndexError):
                out[name] = {"raw": Raw(data)}
    return out, rejected


# ---------- output ----------

BLUE = "\033[94m"
WHITE = "\033[97m"
RED = "\033[91m"
RESET = "\033[0m"


def error(msg):
    if sys.stderr.isatty():
        msg = f"{RED}{msg}{RESET}"
    print(msg, file=sys.stderr, flush=True)


# ---------- quitting ----------

class Quit(Exception):
    pass


@contextlib.contextmanager
def quit_key():
    """Let a single 'q' keypress be read without Enter (terminal cbreak mode)."""
    if not sys.stdin.isatty():
        yield
        return
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def check_quit(wait):
    """Wait up to `wait` seconds for a keypress; raise Quit if it was q."""
    if not sys.stdin.isatty():
        time.sleep(wait)
        return
    ready, _, _ = select.select([sys.stdin], [], [], wait)
    if ready and sys.stdin.read(1).lower() == "q":
        raise Quit


def to_json(record):
    return json.dumps(record, default=lambda o: o.hex())


def flatten(prefix, value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from flatten(f"{prefix}.{k}" if prefix else k, v)
    elif isinstance(value, (list, tuple)):
        if not value:
            yield prefix, "none"
        for i, v in enumerate(value, 1):
            yield from flatten(f"{prefix}[{i}]", v)
    else:
        yield prefix, value


def fmt_value(v):
    if v is None:
        return "no reply"
    if isinstance(v, Raw):
        return " ".join(str(b) for b in v)
    return str(v)


def print_readable(record):
    for name, value in flatten("", record):
        print(f"{BLUE}{name}{RESET}: {WHITE}{fmt_value(value)}{RESET}")
    print(flush=True)


def run(msp, args, show):
    info, rejected = poll(msp, STATIC)
    if not rejected and all(v is None for v in info.values()):
        error("Connected to the ESP bridge, but the flight controller is not answering.\n"
              "Check that it is powered, that TX/RX are crossed (FC TX -> ESP RX),\n"
              "and that MSP is enabled at 115200 on that UART in INAV's Ports tab.")
        return 1
    MODE_NAMES[:] = info.pop("mode_names", None) or []
    show({"info": info})

    log = open(args.log, "a") if args.log else None
    live = dict(LIVE)
    period = 1 / args.rate
    lost = False
    while True:
        start = time.monotonic()
        data, rejected = poll(msp, live)
        for name in rejected:
            del live[name]

        silent = not rejected and all(v is None for v in data.values())
        if silent and not lost:
            error("Flight controller stopped responding - waiting for it... (q to quit)")
        elif not silent and lost:
            error("Flight controller is responding again.")
        lost = silent

        if not silent:
            record = {"t": round(time.time(), 3), **data}
            show(record)
            if log:
                log.write(to_json(record) + "\n")
                log.flush()
        check_quit(max(0, period - (time.monotonic() - start)))


def main():
    ap = argparse.ArgumentParser(
        description="Poll INAV telemetry over MSP through the ESP's Wi-Fi bridge\n"
                    "and print it on this computer. Join the ESP's Wi-Fi network first.",
        epilog="""output modes:
  --read and --info cannot be used together. With neither, --read is used.

while running:
  q or Ctrl-C   stop the telemetry

examples:
  %(prog)s                          readable output, 5 cycles per second
  %(prog)s --info --rate 2          JSON output, 2 cycles per second
  %(prog)s --log flight.jsonl       also save every cycle to flight.jsonl
  %(prog)s --timeout 0.8            wait longer for slow replies""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--host", default="192.168.4.1",
                    help="IP address of the ESP bridge (default: %(default)s)")
    ap.add_argument("--port", type=int, default=5760,
                    help="TCP port of the ESP bridge, matching TCP_PORT in main.py "
                         "(default: %(default)s)")
    ap.add_argument("--rate", type=float, default=5.0,
                    help="polling cycles per second (default: %(default)s). Lower it "
                         "if many values show 'no reply'")
    ap.add_argument("--timeout", type=float, default=0.4,
                    help="seconds to wait for each reply before marking it "
                         "'no reply' (default: %(default)s)")
    ap.add_argument("--log", metavar="FILE",
                    help="save every cycle as a JSON line to FILE. Creates FILE if "
                         "it doesn't exist, otherwise appends to it. Without this "
                         "flag nothing is saved")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--read", action="store_true",
                      help="readable output: one value per line, names in blue, "
                           "values in white, raw payloads as decimal bytes (default)")
    mode.add_argument("--info", action="store_true",
                      help="plain output: one JSON object per cycle, raw payloads "
                           "as hex")
    args = ap.parse_args()
    show = (lambda r: print(to_json(r), flush=True)) if args.info else print_readable

    try:
        msp = MSPClient(args.host, args.port, timeout=args.timeout)
    except OSError as e:
        error(f"Could not connect to the ESP bridge at {args.host}:{args.port} ({e}).\n"
              "Check that this computer is on the ESP's Wi-Fi network and that the bridge is running.")
        return 1

    print("Connected - press q to quit.", file=sys.stderr, flush=True)
    with quit_key():
        try:
            return run(msp, args, show)
        except (Quit, KeyboardInterrupt):
            print("Telemetry stopped.", file=sys.stderr)
            return 0
        except OSError as e:          # includes ConnectionError
            error(f"Lost the connection to the ESP bridge ({e}).")
            return 1


if __name__ == "__main__":
    sys.exit(main())
