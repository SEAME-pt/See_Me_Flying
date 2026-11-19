import sys
import time

from drone_interfaces.msg import FcStatus, RcChannels
import rclpy

rclpy.init()
node = rclpy.create_node('bench_look')
got = {}
node.create_subscription(RcChannels, '/fc/rc', lambda m: got.setdefault('rc', m), 10)
node.create_subscription(FcStatus, '/fc/status', lambda m: got.setdefault('st', m), 10)
end = time.monotonic() + 3.0
while time.monotonic() < end and len(got) < 2:
    rclpy.spin_once(node, timeout_sec=0.1)
line = []
if 'rc' in got:
    r = got['rc']
    ch7 = r.channels[6] if len(r.channels) > 6 else 0
    line.append(f'fc/rc roll {r.roll} pitch {r.pitch} yaw {r.yaw} throttle {r.throttle} '
                f'ch7(SA) {ch7}')
else:
    line.append('fc/rc: nothing in 3 s')
if 'st' in got:
    s = got['st']
    line.append(f'override_active {s.rc_override_active} rc_sent {s.rc_sent} '
                f'link_ok {s.link_ok} armed {s.armed}')
else:
    line.append('fc/status: nothing in 3 s')
print(' | '.join(line))
if 'st' in got and got['st'].armed:
    print('ARMED: disarm now')
    sys.exit(3)
