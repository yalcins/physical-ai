"""Pico tezgâh testi (MicroPython): güç, motor, enkoder, ToF. main.py YÜKLEMEDEN, REPL'de çalıştır.

Kullanım (bilgisayarda):
    mpremote connect auto cp firmware/pico2w/bench_test.py :
    mpremote connect auto repl
REPL'de:
    import bench_test as b
    b.yardim()          # komutları listeler
    b.pil()             # ADC okuması (YALNIZCA GP26'da bölücü direnç varsa)
    b.tara()            # I2C taraması (ToF sensörleri 0x29'da görünmeli)
    b.motor('sol')      # sol motor ileri, 1,5 sn   (b.motor('sag', geri=True) ...)
    b.enkoder()         # tekerleği elle çevir, darbeler sayılır
    b.tof()             # üç ToF mesafesi (vl53l1x.py ve tof.py Pico'da olmalı)

GÜVENLİK: Tekerlekler yerden kesik olsun (robotu kutu üstüne koy). Motor testi en çok 3 sn ve %60 güç.
Pin planı main.py ve CLAUDE.md ile aynıdır. DURUM: Gerçek kartta henüz denenmedi.
"""
import time

from machine import ADC, I2C, PWM, Pin

SDA, SCL = 4, 5
XSHUT = (6, 7, 8)
ENC_SOL = (10, 11)           # A, B
ENC_SAG = (12, 13)
MOTORLAR = {                 # PWM, IN1, IN2
    'sol': (16, 17, 18),
    'sag': (21, 19, 20),
}
STBY_PIN = 22
PIL_ADC = 26
EN_FAZLA_SANIYE = 3.0
EN_FAZLA_GUC = 0.60

_stby = Pin(STBY_PIN, Pin.OUT, value=0)       # açılışta sürücü kapalı


def yardim():
    print('pil()  tara()  motor(taraf, guc=0.35, saniye=1.5, geri=False)  enkoder(saniye=5)  tof(saniye=5)')


def pil():
    """UYARI: GP26'ya pil gerilimini dogrudan baglama (4xAA 3,3 V'u asar); once bolucu direnc gerekir."""
    ham = ADC(Pin(PIL_ADC)).read_u16()
    volt = ham / 65535 * 3.3
    print('ADC ham:', ham, ' pin gerilimi: %.2f V' % volt)
    print('Not: pil gerilimi = pin gerilimi x bölücü oranı; oran montaja bağlı (main.py 3 varsayıyor).')
    return ham


def tara(xshut_acik=None):
    """I2C taraması. xshut_acik=(6,) gibi verilirse yalnızca o sensörün XSHUT pini açılır."""
    pins = [Pin(p, Pin.OUT, value=0) for p in XSHUT]
    for p, no in zip(pins, XSHUT):
        if xshut_acik is None or no in xshut_acik:
            p.value(1)
    time.sleep_ms(20)
    i2c = I2C(0, sda=Pin(SDA), scl=Pin(SCL))
    adresler = i2c.scan()
    print('I2C adresleri:', [hex(a) for a in adresler])
    return adresler


def motor(taraf, guc=0.35, saniye=1.5, geri=False):
    if taraf not in MOTORLAR:
        raise ValueError("taraf 'sol' ya da 'sag' olmalı")
    guc = min(max(guc, 0.0), EN_FAZLA_GUC)
    saniye = min(max(saniye, 0.0), EN_FAZLA_SANIYE)
    pwm_pin, in1, in2 = MOTORLAR[taraf]
    pwm = PWM(Pin(pwm_pin))
    pwm.freq(1000)
    a, b = Pin(in1, Pin.OUT), Pin(in2, Pin.OUT)
    try:
        a.value(0 if geri else 1)
        b.value(1 if geri else 0)
        _stby.value(1)
        pwm.duty_u16(int(guc * 65535))
        print(taraf, 'motor', 'geri' if geri else 'ileri', '%.0f%% güç, %.1f sn' % (guc * 100, saniye))
        time.sleep(saniye)
    finally:                                   # ne olursa olsun durdur
        pwm.duty_u16(0)
        a.value(0)
        b.value(0)
        _stby.value(0)
    print('durdu')


def enkoder(saniye=5):
    """Tekerleği elle çevir. Her enkoderde A kanalındaki yükselen kenarlar sayılır."""
    sayac = {'sol': 0, 'sag': 0}
    pinler = []

    def kes(ad):
        def f(_p):
            sayac[ad] += 1
        return f
    for ad, (a, _b) in (('sol', ENC_SOL), ('sag', ENC_SAG)):
        p = Pin(a, Pin.IN, Pin.PULL_UP)
        p.irq(trigger=Pin.IRQ_RISING, handler=kes(ad))
        pinler.append(p)
    print(saniye, 'sn: sol ve sağ tekerleği elle çevir...')
    time.sleep(saniye)
    for p in pinler:
        p.irq(handler=None)
    print('darbe sayısı:', sayac)
    return sayac


def tof(saniye=5):
    from tof import read_ranges_m, setup_tof     # firmware/pico2w/tof.py ve vl53l1x.py Pico'da olmalı
    setup_tof(I2C(0, sda=Pin(SDA), scl=Pin(SCL)), XSHUT)
    bitis = time.ticks_add(time.ticks_ms(), int(saniye * 1000))
    while time.ticks_diff(bitis, time.ticks_ms()) > 0:
        print('sol %.2f  orta %.2f  sag %.2f m' % tuple(read_ranges_m()))
        time.sleep_ms(200)
