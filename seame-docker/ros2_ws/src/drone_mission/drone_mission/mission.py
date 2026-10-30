"""
mission: Takeoff, Goto and Land action servers, with height from the rangefinder.

The flight logic lives in logic.py; this node reads parameters, feeds it fc/range
and fc/odom, publishes its commands at rate_hz, and turns its goals into ROS
actions. One goal at a time; between goals in the air it holds height.
Times are the node clock, so with use_sim_time everything follows Gazebo.
"""
from dataclasses import fields
import math
import threading
import time

from drone_interfaces.action import Goto, Land, Takeoff
from drone_mission.logic import ACTIVE, CANCELED, LAND, Mission, Params, SUCCEEDED
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
import rclpy
from rclpy._rclpy_pybind11 import RCLError
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import Range
from std_msgs.msg import String
from std_srvs.srv import SetBool


class MissionNode(Node):
    def __init__(self):
        super().__init__('mission')
        rate = self.declare_parameter('rate_hz', 20.0).value
        self.disarm_after_land = self.declare_parameter('disarm_after_land', True).value
        defaults = Params()
        values = {f.name: self.declare_parameter(f.name, getattr(defaults, f.name)).value
                  for f in fields(Params)}
        self.mission = Mission(Params(**values))   # read once at start
        self.lock = threading.Lock()
        self.accepted = {}                         # id(goal request) -> (request, logic Goal)
        self.goals = {}                            # goal uuid -> logic Goal, while running
        group = ReentrantCallbackGroup()

        self.pub = self.create_publisher(TwistStamped, 'setpoint_velocity', 10)
        self.create_subscription(Range, 'fc/range', self.on_range, 10, callback_group=group)
        self.create_subscription(Odometry, 'fc/odom', self.on_odom, 10, callback_group=group)
        # Without a safety_manager nothing arrives here and the mission stays in control.
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(String, 'safety/active_source', self.on_active_source,
                                 latched, callback_group=group)
        self.arm = self.create_client(SetBool, 'fc/arm', callback_group=group)
        self.create_timer(1.0 / rate, self.tick, callback_group=group)
        self.logged = 0

        self.servers = []
        for name, kind, request in [('takeoff', Takeoff, self.request_takeoff),
                                    ('goto', Goto, self.request_goto),
                                    ('land', Land, self.request_land)]:
            self.servers.append(ActionServer(
                self, kind, f'mission/{name}', self.execute,
                goal_callback=lambda g, r=request, n=name: self.on_goal(n, r, g),
                cancel_callback=self.on_cancel, callback_group=group))
        self.get_logger().info('Ready: mission/takeoff, mission/goto, mission/land')

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    # Measurements

    def on_range(self, msg):
        with self.lock:
            self.mission.on_range(self.now(), msg.range, msg.max_range)

    def on_odom(self, msg):
        q = msg.pose.pose.orientation
        up_z = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        p = msg.pose.pose.position
        with self.lock:
            self.mission.on_odom(self.now(), p.x, p.y, yaw, msg.twist.twist.linear.z, up_z)

    def on_active_source(self, msg):
        with self.lock:
            self.mission.set_control(self.now(), msg.data in ('mission', 'none'), msg.data)

    # Goals

    def request_takeoff(self, goal):
        ok, why = self.mission.request_takeoff(self.now(), goal.height)
        if ok:
            self.set_armed(True)
        return ok, why

    def request_goto(self, goal):
        return self.mission.request_goto(self.now(), goal.forward, goal.left, goal.yaw,
                                         goal.speed)

    def request_land(self, goal):
        return self.mission.request_land(self.now())

    def on_goal(self, name, request, goal):
        with self.lock:
            ok, why = request(goal)
            if not ok:
                self.get_logger().warn(f'{name} rejected: {why}')
                return GoalResponse.REJECT
            # rclpy hands this same request object to execute(): the key survives a
            # Land arriving between another goal's acceptance and its execution.
            self.accepted[id(goal)] = (goal, self.mission.goal)
        self.get_logger().info(f'{name} accepted')
        return GoalResponse.ACCEPT

    def on_cancel(self, handle):
        with self.lock:
            g = self.goals.get(bytes(handle.goal_id.uuid))
            if g is not None and g.status == ACTIVE and self.mission.cancel(self.now()):
                return CancelResponse.ACCEPT
        return CancelResponse.REJECT

    def execute(self, handle):
        with self.lock:
            _, g = self.accepted.pop(id(handle.request))
            self.goals[bytes(handle.goal_id.uuid)] = g
        kind = type(handle.request)
        action = {Takeoff.Goal: Takeoff, Goto.Goal: Goto, Land.Goal: Land}[kind]
        while g.status == ACTIVE and rclpy.ok():
            fb = action.Feedback()
            for k, v in g.feedback.items():
                setattr(fb, k, float(v))
            handle.publish_feedback(fb)
            time.sleep(0.1)

        result = action.Result()
        if not rclpy.ok():
            return result       # shutting down: the handle may already be destroyed
        result.success = g.status == SUCCEEDED
        result.message = g.message or g.status
        for k, v in g.result.items():
            setattr(result, k, float(v))
        if g.status == SUCCEEDED:
            handle.succeed()
        elif g.status == CANCELED:
            handle.canceled()
        else:
            handle.abort()
        if g.kind == LAND and g.status == SUCCEEDED and self.disarm_after_land:
            self.set_armed(False)
        with self.lock:
            self.goals.pop(bytes(handle.goal_id.uuid), None)
        return result

    def set_armed(self, armed):
        if not self.arm.service_is_ready():
            self.get_logger().warn('fc/arm not available')
            return
        self.arm.call_async(SetBool.Request(data=armed))

    # Output

    def tick(self):
        with self.lock:
            t = self.now()
            cmd = self.mission.step(t)
            new = self.mission.transitions[self.logged:]
            self.logged = len(self.mission.transitions)
            h = self.mission.height(t)
        where = 'no range' if h is None else f'height {h:.2f} m'
        for _, old, state in new:
            self.get_logger().info(f'State: {old} -> {state} ({where})')
        if cmd is None:
            return   # on the ground: silence, so fc_bridge times out and holds

        out = TwistStamped()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = 'base_link'
        out.twist.linear.x = cmd.vx
        out.twist.linear.y = cmd.vy
        out.twist.linear.z = cmd.vz
        out.twist.angular.z = cmd.yaw_rate
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = MissionNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RCLError:
        # Ctrl-C: rclpy's handler shuts the context down while the multi-threaded
        # executor waits, and the next wait fails. rclpy's handler is kept anyway:
        # it wakes the executor even when nothing else does (no /clock, no messages).
        if rclpy.ok():
            raise
    finally:
        executor.shutdown(timeout_sec=2.0)   # running goals see rclpy.ok() go false
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
