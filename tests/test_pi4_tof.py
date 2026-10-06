"""Pi 4 ToF surucusunun sirasini sahte sensor ve pinlerle sinar (donanim gerekmez)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'pi4'))

from tof import ToFArray  # noqa: E402

LOG = []


class FakePin:
    def __init__(self, n):
        self.n = n

    def on(self):
        LOG.append(('on', self.n))

    def off(self):
        LOG.append(('off', self.n))


class FakeSensor:
    def __init__(self, addr):
        self.addr, self.cm, self.ready = addr, 100.0, True
        self.distance_mode = None
        self.ranging = False
        self.fail = False

    def set_address(self, a):
        LOG.append(('set_address', self.addr, a))
        self.addr = a

    def start_ranging(self):
        self.ranging = True

    def stop_ranging(self):
        self.ranging = False

    @property
    def data_ready(self):
        if self.fail:
            raise OSError
        return self.ready

    @property
    def distance(self):
        return self.cm

    def clear_interrupt(self):
        pass


def build():
    LOG.clear()
    made = []

    def make_sensor(i2c, addr):
        LOG.append(('make_sensor', addr))
        s = FakeSensor(addr)
        made.append(s)
        return s
    arr = ToFArray((5, 6, 13), i2c=object(), make_xshut=FakePin, make_sensor=make_sensor,
                   sleep=lambda s: None)
    return arr, made


def test_xshut_sequence_and_addresses():
    arr, made = build()
    # once hepsi kapali, sonra her sensor: ac -> 0x29'da olustur -> adres ata
    assert LOG[:3] == [('off', 5), ('off', 6), ('off', 13)]
    assert LOG[3:] == [('on', 5), ('make_sensor', 0x29), ('set_address', 0x29, 0x30),
                       ('on', 6), ('make_sensor', 0x29), ('set_address', 0x29, 0x31),
                       ('on', 13), ('make_sensor', 0x29), ('set_address', 0x29, 0x32)]
    assert [s.addr for s in made] == [0x30, 0x31, 0x32]
    assert all(s.ranging and s.distance_mode == 2 for s in made)


def test_read_converts_cm_to_m_and_handles_invalid():
    arr, made = build()
    made[0].cm, made[1].cm, made[2].cm = 25.0, None, 400.0
    assert arr.read() == [0.25, None, 4.0]


def test_not_ready_keeps_last_and_i2c_error_gives_none():
    arr, made = build()
    arr.read()
    made[0].ready = False
    made[0].cm = 50.0                    # hazir degil: eski deger (1.0) kalmali
    made[1].fail = True                  # I2C hatasi: None
    r = arr.read()
    assert r[0] == 1.0 and r[1] is None and r[2] == 1.0


def test_close_stops_and_disables():
    arr, made = build()
    arr.close()
    assert not any(s.ranging for s in made)
    assert LOG[-3:] == [('off', 5), ('off', 6), ('off', 13)]


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
