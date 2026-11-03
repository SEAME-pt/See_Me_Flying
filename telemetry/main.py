# main.py - MicroPython (ESP8266 / D1 Mini) transparent UART <-> TCP bridge for INAV MSP.
#
# The ESP creates its own Wi-Fi network. A computer joins it and opens a TCP
# connection to 192.168.4.1:5760; every byte is passed straight through to the
# flight controller's UART and back. The ESP does no MSP parsing itself.

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


def bridge():
    # Detach the REPL from UART0, otherwise MSP bytes from the flight controller
    # would be treated as typed input (0x03 = Ctrl-C, etc.).
    os.dupterm(None, 1)
    uart = machine.UART(0, BAUD, rxbuf=1024, timeout=0)

    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", TCP_PORT))
    srv.listen(1)
    srv.setblocking(False)

    client = None
    while True:
        if client is None:
            try:
                client, _ = srv.accept()
                client.setblocking(False)
                uart.read()              # drop stale bytes
            except OSError:
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
                try:
                    client.send(data)
                    busy = True
                except OSError as e:
                    if e.args[0] != errno.EAGAIN:   # EAGAIN: drop this chunk
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
