"""3 adet VL53L1X'i tek I2C hattinda kullanmak icin ince sarmalayici.

Kutuphane: drakxtwo/vl53l1x_pico (MIT) -> vl53l1x.py dosyasi Pico'ya kopyalanir:
    https://github.com/drakxtwo/vl53l1x_pico
Bu kutuphanede `VL53L1X(i2c, address=0x29)` ve `read()` (mm) var ama adres degistirme YOK.
O yuzden adresi burada, sensorun 0x0001 yazmacina yazarak biz veriyoruz.
Her sensor ayri XSHUT pinine bagli: once hepsi kapatilir, sonra tek tek acilip adres alir.
Kutuphane baslangic ayarinda olcumu kendisi baslatir (0x87 = 0x40), ayri bir start gerekmez.

DURUM: Gercek sensorle henuz denenmedi. tests/test_pico_tof.py sahte modullerle sirayi sinar.
"""
from machine import Pin
from time import sleep_ms
from vl53l1x import VL53L1X

ADDRESSES = (0x30, 0x31, 0x32)   # sol, orta, sag
I2C_ADDRESS_REG = 0x0001         # sensorun I2C adresi yazmaci
RANGE_RESULT_REG = 0x0089        # olcum sonucu blogu (17 bayt)
RANGE_VALID = 9                  # durum kodu 9 = gecerli olcum
_sensors = []


def setup_tof(i2c, xshut_pins):
    pins = [Pin(p, Pin.OUT, value=0) for p in xshut_pins]   # hepsi kapali basla
    sleep_ms(10)
    for pin, addr in zip(pins, ADDRESSES):
        pin.value(1)                    # sirayla ac
        sleep_ms(10)
        s = VL53L1X(i2c)                # yeni acilan sensor 0x29'da
        s.writeReg(I2C_ADDRESS_REG, addr)
        s.address = addr                # kutuphane bundan sonra yeni adrese konussun
        _sensors.append(s)


def read_ranges_m():
    """Sol, orta, sag mesafe (metre). Gecersiz okuma ya da I2C hatasi: 4.0 (bos)."""
    out = []
    for s in _sensors:
        try:
            data = s.i2c.readfrom_mem(s.address, RANGE_RESULT_REG, 17, addrsize=16)
            status = data[0] & 0x1F
            mm = (data[13] << 8) + data[14]
            out.append(min(max(mm / 1000.0, 0.04), 4.0) if status == RANGE_VALID else 4.0)
        except OSError:
            out.append(4.0)
    return out
