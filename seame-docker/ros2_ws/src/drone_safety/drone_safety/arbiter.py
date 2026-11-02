"""
Command arbitration, without ROS: which source may command the drone right now.

Each source publishes velocity commands on its own topic. The highest-priority
source that has published within `timeout_s` is active, and only its commands
are forwarded to fc_bridge. With none active nothing is forwarded, so
fc_bridge's own timeout sends zero.
"""
from typing import Dict, List, Optional

NONE = 'none'


class Arbiter:
    def __init__(self, priority: List[str], timeout_s: float):
        self.priority = list(priority)        # highest first
        self.timeout_s = timeout_s
        self.last: Dict[str, float] = {}      # source -> time of its last command
        self.current = NONE                   # active source at the last update()

    def fresh(self, t: float, source: str) -> bool:
        seen = self.last.get(source)
        return seen is not None and 0.0 <= t - seen <= self.timeout_s

    def active(self, t: float) -> str:
        for source in self.priority:
            if self.fresh(t, source):
                return source
        return NONE

    def on_command(self, t: float, source: str) -> bool:
        """Record a command; True if it should be forwarded."""
        if source not in self.priority:
            return False
        self.last[source] = t
        return self.active(t) == source

    def update(self, t: float) -> Optional[str]:
        """Return the newly active source if it changed since the last call, else None."""
        now = self.active(t)
        if now == self.current:
            return None
        self.current = now
        return now
