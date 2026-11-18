"""
The drone's state as Prometheus metrics, apart from ROS so it can be tested alone.

metrics_exporter hands it every message it gets; Prometheus reads it over
HTTP, and the metrics are made from the latest messages at that moment. The
names are the ones monitoring/grafana/dashboards/drone.json queries.

A topic quiet for longer than stale_after_s leaves its values out, so a dead
fc_bridge shows as NO DATA on the dashboard instead of its last state. The
per-topic counters and last-seen times always stay: they show it went quiet.

Times are wall clock (time.time), not the node clock: Prometheus and Grafana
compare them with their own clock, and in the sim the node clock is Gazebo's.
"""
import math
import threading
import time
from typing import Any, Callable, Dict, Iterator, Optional, Set

from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, Metric
from prometheus_client.registry import Collector


def gauge(name: str, doc: str, value: float, **labels: str) -> GaugeMetricFamily:
    family = GaugeMetricFamily(name, doc, labels=list(labels))
    family.add_metric(list(labels.values()), value)
    return family


class DroneMetrics(Collector):
    """Latest message per topic in, Prometheus metrics out (one collect() per scrape)."""

    def __init__(self, stale_after_s: float = 3.0, clock: Callable[[], float] = time.time):
        self.stale_after_s = stale_after_s
        self.clock = clock
        self.lock = threading.Lock()   # ROS callbacks write, the HTTP thread reads
        self.latest: Dict[str, Any] = {}
        self.counts: Dict[str, int] = {}
        self.last_seen: Dict[str, float] = {}
        self.active_source: Optional[str] = None
        self.sources: Set[str] = set()

    def on_message(self, topic: str, msg: Any) -> None:
        with self.lock:
            self.latest[topic] = msg
            self.counts[topic] = self.counts.get(topic, 0) + 1
            self.last_seen[topic] = self.clock()

    def on_active_source(self, source: str) -> None:
        # safety/active_source is latched and only sent on change, so it never
        # goes stale and is not counted as a topic.
        with self.lock:
            self.active_source = source
            self.sources.add(source)

    def collect(self) -> Iterator[Metric]:
        with self.lock:
            now = self.clock()
            fresh = {topic: msg for topic, msg in self.latest.items()
                     if now - self.last_seen[topic] <= self.stale_after_s}
            counts = dict(self.counts)
            last_seen = dict(self.last_seen)
            active, sources = self.active_source, sorted(self.sources)

        status = fresh.get('fc/status')
        if status is not None:
            yield gauge('drone_info', 'fc_bridge backend (sim or inav); always 1', 1.0,
                        backend=status.backend)
            yield gauge('drone_armed', '1 if armed', float(status.armed))
            yield gauge('drone_holding', '1 while fc/hold is on (fc_bridge sends zero)',
                        float(status.holding))
            yield gauge('drone_link_ok', '1 while fc_bridge gets state from the FC',
                        float(status.link_ok))
            # -1 means none yet: no sample, so a gap on the graph, not a value.
            if status.state_age_s >= 0.0:
                yield gauge('drone_state_age_seconds', 'Since the last FC state',
                            status.state_age_s)
            if status.setpoint_age_s >= 0.0:
                yield gauge('drone_setpoint_age_seconds', 'Since the last accepted setpoint',
                            status.setpoint_age_s)

        rng = fresh.get('fc/range')
        if rng is not None and math.isfinite(rng.range):   # +-inf: out of range (REP 117)
            yield gauge('drone_range_meters', 'Rangefinder distance (fc/range)', rng.range)

        battery = fresh.get('fc/battery')
        if battery is not None and math.isfinite(battery.voltage):   # NaN: unknown
            yield gauge('drone_battery_volts', 'Battery voltage (fc/battery)', battery.voltage)

        if active is not None:
            family = GaugeMetricFamily(
                'drone_active_source',
                '1 for the source safety_manager forwards to fc_bridge, 0 for the others',
                labels=['source'])
            for source in sources:
                family.add_metric([source], 1.0 if source == active else 0.0)
            yield family

        messages = CounterMetricFamily('drone_topic_messages', 'Messages received per topic',
                                       labels=['topic'])
        seen = GaugeMetricFamily('drone_topic_last_seen_timestamp',
                                 'Wall-clock time of the last message per topic (Unix s)',
                                 labels=['topic'])
        for topic in sorted(counts):
            messages.add_metric([topic], counts[topic])
            seen.add_metric([topic], last_seen[topic])
        yield messages
        yield seen
