"""Pico main.py'nin Wi-Fi baglanma mantigini sahte modullerle sinar (MicroPython gerekmez)."""
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = []
CLOCK = [0]


class FakePin:
    OUT = IN = 0

    def __init__(self, n, mode=None, value=0):
        self.n, self.v = n, value

    def value(self, v=None):
        if v is None:
            return self.v
        self.v = int(bool(v))
        if self.n == 22:
            LOG.append(('stby', self.v))


class FakePWM:
    def __init__(self, pin):
        pass

    def freq(self, f):
        pass

    def duty_u16(self, d):
        LOG.append(('duty', d))


class FakeADC:
    def __init__(self, pin):
        pass


class FakeWLAN:
    STA_IF = 0
    connects = 0
    succeed_on = 2          # kacinci connect() denemesinde baglansin

    def __init__(self, iface):
        self.up = False

    def active(self, a):
        pass

    def connect(self, ssid, pw):
        FakeWLAN.connects += 1
        LOG.append(('connect', FakeWLAN.connects))
        self.up = FakeWLAN.connects >= FakeWLAN.succeed_on

    def isconnected(self):
        return self.up

    def status(self):
        return -2

    def disconnect(self):
        LOG.append(('disconnect',))

    def ifconfig(self):
        return ('192.168.1.51',)


sys.modules['machine'] = types.SimpleNamespace(Pin=FakePin, PWM=FakePWM, ADC=FakeADC, I2C=object)
sys.modules['network'] = types.SimpleNamespace(WLAN=FakeWLAN, STA_IF=0)
sys.modules['secrets'] = types.SimpleNamespace(WIFI_SSID='x', WIFI_PASSWORD='y')
sys.modules['tof'] = types.SimpleNamespace(read_ranges_m=lambda: [4, 4, 4], setup_tof=lambda *a, **k: None)
time.ticks_ms = lambda: CLOCK[0]
time.ticks_diff = lambda a, b: a - b
time.ticks_add = lambda a, b: a + b
time.sleep = lambda s: CLOCK.__setitem__(0, CLOCK[0] + int(s * 1000))
sys.path.insert(0, str(ROOT / 'firmware' / 'pico2w'))
import main  # noqa: E402


def test_motors_stay_off_until_connected_and_retry_after_timeout():
    LOG.clear()
    CLOCK[0] = 0
    FakeWLAN.connects, FakeWLAN.succeed_on = 0, 2
    main.connect_wifi()
    assert FakeWLAN.connects == 2                       # ilk deneme zaman asimina ugradi
    assert ('disconnect',) in LOG
    assert LOG[0] == ('stby', 0)                        # baglanmadan once surucu kapatildi
    assert ('stby', 1) not in LOG                       # hic surulmedi
    assert CLOCK[0] > main.WIFI_TIMEOUT_S * 1000        # gercekten zaman asimi bekledi


def test_immediate_connection():
    LOG.clear()
    CLOCK[0] = 0
    FakeWLAN.connects, FakeWLAN.succeed_on = 0, 1
    main.connect_wifi()
    assert FakeWLAN.connects == 1 and ('disconnect',) not in LOG


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
