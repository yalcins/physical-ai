"""Pico tof.py'yi sahte machine / vl53l1x modulleriyle sinar (MicroPython gerekmez)."""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = []


class FakePin:
    OUT = 1

    def __init__(self, n, mode=None, value=None):
        self.n = n
        LOG.append(('pin', n, value))

    def value(self, v):
        LOG.append(('value', self.n, v))


class FakeI2C:
    def __init__(self):
        self.mem = {}      # (adres, yazmac) -> 17 baytlik blok

    def readfrom_mem(self, addr, reg, n, addrsize=8):
        if (addr, reg) not in self.mem:
            raise OSError
        return self.mem[(addr, reg)]


class FakeVL53L1X:
    def __init__(self, i2c, address=0x29):
        self.i2c, self.address = i2c, address
        LOG.append(('init', address))

    def writeReg(self, reg, value):
        LOG.append(('writeReg', self.address, reg, value))


sys.modules['machine'] = types.SimpleNamespace(Pin=FakePin)
sys.modules['vl53l1x'] = types.SimpleNamespace(VL53L1X=FakeVL53L1X)
sys.modules['time'].sleep_ms = lambda ms: None   # MicroPython'a ozgu
sys.path.insert(0, str(ROOT / 'firmware' / 'pico2w'))
import tof  # noqa: E402


def block(status, mm):
    b = bytearray(17)
    b[0], b[13], b[14] = status, mm >> 8, mm & 0xFF
    return bytes(b)


def test_setup_sequence():
    LOG.clear()
    tof._sensors.clear()
    tof.setup_tof(FakeI2C(), (6, 7, 8))
    assert LOG[:3] == [('pin', 6, 0), ('pin', 7, 0), ('pin', 8, 0)]
    assert LOG[3:] == [('value', 6, 1), ('init', 0x29), ('writeReg', 0x29, 1, 0x30),
                       ('value', 7, 1), ('init', 0x29), ('writeReg', 0x29, 1, 0x31),
                       ('value', 8, 1), ('init', 0x29), ('writeReg', 0x29, 1, 0x32)]
    assert [s.address for s in tof._sensors] == [0x30, 0x31, 0x32]


def test_read_ranges():
    LOG.clear()
    tof._sensors.clear()
    i2c = FakeI2C()
    tof.setup_tof(i2c, (6, 7, 8))
    i2c.mem[(0x30, 0x0089)] = block(9, 250)      # gecerli, 25 cm
    i2c.mem[(0x31, 0x0089)] = block(4, 900)      # gecersiz durum -> bos
    # 0x32 icin kayit yok -> OSError -> bos
    assert tof.read_ranges_m() == [0.25, 4.0, 4.0]
    i2c.mem[(0x30, 0x0089)] = block(9 | 0x80, 30)  # ust bitler maskelenmeli; 3 cm -> 4 cm'e kirpilir
    assert tof.read_ranges_m()[0] == 0.04


if __name__ == '__main__':
    import time
    time.sleep_ms = lambda ms: None
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
