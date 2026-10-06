"""Egitilmis modeli pencere acmadan kaydeder: tek kare PNG + kisa MP4 video.

    python record.py --model models/ppo_pai_f3 --frames 3 --seconds 6 --out ../docs/media/pai-gym

Cizim 'rgb_array' modunda bellekte yapilir (ekran gerekmez). Video icin ffmpeg gerekir.
Model, secilen tohumlar arasinda 'carpmadan biten ve hareketli engele en cok yaklasan'
bolumu secer; boylece video ilginc bir an gosterir. Hangi tohum secildi ekrana yazilir.
"""
import argparse
import os
import subprocess

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')   # pygame pencere acmasin

import numpy as np
import pygame
from stable_baselines3 import PPO

from pai_gym.arena_env import ArenaEnv


def play(env, model, seed, steps, record=False):
    """Bir bolum oynat. Dondurur: (carpti mi, en yakin mesafe, kareler)."""
    obs, _ = env.reset(seed=seed)
    frames, closest, crashed = [], 9.9, False
    for _ in range(steps):
        action, _ = model.predict(obs, deterministic=True)
        obs, _, terminated, truncated, info = env.step(action)
        closest = min(closest, min(info['ranges']))
        if record:
            frames.append(env.render())
        if terminated:
            crashed = bool(info['crashed'])
            break
    return crashed, closest, frames


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model', default='models/ppo_pai_f3')
    p.add_argument('--frames', type=int, default=3, help='modelin hafiza uzunlugu')
    p.add_argument('--layout', default='front3')
    p.add_argument('--seconds', type=float, default=6)
    p.add_argument('--seeds', type=int, default=40, help='denenecek tohum sayisi')
    p.add_argument('--out', default='../docs/media/pai-gym', help='uzantisiz cikti yolu')
    a = p.parse_args()

    kw = dict(frames=a.frames, layout=a.layout)
    env = ArenaEnv(render_mode='rgb_array', **kw)
    fps = env.metadata['render_fps']
    steps = int(a.seconds * fps)               # dt = 0.05 sn -> 20 kare/sn, gercek zamanli
    model = PPO.load(a.model, device='cpu')

    # En ilginc tohum: carpmayan, hareketli engele en cok yaklasan
    best = None
    for seed in range(a.seeds):
        crashed, closest, _ = play(ArenaEnv(**kw), model, seed, steps)
        if not crashed and (best is None or closest < best[1]):
            best = (seed, closest)
    if best is None:
        raise SystemExit('Hicbir tohumda carpmadan bitmedi; --seeds artir.')
    seed = best[0]
    print(f'secilen tohum: {seed} (en yakin mesafe {best[1]:.2f} m)')

    _, _, frames = play(env, model, seed, steps, record=True)
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    surf = pygame.surfarray.make_surface(np.transpose(frames[len(frames) // 2], (1, 0, 2)))
    pygame.image.save(surf, a.out + '.png')

    h, w, _ = frames[0].shape
    ff = subprocess.Popen(
        ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
         '-s', f'{w}x{h}', '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
         '-crf', '24', '-movflags', '+faststart', a.out + '.mp4'], stdin=subprocess.PIPE)
    for f in frames:
        ff.stdin.write(np.ascontiguousarray(f).tobytes())
    ff.stdin.close()
    ff.wait()
    print(f'{len(frames)} kare, {len(frames) / fps:.1f} sn -> {a.out}.png ve .mp4')


if __name__ == '__main__':
    main()
