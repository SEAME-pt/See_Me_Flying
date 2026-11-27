"""
Fly forward until something gets in the way: the decision, without ROS (issue #228).

Fed with the distance ahead (obstacle/front_range: nan = unknown, inf = nothing
found) and how far the drone has flown. Says when to stop, and why:
  obstacle  nearer than stop_m, several results in a row (one can be a mistake)
  obstacle  remembered: flown up to stop_m before where the last results put it
  blind     unknown, or no results at all, for blind_s
Remembered, because the camera measures well until about 1 m and badly after: the
edges of the thing leave the picture. The memory is the median of the last results,
so a few wrong ones don't matter, and unknown does not erase it.
Not knowing stops the drone too. Only the first start_s are excused: the camera
needs movement before it can measure anything.
"""
from collections import deque
from dataclasses import dataclass
import math
import statistics
from typing import Deque, Optional

OBSTACLE, BLIND = 'obstacle', 'blind'


@dataclass
class Params:
    stop_m: float = 1.5     # m: stop for anything nearer
    confirm: int = 3        # results in a row
    memory: int = 15        # results the remembered place is made of
    blind_s: float = 1.0    # s without knowing what is ahead
    start_s: float = 3.0    # s after the start before blind counts


class Forward:
    def __init__(self, params: Optional[Params] = None):
        self.p = params or Params()
        self.places: Deque[float] = deque(maxlen=self.p.memory)
        self.start: Optional[float] = None     # None: not flying forward
        self._clear(0.0)

    def _clear(self, t: float) -> None:
        self.known = t                         # time of the last result that knew
        self.near = 0                          # results in a row nearer than stop_m
        self.distance = math.nan               # last result
        self.flown = 0.0                       # m
        self.places.clear()                    # where results put the thing, in m flown

    def begin(self, t: float) -> None:
        """Flying forward starts now."""
        self._clear(t)
        self.start = t

    def on_flown(self, metres: float) -> None:
        """Take how far the drone is from where it began."""
        self.flown = metres

    def on_distance(self, t: float, distance: float) -> None:
        self.distance = distance
        if math.isnan(distance):
            return                             # unknown: neither near nor clear
        self.known = t
        self.near = self.near + 1 if distance < self.p.stop_m else 0
        self.places.append(self.flown + distance)

    def left(self) -> float:
        """Return the distance to the remembered thing; inf when there is none."""
        if 2 * len(self.places) < self.p.memory:
            return math.inf
        return statistics.median(self.places) - self.flown

    def why_stop(self, t: float) -> Optional[str]:
        """Return OBSTACLE or BLIND when the drone must stop, else None."""
        if self.start is None:
            return None
        if self.near >= self.p.confirm or self.left() < self.p.stop_m:
            return OBSTACLE
        if t - self.start > self.p.start_s and t - self.known > self.p.blind_s:
            return BLIND
        return None
