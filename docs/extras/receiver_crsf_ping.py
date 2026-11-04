#!/usr/bin/env python3
"""
Ask a CRSF/ELRS receiver for its device info (name, versions) through
INAV's serial passthrough.

Before running:
  1. In the INAV CLI:  serialpassthrough 1 420000
  2. CLOSE INAV Configurator completely (it keeps sending MSP data).
  3. pip install pyserial --break-system-packages

Run:   python3 crsf_ping.py            (defaults to /dev/ttyACM0)
       python3 crsf_ping.py /dev/ttyACM1
Exit passthrough afterwards by unplugging USB (power cycle).
Read-only: this only sends a "who are you?" ping; nothing is written.
"""
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"

ADDR_FC = 0xC8          # flight controller (sender)
ADDR_RX = 0xEC          # CRSF receiver
ADDR_BROADCAST = 0x00
TYPE_PING = 0x28
TYPE_DEVICE_INFO = 0x29


def crc8_dvb_s2(data):
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0xD5) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def ping_frame(dest):
    body = bytes([TYPE_PING, dest, ADDR_FC])
    return bytes([ADDR_FC, len(body) + 1]) + body + bytes([crc8_dvb_s2(body)])


def parse_frames(buf):
    """Yield (type, payload) for every valid CRSF frame found in buf."""
    i = 0
    while i + 2 < len(buf):
        length = buf[i + 1]
        if 2 <= length <= 62 and i + 2 + length <= len(buf):
            frame = buf[i + 2:i + 2 + length]
            if crc8_dvb_s2(frame[:-1]) == frame[-1]:
                yield frame[0], frame[1:-1]
                i += 2 + length
                continue
        i += 1


def show_device_info(payload):
    dest, orig = payload[0], payload[1]
    rest = payload[2:]
    name, _, tail = rest.partition(b"\x00")
    print(f"\nDEVICE INFO from 0x{orig:02X}:")
    print(f"  Name: {name.decode(errors='replace')}")
    if len(tail) >= 12:
        serial_no = tail[0:4].hex()
        hw = tail[4:8].hex()
        sw = tail[8:12]
        print(f"  Serial: {serial_no}   Hardware ID: {hw}")
        print(f"  Software version bytes: {sw.hex()}  (ELRS usually: 00 major minor patch -> {sw[1]}.{sw[2]}.{sw[3]})")


def main():
    with serial.Serial(PORT, 420000, timeout=0.1) as ser:
        ser.reset_input_buffer()
        raw = bytearray()
        print(f"Pinging receiver on {PORT} for 5 seconds...")
        end = time.time() + 5
        while time.time() < end:
            for dest in (ADDR_RX, ADDR_BROADCAST):
                ser.write(ping_frame(dest))
            time.sleep(0.25)
            raw += ser.read(512)

        found = False
        for ftype, payload in parse_frames(raw):
            if ftype == TYPE_DEVICE_INFO:
                show_device_info(payload)
                found = True
        if not found:
            print("No device-info reply.")
            if raw:
                print(f"Received {len(raw)} other bytes (first 64): {bytes(raw[:64]).hex(' ')}")
            else:
                print("Nothing at all came back: the receiver may only answer once it has a radio link.")


if __name__ == "__main__":
    main()
