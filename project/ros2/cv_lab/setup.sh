#!/usr/bin/env bash
# Downloads everything cv_lab needs that is not in git: ONNX Runtime, the YOLO model, sample data.
# Run on the HOST (needs Python 3 + internet), from anywhere: ./setup.sh
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p models data third_party

# 1) Sample data
fetch() { [ -f "$2" ] || curl -sSfL -o "$2" "$1"; }
fetch https://ultralytics.com/images/bus.jpg                                          data/bus.jpg
fetch https://raw.githubusercontent.com/opencv/opencv/4.6.0/samples/data/lena.jpg     data/lena.jpg
fetch https://raw.githubusercontent.com/opencv/opencv/4.6.0/samples/data/vtest.avi    data/vtest.avi
fetch https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names       data/coco.names
# Haar cascade for 05_face_haar: only when OpenCV's own copy (opencv-data) is missing
[ -f /usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml ] ||
  fetch https://raw.githubusercontent.com/opencv/opencv/4.6.0/data/haarcascades/haarcascade_frontalface_default.xml \
        models/haarcascade_frontalface_default.xml

# 2) ONNX Runtime C++ (from the official NuGet package: headers + libonnxruntime.so)
if [ ! -f third_party/onnxruntime/include/onnxruntime_cxx_api.h ]; then
  V=${ORT_VERSION:-$(curl -sSf https://api.nuget.org/v3-flatcontainer/microsoft.ml.onnxruntime/index.json \
       | python3 -c "import json,sys;print([v for v in json.load(sys.stdin)['versions'] if '-' not in v][-1])")}
  echo "ONNX Runtime $V"
  tmp=$(mktemp -d)
  curl -sSfL -o "$tmp/ort.nupkg" "https://api.nuget.org/v3-flatcontainer/microsoft.ml.onnxruntime/$V/microsoft.ml.onnxruntime.$V.nupkg"
  python3 -m zipfile -e "$tmp/ort.nupkg" "$tmp/x"
  D=third_party/onnxruntime-$V
  mkdir -p "$D/include" "$D/lib"
  cp "$tmp"/x/build/native/include/*.h "$D/include/"
  cp "$tmp"/x/runtimes/linux-x64/native/libonnxruntime.so "$D/lib/"
  ln -sf libonnxruntime.so "$D/lib/libonnxruntime.so.1"
  ln -sfn "onnxruntime-$V" third_party/onnxruntime
  rm -rf "$tmp"
fi

# 3) YOLO model exported to ONNX (needs the venv with ultralytics, see README)
VENV=${YOLO_VENV:-$HOME/venvs/yolo}
if [ ! -f models/yolo11n.onnx ]; then
  if [ -x "$VENV/bin/yolo" ]; then
    (cd models && "$VENV/bin/yolo" export model=yolo11n.pt format=onnx opset=12 imgsz=640 simplify=True)
  else
    echo "No $VENV/bin/yolo: create the venv first (see README), then run this again."
  fi
fi
echo "Done."
