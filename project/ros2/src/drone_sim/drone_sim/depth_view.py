"""
depth_view: distance to what is straight ahead, from the camera, with an AI depth model.

Reads camera/image and fc/range (height, used to scale the model to metres:
drone_sim/depth.py explains how), publishes camera/distance_ahead (m) and warns
when it is below warn_m. Like camera_view, it only warns; nothing is stopped.

The window shows, side by side:
  left   the camera; green box = what counts as "ahead", text = distance ahead
         (red below warn_m) and how many frames per second the model manages
  right  the model's depth map: bright = close, dark = far

The model file must be downloaded first: see drone_sim/depth.py.
"""
import os
import time

import cv2
from cv_bridge import CvBridge
from drone_sim.depth import DepthModel, DistanceAhead, FAR
import numpy as np
import rclpy
from rclpy._rclpy_pybind11 import RCLError
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile
from sensor_msgs.msg import Image, Range
from std_msgs.msg import Float32

GREEN, RED, WHITE = (0, 200, 0), (0, 0, 255), (255, 255, 255)
DEFAULT_MODEL = '~/project/models/depth_anything_v2_small.onnx'


class DepthView(Node):
    def __init__(self):
        super().__init__('depth_view')
        path = os.path.expanduser(self.declare_parameter('model', DEFAULT_MODEL).value)
        self.warn_m = self.declare_parameter('warn_m', 1.5).value
        self.show = self.declare_parameter('show', True).value
        self.roi = self.declare_parameter('roi', 0.4).value
        width = self.declare_parameter('model_width', 392).value
        if not os.path.isfile(path):
            raise SystemExit(f'No model at {path}: download it first (see drone_sim/depth.py)')
        model = DepthModel(path, width, width * 3 // 4)
        self.get_logger().info(f'Model {os.path.basename(path)} on '
                               f'{model.session.get_providers()[0]}, input {model.size}')
        self.estimator = DistanceAhead(model, roi=self.roi)
        self.bridge = CvBridge()
        self.height = float('nan')
        self.fps = 0.0
        self.pub = self.create_publisher(Float32, 'camera/distance_ahead', 10)
        # Depth 1: the model is slower than the camera, so only the newest frame counts.
        latest = QoSProfile(depth=1, reliability=qos_profile_sensor_data.reliability)
        self.create_subscription(Image, 'camera/image', self.on_image, latest)
        self.create_subscription(Range, 'fc/range', self.on_range, 10)
        self.get_logger().info(f'Waiting for camera/image; warning below {self.warn_m:.1f} m')

    def on_range(self, msg):
        self.height = msg.range

    def on_image(self, msg):
        start = time.perf_counter()
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        depth, distance = self.estimator.update(frame, self.height)
        self.fps += 0.2 * (1 / (time.perf_counter() - start) - self.fps)

        if distance is not None:
            self.pub.publish(Float32(data=distance))
            if distance < self.warn_m:
                self.get_logger().warn(
                    f'Obstacle ahead: {distance:.2f} m, should not fly forward',
                    throttle_duration_sec=1.0)
        if self.show:
            cv2.imshow('depth', self.draw(frame, depth, distance))
            cv2.waitKey(1)

    def draw(self, frame, depth, distance):
        """Return the camera with the overlay, next to the colour depth map."""
        h, w = frame.shape[:2]
        dh, dw = int(h * (1 - self.roi) / 2), int(w * (1 - self.roi) / 2)
        cv2.rectangle(frame, (dw, dh), (w - dw, h - dh), GREEN, 2)
        if distance is None:
            text, colour = 'take off first (scale comes from the floor)', WHITE
            right = np.zeros_like(frame)
        else:
            text = f'ahead: {distance:.2f} m' if distance < FAR - 1 else 'ahead: nothing'
            colour = RED if distance < self.warn_m else WHITE
            near = np.clip(1 - depth / 8.0, 0, 1)            # 0..8 m: bright = close
            right = cv2.applyColorMap((near * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
            cv2.rectangle(right, (dw, dh), (w - dw, h - dh), GREEN, 2)
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, colour, 2)
        cv2.putText(frame, f'{self.fps:.1f} frames/s, height {self.height:.2f} m', (10, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 1)
        return np.hstack([frame, right])


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = DepthView()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RCLError:
        # Stopping can shut ROS down while a frame is being published: not a crash then.
        if rclpy.ok():
            raise
    finally:
        cv2.destroyAllWindows()
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
