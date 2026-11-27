r"""
Distance ahead from a single camera with an AI depth model (issue #226).

The model (Depth Anything V2 Small, Apache-2.0) looks at one image and gives a
*relative* inverse depth per pixel: bigger = closer, but with an unknown scale
and offset, so not metres. To get metres we need a reference whose distance is
known, and the drone has one: the floor. From the height (downward
rangefinder) and the camera tilt, the distance to the floor in the bottom
corners of the image follows from geometry alone. Fitting the model's output
to it there,  model = s / depth + t,  scales the whole image to metres.

The model file is not in git (99 MB). Get it once, from the repo root:
  curl -L -o project/models/depth_anything_v2_small.onnx \\
    https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx

Known weak spots (measured in the sim, see the PR): plain grey background can
look like a close wall; the floor scale is wrong when the bottom corners are not
floor; small thin things far away are missed.

Plain Python, NumPy and OpenCV (ONNX Runtime only in DepthModel), no ROS.
"""
from dataclasses import dataclass
import math
from typing import Optional, Tuple

import cv2
import numpy as np

MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)
FAR = 50.0       # m: "nothing there", also the camera's far clip


@dataclass
class Camera:
    """Where the camera is and how wide it sees (fpv_camera in the worlds)."""

    hfov: float = 2.09            # rad, horizontal field of view
    pitch_up: float = 0.35        # rad, tilted up from the body
    above_body: float = 0.03      # m, camera height above the rangefinder


class DepthModel:
    """The AI model: an image in, relative inverse depth out (bigger = closer)."""

    def __init__(self, path: str, width: int = 392, height: int = 294):
        import onnxruntime as ort     # only here: the rest works without it
        # The NVIDIA GPU when ONNX Runtime can use it, otherwise the CPU.
        providers = [p for p in ('CUDAExecutionProvider', 'CPUExecutionProvider')
                     if p in ort.get_available_providers()]
        self.session = ort.InferenceSession(path, providers=providers)
        self.input = self.session.get_inputs()[0].name
        self.size = (width - width % 14, height - height % 14)   # model needs x14

    def relative(self, bgr: np.ndarray) -> np.ndarray:
        """Return relative inverse depth, same size as the image."""
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        x = cv2.resize(rgb, self.size, interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        x = ((x - MEAN) / STD).transpose(2, 0, 1)[None]
        out = self.session.run(None, {self.input: x})[0][0]
        return cv2.resize(out, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_LINEAR)


def floor_depth(shape: Tuple[int, int], height: float, cam: Camera) -> np.ndarray:
    """
    Return, for each pixel, the depth of a flat floor 'height' m below; nan above the horizon.

    A pixel row v looks (v - cy) / f below the camera axis, and the axis looks
    pitch_up above level, so the ray drops k = (v - cy) / f * cos - sin per metre
    of depth. It hits the floor at depth = camera height / k.
    """
    h, w = shape
    f = (w / 2) / math.tan(cam.hfov / 2)
    v = np.arange(h, dtype=np.float32)
    k = (v - h / 2) / f * math.cos(cam.pitch_up) - math.sin(cam.pitch_up)
    z = np.where(k > 0.05, (height + cam.above_body) / np.maximum(k, 1e-6), np.nan)
    return np.repeat(z[:, None], w, 1).astype(np.float32)


def floor_mask(shape: Tuple[int, int]) -> np.ndarray:
    """Bottom corners: the part of the image that should be floor, left and right."""
    h, w = shape
    m = np.zeros((h, w), bool)
    m[int(h * 0.88):, :int(w * 0.2)] = True
    m[int(h * 0.88):, int(w * 0.8):] = True
    return m


def fit_scale(rel: np.ndarray, depth: np.ndarray, mask: np.ndarray
              ) -> Optional[Tuple[float, float]]:
    """Fit rel = s / depth + t on the masked pixels; None if it makes no sense."""
    use = mask & np.isfinite(depth) & (depth > 0)
    if use.sum() < 50:
        return None
    a = np.stack([1 / depth[use], np.ones(use.sum(), np.float32)], 1)
    (s, t), *_ = np.linalg.lstsq(a, rel[use], rcond=None)
    return (float(s), float(t)) if s > 0 else None


def to_metres(rel: np.ndarray, s: float, t: float) -> np.ndarray:
    """Turn relative inverse depth into metres with a fitted scale."""
    inv = (rel - t) / s
    return np.where(inv > 1 / FAR, 1 / np.maximum(inv, 1 / FAR), FAR).astype(np.float32)


def centre(img: np.ndarray, fraction: float) -> np.ndarray:
    """Return the middle part of img: fraction of its width and height."""
    h, w = img.shape[:2]
    dh, dw = int(h * (1 - fraction) / 2), int(w * (1 - fraction) / 2)
    return img[dh:h - dh, dw:w - dw]


def ahead(depth: np.ndarray, roi: float = 0.4, percentile: float = 10) -> float:
    """
    Return the distance to the closest thing straight ahead, in m.

    The 10th percentile of the centre box, not the minimum: one wrong pixel
    should not raise an alarm, but an obstacle covering a tenth of it should.
    """
    return float(np.percentile(centre(depth, roi), percentile))


class DistanceAhead:
    """Feed it frames and the height; it returns a depth map in metres and the distance ahead."""

    def __init__(self, model: DepthModel, cam: Camera = Camera(), roi: float = 0.4,
                 min_height: float = 0.3):
        self.model, self.cam, self.roi, self.min_height = model, cam, roi, min_height
        self.scale: Optional[Tuple[float, float]] = None   # last good (s, t)

    def update(self, bgr: np.ndarray, height: float
               ) -> Tuple[Optional[np.ndarray], Optional[float]]:
        """Return (depth in m, distance ahead in m), or (None, None) before the first scale."""
        rel = self.model.relative(bgr)
        if math.isfinite(height) and height >= self.min_height:
            shape = (rel.shape[0], rel.shape[1])
            fitted = fit_scale(rel, floor_depth(shape, height, self.cam), floor_mask(shape))
            if fitted is not None:
                self.scale = fitted
        if self.scale is None:        # on the ground: the floor fills the view, no scale
            return None, None
        depth = to_metres(rel, *self.scale)
        return depth, ahead(depth, self.roi)
