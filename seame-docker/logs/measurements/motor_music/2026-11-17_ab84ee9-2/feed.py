import sys

from geometry_msgs.msg import TwistStamped
import rclpy

path = sys.argv[1]
rclpy.init()
node = rclpy.create_node('bench_feed')
pub = node.create_publisher(TwistStamped, '/fc/setpoint_velocity', 10)
last = []


def tick():
    try:
        with open(path) as f:
            values = [float(v) for v in f.read().split()]
        if len(values) == 4:
            last[:] = values
    except (OSError, ValueError):
        pass
    if not last:
        return
    msg = TwistStamped()
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.header.frame_id = 'base_link'
    msg.twist.linear.x, msg.twist.linear.y, msg.twist.linear.z, msg.twist.angular.z = last
    pub.publish(msg)


node.create_timer(0.05, tick)
try:
    rclpy.spin(node)
except KeyboardInterrupt:
    pass
