"""Gazebo'da egitilmis politikayi 6 sn (simulasyon zamani) calistirir, ustten kamerayi kaydeder.

Kullanim: python3 tools/capture_gazebo/record_gz.py docs/media/gazebo   (-> .png ve .mp4)
Once Gazebo kayit modunda acik olmali: bkz. tools/capture_gazebo/run.sh
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, Range

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pai_robot import Policy  # noqa: E402

OUT = sys.argv[1]
SECONDS = 6.0
TOPICS = ('/tof_left/range', '/tof_center/range', '/tof_right/range')


class Rec(Node):
    def __init__(self):
        super().__init__('record_gz', parameter_overrides=[rclpy.parameter.Parameter('use_sim_time', value=True)])
        self.policy = Policy.load(str(ROOT / 'docs' / 'data' / 'policy_latest.json'))
        self.ranges = [None] * 3
        for i, t in enumerate(TOPICS):
            self.create_subscription(Range, t, lambda m, i=i: self.ranges.__setitem__(i, float(m.range)), qos_profile_sensor_data)
        self.create_subscription(Image, '/overhead/image', self.on_image, qos_profile_sensor_data)
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.t0 = None
        self.frames = []
        self.done = False
        self.create_timer(0.05, self.tick)

    def now(self):
        return self.get_clock().now().nanoseconds / 1e9

    def on_image(self, m):
        if self.t0 is not None and not self.done:
            a = np.frombuffer(bytes(m.data), np.uint8).reshape(m.height, m.width, 3)
            # kamera x yukari, y sola bakiyor: 90 derece saat yonunde cevir (x saga, y yukari) ve kenar bosluklarini kirp
            self.frames.append(np.ascontiguousarray(np.rot90(a, k=-1)[60:580, 60:580]))

    def tick(self):
        if None in self.ranges or self.done:
            return
        if self.t0 is None:
            self.t0 = self.now()
            self.get_logger().info('politika basladi')
        if self.now() - self.t0 >= SECONDS:
            self.pub.publish(Twist())
            self.done = True
            return
        v, w = self.policy.command(self.ranges)
        msg = Twist()
        msg.linear.x, msg.angular.z = float(v), float(w)
        self.pub.publish(msg)


rclpy.init()
n = Rec()
while rclpy.ok() and not n.done:
    rclpy.spin_once(n, timeout_sec=0.1)
print('kare sayisi', len(n.frames))
h, w, _ = n.frames[0].shape
fps = len(n.frames) / SECONDS
print('etkin fps', round(fps, 1))
import PIL.Image as PI  # noqa: E402
PI.fromarray(n.frames[len(n.frames) // 2]).save(OUT + '.png')
ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}',
                       '-r', '20', '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '24',
                       '-movflags', '+faststart', OUT + '.mp4'], stdin=subprocess.PIPE)
for f in n.frames:
    ff.stdin.write(f.tobytes())
ff.stdin.close()
ff.wait()
n.destroy_node()
rclpy.shutdown()
