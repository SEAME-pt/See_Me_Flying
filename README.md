# See Me Flying — Autonomous Indoor Drone

SEA:ME 2.0 drone track · Team 4 · last updated Oct 27, 2026

An indoor autonomous drone built on a Pilotix Brook 2.5" running **INAV 9.1.1**, commanded from a **ROS 2 Jazzy** ground stack over Wi-Fi (MSP through an ESP8266). The drone flies in a room of at most 10 × 10 m, without GPS.

## Quick reference

| Item | Value |
| --- | --- |
| **`ROS_DOMAIN_ID`** | **`42`** |
| ROS 2 distro | Jazzy (Docker container `seame-dev`) |
| Simulator | Gazebo Harmonic, world `multicopter_velocity_control.sdf`, drone X3 |
| Flight controller | OddityRC F7 40A AIO (STM32F722), INAV 9.1.1, custom target `ODDITYRCF7AIO` |
| FC ↔ ground link | ESP-12E/F (ESP8266, MicroPython), Wi-Fi AP `SeeMeFlying`, TCP `192.168.4.1:5760`, UART 115200 baud |
| Radio | RadioMaster Pocket, ExpressLRS 4.0, 2.4 GHz |
| Video | Caddx Ratel 2 analog → 5.8 GHz VTX → USB UVC receiver → ROS `/image_raw` |
| Ground station | Raspberry Pi 5 (16 GB, AI HAT+) and team laptops |

### ROS_DOMAIN_ID = 42

The SEA:ME network is shared between teams. ROS 2 nodes only discover each other when they share the same `ROS_DOMAIN_ID`, so **every machine and container on our team must use `42`**, and no other team may use it. Valid range is 1–101 (`0` is the default and likely used by others by accident; above 101 can clash with OS ephemeral ports).

It is already the default everywhere in the repo:

- `seame-docker/compose.yaml` → `ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-42}`
- `seame-docker/.env.example` → `ROS_DOMAIN_ID=42`
- `seame-docker/make-env.sh` → prompts with `[42]` as default

Check it inside the container:

```bash
echo $ROS_DOMAIN_ID   # must print 42
```

On the Raspberry Pi or any machine running ROS outside Docker, add `export ROS_DOMAIN_ID=42` to `~/.bashrc`.

> The CI tests in `drone_fc_bridge` (on the `test` branch) deliberately use `ROS_DOMAIN_ID=199` with `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`, so test runs never leak onto the team domain.

## Architecture

```
                         ┌──────────────── Ground station (ROS 2 Jazzy, domain 42) ───────────────┐
 setpoint_pub / radio_teleop / keyboard ──► /fc/setpoint_velocity ──► fc_bridge ──┬─► sim backend ──► ros_gz_bridge ──► Gazebo (X3)
                         watchdog (listens only) ◄────────────────────────────────┘
                                                                                  └─► inav backend (planned) ── MSP over TCP/UDP
                                                                                                │
                                                                                     Wi-Fi (AP "SeeMeFlying")
                                                                                                │
 Drone:  ESP-12 (MicroPython, UART⇄TCP bridge) ── UART ── OddityRC F7 (INAV 9.1.1) ── ESCs/motors
         ThoneFlow-3901U optical flow ── UART ──┘          ELRS receiver ◄── RadioMaster Pocket (arming, failsafe)
         Caddx Ratel 2 ── VTX 5.8 GHz ──────────────────► UVC receiver ──► usb_cam ──► /image_raw
```

Key design rules:

- **`fc_bridge` is the only node allowed to command the drone.** All sources publish to `/fc/setpoint_velocity`; the bridge clamps and forwards them.
- **Arming stays on the radio.** ROS never arms the real drone. The sim-only "enable" topic will not exist in the `inav` backend.
- **Two failsafe layers.** ROS side: `fc_bridge` sends zero velocity (hover) when setpoints go stale. FC side: INAV's RX failsafe (`DROP`, 1.5 s guard) if the radio link is lost. `msp_override_failsafe` is OFF, so Wi-Fi can't keep the drone flying on radio loss.

## Repository layout

```
See_Me_Flying/
├── README.md                     ← this file
├── seame-docker/                 ROS 2 Jazzy dev container + workspace
│   ├── GUIDE.md                  container setup, step by step
│   ├── Dockerfile, compose.yaml, .env.example, make-env.sh
│   └── ros2_ws/src/
│       ├── drone_bringup/        launch files + YAML config
│       ├── drone_fc_bridge/      fc_bridge (C++) – the only node that commands the drone
│       ├── drone_basics_py/      setpoint_pub (Python), radio_teleop on `test`
│       └── drone_basics_cpp/     watchdog (C++)
├── telemetry/                    INAV ⇄ Wi-Fi bridge
│   ├── main.py                   MicroPython for the ESP12 (UART ⇄ TCP)
│   ├── inav_telemetry.py         MSP telemetry reader for the ground computer
│   └── README.md                 flashing + usage + every telemetry field
├── docs/
│   ├── README.md                 hardware: drone parts, modules, mounts, limitations, wiring
│   ├── Drone_Firmware_Choices.md why INAV (vs ArduPilot / Betaflight), custom target, calibration
│   ├── Drone_INAV_Backup_26_10_26.md   current INAV `diff all`
│   ├── Drone_Betaflight_Backup.md      original Betaflight 4.5.1 config (fallback)
│   ├── Doc-ROS2/
│   │   ├── Drone-SIM-Stack.md    every sim node, topic, parameter, known issue
│   │   └── FPV_Video_Receiver_Setup_UVC_Receiver_to_ROS.md
│   ├── sprints/                  sprint plans (Sprint 0, ALL 1.1–1.4 decisions)
│   ├── 3D Print Files/           STL mounts for ESP12 and PMW3901 + slicer profile
│   ├── extras/wire_diagram.png
│   ├── Sources.md
│   └── pull_request_template.md
└── .assets/                      diagrams and the hardware/software choices note
```

## Getting started (simulation)

Prerequisites: Linux host (Ubuntu 22.04–26.04 or Arch), Docker Engine with the Compose plugin (**not** Docker Desktop — `network_mode: host` breaks ROS discovery there), your user in the `docker` group.

```bash
git clone https://github.com/SEAME-pt/See_Me_Flying.git
cd See_Me_Flying/seame-docker
./make-env.sh 42                 # writes .env with your UID/GID, ROS_DOMAIN_ID=42 and GPU groups
docker compose build             # first time: a few minutes
docker compose up -d
docker compose exec dev bash     # shell inside; repeat for more terminals
```

Inside the container:

```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch drone_bringup sim.launch.py
```

Gazebo opens, the drone climbs for 4 s at 0.3 m/s, then flies circles of 0.6 m radius. On the `test` branch the launch also takes `source:=circle|joy|none` (circle flight, RadioMaster Pocket via USB, or keyboard/manual) and `world:=<sdf>`.

Full setup and troubleshooting: [`seame-docker/GUIDE.md`](seame-docker/GUIDE.md).

| Daily task | Command |
| --- | --- |
| Start container | `docker compose up -d` |
| Open shell | `docker compose exec dev bash` |
| Stop | `docker compose down` |
| Rebuild image | `docker compose build && docker compose up -d` |

## ROS 2 stack

| Process | Language | Package | Role |
| --- | --- | --- | --- |
| `gz sim` | C++ (not a ROS node) | `ros_gz_sim` | Physics, X3 quadcopter with built-in velocity controller |
| `parameter_bridge` | C++ | `ros_gz_bridge` | Copies `/X3/gazebo/command/twist`, `/X3/enable` (ROS→Gz) and `/clock` (Gz→ROS) |
| `fc_bridge` | C++ | `drone_fc_bridge` | 20 Hz; clamps setpoints, sends zero velocity when stale |
| `watchdog` | C++ | `drone_basics_cpp` | Logs when setpoints stop/resume; commands nothing |
| `setpoint_pub` | Python | `drone_basics_py` | Test source: takeoff then circle; placeholder for `mission` |

`fc_bridge` limits (all live-tunable with `ros2 param set`, doubles only):

| Parameter | Value |
| --- | --- |
| `setpoint_timeout_s` | 0.3 s |
| `max_speed_xy` | 0.5 m/s (direction kept, speed capped) |
| `max_speed_z` | 0.3 m/s |
| `max_yaw_rate` | 1.0 rad/s |

Contract topic: **`/fc/setpoint_velocity`** (`geometry_msgs/TwistStamped`, frame `base_link`).

Agreed targets for the real link (ALL 1.1): control loop **50 Hz** (minimum 20 Hz), bridge watchdog **200 ms**.

Details for every node, parameter and known issue: [`docs/Doc-ROS2/Drone-SIM-Stack.md`](docs/Doc-ROS2/Drone-SIM-Stack.md).

## Hardware

| Part | Model | Notes |
| --- | --- | --- |
| Frame | Pilotix Brook 2.5" cinewhoop | Prop guards; high-KV motors (short battery life) |
| Flight controller | OddityRC F7 40A AIO, STM32F722RET6 (512 KB flash) | 5 UARTs; too little flash for ArduPilot |
| Receiver | ELRS 2.4 GHz | Replaced the original TBS Crossfire antenna |
| Camera / VTX | Caddx Ratel 2 + PandaRC VT5804 Bat Lite (5.8 GHz) | Analog; `vtx_power` far too high for indoor use |
| Optical flow | ThoneFlow-3901U (PMW3901) | UART, no rangefinder; notch points to the back |
| Wi-Fi | ESP-12E/F (ESP8266), MicroPython | Replaces the GoPro mount |
| Radio | RadioMaster Pocket | ELRS 4.0 |
| 3D printer | Wanhao Duplicator 12/230 | Mounts sliced with PrusaSlicer |

Wiring plan (Sprint 0): ESP8266 → **UART1** (5 V), ThoneFlow → **UART4** (3.3 V), UART6 free for add-ons. Diagram: [`docs/extras/wire_diagram.png`](docs/extras/wire_diagram.png). Full hardware write-up: [`docs/README.md`](docs/README.md).

## Flight controller (INAV)

- **INAV 9.1.1** on custom target `ODDITYRCF7AIO`, derived from `AOCODARCF722AIO` (gyro `CW180_DEG → CW90_DEG`, LEDs on PA14/PA13, sensor scale 250 → 179).
- **Why INAV:** ArduPilot doesn't fit in 512 KB; Betaflight has no autonomous modes and no ThoneFlow/optical-flow position hold. INAV has baro altitude hold, controlled emergency landing and optical-flow support.
- **Arming:** ARM on AUX1 (ch5) and PREARM on AUX2 (ch6), active at 1700–2100. Two-switch interlock.
- **Failsafe:** `DROP` on radio loss, 1.5 s guard.
- **Calibration:** accelerometer gains X 4096 / Y 4098 / Z 4095; board alignment fixed from the Sensors tab.
- **Motors:** DSHOT300, 12 poles, props-out, Bluejay ESCs.

Backups: [`docs/Drone_INAV_Backup_26_10_26.md`](docs/Drone_INAV_Backup_26_10_26.md) (current) and [`docs/Drone_Betaflight_Backup.md`](docs/Drone_Betaflight_Backup.md) (original). Reasoning: [`docs/Drone_Firmware_Choices.md`](docs/Drone_Firmware_Choices.md).

## Telemetry over Wi-Fi

The ESP12 runs [`telemetry/main.py`](telemetry/main.py): it opens its own access point and passes every byte between a TCP client and the FC UART (no MSP parsing on the ESP).

| Setting | Value |
| --- | --- |
| SSID | `SeeMeFlying` (password in `main.py` — change it before flashing) |
| Address | `192.168.4.1:5760` (TCP) |
| UART baud | 115200, must match the MSP port in INAV |

On the ground computer, join `SeeMeFlying` and run:

```bash
python3 telemetry/inav_telemetry.py                    # readable output, 5 Hz
python3 telemetry/inav_telemetry.py --info --rate 2    # JSON lines
python3 telemetry/inav_telemetry.py --log flight.jsonl # also save to file
```

It reads attitude, altitude, battery, RC channels, motors, arming blockers, active modes and more. Flashing steps and the meaning of every field: [`telemetry/README.md`](telemetry/README.md).

> **Transport decision (ALL 1.2):** TCP for now, because we are configuring INAV and reading telemetry, where reliability and easy debugging matter more than latency. Once ROS commands the real drone, a late command is worse than a lost one, so control traffic should move to **UDP**. The sprint doc evaluated MSPWifiBridge vs ESP-link; the current implementation is our own MicroPython transparent bridge.

## FPV video into ROS

USB UVC receiver on the ground computer (`/dev/video2`) → `usb_cam` in the container → **`/image_raw`** at ~25 Hz, view with `rqt_image_view`. The container needs the device mapped, the cgroup rule, and the `video` group. Guide: [`docs/Doc-ROS2/FPV_Video_Receiver_Setup_UVC_Receiver_to_ROS.md`](docs/Doc-ROS2/FPV_Video_Receiver_Setup_UVC_Receiver_to_ROS.md).

## Status and roadmap

| Sprint | Period | Focus |
| --- | --- | --- |
| Sprint 0 ✔ | 6–16 Oct 2026 | Onboarding, dev container, wiring plan, INAV flashing, setpoint publisher + watchdog |
| Sprint 1 ⏳ | 19 Oct – 1 Nov 2026 | INAV telemetry over Wi-Fi, sim stack + teleop, FPV video to ROS, CI |

**Done:** INAV flashed and calibrated · ESP12 telemetry bridge · sim stack flying in Gazebo · FPV video in ROS · NaN guard and teleop (on `test`).

**Next (before touching real motors):**

- `inav` backend in `fc_bridge` (MSP over the ESP link) — no sim-only enable, check `header.stamp` latency
- State back from the drone/sim: `fc/odom`, `fc/imu`, `fc/attitude`, `fc/battery`, `fc/status`
- `drone_interfaces` package (`FcStatus`), services `fc/arm` (refused on hardware) and `fc/hold`
- `safety_manager` (grows out of the watchdog) and `mission` node (takeoff, waypoints, landing; replaces `setpoint_pub`)
- Perception node on `/image_raw`; optical-flow position hold indoors

Sprint docs: [`docs/sprints/`](docs/sprints/).

## Team

| Member | Areas |
| --- | --- | --- |
| Miguel | Hardware, Stack |
| João | ROS, Hardware |
| Carlos | ROS, Stack |
| David | INAV, ROS |
| Fernando | Stack, INAV |
| Matheus | INAV, ROS |

## Branches and contributing

| Branch | Purpose |
| --- | --- |
| `main` | Stable, reviewed work |
| `test` | Integration branch; newest ROS stack (teleop, `sim.yaml`, failsafe tests) |
| `docs`, `inav_docs`, `INAV/telemetry`, `feature/*`, `ci/*` | Feature work, merged by pull request |

- Open a PR into `main` using [`docs/pull_request_template.md`](docs/pull_request_template.md) and link the issue.
- **CI** (`ci/workflow` branch, `.github/workflows/ci.yml`): on push/PR to `main` or `test`, builds `seame-docker/ros2_ws` in the plain `ros:jazzy` image and runs `colcon test`. Run it locally first:

  ```bash
  cd ~/ros2_ws && rm -rf build install log
  rosdep install --from-paths src --ignore-src -y
  colcon build && colcon test && colcon test-result --verbose
  ```

- Never commit `.env`, `ros2_ws/build/`, `install/` or `log/`.

## Sources

PX4 PMW3901 docs · Pilotix Brook · OddityRC F7 40A AIO · MicroPython ESP8266 · Wanhao D12/230 · INAV docs — links in [`docs/Sources.md`](docs/Sources.md).