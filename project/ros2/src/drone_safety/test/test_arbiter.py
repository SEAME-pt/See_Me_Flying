"""Command arbitration: which source reaches fc_bridge, without ROS."""
from drone_safety.arbiter import Arbiter, NONE

PRIORITY = ['radio', 'manual', 'mission']


def make():
    return Arbiter(PRIORITY, 0.3)


def test_nothing_active_at_start():
    a = make()
    assert a.active(0.0) == NONE
    assert a.update(0.0) is None, 'starts at none: no change to report'


def test_single_source_is_forwarded():
    a = make()
    assert a.on_command(1.0, 'mission')
    assert a.active(1.0) == 'mission'


def test_radio_takes_over_from_mission():
    a = make()
    a.on_command(1.0, 'mission')
    assert a.on_command(1.05, 'radio')
    assert not a.on_command(1.1, 'mission'), 'mission is dropped while the radio commands'
    assert a.active(1.1) == 'radio'


def test_manual_beats_mission_but_not_radio():
    a = make()
    a.on_command(1.0, 'mission')
    assert a.on_command(1.0, 'manual')
    a.on_command(1.0, 'radio')
    assert not a.on_command(1.05, 'manual')


def test_control_returns_when_the_radio_goes_quiet():
    a = make()
    a.on_command(1.0, 'radio')
    a.on_command(1.0, 'mission')
    assert not a.on_command(1.2, 'mission')
    assert a.on_command(1.35, 'mission'), 'radio silent for more than timeout_s'
    assert a.active(1.35) == 'mission'


def test_everything_quiet_is_none():
    a = make()
    a.on_command(1.0, 'mission')
    assert a.active(1.29) == 'mission'
    assert a.active(1.31) == NONE


def test_unknown_source_is_never_forwarded():
    a = make()
    assert not a.on_command(1.0, 'keyboard')
    assert a.active(1.0) == NONE


def test_update_reports_changes_once():
    a = make()
    a.on_command(1.0, 'mission')
    assert a.update(1.0) == 'mission'
    assert a.update(1.1) is None
    a.on_command(1.15, 'radio')
    assert a.update(1.15) == 'radio'
    assert a.update(1.6) == NONE


def test_time_going_backwards_is_not_fresh():
    a = make()
    a.on_command(10.0, 'radio')
    assert a.active(5.0) == NONE, 'sim time reset: an old command must not count'
