"""
sweep_view: is the way ahead clear? From the camera and the odometry, with math only.

Reads camera/image and fc/odom (drone_sim/sweep.py explains the math). Publishes:
  obstacle/state        std_msgs/String: clear, obstacle or unknown
  obstacle/front_range  sensor_msgs/Range: distance ahead in m, stamped with the
                        image's time; inf = nothing found, nan = unknown
Unknown is also published when images or odometry stop. It only warns; nothing
is stopped. Unknown must never be treated as clear.

The window shows the camera with the corridor at the warning distance (box), the
points found in it (dots) and the answer.
"""
import math
import time

import cv2
from cv_bridge import CvBridge
from drone_sim.sweep import Config, HEIGHT, OBSTACLE, OdomBuffer, PlaneSweep, Result, WIDTH
from nav_msgs.msg import Odometry
import rclpy
from rclpy._rclpy_pybind11 import RCLError
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile
from sensor_msgs.msg import Image, Range
from std_msgs.msg import String

COLOURS = {'clear': (0, 200, 0), 'obstacle': (0, 0, 255), 'unknown': (0, 200, 255)}


def seconds(stamp):
    return stamp.sec + stamp.nanosec * 1e-9


class SweepView(Node):
    def __init__(self):
        super().__init__('sweep_view')
        self.show = self.declare_parameter('show', True).value
        self.silence_s = self.declare_parameter('silence_s', 0.5).value
        self.cfg = Config(warn_m=self.declare_parameter('warn_m', 1.5).value)
        self.sweep = PlaneSweep(cfg=self.cfg)
        self.odom = OdomBuffer()
        self.bridge = CvBridge()
        self.pending = None               # newest image, waiting for its odometry
        self.answered = time.monotonic()  # wall time: also works when the sim clock stops
        self.ms = 0.0
        self.state_pub = self.create_publisher(String, 'obstacle/state', 10)
        self.range_pub = self.create_publisher(Range, 'obstacle/front_range', 10)
        # Depth 1: only the newest image counts. Odometry: none may be lost meanwhile.
        latest = QoSProfile(depth=1, reliability=qos_profile_sensor_data.reliability)
        self.create_subscription(Image, 'camera/image', self.on_image, latest)
        self.create_subscription(Odometry, 'fc/odom', self.on_odom, 50)
        self.create_timer(0.1, self.check_silence,
                          clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.get_logger().info(f'Waiting for camera/image and fc/odom; '
                               f'warning below {self.cfg.warn_m:.1f} m')

    def on_image(self, msg):
        self.pending = msg
        self.process()

    def on_odom(self, msg):
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        self.odom.add(seconds(msg.header.stamp), (p.x, p.y, p.z), (q.x, q.y, q.z, q.w))
        self.process()

    def process(self):
        """Work on the waiting image once the odometry has reached its time."""
        msg = self.pending
        if msg is None or self.odom.newest() < seconds(msg.header.stamp):
            return
        self.pending = None
        t = seconds(msg.header.stamp)
        pose = self.odom.at(t)
        if pose is None:
            return                        # no odometry around it: check_silence reports it
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        start = time.perf_counter()
        result = self.sweep.update(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), t, pose)
        self.ms += 0.2 * (1000 * (time.perf_counter() - start) - self.ms)
        self.answered = time.monotonic()
        self.publish(result, msg.header.stamp)
        if result.state == OBSTACLE:
            self.get_logger().warn(
                f'Obstacle ahead: {result.distance:.2f} m, should not fly forward',
                throttle_duration_sec=1.0)
        if self.show:
            self.draw(frame, result, pose)
            cv2.imshow('sweep', frame)
            cv2.waitKey(1)

    def publish(self, result, stamp):
        self.state_pub.publish(String(data=result.state))
        out = Range()
        out.header.stamp = stamp
        out.header.frame_id = 'fpv_camera'
        out.field_of_view = 2 * math.atan(self.cfg.half_width / self.cfg.warn_m)
        out.min_range = self.cfg.nearest
        out.max_range = self.cfg.farthest
        out.range = result.distance
        self.range_pub.publish(out)

    def check_silence(self):
        """No answer for silence_s: say unknown instead of nothing."""
        if time.monotonic() - self.answered > self.silence_s:
            self.publish(Result(reason='no images or odometry'),
                         self.get_clock().now().to_msg())

    def draw(self, frame, result, pose):
        """Draw the corridor, the points found in it and the answer on frame."""
        k = frame.shape[1] / WIDTH
        colour = COLOURS[result.state]
        box = self.sweep.corridor_box(pose)
        if box is not None:
            (u0, v0), (u1, v1) = box
            cv2.rectangle(frame, (int(u0 * k), int(v0 * k)), (int(u1 * k), int(v1 * k)),
                          colour, 2)
        for u, v in (result.pixels if result.pixels is not None else [])[::3]:
            cv2.circle(frame, (int(u * k), int(v * k)), 2, colour, -1)
        text = f'{result.state}: {result.reason}'
        if math.isfinite(result.distance):
            text = f'{result.state}: {result.distance:.2f} m'
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, colour, 2)
        cv2.putText(frame, f'{self.ms:.0f} ms, checked {100 * result.seen:.0f}%',
                    (10, int(HEIGHT * k) - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 1)


def main(args=None):
    rclpy.init(args=args)
    node = SweepView()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RCLError:
        # Stopping can shut ROS down while a frame is being published: not a crash then.
        if rclpy.ok():
            raise
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.try_shutdown()
