"""
Arm and takeover switches, debounce and stick mapping of radio_teleop, without a radio or a launch.

Calls on_joy directly and records what would be published. Default
parameters: axes 0-3 roll, pitch, throttle, yaw; arm on axis 4; all signs +1;
arm_hold_s 0.1; no takeover switch unless a test sets axis_takeover (then
axis 5). Times are the Joy header stamps, in seconds.
"""
from drone_basics_py.radio_teleop import RadioTeleop
import pytest
import rclpy
from rclpy.parameter import Parameter
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
    node.arm_requests = 0

    def request_arm():
        node.arm_requests += 1
    node.request_arm = request_arm
    yield node
    node.destroy_node()
    rclpy.shutdown()


def joy(t, roll=0.0, pitch=0.0, throttle=0.0, yaw=0.0, arm=ARM_OFF, takeover=ARM_OFF):
    msg = Joy(axes=[roll, pitch, throttle, yaw, arm, takeover])
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


def test_engaging_arms_the_fc_once(teleop):
    t = engage(teleop)
    teleop.on_joy(joy(t + 0.05, arm=ARM_ON))
    assert teleop.arm_requests == 1, 'after a Land disarmed it, the sticks must arm it again'


@pytest.fixture
def with_takeover(teleop):
    teleop.set_parameters([Parameter('axis_takeover', value=5)])
    return teleop


def test_arm_alone_does_not_take_over(with_takeover):
    with_takeover.on_joy(joy(10.0, arm=ARM_ON))
    with_takeover.on_joy(joy(10.5, pitch=1.0, arm=ARM_ON))
    assert with_takeover.pub.msgs == []
    assert with_takeover.arm_requests == 0


def test_takeover_alone_does_nothing(with_takeover):
    with_takeover.on_joy(joy(10.0, takeover=ARM_ON))
    with_takeover.on_joy(joy(10.5, takeover=ARM_ON))
    assert with_takeover.pub.msgs == []


def test_takeover_with_arm_on_engages_after_hold(with_takeover):
    with_takeover.on_joy(joy(10.0, arm=ARM_ON))
    with_takeover.on_joy(joy(11.0, arm=ARM_ON, takeover=ARM_ON))
    assert not with_takeover.engaged, 'the hold counts from the takeover, not from arming'
    with_takeover.on_joy(joy(11.0 + HOLD_S + 0.01, arm=ARM_ON, takeover=ARM_ON))
    assert with_takeover.engaged
    assert with_takeover.arm_requests == 1


def test_takeover_off_releases_at_once(with_takeover):
    with_takeover.on_joy(joy(10.0, arm=ARM_ON, takeover=ARM_ON))
    with_takeover.on_joy(joy(10.2, arm=ARM_ON, takeover=ARM_ON))
    assert with_takeover.engaged
    with_takeover.on_joy(joy(10.201, pitch=1.0, arm=ARM_ON, takeover=ARM_OFF))
    assert not with_takeover.engaged
    assert len(with_takeover.pub.msgs) == 1


def test_arm_off_releases_even_with_takeover_on(with_takeover):
    with_takeover.on_joy(joy(10.0, arm=ARM_ON, takeover=ARM_ON))
    with_takeover.on_joy(joy(10.2, arm=ARM_ON, takeover=ARM_ON))
    with_takeover.on_joy(joy(10.201, pitch=1.0, arm=ARM_OFF, takeover=ARM_ON))
    assert not with_takeover.engaged
    assert len(with_takeover.pub.msgs) == 1


def test_missing_takeover_axis_is_off(with_takeover):
    msg = Joy(axes=[0.0, 0.0, 0.0, 0.0, ARM_ON])
    with_takeover.on_joy(msg)
    msg.header.stamp.sec = 11
    with_takeover.on_joy(msg)
    assert with_takeover.pub.msgs == []
