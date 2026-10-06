"""Egitilmis politikayi (docs/data/policy_latest.json) numpy ile calistirir.

Torch ya da gymnasium gerekmez; bu yuzden Raspberry Pi 4'te de calisir.
Gozlem, ArenaEnv ile birebir ayni hazirlanir: mesafe / 1.5 m, 0-1 arasina kirpilir,
hafiza varsa en yeni olcum basta olacak sekilde ard arda eklenir.
"""
import json

import numpy as np

OBS_RANGE = 1.5   # m (arena_env.py ile ayni olmali; tests/ bunu kontrol eder)

# (ad, dogrusal hiz m/s, acisal hiz rad/s) -- arena_env.ACTIONS ile ayni olmali
ACTIONS = (
    ('ileri',       0.20,  0.0),
    ('sol-ileri',   0.12,  1.5),
    ('sag-ileri',   0.12, -1.5),
    ('sola-don',    0.00,  2.5),
    ('saga-don',    0.00, -2.5),
)


class Policy:
    def __init__(self, data):
        self.layers = [(np.array(L['W']), np.array(L['b']), L['act']) for L in data['layers']]
        self.frames = data['frames']
        self.layout = data['sensor_layout']
        self.obs_dim = data['obs_dim']
        self.history = []

    @classmethod
    def load(cls, path):
        with open(path, encoding='utf-8') as f:
            return cls(json.load(f))

    def reset(self):
        self.history = []

    def act(self, ranges):
        """Sensor mesafelerinden (m) bir eylem indeksi uret."""
        r = np.asarray(ranges, dtype=float)
        if not self.history:                       # ilk olcumu tum hafizaya kopyala
            self.history = [r] * self.frames
        else:
            self.history.insert(0, r)
            del self.history[self.frames:]
        x = np.clip(np.concatenate(self.history) / OBS_RANGE, 0.0, 1.0)
        if x.size != self.obs_dim:
            raise ValueError(f'Politika {self.obs_dim} sayi bekliyor, {x.size} geldi '
                             f'(sensor duzeni: {self.layout}).')
        for W, b, act in self.layers:
            x = W @ x + b
            if act == 'tanh':
                x = np.tanh(x)
            elif act == 'relu':
                x = np.maximum(x, 0.0)
        return int(np.argmax(x))

    def command(self, ranges):
        """Eylemi (v, w) hiz komutuna cevir."""
        _, v, w = ACTIONS[self.act(ranges)]
        return v, w
