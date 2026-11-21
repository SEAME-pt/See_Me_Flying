"""
camera_view: time to contact from the drone's camera (issue #226).

Reads camera/image, works out with optical flow how many seconds until the
drone would hit whatever is straight ahead (drone_sim/ttc.py explains how),
publishes it on camera/time_to_contact and warns when it is below ttc_warn_s.
The warning only says the drone shouldn't fly forward; nothing is stopped.

In the sim the image comes from Gazebo's fpv_camera through gz_bridge.yaml; on
the real drone any camera node that publishes camera/image works the same way.

The window shows the camera with:
  green box     the part of the image that counts as "ahead"
  yellow lines  optical flow (how far the image moved, x4 so it is visible)
  text          time to contact; red when below ttc_warn_s
"""
import math

import cv2
from cv_bridge import CvBridge
from drone_sim.ttc import centre, TimeToContact
import rclpy
from rclpy._rclpy_pybind11 import RCLError
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32

GREEN, YELLOW, RED, WHITE = (0, 200, 0), (0, 220, 255), (0, 0, 255), (255, 255, 255)


class CameraView(Node):
    def __init__(self):
        super().__init__('camera_view')
        self.warn_s = self.declare_parameter('ttc_warn_s', 2.0).value
        self.show = self.declare_parameter('show', True).value
        self.ttc = TimeToContact(
            width=self.declare_parameter('width', 320).value,
            roi=self.declare_parameter('roi', 0.4).value,
            smoothing=self.declare_parameter('smoothing', 0.3).value,
            min_texture=self.declare_parameter('min_texture', 8.0).value)
        self.bridge = CvBridge()
        self.pub = self.create_publisher(Float32, 'camera/time_to_contact', 10)
        self.create_subscription(Image, 'camera/image', self.on_image, 10)
        self.get_logger().info(f'Waiting for camera/image; warning below {self.warn_s:.1f} s')

    def on_image(self, msg):
        # The ROS image becomes a normal OpenCV image: a NumPy array (height, width, 3).
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9   # sim time
        seconds = self.ttc.update(frame, t)

        if seconds is not None:
            self.pub.publish(Float32(data=seconds))
            if seconds < self.warn_s:
                self.get_logger().warn(
                    f'Obstacle ahead: contact in {seconds:.1f} s, should not fly forward',
                    throttle_duration_sec=1.0)
        if self.show:
            self.draw(frame, seconds)
            cv2.imshow('camera', frame)
            cv2.waitKey(1)

    def draw(self, frame, seconds):
        """Draw the "ahead" box, the optical flow and the time to contact on frame."""
        h, w = frame.shape[:2]
        k = w / self.ttc.width          # flow is measured on the small image
        dh, dw = int(h * (1 - self.ttc.roi) / 2), int(w * (1 - self.ttc.roi) / 2)
        cv2.rectangle(frame, (dw, dh), (w - dw, h - dh), GREEN, 2)

        flow = self.ttc.flow
        if flow is not None:
            box = centre(flow, self.ttc.roi)
            y0 = (flow.shape[0] - box.shape[0]) // 2
            x0 = (flow.shape[1] - box.shape[1]) // 2
            for y in range(0, box.shape[0], 8):
                for x in range(0, box.shape[1], 8):
                    u, v = box[y, x]
                    p = (int((x0 + x) * k), int((y0 + y) * k))
                    q = (int(p[0] + 4 * u * k), int(p[1] + 4 * v * k))
                    cv2.line(frame, p, q, YELLOW, 1)

        if seconds is None:
            text, colour = 'no texture ahead' if not self.ttc.textured else '...', WHITE
        elif math.isinf(seconds):
            text, colour = 'contact: never', GREEN
        else:
            text, colour = f'contact in {seconds:.1f} s', RED if seconds < self.warn_s else WHITE
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, colour, 2)


def main(args=None):
    rclpy.init(args=args)
    node = CameraView()
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
