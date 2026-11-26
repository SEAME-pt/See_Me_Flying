#!/usr/bin/env bash
# Downloads everything the vision programs need that is not in git: the face models,
# ONNX Runtime (C++) and the YOLO model. Run from anywhere: ./download_models.sh
# Safe to run again: whatever is already there is skipped.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p models third_party

ZOO=https://github.com/opencv/opencv_zoo/raw/main/models

fetch() {   # fetch <url> <file>
  if [ -s "$2" ]; then
    echo "already there: $2"
    return
  fi
  echo "downloading: $2"
  curl -fsSL --retry 3 -o "$2.part" "$1"
  mv "$2.part" "$2"
}

# 1) Face models (enroll, recognize)
# YuNet: face detector (box + 5 landmarks), ~230 KB
fetch "$ZOO/face_detection_yunet/face_detection_yunet_2023mar.onnx" \
      models/face_detection_yunet_2023mar.onnx
# SFace: turns an aligned face into a 128-number vector, ~37 MB
fetch "$ZOO/face_recognition_sface/face_recognition_sface_2021dec.onnx" \
      models/face_recognition_sface_2021dec.onnx

# Haar cascade for face_detection: only when OpenCV's own copy (opencv-data) is missing
if [ ! -f /usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml ]; then
  fetch https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/haarcascade_frontalface_default.xml \
        models/haarcascade_frontalface_default.xml
fi

# 2) ONNX Runtime C++ for yolo_detect, from Microsoft's official NuGet package.
# The package (~105 MB) holds every platform; only the headers and the Linux x64
# library (~20 MB) are kept. Same version as the Python onnxruntime in project/Dockerfile.
ORT_VERSION=${ORT_VERSION:-1.20.1}
if [ ! -f third_party/onnxruntime/include/onnxruntime_cxx_api.h ]; then
  tmp=$(mktemp -d)
  fetch "https://api.nuget.org/v3-flatcontainer/microsoft.ml.onnxruntime/$ORT_VERSION/microsoft.ml.onnxruntime.$ORT_VERSION.nupkg" \
        "$tmp/ort.nupkg"
  python3 -m zipfile -e "$tmp/ort.nupkg" "$tmp/x"
  D=third_party/onnxruntime-$ORT_VERSION
  mkdir -p "$D/include" "$D/lib"
  cp "$tmp"/x/build/native/include/*.h "$D/include/"
  cp "$tmp"/x/runtimes/linux-x64/native/libonnxruntime.so "$D/lib/"
  ln -sf libonnxruntime.so "$D/lib/libonnxruntime.so.1"
  ln -sfn "onnxruntime-$ORT_VERSION" third_party/onnxruntime
  rm -rf "$tmp"
fi

# 3) YOLO11 nano exported to ONNX (yolo_detect). Ultralytics publishes only the .pt
# weights, so the export needs its Python package (see README.md, "YOLO model").
YOLO=${YOLO:-$HOME/venvs/yolo/bin/yolo}
if [ ! -f models/yolo11n.onnx ]; then
  if [ -x "$YOLO" ]; then
    (cd models && "$YOLO" export model=yolo11n.pt format=onnx opset=12 imgsz=640 simplify=True && rm -f yolo11n.pt)
  else
    echo "No $YOLO: models/yolo11n.onnx not made. Set up the venv (README.md, \"YOLO model\") and run this again."
  fi
fi

ls -lh models/
