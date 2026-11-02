# Plan: fixing the known issues

Oct 26, 2026. Built from the "Known issues and limitations" table in [README.md](README.md) and the known issues in [SIM_TELEOP.md](SIM_TELEOP.md). Already resolved, so not listed here: the NaN guard, the matching timeouts, odometry in ROS and the velocity-frame check (body frame, Oct 22).

After each step, update the README and `SIM_TELEOP.md` tables so they stay accurate.

**Assumption (Oct 28):** the real drone gets a rangefinder next to the ThoneFlow-3901. The decision isn't ours to make, but INAV only uses optical flow while it has a valid rangefinder reading, so without one most of steps 4–7 doesn't work indoors.

| # | Step | Status |
| --- | --- | --- |
| 1 | Tests for the existing failsafes | Done, Oct 26 |
| 2 | Small fixes: `~/.gz` cache, arm switch bounce | Done, Oct 26 (cache seen working Oct 29) |
| 3 | State through `fc_bridge`, shaped like INAV with optical flow + rangefinder | Done, Oct 27 |
| 4 | `mission` node v1: takeoff, hold and land on the rangefinder | Done, Oct 29 |
| 5 | `drone_interfaces`, and `mission` as an action server | Done, Oct 29 |
| 6 | `safety_manager`: arbitration and hover | Done, Oct 30 |
| 7 | Prepare `fc_bridge` for hardware | Done, Oct 30 |
| 8 | Later or watch | Later |

## 1. Tests for the existing failsafes

- **What:** `launch_testing` tests for `fc_bridge`:
  - the 0.3 s timeout leads to zero velocity;
  - a NaN setpoint is dropped and the timeout takes over;
  - the horizontal clamp keeps the direction, and z and yaw are clamped;
  - the arm switch in `radio_teleop`.
- **Why first:** every later step touches the command path, and today a regression would only show up by hand.
- **Done when:** `colcon test` passes, and breaking the timeout makes a test fail.

## 2. Small fixes

- **`~/.gz` cache:** mount it in `compose.yaml` so the drone models survive recreating the container.
- **Arm switch bounce:** first confirm it's real with `jstest`. If it is, add a short debounce parameter to `radio_teleop` and a test for it.

## 3. State through `fc_bridge`, shaped like INAV with optical flow + rangefinder

Revised Oct 27. The real drone will get a ThoneFlow-3901 (PMW3901 optical flow, UART, read by INAV's `CXOF` driver) plus a rangefinder still to be chosen. INAV fuses them on the flight controller and runs POSHOLD; ROS only sees what INAV reports. So the sim should report the same kind of state, with the same limits, and not the perfect pose Gazebo knows. The X3 model has no IMU sensor, so `fc/imu` waits until `safety_manager` needs it.

- **Route state through `fc_bridge`:** `gz_bridge.yaml` bridges Gazebo's odometry to an internal `/X3/odom` instead of `/fc/odom`. The sim backend of `fc_bridge` subscribes to it and publishes the `fc/*` state topics. This closes the "`/fc/odom` published by the bridge" issue and gives the `inav` backend the same shape.
- **`fc/odom`** (`nav_msgs/Odometry`), what INAV would estimate:
  - velocity: the sim's body-frame velocity plus noise (`flow_vel_noise`);
  - horizontal position: **integrated from that velocity**, plus a slowly wandering bias (`flow_drift`), starting at 0, 0. Not Gazebo's true x, y: flow only ever gives relative position, and it drifts;
  - height and orientation: from the sim.
- **`fc/attitude`** (`geometry_msgs/QuaternionStamped`): orientation from the sim.
- **`fc/range`** (`sensor_msgs/Range`), the rangefinder. New in the contract:
  - distance along the body's down axis, so it reads longer when tilted;
  - noise `range_noise`; limits `range_min` and `range_max` (VL53L1X-like defaults, 0.04 to 4.0 m);
  - out of range: `+inf` above `range_max`, `-inf` below `range_min` (REP 117).
- **Tests:** fake `/X3/odom` in, check `fc/odom`, `fc/attitude` and `fc/range` out. With the noise parameters set to 0: velocity passes through; xy position comes from integration, not from the sim pose; range is z on the level, 2z at 60° tilt, and `±inf` out of range.
- **Done when:** the tests pass and, in the sim, `fc/odom` xy slowly drifts away from Gazebo's true position while `fc/range` follows the height.

## 4. `mission` node, version 1: takeoff, hold and land on the rangefinder

- **What:** a new node with a state machine: `idle → takeoff → hold → pattern (circle) → land → done`.
  - **Height comes from `fc/range`**, the rangefinder, like INAV's SURFACE mode. Not from `fc/odom` z.
  - Takeoff climbs until `fc/range` reports the target height. The target must stay below `range_max`.
  - Altitude hold: a proportional controller on the measured range, which fixes the drift of about 1 cm every 6 s and the drop during yaw.
  - Landing descends slowly until the range reaches the ground value and stops changing, then sends zero.
  - **Horizontal moves are relative** ("1 m forward from here"), using `fc/odom` velocity and position only over short distances, because flow position drifts.
  - **Range lost** (`±inf`, or no message): stop and hold, then land.
- **Replaces:** `setpoint_pub` as `source:=mission`. The old `circle` source stays for comparison.
- **Fixes three issues:** timed takeoff, never landing, and height drift.
- **Done when:**
  - it reaches 1.2 m ± 5 cm on `fc/range`;
  - it holds height through a full circle and a yaw;
  - it lands and disarms;
  - losing the range makes it hold and land;
  - there are tests for the state transitions.

**Open questions for the team, before the `inav` backend (step 7):** which rangefinder; which flight controller and whether its INAV build has `CXOF`; whether the ThoneFlow is the UART version (3901U); which MSP messages carry INAV's flow-based velocity and position.

## 5. `drone_interfaces` package, and `mission` as an action server

- **What:** custom `FcStatus` message, `Takeoff`/`Land`/`Goto` actions, and `fc/arm` and `fc/hold` services.
- **Then:** `mission` exposes these actions instead of running a fixed script.
- **As built (Oct 29):**
  - `drone_interfaces`: `FcStatus`, and the `Takeoff`, `Land`, `Goto` actions. `fc/arm` and `fc/hold` use the standard `std_srvs/SetBool`, so no custom services.
  - `fc_bridge`: `fc/arm` (drives the sim enable topic; starts armed), `fc/hold` (zero whatever arrives), `fc/status` (1 Hz and on change).
  - `mission`: one goal at a time, hold between goals. `Goto` is relative to the drone's position and heading when it starts, because flow position drifts. Land preempts anything and can't be cancelled. Disarms after Land.
  - `demo_flight`: takeoff, a 1 m square, land; started by `source:=mission` unless `demo:=false`.

## 6. `safety_manager`, grown out of the watchdog

- **What:** command arbitration, so the mission and the radio no longer have to take turns through `source:=`:
  - the radio overrides the mission when the sticks move or the switch is engaged;
  - hover on timeout;
  - a placeholder hook for low battery.
- **Removes:** the "one commander at a time" limitation.
- **Done when:** you can take over a running mission with the sticks, and tests cover the override.
- **As built (Oct 30):**
  - `drone_safety` package, `safety_manager` node: the only publisher of `/fc/setpoint_velocity`. Sources publish on `/cmd/radio`, `/cmd/manual`, `/cmd/mission`; the highest-priority one publishing in the last 0.3 s wins, forwarded with no added delay. Active source latched on `safety/active_source`.
  - The radio takes over by being engaged (arm switch on), since `radio_teleop` only publishes then.
  - Oct 30, after the first Pocket test: a separate takeover switch (arm and takeover both on to fly), and taking over arms `fc_bridge`, so the radio flies after a Land. On the Pocket: axis 6, −1 when on.
  - `mission`: new state `overridden`. Losing control aborts the goal; getting it back never resumes or climbs: holds where it is, or stays grounded.
  - Hover on timeout stays with `fc_bridge` (zero velocity); low battery only warns, since nothing publishes `fc/battery` yet.
  - `sim.launch.py`: the radio always runs, next to any source, like the real drone (`source:=joy` and `radio:=` removed the same day); the watchdog is replaced. Tested with the real Pocket on Oct 30: takeover mid-Goto, release to hold, and re-arming after a Land.

## 7. Prepare `fc_bridge` for hardware

Without writing the `inav` backend yet.

- **`backend` parameter:** add `backend` (`sim` | `mock`) and `contract_version`. The `/X3/enable` publisher runs only when the backend is `sim`.
- **Message timestamp:** check how old `header.stamp` is (a `max_setpoint_latency_s` parameter) and log the measured latency.
- **State:** the `inav` backend publishes `fc/odom`, `fc/attitude` and `fc/range` from MSP, like the sim backend does since step 3. Measure the real sensors' noise and drift and update the sim parameters to match.
- **Mock backend:** lets the tests from step 1 run without Gazebo.
- **Fixes:** the three "before hardware" issues in `fc_bridge`.

- **As built (Oct 30):** decided with João:
  - **ROS runs on the ground laptop, never on the drone**: `fc_bridge` talks MSP to INAV through the ESP8266. So the Wi-Fi hop is *after* `fc_bridge`, and checking `header.stamp` would only measure ROS on the laptop. Dropped; latency belongs in the `inav` backend (time each MSP request and reply, STK-5).
  - **No mock backend:** the step 1 tests already run without Gazebo, and staying close to the real drone matters more than a fake FC.
  - **No `contract_version`:** nothing would read it yet.
  - **`backend` parameter** in `fc_bridge`, `sim` or `inav`. `inav` is a stub: same topics and services, sends nothing, publishes no state, refuses `fc/arm`, and has no Gazebo topics or enable. 3 launch tests (`test_inav.py`).
  - **The sim arms like the hardware:** only the radio arms. SA arms and disarms through `fc/arm` (kill switch, even in flight); like INAV, not with the throttle off centre or on a switch already on at start. The takeover switch, not SA, hands over the sticks, and no longer arms. `mission` (`radio_arms` true) refuses Takeoff until armed, never arms or disarms, and a disarm in the air aborts its goal and grounds it.
  - **`radio:=false`** for when someone else has the Pocket: no radio nodes, `fc_bridge` starts armed, and `mission` arms on Takeoff and disarms after Land, as before.
  - **`backend:=inav`** in `sim.launch.py`: no Gazebo, no bridge, no radio nodes, no sim time. The launch is now one `OpaqueFunction`, so each argument is a plain Python choice.
  - Not done here: measuring the real sensors (needs the hardware) and the MSP code itself.

## 8. Later or watch

- **Later:** per-drone namespaces (Module 3), and aligning tf frame names (`base_link` vs `x3/base_footprint`) when tf comes in.
- **Watch:** the one-off timeout right after the first setpoint. Act if it comes back while setpoints are flowing.
