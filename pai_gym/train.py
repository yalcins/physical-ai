"""PPO ile pai_bot'a engellere carpmadan dolasmayi ogret.

Kullanim:
    python train.py                 # varsayilan 150 bin adim
    python train.py --steps 300000  # daha uzun egitim
    python train.py --no-moving     # sadece sabit engeller (ilk ders icin)
"""
import argparse
import time
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env

from pai_gym.arena_env import ArenaEnv


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--steps', type=int, default=150_000)
    p.add_argument('--envs', type=int, default=8)
    p.add_argument('--out', default='models/ppo_pai')
    p.add_argument('--no-moving', action='store_true',
                   help='hareketli engeller olmadan egit (kolay mufredat)')
    p.add_argument('--frames', type=int, default=1,
                   help='kac adimlik hafiza (3 = son 3 olcumu gor)')
    p.add_argument('--layout', default='front3',
                   help="sensor duzeni: front3 (3 on sensor) veya side5 (+2 yan sensor)")
    a = p.parse_args()

    env = make_vec_env(ArenaEnv, n_envs=a.envs,
                       env_kwargs={'moving_obstacles': not a.no_moving,
                                'frames': a.frames,
                                'layout': a.layout})
    model = PPO('MlpPolicy', env, verbose=1, n_steps=512, batch_size=256,
                learning_rate=3e-4, gamma=0.99, ent_coef=0.01, device='cpu')
    t0 = time.time()
    model.learn(total_timesteps=a.steps)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    model.save(a.out)
    print(f'\nEgitim bitti: {time.time() - t0:.0f} sn. Model: {a.out}.zip')
    print('Izlemek icin:  python play.py --mode model')


if __name__ == '__main__':
    main()
