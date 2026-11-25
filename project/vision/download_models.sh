#!/usr/bin/env bash
# Downloads the models enroll and recognize use, from OpenCV's official
# repositories. Run from anywhere: ./download_models.sh
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p models

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

ls -lh models/
