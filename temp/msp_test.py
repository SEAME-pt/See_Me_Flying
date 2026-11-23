#!/usr/bin/env python3
"""
mock_fc.py - fake INAV flight controller speaking MSP v2 over TCP.
 
Lets you run msp_bench.py without the drone (e.g. in CI):
    python3 mock_fc.py --port 5760 &
    python3 msp_bench.py --tcp 127.0.0.1:5760 --quick
 
Simulates serial delay, noisy sensors and a small RX buffer that drops
requests when flooded, so the load/burst tests show realistic behaviour.
"""
import argparse
import random
import socket
import struct
import threading
import time
 
import msp_bench as m
 
 
def payload_for(cmd, t0):
    t = time.time() - t0
    g = random.gauss
    if cmd == m.MSP_API_VERSION:
        return bytes([0, 2, 5])
    if cmd == m.MSP_FC_VARIANT:
        return b"INAV"
    if cmd == m.MSP_FC_VERSION:
        return bytes([9, 1, 0])
    if cmd == m.MSP_BOARD_INFO:
        return b"MOCK" + b"\x00" * 4
    if cmd == m.MSP_BUILD_INFO:
        return b"Nov 23 2026" + b"12:00:00" + b"abcdef0"
    if cmd == m.MSP_NAME:
        return b"BROOK_MOCK"
    if cmd == m.MSP_SENSOR_STATUS:
        return bytes([1, 1, 1, 0, 1, 0, 2, 0, 1])  # healthy, gyro, acc, -, baro, -, rf unavailable, -, opflow
    if cmd == m.MSP_RAW_IMU:
        acc = [int(g(0, 3)), int(g(0, 3)), int(g(512, 4))]
        gyr = [int(g(0.3, 1)), int(g(-0.2, 1)), int(g(0, 1))]
        return struct.pack("<9h", *acc, *gyr, 0, 0, 0)
    if cmd == m.MSP_ATTITUDE:
        return struct.pack("<3h", int(g(5, 2)), int(g(-8, 2)), int(90 + 0.05 * t) % 360)
    if cmd == m.MSP_ALTITUDE:
        return struct.pack("<ihi", int(g(2 + 0.1 * t, 3)), int(g(0, 5)), int(g(2, 8)))
    if cmd == m.MSP_SONAR_ALTITUDE:
        return struct.pack("<i", -1)
    if cmd == m.MSP2_INAV_OPTICAL_FLOW:
        return struct.pack("<B4h", max(0, min(255, int(g(120, 30)))), int(g(0, 2)), int(g(0, 2)), 0, 0)
    if cmd == m.MSP2_INAV_ANALOG:
        return struct.pack("<BHhIIIIBH", (4 << 4), int(g(1620, 2)), int(g(50, 5)), 0, 120, 0, 0, 87, 0)
    if cmd == m.MSP_RC:
        return struct.pack("<8H", 1500, 1500, 1000, 1500, 1000, 1000, 1000, 1000)
    if cmd == m.MSP2_INAV_STATUS:
        return struct.pack("<4HBI", 500, 0, 0x23, 12, 0, 0) + b"\x00" * 8
    return None
 
 
def handle(conn, args):
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    parser = m.MspParser(accept=(b"<",))
    t0 = time.time()
    queue = []
    lock = threading.Lock()
    alive = True
 
    def responder():
        while alive:
            with lock:
                job = queue.pop(0) if queue else None
            if job is None:
                time.sleep(0.0005)
                continue
            time.sleep(max(0.0, random.gauss(args.delay_ms, args.jitter_ms)) / 1000)
            p = payload_for(job, t0)
            frame = m.encode_v2(job, p, b">") if p is not None else m.encode_v2(job, b"", b"!")
            try:
                conn.sendall(frame)
            except OSError:
                return
 
    th = threading.Thread(target=responder, daemon=True)
    th.start()
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            for f in parser.feed(data):
                with lock:
                    if len(queue) < args.rx_queue:  # small RX buffer -> drops under flood
                        queue.append(f.cmd)
    finally:
        alive = False
        conn.close()
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5760)
    ap.add_argument("--delay-ms", type=float, default=3.0)
    ap.add_argument("--jitter-ms", type=float, default=1.0)
    ap.add_argument("--rx-queue", type=int, default=12)
    args = ap.parse_args()
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", args.port))
    srv.listen()
    print(f"mock FC on 127.0.0.1:{args.port}")
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn, args), daemon=True).start()
 
 
if __name__ == "__main__":
    main()
 
