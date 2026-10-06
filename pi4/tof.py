"""Pi 4 icin 3 adet VL53L1X (TOF400C): ayni I2C hattinda farkli adres + okuma.

Sensorlerin hepsi acilista 0x29 adresindedir. Bu yuzden her birinin XSHUT pini ayri bir
GPIO'ya baglanir: once hepsi kapatilir, sonra tek tek acilip kendi adresini alir.
(Pico'daki firmware/pico2w/tof.py ile ayni fikir.)

Kutuphane: adafruit-circuitpython-vl53l1x (+ Adafruit-Blinka)
    pip install adafruit-circuitpython-vl53l1x
DURUM: Gercek sensorlerle henuz denenmedi. tests/test_pi4_tof.py sahte sensorlerle sirayi sinar.
"""
import time

ADDRESSES = (0x30, 0x31, 0x32)   # sol, orta, sag
BOOT_WAIT_S = 0.01               # XSHUT acildiktan sonra sensorun uyanmasi icin bekleme
LONG_MODE = 2                    # 1 = kisa (~1,3 m), 2 = uzun (~3,6 m); robot 4 m'ye kadar bakar


def _real_i2c():
    import board
    import busio
    return busio.I2C(board.SCL, board.SDA)


def _real_xshut(pin):
    from gpiozero import DigitalOutputDevice
    return DigitalOutputDevice(pin, initial_value=False)


def _real_sensor(i2c, address=0x29):
    import adafruit_vl53l1x
    return adafruit_vl53l1x.VL53L1X(i2c, address=address)


class ToFArray:
    """Sira: sol, orta, sag. Test icin i2c / xshut / sensor fabrikalari disaridan verilebilir."""

    def __init__(self, xshut_pins, addresses=ADDRESSES, i2c=None,
                 make_xshut=_real_xshut, make_sensor=_real_sensor, sleep=time.sleep):
        self.i2c = i2c if i2c is not None else _real_i2c()
        self.xshut = [make_xshut(p) for p in xshut_pins]     # hepsi kapali basliyor
        for pin in self.xshut:
            pin.off()
        sleep(BOOT_WAIT_S)
        self.sensors = []
        for pin, addr in zip(self.xshut, addresses):
            pin.on()                                          # sirayla ac
            sleep(BOOT_WAIT_S)
            s = make_sensor(self.i2c, 0x29)                   # yeni acilan sensor 0x29'da
            s.set_address(addr)                               # kendi adresini ver
            s.distance_mode = LONG_MODE
            s.start_ranging()
            self.sensors.append(s)
        self.last = [None] * len(self.sensors)

    def read(self):
        """Mesafeler (metre). Gecerli olcum yoksa o sensor icin None.

        Yeni veri hazir degilse son gecerli olcum tekrar verilir (VL53L1X ~20 Hz olcer).
        """
        out = []
        for i, s in enumerate(self.sensors):
            try:
                if s.data_ready:
                    cm = s.distance                 # cm; gecersizse None
                    s.clear_interrupt()
                    self.last[i] = None if cm is None else cm / 100.0
            except OSError:
                self.last[i] = None                 # I2C hatasi: olcum yok say
            out.append(self.last[i])
        return out

    def close(self):
        for s in self.sensors:
            try:
                s.stop_ranging()
            except OSError:
                pass
        for pin in self.xshut:
            pin.off()
