---
title: MSP Dashboard and Gateway
---
# msp_dashboard + msp_gateway

Live INAV telemetry over MSP, shown as a terminal table. Labels are drawn once
and only the values that changed are rewritten, so the screen doesn't scroll
or flicker. It's a C++ port of `inav_telemetry.py`'s live view, with every
value translated (units, flag bits, mode names, nav states).

## Build

```bash
cmake -S . -B build
cmake --build build -j
```

Needs CMake ≥ 3.16 and a C++17 compiler (works with the GCC on Arch and on
Raspberry Pi OS / Ubuntu 24.04). No other dependencies.

## Run

```bash
./build/msp_dashboard                         # esp-link AP: 192.168.4.1:23
./build/msp_dashboard -H 192.168.4.1 -p 23
./build/msp_dashboard -s /dev/ttyUSB0 -b 115200   # through a USB serial bridge
./build/msp_dashboard -r 10 -t 0.3            # 10 cycles/s, 300 ms reply timeout
```

Keys: `q` quit, `r` redraw, `:` type a command, `space` stop all motors.
Resizing the terminal re-lays the table out.

The default port is **23**, esp-link's serial bridge port. `inav_telemetry.py`
defaults to 5760, which is `msp_gateway`'s port: pass it `--port 23` to talk to
esp-link directly. ESP setup and the other scripts: [telemetry README](../README.md).

## Sending commands (motor test)

```bash
./build/msp_dashboard --enable-motors --cmd-log commands.log
```

Press `:` to type a command and Enter to send it. Esc cancels the line.

| Command                         | Example        | Does                                |
| ------------------------------- | -------------- | ----------------------------------- |
| `motor <n> <value>`             | `motor 2 1150` | sets one motor                      |
| `motors <value>`                | `motors 10%`   | sets every motor                    |
| `stop`  (or **space** key)      |                | all motors back to 1000             |
| `help`                          |                | lists the commands                  |

Values are 1000-2000, or a percentage of that range (`10%` = 1100).
The "Motors" section shows what the FC actually outputs, so you can see the
command land. Every command and its result goes into the
**Commands sent** panel at the bottom: ack and latency, rejected by the FC,
no reply, or blocked locally and why. `--cmd-log FILE` also appends it all to a
file.

This uses `MSP_SET_MOTOR`, the same message as the Motors tab in INAV
Configurator, so it is a **bench test with the props off**. INAV only applies
it while disarmed. The safety rails:

- Motor commands do nothing unless started with `--enable-motors`.
- Commands are refused while the FC reports armed, or while its arming state
  isn't known.
- Values above `--motor-max` (default 1500) are refused.
- The motors stop by themselves after `--motor-timeout` seconds (default 15)
  without a new command.
- The motors are stopped on quit, on Ctrl-C, and when the terminal or SSH
  session closes.

INAV has no timeout of its own for this. If the **Wi-Fi link drops** while the
motors are spinning, nothing can reach the FC to stop them, and the dashboard
tells you so on exit: disconnect the battery. Keep `--motor-timeout` short.

Flying commands (sticks, modes) are a different path: `MSP_SET_RAW_RC`
through INAV's MSP RC override mode. `encode_set_raw_rc()` is ready for that;
the console just doesn't expose it yet. To add a command, add a branch in
`src/dashboard/console.cpp` that calls `Commander::send()`.

### Testing without the drone

```bash
python3 tools/fake_fc.py --port 5760 &
./build/msp_dashboard -H 127.0.0.1 -p 5760
```

The fake FC answers every polled message with moving values, flips between
armed and disarmed every 10 s, and rejects the link-stats message so the
"not supported" path is exercised too. It accepts `MSP_SET_MOTOR` and echoes
the values back through `MSP_MOTOR` while disarmed. Use `--no-arm` to keep it
disarmed for motor tests.

## msp_gateway: one owner for the MSP link

`msp_gateway` is the only program that talks to esp-link. Every other tool
(the dashboard, the ROS node, INAV Configurator, test scripts) connects to the
gateway instead. The gateway queues requests from all of them, sends them to
the FC a few at a time (see **Pacing** below), routes each reply back to
whoever asked, and logs every frame in both directions with the client it
came from.

```
  dashboard ─┐
  ROS node  ─┼──► msp_gateway (Pi) ──Wi-Fi──► esp-link ──UART──► FC
  laptop    ─┘        │
                      └─► msp_YYYYmmdd_HHMMSS.jsonl   (every frame, every client)
```

### Why it's needed

- **Collisions.** esp-link forwards every client's bytes straight to one
  UART. Two clients writing at the same moment can interleave their frames,
  and the FC then sees garbage. Two clients asking for the same message can
  also receive each other's replies. The gateway writes every frame itself,
  whole, and routes each reply to the client that asked.
- **Pacing.** Up to `--max-inflight` requests (default 4) are on the wire at
  once, and together they stay under `--max-inflight-bytes` (default 200),
  because INAV's UART receive buffer is 256 bytes with no overflow guard. On
  the bench (Nov 25-26, `msp_bench.py`), 1 request in flight gave about 45
  replies/s and 4-8 gave 85-97; 16 doubled the round trip for no gain, and a
  burst of 64 lost 29 of them. MSP replies carry no request id, so each reply
  goes to the oldest request in flight with the same command; INAV answers in
  order.
- **A complete log.** Connected directly to esp-link, a client can see the
  FC's replies to other clients but never the other clients' requests. Behind
  the gateway, every request and reply from every client passes through one
  place and gets logged with who sent it.
- **Safety that survives a crash.** If the client that started the motors
  disconnects for any reason (crash, kill -9, laptop lid closed, SSH drop),
  the gateway sends a motor stop itself.
- **Link recovery.** If the Wi-Fi to the ESP drops, the gateway reconnects
  every 2 s on its own. Clients stay connected to the gateway and simply see
  timeouts in the meantime.

### Running it

On the machine that is connected to the drone's esp-link AP (the Pi):

```bash
./build/msp_gateway                        # esp-link 192.168.4.1:23, clients on port 5760
./build/msp_gateway -v                     # also print every read request, not just writes
./build/msp_gateway --log flight3.jsonl    # choose the log file name
./build/msp_gateway --max-inflight 1       # back to one request at a time
```

Then point every client at the gateway instead of the ESP:

```bash
./build/msp_dashboard -H 127.0.0.1 -p 5760 -t 0.6        # on the Pi itself
./build/msp_dashboard -H <pi-address> -p 5760 -t 0.6     # from another PC
python3 inav_telemetry.py --host <pi-address> --port 5760
```

INAV Configurator can connect over TCP too: put `tcp://<pi-address>:5760` in
the port field.

Other PCs reach the gateway through the Pi's *other* network (Ethernet, or
SEAME Wi-Fi), because the Pi's link to the ESP is its own Wi-Fi network. The
gateway only sees what goes through it. Anyone who joins the ESP's AP and
connects to port 23 directly bypasses it, so keep that AP to the gateway
machine alone (give it a password if your esp-link version allows it).

With several clients sharing one FC, each reply can wait behind other
clients' requests, so give clients a slightly longer timeout (`-t 0.6` above).
The `queue_ms` field in the log shows how long requests waited.

### Pi without Ethernet: the USB bridge (`firmware/pi_bridge`)

If the Pi's only network is its built-in Wi-Fi, keep that on SEAME and reach
the drone through a spare D1 Mini on USB instead:

```
other PCs ──SEAME──► Pi: msp_gateway ──USB──► D1 Mini ──ESP's network──► esp-link ──► FC
```

1. Edit `WIFI_SSID` / `WIFI_PASS` at the top of `firmware/pi_bridge/pi_bridge.ino`
   to match esp-link's AP.
2. Flash it, using either of these:
   - **Arduino IDE:** add the board URL
     `https://arduino.esp8266.com/stable/package_esp8266com_index.json`, install
     "esp8266", pick the board "LOLIN(WEMOS) D1 R2 & mini", then Upload.
   - **arduino-cli:**
     ```bash
     arduino-cli core install esp8266:esp8266 \
       --additional-urls https://arduino.esp8266.com/stable/package_esp8266com_index.json
     arduino-cli compile --fqbn esp8266:esp8266:d1_mini firmware/pi_bridge
     arduino-cli upload  --fqbn esp8266:esp8266:d1_mini -p /dev/ttyUSB0 firmware/pi_bridge
     ```
   - **PlatformIO:** `cd firmware/pi_bridge && pio run -t upload`
3. Plug it into the Pi. The LED blinks fast while joining the Wi-Fi, blinks
   slowly while connecting to esp-link, and stays on once it's bridging.
4. Run the gateway on it:
   ```bash
   ./build/msp_gateway --serial /dev/serial/by-id/usb-1a86_* --baud 115200
   ```
   The `/dev/serial/by-id/` name stays the same even if other USB serial
   devices are plugged in (`1a86` is the D1 Mini's CH340 chip; check
   `ls /dev/serial/by-id/`). `/dev/ttyUSB0` works too.

Opening the port can reset the D1 Mini on some boards. If that happens it
rejoins within a few seconds, and the gateway just sees a few timeouts.

### What's on screen

By default the gateway prints connections, disconnections, link up/down,
errors, timeouts and every **write** (any command that changes something on
the FC: `MSP_SET_*`, reboot, EEPROM write, calibrations). With `-v` it prints
every request:

```
11:17:06.488 client #1 connected from 127.0.0.1:41102
11:17:08.485 #1 MSP_SET_MOTOR [7e047e047e047e04e803e803e803e803]  ok 0 ms
11:17:09.997 client #1 (127.0.0.1:41102) disconnected after 206 requests
11:17:09.997 client #1 left the motors spinning - stopping them
11:17:09.998 #0 MSP_SET_MOTOR [e803e803e803e803e803e803e803e803]  ok 0 ms
```

`#0` is the gateway itself. Payloads are hex, little-endian: `7e04` is
0x047e = 1150.

### The log file

One JSON object per line, everything included (reads too), even without `-v`:

```json
{"time":"2026-11-18T11:17:08.485","event":"transaction","client":1,
 "peer":"127.0.0.1:41102","v":2,"cmd":214,"name":"MSP_SET_MOTOR","write":true,
 "request":"7e047e04...","result":"ok","reply":"","queue_ms":0,"latency_ms":0}
```

| event          | meaning                                                         |
| -------------- | --------------------------------------------------------------- |
| `transaction`  | one request and its outcome: `ok`, `error` (FC rejected it), `timeout`, `upstream_down`, `link_lost` |
| `connect` / `disconnect` | a client came or went                                 |
| `upstream_up` / `upstream_down` | the link to the ESP came up or dropped           |
| `unsolicited`  | a frame from the FC nobody was waiting for (usually a late reply) |
| `dropped`      | a client sent more than 32 requests ahead; the extra was refused |

It's easy to analyse afterwards:

```bash
grep '"write":true' msp_20261118_111705.jsonl            # every command sent to the drone
jq -r 'select(.result=="timeout") | .name' *.jsonl | sort | uniq -c
```

## Reading the table

The **Latency** row is the round-trip time of each request: from sending it to
receiving the FC's reply, averaged over the last few polling cycles, plus the
fastest and slowest reply in the last cycle. It is measured from timestamps
the poller takes anyway, so it adds no MSP traffic. Through the gateway it
includes any time spent waiting behind other clients' requests. "Full cycle"
is how long one pass over every message takes. If it gets close to the
polling period (200 ms at the default 5 Hz), the dashboard can't keep up with
`--rate`. Green is under 50 ms, yellow up to 150 ms, red above that or
whenever a request timed out. `tools/fake_fc.py --delay 12` simulates a slower
link.


| Shown                 | Meaning                                                          |
| --------------------- | ---------------------------------------------------------------- |
| `…`                   | not polled yet                                                   |
| `no reply`            | polled, never answered (raise `--timeout` or lower `--rate`)     |
| dimmed value          | last known value; the latest request timed out                   |
| `not supported by FC` | the FC answered with an MSP error; it's no longer polled         |
| `unexpected payload`  | reply shorter than the decoder expects: check the layout         |

## Code layout

```
include/msp/   src/msp/        msp_core library: no terminal code
  transport    TCP (esp-link) and serial
  client       MSP v2 framing, CRC, request/reply
  messages     decoders, translation tables, encode_set_raw_rc()
  telemetry    Telemetry: latest value + freshness for every message
  poller       polls the FC and fills Telemetry
  commander    sends commands + keeps the command log; MotorTest safety rails
  frame        MSP v1 + v2 parsing in both directions, command names

src/dashboard/                 the terminal front end
  fields.cpp   every row: label + how its value is translated  <- edit here
  dashboard    layout and in-place updates
  console.cpp  typed commands (motor, motors, stop, help)       <- and here
  command_panel  the "Commands sent" log and the input line

src/gateway/main.cpp           msp_gateway
firmware/pi_bridge/            D1 Mini sketch: USB serial <-> Wi-Fi <-> esp-link
  terminal     alternate screen, key input, restore on exit
  main.cpp     options and the main loop
```

To add a value: decode it in `messages.cpp`, add a `Slot` to `Telemetry`,
add an `entry(...)` line in `poller.cpp`, and add a row in `fields.cpp`.

`msp_core` is kept separate so the ROS 2 bridge can link it directly:
a node owns a `Poller`, publishes from `Telemetry`, and sends commands with
`Client::send()` (for example `encode_set_raw_rc()` for `MSP_SET_RAW_RC`).

## Things to verify against your INAV version

These are the same assumptions as `inav_telemetry.py`:

- Message layouts and arming-flag bit numbers follow INAV 9.1.0's
  `fc_msp.c` / `runtime_config.h`.
- RC channel names assume the default AETR channel map.
- Accelerometer is scaled as 1 g = 512, and gyro is in °/s.
- `MSP_NAV_STATUS` mode/state/error names follow INAV's `navigation.h`.
- `MSP_SET_MOTOR` is 8 × uint16 (motors 1-8), applied only while disarmed.

# Tags

#tools
