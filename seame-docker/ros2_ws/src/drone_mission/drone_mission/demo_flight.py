"""
demo_flight: a scripted client of the mission action servers.

Takeoff, a square of side `side` (forward, then a quarter turn left, four
times), then Land. Each step waits for the previous one; after a rejected or
failed step it skips to Land. Stands in for whatever will plan real missions later.
"""
import math
import time

from drone_interfaces.action import Goto, Land, Takeoff
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node


class DemoFlight(Node):
    def __init__(self):
        super().__init__('demo_flight')
        self.height = self.declare_parameter('height', 1.2).value
        self.side = self.declare_parameter('side', 1.0).value
        self.actions = {name: ActionClient(self, kind, f'mission/{name}')
                        for name, kind in [('takeoff', Takeoff), ('goto', Goto),
                                           ('land', Land)]}

    def send(self, name, goal, retry_s=0.0):
        """Send a goal and wait for its result; retry a rejection for retry_s seconds."""
        client = self.actions[name]
        client.wait_for_server()
        deadline = time.monotonic() + retry_s
        while True:
            future = client.send_goal_async(goal)
            rclpy.spin_until_future_complete(self, future)
            handle = future.result()
            if handle.accepted:
                break
            if time.monotonic() >= deadline:
                self.get_logger().error(f'{name} rejected')
                return None
            time.sleep(1.0)
        future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, future)
        result = future.result().result
        self.get_logger().info(f'{name}: {"ok" if result.success else "FAILED"} '
                               f'({result.message})')
        return result if result.success else None

    def run(self):
        # The mission refuses Takeoff until the rangefinder is up: keep asking for 30 s.
        ok = self.send('takeoff', Takeoff.Goal(height=self.height), retry_s=30.0) is not None
        for i in range(4):
            ok = ok and self.send('goto', Goto.Goal(forward=self.side)) is not None
            ok = ok and self.send('goto', Goto.Goal(yaw=math.pi / 2)) is not None
            if not ok:
                break
        # Always: after a failed takeoff the drone may be off the ground. On the
        # ground the mission rejects it, which is fine.
        self.send('land', Land.Goal())
        self.get_logger().info('Demo done' if ok else 'Demo stopped early, landed')


def main(args=None):
    rclpy.init(args=args)
    node = DemoFlight()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
