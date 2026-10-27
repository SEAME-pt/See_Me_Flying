"""
Arm switch, debounce and stick mapping of radio_teleop, without a radio or a launch.

Calls on_joy directly and records what would be published. Default
parameters: axes 0-3 roll, pitch, throttle, yaw; arm on axis 4; all signs +1;
arm_hold_s 0.1. Times are the Joy header stamps, in seconds.
"""
from drone_basics_py.radio_teleop import RadioTeleop
import pytest
import rclpy
from sensor_msgs.msg import Joy

ARM_ON = 1.0
ARM_OFF = -1.0
HOLD_S = 0.1


class Recorder:
    def __init__(self):
        self.msgs = []

    def publish(self, msg):
        self.msgs.append(msg)


@pytest.fixture
def teleop():
    rclpy.init()
    node = RadioTeleop()
    node.pub = Recorder()
    yield node
    node.destroy_node()
    rclpy.shutdown()


def joy(t, roll=0.0, pitch=0.0, throttle=0.0, yaw=0.0, arm=ARM_OFF):
    msg = Joy(axes=[roll, pitch, throttle, yaw, arm])
    msg.header.stamp.sec = int(t)
    msg.header.stamp.nanosec = int(round((t - int(t)) * 1e9))
    return msg


def engage(teleop, t=10.0):
    """Arm cleanly: switch on, held past arm_hold_s. Returns the time it engaged."""
    teleop.on_joy(joy(t, arm=ARM_ON))
    teleop.on_joy(joy(t + HOLD_S + 0.05, arm=ARM_ON))
    assert teleop.engaged
    return t + HOLD_S + 0.05


def test_switch_off_publishes_nothing(teleop):
    teleop.on_joy(joy(10.0, pitch=1.0))
    assert teleop.pub.msgs == []
    assert not teleop.engaged


def test_engage_after_hold(teleop):
    engage(teleop)
    assert len(teleop.pub.msgs) == 1


def test_no_engage_before_hold(teleop):
    teleop.on_joy(joy(10.0, arm=ARM_ON))
    teleop.on_joy(joy(10.0 + HOLD_S - 0.02, arm=ARM_ON))
    assert not teleop.engaged
    assert teleop.pub.msgs == []


def test_bounce_while_arming_does_not_engage(teleop):
    # A burst like the ones arm_bounce.py recorded: flips a few ms apart.
    for t, arm in [(10.000, ARM_ON), (10.005, ARM_OFF), (10.010, ARM_ON),
                   (10.044, ARM_OFF), (10.050, ARM_ON), (10.053, ARM_OFF),
                   (10.080, ARM_ON)]:
        teleop.on_joy(joy(t, arm=arm))
    assert not teleop.engaged
    assert teleop.pub.msgs == []


def test_engages_once_bounce_settles(teleop):
    for t, arm in [(10.000, ARM_ON), (10.005, ARM_OFF), (10.010, ARM_ON)]:
        teleop.on_joy(joy(t, arm=arm))
    teleop.on_joy(joy(10.010 + HOLD_S - 0.01, arm=ARM_ON))
    assert not teleop.engaged, 'hold must count from the last bounce, not the first on'
    teleop.on_joy(joy(10.010 + HOLD_S + 0.01, arm=ARM_ON))
    assert teleop.engaged


def test_off_is_immediate(teleop):
    t = engage(teleop)
    teleop.on_joy(joy(t + 0.001, pitch=1.0, arm=ARM_OFF))
    assert not teleop.engaged
    assert len(teleop.pub.msgs) == 1


def test_bounce_while_disarming_does_not_reengage(teleop):
    t = engage(teleop)
    for dt, arm in [(0.1, ARM_OFF), (0.102, ARM_ON), (0.106, ARM_OFF),
                    (0.110, ARM_ON), (0.140, ARM_OFF)]:
        teleop.on_joy(joy(t + dt, arm=arm))
    assert not teleop.engaged
    assert len(teleop.pub.msgs) == 1


def test_engage_refused_with_throttle_off_centre(teleop):
    teleop.on_joy(joy(10.0, throttle=0.5, arm=ARM_ON))
    teleop.on_joy(joy(10.5, throttle=0.5, arm=ARM_ON))
    assert teleop.pub.msgs == []
    assert not teleop.engaged


def test_throttle_moves_freely_once_engaged(teleop):
    t = engage(teleop)
    teleop.on_joy(joy(t + 0.05, throttle=1.0, arm=ARM_ON))
    assert teleop.pub.msgs[-1].twist.linear.z == pytest.approx(0.3)


def test_sticks_scaled_to_limits(teleop):
    t = engage(teleop)
    teleop.on_joy(joy(t + 0.05, roll=-1.0, pitch=0.5, throttle=-1.0, yaw=1.0, arm=ARM_ON))
    tw = teleop.pub.msgs[-1].twist
    assert tw.linear.x == pytest.approx(0.25)
    assert tw.linear.y == pytest.approx(-0.5)
    assert tw.linear.z == pytest.approx(-0.3)
    assert tw.angular.z == pytest.approx(1.0)
    assert teleop.pub.msgs[-1].header.frame_id == 'base_link'


def test_deadband_gives_zero(teleop):
    t = engage(teleop)
    teleop.on_joy(joy(t + 0.05, roll=0.05, pitch=-0.05, yaw=0.07, arm=ARM_ON))
    tw = teleop.pub.msgs[-1].twist
    assert (tw.linear.x, tw.linear.y, tw.angular.z) == (0.0, 0.0, 0.0)


def test_reengage_needs_throttle_centred_again(teleop):
    t = engage(teleop)
    teleop.on_joy(joy(t + 0.05, arm=ARM_OFF))
    teleop.on_joy(joy(t + 0.10, throttle=0.8, arm=ARM_ON))
    teleop.on_joy(joy(t + 0.50, throttle=0.8, arm=ARM_ON))
    assert not teleop.engaged
    assert len(teleop.pub.msgs) == 1


def test_switch_at_threshold_is_off(teleop):
    teleop.on_joy(joy(10.0, arm=0.5))
    teleop.on_joy(joy(10.5, arm=0.5))
    assert teleop.pub.msgs == []


def test_missing_arm_axis_is_off(teleop):
    teleop.on_joy(Joy(axes=[0.0, 0.0, 0.0, 0.0]))
    assert teleop.pub.msgs == []
