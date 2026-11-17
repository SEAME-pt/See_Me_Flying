# Simulated sensors

How the Gazebo sim produces the sensor data the real drone will give us. Each
simulated sensor publishes on the same topic, with the same message type and
units, as the real one will through INAV and `fc_bridge`. Everything above
`fc_bridge` (mission, safety) must not be able to tell sim from real, so code
tested in the sim behaves the same on the drone.

Body axes: x forward, y left, z up. Not simulated yet: the IMU (accelerometer
and gyro) needs the new test world, and the barometer is only a fallback if
the rangefinder is used.

## How flow and range work together

The flow sensor is a small downward camera that tracks the floor's texture.
It measures an *angle* per second, not a speed: the floor slides past twice as
fast in the image at half the height. So the rangefinder's height is needed
to turn flow into speed (speed ≈ flow × height). That is why INAV only uses
optical flow together with a rangefinder, and why the MTF-02P, which has both
on one board, solves that problem.

`drone_interfaces/msg/OpticalFlow` mirrors INAV's `MSP2_INAV_OPTICAL_FLOW`
(quality, flow rate X/Y, body rate X/Y), but in rad/s. The body rate (gyro)
is included because tilting in place also makes the floor appear to slide;
subtracting it leaves only real movement.

**Sign convention:** forward flight gives negative `flow_rate_y`, flight to
the left positive `flow_rate_x`. Checked by flying in the sim; the unit tests
in `drone_sim_sensors` fail CI if a sign flips.

## Topics

| Topic (channel) | Type (layout) | What it is + source |
|---|---|---|
| `/sim/ground_truth` | `nav_msgs/Odometry` | The drone's exact position and speed in the sim. Used only to grade tests; Gazebo odometry, bridged (`gz_bridge.yaml`) |
| `fc/range` | `sensor_msgs/Range` | Rangefinder: distance to the floor below. From `fc_bridge`, using ground truth, tilt-corrected, flat floor |
| `fc/optical_flow` | `drone_interfaces/OpticalFlow` | Optical flow: how fast the floor appears to slide past the camera. From `flow_model` |
| `fc/odom` | `nav_msgs/Odometry` | Where the drone thinks it is; what `mission` flies on. From `estimator` |

## Sensor parameters (MicoAir MTF-02P: rangefinder + optical flow)

Set in `drone_bringup/config/sim.yaml`. σ is the standard deviation of the
noise: about two thirds of the readings land within ±σ of the true value.

| Parameter | Value | Source |
|---|---|---|
| `range_min` / `range_max` | 0.02 / 6.0 m | MTF-02P spec |
| `range_noise` | 0.01 m (σ) | Placeholder from "±2 cm under 2 m"; replace with bench data |
| `range_fov` | 0.070 rad | MTF-02P spec: 4° full cone |
| `min_height` | 0.08 m | MTF-02P spec: closer than this, flow quality 0 (no usable data) |
| `max_flow_rate` | 7.0 rad/s | MTF-02P spec: 7 m/s at 1 m; faster than this, quality 0 |
| `flow_noise` | 0.01 rad/s (σ) | Placeholder; replace with bench data |
| `quantize` | true | INAV, not the sensor: rates are sent as whole degrees per second, cut toward zero |

## Estimator (`fc/odom`)

In the sim, `fc/odom` comes from the simulated sensors, not from ground
truth. The `estimator` node stands in for INAV's own estimate:

- **Speed:** flow × distance to the floor.
- **Height:** range × cos(tilt).
- **Position:** speed added up over time, turned into room directions by the
  heading.
- **Vertical speed:** the slope of a line fitted through the last 0.6 s of
  heights. A plain difference between two noisy heights would jump by about
  0.7 m/s and break `mission`'s touchdown check (−0.03 m/s).

Bad data: too close to measure counts as on the ground; nothing in range keeps
the last height; lost flow keeps the last speed for 0.3 s, then assumes the
drone has stopped. `fc_bridge`'s old `fc/odom` (true velocity plus noise) is
switched off in sim (`publish_odom: false`).

## Results

Two checks compare the sim's sensors and estimate with ground truth, at 1 m
height:

- **`flow_check`** turns flow and range into a speed, as INAV does. In steady
  flight at 0.28 m/s it was right to within about 1 cm/s.
- **`odom_check`** compares how far `fc/odom` and ground truth have moved
  since it started:

| Test | Truly moved | Position error | Movement missed |
|---|---|---|---|
| 4 m pass at 0.3 m/s | 4.13 m | 0.12 m | 3 % |
| Creep at 0.9 cm/s, ~90 s | 0.81 m | 0.51 m | 63 % |
| Creep at 2.75 cm/s, ~36 s | 1.30 m | 0.41 m | 31 % |

In effect:

- **Normal flight is fine:** the estimate reads about 3 % short, because the
  flow's whole-degree rounding always cuts toward zero.
- **Slow movement is largely unseen:** below about 1.7 cm/s at 1 m, the flow
  reads zero. Slow drift can build up at 0.3 to 0.5 m per minute while the
  estimate thinks the drone is still. Higher up, the blind spot widens.
- **The sim hides this by default:** the sim drone has no wind and a perfect
  controller, so it only drifts when made to move slowly. The real drone will
  drift on its own (draughts, imperfect control), so something must correct
  it: INAV's accelerometer fusion, or absolute fixes such as visual markers.

## Running the checks

```bash
# host
./scripts/stop_sim.sh
docker compose exec -e DISPLAY=$DISPLAY dev bash -c 'cd ~/ros2_ws && source install/setup.bash && ros2 launch drone_bringup sim.launch.py source:=mission radio:=false'

# start.sh -> option 4 shells, after 'source install/setup.bash'
ros2 action send_goal --feedback /mission/takeoff drone_interfaces/action/Takeoff "{height: 1.0}"

# start one check right before each test (it measures from when it starts)
ros2 run drone_sim_sensors flow_check --ros-args -p use_sim_time:=true
ros2 run drone_sim_sensors odom_check --ros-args -p use_sim_time:=true

# 4 m pass
ros2 action send_goal --feedback /mission/goto drone_interfaces/action/Goto "{forward: 4.0, speed: 0.3}"

# creep (use x: 0.03 for the faster one; stop with Ctrl+C)
ros2 topic pub -r 20 /cmd/manual geometry_msgs/msg/TwistStamped "{header: {frame_id: base_link}, twist: {linear: {x: 0.01}}}"

ros2 action send_goal /mission/land drone_interfaces/action/Land "{}"
```