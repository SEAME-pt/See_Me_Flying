# Nodes Information: Drone Sim Stack

Oct 20, 2026 · @Someone · updated Oct 23, 2026

For setup, see [`seame-docker/GUIDE.md`](seame-docker/GUIDE.md). To fly the sim with the keyboard or the RadioMaster Pocket, and for the parameters, failsafes and test results, see [`seame-docker/SIM_TELEOP.md`](seame-docker/SIM_TELEOP.md).

## System overview

This is what runs today in the simulation, as started by `ros2 launch drone_bringup sim.launch.py source:=circle|joy|none`. The `source` argument chooses who commands the drone (default `circle`); exactly one source runs at a time. Acronyms are spelled out the first time they appear.

&#91;embedded content: sim stack · 4 hops for setpoints, clock back to fc\_bridge\]

Setpoints travel one way: the source (`setpoint_pub`, `radio_teleop` or the keyboard) → `fc_bridge` → `ros_gz_bridge` → Gazebo. Simulation time travels back through the same bridge on `/clock`, and every ROS (Robot Operating System) node runs on it because the launch sets `use_sim_time: true`. The watchdog only listens; it changes nothing in the chain.

| Process | Language | Package | Started by |
| --- | --- | --- | --- |
| Gazebo (`gz sim`) | C++ (not a ROS node) | `ros_gz_sim` (apt) | `sim.launch.py` |
| `parameter_bridge` | C++ | `ros_gz_bridge` (apt) | `sim.launch.py` |
| `fc_bridge` | C++ | `drone_fc_bridge` (ours) | `sim.launch.py` |
| `watchdog` | C++ | `drone_basics_cpp` (ours) | `sim.launch.py` |
| `setpoint_pub` | Python | `drone_basics_py` (ours) | `sim.launch.py source:=circle`, 5 s after the rest |
| `joy_node` | C++ | `joy` (apt) | `sim.launch.py source:=joy` |
| `radio_teleop` | Python | `drone_basics_py` (ours) | `sim.launch.py source:=joy` |
| `teleop_twist_keyboard` | Python | `teleop_twist_keyboard` (apt) | By hand, with `source:=none` |

All our nodes read their parameters from `drone_bringup/config/sim.yaml`; the values in the tables below are the ones in that file.

## setpoint\_pub

A test source of velocity commands, standing in for the future `mission` node. Package `drone_basics_py`, file `drone_basics_py/setpoint_pub.py`.

**What it does, in order**

1. Waits for its first timer tick, then records that moment as time zero. With sim time this is when Gazebo's clock starts arriving, not when the process started.
2. **Takeoff phase** (first `takeoff_s` seconds): publishes straight-up velocity `z = climb_speed`, no horizontal motion. Logs `Phase: takeoff`.
3. **Circle phase** (after that): publishes a horizontal velocity of constant size `speed` whose direction turns at 0.5 rad/s, so the drone flies a circle of radius `speed / 0.5` (0.6 m at the default). `z = 0`, so it holds its height. Logs `Phase: circle`.
4. Keeps publishing at `rate_hz` until stopped. It never lands.

| Item | Value |
| --- | --- |
| Publishes | `setpoint_velocity` (`geometry_msgs/TwistStamped`, frame `base_link`), remapped to `/fc/setpoint_velocity` by the launch file |
| QoS (Quality of Service) | Reliable, depth 10 |
| `rate_hz` | 10.0 Hz (read once at start) |
| `speed` | 0.3 m/s (read every tick, so `ros2 param set` changes it live) |
| `takeoff_s` | 4.0 s of sim time |
| `climb_speed` | 0.3 m/s, so about 1.2 m of climb |

All times are on the node clock, so with `use_sim_time` a slow simulation still climbs the full height; it just takes longer in real seconds.

## watchdog

An observer that reports when setpoints stop arriving. It is the seed of the future `safety_manager`. Package `drone_basics_cpp`, file `src/watchdog.cpp`.

**What it does**

1. On startup, sets "last message received" to now.
2. Every time a setpoint arrives, updates "last message received".
3. Every 100 ms, checks how long ago that was. When the gap first exceeds `timeout_s`, logs `No setpoint for X s: a real failsafe would command hover`. When messages come back, logs `Setpoints are back`. It only logs on these changes, never every tick.

It **commands nothing**. The drone's actual failsafe is in `fc_bridge`; the watchdog only tells you it happened. The warning right after launch is expected: `setpoint_pub` starts 5 s later.

| Item | Value |
| --- | --- |
| Subscribes | `setpoint_velocity` (`geometry_msgs/TwistStamped`), remapped to `/fc/setpoint_velocity` by the launch file |
| QoS | Sensor-data profile (best effort, small queue); connects to reliable and best-effort publishers |
| `timeout_s` | 0.3 s, equal to `fc_bridge`'s `setpoint_timeout_s` (code default 0.5) |
| Check period | 100 ms, fixed in code |

## fc\_bridge

The only node allowed to command the drone. Today it has one backend, `sim`; the `inav` backend for the real FC (flight controller) comes later behind the same topics. Package `drone_fc_bridge`, file `src/fc_bridge.cpp`.

**What it does**

1. **Receives** setpoints on `fc/setpoint_velocity` and stores the latest one with the time it arrived. The message's own header timestamp is not used. A setpoint with NaN (Not a Number) or infinity in any field is dropped with a warning (at most once a second) and not stored, so the previous one keeps ageing and the timeout takes over.
2. **Ticks** at `rate_hz` (20 Hz). Each tick it decides whether the stored setpoint is fresh: it arrived no more than `setpoint_timeout_s` ago, and not in the "future" (which happens when sim time is reset).
3. **Fresh:** clamps it and publishes it to Gazebo.
4. **Stale or none yet:** publishes zero velocity. Gazebo's controller keeps following the last command it received, so this explicit zero is what makes the drone stop and hover. That is the failsafe.
5. **Logs** only on changes: `Setpoints received, following them` and `Setpoint timeout: holding (zero velocity)`. It starts stale, so it publishes zeros and logs nothing until the first setpoint.
6. **Keeps the sim drone enabled** by publishing `true` on the enable topic once a second. Sim only: on the real drone, arming stays on the radio.
7. **Reports state** for every Gazebo odometry message on `/X3/odom` (50 Hz), shaped like what INAV will report with the ThoneFlow-3901 optical flow sensor and a rangefinder, not like the perfect pose Gazebo knows:
   - `fc/odom`: velocity in the body frame with noise and a slowly wandering bias, like optical flow. **Horizontal position is integrated from that velocity** and starts at 0, 0, so it drifts (about 0.5 m per minute with the defaults) and never matches Gazebo's x, y. Height and orientation come from the sim. Frames `odom` → `base_link`.
   - `fc/attitude`: the orientation alone.
   - `fc/range`: a downward rangefinder. Reads distance along the body's down axis, so longer when tilted; `+inf` above `range_max`, `-inf` below `range_min` (REP 117). About 0.05 m with the drone on the ground.

**The clamp**, applied to every command before it leaves:

- Horizontal: if the speed `hypot(x, y)` is above `max_speed_xy`, both components are scaled down together, so direction is kept and only the speed is capped.
- Vertical: `z` is limited to ±`max_speed_z`.
- Yaw: `angular.z` is limited to ±`max_yaw_rate`.
- Roll and pitch rates (`angular.x`, `angular.y`) are always sent as zero.

| Item | Value |
| --- | --- |
| Subscribes | `fc/setpoint_velocity` (`geometry_msgs/TwistStamped`), sensor-data QoS |
| Subscribes | `sim_odom_topic` (`nav_msgs/Odometry`), sensor-data QoS |
| Publishes | `gz_twist_topic` (`geometry_msgs/Twist`) every tick; `gz_enable_topic` (`std_msgs/Bool`) every 1 s; `fc/odom` (`nav_msgs/Odometry`), `fc/attitude` (`geometry_msgs/QuaternionStamped`) and `fc/range` (`sensor_msgs/Range`) per sim odometry message |
| `gz_twist_topic` | `/X3/gazebo/command/twist` |
| `gz_enable_topic` | `/X3/enable` |
| `rate_hz` | 20.0 (read once at start) |
| `setpoint_timeout_s` | 0.3 s |
| `max_speed_xy` | 0.5 m/s |
| `max_speed_z` | 0.3 m/s |
| `max_yaw_rate` | 1.0 rad/s |
| `sim_odom_topic` | `/X3/odom` (read once at start) |
| `flow_vel_noise` | 0.02 m/s, white noise on velocity |
| `flow_drift` | 0.002 m/s per √s, random walk of the velocity bias |
| `range_noise` | 0.005 m |
| `range_min`, `range_max` | 0.04 m, 4.0 m (VL53L1X-like; change when the team picks a rangefinder) |

Timeout and clamp limits are read every tick, so `ros2 param set` changes them live. All parameters are doubles: set them as `2.0`, not `2`. The code still declares every parameter with a default; `sim.yaml` only overrides the value. Removing a declaration makes the node crash the first time it reads that parameter.

The clamp limits are safety caps meant for the real airframe. Tune stick feel in `radio_teleop` (`max_xy`, `max_z`, `max_yaw`), not here.

## radio\_teleop

Turns the RadioMaster Pocket, connected over USB as a joystick, into velocity setpoints. **Sim only**: on the real drone the radio talks ELRS (ExpressLRS) straight to INAV and never goes through ROS. Package `drone_basics_py`, file `drone_basics_py/radio_teleop.py`.

**What it does, for every `/joy` message** (`joy_node` repeats the last state at 20 Hz):

1. Reads the arm switch. If it is off: publishes nothing, so `fc_bridge` times out and holds. Logs `Arm switch off` once.
2. If the switch has just been turned on, waits until it has read on without a break for `arm_hold_s` (debounce: the Pocket's switch bounces). Then refuses to engage until the throttle stick is centred, like a real arming check. Logs `Centre the throttle stick to engage` every 2 s.
3. Once engaged: applies sign and deadband to each stick and publishes `TwistStamped` (frame `base_link`). Right stick: forward/back and strafe. Left stick: up/down and yaw.

| Item | Value |
| --- | --- |
| Subscribes | `joy` (`sensor_msgs/Joy`) |
| Publishes | `setpoint_velocity` (`geometry_msgs/TwistStamped`), remapped to `/fc/setpoint_velocity` |
| Axes | roll 0, pitch 1, throttle 2, yaw 3, arm 4 |
| Signs | roll 1.0, pitch −1.0, throttle −1.0, yaw 1.0, arm −1.0 (`joy_node` inverts every Pocket axis) |
| `arm_hold_s` | 0.1 s; off still acts at once |
| `deadband` | 0.08 |
| `max_xy`, `max_z`, `max_yaw` | 0.5 m/s, 0.3 m/s, 1.0 rad/s at full stick |

`joy_node` opens the radio by name (`device_name: "OpenTX Radiomaster Pocket Joystick"`), so a laptop accelerometer or another gamepad can't be picked by mistake.

## ros\_gz\_bridge and Gazebo

**`parameter_bridge`** (package `ros_gz_bridge`, installed with apt) is a translator. Gazebo has its own message system (`gz topic`), separate from ROS, and the bridge copies messages between the two for exactly the topics it is told about:

| Topic | Direction | ROS type | Gazebo type |
| --- | --- | --- | --- |
| `/X3/gazebo/command/twist` | ROS → Gazebo | `geometry_msgs/Twist` | `gz.msgs.Twist` |
| `/X3/enable` | ROS → Gazebo | `std_msgs/Bool` | `gz.msgs.Boolean` |
| `/clock` | Gazebo → ROS | `rosgraph_msgs/Clock` | `gz.msgs.Clock` |
| `/model/x3/odometry` → `/X3/odom` | Gazebo → ROS | `nav_msgs/Odometry` | `gz.msgs.Odometry` |

The list lives in `drone_bringup/config/gz_bridge.yaml`, which the bridge reads through its `config_file` parameter. In YAML the ROS and Gazebo names can differ. Odometry lands on the internal `/X3/odom`, Gazebo's true pose; `fc_bridge` turns it into the contract topics `fc/odom`, `fc/attitude` and `fc/range`. Note the **lowercase** `x3` in the Gazebo odometry topic, unlike the command topics.

`/X3/odom` arrives at 50 Hz with `frame_id: x3/odom` and `child_frame_id: x3/base_footprint`; covariances are all zero; the twist is in the body frame. Nothing above `fc_bridge` should read it: it is ground truth the real drone won't have. Any topic not listed does not cross. The X3 model has no IMU (inertial measurement unit) sensor, so there is none to bridge.

**Gazebo** (`gz sim`, Gazebo Harmonic) is not a ROS node. It loads the world `multicopter_velocity_control.sdf` (SDF: Simulation Description Format) running from the start (`-r`). The world holds two quadcopters, X3 and X4; only X3 is used. X3 has a built-in velocity controller: given a Twist, it works out the motor speeds to reach that velocity and holds it until the next command. Underneath, the physics is real: per-rotor motor models (thrust, rotor drag, spin-up), gravity and collisions. The controller reads commands in the **body frame** (verified Oct 22, 2026: forward follows the nose to within 1°). It accepts commands only while enabled. Our stack never touches the X4 or the `motor_speed` topic, which drives the propellers directly.

## Launch files

Both live in `drone_bringup/launch/` and are installed by the `install(DIRECTORY launch config ...)` line in that package's `CMakeLists.txt`. A new launch file only becomes visible to `ros2 launch` after `colcon build`.

**`sim.launch.py`: the simulation with a choice of commander**

| Argument | Values | Default |
| --- | --- | --- |
| `source` | `circle`, `joy`, `none` (anything else is rejected) | `circle` |
| `world` | SDF file name or full path | `multicopter_velocity_control.sdf` |

1. Always, at once: Gazebo, `parameter_bridge` (with `config/gz_bridge.yaml`), `fc_bridge` and `watchdog`. ROS launch gives no ordering between them; that is fine, because `fc_bridge` simply sits frozen until `/clock` arrives.
2. `source:=circle`: after 5 s of wall time, `setpoint_pub` (takeoff, then circles).
3. `source:=joy`: `joy_node` and `radio_teleop`.
4. `source:=none`: nothing commands the drone; use it when running a source by hand, such as the keyboard.
5. All our nodes get `config/sim.yaml` and `use_sim_time: true`. Every source is remapped from `setpoint_velocity` to `/fc/setpoint_velocity`.
6. Ctrl-C stops everything together.

**`basics.launch.py`: the crash-course exercise**

Starts `setpoint_pub` and `watchdog` only, with settings from `config/basics.yaml` (`rate_hz` 20, `speed` 0.3, `timeout_s` 0.3) and a `use_sim_time` launch argument (default `false`). No Gazebo and no `fc_bridge`; nothing flies. Its topic is `/setpoint_velocity`, not the contract topic.

## Known issues and limitations

None of these stop the simulation from working today. The priority says when each must be fixed: **before hardware** means before the `inav` backend ever commands a real motor.

| Issue | Where | What can go wrong | Fix | Priority |
| --- | --- | --- | --- | --- |
| Sim-only enable published forever | `fc_bridge` | Harmless in sim; on hardware it would be ROS arming the drone | The `inav` backend must not have it. Arming stays on the radio | Before hardware |
| Message timestamp ignored | `fc_bridge` | Age is measured from arrival, so a setpoint delayed in the Wi-Fi link still counts as fresh | Also check `header.stamp` age once the real link exists, and log the measured latency | Before hardware |
| No IMU in the sim | X3 model | No `fc/imu`; nothing needs it yet | Own world and model copy with an IMU sensor when `safety_manager` needs it | Later |
| Flow position drifts while landed | `fc_bridge` | Sitting on the ground, `fc/odom` xy still drifts; INAV ignores flow when landed | Stop integrating below `range_min` if it gets in the way | Watch |
| Rangefinder on the ground reads about 0.05 m | `fc_bridge` sim backend | Just above `range_min` (0.04), so with noise it sometimes reads `-inf` | `mission` must treat `-inf` near the ground as landed, not as a lost sensor | Next |
| Sensor model is a guess | `fc_bridge` sim backend | Noise, drift and range limits are not measured on our hardware | Measure with the real ThoneFlow and rangefinder; update the parameters | Before hardware |
| Velocity-only control: height drifts | X3 controller | Holds zero vertical speed, not a height: drifts down about 1 cm every 6 s and loses about 15 cm in a yaw; takeoff reaches about 1.0 m, not 1.2 | Altitude hold from `fc/range` in `mission` | Next |
| One commander at a time | `sim.launch.py` | `source:=` can't let a mission and a human share control | Command arbitration in `safety_manager` | Next |
| Radio-as-joystick needs RF off | Pocket | A transmitting radio could command a bench drone | Always use the `INAV-SIM` model copy with Internal RF off | Always |
| Frame names differ | `fc_bridge`, Gazebo | Commands say `base_link`, the sim says `x3/base_footprint`; harmless until tf is used | Align when tf is introduced | Later |
| Takeoff is timed, not measured | `setpoint_pub` | Climbs for a fixed time with no height feedback; the real height depends on the controller | Move takeoff to the `mission` node, climbing until odometry reports the target height | Next |
| Never lands | `setpoint_pub` | The flight only ends by stopping the launch | Landing phase in `mission` | Next |
| One-off timeout right after the first setpoint | `fc_bridge` | Seen once at startup: `received`, then `timeout` 14 ms later, then fine | Watch for it; if it repeats while setpoints flow, sim time is jumping and the timeout needs a margin | Watch |
| Topics fixed to the X3, no namespace | all nodes | Fine for one drone; two drones would clash | Namespaces per drone when multi-agent work starts (Module 3) | Later |

The 5 s start delay of `setpoint_pub` is wall time, which could look risky on a slow machine. It is safe: `setpoint_pub` runs on sim time, so its timer does not tick and its takeoff clock does not start until Gazebo's clock arrives.

**Resolved since Oct 20, 2026:** NaN passing through the clamp (now rejected in `fc_bridge`), the watchdog and `fc_bridge` timeouts disagreeing (both 0.3 s from `sim.yaml`), no odometry in ROS (`/fc/odom`), and the unverified velocity frame (body frame confirmed). Since Oct 26: failsafes tested by hand only (now automated, see below), drone models lost when the container is recreated (now in the `gz-cache` volume), and the arm switch bounce (confirmed with `tools/arm_bounce.py`, debounced by `arm_hold_s` in `radio_teleop`). Since Oct 27: `/fc/odom` published by the bridge instead of `fc_bridge`, and no attitude topic (`fc_bridge` now publishes `fc/odom`, `fc/attitude` and `fc/range`).

## Tests

The failsafes have automated tests. Run them inside the container:

```bash
cd ~/ros2_ws && colcon build && colcon test --packages-select drone_fc_bridge drone_basics_py && colcon test-result --verbose
```

| Test file | What it checks |
| --- | --- |
| `drone_fc_bridge/test/test_failsafes.py` | `launch_testing`: starts `fc_bridge` alone on the wall clock. Zero with no setpoints; fresh setpoints forwarded; zero within 0.3 s (± 0.15) of the last setpoint; NaN and infinity rejected and timed out; horizontal clamp keeps direction; z and yaw clamped; roll and pitch rates zeroed; sim enable published. Runs on its own domain (199, localhost only), so a running sim does not interfere. |
| `drone_fc_bridge/test/test_state.py` | `launch_testing`: `fc_bridge` with noise off, fed fake `/X3/odom`. Velocity passes through; xy position is integrated, not copied from the sim; body velocity is rotated by heading; height and attitude from the sim; range is z when level, 2z at 60° roll, `±inf` out of range or upside down. |
| `drone_basics_py/test/test_radio_teleop.py` | pytest, no launch: switch off publishes nothing; engage refused with throttle off centre; re-engage needs the throttle centred again; a bounce while arming or disarming never engages; off is immediate; stick scaling, signs and deadband. |

Breaking the timeout check in `fc_bridge` makes three tests fail (checked Oct 26, 2026).

## Not built yet

What the fc\_bridge interface contract asks for that does not exist today. The first group is the next step.

| Item | Kind | Notes |
| --- | --- | --- |
| `fc/imu` | Topic out, `sensor_msgs/Imu` | The X3 model has no IMU sensor; needs our own world and model copy |
| `fc/battery`, `fc/status` | Topics out | `fc/status` needs the custom `FcStatus` message |
| `drone_interfaces` | Package | Holds `FcStatus` and any other custom messages and services |
| `fc/arm`, `fc/hold` | Services | `fc/arm` refused on hardware; `fc/hold` sends zero |
| `backend` and `contract_version` | `fc_bridge` parameters | `backend` selects `sim`, `inav` or `mock` |
| `inav` backend | `fc_bridge` code | MSP (MultiWii Serial Protocol) over the ESP8266 Wi-Fi link: TCP (Transmission Control Protocol) for bring-up, UDP (User Datagram Protocol) before flight |
| `safety_manager` | Node | Grows out of the watchdog: hover on timeout, return on low battery |
| `mission` | Node | Takeoff, waypoints and landing as an action server; replaces `setpoint_pub` |
