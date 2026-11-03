# Setting up INAV'S telemetry

## ESP12

This step has to be done before wiring the ESP12 to the flight controller, it can be done with the ESP12 already soldered but it's way more work.

### Pre requisites

#### 1 - Installing dependencies

Arch:

```bash
sudo pacman -S python-pipx
sudo pacman -S esptool
pipx install mpremote
pipx ensurepath

sudo usermod -aG uucp $USER
```

#### 2 - Download and flash micropython

Head to `micropython.org/download/ESP8266_GENERIC` and download the latest stable build.

Go to the folder and plug your ESP12 and check your PC recognizes it with `lsusb` and `ls /dev/tty*` a /dev/ttyUSB0 should be present.

**Now use esptool**:

```bash
esptool erase-flash
esptool --baud 460800 write_flash --flash_size=detect 0 ESP8266_GENERIC-*.bin
```

To check if the flash went well you can use:

```bash
pyserial-miniterm --rts 0 --dtr 0 /dev/ttyUSB0 115200
```

Press the rst button and then press enter a few times and you should get `>>>` meaning that you've entered MicroPython's REPL prompt, you can now leave pressing `Ctrl + j`

#### 3 - Sending main.py to the ESP12

On this repo you'll find two python scripts, one for the ESP12 that will run on boot and one for the ground machine, download main.py and run these commands:

> [!IMPORTANT]  
> Check `main.py` and change the network's SSID and password

```bash
mpremote connect /dev/ttyUSB0 cp main.py :main.py 
mpremote connect /dev/ttyUSB0 reset
```

After this you can go ahead and use the `pyserial` again and you should immediatly see the message `MSP bridge starts in 3 seconds[...]`, if you do, great it means that the ESP12 and you can go ahead and solder it to the flight controller.

## Running the script

First, download the `inav_telemtry.py`, turn on the drone using the battery pack and connect to it's wifi SSID, after that you can go ahead and run the script.

The script has flags that the user can check using:

```bash
python3 inav_telemetry.py --help
```

## Values that appear when using the script:


## Sent once at startup

|Name|Meaning|Unit / range|
|---|---|---|
|`info.api_version.protocol`|MSP protocol version|number|
|`info.api_version.api`|MSP API version the firmware speaks|`major.minor`|
|`info.fc_variant`|Firmware identifier|`INAV`|
|`info.fc_version`|Firmware version|`major.minor.patch`|
|`info.board_info`|Short identifier of the flight controller board|4 characters|
|`info.craft_name`|Craft name set in INAV's Configuration tab|text, empty if not set|

## Every cycle

|Name|Meaning|Unit / range|
|---|---|---|
|`t`|Time this cycle was read, as a Unix timestamp|seconds|

### Attitude (`attitude`)

|Name|Meaning|Unit / range|
|---|---|---|
|`attitude.roll_deg`|Roll angle, tilt left or right|degrees, 0.1° resolution|
|`attitude.pitch_deg`|Pitch angle, tilt nose up or down|degrees, 0.1° resolution|
|`attitude.heading_deg`|Heading, the direction the nose points|degrees, 0–359, 0 = north|

### Altitude (`altitude`)

|Name|Meaning|Unit / range|
|---|---|---|
|`altitude.alt_m`|Estimated altitude relative to where the flight controller zeroed it (usually at arming)|meters|
|`altitude.vario_ms`|Vertical speed, positive when climbing|m/s|

### GPS (`gps`)

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

### Home (`gps_home`)

|Name|Meaning|Unit / range|
|---|---|---|
|`gps_home.home_dist_m`|Distance to the home point set at arming|meters|
|`gps_home.home_dir_deg`|Direction to the home point|degrees|

### Battery and signal (`analog`)

|Name|Meaning|Unit / range|
|---|---|---|
|`analog.vbat_v`|Battery voltage|volts, 0.1 V resolution. Tops out at 25.5 V, so it reads wrong on batteries above 6S; use `inav_analog` for those|
|`analog.mah_drawn`|Capacity used since power-up|mAh|
|`analog.rssi_pct`|Radio receiver signal strength|percent, 0–100|
|`analog.current_a`|Current draw|amps, 0.01 A resolution. Reads 0 without a current sensor|

### Raw sensors (`imu_raw`)

|Name|Meaning|Unit / range|
|---|---|---|
|`imu_raw.acc[1]` … `[3]`|Accelerometer X, Y, Z|raw sensor units|
|`imu_raw.gyro[1]` … `[3]`|Gyroscope X, Y, Z (rotation rate)|raw sensor units|
|`imu_raw.mag[1]` … `[3]`|Magnetometer (compass) X, Y, Z|raw sensor units, 0 without a compass|

### Radio, motors, servos

|Name|Meaning|Unit / range|
|---|---|---|
|`rc_channels[n]`|Value of RC channel n as the flight controller sees it. The first four are the stick axes; move each stick to confirm which is which. The rest are AUX switches|µs, about 1000–2000, 1500 = center|
|`motors[n]`|Output sent to motor n|µs, about 1000 (stopped) to 2000 (full). Unused outputs read 0|
|`servos[n]`|Output sent to servo n (control surfaces on planes)|µs, about 1000–2000, 1500 = center|

### Status (`status`, `status_ex`, `inav_status`)

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

### Detailed battery (`inav_analog`)

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
