"""UdpRobot: Wi-Fi uzerinden gercek robotu (Pico 2 W) surer.

Protokol: tek datagram = tek JSON. Port 5005.
  host -> robot : {"cmd": "drive", "v": 0.2, "w": 0.0}
                  {"cmd": "stop"}
                  {"cmd": "mode", "mode": "random" | "remote"}
  robot -> host : {"r": [sol, orta, sag], "bat": 5.9, "mode": "remote"}   (yaklasik 20 Hz)
Robot 0.5 sn komut gelmezse "remote" modunda kendiliginden durur (guvenlik).
"""
import json
import socket
import time

from .base import Robot

PORT = 5005


class UdpRobot(Robot):
    def __init__(self, host, port=PORT, n_sensors=3, timeout=1.0, mode='remote'):
        self.addr = (host, port)
        self.n_sensors = n_sensors
        self.timeout = timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.last = None            # son telemetri sozlugu
        # mode=None: robotun modunu degistirmeden sadece dinle (robot bizi tanisin diye bos paket yolla)
        self.send({'cmd': 'mode', 'mode': mode} if mode else {'cmd': 'ping'})

    def send(self, msg):
        self.sock.sendto(json.dumps(msg).encode(), self.addr)

    def _drain(self):
        """Gelen tum paketleri oku, en yenisini sakla."""
        while True:
            try:
                data, _ = self.sock.recvfrom(1024)
            except BlockingIOError:
                return
            try:
                self.last = json.loads(data)
            except ValueError:
                pass                # bozuk paketi atla

    def telemetry(self, wait=None):
        """Son telemetri. Henuz yoksa `wait` (varsayilan timeout) saniye bekler."""
        deadline = time.time() + (self.timeout if wait is None else wait)
        self._drain()
        while self.last is None and time.time() < deadline:
            time.sleep(0.01)
            self._drain()
        return self.last

    def read_ranges(self):
        t = self.telemetry()
        if t is None:
            raise TimeoutError(f'{self.addr[0]} robotundan veri gelmiyor.')
        return t['r']

    def drive(self, v, w):
        self.send({'cmd': 'drive', 'v': v, 'w': w})

    def wait(self, dt):
        time.sleep(dt)
        self._drain()

    def stop(self):
        self.send({'cmd': 'stop'})

    def set_mode(self, mode):
        self.send({'cmd': 'mode', 'mode': mode})

    def close(self):
        self.stop()
        self.sock.close()
