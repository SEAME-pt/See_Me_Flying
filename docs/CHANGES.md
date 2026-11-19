---
title: What Changed When copy-nando Became main
---
# What changed: copy-nando becomes main

This branch replaces the old `main`. The ROS code is the same code you wrote,
moved into a simpler layout and run through one Makefile. Your work up to
18 November 2026 was brought in; the details are below.

## Tomorrow, first thing

```bash
git fetch && git switch main          # once copy-nando is merged
make build                            # once: the Dockerfile changed
make help                             # every command
```

The [root README](../README.md#using-the-makefile) explains each command and the usual problems (it replaced `Makefile_usage.md`).

## 1. New layout

Everything for the drone is under `project/`. The repo root only has what you
run things with.

| Before (old main) | Now |
|---|---|
| `seame-docker/ros2_ws/src/` | `project/ros2/src/` |
| `seame-docker/scripts/` | `project/scripts/` |
| `seame-docker/ros2_ws/tools/` | `project/scripts/ros2_tools/` |
| `seame-docker/logs/` | `project/logs/` |
| `seame-docker/Dockerfile` | `project/Dockerfile` |
| `seame-docker/compose.yaml` | `compose.yaml` (root) |
| `seame-docker/make-env.sh` | `project/scripts/make-env.sh` |
| `seame-docker/start.sh` | `Makefile` (root) |
| `telemetry/` | `project/telemetry/` |
| `roomodel/room.stl` | `project/ros2/src/drone_bringup/models/room/meshes/room.stl` |

Package renames:

| Before | Now |
|---|---|
| `drone_sim_sensors` | `drone_sim` |
| `drone_basics_py` (radio_teleop) | `drone_teleop` |
| `drone_basics_cpp` (watchdog) | `drone_fc_bridge` (second program, next to fc_bridge) |

## 2. One way to run things: the Makefile

Everything runs from the repo root with `make`. No script needs to be called
by hand.

| Command | What it does |
|---|---|
| `make up` / `make build` | start the container / rebuild the image |
| `make ws` | build the ROS code |
| `make sim-keyboard`, `make sim-joy` | Gazebo with keyboard or RadioMaster; both ask for the camera (FPV, follow, free) |
| `make test`, `make sim-test` | all tests, Gazebo flight test; results in `project/logs/` |
| `make monitor` | Grafana dashboard on http://localhost:3000 |
| `make wifi-rtt`, `make bench-rc`, `make bench-armed`, `make motor-music` | real drone, props off |

## 3. New on this branch

- **Monitoring** (`monitoring/`, package `drone_monitoring`). `metrics_exporter`
  turns the fc_bridge, sensor and safety_manager topics into Prometheus metrics
  on port 9105. `make monitor` starts Prometheus and Grafana with the "Drone
  health" dashboard: armed, active source, battery, hold, FC link, height,
  topic rates and stale topics. The exporter only listens.
- **Watchdog is back and always running.** It is the same code as before, now
  in `drone_fc_bridge`. It watches `/fc/setpoint_velocity` (what fc_bridge
  receives) and warns when nothing arrives for 0.5 s, and when it is back. It
  only warns; fc_bridge's own 0.3 s timeout is what sends zero. Tested in
  `drone_fc_bridge/test/test_watchdog.py`.
- **Camera menu** for the sim, in `sim_keyboard.sh` and `sim_joy.sh`. It
  replaces the camera question `start.sh` used to ask.
- **No emojis** in the scripts or the logbook any more: messages say `Error:`,
  `WARNING:` and `STOP:` instead.

## 4. Your work from other branches, brought in

Everything committed after 13 November on any branch was checked file by file.

| Who | What | Where now |
|---|---|---|
| João | INAV backend on the real drone, sticks over MSP RC OVERRIDE, motor outputs, `MotorOutputs` and `RcChannels` messages, new `FcStatus` fields (`link_ok`, `state_age_s`, `rc_override_active`, `rc_sent`) | `drone_fc_bridge`, `drone_interfaces` (same code as main) |
| João | Bench scripts and motor music | `project/scripts/`, run with `make bench-rc`, `make bench-armed`, `make motor-music` |
| João | Test logbook (15 runs, 2 to 17 Nov) and measurements (`inav_link`, `inav_rc_override`, `motor_music`) | `project/logs/tests/`, `project/logs/measurements/` |
| malves-b | Follow and FPV camera, corrected room mesh | `drone_bringup` (launch argument `camera:=`, `config/gui/`, worlds) |
| Alberto | Computer-vision packages and onnxruntime | `project/Dockerfile` |
| David | `odom_check` (estimator vs ground truth) | `drone_sim`: `ros2 run drone_sim odom_check` |
| Miguel, David | Issue template | `.github/ISSUE_TEMPLATE/` |

**Not brought in, on purpose:**
- `MSPBackend` (`telemetry/Backend/`) is still on its own branch.
- The documentation (`docs/`, READMEs, `GUIDE.md`, `PLAN.md`, `SIM_TELEOP.md`)
  stayed on the `docs` branch. It was reorganized on `docs_update` (Nov 19)
  into `docs/`, `project/*/README.md` and `sprints/`; the
  [root README](../README.md#documentation-map) links every page.

## 5. Removed

| Removed | Why / instead |
|---|---|
| `start.sh`, `smoke_test.sh` | the Makefile |
| `setpoint_pub` and `source:=circle` (drone_basics_py) | Sprint 1 demo, replaced by the mission (`demo:=true` flies a square) |
| `docs/`, `seame-docker/*.md`, `Sprint 2 Planning.pptx` | rewritten on `docs_update`; the old ones are on the `docs` branch |
| `roomodel/` | the same mesh lives in `drone_bringup/models/room/` |

# Tags

#resources
