# vision: faces and people (C++)

Everything the drone will use to see people: find faces, recognise who they are, and
detect people (bodies) to follow them.

| Program | What it does |
|---|---|
| `face_detection` (`main.cpp`) | Finds faces with a Haar cascade. It does not know whose face it is. |
| `enroll` (`enroll.cpp`) | Enrols a person: takes photos and stores their SFace vectors in `gallery.yml`. |
| `recognize` (`recognize.cpp`) | Names the enrolled people on the camera, live. |
| `yolo_detect` (`yolo_detect.cpp`) | Detects people and 79 other object classes with YOLO11/YOLOv8, on an image, a video or a camera. |

`face_common.hpp` holds what `enroll` and `recognize` share: camera, models and gallery.

## Setup

Needs `g++`, `pkg-config`, `libopencv-dev` (OpenCV 4.5.4 or newer) and `python3`.
Run everything from this folder: the paths are relative.

```bash
./download_models.sh   # face models, ONNX Runtime and, if set up, the YOLO model
make                   # builds the programs
```

`download_models.sh` puts the models in `models/` and ONNX Runtime in `third_party/`
(both git-ignored) and skips whatever is already there, so it is safe to run again.

### YOLO model

Ultralytics publishes only the PyTorch weights (`yolo11n.pt`), so `models/yolo11n.onnx` is made
by exporting them with the Ultralytics Python package, once, on the host:

```bash
sudo apt install -y python3-venv
python3 -m venv ~/venvs/yolo && ~/venvs/yolo/bin/pip install ultralytics
./download_models.sh   # now also exports models/yolo11n.onnx
```

Another model: `cd models && ~/venvs/yolo/bin/yolo export model=yolov8n.pt format=onnx opset=12 imgsz=640 simplify=True`,
then `./yolo_detect ... --model models/yolov8n.onnx`. Any detection model whose output is
`1 × (4 + classes) × anchors` works. A different `venv` path: `YOLO=/path/to/yolo ./download_models.sh`.

## Face recognition

1. **YuNet** finds each face: its box and 5 landmarks (eyes, nose tip, mouth corners).
2. **alignCrop** uses the 5 landmarks to rotate and crop the face to 112×112, always in the same position.
3. **SFace** turns the aligned face into a vector of 128 numbers. Faces of the same person
   give similar vectors.
4. The vector is compared with the gallery's by **cosine similarity**: from **0.363**
   (the threshold OpenCV recommends) on, it is the same person.

There is no training: both networks come trained. `enroll` only stores the vectors of the people you enrol.

```bash
./enroll Matheus       # SPACE captures (only with 1 face on screen), ESC saves and quits
./recognize            # ESC quits
```

- Enrol about **10 varied photos** per person: facing the camera, slightly to the side,
  smiling, serious, with and without glasses, under different light. Running
  `./enroll Matheus` again adds photos.
- Another person: `./enroll Someone`.
- Another camera: `./enroll Matheus 2` and `./recognize 2` (the FPV receiver is usually camera 2).
- Another threshold: `./recognize 0 0.5` (stricter) or `./recognize 0 0.3` (looser).
  The number next to the name on screen is the cosine: use it to choose the threshold.

`face_detection` uses OpenCV's own Haar cascade (`/usr/share/opencv4/haarcascades/`, from the
`opencv-data` package). Where that package is missing, `./download_models.sh` puts a copy in `models/`.

## People detection (YOLO)

```bash
./yolo_detect photo.jpg            # image: prints the detections, saves out/result.jpg
./yolo_detect video.mp4            # video
./yolo_detect 2                    # camera 2, e.g. the FPV receiver (/dev/video2)
./yolo_detect 0 --size 640x480 --fps 30 --fourcc MJPG   # a laptop webcam
```

Options: `--model models/yolo11n.onnx --conf 0.25 --nms 0.45 --nogui`. In the window: Esc or `q`
quits, `s` saves a snapshot to `out/`. Without a screen (`--nogui`) it runs 60 frames and prints the timing.

On a camera it asks by default for the FPV receiver's native mode, YUYV 720×576 at 25 fps
([FPV video into ROS](../../docs/FPV_Video_Receiver_Setup_UVC_Receiver_to_ROS.md)), and keeps only
the newest frame, so the image does not fall behind when YOLO is slower than the camera.
Only one program can open a camera at a time: stop `usb_cam` (or `recognize`) first.

## Limitations

- A photo of you on a phone is also recognised as you (no anti-spoofing).
- Small faces (under ~60 px) and profiles are detected worse; with the FPV camera's wide lens,
  faces are only big enough within about 1 m. YOLO finds people much further away.
- `gallery.yml` holds biometric data: it is in `.gitignore` and must never be committed.
