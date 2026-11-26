"""
The room's floor surfaces, for the flow sensor's quality.

A floor map is a YAML file of named surfaces, each with a flow quality (0-255),
and rectangles saying where each surface lies. Later rectangles win where they
overlap; anywhere not covered is the default surface.
"""

import yaml  # type: ignore[import-untyped]


class FloorMap:
    """Look up the flow quality of the floor under a position."""

    def __init__(self, data):
        self.qualities = {name: s['quality'] for name, s in data['surfaces'].items()}
        self.default = self.qualities[data['default']]
        self.areas = []
        for area in data.get('areas', []):
            if area['surface'] not in self.qualities:
                raise ValueError(f"unknown surface '{area['surface']}' in an area")
            self.areas.append((area['surface'], area['x'], area['y']))

    @classmethod
    def load(cls, path):
        """Read a floor map file."""
        with open(path) as f:
            return cls(yaml.safe_load(f))

    def quality(self, x, y):
        """Return the flow quality of the surface under (x, y)."""
        for surface, (x0, x1), (y0, y1) in reversed(self.areas):
            if x0 <= x <= x1 and y0 <= y <= y1:
                return self.qualities[surface]
        return self.default
