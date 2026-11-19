---
title: ESP12 Setup and Telemetry
---
# ESP12 setup and INAV telemetry

The ESP12 (ESP8266) on the drone runs **esp-link**, a transparent bridge: it opens its own Wi-Fi access point and passes every byte between a TCP client on port 23 and the flight controller's UART1, with no MSP parsing on the ESP. Why esp-link and not MicroPython, and how fast the link is: [Wi-Fi latency tests](../../docs/Telemetry_test.md).

## Files in this folder

| File | What it is |
| --- | --- |
| `inav_telemetry.py` | Polls INAV over MSP and prints every value listed below |
| `latency_test.py` | MSP round-trip times; `make wifi-rtt` runs it and keeps the result in `project/logs/` |
| `msp_inventory.py` | Captures raw MSP replies (`capture`) or measures their rates (`rate`) |
| `receiver_crsf_ping.py` | Asks a CRSF/ELRS receiver for its name and version through INAV's serial passthrough ([ELRS guide](../../docs/ELRS_Guide.md)) |
| `tests/` | MSP framing, decoders and the drone recordings (pytest; run by `make test` and CI) |
| [`inav/`](inav/README.md) | INAV firmware choices, MSP captures (`msp/captures/`) and rate runs (`msp/rates/`) |
| [`msp_dashboard/`](msp_dashboard/README.md) | C++ terminal dashboard, and `msp_gateway`, the single owner of the link |

## ESP12

This step has to be done before wiring the ESP12 to the flight controller. It can be done with the ESP12 already soldered, but it's much more work.

### Prerequisites

#### 1 - Installing dependencies

Arch:

```bash
sudo pacman -S esptool
sudo usermod -aG uucp $USER    # serial port access; log out and in again
```

On Debian or Ubuntu the serial group is `dialout` instead of `uucp`. (`mpremote` was only needed for MicroPython, which the drone no longer runs.)

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

## Running the script

Turn on the drone using the battery pack, connect to its Wi-Fi, then from the repo root:

```bash
python3 project/telemetry/inav_telemetry.py --port 23                     # readable output, 5 Hz
python3 project/telemetry/inav_telemetry.py --port 23 --info --rate 2     # JSON lines
python3 project/telemetry/inav_telemetry.py --port 23 --log flight.jsonl  # also save to a file
python3 project/telemetry/inav_telemetry.py --help                        # every flag
```

> [!IMPORTANT]
> Always pass `--port 23`. The script still defaults to 5760, the port of the old MicroPython bridge, and won't connect to esp-link without it. The same goes for `latency_test.py`.

The [MSP dashboard](msp_dashboard/README.md) shows the same values as a live table, and the ROS stack reads them with `fc_bridge`'s `inav` backend ([ROS 2 stack](../ros2/README.md#fc_bridge)).

## Values that appear when using the script

### Sent once at startup

|Name|Meaning|Unit / range|
|---|---|---|
|`info.api_version.protocol`|MSP protocol version|number|
|`info.api_version.api`|MSP API version the firmware speaks|`major.minor`|
|`info.fc_variant`|Firmware identifier|`INAV`|
|`info.fc_version`|Firmware version|`major.minor.patch`|
|`info.board_info`|Short identifier of the flight controller board|4 characters|
|`info.craft_name`|Craft name set in INAV's Configuration tab|text, empty if not set|

### Every cycle

|Name|Meaning|Unit / range|
|---|---|---|
|`t`|Time this cycle was read, as a Unix timestamp|seconds|

#### Attitude (`attitude`)

|Name|Meaning|Unit / range|
|---|---|---|
|`attitude.roll_deg`|Roll angle, tilt left or right|degrees, 0.1° resolution|
|`attitude.pitch_deg`|Pitch angle, tilt nose up or down|degrees, 0.1° resolution|
|`attitude.heading_deg`|Heading, the direction the nose points|degrees, 0–359, 0 = north|

#### Altitude (`altitude`)

|Name|Meaning|Unit / range|
|---|---|---|
|`altitude.alt_m`|Estimated altitude relative to where the flight controller zeroed it (usually at arming)|meters|
|`altitude.vario_ms`|Vertical speed, positive when climbing|m/s|

#### GPS (`gps`)

|Name|Meaning|Unit / range|
|---|---|---|
|`gps.fix`|GPS fix type|0 = no fix, 1 = 2D, 2 = 3D|
|`gps.sats`|Number of satellites used|count|
|`gps.lat`|Latitude|degrees|
|`gps.lon`|Longitude|degrees|
|`gps.alt_m`|GPS altitude above sea level|meters|
|`gps.speed_ms`|Ground speed|m/s|
|`gps.course_deg`|Direction of travel over the ground (not where the nose points)|degrees, 0–359.9|
|`gps.hdop`|Horizontal dilution of precision: lower is more accurate, under about 1.5 is good|number|

#### Home (`gps_home`)

|Name|Meaning|Unit / range|
|---|---|---|
|`gps_home.home_dist_m`|Distance to the home point set at arming|meters|
|`gps_home.home_dir_deg`|Direction to the home point|degrees|

#### Battery and signal (`analog`)

|Name|Meaning|Unit / range|
|---|---|---|
|`analog.vbat_v`|Battery voltage|volts, 0.1 V resolution. Tops out at 25.5 V, so it reads wrong on batteries above 6S; use `inav_analog` for those|
|`analog.mah_drawn`|Capacity used since power-up|mAh|
|`analog.rssi_pct`|Radio receiver signal strength|percent, 0–100|
|`analog.current_a`|Current draw|amps, 0.01 A resolution. Reads 0 without a current sensor|

#### Raw sensors (`imu_raw`)

|Name|Meaning|Unit / range|
|---|---|---|
|`imu_raw.acc[1]` … `[3]`|Accelerometer X, Y, Z|raw sensor units|
|`imu_raw.gyro[1]` … `[3]`|Gyroscope X, Y, Z (rotation rate)|raw sensor units|
|`imu_raw.mag[1]` … `[3]`|Magnetometer (compass) X, Y, Z|raw sensor units, 0 without a compass|

#### Radio, motors, servos

|Name|Meaning|Unit / range|
|---|---|---|
|`rc_channels[n]`|Value of RC channel n as the flight controller sees it. The first four are the stick axes; move each stick to confirm which is which. The rest are AUX switches|µs, about 1000–2000, 1500 = center|
|`motors[n]`|Output sent to motor n|µs, about 1000 (stopped) to 2000 (full). Unused outputs read 0|
|`servos[n]`|Output sent to servo n (control surfaces on planes)|µs, about 1000–2000, 1500 = center|

#### Status (`status`, `status_ex`, `inav_status`)

These three overlap. `inav_status` is the most complete, so you can remove the other two from `LIVE` in the script to save bandwidth.

|Name|In|Meaning|Unit / range|
|---|---|---|---|
|`cycle_time_us`|all|Time the flight controller's main loop takes|microseconds|
|`i2c_errors`|all|I2C bus error counter. Rising values mean a sensor wiring or bus problem|count|
|`sensors[n]`|all|Sensors detected: `acc`, `baro`, `mag`, `gps`, `rangefinder`, `opflow`, `pitot`, `temp`|list, `none` if empty|
|`hardware_ok`|all|`False` if INAV reports a sensor hardware failure|True / False|
|`flight_modes[n]`|all|Modes currently active, named as in INAV's Modes tab (e.g. `ARM`, `ANGLE`, `NAV RTH`). `status` and `status_ex` only carry the first 32 modes|list, `none` if empty|
|`profile`|`status`, `status_ex`|Active PID profile|1-based, as in Configurator|
|`pid_profile`|`inav_status`|Active PID profile|1-based|
|`battery_profile`|`inav_status`|Active battery profile|1-based|
|`mixer_profile`|`inav_status`|Active mixer profile (newer INAV versions only)|1-based|
|`cpu_load_pct`|`status_ex`, `inav_status`|Flight controller CPU load|percent|
|`armed`|`status_ex`, `inav_status`|Whether the aircraft is armed|True / False|
|`was_ever_armed`|`status_ex`, `inav_status`|Whether it has been armed since power-up|True / False|
|`arming_blockers[n]`|`status_ex`, `inav_status`|Reasons arming is currently blocked (e.g. `rc_link`, `not_level`, `arm_switch`, `navigation_unsafe`). `status_ex` only carries the first 16 flags, so use `inav_status`|list, `none` if nothing blocks arming|

#### Detailed battery (`inav_analog`)

|Name|Meaning|Unit / range|
|---|---|---|
|`inav_analog.voltage_v`|Battery voltage, works on any cell count|volts, 0.01 V resolution|
|`inav_analog.current_a`|Current draw|amps, 0.01 A resolution|
|`inav_analog.power_w`|Power draw|watts|
|`inav_analog.mah_drawn`|Capacity used|mAh|
|`inav_analog.mwh_drawn`|Energy used|mWh|
|`inav_analog.remaining_capacity`|Remaining capacity, if battery capacity is set in INAV|in the unit set in INAV (mAh or mWh), 0 if not set|
|`inav_analog.battery_pct`|Estimated remaining battery|percent|
|`inav_analog.cell_count`|Detected number of cells|count|
|`inav_analog.battery_state`|`ok`, `warning`, `critical` or `not_present`|text|
|`inav_analog.full_when_plugged_in`|Whether the battery was detected as full at power-up|True / False|
|`inav_analog.uses_capacity_thresholds`|Whether warnings use capacity instead of voltage|True / False|
|`inav_analog.rssi_pct`|Radio signal strength|percent, 0–100|

# How to connect to the drone's Wi-Fi

By default esp-link creates an open network.

Our network was set with:

```bash
SSID: seemeflying
Password: 123456789
```

Keep the drone's ESP to **one client**: a second one caused link dropouts on Nov 18 ([motor music runs](../logs/measurements/motor_music/README.md)). If several tools need the drone, run [`msp_gateway`](msp_dashboard/README.md#msp_gateway-one-owner-for-the-msp-link) as the only one connected.

# Tests

Tests were made with a bunch of different setups on the ESP, and all are documented in the [Wi-Fi latency tests](../../docs/Telemetry_test.md). The MSP framing and decoders are unit-tested in `tests/` (`make test`, and CI job `telemetry-python`).

# Tags

#guides
