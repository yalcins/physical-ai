"""Kucuk robot yazilimi: Raspberry Pi Pico 2 W (MicroPython).

Iki mod:
  random : kendi basina rastgele dolasir, onunde engel varsa doner (hareketli engel rolu)
  remote : Wi-Fi (UDP, port 5005) ile bilgisayardan gelen {"cmd": "drive"} komutlarini uygular
Protokol pai_robot/udp.py dosyasinda anlatildi. Pin plani CLAUDE.md'deki ile ayni.

DURUM: Gercek kartta henuz denenmedi. ToF icin drakxtwo/vl53l1x_pico kutuphanesi gerekir
(vl53l1x.py, bkz. tof.py).
"""
import json
import random
import socket
import time

import network
from machine import ADC, I2C, PWM, Pin

import secrets   # WIFI_SSID, WIFI_PASSWORD (git'e girmez, .gitignore'da)
from tof import read_ranges_m, setup_tof

PORT = 5005
WHEEL_RADIUS = 0.0215
WHEEL_SEPARATION = 0.115
MAX_WHEEL_RAD_S = 31.0      # ~300 RPM (JGA12-N20B, 6V)
WATCHDOG_S = 0.5            # remote modda bu sure komut gelmezse dur
WIFI_TIMEOUT_S = 20         # tek bir Wi-Fi baglanma denemesi icin en uzun sure
PWM_FREQ = 1000

# TB6612FNG pinleri (CLAUDE.md)
STBY = Pin(22, Pin.OUT, value=0)    # acilista surucu bekleme modunda: motorlar kapali
MOTOR_L = (PWM(Pin(16)), Pin(17, Pin.OUT), Pin(18, Pin.OUT))   # PWMA, AIN1, AIN2
MOTOR_R = (PWM(Pin(21)), Pin(19, Pin.OUT), Pin(20, Pin.OUT))   # PWMB, BIN1, BIN2
for m in (MOTOR_L, MOTOR_R):
    m[0].freq(PWM_FREQ)
battery = ADC(Pin(26))


def set_motor(motor, rad_s):
    pwm, in1, in2 = motor
    duty = min(abs(rad_s) / MAX_WHEEL_RAD_S, 1.0)
    in1.value(1 if rad_s > 0 else 0)
    in2.value(1 if rad_s < 0 else 0)
    pwm.duty_u16(int(duty * 65535))


def drive(v, w):
    """(v m/s, w rad/s) -> tekerlek hizlari. world.wheel_speeds ile ayni formul."""
    left = (v - w * WHEEL_SEPARATION / 2) / WHEEL_RADIUS
    right = (v + w * WHEEL_SEPARATION / 2) / WHEEL_RADIUS
    STBY.value(1)
    set_motor(MOTOR_L, left)
    set_motor(MOTOR_R, right)


def motors_off():
    STBY.value(0)
    set_motor(MOTOR_L, 0)
    set_motor(MOTOR_R, 0)


def connect_wifi():
    """Wi-Fi'ye baglanana kadar motorlar KAPALI kalir. Her deneme WIFI_TIMEOUT_S ile sinirli;
    basarisiz olursa nedeni yazilir ve yeniden denenir. Beklerken LED yanip soner."""
    motors_off()
    led = Pin('LED', Pin.OUT)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    while True:
        wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
        start = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start) > WIFI_TIMEOUT_S * 1000:
                break
            led.value(not led.value())
            time.sleep(0.3)
        if wlan.isconnected():
            led.value(1)
            print('IP:', wlan.ifconfig()[0])
            return
        print('Wi-Fi baglanamadi (durum kodu:', wlan.status(), '), yeniden deneniyor')
        wlan.disconnect()
        motors_off()


def random_command(ranges, state):
    """Rastgele dolasma: 1-3 sn'de bir yeni hareket sec; engel yakinsa yerinde don."""
    left, center, right = ranges[:3]
    if center < 0.20 or min(left, right) < 0.10:
        return (0.0, 2.5 if left > right else -2.5)
    if time.ticks_diff(time.ticks_ms(), state['until']) > 0:
        state['cmd'] = random.choice(((0.20, 0.0), (0.12, 1.5), (0.12, -1.5), (0.0, 2.5), (0.0, -2.5)))
        state['until'] = time.ticks_add(time.ticks_ms(), random.randint(1000, 3000))
    return state['cmd']


def main():
    connect_wifi()
    i2c = I2C(0, sda=Pin(4), scl=Pin(5))
    setup_tof(i2c, xshut_pins=(6, 7, 8))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', PORT))
    sock.setblocking(False)

    mode, host = 'random', None
    cmd = (0.0, 0.0)
    last_cmd = time.ticks_ms()
    state = {'cmd': (0.0, 0.0), 'until': 0}
    last_tx = 0
    while True:
        try:                                    # gelen komut var mi?
            data, host = sock.recvfrom(256)
            msg = json.loads(data)
            if msg.get('cmd') == 'mode':
                mode = msg['mode']
            elif msg.get('cmd') == 'drive':
                cmd = (msg['v'], msg['w'])
                last_cmd = time.ticks_ms()
            elif msg.get('cmd') == 'stop':
                cmd = (0.0, 0.0)
        except (OSError, ValueError):
            pass

        ranges = read_ranges_m()
        if mode == 'random':
            drive(*random_command(ranges, state))
        elif time.ticks_diff(time.ticks_ms(), last_cmd) > WATCHDOG_S * 1000:
            drive(0.0, 0.0)                     # bilgisayar sustu: dur
        else:
            drive(*cmd)

        if host and time.ticks_diff(time.ticks_ms(), last_tx) >= 50:   # 20 Hz telemetri
            bat = battery.read_u16() / 65535 * 3.3 * 3   # bolucu orani montaja gore ayarlanmali
            sock.sendto(json.dumps({'r': ranges, 'bat': round(bat, 2), 'mode': mode}).encode(), host)
            last_tx = time.ticks_ms()


if __name__ == '__main__':
    main()
