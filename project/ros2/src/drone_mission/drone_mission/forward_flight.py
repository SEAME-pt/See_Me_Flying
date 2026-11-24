"""
forward_flight: take off, fly forward until something gets in the way, hover there.

A client of the mission's action servers, like demo_flight: Takeoff, then one long
Goto at `speed`. It listens to obstacle/front_range (drone_sim sweep_view) and to
fc/odom, and cancels the Goto, which makes the mission hover, when
drone_mission/forward.py says so: an obstacle ahead, or no idea what is ahead. With
land:=true it lands after.

If this node dies during the Goto nothing would cancel it, so the launch file shuts
everything down when it exits: fc_bridge then gets no commands and holds.
"""
import math

from action_msgs.msg import GoalStatus
from drone_interfaces.action import Goto, Land, Takeoff
from drone_mission.forward import Forward, OBSTACLE, Params
from nav_msgs.msg import Odometry
import rclpy
from rclpy._rclpy_pybind11 import RCLError
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Range
from std_msgs.msg import String


class ForwardFlight(Node):
    def __init__(self):
        super().__init__('forward_flight')
        self.height = self.declare_parameter('height', 1.2).value
        self.max_m = self.declare_parameter('max_distance', 20.0).value
        self.speed = self.declare_parameter('speed', 0.4).value
        self.land = self.declare_parameter('land', False).value
        self.logic = Forward(Params(
            stop_m=self.declare_parameter('stop_m', 1.5).value,
            confirm=self.declare_parameter('confirm', 3).value,
            blind_s=self.declare_parameter('blind_s', 1.0).value,
            start_s=self.declare_parameter('start_s', 3.0).value))
        self.goto_handle = None
        self.reason = None
        self.here = None                  # (x, y) now and where flying forward began
        self.began = None
        self.actions = {name: ActionClient(self, kind, f'mission/{name}')
                        for name, kind in [('takeoff', Takeoff), ('goto', Goto),
                                           ('land', Land)]}
        self.pub = self.create_publisher(String, 'forward_flight/status', 10)
        self.create_subscription(Range, 'obstacle/front_range', self.on_range, 10)
        self.create_subscription(Odometry, 'fc/odom', self.on_odom, 10)
        self.create_timer(0.05, self.check)
        self.retry = self.create_timer(1.0, self.take_off)
        self.say('waiting for the mission')

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def say(self, text):
        self.get_logger().info(text)
        self.pub.publish(String(data=text))

    def send(self, name, goal, accepted):
        """Send a goal; call accepted(handle) with its handle, None when refused."""
        def done(future):
            handle = future.result()
            accepted(handle if handle.accepted else None)
        self.actions[name].send_goal_async(goal).add_done_callback(done)

    # Takeoff: refused until the rangefinder is up and the drone is armed, so ask again.

    def take_off(self):
        if not self.actions['takeoff'].server_is_ready():
            return
        self.retry.cancel()
        self.send('takeoff', Takeoff.Goal(height=self.height), self.taking_off)

    def taking_off(self, handle):
        if handle is None:
            self.retry.reset()
            return
        self.say('taking off')
        handle.get_result_async().add_done_callback(self.took_off)

    def took_off(self, future):
        result = future.result().result
        if not result.success:
            self.say(f'takeoff failed: {result.message}')
            return
        self.send('goto', Goto.Goal(forward=self.max_m, speed=self.speed), self.going)

    # Forward

    def going(self, handle):
        if handle is None:
            self.say('flying forward was refused')
            return
        self.goto_handle = handle
        self.logic.begin(self.now())
        self.began = self.here
        self.say(f'flying forward at {self.speed:.1f} m/s, up to {self.max_m:.0f} m')
        handle.get_result_async().add_done_callback(self.stopped)

    def on_range(self, msg):
        self.logic.on_distance(self.now(), msg.range)

    def on_odom(self, msg):
        self.here = (msg.pose.pose.position.x, msg.pose.pose.position.y)
        if self.began is not None:
            self.logic.on_flown(math.dist(self.here, self.began))

    def check(self):
        if self.goto_handle is None or self.reason is not None:
            return
        self.reason = self.logic.why_stop(self.now())
        if self.reason is None:
            return
        if self.reason == OBSTACLE:
            self.say(f'something in the way: stopping (camera {self.logic.distance:.2f} m, '
                     f'remembered {self.logic.left():.2f} m)')
        else:
            self.say('cannot see what is ahead: stopping')
        self.goto_handle.cancel_goal_async().add_done_callback(self.cancelled)

    def cancelled(self, future):
        if not future.result().goals_canceling and self.goto_handle is not None:
            self.get_logger().error('stop refused, asking again')
            self.reason = None

    def stopped(self, future):
        self.goto_handle = None
        status, result = future.result().status, future.result().result
        if status == GoalStatus.STATUS_CANCELED:
            self.say(f'stopped ({self.reason}), hovering')
        elif result.success:
            self.say('nothing in the way up to the end, hovering')
        else:
            self.say(f'flight ended: {result.message}')
        if self.land:
            self.send('land', Land.Goal(), lambda handle: self.say(
                'landing' if handle else 'landing refused'))


def main(args=None):
    rclpy.init(args=args)
    node = ForwardFlight()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RCLError:
        # Ctrl-C can shut the context down inside a callback; not a crash then.
        if rclpy.ok():
            raise
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
