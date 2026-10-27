# FPV Video Receiver Setup: UVC Receiver to ROS 2

Oct 26, 2026 · @Someone

## Overview

The drone's analog camera now reaches ROS 2. A USB receiver on the ground computer picks up the 5.8 GHz signal, and `usb_cam` inside the container publishes it as `/image_raw` at about 25 Hz.

&#91;embedded content: video path · drone to ROS 2\]

Frames flow one way, from the drone to `/image_raw`. The dashed perception node does not exist yet; it is the next step.

## Hardware and software in use

The chain uses the drone's analog camera and VTX, one USB receiver on the ground computer, and four ROS 2 Jazzy packages inside the `seame-dev` container.

| Part | What it is | Where it runs | Role |
| --- | --- | --- | --- |
| FPV camera | Analog camera, PAL output | Drone | Captures the image |
| 5.8 GHz VTX | Analog video transmitter | Drone | Sends the camera signal over the air |
| UVC receiver | USB receiver, reports itself as `USB Video` | Ground computer USB port | Turns the analog signal into a standard webcam device |
| `/dev/video2` | Capture node of the receiver | Host, mapped into the container | The device `usb_cam` opens |
| `/dev/video3` | Metadata node of the receiver | Host | Not used; lists no formats |
| `usb_cam` | ROS driver (`ros-jazzy-usb-cam`) | Container | Reads the device, publishes `/image_raw` |
| `image_transport` + plugins | Image transport and compression (`ros-jazzy-image-transport`, `ros-jazzy-image-transport-plugins`) | Container | Raw and compressed image topics |
| `cv_bridge` | ROS image to OpenCV (`ros-jazzy-cv-bridge`) | Container | Installed for the perception node; not used yet |
| `rqt_image_view` | Image viewer (`ros-jazzy-rqt-image-view`) | Container | Shows `/image_raw` on screen |
| `v4l-utils` | `v4l2-ctl` command | Container | Lists devices and formats, tests frame rate |
| `mesa-utils` | `glxinfo` command | Container | GPU check only; not in the video path |

The laptop's own webcam (`Integrated Camera`) is `/dev/video0` and `/dev/video1`. It is not part of the chain.

## Container setup

The container needs three things to open the receiver: the device files, permission from Docker's device cgroup, and membership of the `video` group. Missing any one of them gives a different error (see Troubleshooting).

The relevant part of `docker-compose.yml`:

```yaml
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix
      - ./ros2_ws:/home/dev/ros2_ws
      - /dev:/dev                    # all device files, so new video numbers appear too
    devices:
      - /dev/dri:/dev/dri            # GPU
    device_cgroup_rules:
      - 'c 81:* rmw'                 # video4linux: cameras and the UVC receiver
      - 'c 13:* rmw'                 # input: the RadioMaster as a joystick
    group_add:
      - video                        # lets the dev user open /dev/video*
```

- `/dev:/dev` makes the device files visible. On its own it is not enough: Docker still refuses to open them.
- `device_cgroup_rules` allows opening devices by major number: 81 is video, 13 is input. Without it the error is `Operation not permitted`.
- `group_add: video` matches the device files' group (`root video`, mode `crw-rw----`). Without it the error is `Permission denied`.
- Cgroup rules apply only when the container is created. After changing them, run `docker compose down && docker compose up -d`; a restart is not enough.

Packages installed by hand disappear when the container is recreated. Add them to the `Dockerfile`:

```dockerfile
RUN apt-get update && apt-get install -y \
    ros-jazzy-joy \
    ros-jazzy-usb-cam ros-jazzy-image-transport \
    ros-jazzy-image-transport-plugins ros-jazzy-cv-bridge \
    ros-jazzy-rqt-image-view v4l-utils mesa-utils \
 && rm -rf /var/lib/apt/lists/*
```

Rebuild with `docker compose up -d --build`.

## Identifying the receiver device

On this laptop the receiver's capture node is `/dev/video2`. The number is not fixed: it can change with plug order or USB port, so check it before each session.

1. List every video device with its name. This works on the host or in the container, because `/sys` shows the host's devices:

   ```bash
   for d in /sys/class/video4linux/video*; do echo "$(basename $d): $(cat $d/name)"; done
   ```

   Output today: `video0` and `video1` are `Integrated Camera`, `video2` and `video3` are `USB Video`.
2. Confirm the container can open them. Unlike the loop, this only lists devices the container can actually use:

   ```bash
   v4l2-ctl --list-devices
   ```
3. Find the capture node. It is the one that lists formats; the other node of the same device is metadata and lists none:

   ```bash
   v4l2-ctl -d /dev/video2 --list-formats-ext
   ```

`lsusb` is not installed on the host and is not needed. It comes with the `usbutils` package.

## Format choice

We use **YUYV, 720×576, 25 fps**: the native PAL format, uncompressed. It matches what the analog camera really sends.

| Format | Sizes offered | Frame rates | Used? | Why |
| --- | --- | --- | --- | --- |
| YUYV 720×576 | PAL native | 25 fps | Yes | Native signal, no compression delay |
| YUYV 720×480 | NTSC native | 30 fps | Fallback | Use if the camera is switched to NTSC |
| YUYV 640×480 and smaller | Scaled | up to 30 fps | No | Fewer pixels; option later if bandwidth matters |
| MJPG up to 1920×1080 | Upscaled | up to 60 fps | No | No extra detail, JPEG adds delay and artifacts |

An analog camera only produces PAL (720×576 at 25 fps) or NTSC (720×480 at 30 fps). The larger MJPG sizes and 50/60 fps modes are made by the receiver from that same signal.

Signs the camera is NTSC instead: the picture rolls, has a black band at the bottom or looks squashed. Then switch to `image_width:=720 image_height:=480 framerate:=30.0`.

## Running it

First prove the ground side without the drone, then power the drone and lock the receiver's channel.

**Bench safety:** propellers off, VTX antenna attached before plugging in the LiPo, drone stays on the bench. Unplug the LiPo when done; the VTX heats up fast when not flying.

1. Start the camera driver (terminal 1, inside the container):

   ```bash
   ros2 run usb_cam usb_cam_node_exe --ros-args \
     -p video_device:=/dev/video2 \
     -p image_width:=720 -p image_height:=576 \
     -p pixel_format:=yuyv \
     -p framerate:=25.0
   ```
2. Check the rate (terminal 2): `ros2 topic hz /image_raw` should show about 25 Hz.
3. Open the viewer: `ros2 run rqt_image_view rqt_image_view`. Pick `/image_raw` in the dropdown at the top left; use its refresh button if the list is empty.
4. With the drone off, a blue, black or snowy screen is correct. The receiver sends frames even with no signal, so frames alone do not prove reception.
5. Power the drone, with the receiver's antenna attached and the drone 1–2 m away.
6. Long-press the receiver's button (about 2 s). It scans all channels and locks onto the strongest signal.
7. Wave a hand in front of the drone's camera. If the image in rqt follows, the chain works.

Useful checks while it runs:

- `ros2 topic echo /image_raw --once --field encoding` and `--field width` show the format. Never run a plain `echo` on an image topic: it prints every pixel.
- `ros2 topic bw /image_raw` shows the bandwidth.

## Measured results so far

`/image_raw` runs at **24.9 Hz** against a 25 Hz target, with 2.7 ms jitter. The glass-to-screen latency is not measured yet.

| Measure | Value | How measured |
| --- | --- | --- |
| Average rate | 24.91 Hz | `ros2 topic hz /image_raw`, 230-frame window |
| Frame interval, min / max | 36 ms / 80 ms | Same |
| Frame interval, std dev | 2.7 ms | Same |
| Raw bandwidth | about 20.7 MB/s | Calculated: 720 × 576 × 2 bytes × 25 fps |
| Glass-to-screen latency | Not measured | Stopwatch test, see next steps |

The 80 ms maximum is one dropped frame (two intervals). It does not repeat often enough to change the average.

## Troubleshooting

Every row below happened during setup. Check them in this order: device first, then ROS, then the radio link.

| Symptom | Cause | Fix |
| --- | --- | --- |
| `v4l2-ctl: command not found` after recreating the container | Packages installed by hand were wiped | Reinstall, then add them to the `Dockerfile` |
| `v4l2-ctl --list-devices` shows only `Integrated Camera` | Compose mapped the wrong host device (laptop camera) into the container | Mount `/dev:/dev` instead of single `/dev/videoN` entries |
| `Cannot open device /dev/video0` | No `video0` in the container; `v4l2-ctl` without `-d` tries it | Pass `-d /dev/video2` |
| `Failed to open /dev/video2: Operation not permitted` | Docker's device cgroup blocks it | Add `device_cgroup_rules: 'c 81:* rmw'`, then `down` and `up -d` |
| `Permission denied` on `/dev/videoN` | User not in the `video` group | Add `group_add: video`; check with `groups` |
| `topic [/image_raw] does not appear to be published yet` | `usb_cam` was not running | Start `usb_cam_node_exe` first, in its own terminal |
| rqt window empty or grey | No topic selected | Choose `/image_raw` in the dropdown; press refresh |
| rqt shows blue, black or snow | No drone signal: drone off or channel mismatch | Power the drone; long-press the receiver button to scan |
| `RTPS_TRANSPORT_SHM Error ... open_and_lock_file failed` | Stale Fast DDS shared-memory files | Stop all ROS processes, then `sudo rm -f /dev/shm/fastrtps_* /dev/shm/fast_datasharing*` |

These messages are harmless and can be ignored: the missing `default_cam.yaml` calibration file, `unknown control` lines from `usb_cam`, the `amdgpu: os_same_file_description` warning, the `class_loader` warning when rqt closes, and `cannot find name for group ID 992 / 995`.

## Known issues and next steps

The video reaches ROS at the right rate, but nothing is measured end to end, saved in the image, or started by a launch file yet.

| Issue | What can go wrong | Fix |
| --- | --- | --- |
| Latency not measured | The camera-to-ground hop is unknown in the latency budget | Stopwatch test: phone stopwatch in front of the camera next to the rqt screen, photo of both, 3–5 runs, note average and worst |
| VTX channel not recorded | The receiver found it by scan; with two drones in the lab, it may lock onto the wrong one | Read `get vtx` in the INAV CLI, agree one channel per drone with the team, write it here |
| Device number can change | `video_device:=/dev/video2` points at the wrong device after a re-plug | Check with the `/sys` loop each session, or use the stable path in `/dev/v4l/by-id/` |
| Packages not in the image | Lost on every container recreation | Add them to the `Dockerfile` (Container setup) |
| No camera calibration | Fisheye distortion breaks any geometry (distances, positions) | Calibrate with `camera_calibration`, store as `default_cam.yaml` |
| Started by hand | Easy to forget parameters | Add a camera node to a launch file in `drone_bringup`, parameters in YAML |
| Raw video is about 20.7 MB/s | Large bags; heavy for the Raspberry Pi 5 or a network link | Record short bags, or the compressed topic from `image_transport` |

After these, the next step is a perception node: subscribe to `/image_raw`, convert with `cv_bridge` to OpenCV, and log each frame's age from `header.stamp`.
