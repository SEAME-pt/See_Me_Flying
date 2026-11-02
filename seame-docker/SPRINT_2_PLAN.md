# Sprint 2 plan: ROS side, Nov 2 – Nov 13, 2026

João's part of the sprint: the ROS work and the links it depends on, nothing else on the hardware side. Sprint 1's work is in [PLAN.md](PLAN.md) (steps 1–7) and [CHANGES.md](CHANGES.md).

**Sprint goal: ROS reads the real drone over Wi-Fi, and we know how good the link is.**

The sim stack (steps 1–7 of [PLAN.md](PLAN.md)) is ahead of the hardware. Everything left on the ROS side needs the MSP link, so this sprint is about that link: read-only, on the bench, props off. Nothing in ROS commands a real motor this sprint.

## Assumptions

- ROS runs on the ground laptop; `fc_bridge` talks MSP to INAV through the ESP8266 (STK-1, done). No computer on the drone.
- One drone per team.
- Bench rules for every test with the real drone: props off, radio on and bound, INAV's own failsafe configured (INAV-2, done).
- The MSP message names below come from the MSP and INAV references and must be checked against our INAV version before coding against them.

## What I depend on (not mine, but blocking)

| Item | Issue | Needed by | If it slips |
| --- | --- | --- | --- |
| MSP open on UART1, reachable through the ESP8266 from the laptop | INAV-3.2 (#67) | Day 2 | Items 1–4 wait; do items 6–8 first |
| Rangefinder model, flight controller + `CXOF` support, ThoneFlow version | Team decision | End of week 1 | Flow/rangefinder work moves to next sprint; no effect on this sprint's goal |

## Week 1: talk to INAV

### 1. MSP probe tool

- **What:** `ros2_ws/tools/msp_probe.py`, standalone (no ROS). Connects to the ESP8266 over TCP, sends `MSP_API_VERSION`, `MSP_FC_VARIANT` and `MSP_STATUS`, prints the replies and each round-trip time.
- **Why:** proves the link and the framing (MSP v1 and v2 headers, checksums) before any of it goes into C++.
- **Done when:** INAV answers over Wi-Fi, and the tool reports "INAV" and its version.
- **Size:** 1 day, after INAV-3.2.

### 2. Measure the link

- **What:** extend the probe: N requests at a fixed rate (e.g. 1000 at 20 Hz), report mean, 95th percentile, max round-trip time and drops. Run at the bench and in the cage, with the radio on.
- **Why:** the numbers decide the `inav` backend's timeouts and how fast it can poll. If the link is bad, that is the most important result of the sprint: it reopens the architecture question (an onboard computer).
- **Done when:** the numbers are on the measurement sheet.
- **Issues:** STK-5.1 (#81, method), STK-5.2 (#82, measure), STK-5 (#80).
- **Size:** 1 day.

### 3. Decide the MSP client for `fc_bridge`

- **What:** `fc_bridge` is C++, so the MSP client is C++: a small framing/parsing class with its own tests, or an existing library if one fits (license, MSP v2 support, no heavy deps). Write down the choice in PLAN.md.
- **Size:** half a day.

## Week 2: the read-only `inav` backend

### 4. `fc_bridge` `inav` backend reads state

- **What:** in the existing `inav` branch of `fc_bridge`:
  - connect (TCP), reconnect on loss, log the link state;
  - poll at a rate the link allows (from item 2): attitude (`MSP_ATTITUDE`), status and armed (`MSP2_INAV_STATUS`), battery (`MSP2_INAV_ANALOG`), altitude if useful (`MSP_ALTITUDE`);
  - publish `fc/attitude`, `fc/status` (real armed state; add link age), `fc/battery` (`sensor_msgs/BatteryState`);
  - time every request; a late or missing reply marks the link stale in `fc/status`;
  - still sends no commands.
- **Tests:** a fake MSP server in Python (replies with canned frames) so launch tests run without hardware: attitude decoded, armed state followed, link loss reported, reconnect works.
- **Done when:** on the bench, tilting the drone by hand moves `fc/attitude` in ROS, arming with the radio shows `armed: true` in `fc/status`, and unplugging the ESP8266 is reported.
- **Size:** 3–4 days. The biggest item.

### 5. Low battery, for real

- **What:** `safety_manager` already listens to `fc/battery`; check its warning with real values, and decide the threshold with the team.
- **Done when:** a low battery on the bench logs the warning.
- **Size:** half a day, after item 4.

## Any time (no hardware needed; fill gaps while blocked)

### 6. `-inf` in the air cross-check

- **What:** a rangefinder failing as `-inf` in flight looks like height 0, so `mission` would climb. Trust `-inf` only when `fc/odom` height agrees it's near the ground; otherwise treat it as range lost.
- **Done when:** logic tests cover it, and it's in the README known issues as fixed.
- **Size:** half a day. Listed as "before hardware".

### 7. `fc_bridge` recovery test

- **What:** a launch test: setpoints stop, `fc_bridge` sends zero; setpoints come back, it logs once and follows them again.
- **Why:** noted as missing on #70 and #79.
- **Size:** half a day.

### 8. Command rate and jitter in the sim

- **What:** `ros2 topic hz` on `/cmd/mission`, `/fc/setpoint_velocity` and `/X3/gazebo/command/twist` during the demo; record mean rate and jitter.
- **Issues:** ROS-7.1 (#77); with CI still open, ROS-7 (#76) stays open.
- **Size:** half a day.

## Should do, if the link works early

### 9. How INAV takes commands from MSP

- **What:** research and a props-off bench check, no code. As far as I know INAV doesn't take velocities: a companion sends stick values (`MSP_SET_RAW_RC`) into channels chosen with `msp_override_channels`, only while the radio enables an "MSP RC override" mode. In INAV's position-hold modes, stick deflection then works roughly like a velocity request, and the radio switch is our takeover switch, the other way round.
- **Done when:** a short note in PLAN.md says how `fc/setpoint_velocity` maps to MSP, confirmed on the bench by watching the override in the INAV Configurator's receiver tab (props off).
- **Size:** 1–2 days.

## Not this sprint

- Any ROS command reaching a motor, and any autonomous flight on the real drone.
- Calibrating the sim's sensor model (needs the flow sensor and rangefinder fitted and flying).
- The no-rangefinder sim branch, unless the team decides against a rangefinder.
- CI (STK-4.3): someone else's; our tests are ready for it.

## Risks

| Risk | Effect | What to do |
| --- | --- | --- |
| ESP8266 link slow or lossy | The outer loop over Wi-Fi may not work | Measure in week 1 (item 2); bring the numbers to the team early |
| INAV-3.2 not done by day 2 | Week 1 slips | Start with items 6–8 |
| MSP messages differ in our INAV version | Item 4 takes longer | Check with the probe (item 1) before writing C++ |
| Hardware decisions slip | Flow/rangefinder path waits | Doesn't block this sprint's goal; raise it at the next meeting |

## Checkpoints

- **End of week 1:** the probe talks to INAV over Wi-Fi; latency numbers on the sheet; MSP client chosen.
- **End of week 2:** `fc/attitude`, `fc/status` and `fc/battery` from the real drone in ROS, with tests; items 6–8 done; item 9 if there was time.
