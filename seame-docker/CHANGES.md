# Changes: Oct 26–29, 2026

What changed in the drone sim stack while working through steps 1–4 of [PLAN.md](PLAN.md), and why.

| Step | Summary |
| --- | --- |
| 1 | Automated tests for the failsafes (`fc_bridge` and `radio_teleop`), and the Python test suite running again |
| 2 | Gazebo's model cache survives recreating the container; the arm switch bounce measured and debounced |
| 3 | State comes back through `fc_bridge`, shaped like INAV with an optical flow sensor and a rangefinder |
| 4 | A `mission` node flies takeoff, hold, circle, yaw and landing on its own, with height from the rangefinder |

## After pulling

The image changed (a new apt package, a new volume). On the host, in `seame-docker/`:

```bash
docker compose build && docker compose up -d
```

Then, inside the container:

```bash
cd ~/ros2_ws && colcon build && colcon test --packages-select drone_fc_bridge drone_basics_py drone_mission && colcon test-result --verbose
```

Expected: `57 tests, 0 errors, 0 failures, 2 skipped` with `drone_mission` included. The skipped ones are the templates' copyright checks.

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

## Docs updated

- `README.md`: `fc_bridge` section (state topics and parameters), bridge table, `radio_teleop` debounce, a **Tests** section, known issues and the resolved list.
- `seame-docker/SIM_TELEOP.md`: changes table, diagram, topic tables, the bounce check how-to and result, known issues.
- `README.md` (Oct 29): new `mission` section, launch table, known issues, Tests table.
- `SIM_TELEOP.md` (Oct 29): `source:=mission` how-to and result.
- `PLAN.md`: steps 1–4 marked done; steps 3 and 4 rewritten around optical flow + rangefinder.
