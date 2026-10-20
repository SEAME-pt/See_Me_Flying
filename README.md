# Nodes Information: Drone Sim Stack

Oct 20, 2026 · @Someone

## System overview

This is what runs today in the simulation, as started by `ros2 launch drone_bringup sim.launch.py`. Acronyms are spelled out the first time they appear.

&#91;embedded content: sim stack · 4 hops for setpoints, clock back to fc\_bridge\]

Setpoints travel one way: `setpoint_pub` → `fc_bridge` → `ros_gz_bridge` → Gazebo. Simulation time travels back through the same bridge on `/clock`, and every ROS (Robot Operating System) node runs on it because the launch sets `use_sim_time: true`. The watchdog only listens; it changes nothing in the chain.

| Process | Language | Package | Started by |
| --- | --- | --- | --- |
| Gazebo (`gz sim`) | C++ (not a ROS node) | `ros_gz_sim` (apt) | `sim.launch.py` |
| `parameter_bridge` | C++ | `ros_gz_bridge` (apt) | `sim.launch.py` |
| `fc_bridge` | C++ | `drone_fc_bridge` (ours) | `sim.launch.py` |
| `watchdog` | C++ | `drone_basics_cpp` (ours) | `sim.launch.py` |
| `setpoint_pub` | Python | `drone_basics_py` (ours) | `sim.launch.py`, 5 s after the rest |

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
| `timeout_s` | 0.5 s (default; the launch file does not override it) |
| Check period | 100 ms, fixed in code |

## fc\_bridge

The only node allowed to command the drone. Today it has one backend, `sim`; the `inav` backend for the real FC (flight controller) comes later behind the same topics. Package `drone_fc_bridge`, file `src/fc_bridge.cpp`.

**What it does**

1. **Receives** setpoints on `fc/setpoint_velocity` and stores the latest one with the time it arrived. The message's own header timestamp is not used.
2. **Ticks** at `rate_hz` (20 Hz). Each tick it decides whether the stored setpoint is fresh: it arrived no more than `setpoint_timeout_s` ago, and not in the "future" (which happens when sim time is reset).
3. **Fresh:** clamps it and publishes it to Gazebo.
4. **Stale or none yet:** publishes zero velocity. Gazebo's controller keeps following the last command it received, so this explicit zero is what makes the drone stop and hover. That is the failsafe.
5. **Logs** only on changes: `Setpoints received, following them` and `Setpoint timeout: holding (zero velocity)`. It starts stale, so it publishes zeros and logs nothing until the first setpoint.
6. **Keeps the sim drone enabled** by publishing `true` on the enable topic once a second. Sim only: on the real drone, arming stays on the radio.

**The clamp**, applied to every command before it leaves:

- Horizontal: if the speed `hypot(x, y)` is above `max_speed_xy`, both components are scaled down together, so direction is kept and only the speed is capped.
- Vertical: `z` is limited to ±`max_speed_z`.
- Yaw: `angular.z` is limited to ±`max_yaw_rate`.
- Roll and pitch rates (`angular.x`, `angular.y`) are always sent as zero.

| Item | Value |
| --- | --- |
| Subscribes | `fc/setpoint_velocity` (`geometry_msgs/TwistStamped`), sensor-data QoS |
| Publishes | `gz_twist_topic` (`geometry_msgs/Twist`) every tick; `gz_enable_topic` (`std_msgs/Bool`) every 1 s |
| `gz_twist_topic` | `/X3/gazebo/command/twist` |
| `gz_enable_topic` | `/X3/enable` |
| `rate_hz` | 20.0 (read once at start) |
| `setpoint_timeout_s` | 0.3 s |
| `max_speed_xy` | 0.5 m/s |
| `max_speed_z` | 0.3 m/s |
| `max_yaw_rate` | 1.0 rad/s |

Timeout and clamp limits are read every tick, so `ros2 param set` changes them live. All parameters are doubles: set them as `2.0`, not `2`.

## ros\_gz\_bridge and Gazebo

**`parameter_bridge`** (package `ros_gz_bridge`, installed with apt) is a translator. Gazebo has its own message system (`gz topic`), separate from ROS, and the bridge copies messages between the two for exactly the topics it is told about:

| Topic | Direction | ROS type | Gazebo type |
| --- | --- | --- | --- |
| `/X3/gazebo/command/twist` | ROS → Gazebo | `geometry_msgs/Twist` | `gz.msgs.Twist` |
| `/X3/enable` | ROS → Gazebo | `std_msgs/Bool` | `gz.msgs.Boolean` |
| `/clock` | Gazebo → ROS | `rosgraph_msgs/Clock` | `gz.msgs.Clock` |

In the bridge arguments, `]` means ROS → Gazebo and `[` means Gazebo → ROS. Any topic not listed does not cross: the drone's pose, IMU (inertial measurement unit) and odometry exist in Gazebo but are not visible in ROS yet.

**Gazebo** (`gz sim`, Gazebo Harmonic) is not a ROS node. It loads the world `multicopter_velocity_control.sdf` (SDF: Simulation Description Format) running from the start (`-r`). The world holds two quadcopters, X3 and X4; only X3 is used. X3 has a built-in velocity controller: given a Twist, it works out the motor speeds to reach that velocity and holds it until the next command. It accepts commands only while enabled. Our stack never touches the X4 or the `motor_speed` topic, which drives the propellers directly.

## Launch files

Both live in `drone_bringup/launch/` and are installed by the `install(DIRECTORY launch config ...)` line in that package's `CMakeLists.txt`. A new launch file only becomes visible to `ros2 launch` after `colcon build`.

**`sim.launch.py`: the whole first flight in one command**

1. At once: Gazebo, `parameter_bridge`, `fc_bridge` and `watchdog`. ROS launch gives no ordering between them; that is fine, because `fc_bridge` simply sits frozen until `/clock` arrives.
2. After 5 s of wall time: `setpoint_pub` (takeoff, then circles).
3. All our nodes get `use_sim_time: true`. `watchdog` and `setpoint_pub` are remapped from `setpoint_velocity` to `/fc/setpoint_velocity`.
4. Ctrl-C stops everything together.

**`basics.launch.py`: the crash-course exercise**

Starts `setpoint_pub` and `watchdog` only, with settings from `config/basics.yaml` (`rate_hz` 20, `speed` 0.3, `timeout_s` 0.3) and a `use_sim_time` launch argument (default `false`). No Gazebo and no `fc_bridge`; nothing flies. Its topic is `/setpoint_velocity`, not the contract topic.

## Known issues and limitations

None of these stop the simulation from working today. The priority says when each must be fixed: **before hardware** means before the `inav` backend ever commands a real motor.

| Issue | Where | What can go wrong | Fix | Priority |
| --- | --- | --- | --- | --- |
| NaN (Not a Number) or infinite values pass through the clamp | `fc_bridge` | Comparisons with NaN are always false, so the scale stays 1 and the NaN is forwarded to the drone | Check every field with `std::isfinite`; on failure, treat the setpoint as stale (send zero) and log a warning | Before hardware |
| Sim-only enable published forever | `fc_bridge` | Harmless in sim; on hardware it would be ROS arming the drone | The `inav` backend must not have it. Arming stays on the radio | Before hardware |
| Message timestamp ignored | `fc_bridge` | Age is measured from arrival, so a setpoint delayed in the Wi-Fi link still counts as fresh | Also check `header.stamp` age once the real link exists, and log the measured latency | Before hardware |
| No state comes back from the sim | bridge config | Height, position and attitude are invisible in ROS, so nothing can be checked or closed in a loop | Bridge pose, IMU and odometry onto `fc/odom`, `fc/imu`, `fc/attitude` (contract doc) | Next |
| Takeoff is timed, not measured | `setpoint_pub` | Climbs for a fixed time with no height feedback; the real height depends on the controller | Move takeoff to the `mission` node, climbing until odometry reports the target height | Next |
| Never lands | `setpoint_pub` | The flight only ends by stopping the launch | Landing phase in `mission` | Next |
| Velocity frame not verified | `setpoint_pub`, `fc_bridge` | Commands are labelled `base_link` (body frame); if the X3 controller reads them in the world frame instead, behaviour differs once the drone yaws | Check with odometry: command +x, yaw the drone, see which way it moves | Next |
| Timeouts disagree | `watchdog` 0.5 s vs `fc_bridge` 0.3 s | The watchdog warns after `fc_bridge` has already stopped the drone | Load both from one YAML parameter file | Later |
| One-off timeout right after the first setpoint | `fc_bridge` | Seen once at startup: `received`, then `timeout` 14 ms later, then fine | Watch for it; if it repeats while setpoints flow, sim time is jumping and the timeout needs a margin | Watch |
| Topics fixed to the X3, no namespace | all nodes | Fine for one drone; two drones would clash | Namespaces per drone when multi-agent work starts (Module 3) | Later |
| Drone models downloaded into the container | Gazebo | Lost when the container is recreated; the world will not load without internet | Mount `~/.gz` as a cache folder in `compose.yaml` | Later |

The 5 s start delay of `setpoint_pub` is wall time, which could look risky on a slow machine. It is safe: `setpoint_pub` runs on sim time, so its timer does not tick and its takeoff clock does not start until Gazebo's clock arrives.

## Not built yet

What the fc\_bridge interface contract asks for that does not exist today. The first group is the next step.

| Item | Kind | Notes |
| --- | --- | --- |
| `fc/odom` | Topic out, `nav_msgs/Odometry` | From Gazebo's odometry, bridged; needed for height and position |
| `fc/imu` | Topic out, `sensor_msgs/Imu` | From the X3's IMU sensor, bridged |
| `fc/attitude` | Topic out, `geometry_msgs/QuaternionStamped` | From the pose or odometry |
| `fc/battery`, `fc/status` | Topics out | `fc/status` needs the custom `FcStatus` message |
| `drone_interfaces` | Package | Holds `FcStatus` and any other custom messages and services |
| `fc/arm`, `fc/hold` | Services | `fc/arm` refused on hardware; `fc/hold` sends zero |
| `backend` and `contract_version` | `fc_bridge` parameters | `backend` selects `sim`, `inav` or `mock` |
| `inav` backend | `fc_bridge` code | MSP (MultiWii Serial Protocol) over the ESP8266 Wi-Fi link: TCP (Transmission Control Protocol) for bring-up, UDP (User Datagram Protocol) before flight |
| `safety_manager` | Node | Grows out of the watchdog: hover on timeout, return on low battery |
| `mission` | Node | Takeoff, waypoints and landing as an action server; replaces `setpoint_pub` |
