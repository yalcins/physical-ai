"""Pi 4 robot surucusu (TASLAK): /cmd_vel -> motorlar, ToF -> /tof_*/range.

Gazebo ikiziyle ayni konulari yayinlar; boylece pai_robot.RosRobot ikisinde de calisir.
DURUM: Pi 4 uzerinde henuz denenmedi, pin numaralari BELIRLENMEDI.
PINS sozlugunu gercek kablolamaya gore doldur (Pico pin planindan farkli olabilir).
"""
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import Range

WHEEL_RADIUS = 0.0215
WHEEL_SEPARATION = 0.115
MAX_WHEEL_RAD_S = 31.0
CMD_TIMEOUT = 0.5                    # sn: komut kesilirse dur

# TB6612FNG BCM pinleri -- DOLDURULACAK (None = henuz atanmadi)
PINS = {'pwma': None, 'ain1': None, 'ain2': None,
        'pwmb': None, 'bin1': None, 'bin2': None, 'stby': None}
TOF_NAMES = ('left', 'center', 'right')


class PaiDriver(Node):
    def __init__(self):
        super().__init__('pai_driver')
        if any(v is None for v in PINS.values()):
            raise RuntimeError('PINS doldurulmadi: pi4/pai_driver_node.py icinde pinleri yaz.')
        from gpiozero import DigitalOutputDevice, PWMOutputDevice
        self.stby = DigitalOutputDevice(PINS['stby'], initial_value=True)
        self.left = (PWMOutputDevice(PINS['pwma']), DigitalOutputDevice(PINS['ain1']), DigitalOutputDevice(PINS['ain2']))
        self.right = (PWMOutputDevice(PINS['pwmb']), DigitalOutputDevice(PINS['bin1']), DigitalOutputDevice(PINS['bin2']))
        self.create_subscription(Twist, '/cmd_vel', self.on_cmd, 10)
        self.pubs = [self.create_publisher(Range, f'/tof_{n}/range', 10) for n in TOF_NAMES]
        self.last_cmd = self.get_clock().now()
        self.create_timer(0.05, self.tick)      # 20 Hz: ToF oku + watchdog
        # TODO: VL53L1X okuma (self.read_tof) -- kullanilan Python kutuphanesine gore yazilacak

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

    def tick(self):
        if (self.get_clock().now() - self.last_cmd).nanoseconds > CMD_TIMEOUT * 1e9:
            self.set_motor(self.left, 0.0)
            self.set_motor(self.right, 0.0)


def main():
    rclpy.init()
    rclpy.spin(PaiDriver())


if __name__ == '__main__':
    main()
