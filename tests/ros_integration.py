"""ROS 2 + Gazebo entegrasyon testi (pencere acmaz). Gazebo'yu kendisi baslatir ve kapatir.

Calistir (ROS terminali, .venv AKTIF DEGIL; once colcon build yapilmis olmali):
    source /opt/ros/jazzy/setup.bash && source install/setup.bash
    python3 tests/ros_integration.py          # yaklasik 1-2 dakika

Denenenler:
  A  RosRobot arayuzu Gazebo'yu gercekten suruyor (ToF okuma, /cmd_vel, /odom)
  B  Gazebo ikizi ile Python simulatoru ayni hizi/donusu/ToF mesafesini veriyor
  C  pi4/run_policy.py ROS modunda politikayi calistirip SIGTERM ile temiz cikiyor
  D  pi4/pai_driver_node.py sahte donanimla: /cmd_vel -> motor, ToF -> Range, zaman asimi
"""
import json
import math
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'pai_gym')]

import numpy as np  # noqa: E402
import rclpy  # noqa: E402
from geometry_msgs.msg import Twist  # noqa: E402
from nav_msgs.msg import Odometry  # noqa: E402
from rclpy.node import Node  # noqa: E402
from rclpy.qos import qos_profile_sensor_data  # noqa: E402
from sensor_msgs.msg import Range  # noqa: E402

from pai_robot import Policy  # noqa: E402
from pai_robot.ros import RosRobot  # noqa: E402

RESULTS = []


T_START = time.time()


def check(name, ok, detail=''):
    RESULTS.append((name, ok))
    print(f'[{time.time() - T_START:5.0f}s] ' + ('OK   ' if ok else 'HATA ') + name + (f'  [{detail}]' if detail else ''), flush=True)


def kill_gazebo(proc):
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
    out = subprocess.run(['ps', '-eo', 'pid,comm'], capture_output=True, text=True).stdout
    for line in out.splitlines()[1:]:
        pid, comm = line.split(None, 1)
        if comm.strip() in ('ruby', 'gz', 'parameter_bridge', 'tof_range_node', 'moving_obstacl'):
            try:
                os.kill(int(pid), signal.SIGTERM)
            except ProcessLookupError:
                pass


class Probe(Node):
    """/odom ve ToF dinleyen yardimci dugum (simulasyon zamaniyla)."""

    def __init__(self):
        super().__init__('ros_test_probe', parameter_overrides=[rclpy.parameter.Parameter('use_sim_time', value=True)])
        self.odom = None
        self.ranges = {}
        self.create_subscription(Odometry, '/odom', lambda m: setattr(self, 'odom', m), qos_profile_sensor_data)
        for n in ('left', 'center', 'right'):
            self.create_subscription(Range, f'/tof_{n}/range', lambda m, n=n: self.ranges.__setitem__(n, m.range),
                                     qos_profile_sensor_data)

    def pose(self):
        o = self.odom.pose.pose
        q = o.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        return o.position.x, o.position.y, yaw


def pump(node, n=20):
    """Bekleyen tum mesajlari isle (odom 30 Hz; tek spin_once geride kalir)."""
    for _ in range(n):
        rclpy.spin_once(node, timeout_sec=0.0)


def spin_for(node, seconds):
    end = time.time() + seconds
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.02)


def wait_for(node, cond, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
        if cond():
            return True
    return False


def angle_diff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def test_gazebo():
    probe = Probe()
    robot = RosRobot('ros_test_robot')
    check('A1 ToF okumalari geliyor (3 sensor)', wait_for(probe, lambda: len(probe.ranges) == 3 and probe.odom is not None))
    r = robot.read_ranges()
    spin_for(robot.node, 0.5)
    r = robot.read_ranges()
    check('A2 RosRobot gercek ToF degerlerini aliyor (4,0 baslangic degeri degil)', len(r) == 3 and all(x < 3.99 for x in r), str(r))

    # --- B: ToF mesafesi, robot dogma noktasinda yerinde donerek sol duvara bakarken (x = -1 m) ---
    # Yerinde donmek konumu degistirmez; bu yuzden dunya konumu = dogma noktasi, yon = /odom yonu + dogma yonu.
    SPAWN = (-0.6, -0.6, 0.785)               # sim.launch.py'deki dogma noktasi; /odom bu noktadan baslar
    target = math.pi
    for _ in range(600):
        pump(probe)
        _, _, oyaw = probe.pose()
        err = angle_diff(target, oyaw + SPAWN[2])
        if abs(err) < 0.03:
            break
        robot.drive(0.0, max(-1.5, min(1.5, 3.0 * err)))
        robot.wait(0.05)
        rclpy.spin_once(probe, timeout_sec=0.0)
    robot.stop()
    spin_for(probe, 1.5)
    ox, oy, oyaw = probe.pose()
    yaw = oyaw + SPAWN[2]
    c, s_ = math.cos(SPAWN[2]), math.sin(SPAWN[2])
    wx, wy = SPAWN[0] + c * ox - s_ * oy, SPAWN[1] + s_ * ox + c * oy     # /odom kaymasini da hesaba kat
    from pai_gym.world import World
    w = World(obstacles=[], sensor_noise=False)
    w.place_robot(wx, wy, yaw)
    py_center = w.read_tof()[1]
    samples = []
    for _ in range(15):
        spin_for(probe, 0.1)
        samples.append(probe.ranges['center'])
    gz_center = float(np.median(samples))
    check('B3a robot sol duvara dondu (yon 180 +-10 derece)', abs(angle_diff(yaw, math.pi)) < math.radians(10), f'{math.degrees(yaw):.0f} derece')
    check('B3 ToF orta sensor duvarda: Gazebo ~ Python (+-5 cm)', abs(gz_center - py_center) < 0.05,
          f'Gazebo {gz_center:.3f} m, Python {py_center:.3f} m (yon {math.degrees(yaw):.0f} derece, odom kaymasi {math.hypot(ox, oy) * 100:.1f} cm)')

    # --- A/B: duz gitme ---
    spin_for(probe, 0.5)
    x0, y0, _ = probe.pose()
    t0 = probe.get_clock().now().nanoseconds / 1e9
    for _ in range(400):                      # ~2 sn simulasyon zamani; komut her adimda yenilenir (politika dongusu gibi)
        robot.drive(0.2, 0.0)
        robot.wait(0.05)
        rclpy.spin_once(probe, timeout_sec=0.0)
        if probe.get_clock().now().nanoseconds / 1e9 - t0 >= 2.0:
            break
    robot.stop()
    spin_for(probe, 0.5)
    x1, y1, _ = probe.pose()
    dt = 2.0
    dist = math.hypot(x1 - x0, y1 - y0)
    check('A3 /cmd_vel robotu hareket ettiriyor', dist > 0.1, f'{dist:.2f} m')
    expected = 0.2 * 2.0
    check('B1 duz gitme: Gazebo ~ Python (0,2 m/s, 2 sn)', abs(dist - expected) / expected < 0.2,
          f'Gazebo {dist:.3f} m, Python {expected:.3f} m, gecen sim zamani {dt:.2f} sn')

    # --- B: yerinde donme (2,5 rad/s, 1,5 sn) ---
    _, _, yaw0 = probe.pose()
    t0 = probe.get_clock().now().nanoseconds / 1e9
    wall_end = time.time() + 20                # saat takilirsa testin sonsuza dek beklememesi icin
    while probe.get_clock().now().nanoseconds / 1e9 - t0 < 1.5 and time.time() < wall_end:
        robot.drive(0.0, 2.5)
        robot.wait(0.05)
        rclpy.spin_once(probe, timeout_sec=0.0)
    robot.stop()
    spin_for(probe, 0.5)
    _, _, yaw1 = probe.pose()
    turned = angle_diff(yaw1, yaw0)
    expected = 2.5 * 1.5
    check('B2 donme: Gazebo ~ Python (2,5 rad/s, 1,5 sn)', abs(angle_diff(turned, expected)) < 0.35,
          f'Gazebo {turned:.2f} rad (-pi..pi), Python {angle_diff(expected, 0.0):.2f} rad (3,75 sarilmis)')

    # --- C: run_policy ROS modunda ---
    x0, y0, _ = probe.pose()
    p = subprocess.Popen([sys.executable, str(ROOT / 'pi4' / 'run_policy.py'), '--policy',
                          str(ROOT / 'docs' / 'data' / 'policy_latest.json'), '--seconds', '0'],
                         cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    spin_for(probe, 8.0)
    x1, y1, _ = probe.pose()
    moved = math.hypot(x1 - x0, y1 - y0)
    check('C1 run_policy.py (ROS) robotu surdu', moved > 0.3, f'{moved:.2f} m')
    p.send_signal(signal.SIGTERM)
    try:
        code = p.wait(timeout=8)
    except subprocess.TimeoutExpired:
        p.kill()
        code = None
    check('C2 SIGTERM ile temiz cikis (kod 0)', code == 0, f'cikis kodu {code}')
    spin_for(probe, 1.0)
    xa, ya, _ = probe.pose()
    spin_for(probe, 1.0)
    xb, yb, _ = probe.pose()
    check('C3 cikistan sonra robot duruyor', math.hypot(xb - xa, yb - ya) < 0.02, f'{math.hypot(xb - xa, yb - ya):.3f} m/sn')
    robot.close()
    probe.destroy_node()


# ---------------- D: surucu dugumu, sahte donanimla ----------------
FAKE_DRIVER = '''
import json, sys, types
LOG = open(sys.argv[1], 'a', buffering=1)
class Dev:
    def __init__(self, pin, **kw):
        self.__dict__['pin'] = pin
        self.__dict__['v'] = kw.get('initial_value', 0)
    def __setattr__(self, k, v):
        if k == 'value':
            self.__dict__['v'] = v
            LOG.write(json.dumps([self.__dict__['pin'], v]) + chr(10))
    value = property(lambda self: self.__dict__['v'])
    def off(self): pass
gz = types.SimpleNamespace(DigitalOutputDevice=Dev, PWMOutputDevice=Dev)
sys.modules['gpiozero'] = gz
class FakeToF:
    def __init__(self, pins): self.pins = pins
    def read(self): return [0.50, None, 6.0]       # gecerli, gecersiz (None), menzil disi
    def close(self): LOG.write(json.dumps(['tof_closed']) + chr(10))
sys.modules['tof'] = types.SimpleNamespace(ToFArray=FakeToF)
sys.path.insert(0, sys.argv[2])
import pai_driver_node as d
d.PINS = {k: i + 1 for i, k in enumerate(d.PINS)}
d.XSHUT_PINS = (21, 22, 23)
d.main()
'''


def test_driver():
    env = dict(os.environ, ROS_DOMAIN_ID='77')          # Gazebo'dan ayri alan (konular karismasin)
    with tempfile.TemporaryDirectory() as d:
        log = Path(d) / 'motor.log'
        script = Path(d) / 'fake_driver.py'
        script.write_text(FAKE_DRIVER)
        proc = subprocess.Popen([sys.executable, str(script), str(log), str(ROOT / 'pi4')], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        os.environ['ROS_DOMAIN_ID'] = '77'
        rclpy.shutdown()
        rclpy.init()
        n = Node('driver_probe')
        got = {}
        for name in ('left', 'center', 'right'):
            n.create_subscription(Range, f'/tof_{name}/range', lambda m, name=name: got.__setitem__(name, m), qos_profile_sensor_data)
        pub = n.create_publisher(Twist, '/cmd_vel', 10)
        ok = wait_for(n, lambda: len(got) == 3, timeout=15)
        check('D1 surucu 3 ToF konusunu yayinliyor', ok)
        if ok:
            c, i, r = got['left'], got['center'], got['right']
            check('D2 Range: gecerli deger, gecersiz +inf, menzil disi +inf',
                  abs(c.range - 0.5) < 1e-6 and math.isinf(i.range) and i.range > 0 and math.isinf(r.range) and r.range > 0,
                  f'{c.range}, {i.range}, {r.range}')
            check('D3 Range alanlari (frame, fov, min/max)',
                  c.header.frame_id == 'tof_left' and abs(c.field_of_view - math.radians(27)) < 1e-6
                  and abs(c.min_range - 0.04) < 1e-6 and abs(c.max_range - 4.0) < 1e-6)
        # komut gonder: ileri
        msg = Twist()
        msg.linear.x = 0.2
        end = time.time() + 1.0
        while time.time() < end:
            pub.publish(msg)
            spin_for(n, 0.05)
        lines = [json.loads(l) for l in log.read_text().splitlines()]
        check('D4 /cmd_vel motor PWM degerlerine yansiyor', any(v > 0 for pin, v in (l for l in lines if len(l) == 2)))
        # komut kesilince 0,5 sn icinde duruyor mu?
        spin_for(n, 1.0)
        lines = [json.loads(l) for l in log.read_text().splitlines() if l.startswith('[')]
        pwms = [(i, l) for i, l in enumerate(lines) if len(l) == 2 and isinstance(l[1], float)]
        last_pwm_values = {}
        for _, (pin, v) in pwms:
            last_pwm_values[pin] = v
        check('D5 komut kesilince PWM sifirlandi (zaman asimi)', all(v == 0.0 for v in last_pwm_values.values()) and last_pwm_values,
              str(last_pwm_values))
        # SIGTERM: temiz cikis, motorlar kapali, ToF kapatildi
        proc.send_signal(signal.SIGTERM)
        try:
            code = proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
            code = None
        text = log.read_text()
        check('D6 SIGTERM ile temiz cikis, ToF kapatildi', code == 0 and 'tof_closed' in text, f'cikis kodu {code}')
        n.destroy_node()


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    rclpy.init()
    if which in ('all', 'gazebo'):
        env = dict(os.environ, CAPTURE_WORLD=str(ROOT / 'src/arena_sim/worlds/arena.sdf'),
                   CAPTURE_NO_MOVING='1')          # ToF olcumu, hareketli engelin onune girmesinden etkilenmesin
        gz = subprocess.Popen(['ros2', 'launch', str(ROOT / 'tools/capture_gazebo/capture.launch.py')], env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
        try:
            time.sleep(20)
            test_gazebo()
        finally:
            kill_gazebo(gz)
    if which in ('all', 'driver'):
        test_driver()
    rclpy.shutdown()
    bad = [n for n, ok in RESULTS if not ok]
    print(f'\n{len(RESULTS) - len(bad)}/{len(RESULTS)} basarili' + (f'; BASARISIZ: {bad}' if bad else ''))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
