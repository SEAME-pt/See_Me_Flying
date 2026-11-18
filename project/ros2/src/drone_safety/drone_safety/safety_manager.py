"""
safety_manager: the only publisher of fc/setpoint_velocity.

Sources publish on their own topics (cmd/radio, cmd/manual, cmd/mission). The
highest-priority one that is publishing wins (arbiter.py); its commands are
forwarded as they arrive, so arbitration adds no delay. The active source is
published on safety/active_source (latched) and logged on every change.
Grows out of the watchdog, which only logged a timeout. Times are the node
clock, so with use_sim_time everything follows Gazebo.
"""
from functools import partial

from drone_safety.arbiter import Arbiter, NONE
from geometry_msgs.msg import TwistStamped
import rclpy
from rclpy._rclpy_pybind11 import RCLError
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, qos_profile_sensor_data, QoSProfile
from sensor_msgs.msg import BatteryState
from std_msgs.msg import String


class SafetyManager(Node):
    def __init__(self):
        super().__init__('safety_manager')
        priority = self.declare_parameter('priority', ['radio', 'manual', 'mission']).value
        timeout = self.declare_parameter('source_timeout_s', 0.3).value
        self.battery_low = self.declare_parameter('battery_low', 0.2).value
        self.arbiter = Arbiter(priority, timeout)

        self.pub = self.create_publisher(TwistStamped, 'fc/setpoint_velocity', 10)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.active_pub = self.create_publisher(String, 'safety/active_source', latched)
        for source in priority:
            self.create_subscription(TwistStamped, f'cmd/{source}',
                                     partial(self.on_command, source), qos_profile_sensor_data)
        # Placeholder: nothing publishes fc/battery yet (the inav backend will).
        self.create_subscription(BatteryState, 'fc/battery', self.on_battery, 10)
        self.battery_warned = False
        self.create_timer(0.05, self.check)
        self.publish_active(NONE)
        self.get_logger().info(f'Priority: {" > ".join(priority)}; timeout {timeout:.2f} s')

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def on_command(self, source, msg):
        if self.arbiter.on_command(self.now(), source):
            self.check()                # log a takeover before its first command goes out
            self.pub.publish(msg)

    def check(self):
        changed = self.arbiter.update(self.now())
        if changed is None:
            return
        if changed == NONE:
            self.get_logger().warn('No source publishing: fc_bridge times out and sends zero')
        else:
            self.get_logger().info(f'Active source: {changed}')
        self.publish_active(changed)

    def publish_active(self, source):
        self.active_pub.publish(String(data=source))

    def on_battery(self, msg):
        # Hook for later: return or land on low battery. For now it only warns, once.
        low = 0.0 <= msg.percentage < self.battery_low
        if low and not self.battery_warned:
            self.get_logger().warn(f'Battery low ({msg.percentage:.0%}): would land (not yet)')
        self.battery_warned = low


def main(args=None):
    rclpy.init(args=args)
    node = SafetyManager()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RCLError:
        # Ctrl-C can shut the context down between two waits; the next wait then
        # fails. Not a crash if ROS is shutting down anyway (same as mission).
        if rclpy.ok():
            raise
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
