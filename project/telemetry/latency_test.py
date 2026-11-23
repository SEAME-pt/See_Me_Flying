#!/usr/bin/env python3
"""Measure the round-trip delay to the flight controller.

On the Pi, the drone is reached through the D1 Mini bridge on USB, so there
are two ways to measure:

    Straight through the USB bridge (stop msp_gateway first):
        python3 latency_test.py --serial /dev/ttyUSB0
    Through msp_gateway (it keeps running; adds its own queueing):
        python3 latency_test.py --host 127.0.0.1 --port 5760

From a laptop on the drone's Wi-Fi, TCP straight to esp-link is the default:
    python3 latency_test.py                         (192.168.4.1, port 23)
    python3 latency_test.py --host <pi-address> --port 5760   (through the Pi's gateway)

Each sample sends one small MSP request (API/variant/version, in rotation) and
times how long the matching reply takes. Lost replies, late replies and the
latency spread are reported at the end. Ctrl-C stops early and still prints
the summary.

Every sample is also saved as a row in a CSV file (default:
latency_<target>_<date>-<time>.csv, or choose one with --csv), ready to import
into Google Sheets: File > Import > Upload.

Only the Python standard library is used, so nothing needs installing.
"""
import argparse
import csv
import datetime
import os
import select
import socket
import statistics
import struct
import sys
import termios
import time
import tty

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
    """MSP framing and timing, shared by the TCP and serial links."""

    name = "?"

    def __init__(self):
        self.buf = b""
        self.bad_crc = 0
        self.connect_ms = 0.0

    # --- provided by the subclasses ---
    def fileno(self):
        raise NotImplementedError

    def _read(self):
        raise NotImplementedError

    def send(self, data):
        raise NotImplementedError

    def _after_read(self):
        pass

    def close(self):
        pass

    # --- shared ---
    def _poll(self, timeout):
        """Wait up to `timeout` s for data; append it to the buffer. True if data came."""
        ready, _, _ = select.select([self.fileno()], [], [], max(0.0, timeout))
        if not ready:
            return False
        chunk = self._read()
        if not chunk:
            raise ConnectionError(f"{self.name} closed")
        self.buf += chunk
        self._after_read()
        return True

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

    def ping(self, cmd, timeout):
        """Return (round-trip ms or None if no reply, stale frames seen)."""
        stale = 0
        # Throw away anything left over from earlier requests first. Otherwise a
        # late reply to a previous request with the same command would be taken
        # as the answer to this one and show up as an impossible ~0 ms sample.
        while self._poll(0):
            pass
        for _frame in self.frames():
            stale += 1
        self.buf = b""
        self.send(build_frame(cmd))
        t0 = time.monotonic()
        while True:
            for rcmd, _ok in self.frames():
                if rcmd == cmd:
                    return (time.monotonic() - t0) * 1000, stale
                stale += 1                       # late reply to an earlier request
            left = timeout - (time.monotonic() - t0)
            if left <= 0:
                return None, stale
            self._poll(min(0.02, left))


class TcpLink(Link):
    def __init__(self, host, port, quickack=False):
        super().__init__()
        self.name = f"{host}:{port}"
        self.quickack = quickack
        t = time.monotonic()
        self.sock = socket.create_connection((host, port), timeout=5)
        self.connect_ms = (time.monotonic() - t) * 1000
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.setblocking(False)

    def fileno(self):
        return self.sock.fileno()

    def _read(self):
        return self.sock.recv(4096)

    def send(self, data):
        self.sock.setblocking(True)
        try:
            self.sock.sendall(data)
        finally:
            self.sock.setblocking(False)

    def _after_read(self):
        if self.quickack:                        # Linux resets this after every ACK
            try:
                self.sock.setsockopt(socket.IPPROTO_TCP,
                                     getattr(socket, "TCP_QUICKACK", 12), 1)
            except OSError:
                pass

    def close(self):
        self.sock.close()


class SerialLink(Link):
    """Raw serial port (the D1 Mini bridge on the Pi's USB), standard library only."""

    def __init__(self, device, baud):
        super().__init__()
        self.name = device
        speed = getattr(termios, f"B{baud}", None)
        if speed is None:
            raise OSError(f"unsupported baud rate {baud}")
        t = time.monotonic()
        self.fd = os.open(device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            tty.setraw(self.fd)
            attrs = termios.tcgetattr(self.fd)
            attrs[2] |= termios.CLOCAL | termios.CREAD   # ignore modem lines
            attrs[4] = attrs[5] = speed                  # input and output speed
            termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
            termios.tcflush(self.fd, termios.TCIOFLUSH)
        except Exception:
            os.close(self.fd)
            raise
        self.connect_ms = (time.monotonic() - t) * 1000

    def fileno(self):
        return self.fd

    def _read(self):
        return os.read(self.fd, 4096)

    def _poll(self, timeout):
        ready, _, _ = select.select([self.fd], [], [], max(0.0, timeout))
        if not ready:
            return False
        try:
            chunk = os.read(self.fd, 4096)
        except BlockingIOError:   # woken up with nothing to read: just "no data yet"
            return False
        if not chunk:
            raise ConnectionError(f"{self.name} disconnected")
        self.buf += chunk
        return True

    def send(self, data):
        view = memoryview(data)
        while view:
            try:
                n = os.write(self.fd, view)
            except BlockingIOError:
                select.select([], [self.fd], [], 0.1)
                continue
            view = view[n:]

    def close(self):
        os.close(self.fd)


def processes_using(path):
    """(pid, name) of other processes that have `path` open (needs same user or root)."""
    target = os.path.realpath(path)
    users = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) == os.getpid():
            continue
        fd_dir = f"/proc/{pid}/fd"
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            continue
        for fd in fds:
            try:
                if os.readlink(f"{fd_dir}/{fd}") == target:
                    with open(f"/proc/{pid}/comm") as f:
                        users.append((int(pid), f.read().strip()))
                    break
            except OSError:
                continue
    return users


def wait_until_answering(link, wait_s):
    """Opening the USB port can reset the D1 Mini, which then needs a few
    seconds to rejoin esp-link's Wi-Fi. Wait for the first reply so that
    doesn't count as lost samples. Returns seconds waited, or None."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < wait_s:
        ms, _ = link.ping(COMMANDS[0], 1.0)
        if ms is not None:
            return time.monotonic() - t0
    return None


def pct(sorted_vals, p):
    return sorted_vals[min(len(sorted_vals) - 1, int(len(sorted_vals) * p))]


def main():
    ap = argparse.ArgumentParser(
        description="MSP round-trip latency to the flight controller",
        epilog="On the Pi: --serial /dev/ttyUSB0 (gateway stopped) or --host 127.0.0.1 "
               "(through the gateway).")
    target = ap.add_argument_group("where the drone is")
    target.add_argument("--serial", metavar="DEV",
                        help="serial device of the USB bridge, e.g. /dev/ttyUSB0 or "
                             "/dev/serial/by-id/usb-1a86_...")
    target.add_argument("--baud", type=int, default=115200,
                        help="serial baud rate, same as the bridge sketch (default 115200)")
    target.add_argument("--host", default="192.168.4.1",
                        help="TCP address when --serial isn't used: 127.0.0.1 for the "
                             "gateway on this Pi, 192.168.4.1 for esp-link (default)")
    target.add_argument("--port", type=int, default=23,
                        help="TCP port: 23 for esp-link (default), 5760 for msp_gateway")
    ap.add_argument("-n", "--count", type=int, default=200, help="samples (default 200)")
    ap.add_argument("--interval", type=float, default=0.05,
                    help="pause between samples in seconds (default 0.05)")
    ap.add_argument("--timeout", type=float, default=2.0,
                    help="seconds before a reply counts as lost (default 2.0)")
    ap.add_argument("--quickack", action="store_true",
                    help="TCP only: ACK every reply at once (Linux TCP_QUICKACK) instead "
                         "of delaying ACKs; compare runs with and without it")
    ap.add_argument("--csv", metavar="FILE",
                    help="CSV file for the per-sample results (default: "
                         "latency_<target>_<date>-<time>.csv)")
    args = ap.parse_args()

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    label = (os.path.basename(os.path.realpath(args.serial)) if args.serial
             else args.host.replace(":", "-"))
    csv_path = args.csv or f"latency_{label}_{stamp}.csv"

    # ---- open the link ----
    if args.serial:
        users = processes_using(args.serial)
        if users:
            names = ", ".join(f"{name} (pid {pid})" for pid, name in users)
            print(f"{args.serial} is already open by {names}.\n"
                  "Two programs reading one serial port steal each other's replies.\n"
                  "Either stop it first, or measure through the gateway instead:\n"
                  "    python3 latency_test.py --host 127.0.0.1 --port 5760", file=sys.stderr)
            return 1
        if args.quickack:
            print("note: --quickack only applies to TCP; ignoring it", file=sys.stderr)
        try:
            link = SerialLink(args.serial, args.baud)
        except OSError as e:
            print(f"Could not open {args.serial} ({e}).", file=sys.stderr)
            if isinstance(e, PermissionError):
                print("Add yourself to the dialout group: sudo usermod -aG dialout $USER "
                      "(then log out and back in).", file=sys.stderr)
            print("ls /dev/serial/by-id/ lists the USB serial devices.", file=sys.stderr)
            return 1
        print(f"Opened {args.serial} at {args.baud} baud - waiting for the FC to answer "
              "(the bridge may reset when the port opens)...")
        waited = wait_until_answering(link, 15)
        if waited is None:
            print("No answer after 15 s. Check the bridge LED is solid on (bridging), that\n"
                  "--baud matches the sketch, and that the drone is powered.", file=sys.stderr)
            link.close()
            return 1
        print(f"FC answering after {waited:.1f} s - sending {args.count} requests...")
    else:
        try:
            link = TcpLink(args.host, args.port, args.quickack)
        except OSError as e:
            print(f"Could not connect to {args.host}:{args.port} ({e}).", file=sys.stderr)
            if args.host in ("127.0.0.1", "localhost"):
                print("Is msp_gateway running on this machine?", file=sys.stderr)
            return 1
        print(f"Connected to {args.host}:{args.port} in {link.connect_ms:.0f} ms "
              f"- sending {args.count} requests...")

    csv_file = open(csv_path, "w", newline="")
    writer = csv.writer(csv_file)
    writer.writerow(["sample", "time", "target", "msp_command", "result",
                     "rtt_ms", "late_frames", "corrupted_total"])

    # ---- measure ----
    rtts, lost, stale = [], 0, 0
    try:
        for i in range(args.count):
            cmd = COMMANDS[i % len(COMMANDS)]
            ms, late = link.ping(cmd, args.timeout)
            stale += late
            writer.writerow([
                i + 1,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                link.name, cmd,
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
    finally:
        csv_file.close()
        link.close()

    # ---- summary ----
    sent = len(rtts) + lost
    print(f"\n{link.name}: {sent} sent, {len(rtts)} answered, {lost} lost "
          f"({lost / max(sent, 1) * 100:.1f}%), {stale} late, {link.bad_crc} corrupted")
    if rtts:
        s = sorted(rtts)
        print(f"round trip ms: min {s[0]:.1f}  mean {statistics.mean(s):.1f}  "
              f"median {statistics.median(s):.1f}  p90 {pct(s, 0.9):.1f}  "
              f"p95 {pct(s, 0.95):.1f}  p99 {pct(s, 0.99):.1f}  max {s[-1]:.1f}  "
              f"jitter {statistics.pstdev(s):.1f}")
        if pct(s, 0.9) > 400:
            print("-> many replies take longer than the telemetry script's 0.4 s timeout")
    if link.bad_crc:
        print("-> corrupted frames: bytes are being lost or mangled on the way")
    print(f"per-sample results saved to {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
