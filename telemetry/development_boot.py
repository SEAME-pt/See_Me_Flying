# main.py - MicroPython (ESP8266 / D1 Mini) transparent UART <-> TCP bridge for INAV MSP.
#
# Station mode: the ESP joins an existing Wi-Fi network (the same one as the
# ground computer) and listens on TCP port 5760; every byte is passed straight
# through to the flight controller's UART and back. The ESP does no MSP parsing.
#
# If it can't join that network within STA_TIMEOUT_S, it falls back to creating
# its own network (FALLBACK_SSID) at 192.168.4.1, exactly like before.
#
# Bytes from the flight controller that the socket can't take yet are kept in
# a buffer and sent on the next pass, instead of being dropped (dropped bytes
# corrupt MSP frames, which the ground script then reports as "no reply").

import errno
import machine
import network
import os
import socket
import time

# --- the Wi-Fi network to join (2.4 GHz, WPA/WPA2-Personal) ---
WIFI_SSID = "SEAME"
WIFI_PASSWORD = "SEAME@42"
HOSTNAME = "seemeflying"     # name shown in the router's device list

# Fixed address on that network, so the ground script always knows where to
# connect. Set to None to use DHCP instead (then reserve the address in the
# router, or read it from the boot message).
#STATIC_IP = None
STATIC_IP = ("10.20.87.200", "255.255.0.0", "10.20.0.1", "10.20.0.1")
#             (address,         netmask,         gateway,       DNS)

STA_TIMEOUT_S = 15           # how long to try joining before falling back

# --- fallback access point (used only if joining fails) ---
FALLBACK_SSID = "SeeMeFlying"
FALLBACK_PASSWORD = "123456789"   # WPA2, at least 8 characters

TCP_PORT = 5760
BAUD = 115200                # must match the MSP baud rate on the INAV port
STARTUP_DELAY_S = 3          # window to press Ctrl-C and stay in the REPL
MAX_PENDING = 2048           # cap on unsent FC -> computer bytes (oldest dropped)


def start_ap():
    network.WLAN(network.STA_IF).active(False)
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=FALLBACK_SSID, password=FALLBACK_PASSWORD,
              authmode=network.AUTH_WPA_WPA2_PSK)
    return ap


def start_sta():
    """Join WIFI_SSID. Return the IP address, or None if it didn't connect."""
    network.WLAN(network.AP_IF).active(False)   # don't also broadcast our own network
    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    try:                                         # MicroPython 1.20+
        network.hostname(HOSTNAME)
    except (AttributeError, ValueError, OSError):
        try:
            sta.config(dhcp_hostname=HOSTNAME)   # older firmware
        except (ValueError, OSError):
            pass

    try:                                         # keep the radio awake: modem sleep
        import esp                               # adds 100+ ms of latency per reply
        esp.sleep_type(esp.SLEEP_NONE)
    except (ImportError, AttributeError):
        pass

    if STATIC_IP:
        sta.ifconfig(STATIC_IP)
    if not sta.isconnected():
        sta.connect(WIFI_SSID, WIFI_PASSWORD)

    deadline = time.ticks_add(time.ticks_ms(), STA_TIMEOUT_S * 1000)
    while not sta.isconnected():
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            sta.active(False)
            return None
        time.sleep_ms(200)
    return sta.ifconfig()[0]


def start_network():
    ip = start_sta()
    if ip:
        print("Joined %s - bridge at %s:%d" % (WIFI_SSID, ip, TCP_PORT))
    else:
        start_ap()
        print("Could not join %s - started fallback network %s, bridge at 192.168.4.1:%d"
              % (WIFI_SSID, FALLBACK_SSID, TCP_PORT))


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
    pending = b""
    while True:
        if client is None:
            try:
                client, _ = srv.accept()
                client.setblocking(False)
                uart.read()              # drop stale bytes
                pending = b""
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


print("!DEVELOPMENT TOOL ONLY! MSP bridge starts in %d s - press Ctrl-C to stay in the REPL" % STARTUP_DELAY_S)
time.sleep(STARTUP_DELAY_S)
start_network()              # printed while the REPL is still on USB serial
time.sleep_ms(200)           # let the message finish before UART0 is taken over
try:
    bridge()
except Exception as e:
    os.dupterm(machine.UART(0, 115200), 1)   # give the REPL back on UART0
    print("bridge crashed:", e)
    time.sleep(2)
    machine.reset()
