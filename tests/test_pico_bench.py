"""Pico bench_test.py'yi sahte machine modulu ile sinar (MicroPython gerekmez)."""
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = []
IRQS = {}


class FakePin:
    OUT, IN, PULL_UP, IRQ_RISING = 1, 0, 2, 4

    def __init__(self, n, mode=None, pull=None, value=None):
        self.n = n
        if value is not None:
            LOG.append(('pin', n, value))

    def value(self, v=None):
        if v is None:
            return 0
        LOG.append(('value', self.n, int(v)))

    def irq(self, trigger=None, handler=None):
        IRQS[self.n] = handler


class FakePWM:
    def __init__(self, pin):
        self.pin = pin.n

    def freq(self, f):
        pass

    def duty_u16(self, d):
        LOG.append(('duty', self.pin, d))


class FakeI2C:
    def __init__(self, *a, **k):
        pass

    def scan(self):
        return [0x29]


class FakeADC:
    def __init__(self, pin):
        pass

    def read_u16(self):
        return 32768


sys.modules['machine'] = types.SimpleNamespace(Pin=FakePin, PWM=FakePWM, I2C=FakeI2C, ADC=FakeADC)
time.sleep_ms = lambda ms: None
time.ticks_ms = lambda: 0
time.ticks_add = lambda a, b: a + b
time.ticks_diff = lambda a, b: a - b
sys.path.insert(0, str(ROOT / 'firmware' / 'pico2w'))
import bench_test as b  # noqa: E402

time.sleep = lambda s: LOG.append(('sleep', s))


def test_drive_starts_stops_and_clamps():
    LOG.clear()
    b.motor('sol', guc=0.9, saniye=10)                       # sinirlar: %60, 3 sn
    duties = [d for k, p, d in (e for e in LOG if e[0] == 'duty')]
    assert duties[0] == int(0.60 * 65535) and duties[-1] == 0
    assert ('sleep', 3.0) in LOG
    pins = {e[1]: e[2] for e in LOG if e[0] == 'value'}
    assert pins[22] == 0                                      # sonunda STBY kapali
    assert ('value', 22, 1) in LOG                            # calisirken acik
    assert ('value', 17, 1) in LOG and ('value', 18, 0) in LOG   # sol motor ileri: AIN1=1, AIN2=0


def test_right_motor_reverse_and_error():
    LOG.clear()
    b.motor('sag', geri=True)
    assert ('value', 19, 0) in LOG and ('value', 20, 1) in LOG
    assert any(e[0] == 'duty' and e[1] == 21 for e in LOG)    # sag motor PWM = GP21
    try:
        b.motor('orta')
        assert False
    except ValueError:
        pass


def test_motor_stops_even_on_error():
    LOG.clear()
    real_sleep = time.sleep
    def boom(s):
        raise KeyboardInterrupt
    time.sleep = boom
    try:
        b.motor('sol')
    except KeyboardInterrupt:
        pass
    time.sleep = real_sleep
    assert [e for e in LOG if e[0] == 'duty'][-1][2] == 0 and ('value', 22, 0) in LOG


def test_encoder_counts_pulses():
    LOG.clear()
    IRQS.clear()
    def sleeper(s):                                           # beklerken tekerlek donuyormus gibi darbe uret
        for _ in range(5):
            IRQS[10](None)
        for _ in range(3):
            IRQS[12](None)
    old = time.sleep
    time.sleep = sleeper
    sayac = b.enkoder(1)
    time.sleep = old
    assert sayac == {'sol': 5, 'sag': 3}
    assert IRQS[10] is None and IRQS[12] is None              # kesmeler kapatildi


def test_scan_and_battery():
    assert b.tara() == [0x29]
    assert b.pil() == 32768


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
