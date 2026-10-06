"""Pi 4 robot surucusu (TASLAK): /cmd_vel -> motorlar, ToF -> /tof_*/range.

Gazebo ikiziyle ayni konulari yayinlar; boylece pai_robot.RosRobot ikisinde de calisir.
DURUM: Pi 4 uzerinde henuz denenmedi, pin numaralari BELIRLENMEDI.
ToF okuma ve adres atama tof.py icinde (sahte sensorlerle test edildi, gercek sensorle degil).
PINS sozlugunu gercek kablolamaya gore doldur (Pico pin planindan farkli olabilir).
"""
import math
import signal

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Range

from tof import ToFArray

WHEEL_RADIUS = 0.0215
WHEEL_SEPARATION = 0.115
MAX_WHEEL_RAD_S = 31.0
CMD_TIMEOUT = 0.5                    # sn: komut kesilirse dur

# TB6612FNG BCM pinleri -- DOLDURULACAK (None = henuz atanmadi)
PINS = {'pwma': None, 'ain1': None, 'ain2': None,
        'pwmb': None, 'bin1': None, 'bin2': None, 'stby': None}
# Her ToF'un XSHUT pini (I2C adres ataması için) -- DOLDURULACAK, sıra: sol, orta, sağ
XSHUT_PINS = (None, None, None)
TOF_NAMES = ('left', 'center', 'right')
TOF_FOV = math.radians(27)
TOF_MIN, TOF_MAX = 0.04, 4.0


class PaiDriver(Node):
    def __init__(self):
        super().__init__('pai_driver')
        if any(v is None for v in PINS.values()) or None in XSHUT_PINS:
            raise RuntimeError('PINS / XSHUT_PINS doldurulmadi: pi4/pai_driver_node.py icinde pinleri yaz.')
        from gpiozero import DigitalOutputDevice, PWMOutputDevice
        self.stby = DigitalOutputDevice(PINS['stby'], initial_value=True)
        self.left = (PWMOutputDevice(PINS['pwma']), DigitalOutputDevice(PINS['ain1']), DigitalOutputDevice(PINS['ain2']))
        self.right = (PWMOutputDevice(PINS['pwmb']), DigitalOutputDevice(PINS['bin1']), DigitalOutputDevice(PINS['bin2']))
        self.create_subscription(Twist, '/cmd_vel', self.on_cmd, 10)
        self.pubs = [self.create_publisher(Range, f'/tof_{n}/range', qos_profile_sensor_data) for n in TOF_NAMES]
        self.last_cmd = self.get_clock().now()
        self.create_timer(0.05, self.tick)      # 20 Hz: ToF oku + watchdog
        self.tof = ToFArray(XSHUT_PINS)       # adresleri atar (tof.py)

    def on_cmd(self, msg):
        self.last_cmd = self.get_clock().now()
        v, w = msg.linear.x, msg.angular.z
        self.set_motor(self.left, (v - w * WHEEL_SEPARATION / 2) / WHEEL_RADIUS)
        self.set_motor(self.right, (v + w * WHEEL_SEPARATION / 2) / WHEEL_RADIUS)

    @staticmethod
    def set_motor(motor, rad_s):
        pwm, in1, in2 = motor
        in1.value, in2.value = int(rad_s > 0), int(rad_s < 0)
        pwm.value = min(abs(rad_s) / MAX_WHEEL_RAD_S, 1.0)

    def publish_tof(self):
        """Sensor_msgs/Range, REP 117: menzil disi +inf, min'den yakin -inf (Gazebo ikiziyle ayni)."""
        now = self.get_clock().now().to_msg()
        for name, pub, r in zip(TOF_NAMES, self.pubs, self.tof.read()):
            msg = Range()
            msg.header.stamp = now
            msg.header.frame_id = f'tof_{name}'
            msg.radiation_type = Range.INFRARED
            msg.field_of_view = TOF_FOV
            msg.min_range, msg.max_range = TOF_MIN, TOF_MAX
            if r is None or r > TOF_MAX:
                msg.range = math.inf
            elif r < TOF_MIN:
                msg.range = -math.inf
            else:
                msg.range = r
            pub.publish(msg)

    def stop_motors(self):
        self.set_motor(self.left, 0.0)
        self.set_motor(self.right, 0.0)

    def tick(self):
        self.publish_tof()
        if (self.get_clock().now() - self.last_cmd).nanoseconds > CMD_TIMEOUT * 1e9:
            self.stop_motors()


def main():
    rclpy.init()
    signal.signal(signal.SIGTERM, signal.default_int_handler)   # run.sh stop: SIGTERM -> temiz cikis
    node = PaiDriver()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.stop_motors()                 # her cikista motorlar kapansin (run.sh stop SIGTERM yollar)
        node.tof.close()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
