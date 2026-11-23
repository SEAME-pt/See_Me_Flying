---
title: ESP12 Setup and Telemetry
---
# ESP12 setup and INAV telemetry

The ESP12 (ESP8266) on the drone runs **esp-link**, a transparent bridge: it opens its own Wi-Fi access point and passes every byte between a TCP client on port 23 and the flight controller's UART1, with no MSP parsing on the ESP. Why esp-link and not MicroPython, and how fast the link is: [Wi-Fi latency tests](../../docs/Telemetry_test.md).

Everything in this folder talks **MSP** (the protocol INAV speaks) to the flight controller through that bridge.

## How to reach the drone

There are two setups. Pick one and stick to it, because the drone's ESP must only ever have **one client**: on Nov 18 a second one caused link dropouts that handed the sticks back to the radio ([motor music runs](../logs/measurements/motor_music/README.md)).

```
A. One laptop, direct:
   laptop ──drone Wi-Fi──► esp-link (192.168.4.1:23) ──UART──► FC

B. Several tools, through the Raspberry Pi (ground station):
   laptops ─┐                               ┌─ USB ─► D1 Mini bridge ──drone Wi-Fi──► esp-link ──► FC
   ROS     ─┼──lab Wi-Fi──► Pi: msp_gateway ┘
   scripts ─┘         (port 5760)
```

In setup B the Pi is the only client of the drone's ESP. Everything else connects to `msp_gateway` on the Pi, which queues the requests, logs every frame, and stops the motors if the client that started them disappears. The Pi's own Wi-Fi stays on the lab network and reaches the drone through a second D1 Mini on USB ([USB bridge](msp_dashboard/README.md#pi-without-ethernet-the-usb-bridge-firmwarepi_bridge)).

**Where to point each tool:**

| You are on | Setup | Address |
| --- | --- | --- |
| a laptop on the drone's Wi-Fi | A | `--host 192.168.4.1 --port 23` |
| any computer on the lab Wi-Fi | B | `--host <pi-address> --port 5760` (`hostname -I` on the Pi) |
| the Pi itself, gateway running | B | `--host 127.0.0.1 --port 5760` |
| the Pi itself, gateway stopped | B | `--serial /dev/ttyUSB0` (only the tools that support it) |

The scripts' default ports differ, so pass `--port` explicitly. `inav_telemetry.py` defaults to 5760 (the gateway), while `latency_test.py` and the dashboard default to 23 (esp-link).

## Which tool for what

| I want to… | Use |
| --- | --- |
| watch the drone live, or run a motor test (props off) | [`msp_dashboard`](msp_dashboard/README.md) |
| let several programs use the drone at once, and log every MSP frame | [`msp_gateway`](msp_dashboard/README.md#msp_gateway-one-owner-for-the-msp-link) |
| record decoded telemetry as JSON lines, or feed it to a script | [`inav_telemetry.py`](#inav_telemetrypy) |
| check how fast and reliable the link is | [`latency_test.py`](#latency_testpy) (`make wifi-rtt` to keep the result) |
| record new drone captures for the tests, or measure per-message rates | [`msp_inventory.py`](#msp_inventorypy) |
| identify the ELRS receiver | [`receiver_crsf_ping.py`](#receiver_crsf_pingpy) |
| test the MSP code without the drone | [`tests/`](#tests) and `msp_dashboard/tools/fake_fc.py` |

## Files in this folder

| File | What it is |
| --- | --- |
| `inav_telemetry.py` | Polls INAV and prints decoded values (readable or JSON lines). Also the Python reference decoders the tests check |
| `latency_test.py` | MSP round-trip times, over TCP or the Pi's USB serial bridge |
| `msp_inventory.py` | Captures raw MSP replies (`capture`) or measures their rates (`rate`) |
| `receiver_crsf_ping.py` | One-off tool: asks a CRSF/ELRS receiver for its name and version through INAV's serial passthrough |
| `tests/` | MSP framing, decoders and the drone recordings (pytest; `make test` and CI) |
| [`inav/`](inav/README.md) | INAV firmware choices, MSP captures (`msp/captures/`) and rate runs (`msp/rates/`) |
| [`msp_dashboard/`](msp_dashboard/README.md) | C++ terminal dashboard, `msp_gateway`, the Pi's USB bridge firmware and a fake FC for testing |

The scripts that keep results in `project/logs/` live in `project/scripts/`: `measure_wifi_rtt.py` (behind `make wifi-rtt`) wraps `latency_test.py`.

---

## ESP12

This step has to be done before wiring the ESP12 to the flight controller. It can be done with the ESP12 already soldered, but it's much more work.

### Prerequisites

#### 1 - Installing dependencies

Arch:

```bash
sudo pacman -S esptool
sudo usermod -aG uucp $USER    # serial port access; log out and in again
```

On Debian or Ubuntu the serial group is `dialout` instead of `uucp`.

#### 2 - Download and flash esp-link

Head to `https://github.com/jeelabs/esp-link` and download the stable release we use, 3.2.47.

Go to the folder, plug in your ESP12 and check that your PC recognizes it with `lsusb` and `ls /dev/tty*`: a `/dev/ttyUSB0` should be present.

**Now use esptool**:

```bash
esptool --port /dev/ttyUSB0 erase-flash
esptool --port /dev/ttyUSB0 --baud 460800 write-flash --flash-mode dio --flash-size 4MB \
  0x00000 boot_v1.*.bin \
  0x01000 user1.bin \
  0x3FC000 esp_init_data_default.bin \
  0x3FE000 blank.bin
```

##### Check that the flash worked

After flashing, unplug the ESP and plug it back in. After some time a network called `ESP_XXXXXXX` should appear: connect to it and go to `http://192.168.4.1`, where the settings can be changed.

##### Settings

- µC Console page: baud rate 115200, the same as INAV's MSP port on UART1.
- Pin Assignment page: RST, ISP and LED pins disabled.
- Wi-Fi: AP mode, with our SSID and password (see [How to connect to the drone's Wi-Fi](#how-to-connect-to-the-drones-wi-fi)).

That's all we changed. We also tested the ESP joined to the lab's Wi-Fi (station mode), but it was slower ([results](../../docs/Telemetry_test.md#testing-results)), so the drone's ESP stays in AP mode.

### How to connect to the drone's Wi-Fi

By default esp-link creates an open network. Ours was set with:

```bash
SSID: seemeflying
Password: 123456789
```

In setup B, only the Pi's USB bridge joins this network. Its SSID and password are set at the top of [`pi_bridge.ino`](msp_dashboard/firmware/pi_bridge/pi_bridge.ino).

---

## `inav_telemetry.py`

Polls INAV once per cycle and prints every decoded value. Messages the flight controller rejects are dropped from the poll list automatically. Press `q` (or Ctrl-C) to stop.

Turn on the drone using the battery pack, then from the repo root:

```bash
# setup A: laptop on the drone's Wi-Fi
python3 project/telemetry/inav_telemetry.py --port 23                     # readable output, 5 Hz
python3 project/telemetry/inav_telemetry.py --port 23 --info --rate 2     # JSON lines
python3 project/telemetry/inav_telemetry.py --port 23 --log flight.jsonl  # also save to a file

# setup B: through the Pi's gateway
python3 project/telemetry/inav_telemetry.py --host <pi-address> --port 5760 --log flight.jsonl

python3 project/telemetry/inav_telemetry.py --help                        # every flag
```

> [!IMPORTANT]
> The default port is 5760, which is `msp_gateway`'s. To talk to esp-link directly, pass `--port 23`.

| Flag | Default | Meaning |
| --- | --- | --- |
| `--host` | `192.168.4.1` | esp-link, or the Pi running the gateway |
| `--port` | `5760` | `23` for esp-link, `5760` for the gateway |
| `--rate` | `5` | polling cycles per second |
| `--timeout` | `0.4` | seconds to wait for each reply |
| `--log FILE` | | also write every cycle to FILE as JSON lines |
| `--read` / `--info` | `--read` | one value per line, or one JSON object per cycle |

**When to use it instead of the dashboard:** when you want the values as data, for example a `--log` file to analyse after a flight or JSON lines piped into another script. For watching the drone, the [dashboard](msp_dashboard/README.md) is easier to read and also shows link latency. Its decoders are also the reference the [tests](#tests) check against the drone recordings, so changes to an INAV message layout start here.

### Values it prints

The messages polled are the `LIVE` table near the middle of the script. Commented-out lines there are messages we don't use but kept the decoders for (see [the end of this section](#also-available-commented-out-in-live)).

#### Sent once at startup

| Name | Meaning | Unit / range |
| --- | --- | --- |
| `info.api_version.protocol` | MSP protocol version | number |
| `info.api_version.api` | MSP API version the firmware speaks | `major.minor` |
| `info.fc_variant` | Firmware identifier | `INAV` |
| `info.fc_version` | Firmware version | `major.minor.patch` |
| `info.board_info.board_id` | Short identifier of the flight controller board | 4 characters |
| `info.board_info.target` | Firmware target name | e.g. `ODDITYRCF7AIO` |
| `info.board_info.hardware_revision`, `.osd`, `.has_vcp` | Board revision, whether it has an OSD chip, whether USB is a virtual COM port | number, True / False |
| `info.craft_name` | Craft name set in INAV's Configuration tab | text, empty if not set |

#### Every cycle

| Name | Meaning | Unit / range |
| --- | --- | --- |
| `t` | Time this cycle was read, as a Unix timestamp | seconds |

#### Attitude (`attitude`)

| Name | Meaning | Unit / range |
| --- | --- | --- |
| `attitude.roll_deg` | Roll angle, tilt left or right | degrees, 0.1° resolution |
| `attitude.pitch_deg` | Pitch angle, tilt nose up or down | degrees, 0.1° resolution |
| `attitude.heading_deg` | Heading, the direction the nose points | degrees, 0–359 |

#### Altitude (`altitude`)

| Name | Meaning | Unit / range |
| --- | --- | --- |
| `altitude.alt_m` | Estimated altitude relative to where the flight controller zeroed it (usually at arming) | meters |
| `altitude.vario_ms` | Vertical speed, positive when climbing | m/s |

#### Position estimate (`local_pose`)

| Name | Meaning | Unit / range |
| --- | --- | --- |
| `local_pose.pos_m` | INAV's position estimate `[x, y, z]` | meters |
| `local_pose.vel_ms` | INAV's velocity estimate `[x, y, z]` | m/s |
| `local_pose.roll_deg`, `.pitch_deg`, `.yaw_deg` | Attitude, as in this message | degrees, 0.1° resolution |

#### Optical flow and rangefinder (`opflow`, `rangefinder`)

| Name | Meaning | Unit / range |
| --- | --- | --- |
| `opflow.quality` | Surface quality the flow sensor reports: low over plain or dark surfaces | 0–255 |
| `opflow.flow_rate_x_dps`, `_y_dps` | Image motion the sensor sees | °/s |
| `opflow.body_rate_x_dps`, `_y_dps` | Body rotation INAV subtracts from the flow | °/s |
| `rangefinder.valid` | Whether there is a distance reading | True / False |
| `rangefinder.distance_m` | Distance to the ground (MTF-02), only when valid | meters |
| `rangefinder.code` | Why it isn't valid: `0` no rangefinder running, `-1` out of range | number |

#### Raw sensors (`imu_raw`)

| Name | Meaning | Unit / range |
| --- | --- | --- |
| `imu_raw.acc[1]` … `[3]` | Accelerometer X, Y, Z | raw units, 512 = 1 g |
| `imu_raw.gyro[1]` … `[3]` | Gyroscope X, Y, Z (rotation rate) | °/s |
| `imu_raw.mag[1]` … `[3]` | Magnetometer (compass) X, Y, Z | raw units, 0 without a compass |

#### Radio and motors (`rc_channels`, `motors`, `link_stats`)

| Name | Meaning | Unit / range |
| --- | --- | --- |
| `rc_channels[n]` | Value of RC channel n as the flight controller sees it. Channels 1–4 are roll, pitch, throttle, yaw (INAV's default AETR order); the rest are AUX switches (ARM on ch5, PREARM on ch6) | µs, about 1000–2000, 1500 = center |
| `motors[n]` | Output sent to motor n | about 1000 (stopped) to 2000 (full); unused outputs read 0 |
| `link_stats.rssi_dbm` | Uplink signal strength at the receiver | dBm |
| `link_stats.link_quality_pct` | ELRS link quality: share of packets received | percent |
| `link_stats.snr_db` | Signal-to-noise ratio | dB |

`link_stats` needs the radio on and a CRSF receiver. It read all zeros in every recording so far, so check it shows real values before relying on it.

#### Status (`inav_status`)

| Name | Meaning | Unit / range |
| --- | --- | --- |
| `cycle_time_us` | Time the flight controller's main loop takes | microseconds |
| `i2c_errors` | I2C bus error counter. If it keeps rising, a sensor's wiring or the bus has a problem | count |
| `sensors[n]` | Sensors detected: `acc`, `baro`, `mag`, `gps`, `rangefinder`, `opflow`, `pitot`, `temp` | list |
| `hardware_ok` | `False` if INAV reports a sensor hardware failure | True / False |
| `cpu_load_pct` | Flight controller CPU load | percent |
| `armed`, `was_ever_armed` | Armed now, and armed at any time since power-up | True / False |
| `arming_blockers[n]` | What currently stops arming (e.g. `rc_link`, `not_level`, `arm_switch`, `no_prearm`) | list, empty if it can arm |
| `flight_modes[n]` | Modes currently active, named as in INAV's Modes tab (e.g. `ARM`, `ANGLE`, `MSP RC OVERRIDE`) | list |
| `pid_profile`, `battery_profile`, `mixer_profile` | Active profiles | 1-based, as in Configurator |

#### Battery (`inav_analog`)

| Name | Meaning | Unit / range |
| --- | --- | --- |
| `inav_analog.voltage_v` | Battery voltage | volts, 0.01 V resolution |
| `inav_analog.current_a` | Current draw | amps, 0.01 A resolution |
| `inav_analog.power_w` | Power draw | watts |
| `inav_analog.mah_drawn`, `.mwh_drawn` | Capacity and energy used since power-up | mAh, mWh |
| `inav_analog.remaining_capacity` | Remaining capacity, if battery capacity is set in INAV | INAV's unit (mAh or mWh), 0 if not set |
| `inav_analog.battery_pct` | Estimated remaining battery | percent |
| `inav_analog.cell_count` | Detected number of cells | count |
| `inav_analog.battery_state` | `ok`, `warning`, `critical` or `not_present` | text |
| `inav_analog.full_when_plugged_in`, `.uses_capacity_thresholds` | Battery detected as full at power-up; warnings based on capacity instead of voltage | True / False |
| `inav_analog.rssi_pct` | Radio signal strength as INAV measures it | percent, 0–100 |

#### Navigation (`nav_status`)

| Name | Meaning | Unit / range |
| --- | --- | --- |
| `nav_status.mode`, `.state` | Navigation mode and state, as INAV's numeric codes (0 = none). The dashboard shows them by name | number |
| `nav_status.wp_number`, `.wp_action` | Current waypoint and what it does | number |
| `nav_status.error` | Navigation error code (0 = none) | number |
| `nav_status.heading_hold_target_deg` | Heading that heading hold is keeping | degrees |

#### Also available (commented out in `LIVE`)

Uncomment a line in `LIVE` to poll it again. Their decoders are kept and tested.

| Key | Message | Why it's off |
| --- | --- | --- |
| `gps`, `gps_home` | `MSP_RAW_GPS`, `MSP_COMP_GPS` | no GPS on an indoor drone |
| `analog` | `MSP_ANALOG` | `inav_analog` has the same and more; this one's voltage tops out at 25.5 V |
| `status`, `status_ex` | `MSP_STATUS`, `MSP_STATUS_EX` | `inav_status` has the same and more; these carry only part of the modes and arming flags |
| `servos` | `MSP_SERVO` | no servos on a quad |

---

## `latency_test.py`

Measures how long the flight controller takes to answer. Each sample sends one small MSP request and times the reply. At the end it prints min, median, percentiles, jitter, lost and late replies, and every sample goes into a CSV (ready for Google Sheets: File > Import > Upload). Ctrl-C stops early and still prints the summary. It uses only the Python standard library, so nothing needs installing.

```bash
# setup A: laptop on the drone's Wi-Fi (esp-link, 192.168.4.1:23 by default)
python3 project/telemetry/latency_test.py
python3 project/telemetry/latency_test.py -n 1000 --interval 0.05

# setup B, on the Pi: straight through the USB bridge (stop msp_gateway first)
python3 project/telemetry/latency_test.py --serial /dev/ttyUSB0

# setup B, on the Pi: through the gateway (it keeps running)
python3 project/telemetry/latency_test.py --host 127.0.0.1 --port 5760
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--serial DEV` | | use the USB bridge instead of TCP (`/dev/ttyUSB0`, or the stable name in `/dev/serial/by-id/`) |
| `--baud` | `115200` | serial speed, the same as in `pi_bridge.ino` |
| `--host`, `--port` | `192.168.4.1`, `23` | TCP target when `--serial` isn't used |
| `-n`, `--count` | `200` | number of samples |
| `--interval` | `0.05` | pause between samples, in seconds |
| `--timeout` | `2.0` | seconds before a reply counts as lost |
| `--quickack` | off | TCP only: acknowledge every reply at once instead of delaying ACKs |
| `--csv FILE` | `latency_<target>_<date>-<time>.csv` | where the per-sample results go |

**Comparing the two Pi runs** tells you where time goes. The serial run measures the bare chain (USB → D1 Mini → Wi-Fi → esp-link → FC); the gateway run adds the gateway. If both are slow, the Wi-Fi hop is the problem. If only the gateway run is slow, look at the Pi side.

With `--serial`, it refuses to open the port while another program (usually the gateway) has it open, since both would steal each other's replies. It also waits up to 15 s for the first answer before counting, because opening the port can reset the D1 Mini.

### Keeping the result: `make wifi-rtt`

`latency_test.py` shows a number now. To **record** it in the project's logbook, run it through [`measure_wifi_rtt.py`](../scripts/measure_wifi_rtt.py), which needs a note describing the conditions:

```bash
make wifi-rtt NOTE="bench, AP mode, radio on" ARGS="-n 1000 --interval 0.05"   # laptop, setup A
make wifi-rtt NOTE="Pi, USB bridge, bench" ARGS="--serial /dev/ttyUSB0"        # on the Pi
```

Every flag in `ARGS` goes to `latency_test.py` unchanged. Each run gets a folder in `project/logs/measurements/wifi_rtt/` (`meta.json` with the note, the machine and serial or TCP; `samples.csv`; `values.json`), plus one line in `history.csv` to compare runs over time. Details: [logs README](../logs/README.md).

---

## `msp_inventory.py`

Two jobs, both talking to esp-link directly (setup A; the port is fixed at 23 in the script, so stop anything else using the drone first):

```bash
# Record N raw replies of every message into inav/msp/captures/<state>.jsonl
python3 project/telemetry/msp_inventory.py capture 192.168.4.1 flat_still

# Measure how fast each message can be polled alone, then the whole set together
python3 project/telemetry/msp_inventory.py rate 192.168.4.1 --seconds 10
python3 project/telemetry/msp_inventory.py rate 192.168.4.1 --gap 10   # 10 ms between requests
```

**`capture`** makes the recordings the [tests](#tests) replay (`flat_still`, `tilted`, `flow_moving`, `radio_off` so far). Put the drone in the state the name describes before running it. If you redo a capture, also copy it into `project/ros2/src/drone_fc_bridge/test/data/`: `test_capture_copies.py` fails until both copies match, and prints the `cp` command.

**`rate`** answers a different question from `latency_test.py`. `latency_test.py` asks "is the link healthy?" using tiny requests. `rate` asks "how fast can we poll the real telemetry messages?", per message and as the full set the dashboard and ROS use. Past runs are in `inav/msp/rates/`.

---

## `receiver_crsf_ping.py`

A one-off tool, kept for reference. It asks the CRSF/ELRS receiver soldered to the drone for its name and firmware version, which is how we identified the unmarked receiver ([ELRS guide](../../docs/ELRS_Guide.md), [hardware](../hardware/README.md)). It works over USB through INAV's serial passthrough, not over Wi-Fi, and only reads.

```bash
pip install pyserial --break-system-packages
# 1. In INAV's CLI:              serialpassthrough 1 420000
# 2. Close INAV Configurator completely (it keeps sending MSP)
python3 project/telemetry/receiver_crsf_ping.py /dev/ttyACM0
# 3. Unplug USB afterwards to leave passthrough mode
```

---

## `msp_dashboard/`

The C++ tools. Full instructions are in [their README](msp_dashboard/README.md):

- **`msp_dashboard`**: a live table of every value above, translated, with link latency, a command line for motor tests (props off) and a log of every command sent.
- **`msp_gateway`**: the single owner of the link in setup B. It queues requests from every client, logs every frame to a JSON-lines file, reconnects on its own and stops the motors if their client disappears.
- **`firmware/pi_bridge`**: the sketch for the D1 Mini on the Pi's USB.
- **`tools/fake_fc.py`**: a fake flight controller over TCP for trying everything without the drone (`--no-arm` for motor tests, `--delay` to simulate a slow link).

```bash
cd project/telemetry/msp_dashboard
cmake -S . -B build && cmake --build build -j
./build/msp_gateway --serial /dev/ttyUSB0                          # on the Pi
./build/msp_dashboard -H <pi-address> -p 5760 -t 0.6               # anywhere on the lab Wi-Fi
```

---

## Tests

Plain pytest, no drone needed. `make test` runs them along with the ROS tests, and CI runs them in the `telemetry-python` job (which also runs `flake8` with a 140-character line limit on this whole folder).

```bash
python3 -m pytest project/telemetry -v
```

| File | Checks |
| --- | --- |
| `test_msp_frame.py` | MSP v2 framing: checksum, request frames, the reply parser, error replies, timeouts |
| `test_decoders.py` | Every decoder with hand-made payloads: units, scaling, bit fields |
| `test_captures.py` | The decoders on the real drone recordings in `inav/msp/captures/` |
| `test_capture_copies.py` | The copies of those recordings in `project/ros2` match the originals |

More on what is and isn't covered: [CI tests](../../docs/CI_Tests.md).

### Three decoders, one truth

INAV's messages are decoded in three places: `inav_telemetry.py` (Python), `msp_dashboard/src/msp/messages.cpp` (dashboard and gateway), and `drone_fc_bridge/src/inav_decode.cpp` (ROS). The recordings in `inav/msp/captures/` are the shared reference. If INAV is upgraded or a decoder changes, fix it in all three and check them against the recordings: the Python tests and the ROS gtests do this automatically, while the dashboard was checked by hand against the same files on Nov 20.

# Tags

#guides
