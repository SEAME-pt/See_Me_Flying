"""
Log every arm switch change seen on /joy, and flag bounces.

Uses the radio_teleop settings from sim.yaml: axis 4, sign -1, threshold 0.5.
A bounce is a change less than BOUNCE_S after the previous one: a clean flip
gives one change, a bouncing switch gives a burst. Ctrl-C prints a summary.
"""
import sys

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Joy

AXIS_ARM = 4
SIGN_ARM = -1.0
ARM_THRESHOLD = 0.5
BOUNCE_S = 0.3


class ArmBounce(Node):
    def __init__(self):
        super().__init__('arm_bounce')
        self.armed = None
        self.last_change = None
        self.changes = 0
        self.bounces = 0
        self.create_subscription(Joy, '/joy', self.on_joy, 50)
        self.no_joy_timer = self.create_timer(3.0, self.warn_no_joy)
        print('Flip the arm switch (SA) on and off, slowly, about 20 times. Ctrl-C to stop.',
              flush=True)

    def warn_no_joy(self):
        if self.armed is None:
            print('No /joy messages yet: is joy_node running, and the radio plugged in '
                  '(lsusb on the host) in USB Joystick mode?', flush=True)

    def on_joy(self, msg):
        if len(msg.axes) <= AXIS_ARM:
            return
        raw = msg.axes[AXIS_ARM]
        armed = SIGN_ARM * raw > ARM_THRESHOLD
        if armed == self.armed:
            return
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if self.armed is None:
            print(f'start: {"ARMED" if armed else "off"} (raw {raw:+.2f})', flush=True)
        else:
            self.changes += 1
            dt = t - self.last_change
            bounce = dt < BOUNCE_S
            self.bounces += bounce
            mark = '  <-- BOUNCE' if bounce else ''
            print(f'{"ARMED" if armed else "off  "}  raw {raw:+.2f}  {dt * 1000:7.0f} ms '
                  f'after the previous change{mark}', flush=True)
        self.armed = armed
        self.last_change = t


def main():
    rclpy.init()
    node = ArmBounce()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    print(f'\n{node.changes} changes, {node.bounces} bounces (< {BOUNCE_S * 1000:.0f} ms apart)',
          file=sys.stderr)


if __name__ == '__main__':
    main()
