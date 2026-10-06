"""RosRobot: ROS 2 konulari uzerinden Gazebo ikizini veya Pi 4 robotunu surer.

Konular CLAUDE.md'deki ortak arayuzle ayni: /cmd_vel, /tof_left|center|right/range.
Not: ROS 2 Jazzy ortami gerekir (.venv degil); bu dosya henuz bir ROS ortaminda denenmedi.
"""
import time

from .base import Robot

TOPICS = ('/tof_left/range', '/tof_center/range', '/tof_right/range')


class RosRobot(Robot):
    def __init__(self, node_name='pai_robot'):
        import rclpy
        from geometry_msgs.msg import Twist
        from sensor_msgs.msg import Range
        self._rclpy, self._Twist = rclpy, Twist
        rclpy.init()
        self.node = rclpy.create_node(node_name)
        self.pub = self.node.create_publisher(Twist, '/cmd_vel', 10)
        self.ranges = [4.0] * len(TOPICS)
        for i, topic in enumerate(TOPICS):
            self.node.create_subscription(Range, topic, lambda m, i=i: self._on_range(i, m), 10)
        self.n_sensors = len(TOPICS)

    def _on_range(self, i, msg):
        self.ranges[i] = float(msg.range)

    def read_ranges(self):
        self._rclpy.spin_once(self.node, timeout_sec=0.0)
        return list(self.ranges)

    def drive(self, v, w):
        msg = self._Twist()
        msg.linear.x, msg.angular.z = float(v), float(w)
        self.pub.publish(msg)

    def wait(self, dt):
        end = time.time() + dt
        while time.time() < end:
            self._rclpy.spin_once(self.node, timeout_sec=0.01)

    def close(self):
        self.stop()
        self.node.destroy_node()
        self._rclpy.shutdown()
