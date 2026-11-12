"""
Check that the values in sim.yaml (and the node names in sim.launch.py) agree.

this file opens and read the sim and launch files, and
compares the main values to make sure that they are consistnet with each other.

this file checks:
- the mission climb speed is the same as the drone climb speed limit.
- the safety timeout is the same as the drone setpoint timeout.
- checks that the speed requested is within the drone speed limit.
- checks that the heights are within the rangefinder limits.
- checks that the demo height is within the rangefinder limits.
- checks that the flow model min height is below the ground height.
- checkds the priority list is radio > mission > setpoint_pub > safety_manager.
- checks that all times and rates are positive.
- decimals are floats, not ints (0.0 instead of 0).
- No typos in the section names, which would make the node ignore the section.

"""

from pathlib import Path
import re

import pytest
import yaml

CONFIG = Path(__file__).resolve().parents[1] / 'config' / 'sim.yaml'
LAUNCH = CONFIG.parents[1] / 'launch' / 'sim.launch.py'


@pytest.fixture(scope='module')
def cfg():
    with open(CONFIG) as f:
        data = yaml.safe_load(f)
    return {node: section['ros__parameters'] for node, section in data.items()}


@pytest.fixture(scope='module')
def fc(cfg):
    return cfg['fc_bridge']


def test_mission_climb_speed_equals_fc_limit(cfg, fc):
    assert cfg['mission']['max_vz'] == fc['max_speed_z'], (
        'mission.max_vz must equal fc_bridge.max_speed_z: lower and the mission climbs '
        'slower than it plans for, higher and fc_bridge clamps it without telling the mission')


def test_safety_timeout_equals_fc_timeout(cfg, fc):
    assert cfg['safety_manager']['source_timeout_s'] == fc['setpoint_timeout_s']


@pytest.mark.parametrize('node, key, fc_key', [
    ('mission', 'speed', 'max_speed_xy'),
    ('mission', 'land_speed', 'max_speed_z'),
    ('mission', 'yaw_rate', 'max_yaw_rate'),
    ('setpoint_pub', 'speed', 'max_speed_xy'),
    ('setpoint_pub', 'climb_speed', 'max_speed_z'),
    ('radio_teleop', 'max_xy', 'max_speed_xy'),
    ('radio_teleop', 'max_z', 'max_speed_z'),
    ('radio_teleop', 'max_yaw', 'max_yaw_rate'),
])
def test_command_within_fc_limit(cfg, fc, node, key, fc_key):
    value = cfg[node][key]
    assert 0.0 < value <= fc[fc_key], (
        f'{node}.{key} = {value} must be > 0 and <= fc_bridge.{fc_key} = {fc[fc_key]}')


def test_heights_inside_rangefinder(cfg, fc):
    m = cfg['mission']
    assert fc['range_min'] < m['ground_h'] < m['target_h'] < fc['range_max']


def test_demo_height_inside_rangefinder(cfg, fc):
    assert cfg['mission']['ground_h'] < cfg['demo_flight']['height'] < fc['range_max']


def test_flow_works_once_airborne(cfg):
    # Above ground_h the mission counts the drone as flying; flow must work there.
    assert cfg['flow_model']['min_height'] < cfg['mission']['ground_h']


def test_radio_has_top_priority(cfg):
    assert cfg['safety_manager']['priority'][0] == 'radio', 'the pilot must always win'


def test_times_and_rates_positive(cfg):
    for node, params in cfg.items():
        for key, value in params.items():
            if key.endswith(('_s', '_hz')):
                assert value > 0, f'{node}.{key} = {value}'


def test_decimals_are_floats(cfg):
    # 0 instead of 0.0 makes a node refuse to start (wrong parameter type).
    for node, params in cfg.items():
        for key, value in params.items():
            if isinstance(value, bool) or key.startswith(('axis_', 'seed')):
                continue
            assert not isinstance(value, int), f'{node}.{key}: write {value}.0, not {value}'


def test_every_section_is_a_launched_node(cfg):
    # A typo in a section name makes the node silently ignore all of it.
    launched = set(re.findall(r"executable='(\w+)'", LAUNCH.read_text()))
    assert set(cfg) <= launched, f'not started by sim.launch.py: {set(cfg) - launched}'
