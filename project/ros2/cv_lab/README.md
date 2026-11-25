# cv_lab · OpenCV C++ and YOLO

A sandbox for learning OpenCV in C++ and YOLO object detection. Not a ROS package (`COLCON_IGNORE`), so `colcon build` skips it.

## What is installed, and where

| Piece | Where | Why |
| --- | --- | --- |
| OpenCV 4.6 (C++) | Dev container (`seame-dev`), comes with `ros-jazzy-cv-bridge` | Same version the ROS nodes will use |
| ONNX Runtime (C++) | `third_party/onnxruntime` (in the mounted volume, survives container rebuilds) | Runs the YOLO network. OpenCV 4.6's own DNN module **cannot** load YOLOv8/YOLO11 ONNX models |
| Ultralytics (Python) | Host, venv `~/venvs/yolo` | Only to download and export models to ONNX (and, later, to train) |
| `yolo11n.onnx` | `models/` | YOLO11 nano, 80 COCO classes, input 640×640 |

Models, the sample video, `third_party/` and `build/` are git-ignored; `./setup.sh` (on the host) downloads them again. The Haar cascade comes with OpenCV (`opencv-data`); `setup.sh` downloads it only where that package is missing.

## Build and run (inside the container)

```bash
docker compose exec dev bash
cd ~/ros2_ws/cv_lab
cmake -S . -B build && cmake --build build -j8
./build/00_check_env
```

Every `src/NAME.cpp` becomes `build/NAME` automatically: to add a program, just create a new `.cpp` and build again. Programs whose name starts with `yolo_` are also linked against ONNX Runtime. Run them **from the `cv_lab` folder** (paths like `data/...` are relative).

With no display (`DISPLAY=` before the command) the programs save their images in `out/` instead.

| Program | What it shows |
| --- | --- |
| `00_check_env` | OpenCV version, reading an image |
| `01_image_basics` | `cv::Mat`, pixels, grey, resize, crop (ROI), drawing, saving |
| `02_color_threshold data/lena.jpg` | HSV segmentation with trackbars, morphology |
| `03_edges_contours data/bus.jpg` | Gaussian blur, Canny, contours, polygon approximation |
| `04_video_motion data/vtest.avi` | Video reading, background subtraction (MOG2), motion boxes |
| `05_face_haar data/lena.jpg` | Classic Haar cascade detector |
| `yolo_detect data/bus.jpg` | YOLO11: pre-processing, inference, decoding, NMS, drawing |
| `yolo_detect data/vtest.avi` | Same on video, with FPS |

`yolo_detect` options: `--model models/yolov8n.onnx --conf 0.25 --nms 0.45 --nogui`. In the window: Esc/`q` quits, `s` saves a snapshot to `out/`.

## YOLO on the drone's camera

`yolo_detect` opens a camera directly through V4L2: `./build/yolo_detect /dev/video2` (or just `2`). By default it asks for the FPV receiver's native mode, YUYV 720×576 at 25 fps (see `docs/FPV_Video_Receiver_Setup_UVC_Receiver_to_ROS.md`); for another camera pass `--size 640x480 --fps 30`, and `--fourcc MJPG` for a compressed stream (less USB bandwidth). It keeps only the newest frame, so the image does not fall behind when YOLO is slower than the camera.

1. **The receiver must be visible as `/dev/videoN`:** `ls /dev/video*`.
2. **Find the capture node** (the one that lists formats), inside the container:
   ```bash
   for d in /sys/class/video4linux/video*; do echo "$(basename $d): $(cat $d/name)"; done
   v4l2-ctl -d /dev/video2 --list-formats-ext
   ```
   The container sees new devices without a restart (`/dev:/dev` is mounted and video devices are allowed in `compose.yaml`).
3. **Run it:** `./build/yolo_detect /dev/video2`.

Only one program can open the device at a time: stop `usb_cam` first. To run YOLO **and** keep `/image_raw` for the rest of ROS, YOLO has to become a ROS node that subscribes to `/image_raw` (exercise 15).

## Exporting other YOLO models (host)

```bash
cd project/ros2/cv_lab/models   # from the repository root
~/venvs/yolo/bin/yolo export model=yolov8n.pt format=onnx opset=12 imgsz=640 simplify=True
```

Any detection model (`yolov8*`, `yolo11*`, or your own trained `best.pt`) works with `yolo_detect` as long as the output is `1 × (4 + classes) × anchors`. Visualise a model's layers at <https://netron.app>.

## Exercises

Do them in order; each one is a new file in `src/` (copy the closest example as a starting point).

### Level 1 · Images
1. **Info card.** Read any image and print its size, channels, and the mean and min/max of each channel (`cv::mean`, `cv::minMaxLoc` on `cv::split` channels).
2. **Mirror and rotate.** Show the image flipped horizontally (`cv::flip`) and rotated 30° around its centre (`cv::getRotationMatrix2D` + `cv::warpAffine`).
3. **Manual grey.** Convert to grey with two nested loops over pixels (`at<cv::Vec3b>`, weights 0.299 R + 0.587 G + 0.114 B) and compare the result and the time with `cv::cvtColor`. Then do it again with `img.ptr<cv::Vec3b>(y)`: which is faster, and why?
4. **Histogram.** Draw the grey histogram as an image (`cv::calcHist`), then apply `cv::equalizeHist` and compare both histograms.

### Level 2 · Filters and shapes
5. **Blur bench.** Apply `blur`, `GaussianBlur`, `medianBlur` and `bilateralFilter` to `lena.jpg` with salt-and-pepper noise you add yourself. Which one cleans it best? Show the four side by side (`cv::hconcat`).
6. **Shape classifier.** Draw (with `cv::rectangle`, `cv::circle`, `cv::fillPoly`) a white image with triangles, squares and circles, then use `03_edges_contours` ideas to label each shape by name.
7. **Coloured marker.** Print a coloured circle (or show it on your phone). With `02_color_threshold`, find a good HSV range, then write a program that prints the centre of the biggest blob (`cv::moments`: `cx = m10/m00`). That is what a drone uses to centre itself over a landing pad.

### Level 3 · Video
8. **Video writer.** Read `vtest.avi`, convert to grey + Canny, and write the result with `cv::VideoWriter` (`out/edges.avi`). Print the processing FPS.
9. **Count people crossing a line.** Using `04_video_motion`, draw a horizontal line and count the blobs whose centre crosses it.

### Level 4 · YOLO
10. **Read the code.** In `yolo_detect.cpp`, explain in a comment why the output is transposed, what `scale` corrects, and what happens to the boxes if you remove `NMSBoxes`. Try `--nms 1.0`.
11. **Filter classes.** Add a `--classes 0,2` option that only keeps people and cars. Count people per frame on `vtest.avi`.
12. **Threshold sweep.** On `bus.jpg`, run with `--conf` from 0.1 to 0.9 and note how many detections survive. Where does it start to miss real objects?
13. **YOLOv8 vs YOLO11.** Export `yolov8n` and compare speed (ms) and detections on the same images.
14. **Speed.** Measure separately pre-processing, inference and post-processing time (`cv::TickMeter`). Try `SetIntraOpNumThreads(1)` vs `4`, and input 320 (`imgsz=320` at export). What would you pick for a Raspberry Pi on the drone?
15. **Bridge to the project.** When comfortable, turn `yolo_detect` into a ROS 2 node that subscribes to the camera image (`cv_bridge`) and publishes the detections (e.g. `vision_msgs/Detection2DArray`).
