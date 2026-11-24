"""
Distance ahead from one moving camera, with math only (issues #226, #227).

Near things shift more between two images than far ones. The odometry tells how
the drone moved and turned between them, so for a guessed distance we know where
each pixel must have been. Plane sweep tries a list of distances and keeps, for
each pixel, the one where the images match best:

  1. take the image now, and one or two from before the drone moved 15-35 cm.
  2. for each distance: warp the older image as if everything were there, compare.
  3. keep pixels with one clear best match that also beats "very far".
  4. keep the points inside the corridor the drone flies through.
  5. the nearest of them (10th percentile) is the distance ahead.

A plain wall has no detail to match, only an outline. So a blank area whose outline
lies on one flat surface is taken to be that surface (blank_surfaces). Sky is not:
part of its outline is far away.

It needs movement and visible detail (edges are enough). Without them the answer
is UNKNOWN, never CLEAR: not seeing an obstacle is not the same as seeing that
there is none.

Plain Python, NumPy and OpenCV, no ROS, so it can be tested on its own.
"""
from collections import deque
from dataclasses import dataclass, field
import math
from typing import Any, Deque, List, Optional, Tuple

import cv2
import numpy as np

CLEAR, OBSTACLE, UNKNOWN = 'clear', 'obstacle', 'unknown'
WIDTH, HEIGHT = 320, 240     # working size: smaller is faster
FAR = 60.0                   # m: "very far", no visible shift
MAX_COST = 40.0              # grey levels: caps the difference of one pixel


@dataclass
class Camera:
    """Where the camera is and how wide it sees (fpv_camera in the worlds)."""

    hfov: float = 2.09          # rad, horizontal field of view
    pitch_up: float = 0.35      # rad, tilted up from the body
    forward: float = 0.24       # m, ahead of the body centre
    up: float = 0.03            # m, above the body centre


@dataclass
class Config:
    """Settings of the sweep; lengths in m, times in s."""

    warn_m: float = 1.5         # OBSTACLE below this
    half_width: float = 0.5     # corridor the drone flies through
    half_height: float = 0.4
    nearest: float = 0.35       # distances to try
    farthest: float = 8.0
    steps: int = 40
    baselines: Tuple[float, ...] = (0.15, 0.35)   # how far the drone must have moved
    max_age: float = 1.2        # older images are dropped
    min_points: int = 40        # pixels needed to call something a thing
    min_seen: float = 0.2       # share of the corridor view that must be checked for CLEAR
    min_height: float = 0.6     # lower than this the floor is inside the corridor
    max_speed: float = 5.0      # faster than this is an odometry jump
    blank: float = 6.0          # brightness change per pixel below this is blank
    blank_area: int = 400       # pixels: smaller blank areas are ignored
    blank_agree: float = 0.6    # share of the outline that must be on one surface


@dataclass
class Pose:
    """Body pose: rot turns body directions into odom directions."""

    pos: np.ndarray
    rot: np.ndarray


@dataclass
class Result:
    """What is ahead: distance is nan when unknown, inf when nothing was found."""

    state: str = UNKNOWN
    distance: float = math.nan
    reason: str = ''
    seen: float = 0.0                                   # share of the corridor view checked
    pixels: Any = field(default=None, repr=False)       # (n, 2) pixels of the points found


def rotation(q: Tuple[float, float, float, float]) -> np.ndarray:
    """Return the rotation matrix of a quaternion (x, y, z, w)."""
    x, y, z, w = np.array(q, float) / np.linalg.norm(q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


class OdomBuffer:
    """
    Recent odometry, to get the pose at the exact time of an image.

    The height is the rangefinder's, and its noise (cm) is large next to the 15 cm the
    drone moves between images, so it is a line through the last `smooth` s of it.
    """

    def __init__(self, keep: float = 2.0, max_gap: float = 0.2, smooth: float = 0.4):
        self.keep, self.max_gap, self.smooth = keep, max_gap, smooth
        self.rows: Deque[Tuple[float, np.ndarray, np.ndarray]] = deque()

    def newest(self) -> float:
        return self.rows[-1][0] if self.rows else -math.inf

    def add(self, t: float, pos: Tuple[float, float, float],
            quat: Tuple[float, float, float, float]) -> None:
        if t < self.newest():
            self.rows.clear()           # time went back: the sim was restarted
        if t == self.newest() or np.linalg.norm(quat) < 0.5:
            return
        q = np.array(quat, float)
        if self.rows and float(q @ self.rows[-1][2]) < 0:
            q = -q                      # the same attitude, so that averaging works
        self.rows.append((t, np.array(pos, float), q))
        while t - self.rows[0][0] > self.keep:
            self.rows.popleft()

    def at(self, t: float) -> Optional[Pose]:
        """Return the pose at time t, or None if the odometry around it is missing."""
        rows = list(self.rows)
        for (t0, p0, q0), (t1, p1, q1) in zip(rows, rows[1:]):
            if t0 <= t <= t1:
                if t1 - t0 > self.max_gap:
                    return None
                k = (t - t0) / (t1 - t0)
                q = q0 + k * (q1 - q0)
                pos = p0 + k * (p1 - p0)
                pos[2] = self._height(t)
                return Pose(pos, rotation((q[0], q[1], q[2], q[3])))
        return None

    def _height(self, t: float) -> float:
        rows = [(r[0] - t, r[1][2]) for r in self.rows if -self.smooth <= r[0] - t <= 0.05]
        x, z = np.array(rows).T
        if len(rows) < 4:
            return float(z[np.abs(x).argmin()])
        return float(np.polyfit(x, z, 1)[1])


def heading_axes(rot: np.ndarray) -> np.ndarray:
    """Return forward, left, up as rows: level, whatever the drone's tilt."""
    f = np.array([rot[0, 0], rot[1, 0], 0.0])
    f /= max(float(np.linalg.norm(f)), 1e-9)
    return np.array([f, [-f[1], f[0], 0.0], [0.0, 0.0, 1.0]])


class PlaneSweep:
    """Feed it images with their time and pose; it returns what is ahead."""

    def __init__(self, cam: Optional[Camera] = None, cfg: Optional[Config] = None):
        self.cam, self.cfg = cam or Camera(), cfg or Config()
        c, s = math.cos(self.cam.pitch_up), math.sin(self.cam.pitch_up)
        # Columns: the camera's right, down and forward, in body directions.
        self.mount = np.array([[0.0, s, c], [-1.0, 0.0, 0.0], [0.0, -c, s]])
        self.offset = np.array([self.cam.forward, 0.0, self.cam.up])
        f = (WIDTH / 2) / math.tan(self.cam.hfov / 2)
        cx, cy = (WIDTH - 1) / 2, (HEIGHT - 1) / 2        # middle, between two pixels
        self.k = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1.0]])
        self.k_inv = np.linalg.inv(self.k)
        v, u = np.mgrid[0:HEIGHT, 0:WIDTH]
        self.rays = np.stack([(u - cx) / f, (v - cy) / f, np.ones(u.shape)], -1)
        # Even steps in 1 / distance: the shift between images is even in that.
        self.depths = 1 / np.linspace(1 / self.cfg.nearest, 1 / self.cfg.farthest,
                                      self.cfg.steps)
        self.history: Deque[Tuple[float, np.ndarray, np.ndarray, np.ndarray]] = deque()

    def reset(self) -> None:
        self.history.clear()

    def update(self, gray: np.ndarray, t: float, pose: Pose) -> Result:
        """Add a grey image taken at time t (s) from pose; return what is ahead."""
        img = cv2.resize(gray, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
        img = cv2.GaussianBlur(img, (0, 0), 1.0).astype(np.float32)
        rot = pose.rot @ self.mount                       # camera -> odom
        pos = pose.pos + pose.rot @ self.offset
        if self.history and self._jumped(t, pos):
            self.reset()
            self.history.append((t, img, rot, pos))
            return Result(reason='odometry or time jumped')
        sources = self._sources(t, pos)
        self.history.append((t, img, rot, pos))
        while t - self.history[0][0] > self.cfg.max_age:
            self.history.popleft()
        if pose.pos[2] < self.cfg.min_height:
            return Result(reason='too low')
        if not sources:
            return Result(reason='not moving')
        axes = heading_axes(pose.rot) @ rot               # camera -> forward, left, up
        return self._decide(img, self._costs(img, rot, pos, sources), axes)

    def corridor_box(self, pose: Pose) -> Optional[Tuple[Tuple[float, float],
                                                         Tuple[float, float]]]:
        """Return the corridor at warn_m as a box of pixels, for drawing."""
        axes = heading_axes(pose.rot) @ pose.rot @ self.mount
        c = self.cfg
        corners = np.array([[c.warn_m, y, z] for y in (-c.half_width, c.half_width)
                            for z in (-c.half_height, c.half_height)]) @ axes
        if (corners[:, 2] <= 0.1).any():
            return None
        p = corners / corners[:, 2:3] @ self.k.T
        return ((float(p[:, 0].min()), float(p[:, 1].min())),
                (float(p[:, 0].max()), float(p[:, 1].max())))

    def _jumped(self, t: float, pos: np.ndarray) -> bool:
        dt = t - self.history[-1][0]
        moved = float(np.linalg.norm(pos - self.history[-1][3]))
        return dt <= 0 or dt > self.cfg.max_age or moved > self.cfg.max_speed * dt + 0.05

    def _sources(self, t: float, pos: np.ndarray) -> List[Tuple[np.ndarray, np.ndarray,
                                                                np.ndarray]]:
        """Return, for each baseline, the newest image from at least that far away."""
        out = []
        for need in self.cfg.baselines:
            for t0, img, rot, p in reversed(self.history):
                if t - t0 > self.cfg.max_age:
                    break
                if np.linalg.norm((pos - p)[:2]) >= need:     # level: height is noisy
                    out.append((img, rot, p))
                    break
        return out

    def _costs(self, img: np.ndarray, rot: np.ndarray, pos: np.ndarray,
               sources: List[Tuple[np.ndarray, np.ndarray, np.ndarray]]) -> np.ndarray:
        """Return how badly the images match, per distance (the last is FAR) and pixel."""
        depths = list(self.depths) + [FAR]
        costs = np.zeros((len(depths), HEIGHT, WIDTH), np.float32)
        normal = np.array([0.0, 0.0, 1.0])
        for old, rot0, pos0 in sources:
            turn, move = rot0.T @ rot, rot0.T @ (pos - pos0)
            for i, d in enumerate(depths):
                h = self.k @ (turn + np.outer(move, normal) / d) @ self.k_inv
                warped = cv2.warpPerspective(
                    old, h, (WIDTH, HEIGHT), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=-999)
                diff = np.minimum(np.abs(img - warped), MAX_COST)
                diff[warped < -1] = MAX_COST              # was outside the older image
                costs[i] += cv2.boxFilter(diff, -1, (9, 9))
        return costs / len(sources)

    def _decide(self, img: np.ndarray, costs: np.ndarray, axes: np.ndarray) -> Result:
        cfg, near, far = self.cfg, costs[:-1], costs[-1]
        best = near.argmin(0)
        cost = np.take_along_axis(near, best[None], 0)[0]
        others = np.abs(np.arange(cfg.steps)[:, None, None] - best[None]) > 5
        second = np.where(others, near, np.inf).min(0)
        # A thing: one clear best distance, better than "far", not at the list's ends.
        found = ((cost < 0.6 * far) & (cost < 0.8 * second) & (far > 2.0) & (cost < 10)
                 & (best > 0) & (best < cfg.steps - 1))
        inv = np.where(found, 1 / self.depths[best], 0.0)
        view = self._inside(self.rays * cfg.warn_m @ axes.T)
        surface = self.blank_surfaces(img, found, inv, near, far, view)
        known = found | (surface > 0)
        inv = np.where(found, inv, surface)
        points = (self.rays[known] / inv[known][:, None]) @ axes.T
        inside = self._inside(points)
        pixels = np.argwhere(known)[inside][:, ::-1]
        ahead = np.sort(points[inside][:, 0])
        # Checked: pixels of the corridor's view where being near clearly does not fit.
        close = self.depths < cfg.warn_m
        near_cost = near[close].min(0)
        rest = np.minimum(near[~close].min(0), far)
        checked = (rest < 0.8 * near_cost) & (rest < 10) & (near_cost > 2.0)
        checked |= surface > 0
        seen = float(checked[view].mean()) if view.any() else 0.0

        if len(ahead) >= cfg.min_points:
            distance = float(ahead[int(0.1 * len(ahead))])
            if distance < cfg.warn_m:
                return Result(OBSTACLE, distance, 'close', seen, pixels)
        else:
            distance = math.inf
        if seen < cfg.min_seen:
            return Result(UNKNOWN, math.nan, 'not enough detail', seen, pixels)
        return Result(CLEAR, distance, 'checked', seen, pixels)

    def blank_surfaces(self, img: np.ndarray, found: np.ndarray, inv: np.ndarray,
                       near: np.ndarray, far: np.ndarray, view: np.ndarray) -> np.ndarray:
        """
        Return 1 / distance for blank pixels that belong to a flat surface, else 0.

        On a flat surface 1 / distance is a straight-line function of the pixel:
        a * u + b * v + c. It is fitted to the outline of each blank area.
        """
        cfg = self.cfg
        change = (np.abs(cv2.Sobel(img, cv2.CV_32F, 1, 0))
                  + np.abs(cv2.Sobel(img, cv2.CV_32F, 0, 1)))
        blank = (cv2.boxFilter(change, -1, (9, 9)) < cfg.blank).astype(np.uint8)
        # Outline pixels that are clearly far count as votes for "not a near surface".
        nearer = near[:30].min(0)
        distant = (far < 0.8 * nearer) & (far < 10) & (nearer > 2.0) & ~found
        out = np.zeros(img.shape)
        count, labels, stats, middle = cv2.connectedComponentsWithStats(blank)
        for i in range(1, count):
            area = labels == i
            if stats[i, cv2.CC_STAT_AREA] < cfg.blank_area or not (area & view).any():
                continue
            grown = cv2.dilate(area.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
            ring = np.argwhere(grown & ~area & (found | distant))
            if len(ring) < cfg.min_points:
                continue
            plane = self._fit(ring, inv[ring[:, 0], ring[:, 1]], middle[i])
            if plane is not None:
                v, u = np.nonzero(area)
                value = plane[0] * u + plane[1] * v + plane[2]
                out[v, u] = np.where(value > 1 / cfg.farthest, value, 0.0)
        return out

    def _fit(self, ring: np.ndarray, inv: np.ndarray, middle: np.ndarray
             ) -> Optional[np.ndarray]:
        """Fit the surface most outline pixels agree on, or None if they don't agree."""
        a = np.c_[ring[:, 1], ring[:, 0], np.ones(len(ring))].astype(float)
        rng = np.random.default_rng(0)
        best = np.zeros(len(ring), bool)
        for _ in range(60):
            pick = rng.choice(len(ring), 3, replace=False)
            if abs(np.linalg.det(a[pick])) < 50:          # three points in a line
                continue
            fits = np.abs(a @ np.linalg.solve(a[pick], inv[pick]) - inv) < 0.02 + 0.1 * inv
            if fits.sum() > best.sum():
                best = fits
        # Agreement all around the area, not only on one side of it.
        angle = np.arctan2(ring[best, 0] - middle[1], ring[best, 1] - middle[0])
        sides = len(np.unique(((angle + math.pi) / (2 * math.pi) * 12).astype(int) % 12))
        if best.mean() < self.cfg.blank_agree or sides < 4:
            return None
        plane: np.ndarray = np.linalg.lstsq(a[best], inv[best], rcond=None)[0]
        return plane

    def _inside(self, p: np.ndarray) -> np.ndarray:
        """Return which points (forward, left, up) are in the corridor."""
        return ((p[..., 0] > 0.05) & (np.abs(p[..., 1]) < self.cfg.half_width)
                & (np.abs(p[..., 2]) < self.cfg.half_height))
