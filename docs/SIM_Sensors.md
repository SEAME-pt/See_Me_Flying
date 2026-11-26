---
title: Simulated Sensors
---
# Simulated sensors

How the Gazebo sim produces the sensor data the real drone will give us. Each
simulated sensor publishes on the same topic, with the same message type and
units, as the real one will through INAV and `fc_bridge`. Everything above
`fc_bridge` (the estimator, mission, safety) must not be able to tell
sim from real, so code tested in the sim behaves the same on the drone.

Body axes: x forward, y left, z up. Not simulated yet: the IMU (accelerometer
and gyro) needs the new test world, and the barometer is only a fallback if
the rangefinder is used.

### How flow and range work together

The flow sensor is a small downward camera that tracks the floor's texture.
It measures an *angle* per second, not a speed: the floor slides past twice as
fast in the image at half the height. So the rangefinder's height is needed
to turn flow into speed (speed ≈ flow × height). That is why INAV only uses
optical flow together with a rangefinder, and why the MTF-02P, which has both
on one board, solves that problem.

### Output as "Messages"

`drone_interfaces/msg/OpticalFlow` mirrors INAV's `MSP2_INAV_OPTICAL_FLOW`
(quality, flow rate X/Y, body rate X/Y), but in rad/s. INAV 9.1.0 sends the
rates as whole degrees per second; `fc_bridge`'s `inav` backend converts them,
and in the sim `flow_model` cuts them to whole degrees the same way.

The gyro's rotation over the same moment is needed because tilting the drone
in place also makes the floor appear to slide, without any movement.
Subtracting this body rate leaves only the part caused by actually moving.

### Sign convention

Forward flight gives negative `flow_rate_y`, and flight to the left gives
positive `flow_rate_x`. This was checked by flying in the sim, and the unit
tests in `drone_sim/test/test_flow_model.py` enforce it, so a wrong
sign fails CI. 

### Topics
| Topic (channel) | Type (layout) | What it is + source |
|---|---|---|
| `/sim/ground_truth` | `nav_msgs/Odometry` | The drone's exact position and speed in the sim. Used only to grade tests, comes from Gazebo odometry, bridged (`gz_bridge.yaml`)|
| `/X3/odom` | `nav_msgs/Odometry` | Internal input of `fc_bridge`, same odometry as above |
| `fc/range` | `sensor_msgs/Range` | Rangefinder: distance to the floor below. Gotten from `fc_bridge`, from ground truth, tilt-corrected, flat floor |
| `fc/optical_flow` | `drone_interfaces/OpticalFlow` | Optical flow: how fast the floor appears to slide past the camera. From `flow_model` (`drone_sim`), which reads `/sim/ground_truth` and the world's floor surfaces |
| `fc/odom` | `nav_msgs/Odometry` | The drone's estimated speed and position. From `estimator` (`drone_sim`), built from the three topics above |

### From sensors to `fc/odom`: the estimator

`estimator` (`drone_sim`, logic in `drone_sim/estimator.py`) does what INAV
does on the real drone: body velocity is flow (minus the body rate) × the
distance to the floor, height is the rangefinder corrected for tilt, and
position is integrated from velocity, so it drifts like the real thing. No IMU
fusion yet. When flow is lost it keeps the last speed for `hold_s` (0.3 s),
then stops; vertical speed comes from the heights over `vz_window` (0.6 s).
Because it publishes `fc/odom`, `sim.yaml` sets `fc_bridge`'s `publish_odom`
to false. `odom_check` compares it with the ground truth (below); the unit
tests are in `drone_sim/test/test_estimator.py`. Every node and parameter of
the stack: [ROS 2 stack](../project/ros2/README.md).

### Floor surfaces: where flow is lost

The flow sensor needs texture to track: over a plain surface it has nothing to
follow, and its quality drops to 0. So `flow_model` sets the quality from the
floor under the drone.

A world can have a surfaces file beside it, `worlds/<world>_surfaces.yaml`: a
quality per surface, a default surface, and rectangles of floor with their
surface (where two overlap, the later one wins). `sim.launch.py` passes it to
`flow_model` as `surfaces_file` when the file exists, so only `room_world` has
one today. Without it, the floor is carpet everywhere with quality 255, as
before. Quality 0 means no flow, the same as below 8 cm or above 7 rad/s. The
lookup is `drone_sim/floor_map.py`, tested in `drone_sim/test/test_floor_map.py`.

| Surface | Quality | Where it comes from |
|---|---|---|
| carpet (the default) | 100 | Read at rest on the room's grey carpet by the earlier ThoneFlow-3901U |
| table | 0 | The ThoneFlow-3901U read nothing over the white, smooth tops |
| shelves, fridge | 0 | Not measured; treated like the tables |
| mat | 60 | A guess; not placed yet, its position is still to be measured |

These are placeholders. The drone now uses the MTF-02P, which still has to be
measured over each surface; `make bench` already reports its flow quality at
rest (the *MTF-02P at rest* section in [telemetry](../project/telemetry/README.md)).

**What a plain table does to the estimate.** When flow is lost, the estimator
keeps the last speed for 0.3 s, then assumes the drone has stopped; it never
reports that flow is lost. The mission steers by the estimate, so it keeps
flying at full speed until the estimate catches up. Measured in the sensor
test (below), crossing table group 4 (1.5 m wide) at 0.3 m/s: flow was lost
for 5.5 s while the drone moved 1.52 m, and the estimate moved only 0.07 m, so
it missed 95 % of it. Asked to fly 1.7 m, the drone flew 3.11 m: 1.41 m too
far, about the width of the table, with the estimate 1.50 m off. INAV's
own reaction to lost flow is not modelled yet. Making the estimator behave
like it (the speed fading out, a growing uncertainty, an "invalid" flag within
1 s, then stop, and land if flow does not come back) is future work.

**Known limitations.**

- The sim's rangefinder, and the height `flow_model` uses, assume a flat
  floor: over a table, nothing sees the top 0.78 m higher. Quality 0 over the
  tables makes this harmless for the flow, but the real drone loses its height
  reference there too. An obstacle-aware rangefinder is future work.
- The room model has no textures yet (`room.mtl` is missing, and Gazebo loads
  the STL, which can't carry them), so the quality comes from the surfaces
  file, not from what a camera would see. The room gets textures next sprint;
  quality derived from floor photos comes later.

## Measuring simulated sensors vs ground truth

`flow_check` computes velocity from the sensors, like INAV
on the real drone, and prints its error vs the true values.

Result (1 m height, 0.28 m/s steady): v_x error mean −0.006 to −0.009 m/s,
std 0.011 to 0.013 m/s; v_y error mean under 0.01 m/s. The flow
plus range got the speed right to within about 1 cm/s.

Two effects from the rounding that are expected on the real
drone too:

- **Flow speed reads slightly low**, by about half a degree per second
  (≈ 0.009 m/s at 1 m, growing with height). The drone thinks it moves a bit
  slower than it does, so it may travel slightly further than commanded.
- **Movement slower than about 1 degree per second does not show in the flow
  at all** (≈ 1.7 cm/s at 1 m). A hovering drone could slowly drift, up to
  about 1 m per minute at 1 m height, without the flow noticing, unless
  something else (for example the accelerometer, or the estimator) corrects it.

Test commands:

```bash
# host, repo root: stop any sim, then start one with no radio (the drone starts armed)
make sim-stop
make ws
docker compose exec -e DISPLAY=$DISPLAY dev bash -c 'cd ~/ros2_ws && source install/setup.bash && ros2 launch drone_bringup sim.launch.py source:=mission radio:=false'

# a second terminal: make shell
ros2 run drone_sim flow_check --ros-args -p use_sim_time:=true   # or odom_check, for the estimator
ros2 action send_goal --feedback /mission/takeoff drone_interfaces/action/Takeoff "{height: 1.0}"
ros2 action send_goal --feedback /mission/goto drone_interfaces/action/Goto "{left: -1.3}"   # into the carpet lane, y = 2.7
ros2 action send_goal --feedback /mission/goto drone_interfaces/action/Goto "{forward: 4.0, speed: 0.3}"
ros2 action send_goal /mission/land drone_interfaces/action/Land "{}"
```

## Automated sensor test

`make sim-test-sensors` flies the same checks headless, in a throwaway
container, with no commands to type, in `room_world` (the sim's default
world). It is also run every night in CI (the `gazebo-sensors` job of
`.github/workflows/nightly.yml`).

| Step | What it measures |
|---|---|
| Into the carpet lane | Moves to y = 2.7, carpet from wall to wall, so the next four steps never cross a table |
| Hover 10 s | `fc/odom` height against the true height, and its vertical speed |
| 4 m pass at 0.3 m/s | flow speed error while the speed is steady, and estimate drift |
| Creep at 1 cm/s for 60 s | how much of a slow movement the estimate misses |
| Creep at 3 cm/s for 30 s | the same, just above the blind spot |
| Across a plain table | 1.7 m to the right over table group 4: how much of the distance flown without flow the estimate misses, and how far the mission overshoots |

The limits live in `drone_bringup/config/sim_test_limits.yaml`, each with the
value it was set from. The missed shares (creeps and table) are bands: they
record how the sim behaves today, and are meant to change when the estimator does. A quick check
of that file runs in every `colcon test`.

Results go to `project/logs/sim_sensors/<date>_<commit>/`: `result.json`, the
test's log with what each step measured, and a rosbag of the flight (kept on
your disk only). The test itself is `drone_bringup/test/test_sim_sensors.py`.

## Sensor specs (MicoAir MTF-02P: rangefinder + optical flow)

Set in `drone_bringup/config/sim.yaml`. σ is the standard deviation of the
noise: about two thirds of the readings land within ±σ of the true value.

| Parameter | Value | Source |
|---|---|---|
| `range_min` | 0.02 m | MTF-02P spec |
| `range_max` | 6.0 m | MTF-02P spec |
| `range_noise` | 0.01 m (σ) | Placeholder from "±2 cm under 2 m"; replace with bench data |
| `range_fov` | 0.070 rad | 2° half-angle, so a 4° full cone |
| `min_height` | 0.08 m | MTF-02P spec: closer than this, the flow reports quality 0 (no usable data) |
| `max_flow_rate` | 7.0 rad/s | MTF-02P spec: 7 m/s at 1 m; faster than this, quality 0 |
| `flow_noise` | 0.01 rad/s (σ) | Placeholder; replace with real bench data |
| `quantize` | true | INAV, not the sensor: rates are sent as whole degrees per second, cut toward zero |
| `seed` | -1 | Sim only: below 0 gives different noise every run; a fixed number repeats the same noise |

# Tags

#simulator