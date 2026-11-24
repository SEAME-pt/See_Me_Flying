"""Check that sim_test_limits.yaml is complete and sensible, without running the sim."""

from pathlib import Path

import yaml

LIMITS = Path(__file__).resolve().parents[1] / 'config' / 'sim_test_limits.yaml'
EXPECTED = {'hover_height_mean', 'hover_height_std', 'hover_vz_std', 'flow_mean',
            'flow_std', 'pass_error', 'creep_1cm', 'creep_3cm'}


def load():
    with open(LIMITS) as f:
        return yaml.safe_load(f)['sensors']


def test_every_limit_is_there():
    assert set(load()) == EXPECTED


def test_limits_are_positive():
    for name, value in load().items():
        if not isinstance(value, list):
            assert value > 0, name


def test_bands_are_ordered_shares():
    for name, value in load().items():
        if isinstance(value, list):
            lo, hi = value
            assert 0.0 <= lo < hi <= 1.0, name
