---
title: Computer Vision on the Ratel 2 Feed
---
# Computer vision on the Ratel 2 feed

## Before you start

The Ratel 2 analog camera already reaches ROS 2 (Robot Operating System 2) as `/image_raw` through the UVC (USB Video Class) receiver ([FPV video into ROS](FPV_Video_Receiver_Setup_UVC_Receiver_to_ROS.md)). This guide builds recognition on top of it in three milestones, each proving more of the chain:

| Milestone | Recognises | Training needed | Proves |
| --- | --- | --- | --- |
| 1. ArUco markers | Printed markers, with 3D position | None | Camera → ROS → detection → mission, and the calibration |
| 2. Pretrained YOLO (You Only Look Once) | 80 everyday classes (person, bottle, chair…) | None | Neural inference in ROS, and its latency |
| 3. Custom YOLO | Your own objects | Your labelled frames | The real task, on real analog images |

Both detectors publish the same message, `vision_msgs/Detection2DArray` on `/perception/detections`, so a consumer of detections does not change when one detector is swapped for the other.

**You need**

- The camera chain working: `ros2 topic hz /image_raw` shows frames from the receiver.
- The drone powered from a LiPo (lithium polymer) battery, props off, VTX (video transmitter) on low power, for every step that needs the live feed. [Battery on or off](Battery_On_Off_Camera_Work.md) says which steps those are.
- A printer, a flat board (cardboard or foam board) and tape.
- For milestones 2 and 3: internet on the host, and ideally an NVIDIA GPU (graphics processing unit) or a Google Colab account for training.

**Where things live.** The container's `~/ros2_ws` is `project/ros2` in the repository (mounted by `compose.yaml`), so everything there survives the container being recreated:

| Folder in `project/ros2` | Holds | In git |
| --- | --- | --- |
| `src/drone_perception/` | The two detector nodes | Yes |
| `src/drone_bringup/launch/perception.launch.py` | Camera node plus one detector | Yes |
| `config/camera/` | Camera calibration files | Yes |
| `tools/` | Checkerboard, marker, frame-extraction and dataset-split scripts | Yes |
| `models/` | ONNX (Open Neural Network Exchange) models | No: `*.onnx` and `*.pt` are ignored; rebuild them with step 6.2 |
| `bags/`, `frames/`, `dataset/` | Recordings, extracted frames, training data | No: ignored, too large |

## Step 1: The container image

`project/Dockerfile` already installs what this guide uses:

- apt: `ros-jazzy-v4l2-camera` (the camera driver node), `ros-jazzy-camera-calibration`, `ros-jazzy-vision-msgs`, `ros-jazzy-image-proc`, `ros-jazzy-cv-bridge`, `python3-opencv` (OpenCV, the Open Source Computer Vision Library) and `python3-pip`.
- pip: `onnxruntime==1.20.1` and `numpy<2`. `numpy<2` keeps pip from replacing the numpy that `cv_bridge` was built against; a numpy 2 upgrade breaks `cv_bridge` with confusing import errors.

Build and enter, from the repository root on the host:

```bash
make build
make shell
```

Check, inside the container:

```bash
python3 -c "import cv2, onnxruntime; print(cv2.__version__, onnxruntime.__version__)"
python3 -c "import cv2; print(hasattr(cv2, 'aruco'))"     # must print True
```

**The camera device.** The receiver appears as a different `/dev/videoN` on each computer. The container sees all of them: `compose.yaml` mounts `/dev`, allows every video device (`device_cgroup_rules: 'c 81:* rmw'`) and adds the host's `video` group (`VIDEO_GID`, written to `.env` by `project/scripts/make-env.sh`). The launch file opens the device named by the `CAMERA_DEVICE` environment variable, or `/dev/video2` when it is unset. The commands below write it as `$CAMERA_DEVICE`; replace it with your device if the variable is unset. `v4l2-ctl --list-devices` lists the devices; the receiver reports itself as `USB Video`.

## Step 2: Calibrate the camera

Calibration measures the lens: focal length, centre and distortion. Marker positions in milestone 1 are only correct with it. It is done once per camera unit, at the resolution in use (640×480 here); a different resolution needs a new calibration.

**The committed calibration.** `project/ros2/config/camera/ratel2.yaml` was made on 20 November 2026 on one of the team's two Ratel 2 units. The units carry no labels yet, so the file does not say which one. Calibration belongs to one physical camera: the other unit needs its own file, made with the steps below and saved under its own name (for example `ratel2_b.yaml`), then passed to the launch file with `camera_info_url:=file:///home/dev/ros2_ws/config/camera/ratel2_b.yaml`.

**2.1 Make a checkerboard.** [`tools/make_checkerboard.py`](../project/ros2/tools/make_checkerboard.py) draws a board of 10×7 squares, which is 9×6 inner corners:

```bash
cd ~/ros2_ws/tools && python3 make_checkerboard.py
```

Print `checkerboard_9x6.png` (it appears in `project/ros2/tools` on the host), tape it perfectly flat to a board, and measure one square with a ruler, in metres (for example 0.024).

**2.2 Run the calibrator.** Terminal 1, the camera node:

```bash
ros2 run v4l2_camera v4l2_camera_node --ros-args \
  -p video_device:=$CAMERA_DEVICE -p image_size:="[640,480]" -p pixel_format:=YUYV
```

Terminal 2, with your measured square size:

```bash
ros2 run camera_calibration cameracalibrator --size 9x6 --square 0.024 \
  --no-service-check --ros-args -r image:=/image_raw
```

A window opens. Hold the board in front of the camera and move it: left and right, up and down, near and far, and tilted in every direction, including into the corners of the image. The X, Y, Size and Skew bars fill up. When they are green and **CALIBRATE** lights up, click it, wait, then click **SAVE**.

**2.3 Keep the result.** SAVE writes `/tmp/calibrationdata.tar.gz`, which is lost with the container. Copy the calibration into the workspace, under a name for this unit:

```bash
cd /tmp && tar -xzf calibrationdata.tar.gz ost.yaml
cp /tmp/ost.yaml ~/ros2_ws/config/camera/ratel2_b.yaml
```

**2.4 Use it.** Restart the camera node with the file:

```bash
ros2 run v4l2_camera v4l2_camera_node --ros-args \
  -p video_device:=$CAMERA_DEVICE -p image_size:="[640,480]" -p pixel_format:=YUYV \
  -p camera_info_url:=file:///home/dev/ros2_ws/config/camera/ratel2.yaml
```

Check in terminal 2: `ros2 topic echo /camera_info --once --field k` prints nine numbers that are not all zero. A warning that the camera name does not match the file is harmless.

## Step 3: The drone_perception package

[`project/ros2/src/drone_perception`](../project/ros2/src/drone_perception) is an `ament_python` package holding both detector nodes:

| Executable | File | Subscribes | Publishes |
| --- | --- | --- | --- |
| `aruco_detector` | `drone_perception/aruco_detector.py` | `image_raw`, `camera_info` | `perception/detections`, `perception/debug_image` |
| `yolo_detector` | `drone_perception/yolo_detector.py` | `image_raw` | `perception/detections`, `perception/debug_image` |

Its `package.xml` depends on `rclpy`, `sensor_msgs`, `vision_msgs`, `cv_bridge`, `python3-opencv` and `python3-numpy`; `onnxruntime` comes from the Dockerfile's pip line, since rosdep has no key for it. `setup.py` registers the two executables as `console_scripts`.

Both nodes subscribe to images with a best-effort QoS (Quality of Service) of depth 1: when a frame takes longer to process than the next one takes to arrive, old frames are dropped, not queued. Each node logs its processing time and the frame's age (from the driver timestamp to the result) every 2 seconds.

## Step 4: Milestone 1, ArUco markers

**4.1 Print markers.** [`tools/make_markers.py`](../project/ros2/tools/make_markers.py) writes markers 0 to 3 of the `DICT_4X4_50` dictionary:

```bash
cd ~/ros2_ws/tools && python3 make_markers.py
```

Print them, keep the white border, and measure the black square's edge in metres (for example 0.10). That number is `marker_size_m` below.

**4.2 The node.** [`aruco_detector.py`](../project/ros2/src/drone_perception/drone_perception/aruco_detector.py) works on OpenCV 4.6 and 4.7+ (the two have different ArUco APIs). Parameters:

| Parameter | Default | Meaning |
| --- | --- | --- |
| `dictionary` | `DICT_4X4_50` | ArUco dictionary name |
| `marker_size_m` | `0.10` | Black square edge, in metres |
| `mask_border_px` | `0` | Pixels blacked out at each edge, where INAV's OSD (on-screen display) text sits |

For each marker it publishes a `Detection2D` with the marker id, its bounding box, and class id `aruco_<id>`. Once a calibration has arrived on `camera_info`, it also fills in the marker's position from `cv2.solvePnP`. The position is in the camera's optical frame, in metres: x right, y down, z straight out of the lens. It is not the drone's body frame.

**4.3 Build and run.**

```bash
cd ~/ros2_ws
colcon build --packages-select drone_perception
source install/setup.bash
```

The workspace is built without `--symlink-install` (as `make ws` does); mixing builds with and without it in the same workspace makes colcon fail on the Python packages.

Terminal 1: the camera node with calibration (step 2.4). Terminal 2:

```bash
ros2 run drone_perception aruco_detector --ros-args -p marker_size_m:=0.10
```

**4.4 Check.**

```bash
ros2 run rqt_image_view rqt_image_view            # pick /perception/debug_image
ros2 topic echo /perception/detections            # ids and positions
ros2 topic hz /perception/detections              # should match the camera rate
```

Done when a marker held in front of the camera gets an outline and an id in the debug image, and its `position.z` changes by about 0.5 when you move it 0.5 m further away. If the OSD text triggers false detections, add `-p mask_border_px:=40`.

## Step 5: One launch file for camera and detector

[`drone_bringup/launch/perception.launch.py`](../project/ros2/src/drone_bringup/launch/perception.launch.py) starts the `v4l2_camera` node (640×480, YUYV) with its calibration, plus one detector chosen by the `detector` argument. `drone_bringup/package.xml` lists `v4l2_camera` and `drone_perception` as `exec_depend`, and its `install(DIRECTORY launch config ...)` line installs the file.

| Argument | Default | Meaning |
| --- | --- | --- |
| `video_device` | `$CAMERA_DEVICE`, or `/dev/video2` if unset | The receiver's device |
| `detector` | `aruco` | `aruco` or `yolo` |
| `marker_size_m` | `0.10` | Passed to `aruco_detector` |
| `model_path` | `/home/dev/ros2_ws/models/yolov8n.onnx` | Passed to `yolo_detector` |
| `camera_info_url` | `file:///home/dev/ros2_ws/config/camera/ratel2.yaml` | Calibration file |

```bash
cd ~/ros2_ws && colcon build --packages-select drone_perception drone_bringup && source install/setup.bash
ros2 launch drone_bringup perception.launch.py
ros2 launch drone_bringup perception.launch.py detector:=yolo   # after step 6.2
```

A launch argument arrives as text, so if `marker_size_m` is rejected as a string, pass it with the decimal point (`marker_size_m:=0.10`), never `1`.

## Step 6: Milestone 2, pretrained YOLO

Training tools (PyTorch, Ultralytics) are large and change often, so they stay out of the ROS container. The model is exported to ONNX on the host; the ROS node only needs `onnxruntime`. The same node runs a custom model from step 7 unchanged.

Ultralytics is licensed AGPL-3.0 (GNU Affero General Public License version 3). Check with the program whether that is acceptable before using it in the corporate capstone.

**6.1 Host: a training environment.**

```bash
sudo apt install python3-venv
python3 -m venv ~/yolo-env
source ~/yolo-env/bin/activate
pip install ultralytics onnx
```

On a host without an NVIDIA GPU, install the CPU-only PyTorch first, before `ultralytics`: it is about 200 MB instead of several GB of CUDA libraries.

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

If `pip install ultralytics` fails because the host's Python is too new for PyTorch, create the environment with Python 3.12 instead (for example `uv venv --python 3.12 ~/yolo-env`), or do steps 6.1, 7.5 and 7.6 in Google Colab.

**6.2 Host: export the model.** Models are not in git; every teammate builds them with this command, from the repository root:

```bash
mkdir -p project/ros2/models && cd project/ros2/models
yolo export model=yolov8n.pt format=onnx imgsz=640 opset=12
```

This downloads `yolov8n.pt` and writes `yolov8n.onnx` next to it. The class names are stored inside the ONNX file, so the node finds them on its own.

**6.3 The node.** [`yolo_detector.py`](../project/ros2/src/drone_perception/drone_perception/yolo_detector.py) letterboxes each frame to the model's input size (resize keeping the aspect ratio, pad to a square), runs it through `onnxruntime` on every execution provider available, and applies non-maximum suppression (`cv2.dnn.NMSBoxes`) to the boxes. Parameters:

| Parameter | Default | Meaning |
| --- | --- | --- |
| `model_path` | empty | ONNX model file |
| `conf_threshold` | `0.4` | Minimum class score |
| `iou_threshold` | `0.5` | IoU (intersection over union) above which overlapping boxes are merged |
| `mask_border_px` | `0` | Pixels blacked out at each edge (OSD text) |

The decoding matches the YOLOv8/YOLO11 ONNX output, one row per candidate box: 4 box values, then one score per class. Other model families (YOLOv5, YOLOv10) lay it out differently and need a different decoder.

**6.4 Build and run.** Both packages are rebuilt: `drone_perception` for the node, `drone_bringup` for the launch file.

```bash
cd ~/ros2_ws
colcon build --packages-select drone_perception drone_bringup
source install/setup.bash
ros2 launch drone_bringup perception.launch.py detector:=yolo
```

**6.5 Check.** Open `/perception/debug_image` in `rqt_image_view` and walk in front of the camera: a green `person` box should follow you. The log line gives inference time and frame age, the first latency numbers. On a laptop CPU (central processing unit), `yolov8n` at 640 takes about 100 ms per frame (measured in 8.4), so it cannot keep up with 30 fps (frames per second): frames are dropped, not queued, because of the depth-1 QoS.

## Step 7: Milestone 3, your own objects

The model learns from frames of this exact analog link: noise, interference, blur and OSD included. That is why the dataset comes from the Ratel 2 itself, not from internet photos. Aim for a few hundred labelled frames per class to start.

**7.1 Record.** Camera node running (terminal 1), then in terminal 2:

```bash
mkdir -p ~/ros2_ws/bags && cd ~/ros2_ws/bags
ros2 bag record --topics /image_raw /camera_info -o cage_01
```

You do not need to fly. Carry the powered drone (props off) around the objects: different distances, angles, heights, lighting, and with the objects partly hidden. Record each session into a new name (`cage_02`, `cage_03`…), a minute or two each.

**7.2 Extract frames.** Consecutive frames are nearly identical, so [`tools/extract_frames.py`](../project/ros2/tools/extract_frames.py) keeps one in every 15 (a third argument changes that):

```bash
cd ~/ros2_ws
python3 tools/extract_frames.py bags/cage_01 frames/raw
python3 tools/extract_frames.py bags/cage_02 frames/raw
```

It reads bags in `mcap` storage. If it fails on the storage format, run `ros2 bag info bags/cage_01` and change `storage_id` in the script to the one it shows (`sqlite3` instead of `mcap`).

**7.3 Label (host).** Label Studio runs in its own environment:

```bash
python3 -m venv ~/ls-env && source ~/ls-env/bin/activate
pip install label-studio
label-studio start                     # opens http://localhost:8080
```

Create a project with the **Object Detection with Bounding Boxes** template, replace the example labels with your classes, and import the images from `project/ros2/frames/raw`. Draw a tight box around every instance of every class in every image; an object you skip teaches the model that it is background. When done, **Export** in **YOLO** format and unzip it to `project/ros2/frames/export`. It contains `images/`, `labels/` and `classes.txt`.

**7.4 Split into train and validation.** [`tools/split_dataset.py`](../project/ros2/tools/split_dataset.py) copies 20 % of the images (with a fixed random seed) into the validation set and writes `data.yaml`. Run it on the host, inside `~/yolo-env`, so the paths in `data.yaml` are host paths. From the repository root:

```bash
source ~/yolo-env/bin/activate
cd project/ros2
python3 tools/split_dataset.py frames/export dataset
```

A random split puts near-identical frames on both sides and makes the scores look better than they are. With several sessions, keep one whole session (for example `cage_03`) only for validation.

**7.5 Train (host or Colab).**

```bash
yolo detect train data=dataset/data.yaml model=yolov8n.pt epochs=100 imgsz=640 batch=16
yolo detect val model=runs/detect/train/weights/best.pt data=dataset/data.yaml
```

On a CPU this takes hours; an NVIDIA GPU or Colab takes minutes. `val` prints mAP50 and mAP50-95 (mean average precision at an IoU of 0.5, and averaged over IoU 0.5 to 0.95) per class: write them down. `runs/detect/train/val_batch0_pred.jpg` shows what the model gets wrong.

**7.6 Export and run.**

```bash
yolo export model=runs/detect/train/weights/best.pt format=onnx imgsz=640 opset=12
cp runs/detect/train/weights/best.onnx models/ratel_v1.onnx
```

In the container:

```bash
ros2 launch drone_bringup perception.launch.py detector:=yolo \
  model_path:=/home/dev/ros2_ws/models/ratel_v1.onnx
```

Same node, same topics; only the model file changed. Give every model a version in its name and note which dataset trained it.

## Step 8: Deploy and measure

The program asks for measured numbers, not just a working demo. Collect the same set for every model and every computer.

**8.1 Numbers to record**

| Number | How to get it |
| --- | --- |
| Accuracy (mAP50, mAP50-95) of the PyTorch model | `yolo detect val model=runs/detect/train/weights/best.pt data=dataset/data.yaml` |
| Accuracy of the exported ONNX model | `yolo detect val model=models/ratel_v1.onnx data=dataset/data.yaml` |
| Inference time per frame | The node's log line, `inference … ms` |
| Frame age at detection | The node's log line, `frame age … ms` (from driver timestamp to result) |
| Detection rate | `ros2 topic hz /perception/detections` |
| Camera-to-driver delay | Not visible in ROS: film a millisecond clock through the camera and compare it with the clock on screen in the debug image |

To keep a run for the report, record detections and the debug image together:

```bash
ros2 bag record --topics /perception/detections /perception/debug_image -o run_ratel_v1
```

**8.2 Laptop with an NVIDIA GPU.** The container needs GPU access (the NVIDIA Container Toolkit on the host) and `onnxruntime-gpu` with a matching CUDA (Compute Unified Device Architecture) instead of `onnxruntime`. The node uses every execution provider `onnxruntime` offers, so it picks the GPU on its own; its startup log then lists `CUDAExecutionProvider`. Compare inference time with the CPU run.

**8.3 Raspberry Pi 5 with the Hailo AI HAT+ (Hardware Attached on Top).** The Hailo accelerator cannot run ONNX directly. The model goes through Hailo's toolchain first:

1. On an x86 Linux machine, install the Hailo Dataflow Compiler and Model Zoo from the Hailo Developer Zone (free account needed).
2. Compile `best.onnx` to a `.hef` (Hailo Executable Format) file for the HAT's chip (`hailo8l` for the 13 TOPS (tera operations per second) version, `hailo8` for 26 TOPS). The compiler quantizes the model to INT8 (8-bit integers), using a calibration set: a few hundred of your own frames from `frames/raw`, not internet images.
3. On the Pi, install the Hailo runtime and run the `.hef` with it. The ROS topics stay the same; only the inference call changes from `onnxruntime` to the Hailo runtime.
4. Measure accuracy again after quantization and compare it with the ONNX number from 8.1. The drop is one of the module's required figures.

The Pi runs Raspberry Pi OS (operating system), not Ubuntu 24.04, so ROS 2 Jazzy runs there in the same Docker image, built for arm64, with the Hailo device passed into the container.

**8.4 Measured on the Ratel 2.** Measured on 25 November 2026 with `perception.launch.py`, the receiver at 640×480 and the calibration `ratel2.yaml`, on a laptop with an AMD Ryzen 7 5700U CPU and no GPU.

ArUco (`DICT_4X4_50`, one printed marker of 0.045 m, id 11):

| Number | Result |
| --- | --- |
| Processing time per frame | 4 to 6 ms |
| Frame age at detection | 7 to 10 ms |
| Distance `z` with the marker held at 0.30 m | 0.291 to 0.305 m (mean about 0.297 m) |
| Distance `z` with the marker held at 0.60 m | 0.577 to 0.634 m (mostly 0.59 to 0.61 m) |
| Farthest detection | about 1.0 m |
| False detections | ids 17 and 45 appeared in 8 frames while only marker 11 was in view |

The spread of `z` grows with distance: about ±0.7 cm at 0.30 m, about ±2 cm at 0.60 m, and about ±4 cm near 1.0 m.

Pretrained YOLO (`yolov8n.onnx`, 640, `CPUExecutionProvider`):

| Number | Result |
| --- | --- |
| Inference time per frame | 85 to 140 ms, peaks of 200 ms |
| Frame age at detection | 100 to 160 ms, peaks of 330 ms |
| Detection rate | about 7 to 10 Hz, with the camera at 30 Hz |
| Scores on objects in view | laptop 0.82 to 0.91, bottle 0.78 to 0.89, chair 0.60 to 0.79 |
| Low-score detections | `dining table` and `refrigerator`, 0.40 to 0.66 |

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `AttributeError: module 'cv2' has no attribute 'aruco'` | An OpenCV build without the contrib modules (often a pip `opencv-python` shadowing the apt one) | `pip uninstall opencv-python`; use the apt `python3-opencv` |
| `cv_bridge` import error mentioning numpy | pip upgraded numpy to 2.x | `pip install --break-system-packages "numpy<2"` |
| Camera node cannot open the device | Wrong `video_device`, or `CAMERA_DEVICE` unset and the receiver is not `/dev/video2` | `v4l2-ctl --list-devices`; pass `video_device:=/dev/videoN` |
| Calibrator window opens but the bars never move | Board not detected: wrong `--size` (count inner corners) or board bent | Use `--size 9x6` for the generated board; tape it flat |
| Markers detected but no positions | Node started without calibration | Check `ros2 topic echo /camera_info --once --field k`; restart the camera node with `camera_info_url` |
| Marker distance off by a fixed factor | Wrong `marker_size_m` | Measure the black square only, without the white border |
| False markers or boxes along the edges | INAV's OSD text | `-p mask_border_px:=40` (adjust to your OSD layout) |
| Marker ids that are not in view appear in single frames | Analog noise decoded as a valid marker | The consumer accepts only the expected ids, and only after several consecutive frames |
| YOLO node exits at start | No model at `model_path` | Run step 6.2; check `ls ~/ros2_ws/models` |
| YOLO node starts, no boxes ever | Confidence too high, or no class names in the model | Check the startup log for the class count; try `-p conf_threshold:=0.25` |
| Boxes in the wrong place | Model is not YOLOv8/YOLO11 layout | Export a YOLOv8 or YOLO11 model, or adapt the decoder |
| Detection rate far below camera rate | Inference too slow for 30 fps | Expected on CPU; use a smaller `imgsz` (for example 416) at export, or the GPU / Hailo |
| `frame age` grows over time | A queue somewhere: subscriber depth above 1 or a reliable QoS | Keep `SENSOR_QOS` with depth 1 on the image subscription |
| colcon fails with "existing path cannot be removed" | The workspace was built once with `--symlink-install` and once without | `make ws-clean`, then build again without it |

## Not verified

- The ONNX metadata key for class names, and the output layout, for Ultralytics versions other than 8.4.216 (the version used in 8.4). If the node logs 0 classes or the boxes are wrong, this is the place to look.
- Whether `ultralytics` and PyTorch install on every host's Python version (step 6.1 has the fallback).
- The Hailo steps in 8.3: tool names, flags and supported models change between Hailo releases. The Hailo Developer Zone documentation for the HAT is the reference; this guide gives no exact `hailomz` commands.
