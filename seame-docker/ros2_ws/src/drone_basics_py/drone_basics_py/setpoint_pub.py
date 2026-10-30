import math

from geometry_msgs.msg import TwistStamped
import rclpy
from rclpy._rclpy_pybind11 import RCLError
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class SetpointPub(Node):
    """
    Takeoff, then circles.

    Phase 1 (first takeoff_s seconds): climb straight up at climb_speed.
    Phase 2 (after that): fly a horizontal circle at speed, holding height.
    Time is the node clock, so with use_sim_time it follows Gazebo, not the wall.
    """

    def __init__(self):
        super().__init__('setpoint_pub')
        self.declare_parameter('rate_hz', 10.0)
        self.declare_parameter('speed', 0.3)        # m/s, circle speed
        self.declare_parameter('takeoff_s', 4.0)    # s of climbing before circling
        self.declare_parameter('climb_speed', 0.3)  # m/s; 4 s x 0.3 = 1.2 m
        rate = self.get_parameter('rate_hz').value
        self.pub = self.create_publisher(TwistStamped, 'setpoint_velocity', 10)
        self.t0 = None   # set on the first tick, once the (sim) clock is running
        self.phase = None
        self.timer = self.create_timer(1.0 / rate, self.tick)

    def tick(self):
        now = self.get_clock().now()
        if self.t0 is None:
            self.t0 = now
        t = (now - self.t0).nanoseconds * 1e-9
        takeoff_s = self.get_parameter('takeoff_s').value

        msg = TwistStamped()
        msg.header.stamp = now.to_msg()
        msg.header.frame_id = 'base_link'

        if t < takeoff_s:
            self.log_phase('takeoff')
            msg.twist.linear.z = self.get_parameter('climb_speed').value
        else:
            self.log_phase('circle')
            speed = self.get_parameter('speed').value  # read each tick: tunable live
            tc = t - takeoff_s
            msg.twist.linear.x = speed * math.cos(0.5 * tc)
            msg.twist.linear.y = speed * math.sin(0.5 * tc)

        self.pub.publish(msg)

    def log_phase(self, phase):
        if phase != self.phase:
            self.get_logger().info(f'Phase: {phase}')
            self.phase = phase


def main(args=None):
    rclpy.init(args=args)
    node = SetpointPub()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RCLError:
        # Ctrl-C can shut the context down between two waits; not a crash then.
        if rclpy.ok():
            raise
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
