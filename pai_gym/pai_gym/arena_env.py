"""Gymnasium ortami: pai_bot engellere carpmadan arenada dolasmayi ogrenir.

Gozlem : 3 ToF mesafesi (sol, orta, sag), 0-1 arasina olceklenmis.
         frames > 1 ise robot onceki adimlari da "hatirlar": gozlem
         [simdi, 1 adim once, 2 adim once, ...] seklinde arka arkaya dizilir.
         Boylece hareketli bir engelin yaklasip yaklasmadigi anlasilir.
Eylem  : 5 ayrik hareket (asagidaki ACTIONS tablosu)
Odul   : ileri gittikce +, yerinde donerken kucuk -, engele cok yaklasinca -,
         carpinca buyuk - ve bolum biter
"""
import math

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .world import TOF_MAX, Circle, World, default_obstacles

# (ad, dogrusal hiz m/s, acisal hiz rad/s) -> gercek robota /cmd_vel olarak gider
ACTIONS = (
    ('ileri',       0.20,  0.0),
    ('sol-ileri',   0.12,  1.5),
    ('sag-ileri',   0.12, -1.5),
    ('sola-don',    0.00,  2.5),
    ('saga-don',    0.00, -2.5),
)

OBS_RANGE = 1.5   # m: bundan uzak mesafeler "bos" kabul edilir (1.0)


class ArenaEnv(gym.Env):
    metadata = {'render_modes': ['human', 'rgb_array'], 'render_fps': 20}

    def __init__(self, render_mode=None, dt=0.05, max_steps=1000,
                 random_start=True, sensor_noise=True, moving_obstacles=True,
                 frames=1):
        super().__init__()
        self.render_mode = render_mode
        self.dt = dt
        self.max_steps = max_steps
        self.random_start = random_start
        self.sensor_noise = sensor_noise
        self.moving_obstacles = moving_obstacles
        self.frames = frames                # kac adimlik hafiza (1 = hafiza yok)
        self.history = []                   # son olcumler, en yenisi basta
        self.action_space = spaces.Discrete(len(ACTIONS))
        self.observation_space = spaces.Box(0.0, 1.0, shape=(3 * frames,), dtype=np.float32)
        self.world = None
        self.renderer = None
        self.steps = 0
        self.last_ranges = [TOF_MAX] * 3
        self.last_action = 0
        self.episode_return = 0.0

    def _obs(self):
        # Hafizadaki tum olcumleri tek bir uzun listeye birlestir
        r = np.concatenate(self.history).astype(np.float32)
        return np.clip(r / OBS_RANGE, 0.0, 1.0)

    def _remember(self):
        # En yeni olcumu basa ekle, eskilerden fazlasini at
        self.history.insert(0, np.array(self.last_ranges))
        del self.history[self.frames:]

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        obstacles = default_obstacles()
        if not self.moving_obstacles:
            obstacles = [o for o in obstacles if not (isinstance(o, Circle) and o.moving)]
        self.world = World(obstacles=obstacles, rng=self.np_random,
                           sensor_noise=self.sensor_noise)
        if self.random_start:
            self.world.place_robot(*self.world.random_free_pose())
        else:
            self.world.place_robot(-0.6, -0.6, math.pi / 4)
        self.steps = 0
        self.episode_return = 0.0
        self.last_ranges = self.world.read_tof()
        # Basta hafiza bos: ilk olcumu tum hafiza yerlerine kopyala
        self.history = [np.array(self.last_ranges)] * self.frames
        if self.render_mode == 'human':
            self.render()
        return self._obs(), {}

    def step(self, action):
        _, v, w = ACTIONS[int(action)]
        self.last_action = int(action)
        self.world.step(v, w, self.dt)
        self.steps += 1
        self.last_ranges = self.world.read_tof()
        self._remember()

        crashed = self.world.collided()
        nearest = min(self.last_ranges)

        reward = 1.0 * v                    # ileri gitmek iyi
        if v == 0.0:
            reward -= 0.05                  # yerinde donmek hafif ceza
        if nearest < 0.10:
            reward -= 0.2 * (0.10 - nearest) / 0.10   # tehlikeli yakinlik
        if crashed:
            reward -= 10.0

        self.episode_return += reward
        terminated = crashed
        truncated = self.steps >= self.max_steps
        info = {'crashed': crashed, 'ranges': list(self.last_ranges)}
        if self.render_mode == 'human':
            self.render()
        return self._obs(), float(reward), terminated, truncated, info

    def render(self):
        if self.render_mode is None:
            return None
        if self.renderer is None:
            from .render import Renderer
            self.renderer = Renderer(self.render_mode, fps=self.metadata['render_fps'])
        return self.renderer.draw(self)

    def close(self):
        if self.renderer is not None:
            self.renderer.close()
            self.renderer = None
