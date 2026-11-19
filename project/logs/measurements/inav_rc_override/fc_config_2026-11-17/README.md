# Flight controller config, Nov 17, 2026 (INAV-6 setup)

`diff all` from the INAV Configurator CLI over USB, before and after `set msp_override_channels = 15` + `save`. Board ODDITYRCF7AIO, INAV 9.1.0 (e519b69b). Full outputs are in the chat of that day; the lines that matter are below.

Checked: `map` = AETR, `receiver_type` = SERIAL.

Changed by the save: `msp_override_channels = 15` (new). `gyro_zero_y/z` and `ins_gravity_cmss` moved slightly: the boot calibration, stored by `save`, harmless.

Modes (`aux <index> <mode id> <aux channel> <low> <high>`), the same before and after the `set`:
- `aux 0 0 0 1700 2100`: ARM on AUX1 (channel 5).
- `aux 1 51 1 1700 2100`: PREARM (id 51) on AUX2 (channel 6).
- `aux 2 1 0 1700 2100`: ANGLE on AUX1, so the drone is always in ANGLE when armed.
- `aux 3 50 2 1700 2100`: MSP RC OVERRIDE (id 50) on AUX3 (channel 7), the radio's 2-position switch SA. Added afterwards in the Modes tab. Checked over USB with the radio on: only CH7 moves with SA, and the mode lights up when SA is on.

Other settings that matter for INAV-6:
- `rc_expo = 80`, `rc_yaw_expo = 80` (defaults 70 and 20), `roll_rate = pitch_rate = 70`, `yaw_rate = 60`.
- `failsafe_procedure = DROP`: radio lost while armed stops the motors. `failsafe_delay` at default (5): the override reverts about 0.9 s after frames stop.
- No NAV ALTHOLD on a switch: throttle from ROS would be raw throttle.
- `opflow_hardware = CXOF`, `serial 3 16384 ... 19200`: UART3 is the old flow sensor's (FUNCTION_OPTICAL_FLOW). `serial 2 4096`: UART2 is VTX Tramp. No rangefinder set.
