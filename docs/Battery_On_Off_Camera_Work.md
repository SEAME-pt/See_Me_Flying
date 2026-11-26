---
title: Battery On or Off for Camera Work
---
# Battery on or off: step-by-step for the camera and vision work

## The short rule

**The battery is on only when you need the live picture from the Ratel 2.** Everything else (Docker, code, builds, training, labelling, and testing detectors on recordings) runs with the battery off.

The practical consequence: record once with the battery on, then develop for hours on the recording with the battery off. That saves LiPo (lithium polymer) battery cycles, keeps the VTX (video transmitter) from overheating, and makes tests repeatable.

**What powers what**

| Part | Battery off, FC (flight controller) on USB (Universal Serial Bus) | Battery on (LiPo) |
| --- | --- | --- |
| UVC (USB Video Class) receiver on the computer | On (powered by the computer's USB) | On |
| Flight controller and INAV | On | On |
| Ratel 2 camera | Maybe, if its pad is on the 5 V rail that USB feeds | On |
| VTX (5.8 GHz video transmitter) | Usually off: it runs from battery voltage | On, transmitting |
| ESP8266 Wi-Fi bridge | Not needed for video | Not needed for video |

Without the VTX nothing reaches the receiver, so with the battery off the receiver shows a **solid blue frame**. The camera node, `/image_raw` and the viewers all still run; they just carry a blue picture. Blue means "no signal", not "broken".

## Before you connect the battery

Run through this every time, in this order.

1. **Props off.** Check all four.
2. **VTX antenna on.** Powering a VTX without its antenna can destroy it. Receiver antenna on too.
3. **Battery checked.** No puffing, dents or damaged wires. Check its voltage: a charged 4S pack (four cells in series) reads about 16.8 V.
4. **Smoke stopper** between battery and drone, at least for the first power-up after any soldering.
5. **LiPo on a fireproof surface or in a LiPo bag**, never on a laptop or paper.
6. **Radio on first,** with the kill switch in the safe position, even though you will not arm.
7. **Software ready before power.** Start the camera node and viewer first (they show blue), so the battery is not running while you type commands.
8. **Connect the battery.** The blue frame should change to the camera picture within a few seconds.

**While it runs**

- **VTX heat.** On the bench there is no airflow, and the VTX gets hot fast. Keep it on its lowest power level and limit sessions to about 5 minutes, then unplug and let it cool.
- **Do not arm.** The camera and VTX work disarmed.
- **Watch the voltage** in INAV's OSD (on-screen display). Stop at about 14.0 V (3.5 V per cell) and do not go lower.
- **Never leave a connected LiPo unattended.**

**Optional: skip the LiPo on the bench.** A bench power supply set to 15–16 V with a current limit of about 1 A powers the drone like a battery, with no cycles used and a built-in current limit. Check with your instructor that the flight controller accepts it.

## A session, step by step

Group the work so the battery is on for two short windows only. Step numbers in brackets refer to [Computer vision on the Ratel 2 feed](Computer_Vision_Ratel2.md). `$CAMERA_DEVICE` is the receiver's device (that guide's step 1 says how to find it).

**Phase A: preparation (battery OFF)**

1. Build or update the container, write code, `colcon build`.
2. Print the checkerboard and markers; measure them.
3. Plug in the receiver and start the camera node. A blue frame at about 30 fps (frames per second) confirms the whole software side:

```bash
# terminal 1
ros2 run v4l2_camera v4l2_camera_node --ros-args \
  -p video_device:=$CAMERA_DEVICE -p image_size:="[640,480]" -p pixel_format:=YUYV
# terminal 2
ros2 topic hz /image_raw
```

**Phase B: capture (battery ON, about 5 minutes)**

4. Run the safety checklist and connect the battery. The picture appears.
5. Calibrate (step 2.2): click **CALIBRATE**, then **SAVE**.
6. Record what you will need later, camera info included, so replays behave like the live camera:

```bash
cd ~/ros2_ws/bags
ros2 bag record --topics /image_raw /camera_info -o markers_01      # markers in view
ros2 bag record --topics /image_raw /camera_info -o cage_01         # objects for training
```

7. Disconnect the battery. The frame goes blue again; that is expected.

**Phase C: development (battery OFF, as long as you like)**

8. Save the calibration (steps 2.3 and 2.4).
9. Write and tune detectors against the recordings, not the live drone (see "Working with the battery off").
10. Extract frames, label, train and export models (step 7).

**Phase D: live test (battery ON, about 5 minutes)**

11. Safety checklist, connect the battery.
12. Run the detector on the live feed and record the numbers for the report (step 8.1):

```bash
ros2 launch drone_bringup perception.launch.py
cd ~/ros2_ws/bags && ros2 bag record --topics /perception/detections /perception/debug_image -o live_test_01
```

13. Disconnect the battery.

## Every step of the vision guide: battery on or off

| Vision guide step | Battery | Why |
| --- | --- | --- |
| 1 Container image | OFF | Software only |
| 2.1 Make and print the checkerboard | OFF | Software and printer |
| 2.2 Run the calibrator | **ON** | Needs the live picture of the board |
| 2.3 Copy the calibration file | OFF | File copy; works as long as the container was not recreated since SAVE |
| 2.4 Restart the node with the calibration, check `camera_info` | OFF | `camera_info` is published even on a blue frame |
| 3 The `drone_perception` package | OFF | Code |
| 4.1 Make and print markers | OFF | Software and printer |
| 4.2–4.3 Build the ArUco node | OFF | Code |
| 4.4 Check marker detection | OFF on a bag, **ON** for the live check | Develop on `markers_01`; confirm live once |
| 5 Launch file: build | OFF | Code |
| 5 Launch file: run | OFF on a bag, **ON** live | The launch file starts the camera node, so live needs power |
| 6.1–6.2 Training environment, export YOLO (You Only Look Once) | OFF | Host software |
| 6.3–6.4 Build and run the YOLO node | OFF on a bag | Any recording with people or objects works |
| 6.5 Live check and first latency numbers | **ON** | Needs the live feed |
| 7.1 Record the dataset | **ON** | The only way to get real frames |
| 7.2–7.6 Extract, label, split, train, export | OFF | All offline |
| 8.1 Accuracy (`yolo detect val`) | OFF | Runs on the labelled dataset |
| 8.1 Latency, frame age, detection rate | **ON** | Must be measured on the live chain |
| 8.2–8.3 GPU (graphics processing unit) or Hailo setup | OFF | Setup; then one ON session to measure |

Counted up: calibration, dataset recording and the final live measurements are the only steps that truly need power.

## Working with the battery off

A recording replays `/image_raw` and `/camera_info` exactly as the camera published them, so the detector nodes cannot tell the difference. Do not run the camera node at the same time, or two sources publish on `/image_raw`.

Terminal 1, replay in a loop:

```bash
cd ~/ros2_ws/bags
ros2 bag play markers_01 --loop
```

Terminal 2, the detector on its own (not the launch file, which would also start the camera node):

```bash
ros2 run drone_perception aruco_detector --ros-args -p marker_size_m:=0.10
# or
ros2 run drone_perception yolo_detector --ros-args \
  -p model_path:=/home/dev/ros2_ws/models/yolov8n.onnx
```

Terminal 3, look at the result:

```bash
ros2 run rqt_image_view rqt_image_view            # pick /perception/debug_image
ros2 topic echo /perception/detections
```

Useful while tuning: `ros2 bag play markers_01 --loop --rate 0.5` plays at half speed, and `ros2 bag info markers_01` shows what a recording contains.

Two things you cannot measure on a recording: latency and frame rate under real conditions. The frame age the node logs during replay reflects the replay, not the camera chain. Measure those in Phase D.

## Ending a session

1. Stop recording (Ctrl-C), then disconnect the battery. Unplugging first is fine for the drone, but you would capture blue frames at the end of the bag.
2. Check the bag: `ros2 bag info bags/<name>` shows the duration and message count.
3. Let the VTX cool before the next power-up.
4. If the battery will not be used again within a day or two, bring it to storage voltage (about 3.8 V per cell, 15.2 V for 4S) with the charger's storage mode. Follow the class's LiPo handling rules.

## Not verified

- Whether the flight controller's camera pad is powered over USB; this decides if the camera alone runs with the battery off. It does not change the procedure, since the VTX needs the battery anyway.
- The exact voltage limits, VTX power levels and bench-supply settings for this flight controller and VTX. Check them against the hardware docs or with the instructor.
