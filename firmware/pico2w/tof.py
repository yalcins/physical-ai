"""3 adet VL53L1X'i tek I2C hattinda kullanmak icin ince sarmalayici.

Her sensor ayri XSHUT pinine bagli: once hepsini kapat, sonra tek tek ac ve
farkli I2C adresi ver. `VL53L1X` sinifi, kullandiginiz MicroPython kutuphanesine gore
uyarlanmalidir (burada: VL53L1X(i2c, address), .read() -> mm, .set_address(a)).
"""
from machine import Pin
from vl53l1x import VL53L1X     # kutuphane Pico'ya ayrica kopyalanir

ADDRESSES = (0x30, 0x31, 0x32)   # sol, orta, sag
_sensors = []


def setup_tof(i2c, xshut_pins):
    pins = [Pin(p, Pin.OUT) for p in xshut_pins]
    for p in pins:
        p.value(0)               # hepsini kapat
    for p, addr in zip(pins, ADDRESSES):
        p.value(1)               # sirayla ac, adres ata
        s = VL53L1X(i2c)
        s.set_address(addr)
        _sensors.append(s)


def read_ranges_m():
    """Sol, orta, sag mesafe (metre). Okuma basarisizsa 4.0 (bos) dondurulur."""
    out = []
    for s in _sensors:
        try:
            out.append(min(max(s.read() / 1000.0, 0.04), 4.0))
        except OSError:
            out.append(4.0)
    return out
