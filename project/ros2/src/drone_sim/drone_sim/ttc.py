"""
Time to contact from a single camera, with optical flow (issue #226).

The idea: flying straight at a surface, the image of that surface grows.
Every point moves away from the centre of the image, and the closer the
surface, the faster it grows. If a point at distance x from the centre moves
outwards by u pixels per frame, then u = x / tau, where tau is the number of
frames until contact. So we never need to know the distance in metres: how
fast the image grows already tells us how soon we would hit it.

Steps, every frame:
  1. optical flow: how far each pixel moved since the last frame (OpenCV).
  2. growth: in the centre of the image (what is straight ahead), fit
     u = a * x + c and v = b * y + d. a and b are how fast the image grows
     sideways and up/down; c and d soak up any sideways drift or tilt.
  3. time to contact: growth a + b equals 2 / tau, so tau = 2 / (a + b)
     frames, times the time between frames for seconds.
  4. smooth over a few frames, because flow is noisy.

Plain Python and OpenCV, no ROS, so it can be tested on its own.
"""
import math
from typing import Optional

import cv2
import numpy as np

# Below this growth rate (1/s) the image is not growing: nothing ahead, or
# moving away. 0.05 /s means a time to contact of 40 s, effectively "never".
MIN_RATE = 0.05


def centre(img: np.ndarray, fraction: float) -> np.ndarray:
    """Return the middle part of img: fraction of its width and height."""
    h, w = img.shape[:2]
    dh, dw = int(h * (1 - fraction) / 2), int(w * (1 - fraction) / 2)
    return img[dh:h - dh, dw:w - dw]


def texture(gray: np.ndarray) -> float:
    """
    Return how much detail a grey image has: mean brightness change per pixel.

    Optical flow can only follow detail. A plain white wall scores near 0 and
    then the flow, and so the time to contact, cannot be trusted.
    """
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
    return float(np.mean(np.abs(gx) + np.abs(gy)))


def optical_flow(prev: np.ndarray, gray: np.ndarray) -> np.ndarray:
    """Return the flow between two grey frames: array (h, w, 2) of (u, v) in pixels."""
    return cv2.calcOpticalFlowFarneback(
        prev, gray, None, pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0)


def growth(flow: np.ndarray) -> float:
    """
    Return how fast the flow field spreads out, per frame (a + b, see top).

    a is the slope of u against x, found with least squares: cov(u, x) / var(x).
    Same for b with v and y. Positive = growing (getting closer).
    """
    h, w = flow.shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = flow[..., 0], flow[..., 1]
    x -= x.mean()
    y -= y.mean()
    a = float(np.sum(u * x) / np.sum(x * x))
    b = float(np.sum(v * y) / np.sum(y * y))
    return a + b


class TimeToContact:
    """Feed it frames with their times; it returns the time to contact in seconds."""

    def __init__(self, width: int = 320, roi: float = 0.4, smoothing: float = 0.3,
                 min_texture: float = 8.0):
        self.width = width              # frames are shrunk to this width: faster
        self.roi = roi                  # part of the image that counts as "ahead"
        self.smoothing = smoothing      # 0..1, weight of the newest frame
        self.min_texture = min_texture  # below this the centre is too plain
        self.prev: Optional[np.ndarray] = None
        self.prev_t = 0.0
        self.rate = 0.0                 # smoothed growth per second (= 2 / ttc)
        self.flow: Optional[np.ndarray] = None   # last flow, for drawing
        self.textured = False

    def prepare(self, frame: np.ndarray) -> np.ndarray:
        """Return frame as a small grey image."""
        gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        return cv2.resize(gray, (self.width, int(h * self.width / w)))

    def update(self, frame: np.ndarray, t: float) -> Optional[float]:
        """
        Add a frame taken at time t (s). Return time to contact in seconds.

        Returns math.inf when the centre is not getting closer, and None when
        there is no answer yet (first frame, bad timing, or too little texture).
        """
        gray = self.prepare(frame)
        prev, prev_t = self.prev, self.prev_t
        self.prev, self.prev_t = gray, t
        dt = t - prev_t
        if prev is None or dt <= 0.0:
            return None
        self.textured = texture(centre(gray, self.roi)) >= self.min_texture
        if not self.textured:
            return None
        self.flow = optical_flow(prev, gray)
        rate = growth(centre(self.flow, self.roi)) / dt
        self.rate += self.smoothing * (rate - self.rate)
        return 2.0 / self.rate if self.rate > MIN_RATE else math.inf
