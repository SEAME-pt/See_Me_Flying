#!/usr/bin/env python3
"""Measure the round-trip delay between this computer and the flight controller
through the ESP's TCP bridge.

Works in both ESP modes; only the address changes:
    ESP makes its own network (AP):   python3 latency_test.py
    ESP joined a network (station):   python3 latency_test.py --host 10.0.0.57

Each sample sends one small MSP request (API/variant/version, in rotation) and
times how long the matching reply takes. Lost replies, late replies and the
latency spread are reported at the end. Ctrl-C stops early and still prints
the summary.

Every sample is also saved as a row in a CSV file (default:
latency_<host>_<date>-<time>.csv, or choose one with --csv), ready to import
into Google Sheets: File > Import > Upload.
"""
import argparse
import csv
import datetime
import socket
import statistics
import struct
import sys
import time

COMMANDS = [1, 2, 3]   # MSP_API_VERSION, MSP_FC_VARIANT, MSP_FC_VERSION


def crc8_dvb_s2(data):
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0xD5) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def build_frame(cmd):
    body = struct.pack("<BHH", 0, cmd, 0)
    return b"$X<" + body + bytes([crc8_dvb_s2(body)])


class Link:
    def __init__(self, host, port, quickack=False):
        self.quickack = quickack
        t = time.monotonic()
        self.sock = socket.create_connection((host, port), timeout=5)
        self.connect_ms = (time.monotonic() - t) * 1000
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.settimeout(0.02)
        self.buf = b""
        self.bad_crc = 0

    def frames(self):
        """Yield (cmd, ok) for every complete frame now in the buffer."""
        while True:
            i = self.buf.find(b"$X")
            if i < 0:
                self.buf = self.buf[-1:]
                return
            self.buf = self.buf[i:]
            if len(self.buf) < 8:
                return
            direction = self.buf[2:3]
            _flag, cmd, size = struct.unpack_from("<BHH", self.buf, 3)
            if direction not in (b">", b"!") or size > 4096:
                self.buf = self.buf[2:]
                continue
            total = 9 + size
            if len(self.buf) < total:
                return
            body, crc = self.buf[3:8 + size], self.buf[8 + size]
            self.buf = self.buf[total:]
            if crc8_dvb_s2(body) == crc:
                yield cmd, direction == b">"
            else:
                self.bad_crc += 1

    def read_some(self):
        try:
            chunk = self.sock.recv(1024)
        except socket.timeout:
            return
        if not chunk:
            raise ConnectionError("bridge closed the connection")
        self.buf += chunk
        if self.quickack:                        # Linux resets this after every ACK
            try:
                self.sock.setsockopt(socket.IPPROTO_TCP,
                                     getattr(socket, "TCP_QUICKACK", 12), 1)
            except OSError:
                pass

    def ping(self, cmd, timeout):
        """Return round-trip ms, or None if no reply. Also counts stale frames."""
        stale = 0
        # Throw away anything left over from earlier requests first. Otherwise a
        # late reply to a previous request with the same command would be taken
        # as the answer to this one and show up as an impossible ~0 ms sample.
        self.sock.setblocking(False)
        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    raise ConnectionError("bridge closed the connection")
                self.buf += chunk
        except (BlockingIOError, socket.timeout):
            pass
        finally:
            self.sock.settimeout(0.02)
        for _frame in self.frames():
            stale += 1
        self.buf = b""
        self.sock.sendall(build_frame(cmd))
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            for rcmd, _ok in self.frames():
                if rcmd == cmd:
                    return (time.monotonic() - t0) * 1000, stale
                stale += 1                       # late reply to an earlier request
            self.read_some()
        return None, stale


def pct(sorted_vals, p):
    return sorted_vals[min(len(sorted_vals) - 1, int(len(sorted_vals) * p))]


def main():
    ap = argparse.ArgumentParser(description="MSP round-trip latency through the ESP bridge")
    ap.add_argument("--host", default="192.168.4.1",
                    help="ESP address: 192.168.4.1 in AP mode (default), or the IP "
                         "it got from the router in station mode")
    ap.add_argument("--port", type=int, default=5760)
    ap.add_argument("-n", "--count", type=int, default=200, help="samples (default 200)")
    ap.add_argument("--interval", type=float, default=0.05,
                    help="pause between samples in seconds (default 0.05)")
    ap.add_argument("--timeout", type=float, default=2.0,
                    help="seconds before a reply counts as lost (default 2.0)")
    ap.add_argument("--quickack", action="store_true",
                    help="ACK every reply at once (Linux TCP_QUICKACK) instead of "
                         "delaying ACKs; compare runs with and without it")
    ap.add_argument("--csv", metavar="FILE",
                    help="CSV file for the per-sample results (default: "
                         "latency_<host>_<date>-<time>.csv)")
    args = ap.parse_args()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    csv_path = args.csv or f"latency_{args.host.replace(':', '-')}_{stamp}.csv"

    try:
        link = Link(args.host, args.port, args.quickack)
    except OSError as e:
        print(f"Could not connect to {args.host}:{args.port} ({e}).", file=sys.stderr)
        if args.host == "192.168.4.1":
            print("If the ESP is in station mode, pass its IP with --host.", file=sys.stderr)
        return 1
    print(f"Connected to {args.host}:{args.port} in {link.connect_ms:.0f} ms "
          f"- sending {args.count} requests...")

    csv_file = open(csv_path, "w", newline="")
    writer = csv.writer(csv_file)
    writer.writerow(["sample", "time", "host", "msp_command", "result",
                     "rtt_ms", "late_frames", "corrupted_total"])

    rtts, lost, stale = [], 0, 0
    try:
        for i in range(args.count):
            cmd = COMMANDS[i % len(COMMANDS)]
            ms, late = link.ping(cmd, args.timeout)
            stale += late
            writer.writerow([
                i + 1,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                args.host, cmd,
                "lost" if ms is None else "ok",
                "" if ms is None else f"{ms:.2f}",
                late, link.bad_crc,
            ])
            csv_file.flush()                     # keep rows even if it stops early
            if ms is None:
                lost += 1
                print(f"  #{i + 1}: lost", flush=True)
            else:
                rtts.append(ms)
                if ms > 100:
                    print(f"  #{i + 1}: slow {ms:.0f} ms", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("stopped early")
    except OSError as e:
        print(f"connection lost: {e}", file=sys.stderr)

    csv_file.close()

    sent = len(rtts) + lost
    print(f"\n{args.host}: {sent} sent, {len(rtts)} answered, {lost} lost "
          f"({lost / max(sent, 1) * 100:.1f}%), {stale} late, {link.bad_crc} corrupted")
    if rtts:
        s = sorted(rtts)
        print(f"round trip ms: min {s[0]:.1f}  median {statistics.median(s):.1f}  "
              f"p90 {pct(s, 0.9):.1f}  p99 {pct(s, 0.99):.1f}  max {s[-1]:.1f}  "
              f"jitter {statistics.pstdev(s):.1f}")
        if pct(s, 0.9) > 400:
            print("-> many replies take longer than the telemetry script's 0.4 s timeout")
    if link.bad_crc:
        print("-> corrupted frames: bytes are being lost or mangled on the way")
    print(f"per-sample results saved to {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
