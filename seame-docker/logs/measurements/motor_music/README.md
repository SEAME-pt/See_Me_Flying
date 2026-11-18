# Motor music runs

`scripts/motor_music/sing.sh`: the motors play a melody through ROS (`fc/setpoint_velocity` → fc_bridge `rc_override` → INAV), props off. Only the runs worth keeping are here, with their events, step times and metadata; bags and recordings stay on the laptop that ran them. The laptop mic records no real sound, so there is no audio of any run.

| Run | What it shows |
|---|---|
| `2026-11-17_ab84ee9-4` | Calibration on the normal PID profile: INAV's stabilisation winds up within a second without props and holds the motors at about [1720, 1400, 1400, 1080] whatever the throttle. Any props-off motor test needs a control profile with roll, pitch and yaw PIDs at zero. |
| `2026-11-17_dbf0160-2` | The first song, on the zero-PID profile: recognizable. INAV gives the motors stick − 20; notes reach the motors 150–270 ms after ROS publishes them. Details in its `notes.md`. |
| `2026-11-18_1c32036-5` | A run broken by link dropouts (below): the override held only 3.8–14 s after "go", so only that part of the song played. `bridge.log` has the dropouts. |
| `2026-11-18_1c32036-12` | The same song after the fix: one dropout in the whole run, the override held through the song. |

Not kept: earlier attempts while a wire to the ESP was loose (the FC never answered), a trial with the tuning measured in `dbf0160-2` (zero 1079, base 1250: it sounded worse by ear, so the defaults stayed at 976/1150), and today's other broken runs.

## Nov 18: most runs didn't play

Same code and build as Nov 17. SA was on (CH7 2000), but INAV kept the radio's sticks most of the time. The bridge logged 5 to 23 "No reply from the FC" per run (Nov 17: 0 to 4), and the laptop lost the drone's Wi-Fi 11 times in 12 minutes (beacon loss and deauth in its journal). INAV only applies MSP RC OVERRIDE after 0.7 s of unbroken MSP_SET_RAW_RC frames and drops it after about 0.4 s without them, so every dropout handed control back to the radio.

Cause: a Raspberry Pi with a second ESP was connected to the drone's ESP. With it disconnected, the song played normally again. **Keep the drone's ESP to one client, the laptop running fc_bridge.**
