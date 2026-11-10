# INAV MSP candidate list (INAV-4.1, #124)

This is the list of read-only MSP messages to capture (#125) and measure (#126) for the MSP inventory (#123).

Every ID, payload layout and unit below was checked against the INAV source at the `9.1.0` tag:

- `src/main/msp/msp_protocol.h`: v1 message IDs
- `src/main/msp/msp_protocol_v2_inav.h`: INAV v2 message IDs (0x2000 and up)
- `src/main/fc/fc_msp.c`: the code that builds each reply

All multi-byte fields are little-endian. "int" fields are signed, "uint" fields are unsigned.

`telemetry/inav_telemetry.py` polls exactly this list, with a decoder for every message. Its additions for this issue are marked `### New Check ###`.

**On drone** shows that the message answered over esp-link on the real FC (INAV 9.1.0, board ODF7, target ODDITYRCF7AIO, craft PILOTIX-BROOK). Every message on this list answered in the run of the updated `inav_telemetry.py` on 2026-11-08: 11 polling cycles, 4 of 143 requests without a reply (about 3%). The drone was upside down on the bench, props off, with no radio connected.

## Live messages: keep

These are polled continuously.

| Message | ID | Payload, in order | Bytes | Needed by | On drone |
| --- | --- | --- | --- | --- | --- |
| MSP2_INAV_STATUS | 0x2000 | cycle time: uint16, µs · I2C errors: uint16 · sensors: uint16 bitmask · CPU load: uint16, % · profiles: uint8 (battery profile in high 4 bits, PID profile in low 4 bits) · arming flags: uint32 bitmask · active modes: 8-byte bitmask · mixer profile: uint8 | 22 | ROS-5, ROS-6 | 2026-11-08 |
| MSP_ATTITUDE | 108 | roll: int16, 0.1° · pitch: int16, 0.1° · yaw: int16, 1° | 6 | ROS-5, ROS-6, STK-5 | 2026-11-08 |
| MSP_ALTITUDE | 109 | estimated altitude: int32, cm · vertical speed: int16, cm/s · baro altitude: int32, cm | 10 | ROS-5, ROS-6 | 2026-11-08 |
| MSP_RAW_IMU | 102 | acc X, Y, Z: int16, 1/512 g · gyro X, Y, Z: int16, °/s · mag X, Y, Z: int16, raw (always 0 without a magnetometer) | 18 | ROS-6 | 2026-11-08 |
| MSP2_INAV_ANALOG | 0x2002 | battery flags: uint8 (see notes) · voltage: uint16, 0.01 V · current: int16, 0.01 A · power: int32, 0.01 W · used: uint32, mAh · used: uint32, mWh · remaining capacity: uint32 · battery: uint8, % · RSSI: uint16, 0–1023 | 24 | ROS-6 | 2026-11-08 |
| MSP2_INAV_OPTICAL_FLOW | 0x2001 | quality: uint8, 0–255 · flow rate X, Y: int16, °/s · body rate X, Y: int16, °/s | 9 | ROS-6, INAV-5 | 2026-11-08 (quality 100 while still) |
| MSP_RC | 105 | one uint16 per RC channel, µs | 2 × channels (34 with 17 channels) | ROS-6 | 2026-11-08 |
| MSP_SONAR_ALTITUDE | 58 | rangefinder distance: int32, cm; negative means no valid reading (−1 = out of range) | 4 | ROS-6, INAV-5 | 2026-11-08 (reads 0 cm: no sensor fitted yet, see notes) |
| MSP2_INAV_FULL_LOCAL_POSE | 0x2220 | roll, pitch, yaw: int16, 0.1° · then for X, Y, Z in turn: position int32 and velocity int16, from INAV's position estimator (INAV's navigation code works in cm and cm/s) | 24 | ROS-5, ROS-6, INAV-5 | 2026-11-08 (position and velocity 0 with no position estimate yet) |

**MSP2_INAV_FULL_LOCAL_POSE** returns INAV's own position and velocity estimate in one reply, which is what an indoor drone with optical flow needs. It also gives yaw in 0.1° steps, where MSP_ATTITUDE gives whole degrees.

## Startup messages: keep

These are asked once, when the ground side connects.

| Message | ID | Payload, in order | Bytes | Needed by | On drone |
| --- | --- | --- | --- | --- | --- |
| MSP_API_VERSION | 1 | MSP protocol version: uint8 · API major: uint8 · API minor: uint8 | 3 | STK-5 (link check) | 2026-11-08 (API 2.5) |
| MSP_FC_VARIANT | 2 | firmware name: 4 ASCII characters (`INAV`) | 4 | ROS-6 | 2026-11-08 |
| MSP_FC_VERSION | 3 | major, minor, patch: uint8 each | 3 | ROS-6 | 2026-11-08 |
| MSP_BOARD_INFO | 4 | board ID: 4 ASCII characters (`ODF7`) · hardware revision: uint16 · OSD support: uint8 · comms capabilities: uint8 · target name length: uint8 · target name: ASCII | 9 + name | ROS-6 | 2026-11-08 |
| MSP_NAME | 10 | craft name: ASCII, no terminator | name length | ROS-6 | 2026-11-08 |
| MSP_BOXNAMES | 116 | names of the available flight modes, each followed by `;` | varies | ROS-6 | 2026-11-08 |

## Optional: decide with ROS-5.1

| Message | ID | Payload | Bytes | Why it might be useful | On drone |
| --- | --- | --- | --- | --- | --- |
| MSP_NAV_STATUS | 121 | nav mode, nav state, waypoint action, waypoint number, nav error: uint8 each · heading-hold target: int16 | 7 | Shows what INAV's navigation is doing during autonomous flight (INAV-5, INAV-6) | 2026-11-08 |
| MSP2_INAV_GET_LINK_STATS | 0x2103 | uplink RSSI: uint8 (sent as minus dBm) · link quality: uint8 · SNR: int8 | 3 | Radio link quality, once the radio is connected | 2026-11-08 (all 0 with no radio) |
| MSP_MOTOR | 104 | 8 × uint16 motor outputs | 16 | Only meaningful while armed; reads 1000 on the bench | 2026-11-08 |

## Dropped

These are removed from `inav_telemetry.py` too.

| Message | ID | Reason |
| --- | --- | --- |
| MSP_STATUS | 101 | Deprecated in INAV 9.1 and removed in 10.0. Use MSP2_INAV_STATUS. |
| MSP_STATUS_EX | 150 | Deprecated in INAV 9.1 and removed in 10.0. Use MSP2_INAV_STATUS. |
| MSP_ANALOG | 110 | Deprecated in INAV 9.1 and removed in 10.0. Use MSP2_INAV_ANALOG. |
| MSP_RAW_GPS | 106 | No GPS on an indoor drone; read all zeros in the link check |
| MSP_COMP_GPS | 107 | No GPS, so no home distance or direction; read all zeros |
| MSP_SERVO | 103 | No servos; read the 1500 default on every channel |
| MSP2_INAV_AIR_SPEED | 0x2009 | No airspeed sensor; always 0 |
| MSP_ACTIVEBOXES | 113 | Same mode bitmask as in MSP2_INAV_STATUS |
| MSP_SENSOR_STATUS | 151 | Polling it makes INAV treat the link as a Configurator connection for 1 s, which stops Blackbox logging when `blackbox_arm_control` is −1. The sensor bitmask in MSP2_INAV_STATUS covers the same need. |

## Excluded: write commands

Commands that change the FC's state, such as `MSP_SET_RAW_RC` (200), are not part of the inventory. They belong to INAV-6 and its safety limits. The capture and rate scripts send read commands only.

## Notes for the decoders (ROS-6.2)

- **Sensor bitmask** (MSP2_INAV_STATUS): bit 0 acc, 1 baro, 2 mag, 3 GPS, 4 rangefinder, 5 optical flow, 6 pitot, 7 temperature, 15 hardware failure.
- **Arming flags** (MSP2_INAV_STATUS): bit 2 armed, bit 3 was ever armed, and bits 6–30 are reasons arming is blocked. The ones seen on the bench are bit 8 not level, bit 18 no RC link and bit 28 no prearm. The full list is in `src/main/fc/runtime_config.h`.
- **Mode bitmask:** bit *n* means the *n*-th name in the MSP_BOXNAMES reply, counting from 0, is active. It is not a fixed mode ID, so always read MSP_BOXNAMES at startup. On this drone, with no radio connected, the active mode decodes as `FAILSAFE`.
- **Rangefinder:** trust MSP_SONAR_ALTITUDE only when the rangefinder bit (bit 4) is set in the MSP2_INAV_STATUS sensor bitmask. With no sensor fitted it reads 0 cm, which looks like a valid distance.
- **Battery flags** (MSP2_INAV_ANALOG): bit 0 full when plugged in, bit 1 uses capacity thresholds, bits 2–3 battery state, bits 4–7 cell count.
- **Remaining capacity** is in mAh or mWh, depending on the `battery_capacity_unit` setting.
- **Yaw** is in whole degrees in MSP_ATTITUDE but in 0.1° steps in MSP2_INAV_FULL_LOCAL_POSE.
- **Signed fields:** INAV writes some signed values with unsigned write calls (current, optical flow rates, attitude), so decode them as signed.
