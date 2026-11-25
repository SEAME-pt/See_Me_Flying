# vision: face detection and face recognition (C++)

| Program | What it does |
|---|---|
| `face_detection` (`main.cpp`) | Finds faces with a Haar cascade. It does not know whose face it is. |
| `enroll` (`enroll.cpp`) | Enrols a person: takes photos and stores their SFace vectors in `gallery.yml`. |
| `recognize` (`recognize.cpp`) | Names the enrolled people on the camera, live. |

`face_common.hpp` holds what the last two share: camera, models and gallery.

## How it works

1. **YuNet** finds each face: its box and 5 landmarks (eyes, nose tip, mouth corners).
2. **alignCrop** uses the 5 landmarks to rotate and crop the face to 112×112, always in the same position.
3. **SFace** turns the aligned face into a vector of 128 numbers. Faces of the same person
   give similar vectors.
4. The vector is compared with the gallery's by **cosine similarity**: from **0.363**
   (the threshold OpenCV recommends) on, it is the same person.

There is no training: both networks come trained. `enroll` only stores the vectors of the people you enrol.

## Usage

Needs `g++`, `pkg-config` and `libopencv-dev` (OpenCV 4.5.4 or newer).
Run everything from this folder: the model and gallery paths are relative.

```bash
./download_models.sh   # once: YuNet (~230 KB) and SFace (~37 MB) from opencv_zoo
make                   # builds the three programs
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

## Limitations

- A photo of you on a phone is also recognised as you (no anti-spoofing).
- Small faces (under ~60 px) and profiles are detected worse.
- `gallery.yml` holds biometric data: it is in `.gitignore` and must never be committed.
