# Sim Stack: Parameters, Odometry, Failsafes and Teleop

Oct 23, 2026 · João Barros

What was added on top of "the X3 flies circles on its own", and how to try each part. Read `GUIDE.md` first if your container isn't set up yet; the Nodes Information doc (`README.md`) describes the nodes as they were before this work.

## What changed, in one table

| Area | Change | Files |
| --- | --- | --- |
| Parameters | Every node reads its settings from one YAML file. The `safety_manager` and `fc_bridge` timeouts agree (0.3 s). | `drone_bringup/config/sim.yaml` |
| Bridge | The Gazebo bridge topics moved from command-line arguments to YAML | `drone_bringup/config/gz_bridge.yaml` |
| Launch | `source:=circle\|mission\|joy\|none` chooses who commands the drone; `world:=` chooses the SDF | `drone_bringup/launch/sim.launch.py` |
| State | Odometry of the X3 is visible in ROS: Gazebo's true pose on `/X3/odom`, and what the stack sees on `fc/odom`, `fc/attitude`, `fc/range` from `fc_bridge` (Oct 27: shaped like optical flow + rangefinder, xy drifts) | `gz_bridge.yaml`, `fc_bridge.cpp` |
| Safety | `fc_bridge` rejects setpoints containing NaN or infinity | `drone_fc_bridge/src/fc_bridge.cpp` |
| Teleop | Keyboard teleop (`teleop_twist_keyboard`) | `Dockerfile` |
| Teleop | RadioMaster Pocket as a USB joystick, with the arm switch as deadman | `drone_basics_py/radio_teleop.py`, `setup.py`, `package.xml`, `sim.yaml` |
| Container | `/dev/input` and the `input` group passed into the container | `compose.yaml`, `make-env.sh`, `Dockerfile` (`ros-jazzy-joy`) |
| Tools | `odom_yaw.py`: prints x, y, z and heading twice a second | `ros2_ws/tools/odom_yaw.py` |
| Tools | `arm_bounce.py`: logs every arm switch change on `/joy` and flags bounces | `ros2_ws/tools/arm_bounce.py` |
| Container | Gazebo's model cache (`~/.gz`) kept in the `gz-cache` volume, so the X3 survives recreating the container | `compose.yaml`, `Dockerfile` |

## How it fits together

```
   source:=circle   setpoint_pub ─────────────────────────────┐
   source:=mission  demo_flight → actions → mission ───────────┼─► /cmd/mission  (3)
   always             Pocket → joy_node → radio_teleop ─────────► /cmd/radio    (1)
   by hand: keyboard or ros2 topic pub ───────────────────────────► /cmd/manual   (2)
                                                                         │
                         safety_manager: highest-priority source publishing in the last 0.3 s
                         (logs and latches it on safety/active_source; mission listens)
                                                                         ▼
                                                          /fc/setpoint_velocity
                                                          (TwistStamped, base_link)
                                                                         ▼
                              fc_bridge: NaN guard → 0.3 s timeout → clamp → 20 Hz
                                                                         │
                                                                         ▼
                                     ros_gz_bridge ──► Gazebo X3 velocity controller
                                     ros_gz_bridge ◄── /model/x3/odometry, /clock
                                           │
                                           ▼
                                   /X3/odom ──► fc_bridge ──► fc/odom, fc/attitude, fc/range
```

Only `safety_manager` publishes on `/fc/setpoint_velocity`, so sources never fight: the radio beats manual beats the mission. Every source still ends in `fc_bridge`, so the timeout, NaN guard and clamp apply to all of them.

## First-time setup after pulling

The Dockerfile and `compose.yaml` changed, so the container must be rebuilt. On the **host**, in `seame-docker/`:

```bash
./make-env.sh                 # adds INPUT_GID to .env (answer y to overwrite)
docker compose build
docker compose up -d --force-recreate
xhost +local:                 # lets the container open Gazebo's window; needed again after every login
```

Inside the container (`docker compose exec dev bash`):

```bash
cd ~/ros2_ws && colcon build --symlink-install && source install/setup.bash
```

Rule of thumb: `docker compose`, `lsusb`, `jstest`, `xhost` and editing files run on the **host**. `colcon`, `ros2` and `gz` run in the **container** (prompt `dev@...`). Building from the host fails with a `CMakeCache.txt ... is different` error.

You may see `groups: cannot find name for group ID 990` (and `994`) when entering the container. Harmless: those are the render and input groups, added by number.

## Try it

### 1. Circle flight (the old behaviour)

```bash
ros2 launch drone_bringup sim.launch.py            # source:=circle is the default
```

Takeoff, then circles. In a second terminal:

```bash
python3 ~/ros2_ws/tools/odom_yaw.py /X3/odom
```

**Expect:** z rises to about 1.0 m, then x and y trace a circle of about 0.55 m radius centred near (0, 0.55). `/X3/odom` is Gazebo's true pose. Without the argument the tool reads `fc/odom`, what the stack sees: the same circle, slowly drifting away (about 0.5 m per minute).

### 1b. Mission (Takeoff, Goto and Land actions on the rangefinder)

```bash
ros2 launch drone_bringup sim.launch.py source:=mission
```

`demo_flight` takes off to 1.2 m, flies a 1 m square (forward, quarter turn left, four times) and lands.

**Expect** in the launch log: a few `takeoff rejected: no rangefinder reading` or `rangefinder not steady yet` while the sim starts, then `takeoff accepted`, `State: grounded -> takeoff`, `takeoff -> hold` at about 1.16 m, eight `goto: ok`, `land: ok`, `Disarmed (fc/arm)`, `Demo done`. With `odom_yaw.py /X3/odom`: z at 1.20 m throughout, a square of about 0.85 m sides, back to about 0.05 m.

**Sending goals by hand:** start with `source:=mission demo:=false`, then in a second container terminal:

```bash
ros2 action send_goal /mission/takeoff drone_interfaces/action/Takeoff "{height: 1.0}" --feedback
```

```bash
ros2 action send_goal /mission/goto drone_interfaces/action/Goto "{forward: 1.0, left: 0.5, yaw: 1.57}" --feedback
```

```bash
ros2 action send_goal /mission/land drone_interfaces/action/Land "{}" --feedback
```

Ctrl-C on a Takeoff or Goto cancels it (the drone holds); a Land can't be cancelled. `ros2 topic echo /fc/status` shows armed, holding and the rest; `ros2 service call /fc/hold std_srvs/srv/SetBool "{data: true}"` freezes the drone whatever the mission sends.

### 1c. Mission with the radio as override

```bash
ros2 launch drone_bringup sim.launch.py source:=mission demo:=false
```

Take off and start a long Goto (see "Sending goals by hand" above), then, with SA on, centre the throttle and flip the takeover switch on (the other shoulder switch, axis 6). **Expect:** `Active source: radio` from `safety_manager`, `goto -> overridden` from `mission`, the Goto aborted with `overridden by radio`, and the sticks fly the drone. Flip takeover (or SA) off: `overridden -> hold` at the height you left it, `Active source: mission`. Send a Land, or land it yourself before flipping off: then the mission goes to `grounded`. After a Land (which disarms), taking over again arms the drone (`Armed (fc/arm)` from `fc_bridge`) and the sticks fly it; no Takeoff goal needed.

With `demo:=true` the demo stops at the first aborted step and asks for a Land, which the mission refuses while you have control; that's expected.

### 2. Keyboard

Terminal A:

```bash
ros2 launch drone_bringup sim.launch.py source:=none
```

Terminal B (keep it focused while flying):

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true -p frame_id:=base_link -p use_sim_time:=true -r cmd_vel:=/cmd/manual
```

| Key | Command |
| --- | --- |
| `t` / `b` | Up / down |
| `i` / `,` | Forward / back |
| `j` / `l` | Yaw left / right |
| `J` / `L` (Shift) | Strafe left / right |
| `k` | Stop |
| `q` / `z` | All speeds ×1.1 / ×0.9 |

These are the node's built-in keys. Releasing a key stops the drone within 0.3 s (the `fc_bridge` timeout). A lurch at the start of every key hold is the OS key-repeat delay being longer than 0.3 s; shorten it on the host with `xset r rate 200 30` (X11) or in Settings → Accessibility → Typing (GNOME Wayland). Don't raise the timeout to hide it.

### 3. RadioMaster Pocket

> **Safety.** This path is **sim only**. On the real drone the Pocket talks ELRS straight to INAV and never goes through ROS. In USB joystick mode the radio **keeps transmitting** if its RF module is on, so always use a model with **Internal RF: Off**, and never fly the sim with a drone battery plugged in nearby.

**Radio (once):**

1. In EdgeTX, copy the team's INAV model and name the copy, for example `INAV-SIM`. Same channels, switches, rates and arm switch as the real drone.
2. In the copy: **Internal RF → Off**. Change nothing else.
3. Plug the Pocket into the host with a **data** USB cable (charge-only cables don't work) and choose **USB Joystick (HID)**. On the Vostro 5568 the bottom USB port doesn't work; use another one.

**Check on the host:**

```bash
lsusb | grep -i radiomaster                  # 1209:4f54 ... Radiomaster Pocket Joystick
ls /dev/input/by-id/ | grep -i pocket
```

Don't trust `js0` blindly: some laptops (Dells) have an accelerometer there. `joy_node` selects the radio by name, so this doesn't matter in ROS.

**Check in the container:**

```bash
ros2 run joy joy_enumerate_devices           # must list "OpenTX Radiomaster Pocket Joystick"
```

**Fly:**

```bash
ros2 launch drone_bringup sim.launch.py source:=none
```

1. Disarmed: nothing is published; `fc_bridge` holds (zero velocity).
2. Arm with the throttle off centre: `Centre the throttle stick to engage`, no motion.
3. Centre the throttle, arm: `Engaged: sticks command velocity` about 0.1 s later (the debounce). Throttle up climbs.
4. Disarm at any time: the drone should stop and hover within about 0.3 s. Pulling the USB cable should have the same effect (both not yet tested mid-flight).

Stick mapping (Mode 2): right stick = forward/back and strafe, left stick = up/down and yaw. Forward always means where the nose points (see Results).

## Parameters (`drone_bringup/config/sim.yaml`)

All decimals are doubles: write `0.3`, never `0`. Axis indices are integers. A wrong type makes the node refuse to start. Nodes must still **declare** every parameter in their code; the YAML only overrides the default. Removing a declaration crashes the node the first time it reads the value.

**`fc_bridge`**: the hard limits. These are safety caps meant for the real airframe, not handling settings: tune stick feel in `radio_teleop`, not here.

| Parameter | Value | Meaning |
| --- | --- | --- |
| `rate_hz` | 20.0 | Commands sent to Gazebo per second |
| `setpoint_timeout_s` | 0.3 | Older setpoints are stale: zero velocity is sent |
| `max_speed_xy` | 0.5 | Horizontal speed cap, m/s (direction kept) |
| `max_speed_z` | 0.3 | Vertical speed cap, m/s |
| `max_yaw_rate` | 1.0 | Yaw rate cap, rad/s |

**`safety_manager`**: `source_timeout_s` 0.3. Keep it equal to `setpoint_timeout_s`. `priority` `[radio, manual, mission]`.

**`setpoint_pub`**: `rate_hz` 10.0, `speed` 0.3, `takeoff_s` 4.0, `climb_speed` 0.3.

**`joy_node`**

| Parameter | Value | Meaning |
| --- | --- | --- |
| `device_name` | `OpenTX Radiomaster Pocket Joystick` | Opens the radio by name, so another joystick can't be picked by mistake |
| `deadzone` | 0.05 | Stick noise ignored by `joy_node` |
| `autorepeat_rate` | 20.0 | `/joy` is republished at 20 Hz even when nothing moves, which keeps `fc_bridge` fresh |

**`radio_teleop`**

| Parameter | Value | Meaning |
| --- | --- | --- |
| `axis_roll`, `axis_pitch`, `axis_throttle`, `axis_yaw`, `axis_arm` | 0, 1, 2, 3, 4 | Index into `/joy` axes |
| `sign_roll` | 1.0 | Stick right → −y (ROS y points left) |
| `sign_pitch` | −1.0 | Stick up → +x |
| `sign_throttle` | −1.0 | Stick up → +z |
| `sign_yaw` | 1.0 | Stick right → negative yaw rate (clockwise) |
| `sign_arm` | −1.0 | The arm switch reads −1 when armed |
| `axis_takeover`, `sign_takeover` | 6, −1.0 | The takeover switch, the shoulder switch opposite SA; reads −1 when on. −1 for the axis = none, arm alone takes over |
| `arm_threshold` | 0.5 | `sign_arm × axis` above this means armed |
| `arm_hold_s` | 0.1 | Debounce: the switch must read armed this long, without a break, before it engages. Off acts at once. Needs `joy_node` `autorepeat_rate` above 0 |
| `deadband` | 0.08 | Stick values below this count as centred |
| `max_xy`, `max_z`, `max_yaw` | 0.5, 0.3, 1.0 | Command at full stick (m/s, m/s, rad/s) |

Why the signs look odd: `joy_node` reports every axis of the Pocket **inverted** compared with `jstest` (up, right and armed are −1 in `/joy`). The signs above undo that and convert to ROS conventions (REP 103: +x forward, +y left, +z up, +yaw counter-clockwise).

## Topics added

| Topic | Type | From | Notes |
| --- | --- | --- | --- |
| `/X3/odom` | `nav_msgs/Odometry` | `ros_gz_bridge`, from `/model/x3/odometry` | 50 Hz, Gazebo's true pose. `frame_id: x3/odom`, `child_frame_id: x3/base_footprint`. Covariances are all zero. Only `fc_bridge` and debugging tools should read it. |
| `/fc/odom`, `/fc/attitude`, `/fc/range` | `Odometry`, `QuaternionStamped`, `Range` | `fc_bridge` | 50 Hz. Shaped like INAV with optical flow + rangefinder: xy integrated from noisy velocity, so it drifts. See the README `fc_bridge` section. |
| `/joy` | `sensor_msgs/Joy` | `joy_node` | Always launched; empty until the Pocket is plugged in |

The Gazebo topic is `/model/x3/odometry` with a **lowercase** x3, unlike the command topics (`/X3/...`). With the uppercase name the bridge connects to nothing, silently.

## How the failsafes work

| Event | What happens |
| --- | --- |
| No setpoint for 0.3 s (key released, `radio_teleop` silent, node crashed, USB unplugged) | `fc_bridge` sends zero velocity → the drone hovers. `safety_manager` logs `No source publishing`. |
| Setpoint with NaN or infinity in any field | `fc_bridge` drops it and logs `Rejected non-finite setpoint` at most once a second. The previous setpoint keeps ageing, so the timeout above takes over. |
| Too fast | Clamped to the `fc_bridge` limits; horizontal direction kept |
| Arm on, takeover off | Nothing: the radio is ready but the mission (or hover) keeps control |
| Takeover on, arm off | Nothing |
| Takeover on with arm on, after a Land | `radio_teleop` arms `fc_bridge` (`fc/arm`) and the sticks fly it |
| Arm or takeover switch off | `radio_teleop` stops publishing → control goes back to the mission, or with none, timeout → hover |
| Takeover on (arm on) during a mission | The radio takes over at once; the mission aborts its goal (`overridden by radio`) and goes quiet. Switch off: the mission holds where you left it (or stays grounded if you landed) and waits for a new goal |
| Arm switch on with the throttle off centre | `radio_teleop` refuses to engage until the throttle is centred |

Test the NaN guard (sim with `source:=none`):

```bash
ros2 topic pub -r 20 /fc/setpoint_velocity geometry_msgs/msg/TwistStamped '{twist: {linear: {x: .nan, z: 0.3}}}' > /dev/null
```

The drone stays on the ground and `ros2 topic echo /X3/gazebo/command/twist --once` shows zeros. Replace `.nan` with `0.0` and it climbs.

## Results (Oct 22–23, 2026)

| Test | Result |
| --- | --- |
| Velocity frame | **Body frame.** Forward follows the nose: commanded forward at yaw 66.1° moved at 66.2°; at −169.2° moved at −168.5°. `fc_bridge` needs no rotation. |
| Circle (`source:=circle`) | Radius about 0.545 m against 0.6 commanded (the drone flies about 0.27 m/s, not 0.3). Lap 12.5 s against 12.6. |
| Takeoff height | About 1.02 m against 1.2 m planned (spin-up eats part of the 4 s climb) |
| Height hold | Drifts down about 1 cm every 6 s; loses about 15 cm during a 125° yaw |
| Mission v1 (fixed flight, Oct 29) | Takeoff to 1.24 m peak, settled at 1.20 m; 1.197–1.203 m through the circle and a full 360° turn; landed and stopped publishing after about 42 s of sim time |
| Mission v2 demo (actions, Oct 29) | All goals succeeded; 1.19–1.22 m through eight Goto goals; true square sides 0.82–0.91 m against 1.0 (Goto tolerance 0.10 m plus `fc/odom` drift); back within 0.09 m of the start; disarmed after landing |
| Odometry rate | 50.0 Hz |
| Arm switch | **Bounce confirmed** (`arm_bounce.py`, Oct 26): bursts of up to about 10 flips, 0–35 ms apart, mostly on a slow arm. Fixed with `arm_hold_s` 0.1 s in `radio_teleop`. Deliberate fast flicks are 100 ms or more apart. |

### Checking the arm switch for bounce

Radio connected, nothing else running. Two container terminals:

```bash
ros2 run joy joy_node --ros-args -p device_name:="OpenTX Radiomaster Pocket Joystick"
```

```bash
python3 ~/ros2_ws/tools/arm_bounce.py
```

Flip SA on and off slowly about 20 times, then Ctrl-C. A clean switch prints one line per flip, each hundreds of ms after the last. A bounce shows as lines less than 300 ms apart, marked `<-- BOUNCE`.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `CMakeCache.txt ... is different than the directory` | Built on the host | Build inside the container |
| `ros2: command not found` | Host terminal | `docker compose exec dev bash` |
| Gazebo: `could not connect to display :0` | X access not granted this login | `xhost +local:` on the host |
| Nothing moves, `mission` never logs `takeoff accepted`, and Ctrl-C is slow | No `/clock`: a Gazebo server left over from an earlier run, stuck at startup (`gz topic -l` shows only `/gazebo/starting_world`) | Ctrl-C the launch; in the container, `pgrep -af "gz sim"`, then `pkill -f "gz sim server"`. A stuck server ignores that: if `pgrep` still shows it, `pkill -9 -f "gz sim server"`. Launch again |
| The drone flickers or jumps between heights, during missions and under the radio | Two Gazebo sims in one partition: `fc_bridge` reads both drones in turn. Usually a launch that failed after starting Gazebo (e.g. a missing package), leaving it running on its own | `sim.launch.py` now refuses to start while another `gz sim` runs in your `GZ_PARTITION`, and checks its packages before starting anything. If it refuses: close the old Gazebo, or `pkill -f "gz sim"` in the container |
| `Package 'drone_safety' not found` (or another `drone_*`) | Built after this terminal sourced the workspace: sourcing only sees packages that existed then | `colcon build && source install/setup.bash`, in every terminal |
| Gazebo dies with exit code 139, `Authorization required` in the log (also with `-s`, headless) | Same: the sensors system needs OpenGL through the X display | `DISPLAY=:0 xhost +local:` on the host; `xhost` must then list `LOCAL:` |
| `fc_bridge` dies on the first valid setpoint | A `declare_parameter` line was removed or commented out | Keep every declaration; the YAML only overrides it |
| `radio_teleop`: `has no attribute 'main'` | `radio_teleop.py` empty or not saved | Check with `wc -l`, then rebuild |
| Sticks do nothing | Arm or takeover off (correct), or `radio_teleop` died; `ros2 topic echo /safety/active_source` should say `radio` while engaged | Arm with the throttle centred; check the launch log |
| Never engages | Throttle not centred (the Pocket's throttle doesn't spring back) | Find the centre; `ros2 topic echo /joy --field axes` shows it |
| Radio not in `lsusb` | Charge-only cable, USB mode not Joystick, or a dead port | Another cable or port; EdgeTX USB mode: Ask or Joystick |
| `/dev/input` empty in the container | A volume line in `compose.yaml` indented differently from the others: YAML merges it into the line above | Same indentation for every `- ` entry; `docker compose up -d --force-recreate` |
| `ros2 topic hz /fc/odom`: "not published yet" for a moment | The bridge or `fc_bridge` hadn't connected yet | Wait a second |
| Two publishers on `/fc/setpoint_velocity` | A node started by hand on the old topic, next to `safety_manager` | Publish on `/cmd/manual` instead; it outranks the mission. Check with `ros2 topic info /fc/setpoint_velocity -v`: only `safety_manager` should publish |

## Known issues

| Issue | Impact | Next step |
| --- | --- | --- |
| Velocity-only control: height drifts down and drops in yaw | Fine with a human on the sticks; `mission` corrects it with `fc/range` | Altitude hold for the radio in `safety_manager` |
| Frame names: commands say `base_link`, the sim says `x3/base_footprint` | Nothing yet (no tf in use) | Align when tf is introduced |
| Radio-as-joystick is sim only and needs RF off | A transmitting radio could command a bench drone | Always the `INAV-SIM` model |
