"""Gazebo'daki hareketli engelleri (moving_1, moving_2) gezdirir.

pai_gym/world.py'deki World.step() ile ayni mantik: engel sabit hizla gider,
arena duvarina degince seker. Boylece simulatordeki ve Gazebo'daki
"hareketli Pico robotlar" ayni davranir.

Not: hareket komutu Gazebo'ya /world/arena/set_pose_vector servisiyle gider.
"""
import rclpy
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.pose_v_pb2 import Pose_V
from gz.transport13 import Node as GzNode
from rclpy.node import Node

HALF = 1.0        # arena ic yarisi (m)
Z = 0.06          # silindir merkez yuksekligi (m)

# ad: [x, y, yaricap, vx, vy]  (world.py default_obstacles ile ayni)
ENGELLER = {
    'moving_1': [0.3, -0.4, 0.05, 0.08, 0.05],
    'moving_2': [-0.5, 0.0, 0.05, -0.05, 0.09],
}


class MovingObstacles(Node):

    def __init__(self):
        super().__init__('moving_obstacles_node')
        self.gz = GzNode()
        self.engeller = {ad: list(v) for ad, v in ENGELLER.items()}
        self.dt = 1.0 / 30.0
        # use_sim_time acik oldugu icin zamanlayici simulasyon saatiyle isler
        self.create_timer(self.dt, self.adim)
        self.get_logger().info('Hareketli engeller hazir: moving_1, moving_2')

    def adim(self):
        istek = Pose_V()
        for ad, e in self.engeller.items():
            e[0] += e[3] * self.dt
            e[1] += e[4] * self.dt
            # Duvara degince hizi ters cevir (sek)
            if abs(e[0]) > HALF - e[2]:
                e[3] = -e[3]
                e[0] = HALF - e[2] if e[0] > 0 else -(HALF - e[2])
            if abs(e[1]) > HALF - e[2]:
                e[4] = -e[4]
                e[1] = HALF - e[2] if e[1] > 0 else -(HALF - e[2])
            p = istek.pose.add()
            p.name = ad
            p.position.x, p.position.y, p.position.z = e[0], e[1], Z
            p.orientation.w = 1.0
        self.gz.request('/world/arena/set_pose_vector', istek, Pose_V, Boolean, 100)


def main():
    rclpy.init()
    node = MovingObstacles()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
