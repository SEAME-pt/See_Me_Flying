import ast
import time

import cv2
import numpy as np
import onnxruntime as ort
import rclpy
from cv_bridge import CvBridge
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose

SENSOR_QOS = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                        history=HistoryPolicy.KEEP_LAST, depth=1)


class YoloDetector(Node):
    def __init__(self):
        super().__init__('yolo_detector')
        self.declare_parameter('model_path', '')
        self.declare_parameter('conf_threshold', 0.4)
        self.declare_parameter('iou_threshold', 0.5)
        self.declare_parameter('mask_border_px', 0)

        path = self.get_parameter('model_path').value
        self.session = ort.InferenceSession(path, providers=ort.get_available_providers())
        inp = self.session.get_inputs()[0]
        self.input_name = inp.name
        self.size = int(inp.shape[2])                       # 640
        meta = self.session.get_modelmeta().custom_metadata_map
        self.names = ast.literal_eval(meta['names']) if 'names' in meta else {}
        self.get_logger().info(f'Loaded {path}: {len(self.names)} classes, '
                               f'providers {self.session.get_providers()}')

        self.bridge = CvBridge()
        self.create_subscription(Image, 'image_raw', self.on_image, SENSOR_QOS)
        self.det_pub = self.create_publisher(Detection2DArray, 'perception/detections', 10)
        self.dbg_pub = self.create_publisher(Image, 'perception/debug_image', SENSOR_QOS)

    def letterbox(self, img):
        """Resize keeping the aspect ratio, pad to a square, as YOLO was trained."""
        h, w = img.shape[:2]
        r = self.size / max(h, w)
        nh, nw = round(h * r), round(w * r)
        top, left = (self.size - nh) // 2, (self.size - nw) // 2
        canvas = np.full((self.size, self.size, 3), 114, np.uint8)
        canvas[top:top + nh, left:left + nw] = cv2.resize(img, (nw, nh))
        return canvas, r, left, top

    def on_image(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        work = frame.copy()
        b = self.get_parameter('mask_border_px').value
        if b > 0:                                           # hide INAV's OSD text
            work[:b] = 0
            work[-b:] = 0
            work[:, :b] = 0
            work[:, -b:] = 0

        canvas, r, left, top = self.letterbox(work)
        blob = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)[None]
        blob = blob.astype(np.float32) / 255.0

        t0 = time.perf_counter()
        pred = self.session.run(None, {self.input_name: blob})[0][0].T   # (N, 4 + classes)
        infer_ms = (time.perf_counter() - t0) * 1000.0

        conf = self.get_parameter('conf_threshold').value
        class_scores = pred[:, 4:]
        cls = class_scores.argmax(axis=1)
        scores = class_scores.max(axis=1)
        keep = scores > conf
        boxes, cls, scores = pred[keep, :4], cls[keep], scores[keep]

        # centre x, centre y, w, h in the padded square -> x, y, w, h in the frame
        xywh = np.empty_like(boxes)
        xywh[:, 0] = (boxes[:, 0] - boxes[:, 2] / 2 - left) / r
        xywh[:, 1] = (boxes[:, 1] - boxes[:, 3] / 2 - top) / r
        xywh[:, 2] = boxes[:, 2] / r
        xywh[:, 3] = boxes[:, 3] / r
        idx = cv2.dnn.NMSBoxes(xywh.tolist(), scores.tolist(), conf,
                               self.get_parameter('iou_threshold').value)

        out = Detection2DArray()
        out.header = msg.header
        for k in np.array(idx, dtype=int).flatten():
            x, y, w, h = (float(v) for v in xywh[k])
            label = self.names.get(int(cls[k]), str(int(cls[k])))
            det = Detection2D()
            det.header = msg.header
            det.bbox.center.position.x = x + w / 2
            det.bbox.center.position.y = y + h / 2
            det.bbox.size_x = w
            det.bbox.size_y = h
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id = label
            hyp.hypothesis.score = float(scores[k])
            det.results.append(hyp)
            out.detections.append(det)
            cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 0), 2)
            cv2.putText(frame, f'{label} {scores[k]:.2f}', (int(x), int(y) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        self.det_pub.publish(out)
        dbg = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
        dbg.header = msg.header
        self.dbg_pub.publish(dbg)

        age_ms = (self.get_clock().now() - Time.from_msg(msg.header.stamp)).nanoseconds / 1e6
        self.get_logger().info(
            f'{len(out.detections)} objects, inference {infer_ms:.1f} ms, '
            f'frame age {age_ms:.1f} ms', throttle_duration_sec=2.0)


def main(args=None):
    rclpy.init(args=args)
    node = YoloDetector()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
