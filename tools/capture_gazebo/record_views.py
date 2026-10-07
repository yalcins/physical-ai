"""Gazebo kayitlari (pencere acmaz). Iki kip:

  python3 tools/capture_gazebo/record_views.py stills docs/media/sim
      Robot dogma noktasinda dururken: tum simulasyon (ust/on/yan) ve robot yakin cekim (ust/on/yan/capraz) PNG.
  python3 tools/capture_gazebo/record_views.py trial docs/media/sim
      Egitilmis politika robotu 6 sn (simulasyon zamani) surer; ust/on/yan kameralardan MP4 + ortadaki kare PNG.

Once Gazebo kayit modunda acik olmali: bkz. tools/capture_gazebo/run.sh
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from PIL import Image as PILImage
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, Range

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cameras import CAMS  # noqa: E402
from pai_robot import Policy  # noqa: E402

MODE, OUT = sys.argv[1], Path(sys.argv[2])
SECONDS = 6.0
TRIAL_CAMS = ('scene_top', 'scene_front', 'scene_side')
RANGES = ('/tof_left/range', '/tof_center/range', '/tof_right/range')


def fix(name, a):
    """Ust kamera x'i yukari, y'yi sola gosterir: saat yonunde cevir (x saga, y yukari) ve kenar bosluklarini kirp."""
    if name == 'scene_top':
        return np.ascontiguousarray(np.rot90(a, k=-1)[60:580, 60:580])
    return a


class Rec(Node):
    def __init__(self):
        super().__init__('record_views', parameter_overrides=[rclpy.parameter.Parameter('use_sim_time', value=True)])
        self.latest, self.frames, self.recording = {}, {n: [] for n in TRIAL_CAMS}, False
        self.ranges = [None] * 3
        for n in CAMS:
            self.create_subscription(Image, f'/cam_{n}/image', lambda m, n=n: self.on_image(n, m), qos_profile_sensor_data)
        for i, t in enumerate(RANGES):
            self.create_subscription(Range, t, lambda m, i=i: self.ranges.__setitem__(i, float(m.range)), qos_profile_sensor_data)
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.policy = Policy.load(str(ROOT / 'docs' / 'data' / 'policy_latest.json'))
        self.t0, self.done = None, False
        self.create_timer(0.05, self.tick)

    def now(self):
        return self.get_clock().now().nanoseconds / 1e9

    def on_image(self, name, m):
        a = np.frombuffer(bytes(m.data), np.uint8).reshape(m.height, m.width, 3)
        a = fix(name, a)
        self.latest[name] = a
        if self.recording and name in self.frames:
            self.frames[name].append((m.header.stamp.sec + m.header.stamp.nanosec / 1e9, a.copy()))

    def tick(self):
        if MODE != 'trial' or None in self.ranges or len(self.latest) < len(CAMS) or self.done:
            return
        if self.t0 is None:
            self.t0, self.recording = self.now(), True
            self.get_logger().info('deneme basladi')
        if self.now() - self.t0 >= SECONDS:
            self.pub.publish(Twist())
            self.recording, self.done = False, True
            return
        v, w = self.policy.command(self.ranges)
        msg = Twist()
        msg.linear.x, msg.angular.z = float(v), float(w)
        self.pub.publish(msg)


def save_png(a, path):
    PILImage.fromarray(a).save(path)


def save_mp4(frames, path):
    h, w, _ = frames[0].shape
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}',
                           '-r', '20', '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '24',
                           '-movflags', '+faststart', str(path)], stdin=subprocess.PIPE)
    for f in frames:
        ff.stdin.write(f.tobytes())
    ff.stdin.close()
    ff.wait()


rclpy.init()
n = Rec()
OUT.mkdir(parents=True, exist_ok=True)
import time  # noqa: E402
end = time.time() + 90
while rclpy.ok() and time.time() < end and len(n.latest) < len(CAMS):
    rclpy.spin_once(n, timeout_sec=0.1)
if len(n.latest) < len(CAMS):
    raise SystemExit(f'Kameralar gelmedi: {sorted(set(CAMS) - set(n.latest))}')

if MODE == 'stills':
    t_end = n.now() + 2.0                               # sahne otursun (2 sn simulasyon zamani)
    while n.now() < t_end and time.time() < end:
        rclpy.spin_once(n, timeout_sec=0.05)
    for name, a in n.latest.items():
        save_png(a, OUT / f'{name.replace("_", "-")}.png')
    print('png:', ', '.join(sorted(n.latest)))
elif MODE == 'trial':
    while rclpy.ok() and not n.done and time.time() < end + 60:
        rclpy.spin_once(n, timeout_sec=0.1)
    for name, stamped in n.frames.items():
        # Kameralar farkli hizda yayinliyor: 20 kare/sn'ye esitle (her 0,05 sn icin o ana kadarki son kare)
        t_start = stamped[0][0]
        frames, j = [], 0
        for k in range(int(SECONDS * 20)):
            while j + 1 < len(stamped) and stamped[j + 1][0] <= t_start + k * 0.05:
                j += 1
            frames.append(stamped[j][1])
        stem = 'trial-' + name.replace('scene_', '')
        save_mp4(frames, OUT / f'{stem}.mp4')
        save_png(frames[len(frames) // 2], OUT / f'{stem}.png')
        print(stem, len(frames), 'kare')
else:
    raise SystemExit('Kip: stills ya da trial')
n.destroy_node()
rclpy.shutdown()
