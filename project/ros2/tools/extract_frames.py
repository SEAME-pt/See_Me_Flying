import sys
from pathlib import Path

import cv2
from cv_bridge import CvBridge
from rclpy.serialization import deserialize_message
from rosbag2_py import ConverterOptions, SequentialReader, StorageOptions
from sensor_msgs.msg import Image

bag, out = sys.argv[1], Path(sys.argv[2])
every = int(sys.argv[3]) if len(sys.argv) > 3 else 15
out.mkdir(parents=True, exist_ok=True)

reader = SequentialReader()
reader.open(StorageOptions(uri=bag, storage_id='mcap'), ConverterOptions('cdr', 'cdr'))
bridge = CvBridge()
n = saved = 0
while reader.has_next():
    topic, data, _ = reader.read_next()
    if topic != '/image_raw':
        continue
    if n % every == 0:
        img = bridge.imgmsg_to_cv2(deserialize_message(data, Image), 'bgr8')
        cv2.imwrite(str(out / f'{Path(bag).name}_{n:06d}.jpg'), img)
        saved += 1
    n += 1
print(f'saved {saved} of {n} frames to {out}')
