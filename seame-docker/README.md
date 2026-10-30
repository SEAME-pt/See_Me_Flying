# Nodes Information: Drone Sim Stack

Oct 20, 2026 · @Someone · updated Oct 23, 2026

For setup, see [`GUIDE.md`](GUIDE.md). To fly the sim with the keyboard or the RadioMaster Pocket, and for the parameters, failsafes and test results, see [`SIM_TELEOP.md`](SIM_TELEOP.md).

## System overview

This is what runs today in the simulation, as started by `ros2 launch drone_bringup sim.launch.py source:=circle|mission|none`. The `source` argument chooses what flies the drone on its own (default `circle`). The RadioMaster Pocket is **always** there as the override, like on the real drone: engaged, it takes over from any source. Acronyms are spelled out the first time they appear.

&#91;embedded content: sim stack · 4 hops for setpoints, clock back to fc\_bridge\]

Setpoints travel one way: the sources (`mission` or `setpoint_pub`, `radio_teleop`, the keyboard) → `safety_manager`, which picks one → `fc_bridge` → `ros_gz_bridge` → Gazebo. Simulation time travels back through the same bridge on `/clock`, and every ROS (Robot Operating System) node runs on it because the launch sets `use_sim_time: true`. Since Oct 30 the sources no longer publish to `fc_bridge` directly: see `safety_manager`.

| Process | Language | Package | Started by |
| --- | --- | --- | --- |
| Gazebo (`gz sim`) | C++ (not a ROS node) | `ros_gz_sim` (apt) | `sim.launch.py` |
| `parameter_bridge` | C++ | `ros_gz_bridge` (apt) | `sim.launch.py` |
| `fc_bridge` | C++ | `drone_fc_bridge` (ours) | `sim.launch.py` |
| `safety_manager` | Python | `drone_safety` (ours) | `sim.launch.py` |
| `setpoint_pub` | Python | `drone_basics_py` (ours) | `sim.launch.py source:=circle`, 5 s after the rest |
| `mission` | Python | `drone_mission` (ours) | `sim.launch.py source:=mission` |
| `demo_flight` | Python | `drone_mission` (ours) | `sim.launch.py source:=mission` (unless `demo:=false`) |
| `joy_node` | C++ | `joy` (apt) | `sim.launch.py`, always |
| `radio_teleop` | Python | `drone_basics_py` (ours) | `sim.launch.py`, always |
| `teleop_twist_keyboard` | Python | `teleop_twist_keyboard` (apt) | By hand, with `source:=none` |

All our nodes read their parameters from `drone_bringup/config/sim.yaml`; the values in the tables below are the ones in that file.

## setpoint\_pub

A test source of velocity commands: takeoff for a fixed time, then circles forever. Kept for comparison; `mission` does the same flight properly. Package `drone_basics_py`, file `drone_basics_py/setpoint_pub.py`.

**What it does, in order**

1. Waits for its first timer tick, then records that moment as time zero. With sim time this is when Gazebo's clock starts arriving, not when the process started.
2. **Takeoff phase** (first `takeoff_s` seconds): publishes straight-up velocity `z = climb_speed`, no horizontal motion. Logs `Phase: takeoff`.
3. **Circle phase** (after that): publishes a horizontal velocity of constant size `speed` whose direction turns at 0.5 rad/s, so the drone flies a circle of radius `speed / 0.5` (0.6 m at the default). `z = 0`, so it holds its height. Logs `Phase: circle`.
4. Keeps publishing at `rate_hz` until stopped. It never lands.

| Item | Value |
| --- | --- |
| Publishes | `setpoint_velocity` (`geometry_msgs/TwistStamped`, frame `base_link`), remapped to `/cmd/mission` by the launch file |
| QoS (Quality of Service) | Reliable, depth 10 |
| `rate_hz` | 10.0 Hz (read once at start) |
| `speed` | 0.3 m/s (read every tick, so `ros2 param set` changes it live) |
| `takeoff_s` | 4.0 s of sim time |
| `climb_speed` | 0.3 m/s, so about 1.2 m of climb |

All times are on the node clock, so with `use_sim_time` a slow simulation still climbs the full height; it just takes longer in real seconds.

## mission

Flies on request: three action servers, `mission/takeoff`, `mission/goto` and `mission/land`, with height from the rangefinder (`fc/range`), like INAV's SURFACE mode. One goal at a time; between goals in the air it holds height. Package `drone_mission`: the flight logic is plain Python in `drone_mission/logic.py` (no ROS, so it can be tested on its own); `drone_mission/mission.py` is the ROS node around it; `drone_mission/demo_flight.py` is a scripted client. The action types are in `drone_interfaces`.

**States:** `grounded → takeoff → hold ⇄ goto → land → grounded`, plus `range_lost`. On the ground it publishes nothing; in the air it publishes at `rate_hz` in every state, so `fc_bridge` never times out between goals.

| Action | Goal | Accepted when | Ends |
| --- | --- | --- | --- |
| `Takeoff` | `height` (0 = `target_h`) | On the ground, with rangefinder readings arriving for `ready_s` without a gap, below the rangefinder's `max_range`, and **armed**: by the radio (`radio_arms`, like the real drone), or, with `radio_arms` false, it arms first (`fc/arm`) | Within `tolerance` of the height: hold. Not there after `takeoff_timeout_s`: aborted, and it lands |
| `Goto` | `forward`, `left` (m), `yaw` (rad), `speed` (0 = `speed`) | Holding, with no other goal, with `fc/odom` | Within `pos_tolerance` and `yaw_tolerance`: hold. Aborted when odometry stops or after twice the ideal time plus `goto_margin_s` |
| `Land` | none | Whenever it's in the air. Aborts any other goal | Touchdown: grounded. Disarms only with `radio_arms` false; otherwise the pilot disarms with the radio |

`Takeoff` and `Goto` can be cancelled (it holds where it is); `Land` can't. A rejected goal logs why: `takeoff rejected: rangefinder not steady yet`, `takeoff rejected: not armed: arm with the radio`.

**Disarmed in the air** (`fc/status` goes from armed to disarmed: the radio's arm switch is the kill switch): the goal is aborted (`disarmed`) and it goes straight to **grounded**, silent. Only a change counts, so a status sent just before its own arm request landed can't abort a Takeoff.

**Goto is relative:** `forward` and `left` are in the heading the drone has when the goal starts, measured with `fc/odom`. Optical flow position drifts, so this is good for a few metres, not for coming back to an absolute spot. It flies towards the target at up to `speed` (slower within 1/`kp_xy` m of it), turns at up to `yaw_rate`, and holds height.

**Height:** `fc/range` × the world z of the body z axis (from `fc/odom`'s orientation), so tilt doesn't inflate it. `-inf` (below the sensor's minimum) counts as 0, the ground. In every airborne state, `vz = kp_z × (target − height)`, limited to ±`max_vz`; this corrects the X3 controller's sag.

**Touchdown,** either of: height below `ground_h` for `touchdown_s`; or, after 1.5 s in **land**, commanding down but not moving down (`fc/odom` z velocity above −0.03 m/s) for `touchdown_s`. The second works with no rangefinder at all.

**Range lost** (no message for `range_timeout_s`, or `+inf`) while flying: the goal is aborted (`rangefinder lost`) and it hovers in **range_lost**. If the range comes back within `lost_hold_s` it never climbs on its own: on the ground it goes back to **grounded**; after an interrupted Takeoff it holds the height it reached; otherwise it holds as before. If the range doesn't come back, it lands blind (touchdown from odometry). A `Land` goal sent then attaches to that landing.

**Ctrl-C:** the node runs a multi-threaded executor (actions block while they run). It keeps rclpy's signal handling, which wakes it even with no `/clock` and no messages, and catches the error that handling causes in that executor; running goals stop waiting, so it exits within a second or two. It may print one `The following exception was never retrieved: ...` line on the way out: rclpy's action server reporting on its own parts after they are destroyed. Harmless.

| Item | Value |
| --- | --- |
| Subscribes | `fc/range` (`sensor_msgs/Range`), `fc/odom` (`nav_msgs/Odometry`), `fc/status` (`drone_interfaces/FcStatus`, for armed) |
| Publishes | `setpoint_velocity` (`geometry_msgs/TwistStamped`, frame `base_link`) at `rate_hz` (20), remapped to `/cmd/mission` |
| Subscribes (control) | `safety/active_source` (`std_msgs/String`): not `mission` or `none` means overridden |
| Actions | `mission/takeoff`, `mission/goto`, `mission/land` (`drone_interfaces/action/...`) |
| Calls | `fc/arm` (`std_srvs/SetBool`), only with `radio_arms` false: true on Takeoff, false after a Land |
| `target_h`, `tolerance` | 1.2 m, 0.05 m |
| `kp_z`, `max_vz` | 1.0 (m/s)/m, 0.3 m/s |
| `land_speed`, `ground_h`, `touchdown_s` | 0.15 m/s, 0.12 m, 1.0 s |
| `speed`, `kp_xy`, `pos_tolerance` | 0.3 m/s, 1.0 (m/s)/m, 0.10 m |
| `yaw_rate`, `kp_yaw`, `yaw_tolerance` | 0.5 rad/s, 1.5 (rad/s)/rad, 0.05 rad |
| `goto_margin_s` | 10.0 s |
| `range_timeout_s`, `ready_s`, `odom_timeout_s`, `lost_hold_s` | 0.5 s, 1.0 s, 0.5 s, 2.0 s |
| `takeoff_timeout_s` | 20.0 s |
| `radio_arms` | true; the launch sets false with `radio:=false` |

All parameters are read once at start.

**`demo_flight`:** a client that takes off to `height` (1.2 m), flies a square of side `side` (1.0 m: forward, quarter turn left, four times), and lands. It keeps asking for Takeoff for 2 minutes, since the mission refuses it until the rangefinder is steady and the drone is armed (arm with the radio); after any failed step, including Takeoff, it skips to Land.

**Sim result (Oct 29, 2026, headless, `source:=mission`, the demo):** every goal succeeded. Height stayed 1.19–1.22 m through all eight Goto goals. In Gazebo's true pose the square's sides were 0.82–0.91 m (the Goto ends within 0.10 m, and `fc/odom` drifts), and it came back 0.09 m from where it started. Landed, then `fc_bridge` logged `Disarmed (fc/arm)`. About 45 s of sim time.

**Version 1 (Oct 29, `c50f8e9`)** ran a fixed flight (takeoff, hold, circle, yaw, land) with no actions; it settled at 1.20 m and held 1.197–1.203 m through the circle and a full turn.

## safety\_manager

Decides which command source reaches the drone. Since Oct 30 it is the **only publisher of `/fc/setpoint_velocity`**: every source publishes on its own topic, and `safety_manager` forwards one of them. Grew out of the watchdog, which only logged a timeout; the watchdog still runs in `basics.launch.py`. Package `drone_safety`: the rule is plain Python in `drone_safety/arbiter.py` (no ROS, tested on its own), `drone_safety/safety_manager.py` is the node.

| Source | Topic | Priority |
| --- | --- | --- |
| `radio_teleop` (RadioMaster Pocket) | `/cmd/radio` | 1, highest |
| Anything by hand: keyboard, `ros2 topic pub` | `/cmd/manual` | 2 |
| `mission` or `setpoint_pub` | `/cmd/mission` | 3 |

**The rule:** the highest-priority source that has published within `source_timeout_s` is active, and only its commands are forwarded, as they arrive (no added delay). With none active nothing is forwarded, so `fc_bridge`'s timeout sends zero, as before.

**Taking over:** `radio_teleop` only publishes while its arm and takeover switches are both on, so **flipping takeover on (with arm on) takes control** from the mission, and either switch off gives it back. Taking over also arms `fc_bridge`, so it works after a Land. The active source is published on `safety/active_source` (`std_msgs/String`, latched) and logged on every change: `Active source: radio`, `No source publishing: fc_bridge times out and sends zero`.

**`mission` listens to it:** when another source becomes active it aborts its goal (`overridden by radio`) and goes quiet in state **overridden**, refusing new goals. When control comes back (active is `mission` or `none`) it never resumes on its own: on the ground it goes to **grounded**, in the air it holds the height it is at. Then it takes new goals.

**Low battery:** a placeholder. It subscribes to `fc/battery` (`sensor_msgs/BatteryState`; nothing publishes it yet) and warns once below `battery_low`. Returning or landing comes later.

| Item | Value |
| --- | --- |
| Subscribes | `cmd/radio`, `cmd/manual`, `cmd/mission` (`geometry_msgs/TwistStamped`, sensor-data QoS); `fc/battery` |
| Publishes | `fc/setpoint_velocity` (`geometry_msgs/TwistStamped`); `safety/active_source` (`std_msgs/String`, transient local) |
| `priority` | `["radio", "manual", "mission"]`, highest first; each name `n` is the topic `cmd/n` |
| `source_timeout_s` | 0.3 s, equal to `fc_bridge`'s `setpoint_timeout_s` |
| `battery_low` | 0.2 (fraction) |

**Sim result (Oct 30, 2026, headless, with `ros2 topic pub` standing in for the radio):** during a 3 m Goto, commands on `/cmd/radio` took over at once; the Goto aborted with `overridden by radio`; the "radio" brought the drone from 1.20 m down to 0.28 m; when it stopped, `mission` held at about 0.33 m (no climb back) and accepted a Land.

## fc\_bridge

The only node allowed to command the drone. Parameter `backend`: `sim` (Gazebo) or `inav`, the real FC (flight controller) over MSP through the ESP8266. `inav` is a stub today: same topics and services, but it sends nothing, publishes no state, and refuses `fc/arm` (only the radio arms the real drone). It has no Gazebo topics and no enable, so nothing sim-only can reach the real drone. Any other value stops the node at start. Package `drone_fc_bridge`, file `src/fc_bridge.cpp`.

**What it does**

1. **Receives** setpoints on `fc/setpoint_velocity` and stores the latest one with the time it arrived. The message's own header timestamp is not used. A setpoint with NaN (Not a Number) or infinity in any field is dropped with a warning (at most once a second) and not stored, so the previous one keeps ageing and the timeout takes over.
2. **Ticks** at `rate_hz` (20 Hz). Each tick it decides whether the stored setpoint is fresh: it arrived no more than `setpoint_timeout_s` ago, and not in the "future" (which happens when sim time is reset).
3. **Fresh:** clamps it and publishes it to Gazebo.
4. **Stale or none yet:** publishes zero velocity. Gazebo's controller keeps following the last command it received, so this explicit zero is what makes the drone stop and hover. That is the failsafe.
5. **Logs** only on changes: `Setpoints received, following them` and `Setpoint timeout: holding (zero velocity)`. It starts stale, so it publishes zeros and logs nothing until the first setpoint.
6. **Keeps the sim drone enabled** (sim only) by publishing the armed state on the enable topic once a second and on every change. Disarmed, the X3's motors stop. `armed_at_start` is set by the launch: false with the radio (it arms), true with `radio:=false`. With `inav`, always disarmed until MSP reports otherwise.
7. **Reports state** for every Gazebo odometry message on `/X3/odom` (50 Hz), shaped like what INAV will report with the ThoneFlow-3901 optical flow sensor and a rangefinder, not like the perfect pose Gazebo knows:
   - `fc/odom`: velocity in the body frame with noise and a slowly wandering bias, like optical flow. **Horizontal position is integrated from that velocity** and starts at 0, 0, so it drifts (about 0.5 m per minute with the defaults) and never matches Gazebo's x, y. Height and orientation come from the sim. Frames `odom` → `base_link`.
   - `fc/attitude`: the orientation alone.
   - `fc/range`: a downward rangefinder. Reads distance along the body's down axis, so longer when tilted; `+inf` above `range_max`, `-inf` below `range_min` (REP 117). About 0.05 m with the drone on the ground.
8. **Services** (`std_srvs/SetBool`): `fc/arm` sets the armed state (sim only: `radio_teleop` calls it from the arm switch, or `mission` with `radio:=false`; `inav` refuses it); `fc/hold` true makes it ignore setpoints and send zero until set false. Both log the change.
9. **Status** on `fc/status` (`drone_interfaces/FcStatus`) once a second and on every change: backend, armed, holding, following setpoints, setpoint age, rangefinder valid.

**The clamp**, applied to every command before it leaves:

- Horizontal: if the speed `hypot(x, y)` is above `max_speed_xy`, both components are scaled down together, so direction is kept and only the speed is capped.
- Vertical: `z` is limited to ±`max_speed_z`.
- Yaw: `angular.z` is limited to ±`max_yaw_rate`.
- Roll and pitch rates (`angular.x`, `angular.y`) are always sent as zero.

| Item | Value |
| --- | --- |
| Subscribes | `fc/setpoint_velocity` (`geometry_msgs/TwistStamped`), sensor-data QoS |
| Subscribes | `sim_odom_topic` (`nav_msgs/Odometry`), sensor-data QoS |
| Publishes | `gz_twist_topic` (`geometry_msgs/Twist`) every tick; `gz_enable_topic` (`std_msgs/Bool`) every 1 s; `fc/odom` (`nav_msgs/Odometry`), `fc/attitude` (`geometry_msgs/QuaternionStamped`) and `fc/range` (`sensor_msgs/Range`) per sim odometry message; `fc/status` (`drone_interfaces/FcStatus`) |
| Services | `fc/arm`, `fc/hold` (`std_srvs/SetBool`) |
| `backend` | `sim` or `inav` (read once at start) |
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
| `armed_at_start` | true (read once at start; sim only; the launch sets it) |

Timeout and clamp limits are read every tick, so `ros2 param set` changes them live. All parameters are doubles: set them as `2.0`, not `2`. The code still declares every parameter with a default; `sim.yaml` only overrides the value. Removing a declaration makes the node crash the first time it reads that parameter.

The clamp limits are safety caps meant for the real airframe. Tune stick feel in `radio_teleop` (`max_xy`, `max_z`, `max_yaw`), not here.

## radio\_teleop

Turns the RadioMaster Pocket, connected over USB as a joystick, into velocity setpoints. **Sim only**: on the real drone the radio talks ELRS (ExpressLRS) straight to INAV and never goes through ROS. Package `drone_basics_py`, file `drone_basics_py/radio_teleop.py`.

**What it does, for every `/joy` message** (`joy_node` repeats the last state at 20 Hz):

1. **Arm switch (SA) arms and disarms** the drone through `fc/arm`, like INAV on the real drone. It arms once SA has read on for `arm_hold_s` without a break (the Pocket's switch bounces), and only with the throttle centred (`Centre the throttle stick to arm`). Like INAV, it won't arm on a switch that was already on when it started: flip it off and on (`Arm switch was on at start`). **SA off disarms at once, even in flight: it's the kill switch**, and the sim drone drops.
2. **Takeover switch** (`axis_takeover`, axis 6 on the Pocket; −1 means none, arm alone takes over): while armed and on for `arm_hold_s`, and with the throttle centred, the sticks take control (`Engaged`). Takeover off, or SA off, releases at once (`Released`): nothing is published, so the mission keeps control, or with none `fc_bridge` times out and holds. Armed with takeover off, the radio is ready but the mission flies.
3. On the real drone the radio arms INAV itself, and the takeover switch is INAV's mode switch between the companion (MSP) and the sticks; neither node runs there.
4. Once engaged: applies sign and deadband to each stick and publishes `TwistStamped` (frame `base_link`). Right stick: forward/back and strafe. Left stick: up/down and yaw.

| Item | Value |
| --- | --- |
| Subscribes | `joy` (`sensor_msgs/Joy`) |
| Calls | `fc/arm` (`std_srvs/SetBool`): true when SA arms, false when it goes off |
| Publishes | `setpoint_velocity` (`geometry_msgs/TwistStamped`), remapped to `/cmd/radio`: only while engaged, which is what makes the radio take over |
| Axes | roll 0, pitch 1, throttle 2, yaw 3, arm 4, takeover 6 |
| Signs | roll 1.0, pitch −1.0, throttle −1.0, yaw 1.0, arm −1.0, takeover −1.0 (`joy_node` inverts every Pocket axis) |
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

**`sim.launch.py`: the simulation (or the real drone) with a choice of commander**

| Argument | Values | Default |
| --- | --- | --- |
| `backend` | `sim`: Gazebo. `inav`: the real drone over MSP (stub: nothing is sent yet). No Gazebo, bridge, radio nodes or sim time with `inav` | `sim` |
| `source` | `circle`, `mission`, `none` (anything else is rejected, including the old `joy`) | `circle` |
| `radio` | `true`, `false`. Sim only. `false`: no Pocket (someone else has it): no radio nodes, `fc_bridge` starts armed and `mission` arms on Takeoff and disarms after Land | `true` |
| `demo` | `true`, `false`: with `source:=mission`, also run `demo_flight` | `true` |
| `world` | Sim only: SDF file name or full path | `multicopter_velocity_control.sdf` |

Everything is decided in one function once the arguments are known (`OpaqueFunction`), so switching sim and real is one argument, never a node.

0. Before starting anything, the launch checks that every package it needs is found, and (sim only) that no other `gz sim` runs in your `GZ_PARTITION`; otherwise it stops with the reason. Two sims in one partition share topics, so `fc_bridge` would read both drones in turn and the drone flickers.
1. Always, at once: `fc_bridge` and `safety_manager`, plus Gazebo and `parameter_bridge` (with `config/gz_bridge.yaml`) with `backend:=sim`. ROS launch gives no ordering between them; that is fine, because `fc_bridge` simply sits frozen until `/clock` arrives.
2. `source:=circle`: after 5 s of wall time, `setpoint_pub` (takeoff, then circles). It runs on a timer, not on arming: with the radio, arm before it starts, or use `radio:=false`.
3. `source:=mission`: `mission`, and `demo_flight` unless `demo:=false`, at once (`demo_flight` retries Takeoff for 2 minutes, until the rangefinder is up and you've armed with the radio).
4. `source:=none`: nothing flies the drone on its own; fly it with the radio alone, or by hand (keyboard on `/cmd/manual`).
5. With `backend:=sim` and `radio:=true` (the default): `joy_node` and `radio_teleop`. The real drone never flies without the radio as a backup, and only the radio arms it, so the sim does the same. With the Pocket unplugged, `joy_node` waits quietly and picks it up when it appears; until you arm, nothing flies.
6. All our nodes get `config/sim.yaml`, and `use_sim_time` true with `sim` (false with `inav`). Each source is remapped from `setpoint_velocity` to its own topic: `/cmd/mission` (`setpoint_pub`, `mission`) or `/cmd/radio` (`radio_teleop`).
7. Ctrl-C stops everything together. Every Python node handles the shutdown race in rclpy (the context can close between two waits), so none of them dies with a traceback.

**`basics.launch.py`: the crash-course exercise**

Starts `setpoint_pub` and `watchdog` only, with settings from `config/basics.yaml` (`rate_hz` 20, `speed` 0.3, `timeout_s` 0.3) and a `use_sim_time` launch argument (default `false`). No Gazebo and no `fc_bridge`; nothing flies. Its topic is `/setpoint_velocity`, not the contract topic.

## Known issues and limitations

None of these stop the simulation from working today. The priority says when each must be fixed: **before hardware** means before the `inav` backend ever commands a real motor.

| Issue | Where | What can go wrong | Fix | Priority |
| --- | --- | --- | --- | --- |
| Wi-Fi latency not measured or checked | `fc_bridge` `inav` backend | ROS runs on the ground laptop, so the Wi-Fi hop is between `fc_bridge` and INAV (MSP through the ESP8266), after the setpoint timeout. A slow link would deliver old commands | Measure MSP round-trip time (STK-5); the `inav` backend times its requests and stops sending (INAV's own failsafe takes over) when replies are late | Before hardware |
| No IMU in the sim | X3 model | No `fc/imu`; nothing needs it yet | Own world and model copy with an IMU sensor when `safety_manager` needs it | Later |
| Flow position drifts while landed | `fc_bridge` | Sitting on the ground, `fc/odom` xy still drifts; INAV ignores flow when landed | Stop integrating below `range_min` if it gets in the way | Watch |
| Rangefinder on the ground reads about 0.05 m | `fc_bridge` sim backend | Just above `range_min` (0.04), so with noise it sometimes reads `-inf` | `mission` must treat `-inf` near the ground as landed, not as a lost sensor | Next |
| Sensor model is a guess | `fc_bridge` sim backend | Noise, drift and range limits are not measured on our hardware | Measure with the real ThoneFlow and rangefinder; update the parameters | Before hardware |
| Velocity-only control: height drifts | X3 controller | Holds zero vertical speed, not a height: drifts down about 1 cm every 6 s and loses about 15 cm in a yaw. Still true for `circle` and the radio; `mission` corrects it | Altitude hold for the radio too, in `safety_manager` | Later |
| Takeoff overshoot | `mission` | Overshoots the target by about 4 cm before settling | Lower `kp_z` near the target, or slow the climb before it | Watch |
| `-inf` in the air is read as the ground | `mission` | A rangefinder failing as `-inf` in flight would look like height 0, so the mission climbs | Cross-check with `fc/odom` z before trusting `-inf` | Before hardware |
| Goto ends short of the target | `mission` | Ends within `pos_tolerance` (0.10 m) of an `fc/odom` target, and `fc/odom` drifts: the sim's 1 m sides came out 0.82–0.91 m | Lower `pos_tolerance`; accept that flow can't do exact distances | Watch |
| Armed on the ground after landing | `mission` | With the radio arming (default), the mission never disarms: the pilot does, with SA. With `radio:=false`, only a successful Land goal disarms; landing after a lost rangefinder or a takeoff timeout stays armed | Like the real drone; disarm with the radio. INAV can also auto-disarm on landing, to be decided with the `inav` backend | Later |
| One goal at a time, no queue | `mission` | A second Goto is rejected while one runs; clients must wait | A queue, or waypoint lists in one goal, when missions need it | Later |
| Mission command gaps under CPU load | `mission` | Twice in the sim its 20 Hz commands paused for more than 0.3 s while a `ros2` CLI started, so `fc_bridge` sent zero for a moment | Watch; if it shows up on the real laptop, raise `source_timeout_s`/`setpoint_timeout_s` a little or move the timer to its own thread | Watch |
| `mission` sometimes slow to exit | `mission` | Once in 11 Ctrl-Cs (Oct 30, after a radio takeover) it didn't exit within 15 s; not reproduced since | Watch; launch kills it after 15 s anyway | Watch |
| Radio-as-joystick needs RF off | Pocket | A transmitting radio could command a bench drone | Always use the `INAV-SIM` model copy with Internal RF off | Always |
| Frame names differ | `fc_bridge`, Gazebo | Commands say `base_link`, the sim says `x3/base_footprint`; harmless until tf is used | Align when tf is introduced | Later |
| One-off timeout right after the first setpoint | `fc_bridge` | Seen once at startup: `received`, then `timeout` 14 ms later, then fine | Watch for it; if it repeats while setpoints flow, sim time is jumping and the timeout needs a margin | Watch |
| Topics fixed to the X3, no namespace | all nodes | Fine for one drone; two drones would clash | Namespaces per drone when multi-agent work starts (Module 3) | Later |

The 5 s start delay of `setpoint_pub` is wall time, which could look risky on a slow machine. It is safe: `setpoint_pub` runs on sim time, so its timer does not tick and its takeoff clock does not start until Gazebo's clock arrives.

**Resolved since Oct 20, 2026:** NaN passing through the clamp (now rejected in `fc_bridge`), the watchdog and `fc_bridge` timeouts disagreeing (both 0.3 s from `sim.yaml`), no odometry in ROS (`/fc/odom`), and the unverified velocity frame (body frame confirmed). Since Oct 26: failsafes tested by hand only (now automated, see below), drone models lost when the container is recreated (now in the `gz-cache` volume), and the arm switch bounce (confirmed with `tools/arm_bounce.py`, debounced by `arm_hold_s` in `radio_teleop`). Since Oct 27: `/fc/odom` published by the bridge instead of `fc_bridge`, and no attitude topic (`fc_bridge` now publishes `fc/odom`, `fc/attitude` and `fc/range`). Since Oct 29: timed takeoff, never landing, and height drift in autonomous flight (the `mission` node); no disarm after landing in the sim (`mission` calls `fc/arm`). Since Oct 30: one commander at a time (`safety_manager` arbitrates; the radio overrides a running mission); sim-only enable and ROS arming reaching the real drone (`backend:=inav` has no enable topic and refuses `fc/arm`; in the sim only the radio arms, unless `radio:=false`).

## Tests

The failsafes have automated tests. Run them inside the container:

```bash
cd ~/ros2_ws && colcon build && colcon test --packages-select drone_fc_bridge drone_basics_py drone_mission drone_safety && colcon test-result --verbose
```

| Test file | What it checks |
| --- | --- |
| `drone_fc_bridge/test/test_failsafes.py` | `launch_testing`: starts `fc_bridge` alone on the wall clock. Zero with no setpoints; fresh setpoints forwarded; zero within 0.3 s (± 0.15) of the last setpoint; NaN and infinity rejected and timed out; horizontal clamp keeps direction; z and yaw clamped; roll and pitch rates zeroed; sim enable published. Runs on its own domain (199, localhost only), so a running sim does not interfere. |
| `drone_fc_bridge/test/test_state.py` | `launch_testing`: `fc_bridge` with noise off, fed fake `/X3/odom`. Velocity passes through; xy position is integrated, not copied from the sim; body velocity is rotated by heading; height and attitude from the sim; range is z when level, 2z at 60° roll, `±inf` out of range or upside down. |
| `drone_mission/test/test_logic.py` | pytest, no ROS: 31 tests (Oct 29), whole flights against a toy drone (height, x, y, yaw) in milliseconds. 37 since Oct 30, with overrides, and 43 with arming: Takeoff refused until armed (and before any `fc/status`); with `radio_arms` false it needs no arm, and a stale disarmed status doesn't abort it; disarmed in the air aborts the goal and goes grounded and silent; disarmed on the ground changes nothing. Overrides: the goal aborts and the mission goes quiet; goals refused while overridden; control back in the air holds where the pilot left it and takes new goals; back on the ground stays grounded; an override aborts a Land too. Takeoff (default and given height; refused without range, above `max_range`, in the air; timeout lands; cancel holds); Goto (forward, relative to heading, a square comes back, refused on the ground and during takeoff and without odometry, aborts when odometry stops, timeout, cancel holds, feedback); Land (preempts Goto, can't be cancelled, refused on the ground); hold corrects sag; tilt; `-inf` = ground; range lost then back, aborting a Goto, or lost too long and blind landing; Land during an autonomous landing; Takeoff waits for a steady range, and a gap restarts the wait; range lost during Takeoff: back to grounded if still on the ground, or holds the height reached, never climbs with no goal. |
| `drone_safety/test/test_arbiter.py` | pytest, no ROS: nothing active at start; one source forwarded; the radio takes over from the mission and the mission is dropped; manual beats mission but not radio; control returns once the radio is quiet for the timeout; all quiet is none; unknown sources never forwarded; changes reported once; time going backwards isn't fresh. |
| `drone_fc_bridge/test/test_inav.py` | `launch_testing`: `fc_bridge` with `backend: inav` (and `armed_at_start` true, which must not apply). `fc/status` says `inav` and disarmed; `fc/arm` true and false both refused; nothing published on the Gazebo twist or enable topics, and no publisher on them. |
| `drone_fc_bridge/test/test_services.py` | `launch_testing`: starts armed; `fc/arm` false/true changes the enable topic and `fc/status`; `fc/hold` sends zero despite fresh setpoints, and releasing it follows them again; `fc/status` reports the setpoint age. |
| `drone_basics_py/test/test_radio_teleop.py` | pytest, no launch: SA arms the FC once and SA off disarms, even in flight; SA on at start must be cycled; arming refused with throttle off centre; switch off publishes nothing; arm alone (armed, ready) or takeover alone flies nothing; either off releases at once; the hold counts from the takeover; engage refused with throttle off centre; re-engage needs the throttle centred again; a bounce while arming or disarming never engages; off is immediate; stick scaling, signs and deadband. |

Breaking the timeout check in `fc_bridge` makes three tests fail (checked Oct 26, 2026).

## Not built yet

What the fc\_bridge interface contract asks for that does not exist today. The first group is the next step.

| Item | Kind | Notes |
| --- | --- | --- |
| `fc/imu` | Topic out, `sensor_msgs/Imu` | The X3 model has no IMU sensor; needs our own world and model copy |
| `fc/battery` | Topic out | Battery from INAV over MSP; nothing in the sim yet |
| `inav` backend | `fc_bridge` code | A stub since Oct 30 (`backend:=inav`). MSP (MultiWii Serial Protocol) over the ESP8266 Wi-Fi link: TCP (Transmission Control Protocol) for bring-up, UDP (User Datagram Protocol) before flight |
| Low-battery action | `safety_manager` | Only warns today; return or land comes with `fc/battery` from the `inav` backend |
