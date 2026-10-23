# Sim Stack: Parameters, Odometry, Failsafes and Teleop

Oct 23, 2026 · João Barros

What was added on top of "the X3 flies circles on its own", and how to try each part. Read `GUIDE.md` first if your container isn't set up yet; the Nodes Information doc (`README.md`) describes the nodes as they were before this work.

## What changed, in one table

| Area | Change | Files |
| --- | --- | --- |
| Parameters | Every node reads its settings from one YAML file. The watchdog and `fc_bridge` timeouts now agree (0.3 s). | `drone_bringup/config/sim.yaml` |
| Bridge | The Gazebo bridge topics moved from command-line arguments to YAML | `drone_bringup/config/gz_bridge.yaml` |
| Launch | `source:=circle\|joy\|none` chooses who commands the drone; `world:=` chooses the SDF | `drone_bringup/launch/sim.launch.py` |
| State | Odometry of the X3 is now visible in ROS on `/fc/odom` (50 Hz) | `gz_bridge.yaml` |
| Safety | `fc_bridge` rejects setpoints containing NaN or infinity | `drone_fc_bridge/src/fc_bridge.cpp` |
| Teleop | Keyboard teleop (`teleop_twist_keyboard`) | `Dockerfile` |
| Teleop | RadioMaster Pocket as a USB joystick, with the arm switch as deadman | `drone_basics_py/radio_teleop.py`, `setup.py`, `package.xml`, `sim.yaml` |
| Container | `/dev/input` and the `input` group passed into the container | `compose.yaml`, `make-env.sh`, `Dockerfile` (`ros-jazzy-joy`) |
| Tools | `odom_yaw.py`: prints x, y, z and heading twice a second | `ros2_ws/tools/odom_yaw.py` |

## How it fits together

```
                    source:=circle   setpoint_pub ──┐
                    source:=joy      Pocket → joy_node → radio_teleop ──┤
                    source:=none     (you, by hand: keyboard or ros2 topic pub) ──┤
                                                                         ▼
                                                          /fc/setpoint_velocity
                                                          (TwistStamped, base_link)
                                                                         │
                                         watchdog (only logs) ◄──────────┤
                                                                         ▼
                              fc_bridge: NaN guard → 0.3 s timeout → clamp → 20 Hz
                                                                         │
                                                                         ▼
                                     ros_gz_bridge ──► Gazebo X3 velocity controller
                                     ros_gz_bridge ◄── /model/x3/odometry, /clock
                                           │
                                           ▼
                                        /fc/odom
```

Exactly one source runs at a time, so two publishers never fight over `/fc/setpoint_velocity`. Every source ends in `fc_bridge`, so the timeout, NaN guard and clamp apply to all of them.

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
python3 ~/ros2_ws/tools/odom_yaw.py
```

**Expect:** z rises to about 1.0 m, then x and y trace a circle of about 0.55 m radius centred near (0, 0.55).

### 2. Keyboard

Terminal A:

```bash
ros2 launch drone_bringup sim.launch.py source:=none
```

Terminal B (keep it focused while flying):

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true -p frame_id:=base_link -p use_sim_time:=true -r cmd_vel:=/fc/setpoint_velocity
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
ros2 launch drone_bringup sim.launch.py source:=joy
```

1. Disarmed: nothing is published; `fc_bridge` holds (zero velocity).
2. Arm with the throttle off centre: `Centre the throttle stick to engage`, no motion.
3. Centre the throttle, arm: `Engaged: sticks command velocity`. Throttle up climbs.
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

**`watchdog`**: `timeout_s` 0.3. Keep it equal to `setpoint_timeout_s`.

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
| `arm_threshold` | 0.5 | `sign_arm × axis` above this means armed |
| `deadband` | 0.08 | Stick values below this count as centred |
| `max_xy`, `max_z`, `max_yaw` | 0.5, 0.3, 1.0 | Command at full stick (m/s, m/s, rad/s) |

Why the signs look odd: `joy_node` reports every axis of the Pocket **inverted** compared with `jstest` (up, right and armed are −1 in `/joy`). The signs above undo that and convert to ROS conventions (REP 103: +x forward, +y left, +z up, +yaw counter-clockwise).

## Topics added

| Topic | Type | From | Notes |
| --- | --- | --- | --- |
| `/fc/odom` | `nav_msgs/Odometry` | `ros_gz_bridge`, from `/model/x3/odometry` | 50 Hz. `frame_id: x3/odom`, `child_frame_id: x3/base_footprint`. Covariances are all zero. |
| `/joy` | `sensor_msgs/Joy` | `joy_node` | Only with `source:=joy` |

The Gazebo topic is `/model/x3/odometry` with a **lowercase** x3, unlike the command topics (`/X3/...`). With the uppercase name the bridge connects to nothing, silently.

## How the failsafes work

| Event | What happens |
| --- | --- |
| No setpoint for 0.3 s (key released, `radio_teleop` silent, node crashed, USB unplugged) | `fc_bridge` sends zero velocity → the drone hovers. The watchdog logs it. |
| Setpoint with NaN or infinity in any field | `fc_bridge` drops it and logs `Rejected non-finite setpoint` at most once a second. The previous setpoint keeps ageing, so the timeout above takes over. |
| Too fast | Clamped to the `fc_bridge` limits; horizontal direction kept |
| Arm switch off | `radio_teleop` stops publishing → timeout → hover |
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
| Odometry rate | 50.0 Hz |
| Arm switch | One burst of 12 on/off flips in 0.2 s was seen in `jstest`. To be confirmed. |

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `CMakeCache.txt ... is different than the directory` | Built on the host | Build inside the container |
| `ros2: command not found` | Host terminal | `docker compose exec dev bash` |
| Gazebo: `could not connect to display :0` | X access not granted this login | `xhost +local:` on the host |
| `fc_bridge` dies on the first valid setpoint | A `declare_parameter` line was removed or commented out | Keep every declaration; the YAML only overrides it |
| `radio_teleop`: `has no attribute 'main'` | `radio_teleop.py` empty or not saved | Check with `wc -l`, then rebuild |
| `/fc/setpoint_velocity` not published with `source:=joy` | Disarmed (correct), or `radio_teleop` died | Arm with the throttle centred; check the launch log |
| Never engages | Throttle not centred (the Pocket's throttle doesn't spring back) | Find the centre; `ros2 topic echo /joy --field axes` shows it |
| Radio not in `lsusb` | Charge-only cable, USB mode not Joystick, or a dead port | Another cable or port; EdgeTX USB mode: Ask or Joystick |
| `/dev/input` empty in the container | A volume line in `compose.yaml` indented differently from the others: YAML merges it into the line above | Same indentation for every `- ` entry; `docker compose up -d --force-recreate` |
| `ros2 topic hz /fc/odom`: "not published yet" for a moment | The bridge hadn't connected yet | Wait a second |
| Two publishers on `/fc/setpoint_velocity` | A node started by hand while the launch has a source | Use `source:=none` when running anything by hand. Check with `ros2 topic info /fc/setpoint_velocity -v` |

## Known issues

| Issue | Impact | Next step |
| --- | --- | --- |
| Velocity-only control: height drifts down and drops in yaw | Fine with a human on the sticks; a mission node can't rely on it | Altitude hold using `/fc/odom` (mission node or `safety_manager`) |
| `/fc/odom` is published by the bridge, not `fc_bridge` | Sim shortcut; on hardware the `inav` backend publishes it | Keep the topic name; move the publisher with the `inav` backend |
| Frame names: commands say `base_link`, the sim says `x3/base_footprint` | Nothing yet (no tf in use) | Align when tf is introduced |
| Radio-as-joystick is sim only and needs RF off | A transmitting radio could command a bench drone | Always the `INAV-SIM` model |
| Possible arm switch bounce | Could toggle Engaged/off quickly | Confirm; if real, use another switch or debounce in `radio_teleop` |
| One source at a time (`source:=`) | Mission and human can't share control | Command arbitration in `safety_manager` (step 8 of the teleop guide) |
| Failsafes tested by hand only | A regression would go unnoticed | Automated `launch_testing` tests for timeout, NaN, clamp and arm switch |
