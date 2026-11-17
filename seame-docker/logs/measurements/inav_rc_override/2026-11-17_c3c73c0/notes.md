# ROS drives the motors through MSP RC OVERRIDE, armed, props off, Nov 17

`scripts/bench_rc_armed.sh` with the `inav-6` build (commit c3c73c0, `fc/motors` included). **Props off**, the drone held by hand, armed from the radio, laptop on the drone's Wi-Fi. FC config: `../fc_config_2026-11-17/`; the motor mixer is INAV's default quad X (`mmix` in `docs/extras/Drone_INAV_Backup_26_10_26.txt`): 1 rear right, 2 front right, 3 rear left, 4 front left.

`events.log` has every step and readout, `bridge.log` the node, `bag/` `fc/rc`, `fc/motors`, `fc/status`, `fc/setpoint_velocity`, `fc/attitude`. Times below are seconds into the bag's minute (`:15` = 1794929615).

## Results

| Step | Expected | Seen |
| --- | --- | --- |
| Arm on the radio, SA off | motors idle | all four at 1080 (`throttle_idle`) |
| SA on, ROS at idle | throttle 1000, no jump | throttle 1000, motors still 1080: no jump ✅ |
| Ramp 1167 → 1333 → 1500 → 1000 | motors follow | they rise and fall with each step ✅ (on top of the offset below) |
| Left (roll 1250) | right motors up, left down | 1 +350, 2 +370, 3 −145 (to idle), 4 −380 ✅ |
| Forward (pitch 1750) | rear up, front down | 2 (front right) −230, 1 (rear) +70…+130, 3 (rear) up to +90; 4 (front left) rose, but the drone was rolled left by hand at the same time (−1° → −5°), which raises the left motors ✅ mostly |
| Yaw left (yaw 1250) | one diagonal up | **2 and 3** up (+380, +210), 1 and 4 down. Which way that turns the drone depends on the motors' spin direction: see below |
| SA off, disarm | radio, motors stop | ✅ |
| Failsafe: armed, SA on at idle, radio off | motors stop | **INAV disarmed itself** (`:74.5`), motors 1000 ✅ |

## The motors aren't even with level sticks

During the whole armed run the drone sat 4–9° nose down in the hand (`fc/attitude` pitch), roll moving a few degrees either way. ANGLE mode tries to level it; without props nothing levels, so the correction keeps growing (the I term winds up): front motors 2 and 4 high, rear 3 at idle, even at a level stick. Expected with props off, and it is why each direction is read as a change against the second before it, not as absolute values.

## Timings

- **Setpoint to INAV:** a new setpoint shows in `fc/rc` 170–270 ms later, and in the motors in the same reply. That is the bridge tick, up to one poll cycle and the Wi-Fi round trip.
- **Poll rate:** 8.6 cycles/s, down from 10 with 8 reads (adding `MSP_MOTOR`) and the stick frame. INAV answers one request per 10 ms, so a cycle no longer fits in 100 ms.

## What it settles

- **Failsafe with the override on:** the open question from the unarmed run. Radio off while armed with SA on: INAV disarms (`failsafe_procedure = DROP`). Unarmed, the override just keeps applying; armed, the radio link still decides.
- **Arming with SA on:** between step 5's prompts INAV reports disarmed at `:97.4`, armed again at `:03.9` with the override still on (off at `:06.9`), and disarmed at `:34.7`. So INAV accepts arming while ROS has the sticks, as long as ROS's throttle is low (here 1000). With ROS at 1500 it should refuse (throttle not low); not tried.

## Open

- **Yaw direction.** Our yaw-left is a stick to the left (1250), the same as a pilot's; INAV turned it into motors 2 and 3 up. With props-in motors (INAV's default spin), that pair turns the drone right; with props-out, left. To check, armed and props off: push the radio's yaw stick left with SA off and see which pair rises. If it is 2 and 3 too, ROS and the pilot agree, and the actual turn direction is the FC's setup, to see on the first flight.
- The half-broken motor (which one?) showed nothing unusual in the readback.
