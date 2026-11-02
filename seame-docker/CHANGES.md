# Changes: Oct 26–30, 2026

What changed in the drone sim stack while working through steps 1–6 of [PLAN.md](PLAN.md), and why.

| Step | Summary |
| --- | --- |
| 1 | Automated tests for the failsafes (`fc_bridge` and `radio_teleop`), and the Python test suite running again |
| 2 | Gazebo's model cache survives recreating the container; the arm switch bounce measured and debounced |
| 3 | State comes back through `fc_bridge`, shaped like INAV with an optical flow sensor and a rangefinder |
| 4 | A `mission` node flies takeoff, hold, circle, yaw and landing on its own, with height from the rangefinder |
| 5 | `mission` takes `Takeoff`, `Goto` and `Land` actions; `fc_bridge` gets `fc/arm`, `fc/hold` and `fc/status` |
| 6 | `safety_manager` picks which source commands the drone; the radio takes over a running mission |

## After pulling

The image changed (a new apt package, a new volume). On the host, in `seame-docker/`:

```bash
docker compose build && docker compose up -d
```

Then, inside the container:

```bash
cd ~/ros2_ws && colcon build && colcon test --packages-select drone_fc_bridge drone_basics_py drone_mission drone_safety && colcon test-result --verbose
```

Expected: `98 tests, 0 errors, 0 failures, 3 skipped` with `drone_mission` included. The skipped ones are the templates' copyright checks.

## Step 1: tests for the failsafes

**Purpose:** `fc_bridge` is the only thing between a bad command and the drone, and the arm switch is the deadman. Both were only checked by hand, so a later change (mission node, `safety_manager`, `inav` backend) could break them without anyone noticing.

| File | Change | Why |
| --- | --- | --- |
| `drone_fc_bridge/test/test_failsafes.py` | New. 9 `launch_testing` tests: starts the real `fc_bridge` alone (no Gazebo) and plays both the commander and Gazebo | Proves: zero with no setpoints; fresh setpoints pass; zero within 0.3 s (± 0.15) of the last setpoint and not before; NaN and infinity rejected and timed out; horizontal clamp keeps direction; z and yaw clamped; roll and pitch rates zeroed; sim enable published |
| `drone_fc_bridge/CMakeLists.txt` | Registers the launch tests, on ROS domain 199, localhost only | So `colcon test` runs them, and a sim running on the team's domain can't interfere |
| `drone_fc_bridge/package.xml` | `test_depend` entries | So `rosdep` installs what the tests need on a fresh machine |
| `drone_basics_py/test/test_radio_teleop.py` | New. Plain pytest: calls `on_joy` directly with fake `Joy` messages and records what would be published | Proves the arm switch logic: switch off publishes nothing; engage refused with throttle off centre, also on re-engage; stick scaling, signs and deadband |
| `Dockerfile` | Adds `ros-jazzy-ament-mypy` | The package's template `test_mypy.py` crashed on import, which stopped **all** `drone_basics_py` tests from running, including flake8 and pep257 |
| `radio_teleop.py`, `setpoint_pub.py` | Import order, docstring layout, final newline. No behaviour change | Once the suite ran again, flake8 and pep257 failed on these. Fixed so the suite is green and a real failure stands out |

**Checked:** with the timeout check in `fc_bridge` deliberately broken, the timeout, NaN and infinity tests fail.

## Step 2: small fixes

### Gazebo model cache

**Purpose:** Gazebo downloads the X3 and X4 models (about 117 MB) into `~/.gz` the first time. That folder lived inside the container, so recreating the container lost them, and the world wouldn't load without internet.

| File | Change | Why |
| --- | --- | --- |
| `compose.yaml` | Named volume `gz-cache` mounted on `/home/dev/.gz` | Docker keeps a named volume when the container is removed (only `docker compose down -v` deletes it) |
| `Dockerfile` | `mkdir -p ~/.gz` as the `dev` user | An empty named volume takes the ownership of the folder in the image. Without it the volume would belong to root and Gazebo couldn't write to it |

**Not yet seen working:** the first sim launch after the rebuild downloads the models once more into the volume; after that they should survive `docker compose up -d --force-recreate`.

### Arm switch bounce

**Purpose:** one burst of fast on/off flips had been seen in `jstest`. Confirm it before changing the deadman.

| File | Change | Why |
| --- | --- | --- |
| `ros2_ws/tools/arm_bounce.py` | New. Logs every arm switch change on `/joy` with the time since the previous one, flags changes under 300 ms, prints a total. Warns every 3 s while no `/joy` arrives | To measure the bounce |
| `radio_teleop.py` | New parameter `arm_hold_s` (0.1 s): the switch must read on, without a break, that long before it engages. **Off still acts at once** | Measured Oct 26: bursts of up to about 10 flips 0–35 ms apart, mostly on a slow arm; deliberate fast flicks are 100 ms or more apart. Only arming waits, so the deadman never gets slower; a flicker to off while flying disengages, which is the safe direction |
| `drone_bringup/config/sim.yaml` | `arm_hold_s: 0.1` | Visible and tunable with the other radio settings |
| `test_radio_teleop.py` | Now 14 tests, every `Joy` stamped; new: no engage before the hold, a bounce burst never engages, the hold counts from the last bounce, off is immediate, a bounce while disarming doesn't re-engage | Locks the debounce in |

**Checked:** with the debounce disabled, 7 tests fail. **Not yet checked:** arming with the real radio in the sim (`source:=joy`), which should log one `Engaged` per arm.

**Limitation:** the debounce relies on `joy_node` repeating its last state (`autorepeat_rate`, 20 Hz in `sim.yaml`). With repeats off, a switch held still sends no next message and never engages.

## Step 3: state through `fc_bridge`

**Purpose:** the real drone will get a ThoneFlow-3901 (PMW3901 optical flow over UART, read by INAV's `CXOF` driver) and, ideally, a rangefinder. INAV fuses them on the flight controller and runs POSHOLD; ROS only sees what INAV reports. Gazebo's odometry is perfect ground truth, which the real drone will never have. So the sim now reports state of the same kind and with the same limits, and code above `fc_bridge` can't come to rely on what the real drone won't give it. It also puts commands and state on one path through `fc_bridge`, the shape the `inav` backend needs.

| File | Change | Why |
| --- | --- | --- |
| `drone_bringup/config/gz_bridge.yaml` | Gazebo odometry now bridged to the internal `/X3/odom`, not `/fc/odom` | `/fc/odom` belongs to `fc_bridge`. Closes the "`/fc/odom` published by the bridge" known issue |
| `drone_fc_bridge/src/fc_bridge.cpp` | The sim backend subscribes to `/X3/odom` and publishes `fc/odom`, `fc/attitude`, `fc/range` | See below |
| `drone_fc_bridge/CMakeLists.txt`, `package.xml` | `nav_msgs`, `sensor_msgs`; second launch test | New message types and tests |
| `drone_fc_bridge/test/test_state.py` | New. 7 `launch_testing` tests with noise off, fake `/X3/odom` in | Proves: velocity passes through; xy integrated, not copied from the sim; body velocity rotated by heading; height and attitude from the sim; range is z when level, 2z at 60° roll, `±inf` out of range or upside down |
| `ros2_ws/tools/odom_yaw.py` | Optional topic argument | `odom_yaw.py /X3/odom` shows the true pose; without it, `fc/odom` |

What `fc_bridge` publishes now, per sim odometry message (50 Hz):

| Topic | Content | Like the real drone because |
| --- | --- | --- |
| `fc/odom` | Body-frame velocity with noise (`flow_vel_noise` 0.02 m/s) and a random-walk bias (`flow_drift` 0.002 m/s per √s). xy **integrated** from it, starting at 0, 0. z and orientation from the sim | Optical flow measures velocity, not position, and integrating it drifts |
| `fc/attitude` | Orientation | INAV always reports attitude |
| `fc/range` | Distance along the body's down axis, noise 0.005 m, limits 0.04–4.0 m (VL53L1X-like). `+inf` above, `-inf` below (REP 117) | A downward rangefinder reads longer when tilted and has a range |

**Checked:** with `fc/odom` deliberately copying Gazebo's x, the integration test fails. In the headless sim with the circle flight, `fc/odom` traced the same circle while drifting about 0.5 m from the truth over a minute, and `fc/range` followed the height.

**Found, now in the README's known issues:**

- On the ground the range reads about 0.05 m (the model origin is 6 cm up), just above `range_min`, so it sometimes reads `-inf`. `mission` must treat that as landed, not as a lost sensor.
- `fc/odom` xy drifts even while landed; INAV ignores flow when landed.
- Noise, drift and limits are guesses until measured on the real sensors.
- The X3 model has no IMU sensor, so `fc/imu` is postponed until `safety_manager` needs it.

## Step 4: the `mission` node

**Purpose:** `setpoint_pub` climbed for a fixed time, never landed, and let the height sag. The first real autonomy should take off to a measured height, hold it, and land by itself, using only what the real drone will have: the rangefinder for height, and velocity commands that INAV in POSHOLD can follow. It assumes a rangefinder will be fitted (see PLAN.md).

| File | Change | Why |
| --- | --- | --- |
| `ros2_ws/src/drone_mission/` | New `ament_python` package: `logic.py` (the state machine, plain Python), `mission.py` (the ROS node), and the template lint tests (flake8, pep257, mypy, xmllint) | A package of its own, since `drone_basics_py` is the crash course. The logic has no ROS in it so whole flights can be tested in milliseconds |
| `drone_mission/drone_mission/logic.py` | Phases `wait → takeoff → hold → circle → yaw → land → done`, plus `range_lost`. Height = range × tilt; `-inf` = ground. P controller on height in every airborne phase. Touchdown from the range, or from "commanding down, not moving down". Range lost: hover, resume if it returns within 2 s, otherwise land blind. Takeoff timeout lands | Each behaviour in the plan's "done when" |
| `drone_mission/test/test_logic.py` | 15 tests against a toy drone (height follows commanded vz, range 0.04–4 m) | See the README Tests table |
| `drone_bringup/launch/sim.launch.py` | `source:=mission` | `circle` stays for comparison |
| `drone_bringup/config/sim.yaml` | `mission` parameters | Visible and tunable with the rest |
| `drone_bringup/package.xml` | `exec_depend` on `drone_mission` | The launch file starts it |

**Checked:**

- With altitude hold switched off, 9 tests fail; with the "not moving down" touchdown switched off, the blind-landing test fails.
- In headless Gazebo (Oct 29): takeoff to 1.24 m peak, settled at 1.20 m; 1.197–1.203 m through the circle and a full turn; landed and went quiet after about 42 s of sim time.
- The `gz-cache` volume works: the models loaded from it after the container was recreated.

**Found, now in the README's known issues:** a 4 cm takeoff overshoot; a rangefinder failing as `-inf` in the air would read as the ground; nothing disarms after landing (on hardware, that stays on the radio for now).

**Running the sim headless needs X access:** Gazebo's sensors system wants OpenGL even with `-s`, and in the container that only works through the X display. If Gazebo dies with exit code 139 and `Authorization required` in the log, run `DISPLAY=:0 xhost +local:` on the host.

## Step 5: interfaces and actions

**Purpose:** step 4's mission was a fixed script. Missions should be requested from outside, step by step, and refused when unsafe, which is what ROS actions are for: a goal, feedback while it runs, a result, and cancelling. `fc_bridge` also needed a way to report its state and to be told to arm, disarm or freeze.

| File | Change | Why |
| --- | --- | --- |
| `ros2_ws/src/drone_interfaces/` | New `ament_cmake` interface package: `msg/FcStatus.msg`; `action/Takeoff.action`, `Land.action`, `Goto.action` | One place for the stack's custom types. Arm and hold use `std_srvs/SetBool` instead of new types |
| `drone_fc_bridge/src/fc_bridge.cpp` | `fc/arm` (armed state drives the sim enable topic; `armed_at_start` true), `fc/hold` (zero while on), `fc/status` | So the mission can arm and disarm, anything can freeze the drone, and everyone can see `fc_bridge`'s state |
| `drone_fc_bridge/test/test_services.py` | New launch test, 4 tests | Locks those in |
| `drone_mission/drone_mission/logic.py` | Rewritten for goals: `grounded → takeoff → hold ⇄ goto → land → grounded`, plus `range_lost`. Relative `Goto` with heading. Accept/refuse rules; cancel; Land preempts | See the README `mission` section |
| `drone_mission/drone_mission/mission.py` | Three action servers on a multi-threaded executor, a lock around the logic, arms on Takeoff and disarms after Land, handles SIGINT/SIGTERM itself | rclpy's default handler made the multi-threaded executor die with an `RCLError` at Ctrl-C |
| `drone_mission/drone_mission/demo_flight.py` | New scripted client: takeoff, 1 m square, land | Replaces v1's fixed flight as the demo |
| `drone_mission/test/test_logic.py` | Rewritten: 31 tests, the toy drone now moves in x, y, yaw | See the README Tests table |
| `drone_bringup/launch/sim.launch.py` | `demo` argument; `demo_flight` with `source:=mission` | Server alone with `demo:=false`, to send goals by hand |
| `drone_bringup/config/sim.yaml` | New `mission` parameters, `demo_flight` section | |

**Checked:**

- With `Goto`'s world velocity sent without turning it into the body frame, the heading and square tests fail; with Land not preempting, the preemption test fails.
- In headless Gazebo (Oct 29): the demo's every goal succeeded; 1.19–1.22 m through eight Goto goals; true square sides 0.82–0.91 m; back within 0.09 m of the start; disarmed after landing; `mission` shuts down cleanly on Ctrl-C.

**Fixed after a manual run (Oct 29):**

- A second launch did nothing: a Gazebo server from the previous run was stuck at startup, so there was no `/clock`. And with no clock, `mission` ignored Ctrl-C for 15 s until launch killed it, because its own signal handler only ran when the node woke up. It now keeps rclpy's signal handling (which wakes it anyway) and catches the error that handling causes in a multi-threaded executor; running goals stop waiting at shutdown. Checked: clean exit with no clock, during a Goto, and after the demo.
- Takeoff could be accepted on the first rangefinder reading while the sim was still starting, then abort as `rangefinder lost` and go to `hold` on the ground with a 1.2 m target, which would climb with no goal. Now Takeoff needs `ready_s` (1 s) of readings without a gap, and recovering from `range_lost` never climbs on its own. `demo_flight` now lands after a failed Takeoff too. 4 new tests; all fail with the old behaviour.
- Checked: two demos in a row in headless Gazebo, both complete.

**Found, now in the README's known issues:** Goto ends short of the target (tolerance plus drift); one goal at a time with no queue; ROS can arm the sim drone, which must not carry over to hardware; an automatic landing doesn't disarm (accepted for now).

## Step 6: `safety_manager`

**Purpose:** until now exactly one source could run (`source:=`), so a pilot couldn't take over a running mission without restarting the launch. On the real drone that takeover is the main safety feature. Now every source publishes on its own topic and one node decides who reaches `fc_bridge`.

| File | Change | Why |
| --- | --- | --- |
| `ros2_ws/src/drone_safety/` | New `ament_python` package: `arbiter.py` (the rule, plain Python), `safety_manager.py` (the node), lint tests | The rule tested on its own, like `mission` |
| `drone_safety/drone_safety/arbiter.py` | Highest-priority source that published in the last `source_timeout_s` wins: radio > manual > mission | A radio that is engaged always wins; a quiet source hands control back by itself |
| `drone_safety/drone_safety/safety_manager.py` | The only publisher of `/fc/setpoint_velocity`; forwards the active source's commands as they arrive; latches `safety/active_source`; logs changes; low-battery warning placeholder | Replaces the watchdog in the sim |
| `drone_safety/test/test_arbiter.py` | 9 tests | See the README Tests table |
| `drone_mission/drone_mission/logic.py`, `mission.py` | State `overridden`: losing control aborts the goal and goes quiet, goals refused; control back holds where it is or stays grounded. The node listens to `safety/active_source` | The mission must not fight the pilot, nor resume a goal from a place the pilot moved it to |
| `drone_mission/test/test_logic.py` | 6 more tests (37) | |
| `drone_bringup/launch/sim.launch.py` | Sources remapped to `/cmd/mission` and `/cmd/radio`; `safety_manager` instead of the watchdog; **the radio always runs**; `source` is now `circle`, `mission` or `none` | The real drone never flies without the radio as a backup, so neither does the sim. `source:=joy` is gone (use `source:=none` to fly with the radio alone) and fails loudly; `radio:=` is gone and ignored |
| `drone_bringup/config/sim.yaml`, `package.xml` | `safety_manager` parameters instead of the watchdog's; depends on `drone_safety` | |

**Checked:**

- With the priority order reversed, the arbiter tests fail; the 6 override tests cover the mission side.
- In headless Gazebo (Oct 30), with `ros2 topic pub` on `/cmd/radio` as the radio: the radio took over during a 3 m Goto, which aborted with `overridden by radio`; the drone went from 1.20 m to 0.28 m under "radio" control; afterwards `mission` held at about 0.33 m and landed on request.
- With the Pocket unplugged, `joy_node` waits quietly and the demo completes; five Ctrl-Cs in a row, every node exits cleanly.
- With the real Pocket (Oct 30, SIM_TELEOP section 1c): takeover mid-Goto, release to hold, re-arm and fly after a Land. Works.

**Found, now in the README's known issues:** `mission`'s 20 Hz commands paused for over 0.3 s twice while a `ros2` CLI started (CPU load), so `fc_bridge` sent zero for a moment; once in 11 Ctrl-Cs `mission` didn't exit within 15 s, not reproduced since.

**Shutdown race fixed in every Python node:** with the radio nodes always running, `radio_teleop` (and once `safety_manager`) died at Ctrl-C with the same `RCLError` `mission` had: rclpy's handler can close the context between two waits. `safety_manager`, `radio_teleop`, `setpoint_pub` and `demo_flight` now treat it as a normal shutdown.

**Launch guard (Oct 30):** the first Pocket test flickered. The cause was two Gazebo sims, not the radio. A launch run before `drone_safety` was sourced started Gazebo and only then failed on the missing package, leaving that Gazebo running without its launch. The next launch started a second one in the same partition, and `fc_bridge` read both drones' odometry and range in turn. `sim.launch.py` now checks every package it needs before starting anything, and refuses to start while another `gz sim` runs in the same `GZ_PARTITION`. Checked in the container: with `drone_safety` hidden, the launch fails and leaves no Gazebo behind; a second launch next to a running one is refused; a normal launch still starts.

**Takeover switch and re-arming (Oct 30):** in the first Pocket test the radio couldn't fly after a Land: the Land disarms `fc_bridge`, which then ignored the sticks until a Takeoff goal armed it again. And with one switch for both arming and taking over, the radio couldn't be armed and ready without grabbing control. `radio_teleop` now has a second switch, `axis_takeover`: the sticks command only while arm **and** takeover are on, and engaging calls `fc/arm`. On the real drone this matches INAV: the radio arms, and a mode switch chooses between the companion (MSP) and the sticks. On the Pocket it's the shoulder switch opposite SA: `/joy` axis 6, −1 when on (`axis_takeover: 6`, `sign_takeover: -1.0` in `sim.yaml`). 7 more tests in `test_radio_teleop.py` (21); with the `fc/arm` call removed, 2 of them fail. In headless Gazebo with a fake `/joy`: Takeoff, Land (disarmed at 0.05 m), takeover → `Armed (fc/arm)`, climbed to 1.0 m, released → `mission` held at 0.94 m.

**Changed for anyone publishing by hand:** publish on `/cmd/manual`, not `/fc/setpoint_velocity`. The keyboard command in SIM_TELEOP is updated.

## Step 7: `fc_bridge` ready for the real drone, and the sim arms like it

**Purpose:** on the real drone ROS runs on the ground laptop and talks MSP to INAV through the ESP8266; only the radio arms, and nothing sim-only may ever reach it. Switching between Gazebo and the drone must be one launch argument (issue ROS-4).

| File | Change | Why |
| --- | --- | --- |
| `drone_fc_bridge/src/fc_bridge.cpp` | `backend` parameter, `sim` or `inav` (anything else stops the node). `inav`: stub, same topics and services, sends nothing, refuses `fc/arm`, no Gazebo topics, no enable; `fc/status` reports the backend | The shape of the real backend, with no way for ROS to arm the drone or a sim topic to leak |
| `drone_fc_bridge/test/test_inav.py` | 3 launch tests: status says `inav` and disarmed; `fc/arm` refused; nothing and nobody on the Gazebo topics | |
| `drone_basics_py/drone_basics_py/radio_teleop.py` | SA arms and disarms through `fc/arm`: off is the kill switch, even in flight. Like INAV: not with the throttle off centre, and not on a switch already on at start. Takeover no longer arms | On the real drone only the radio arms |
| `drone_mission/drone_mission/logic.py`, `mission.py` | `radio_arms` (default true): Takeoff needs the drone armed, the node never arms or disarms. Listens to `fc/status`: armed to disarmed in the air aborts the goal (`disarmed`) and grounds it. `disarm_after_land` removed | Matches the real drone; with `radio_arms` false the old behaviour stays |
| `drone_mission/drone_mission/demo_flight.py` | Retries Takeoff for 2 minutes, not 30 s | Time to arm with the radio |
| `drone_bringup/launch/sim.launch.py` | `backend:=sim\|inav`; `radio:=true\|false` (false: no radio nodes, `fc_bridge` starts armed, `mission` arms itself). Rebuilt around one `OpaqueFunction` | Sim to real is one argument; testing without the Pocket when someone else has it |
| Tests | 6 more mission logic tests (43), radio tests reworked for arming (24) | |

**Dropped from the plan, and why:** a `header.stamp` age check (the Wi-Fi hop is after `fc_bridge`, so it would only measure ROS on the laptop; latency goes in the `inav` backend), the mock backend (the step 1 tests already run without Gazebo), `contract_version` (nothing reads it).

**Checked:**

- Each new guard broken on purpose fails a test: the Takeoff arming check (2 fail), the disarm-in-the-air abort (1), SA off not disarming (2), no off-at-start check (1), `inav` accepting `fc/arm` (3).
- Headless Gazebo, fake Pocket (`radio:=true`): Takeoff refused (`not armed`); SA on armed it; Takeoff to 1.0 m; SA off in the air: disarmed, dropped to 0.05 m, `mission` `hold -> grounded`.
- `radio:=false`: the demo flew by itself (eight Gotos, Land, disarmed); no radio nodes started.
- `backend:=inav`: no Gazebo started; `fc/status` `inav`, disarmed; `fc/arm` refused; Takeoff refused (`not armed`).
- All tests pass except the 4 older lint failures (`basics.launch.py`, `watchdog.cpp`).

**Changed for everyone:** the drone starts disarmed. Arm with SA (throttle centred), or launch with `radio:=false`.

## Docs updated

- `README.md`: `fc_bridge` section (state topics and parameters), bridge table, `radio_teleop` debounce, a **Tests** section, known issues and the resolved list.
- `seame-docker/SIM_TELEOP.md`: changes table, diagram, topic tables, the bounce check how-to and result, known issues.
- `README.md` (Oct 29): new `mission` section, launch table, known issues, Tests table.
- `SIM_TELEOP.md` (Oct 29): `source:=mission` how-to and result.
- `PLAN.md`: steps 1–4 marked done; steps 3 and 4 rewritten around optical flow + rangefinder.
