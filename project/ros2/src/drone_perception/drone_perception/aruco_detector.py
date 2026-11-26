import cv2
from cv_bridge import CvBridge
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose

# Newest frame only: drop old frames instead of queueing them
SENSOR_QOS = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                        history=HistoryPolicy.KEEP_LAST, depth=1)


def mask_border(img, b):
    """Black out the frame edges, where INAV's OSD text sits."""
    if b > 0:
        img[:b] = 0
        img[-b:] = 0
        img[:, :b] = 0
        img[:, -b:] = 0
    return img


class ArucoDetector(Node):
    def __init__(self):
        super().__init__('aruco_detector')
        self.declare_parameter('dictionary', 'DICT_4X4_50')
        self.declare_parameter('marker_size_m', 0.10)
        self.declare_parameter('mask_border_px', 0)

        name = self.get_parameter('dictionary').value
        self.dict = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, name))
        if hasattr(cv2.aruco, 'ArucoDetector'):           # OpenCV >= 4.7
            self.detector = cv2.aruco.ArucoDetector(self.dict, cv2.aruco.DetectorParameters())
        else:                                              # OpenCV 4.6
            self.detector = None
            self.params = cv2.aruco.DetectorParameters_create()

        self.bridge = CvBridge()
        self.K = None
        self.D = None
        self.create_subscription(CameraInfo, 'camera_info', self.on_info, SENSOR_QOS)
        self.create_subscription(Image, 'image_raw', self.on_image, SENSOR_QOS)
        self.det_pub = self.create_publisher(Detection2DArray, 'perception/detections', 10)
        self.dbg_pub = self.create_publisher(Image, 'perception/debug_image', SENSOR_QOS)

    def on_info(self, msg):
        if self.K is None and msg.k[0] > 0.0:
            self.K = np.array(msg.k, dtype=np.float64).reshape(3, 3)
            self.D = np.array(msg.d, dtype=np.float64)
            self.get_logger().info('Calibration received: marker positions enabled')

    def detect(self, gray):
        if self.detector is not None:
            return self.detector.detectMarkers(gray)
        return cv2.aruco.detectMarkers(gray, self.dict, parameters=self.params)

    def on_image(self, msg):
        t0 = self.get_clock().now()
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mask_border(gray, self.get_parameter('mask_border_px').value)
        corners, ids, _ = self.detect(gray)

        out = Detection2DArray()
        out.header = msg.header
        if ids is not None:
            s = self.get_parameter('marker_size_m').value / 2.0
            # Marker corners in the marker's own frame, OpenCV corner order
            obj = np.array([[-s, s, 0], [s, s, 0], [s, -s, 0], [-s, -s, 0]], np.float32)
            for c, marker_id in zip(corners, ids.flatten()):
                pts = c.reshape(4, 2).astype(np.float32)
                det = Detection2D()
                det.header = msg.header
                det.id = str(int(marker_id))
                det.bbox.center.position.x = float(pts[:, 0].mean())
                det.bbox.center.position.y = float(pts[:, 1].mean())
                det.bbox.size_x = float(pts[:, 0].max() - pts[:, 0].min())
                det.bbox.size_y = float(pts[:, 1].max() - pts[:, 1].min())
                hyp = ObjectHypothesisWithPose()
                hyp.hypothesis.class_id = f'aruco_{int(marker_id)}'
                hyp.hypothesis.score = 1.0
                if self.K is not None:
                    ok, _rvec, tvec = cv2.solvePnP(obj, pts, self.K, self.D,
                                                   flags=cv2.SOLVEPNP_IPPE_SQUARE)
                    if ok:
                        x, y, z = (float(v) for v in tvec.flatten())
                        hyp.pose.pose.position.x = x
                        hyp.pose.pose.position.y = y
                        hyp.pose.pose.position.z = z
                det.results.append(hyp)
                out.detections.append(det)
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

        self.det_pub.publish(out)
        dbg = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
        dbg.header = msg.header
        self.dbg_pub.publish(dbg)

        now = self.get_clock().now()
        proc_ms = (now - t0).nanoseconds / 1e6
        age_ms = (now - Time.from_msg(msg.header.stamp)).nanoseconds / 1e6
        self.get_logger().info(
            f'{len(out.detections)} markers, processing {proc_ms:.1f} ms, '
            f'frame age {age_ms:.1f} ms', throttle_duration_sec=2.0)


def main(args=None):
    rclpy.init(args=args)
    node = ArucoDetector()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
