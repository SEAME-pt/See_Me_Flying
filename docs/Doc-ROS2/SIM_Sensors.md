# Simulated sensors

How the Gazebo sim produces the sensor data the real drone will give us. Each
simulated sensor publishes on the same topic, with the same message type and
units, as the real one will through INAV and `fc_bridge`. Everything above
`fc_bridge` (mission, safety, later the estimator) must not be able to tell
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
rates as whole degrees per second; `fc_bridge` will convert them.

The gyro's rotation over the same moment is needed because tilting the drone
in place also makes the floor appear to slide, without any movement.
Subtracting this body rate leaves only the part caused by actually moving.

### Sign convention

Forward flight gives negative `flow_rate_y`, and flight to the left gives
positive `flow_rate_x`. This was checked by flying in the sim, and the unit
tests in `drone_sim_sensors/test/test_flow_model.py` enforce it, so a wrong
sign fails CI. 

### Topics
| Topic (channel) | Type (layout) | What it is + source |
|---|---|---|
| `/sim/ground_truth` | `nav_msgs/Odometry` | The drone's exact position and speed in the sim. Used only to grade tests, comes from Gazebo odometry, bridged (`gz_bridge.yaml`)|
| `/X3/odom` | `nav_msgs/Odometry` | Internal input of `fc_bridge`, same odometry as above |
| `fc/range` | `sensor_msgs/Range` | Rangefinder: distance to the floor below. Gotten from `fc_bridge`, from ground truth, tilt-corrected, flat floor |
| `fc/optical_flow` | `drone_interfaces/OpticalFlow` | Optical flow: how fast the floor appears to slide past the camera. From `flow_model` (`drone_sim_sensors`) |

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

Test Commands:

```bash
# host
./scripts/stop_sim.sh
docker compose exec -e DISPLAY=$DISPLAY dev bash -c 'cd ~/ros2_ws && source install/setup.bash && ros2 launch drone_bringup sim.launch.py source:=mission radio:=false'

# start.sh -> option 4 shell with 'source install/setup.sh'
ros2 run drone_sim_sensors flow_check --ros-args -p use_sim_time:=true
ros2 action send_goal --feedback /mission/takeoff drone_interfaces/action/Takeoff "{height: 1.0}"
ros2 action send_goal --feedback /mission/goto drone_interfaces/action/Goto "{forward: 4.0, speed: 0.3}"
ros2 action send_goal /mission/land drone_interfaces/action/Land "{}"
```

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
