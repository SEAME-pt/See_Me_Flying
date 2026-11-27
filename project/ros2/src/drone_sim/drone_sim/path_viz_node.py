"""
path_viz: where the drone was told to go, thinks it is and really is, as lines (sim only).

The lines go to RViz (nav_msgs/Path topics) and, when a Gazebo window is open, into
that window as markers. Markers are drawn on screen only: sensors don't see them.
"""

import threading
import time

from drone_sim.path_viz import Paths
from geometry_msgs.msg import PointStamped, PoseStamped, TransformStamped
from nav_msgs.msg import Odometry, Path
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from tf2_ros import StaticTransformBroadcaster

# The frame every line is drawn in: Gazebo's world, where the drone spawns.
FRAME = 'world'
# Latched: an RViz opened later still gets the lines drawn so far.
LATCHED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
# Line colours (red, green, blue) in the Gazebo window; the RViz config uses the same.
COLORS = {'planned': (0.1, 0.4, 1.0), 'estimated': (1.0, 0.55, 0.0), 'true': (0.0, 0.8, 0.0)}


def position(msg):
    """Return (x, y, z) of an Odometry message."""
    p = msg.pose.pose.position
    return p.x, p.y, p.z


class GazeboLines:
    """
    Draw the lines in the Gazebo window, through its /marker service.

    Requests go out from a thread of their own, at most twice a second: with no
    window open, each request waits for its timeout, and ROS callbacks must not.
    Needs Gazebo's Python bindings (they come with ros_gz); without them the
    constructor raises ImportError.
    """

    def __init__(self, logger):
        from gz.msgs10.empty_pb2 import Empty
        from gz.msgs10.marker_pb2 import Marker
        from gz.transport13 import Node as GzNode
        self.marker_type, self.reply_type = Marker, Empty
        self.node = GzNode()
        self.logger = logger
        self.pending = {}
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.warned = False
        threading.Thread(target=self.run, daemon=True).start()

    def draw(self, lines):
        """Queue lines to draw, {name: [(x, y, z), ...]}; a newer copy replaces an older one."""
        with self.lock:
            self.pending.update(lines)
        self.wake.set()

    def run(self):
        while True:
            self.wake.wait()
            self.wake.clear()
            with self.lock:
                lines, self.pending = self.pending, {}
            try:
                # every line is sent, even after one goes unanswered
                answered = True
                for name, points in lines.items():
                    answered = self.send(name, points) and answered
            except Exception as e:
                self.logger.error(f'Gazebo drawing stopped (RViz unaffected): {e}')
                return
            if not answered and not self.warned:
                self.logger.warning('no Gazebo window answering: lines in RViz only for now')
                self.warned = True
            time.sleep(0.5)

    def send(self, name, points):
        """Replace one line in the window; True if the window answered."""
        m = self.marker_type()
        m.ns = f'path_viz/{name}'
        m.id = 1
        m.action = self.marker_type.ADD_MODIFY
        m.type = self.marker_type.LINE_STRIP
        r, g, b = COLORS[name]
        for color in (m.material.ambient, m.material.diffuse, m.material.emissive):
            color.r, color.g, color.b, color.a = r, g, b, 1.0
        for x, y, z in points:
            p = m.point.add()
            p.x, p.y, p.z = x, y, z
        ok, _ = self.node.request('/marker', m, self.marker_type, self.reply_type, 300)
        return ok


class PathViz(Node):
    """Publish viz/path/planned, estimated (fc/odom) and true (ground truth) in FRAME."""

    def __init__(self):
        super().__init__('path_viz')
        self.paths = Paths(
            step=self.declare_parameter('step', 0.03).value,
            max_points=self.declare_parameter('max_points', 3000).value)
        self.pubs = {name: self.create_publisher(Path, f'viz/path/{name}', LATCHED)
                     for name in self.paths.lines}
        self.changed = dict.fromkeys(self.paths.lines, False)
        self.tf = StaticTransformBroadcaster(self)
        # gazebo: also draw in the Gazebo window (set false when there is none)
        self.gazebo = None
        if self.declare_parameter('gazebo', True).value:
            try:
                self.gazebo = GazeboLines(self.get_logger())
            except ImportError:
                self.get_logger().warning('no Gazebo Python bindings: lines in RViz only')
        self.create_subscription(Odometry, 'fc/odom', self.on_estimate, 10)
        self.create_subscription(Odometry, '/sim/ground_truth', self.on_truth, 10)
        self.create_subscription(PointStamped, 'mission/target', self.on_target, 10)
        self.create_timer(0.2, self.publish)
        self.get_logger().info('path_viz running: mission/target, fc/odom and ground truth '
                               '-> viz/path/*')

    def on_truth(self, msg):
        if self.paths.add_truth(position(msg)):
            self.changed['true'] = True

    def on_target(self, msg):
        if self.paths.add_target((msg.point.x, msg.point.y, msg.point.z)):
            self.changed['planned'] = True

    def on_estimate(self, msg):
        lined_up = self.paths.shift is not None
        if self.paths.add_estimate(position(msg)):
            self.changed['estimated'] = True
        if not lined_up and self.paths.shift is not None:
            self.publish_odom_frame()

    def publish_odom_frame(self):
        """
        Place odom (fc/odom's frame) in FRAME, shifted by the start points' difference.

        RViz needs FRAME in its transform tree to draw anything; this puts it there.
        """
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = FRAME
        t.child_frame_id = 'odom'
        x, y, z = self.paths.shift
        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.translation.z = z
        t.transform.rotation.w = 1.0
        self.tf.sendTransform(t)
        self.get_logger().info(f"lined up: odom's (0, 0) is ({x:.2f}, {y:.2f}) in {FRAME}")

    def publish(self):
        """Publish the lines that have new points, to RViz and to the Gazebo window."""
        names = [name for name, changed in self.changed.items() if changed]
        if not names:
            return
        stamp = self.get_clock().now().to_msg()
        for name in names:
            self.pubs[name].publish(self.path_msg(name, stamp))
            self.changed[name] = False
        if self.gazebo is not None:
            self.gazebo.draw({name: list(self.paths.lines[name].points) for name in names})

    def path_msg(self, name, stamp):
        """Build the nav_msgs/Path of one line."""
        msg = Path()
        msg.header.stamp = stamp
        msg.header.frame_id = FRAME
        for x, y, z in self.paths.lines[name].points:
            pose = PoseStamped()
            pose.header = msg.header
            pose.pose.position.x = x
            pose.pose.position.y = y
            pose.pose.position.z = z
            pose.pose.orientation.w = 1.0
            msg.poses.append(pose)
        return msg


def main():
    rclpy.init()
    rclpy.spin(PathViz())
