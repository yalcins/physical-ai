"""Pico'yu taklit eden UDP sunucusu: World ile ayni protokolu konusur (donanim gerekmez)."""
import json
import socket
import threading
import time

import numpy as np
from pai_gym.world import World, default_obstacles


class FakePico(threading.Thread):
    def __init__(self, port=0, watchdog=0.5):
        super().__init__(daemon=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('127.0.0.1', port))
        self.sock.settimeout(0.02)
        self.port = self.sock.getsockname()[1]
        self.world = World(default_obstacles(), rng=np.random.default_rng(0))
        self.world.place_robot(-0.6, -0.6, 0.78)
        self.cmd, self.last_cmd, self.host = (0.0, 0.0), time.time(), None
        self.mode, self.watchdog, self.running = 'remote', watchdog, True

    def run(self):
        last = time.time()
        while self.running:
            try:
                data, self.host = self.sock.recvfrom(256)
                m = json.loads(data)
                if m['cmd'] == 'drive':
                    self.cmd, self.last_cmd = (m['v'], m['w']), time.time()
                elif m['cmd'] == 'stop':
                    self.cmd = (0.0, 0.0)
                elif m['cmd'] == 'mode':
                    self.mode = m['mode']
            except socket.timeout:
                pass
            now = time.time()
            v, w = self.cmd if now - self.last_cmd < self.watchdog else (0.0, 0.0)
            self.world.step(v, w, now - last)
            last = now
            if self.host:
                msg = {'r': self.world.read_tof(), 'bat': 6.0, 'mode': self.mode}
                self.sock.sendto(json.dumps(msg).encode(), self.host)

    def close(self):
        self.running = False
        self.join(timeout=1)
        self.sock.close()
