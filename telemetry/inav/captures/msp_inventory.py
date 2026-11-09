#!/usr/bin/env python3
"""Capture raw MSPv2 replies from INAV, or measure their rates, over the esp-link TCP bridge.

  capture <esp-ip> <state>   save N raw replies per message to inav/msp/captures/<state>.jsonl
  rate    <esp-ip>           measure each message alone, then the whole set together
"""
import json, pathlib, socket, statistics, struct, sys, time

PORT = 23          # esp-link serial bridge
TIMEOUT = 0.5      # seconds to wait for one reply
N = 20             # replies captured per message
SECONDS = 30       # duration of each rate run
SETUP = {"fc": "INAV 9.1.0", "bridge": "esp-link 3.2.47"}

# Read-only messages from the final candidate list (inav/msp/candidates.md, #124),
# checked against the INAV 9.1.0 source.
STARTUP = {
    "MSP_API_VERSION": 1, "MSP_FC_VARIANT": 2, "MSP_FC_VERSION": 3,
    "MSP_BOARD_INFO": 4, "MSP_NAME": 10, "MSP_BOXNAMES": 116,
}
LIVE_MSGS = {
    "MSP2_INAV_STATUS": 0x2000, "MSP_ATTITUDE": 108, "MSP_ALTITUDE": 109,
    "MSP_RAW_IMU": 102, "MSP2_INAV_ANALOG": 0x2002, "MSP2_INAV_OPTICAL_FLOW": 0x2001,
    "MSP_RC": 105, "MSP_SONAR_ALTITUDE": 58, "MSP2_INAV_FULL_LOCAL_POSE": 0x2220,
}
OPTIONAL = {"MSP_NAV_STATUS": 121, "MSP2_INAV_GET_LINK_STATS": 0x2103, "MSP_MOTOR": 104}
MSGS = {**STARTUP, **LIVE_MSGS, **OPTIONAL}
LIVE = list(LIVE_MSGS) + list(OPTIONAL)


def crc8(data):
    c = 0
    for b in data:
        c ^= b
        for _ in range(8):
            c = ((c << 1) ^ 0xD5) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    return c


def request(cmd):
    body = struct.pack("<BHH", 0, cmd, 0)
    return b"$X<" + body + bytes([crc8(body)])


def read_exact(s, n):
    buf = b""
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("link closed")
        buf += chunk
    return buf


def read_frame(s, deadline=None):
    """Return (cmd, raw_bytes, ok) for the next MSPv2 frame on the link."""
    while True:
        if deadline and time.monotonic() > deadline:
            raise TimeoutError                    # bytes kept coming, but no frame
        if read_exact(s, 1) == b"$" and read_exact(s, 1) == b"X":
            break
    direction = read_exact(s, 1)
    hdr = read_exact(s, 5)
    _, cmd, size = struct.unpack("<BHH", hdr)
    payload = read_exact(s, size)
    crc = read_exact(s, 1)[0]
    raw = b"$X" + direction + hdr + payload + bytes([crc])
    return cmd, raw, direction == b">" and crc == crc8(hdr + payload)


def ask(s, cmd):
    """Send one request; return (raw, ok, rtt_ms) or None if no reply within TIMEOUT.
    Skips late replies to older requests. TIMEOUT is for the whole reply, so a link
    that keeps sending other bytes can't hold the script forever."""
    t0 = time.monotonic()
    deadline = t0 + TIMEOUT
    s.sendall(request(cmd))
    try:
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return None
            s.settimeout(left)
            rcmd, raw, ok = read_frame(s, deadline)
            if rcmd == cmd:
                return raw, ok, (time.monotonic() - t0) * 1000
    except TimeoutError:
        return None
    finally:
        s.settimeout(TIMEOUT)


def check_fc(s):
    """Stop early if the FC behind the ESP doesn't answer, instead of waiting through every timeout."""
    for _ in range(5):
        if ask(s, 1):                             # MSP_API_VERSION
            return
    sys.exit("Connected to the ESP bridge, but the flight controller is not answering.\n"
             "Check that the battery is plugged in, that no other program is using the link,\n"
             "and that esp-link's baud matches UART1 in INAV's Ports tab. Then try again.")


def connect(host):
    try:
        s = socket.create_connection((host, PORT), timeout=5)   # Wi-Fi connect can be slow
    except OSError as e:
        sys.exit(f"Could not connect to the ESP bridge at {host}:{PORT} ({e}).\n"
                 "Check that this computer is on the drone's Wi-Fi, that the battery is\n"
                 "plugged in, and that no other program (inav_telemetry.py, Configurator)\n"
                 "is connected to the bridge.")
    s.settimeout(TIMEOUT)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return s


def capture(host, state):
    out = pathlib.Path("inav/msp/captures")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{state}.jsonl"
    s = connect(host)
    check_fc(s)
    print("capturing to", path.resolve())
    with open(path, "w") as f:
        f.write(json.dumps({"setup": SETUP, "state": state, "host": host,
                            "time": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")
        for name, cmd in MSGS.items():
            got = 0
            for i in range(N):
                r = ask(s, cmd)
                rec = {"name": name, "cmd": cmd, "i": i}
                rec.update({"error": "timeout"} if r is None else
                           {"ok": r[1], "rtt_ms": round(r[2], 2), "hex": r[0].hex()})
                f.write(json.dumps(rec) + "\n")
                got += r is not None
            print(f"  {name:26} {got}/{N} replies")
    print("saved", path.resolve())


def run(s, names):
    """Poll names in a loop for SECONDS; return per-name (good, lost, rtts) and loop count."""
    stats = {n: [0, 0, []] for n in names}
    loops, end = 0, time.monotonic() + SECONDS
    while time.monotonic() < end:
        for n in names:
            r = ask(s, MSGS[n])
            if r and r[1]:
                stats[n][0] += 1
                stats[n][2].append(r[2])
            else:
                stats[n][1] += 1
        loops += 1
    return stats, loops


def report(label, stats):
    for n, (good, lost, rtts) in stats.items():
        p95 = statistics.quantiles(rtts, n=20)[18] if len(rtts) >= 20 else float("nan")
        med = statistics.median(rtts) if rtts else float("nan")
        loss = 100 * lost / max(good + lost, 1)
        print(f"{label:6} {n:24} {good / SECONDS:7.1f} Hz  median {med:6.1f} ms  p95 {p95:6.1f} ms  loss {loss:5.1f} %")


def rate(host):
    s = connect(host)
    check_fc(s)
    for n in LIVE:
        report("alone", run(s, [n])[0])
    stats, loops = run(s, list(LIVE_MSGS))       # the set ROS-6 polls; optional ones excluded
    report("set", stats)
    print(f"full set: {loops / SECONDS:.1f} cycles/s")


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "capture":
        capture(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 3 and sys.argv[1] == "rate":
        rate(sys.argv[2])
    else:
        sys.exit(__doc__)