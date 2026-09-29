"""Simulasyondaki dar lidar taramalarini gercek VL53L1X gibi tek bir mesafeye cevirir.

Gercek robotlar da ayni konulara (/tof_left/range, /tof_center/range,
/tof_right/range) sensor_msgs/Range yayinlayacak. Boylece ogrenme kodu
simulasyon ile gercek robot arasinda hic degismeden calisir.
"""
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan, Range

SENSORS = ('tof_left', 'tof_center', 'tof_right')


class TofRangeNode(Node):

    def __init__(self):
        super().__init__('tof_range_node')
        self.range_pubs = {}
        for name in SENSORS:
            self.range_pubs[name] = self.create_publisher(
                Range, f'/{name}/range', qos_profile_sensor_data)
            self.create_subscription(
                LaserScan, f'/{name}/scan',
                lambda msg, n=name: self.on_scan(n, msg),
                qos_profile_sensor_data)
        self.get_logger().info('ToF donusturucu hazir: /tof_*/scan -> /tof_*/range')

    def on_scan(self, name, scan):
        valid = [r for r in scan.ranges
                 if math.isfinite(r) and scan.range_min <= r <= scan.range_max]
        out = Range()
        out.header = scan.header
        out.radiation_type = Range.INFRARED
        out.field_of_view = scan.angle_max - scan.angle_min
        out.min_range = scan.range_min
        out.max_range = scan.range_max
        # REP 117: menzilde nesne yoksa +inf
        out.range = min(valid) if valid else math.inf
        self.range_pubs[name].publish(out)


def main():
    rclpy.init()
    node = TofRangeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
