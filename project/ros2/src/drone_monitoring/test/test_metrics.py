"""
DroneMetrics without ROS running: messages in, Prometheus samples out.

Catches: a metric renamed on one side only (exporter or dashboard), a stale
value still shown after its topic went quiet, a placeholder (-1, inf) shown
as a real reading, and the active source not switching.
"""
import json
import math
from pathlib import Path
import re

from drone_interfaces.msg import FcStatus
from drone_monitoring.metrics import DroneMetrics
from prometheus_client import CollectorRegistry, generate_latest
import pytest
from sensor_msgs.msg import BatteryState, Range

# project/ros2/src/drone_monitoring/test -> the repo root
REPO = Path(__file__).resolve().parents[5]
DASHBOARD = REPO / 'monitoring' / 'grafana' / 'dashboards' / 'drone.json'


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@pytest.fixture
def setup():
    clock = Clock()
    metrics = DroneMetrics(stale_after_s=3.0, clock=clock)
    registry = CollectorRegistry()
    registry.register(metrics)
    return metrics, registry, clock


def status(**fields):
    msg = FcStatus(backend='sim', armed=True, holding=False, link_ok=True,
                   state_age_s=0.02, setpoint_age_s=0.1)
    for name, value in fields.items():
        setattr(msg, name, value)
    return msg


def test_nothing_received_means_no_values(setup):
    _, registry, _ = setup
    for name in ('drone_armed', 'drone_link_ok', 'drone_range_meters', 'drone_battery_volts'):
        assert registry.get_sample_value(name) is None, name


def test_status_values(setup):
    metrics, registry, _ = setup
    metrics.on_message('fc/status', status(holding=True))
    assert registry.get_sample_value('drone_info', {'backend': 'sim'}) == 1.0
    assert registry.get_sample_value('drone_armed') == 1.0
    assert registry.get_sample_value('drone_holding') == 1.0
    assert registry.get_sample_value('drone_link_ok') == 1.0
    assert registry.get_sample_value('drone_state_age_seconds') == pytest.approx(0.02)
    assert registry.get_sample_value('drone_setpoint_age_seconds') == pytest.approx(0.1)


def test_no_age_yet_is_no_sample(setup):
    # FcStatus sends -1 before the first setpoint or FC state: not an age.
    metrics, registry, _ = setup
    metrics.on_message('fc/status', status(state_age_s=-1.0, setpoint_age_s=-1.0,
                                           link_ok=False))
    assert registry.get_sample_value('drone_state_age_seconds') is None
    assert registry.get_sample_value('drone_setpoint_age_seconds') is None
    assert registry.get_sample_value('drone_link_ok') == 0.0


def test_quiet_topic_drops_its_values_but_keeps_its_counter(setup):
    metrics, registry, clock = setup
    metrics.on_message('fc/status', status())
    clock.t += 2.9
    assert registry.get_sample_value('drone_armed') == 1.0
    clock.t += 0.2   # 3.1 s since the last fc/status
    assert registry.get_sample_value('drone_armed') is None
    assert registry.get_sample_value('drone_topic_messages_total', {'topic': 'fc/status'}) == 1
    assert registry.get_sample_value('drone_topic_last_seen_timestamp',
                                     {'topic': 'fc/status'}) == 1000.0


def test_range_out_of_limits_is_no_sample(setup):
    metrics, registry, _ = setup
    metrics.on_message('fc/range', Range(range=1.25))
    assert registry.get_sample_value('drone_range_meters') == pytest.approx(1.25)
    for out in (math.inf, -math.inf):   # REP 117: too far, too close
        metrics.on_message('fc/range', Range(range=out))
        assert registry.get_sample_value('drone_range_meters') is None


def test_battery(setup):
    metrics, registry, _ = setup
    metrics.on_message('fc/battery', BatteryState(voltage=15.2))
    assert registry.get_sample_value('drone_battery_volts') == pytest.approx(15.2)
    metrics.on_message('fc/battery', BatteryState(voltage=math.nan))
    assert registry.get_sample_value('drone_battery_volts') is None


def test_active_source_switches(setup):
    metrics, registry, clock = setup
    metrics.on_active_source('mission')
    metrics.on_active_source('radio')
    clock.t += 60.0   # latched, sent on change only: never stale
    assert registry.get_sample_value('drone_active_source', {'source': 'radio'}) == 1.0
    assert registry.get_sample_value('drone_active_source', {'source': 'mission'}) == 0.0


def test_counts_messages_per_topic(setup):
    metrics, registry, clock = setup
    for _ in range(5):
        clock.t += 0.1
        metrics.on_message('fc/range', Range(range=1.0))
    assert registry.get_sample_value('drone_topic_messages_total', {'topic': 'fc/range'}) == 5
    assert registry.get_sample_value('drone_topic_last_seen_timestamp',
                                     {'topic': 'fc/range'}) == pytest.approx(1000.5)


def test_every_metric_the_dashboard_queries_exists(setup):
    if not DASHBOARD.is_file():
        pytest.skip(f'{DASHBOARD} not here (the dev container mounts only project/)')
    metrics, registry, _ = setup
    metrics.on_message('fc/status', status())
    metrics.on_message('fc/range', Range(range=1.0))
    metrics.on_message('fc/battery', BatteryState(voltage=15.0))
    metrics.on_active_source('mission')
    exported = set(re.findall(r'^(drone_\w+)', generate_latest(registry).decode(), re.M))

    panels = json.loads(DASHBOARD.read_text())['panels']
    queried = {name for panel in panels for target in panel.get('targets', [])
               for name in re.findall(r'\bdrone_\w+', target['expr'])}
    assert queried, 'no drone_ metric found in the dashboard'
    missing = sorted(queried - exported)
    assert not missing, f'the dashboard queries metrics nobody exports: {missing}'
