"""
Path building for path_viz: no ROS here, so it runs in unit tests.

Every line is drawn in the truth's coordinates (Gazebo's world, where the drone
spawns). The truth goes in as it comes. The estimate (fc/odom) starts at (0, 0, 0)
where the estimator started, so it is shifted to start where the truth starts.
The shift is set once, from the first estimate after the first truth, like
checks.Drift (plus height). path_viz must therefore start with the sim, while the
drone is still on the ground: started later, the drift so far is hidden.

The plan is the mission's targets, in fc/odom's coordinates like the estimate, so
it gets the same shift: a straight line from the estimate at the first target,
then from each target to the next.
"""

from collections import deque
import math


class Trail:
    """The points of one line: a new point each time the drone has moved `step` metres."""

    def __init__(self, step=0.03, max_points=3000):
        self.step = step
        self.points = deque(maxlen=max_points)

    def add(self, p):
        """Add p = (x, y, z) unless it is closer than `step` to the last point; True if added."""
        if self.points and math.dist(p, self.points[-1]) < self.step:
            return False
        self.points.append(p)
        return True


class Paths:
    """The lines path_viz draws, by name, all in the truth's coordinates."""

    def __init__(self, step=0.03, max_points=3000):
        self.lines = {name: Trail(step, max_points)
                      for name in ('planned', 'estimated', 'true')}
        # added to every estimate: where fc/odom's (0, 0, 0) is in the truth's coordinates
        self.shift = None
        self.truth = None
        self.estimate = None   # the latest, in fc/odom's coordinates

    def add_truth(self, p):
        """Add a ground-truth position; True if the true line has a new point."""
        self.truth = p
        return self.lines['true'].add(p)

    def add_estimate(self, p):
        """Add an fc/odom position; True if the estimated line has a new point."""
        if self.shift is None:
            if self.truth is None:
                return False   # nothing to line up with yet
            self.shift = tuple(t - e for t, e in zip(self.truth, p))
        self.estimate = p
        return self.lines['estimated'].add(self.to_world(p))

    def add_target(self, p):
        """Add a mission target (fc/odom's coordinates); True if the planned line changed."""
        if self.shift is None:
            return False   # can't place it yet
        line = self.lines['planned']
        if not line.points:
            line.add(self.to_world(self.estimate))   # the plan starts where the drone is
        return line.add(self.to_world(p))

    def to_world(self, p):
        """Move a point from fc/odom's coordinates to the truth's."""
        return tuple(a + s for a, s in zip(p, self.shift))
