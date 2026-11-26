---
title: Sprint 1
---
# Sprint 1 — Telemetry, Simulation & Video

- **Period:** 19 October – 1 November 2026
- **Duration:** 2 weeks
- **Phase:** Implementation

> [!NOTE]
> This page was put together from the other project documents on Nov 19. Add the sprint review's own notes (goals, what slipped, retrospective) where they belong.

## 1. Sprint Objective

Turn the Sprint 0 baseline into working links: read INAV over Wi-Fi, fly the drone in simulation with the same command path the real drone will use, bring the FPV video into ROS, and check every change in CI.

## 2. Work Completed

### 2.1 Telemetry and INAV

- ESP12 bridge between the flight controller's UART1 and the ground computer, first on MicroPython, later on esp-link for lower latency ([ESP12 setup](project/telemetry/README.md), [Wi-Fi latency tests](Telemetry_test.md)).
- `inav_telemetry.py` reads attitude, altitude, battery, RC channels, motors, arming blockers and modes over MSP.
- Radio receiver replaced (TBS Crossfire → BETAFPV Nano RX on ELRS 4.1.0), bound to the RadioMaster Pocket, arming and radio-loss failsafe tested ([ELRS guide](ELRS_Guide.md)).
- Battery reading calibrated: `vbat_scale = 1103` (Oct 28, [Li-Po battery tests](Li-Po_Battery_Tests.md)).
- INAV configuration backed up on Oct 26 ([`project/hardware/flight-controller/`](../project/hardware/flight-controller/)).

### 2.2 Simulation stack

- `fc_bridge` sends zero velocity when setpoints go stale (0.3 s), rejects NaN, and clamps every command.
- `radio_teleop`: the RadioMaster over USB arms, disarms and takes over in the sim, with the arm switch debounced (Oct 26).
- Failsafe tests automated with `launch_testing` (Oct 26); drone models kept across container rebuilds.
- `fc_bridge` reports `fc/odom`, `fc/attitude` and `fc/range` like the real drone will (Oct 27).
- `mission` node: takeoff, goto and land on the rangefinder, replacing the timed `setpoint_pub` (Oct 29).
- `safety_manager`: one commander at a time, the radio overrides the mission (Oct 30).

Every node in detail: [ROS 2 stack](project/ros2/README.md).

### 2.3 Video and CI

- FPV video into ROS as `/image_raw` at about 25 Hz ([FPV guide](FPV_Video_Receiver_Setup_UVC_Receiver_to_ROS.md)).
- CI builds and tests the ROS workspace on every push and pull request.

## 3. Decisions

| Decision | Choice |
| --- | --- |
| ALL 1.1: control rates | Control loop 50 Hz (minimum 20 Hz), bridge watchdog 200 ms |
| ALL 1.2: transport to the drone | TCP for now: reliability and easy debugging while configuring INAV. Later settled for good: esp-link's UDP needs client code that INAV can't run |
| Command timeout | 0.3 s, three intervals at 10 Hz (Sprint 0 used 0.5 s) |

## 4. Carried Over

- An `inav` backend in `fc_bridge`, so ROS can read and command the real drone (done Nov 16–17).
- Wi-Fi latency measured properly (done Nov 12).
- A rangefinder for the real drone: the MicoAir MTF-02P was chosen.
- Perception on `/image_raw`.

# Tags

#sprints
