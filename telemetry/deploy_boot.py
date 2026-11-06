# main.py - MicroPython (ESP8266 / D1 Mini) transparent UART <-> TCP bridge for INAV MSP.
#
# The ESP creates its own Wi-Fi network. A computer joins it and opens a TCP
# connection to 192.168.4.1:5760; every byte is passed straight through to the
# flight controller's UART and back. The ESP does no MSP parsing itself.
#
# - Bytes from the flight controller that the socket can't take yet are kept
#   and sent on the next pass instead of being dropped.
# - A new connection always replaces the old one, so a stuck or forgotten
#   client can't lock the bridge.
# - If a stray '#' has put the FC's port into CLI mode, the bridge sends
#   'exit' (the FC leaves CLI and reboots) when it starts and on every connect.

import errno
import machine
import network
import os
import socket
import time

SSID = "SeeMeFlying"
PASSWORD = "123456789"   # WPA2, at least 8 characters
TCP_PORT = 5760
BAUD = 115200                # must match the MSP baud rate on the INAV port
STARTUP_DELAY_S = 3          # window to press Ctrl-C and stay in the REPL
MAX_PENDING = 2048           # cap on unsent FC -> computer bytes (oldest dropped)


def start_ap():
    network.WLAN(network.STA_IF).active(False)
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=SSID, password=PASSWORD, authmode=network.AUTH_WPA_WPA2_PSK)
    return ap


def close(sock):
    try:
        sock.close()
    except OSError:
        pass


def leave_cli(uart):
    """If the FC's port is stuck in CLI mode (a stray '#' got in), make it leave.
    INAV's CLI ignores an empty Enter, so instead of probing, this always sends
    'exit': the DELs first clear any half-typed noise in the CLI's line buffer.
    In MSP mode none of these bytes mean anything and they are ignored.
    Returns True if the FC answered "Leaving CLI mode" (it now reboots)."""
    uart.read()                          # drop stale bytes
    uart.write(b"\x7f" * 64 + b"exit\r\n")
    time.sleep_ms(300)
    reply = uart.read() or b""
    return b"Leaving CLI" in reply


def bridge():
    # Detach the REPL from UART0, otherwise MSP bytes from the flight controller
    # would be treated as typed input (0x03 = Ctrl-C, etc.).
    os.dupterm(None, 1)
    uart = machine.UART(0, BAUD, rxbuf=1024, timeout=0)
    leave_cli(uart)

    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", TCP_PORT))
    srv.listen(1)
    srv.setblocking(False)

    client = None
    pending = b""
    while True:
        # a new client always replaces the old one
        try:
            new, _ = srv.accept()
        except OSError:
            new = None
        if new is not None:
            if client is not None:
                close(client)
            client = new
            client.setblocking(False)
            leave_cli(uart)              # also drops stale bytes
            pending = b""
        if client is None:
            time.sleep_ms(50)
            continue

        busy = False

        # computer -> flight controller
        try:
            data = client.recv(256)
            if data == b"":              # computer disconnected
                close(client)
                client = None
                continue
            uart.write(data)
            busy = True
        except OSError as e:
            if e.args[0] != errno.EAGAIN:
                close(client)
                client = None
                continue

        # flight controller -> computer
        n = uart.any()
        if n:
            data = uart.read(n)
            if data:
                pending += data
                if len(pending) > MAX_PENDING:
                    pending = pending[-MAX_PENDING:]
        if pending:
            try:
                sent = client.send(pending)  # may send only part of it
                if sent:
                    pending = pending[sent:]
                    busy = True
            except OSError as e:
                if e.args[0] != errno.EAGAIN:  # EAGAIN: try again next pass
                    close(client)
                    client = None
                    continue

        if not busy:
            time.sleep_ms(2)


print("MSP bridge starts in %d s - press Ctrl-C to stay in the REPL" % STARTUP_DELAY_S)
time.sleep(STARTUP_DELAY_S)
start_ap()
try:
    bridge()
except Exception as e:
    os.dupterm(machine.UART(0, 115200), 1)   # give the REPL back on UART0
    print("bridge crashed:", e)
    time.sleep(2)
    machine.reset()
