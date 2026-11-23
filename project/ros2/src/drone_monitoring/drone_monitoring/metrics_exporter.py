"""
metrics_exporter: the drone's state for Prometheus and Grafana (make monitor).

Subscribes to what fc_bridge, the sensors and safety_manager publish and serves
it on http://<address>:<port>/metrics (127.0.0.1:9105, scraped by
monitoring/prometheus.yml). The metrics themselves are made in metrics.py.
Only listens: nothing here can command the drone.

Started by sim.launch.py with both backends. If the port is taken (another
exporter is running) it logs an error and exits; the rest of the stack runs on.
"""
from functools import partial

from drone_interfaces.msg import FcStatus, OpticalFlow
from drone_monitoring.metrics import DroneMetrics
from geometry_msgs.msg import QuaternionStamped, TwistStamped
from nav_msgs.msg import Odometry
from prometheus_client import CollectorRegistry, start_http_server
import rclpy
from rclpy._rclpy_pybind11 import RCLError
from rclpy.executors import ExternalShutdownException
from rclpy.logging import get_logger
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, qos_profile_sensor_data, QoSProfile
from sensor_msgs.msg import BatteryState, Range
from std_msgs.msg import String

# Counted per topic (rate and time since the last message on the dashboard).
TOPICS = {
    'fc/status': FcStatus,
    'fc/range': Range,
    'fc/odom': Odometry,
    'fc/attitude': QuaternionStamped,
    'fc/optical_flow': OpticalFlow,
    'fc/battery': BatteryState,              # nothing publishes it yet (the inav backend will)
    'fc/setpoint_velocity': TwistStamped,    # only while a source is commanding
}


class MetricsExporter(Node):
    def __init__(self):
        super().__init__('metrics_exporter')
        address = self.declare_parameter('address', '127.0.0.1').value
        port = self.declare_parameter('port', 9105).value
        stale = self.declare_parameter('stale_after_s', 3.0).value

        self.metrics = DroneMetrics(stale_after_s=stale)
        registry = CollectorRegistry()   # only ours, not the Python process metrics
        registry.register(self.metrics)
        start_http_server(port, addr=address, registry=registry)   # OSError if taken

        # Best effort takes messages from reliable and best-effort publishers alike.
        for topic, msg_type in TOPICS.items():
            self.create_subscription(msg_type, topic, partial(self.metrics.on_message, topic),
                                     qos_profile_sensor_data)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(String, 'safety/active_source',
                                 lambda msg: self.metrics.on_active_source(msg.data), latched)
        self.get_logger().info(f'Metrics on http://{address}:{port}/metrics')


def main(args=None):
    rclpy.init(args=args)
    try:
        node = MetricsExporter()
    except OSError as e:
        # Not worth stopping the drone stack for: log it and leave.
        get_logger('metrics_exporter').error(
            f'Cannot serve metrics ({e}): is another metrics_exporter running? '
            'Set another port with -p port:=<n>. Metrics off.')
        rclpy.try_shutdown()
        return
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RCLError:
        # Ctrl-C can shut the context down between two waits (same as safety_manager).
        if rclpy.ok():
            raise
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
