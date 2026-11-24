# Using the Makefile

Run everything from the repo root. `make` lists all commands.

## Start

```bash
make up      # start the container (first time: builds the image)
make ws      # build the ROS code
```

After pulling a change to `project/Dockerfile`, run `make build` once.

## Simulation

```bash
make sim-keyboard   # Gazebo + keyboard (the drone starts armed)
make sim-joy        # Gazebo + RadioMaster Pocket over USB
make sim-stop       # stop the sim
```

Both ask for the camera before starting:

```
1) FPV (the drone's front camera)
2) Follow mode (behind the drone)
3) Normal camera (free)
```

With the RadioMaster (`sim-joy`):

1. Plug it in by USB and choose **USB Joystick (HID)** on the radio.
2. Arm: switch **SA** off, throttle stick in the **middle**, SA on.
3. Fly: flip the **takeover** switch (other shoulder) on.
4. SA off disarms at once, even in the air.

## Monitoring

```bash
make monitor        # Grafana dashboard on http://localhost:3000
make monitor-stop   # stop it (its data is kept)
```

The dashboard shows data while a sim or the drone stack runs.

## Tests

```bash
make test       # all tests (~2 min)
make sim-test   # full Gazebo flight (~2 min)
```

Results go to `project/logs/`.

## Real drone (laptop on the drone's Wi-Fi)

**Props off** for the bench runs. They are interactive: they tell you what to do with the radio.

```bash
make wifi-rtt NOTE="bench, AP mode"      # Wi-Fi round trip to the FC
make bench-rc                            # ROS sticks through MSP RC OVERRIDE, unarmed
make bench-armed                         # armed, ROS drives the motors
make motor-music MODE=calibrate          # the motors play a song
make motor-music MODE=play SONG=path/song.rtttl
```

Results go to `project/logs/measurements/`.

## Other

```bash
make shell           # terminal inside the container
make logs            # follow the container's output
make down            # stop the container (and monitoring)
make build           # rebuild the image after changing project/Dockerfile
make ws-clean        # delete the build, then run make ws
make clean-volumes   # also delete the Gazebo model cache and monitoring data
```

## Problems

- **"seame-dev is already in use"**: another copy of the repo has its container running. Run `docker rm -f seame-dev`.
- **"Gazebo is already running"**: `make sim-stop`
- **"Package not found"**: `make ws`
- **"make-env.sh: Permission denied"**: `chmod +x project/scripts/make-env.sh`
- **Joystick not found** (`ls /dev/input/js*` shows nothing): try another USB cable or port. `journalctl -kf | grep -i usb` must not show `error -71`.
- **Drone ignores the RadioMaster**: it isn't armed. Centre the throttle, then flip SA off and on.
- **Grafana shows NO DATA**: start a sim first.



## ros2 run drone_sim depth_view --ros-args -p use_sim_time:=true