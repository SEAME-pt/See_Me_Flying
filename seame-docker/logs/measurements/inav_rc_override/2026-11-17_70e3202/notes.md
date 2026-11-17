# ROS sticks through MSP RC OVERRIDE on the real drone, Nov 17

`scripts/bench_rc_override.sh` with the `inav-6` build (commit 70e3202): `fc_bridge backend:=inav rc_override:=true` on the ground laptop, joined to the drone's Wi-Fi (esp-link, `192.168.4.1:23`). Props off, **never armed** (AUX1 at 1000 for the whole bag), Configurator closed. FC config: `../fc_config_2026-11-17/` (`msp_override_channels = 15`, MSP RC OVERRIDE on SA = channel 7).

`events.log` has a line per step and each readout; `bridge.log` the node's log; `bag/` (MCAP) `fc/rc`, `fc/status`, `fc/setpoint_velocity`, `fc/attitude`. Times below are from the bag.

## Results

| # | Step | Expected | Seen |
| --- | --- | --- | --- |
| 1 | SA off, radio pitch stick up | `fc/rc` follows the radio | Pitch went up to 2012 in the bag (the readout itself caught it centred). Radio values otherwise: roll 1503, yaw 1498, throttle 989. `override_active` false. ✅ |
| 2 | SA on, no setpoint | 1500 ×4, `override_active` true | 1500 ×4, true. Radio pitch held up: still 1500, the radio is ignored. ✅ |
| 2 | forward 0.25 m/s | pitch 1750 | pitch 1750 ✅ |
| 2 | left 0.25 m/s | roll 1250 | roll 1250 ✅ |
| 2 | up 0.15 m/s | throttle 1750 | throttle 1750 ✅ |
| 2 | yaw left 0.5 rad/s | yaw 1250 | yaw 1250 ✅ |
| 3 | setpoints stop | 1500 ×4 | 1500 ×4 ✅ |
| 4 | bridge stopped while sending pitch 1750 | back to the radio after ~0.9 s | Back to the radio: the listen-only bridge's first reading (2.1 s after the stop) was already the radio's. ✅, but only a bound: ≤ 2.1 s |
| 5 | laptop off the Wi-Fi (link silent for about 7 s) | back to the radio; ROS again after reconnecting | Silent link caught 0.75 s after the last reply, reconnected after 7 s; the first readings were the radio's (INAV had dropped the override), then ROS's pitch 1750 again 2.0 s after the link came up ✅ |
| 6 | SA on, radio off | not known | **The override keeps applying**: pitch 1750, `override_active` true, channel 7 held at 2000, in both readouts 5 s apart with the radio off |
| 7 | radio on, SA off | the radio | radio values, `override_active` false ✅ |

All four axes have the sign and AETR order step B's tests pin, so the mapping matches INAV.

## Timings

- **Takeover:** after the bridge (re)starts sending, INAV kept the radio's values for 0.95 s (step 4 → 5 restart) and 2.0 s (after the Wi-Fi drop) before using ROS's sticks. The docs say it needs more than 700 ms of frames; over this Wi-Fi it takes longer.
- **Return to the radio:** at most 2.1 s after the last frame; a better bound needs a reader that stays connected while the sender stops (not possible with one bridge).
- **Link:** three single-cycle gaps ("No reply from the FC") in 3.5 minutes besides the planned drop, each back the next cycle, as on Nov 16.

## What it means

- Step 6: losing the radio does **not** end the override. Disarmed here, nothing happens. Armed, the radio failsafe (`failsafe_procedure = DROP`) follows the radio only and would still cut the motors; but if INAV's RX failsafe did not trip, ROS would keep flying with no pilot able to take over by switch. To confirm before ROS flies it: does INAV's failsafe trip with the override on and the radio off, while armed?
- Throttle 1500 with ROS in control is raw half throttle (no ALTHOLD); see the plan's risk list before any armed test.

Not checked: radio sticks with the override on in every axis (only pitch was held).
