"""Ustten gorunum (pygame). Arena, engeller, robot ve ToF konilerini cizer."""
import math

import numpy as np
import pygame

from .world import HALF, ROBOT_RADIUS, TOF_FOV, TOF_SENSORS, Box, Circle

SIZE = 640          # arena piksel boyutu
PANEL = 110         # alttaki bilgi paneli
SCALE = SIZE / (2 * HALF)

BG = (235, 230, 218)
WALL = (150, 110, 70)
OBST = (60, 120, 200)
MOVING = (210, 80, 60)
ROBOT = (215, 150, 70)
RAY = (40, 160, 90)
RAY_NEAR = (220, 50, 50)
TEXT = (40, 40, 40)


def to_px(x, y):
    return int((x + HALF) * SCALE), int((HALF - y) * SCALE)


class Renderer:

    def __init__(self, mode, fps=20):
        pygame.init()
        self.mode = mode
        self.fps = fps
        if mode == 'human':
            self.screen = pygame.display.set_mode((SIZE, SIZE + PANEL))
            pygame.display.set_caption('Physical AI Arena - pai_bot')
        else:
            self.screen = pygame.Surface((SIZE, SIZE + PANEL))
        self.font = pygame.font.SysFont('dejavusans', 16)
        self.clock = pygame.time.Clock()

    def draw(self, env):
        from .arena_env import ACTIONS
        w = env.world
        s = self.screen
        s.fill(BG)
        pygame.draw.rect(s, WALL, (0, 0, SIZE, SIZE), 6)

        for ob in w.obstacles:
            if isinstance(ob, Circle):
                col = MOVING if ob.moving else OBST
                pygame.draw.circle(s, col, to_px(ob.x, ob.y), int(ob.r * SCALE))
            elif isinstance(ob, Box):
                x0, y0 = to_px(ob.x - ob.w / 2, ob.y + ob.h / 2)
                pygame.draw.rect(s, OBST, (x0, y0, int(ob.w * SCALE), int(ob.h * SCALE)))

        # ToF konileri
        for (_, fwd, side, ang), d in zip(TOF_SENSORS, env.last_ranges):
            ox, oy, heading = w.sensor_origin(fwd, side, ang)
            col = RAY_NEAR if d < 0.15 else RAY
            pts = [to_px(ox, oy)]
            for o in np.linspace(-TOF_FOV / 2, TOF_FOV / 2, 7):
                pts.append(to_px(ox + d * math.cos(heading + o), oy + d * math.sin(heading + o)))
            cone = pygame.Surface(s.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(cone, (*col, 60), pts)
            s.blit(cone, (0, 0))
            pygame.draw.line(s, col, pts[0], to_px(ox + d * math.cos(heading), oy + d * math.sin(heading)), 2)

        # robot
        c = to_px(w.x, w.y)
        pygame.draw.circle(s, ROBOT, c, int(ROBOT_RADIUS * SCALE))
        nose = to_px(w.x + ROBOT_RADIUS * math.cos(w.theta), w.y + ROBOT_RADIUS * math.sin(w.theta))
        pygame.draw.line(s, TEXT, c, nose, 3)

        # bilgi paneli
        pygame.draw.rect(s, (250, 248, 243), (0, SIZE, SIZE, PANEL))
        l, m, r = env.last_ranges
        lines = [
            f'ToF  sol: {l:4.2f} m   orta: {m:4.2f} m   sag: {r:4.2f} m',
            f'Eylem: {ACTIONS[env.last_action][0]:<10}  Adim: {env.steps:4d}   Toplam odul: {env.episode_return:6.2f}',
            'Kirmizi daireler hareketli engeller (sahadaki Pico robotlar gibi)',
        ]
        for i, text in enumerate(lines):
            s.blit(self.font.render(text, True, TEXT), (12, SIZE + 12 + i * 30))

        if self.mode == 'human':
            pygame.event.pump()
            pygame.display.flip()
            self.clock.tick(self.fps)
            return None
        return np.transpose(pygame.surfarray.array3d(s), (1, 0, 2))

    def close(self):
        pygame.quit()
