"""Arenayi izle / robotu sur.

Modlar:
    python play.py --mode manual   # ok tuslariyla sen sur (ToF degerlerini izle!)
    python play.py --mode random   # rastgele eylemler (egitim oncesi)
    python play.py --mode rule     # elle yazilmis kural tabanli kontrolcu
    python play.py --mode model    # egitilmis PPO modeli (egitim sonrasi)
"""
import argparse

import pygame

from pai_gym.arena_env import ArenaEnv


def rule_policy(obs):
    """Basit kural: onde engel varsa bos tarafa don, yoksa ileri git."""
    left, center, right = obs            # 0-1 arasi (1.0 = 1.5 m veya uzak)
    if center < 0.15 or min(left, right) < 0.08:
        return 3 if left > right else 4  # yerinde don
    if left < 0.2:
        return 2                         # saga kay
    if right < 0.2:
        return 1                         # sola kay
    return 0                             # ileri


def manual_policy():
    k = pygame.key.get_pressed()
    if k[pygame.K_UP] and k[pygame.K_LEFT]:
        return 1
    if k[pygame.K_UP] and k[pygame.K_RIGHT]:
        return 2
    if k[pygame.K_LEFT]:
        return 3
    if k[pygame.K_RIGHT]:
        return 4
    if k[pygame.K_UP]:
        return 0
    return None                          # tus yok -> bekle


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['manual', 'random', 'rule', 'model'], default='rule')
    p.add_argument('--model', default='models/ppo_pai')
    p.add_argument('--episodes', type=int, default=5)
    p.add_argument('--no-moving', action='store_true')
    p.add_argument('--frames', type=int, default=1,
                   help='modelin egitildigi hafiza uzunlugu')
    p.add_argument('--layout', default='front3',
                   help='sensor duzeni: front3 veya side5')
    p.add_argument('--scenario', default=None,
                   help='senaryo: default, pico2, empty ya da bir .json yolu (pai_gym/scenarios/)')
    a = p.parse_args()

    env = ArenaEnv(render_mode='human', moving_obstacles=not a.no_moving,
                   frames=a.frames, layout=a.layout, scenario=a.scenario)
    model = None
    if a.mode == 'model':
        from stable_baselines3 import PPO
        model = PPO.load(a.model, device='cpu')

    for ep in range(a.episodes):
        obs, _ = env.reset()
        done = False
        while not done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    env.close()
                    return
            if a.mode == 'manual':
                action = manual_policy()
                if action is None:
                    env.render()
                    continue
            elif a.mode == 'random':
                action = env.action_space.sample()
            elif a.mode == 'rule':
                action = rule_policy(obs[:3])   # ilk uc deger = on sol/orta/sag
            else:
                action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
        sonuc = 'CARPTI' if info['crashed'] else 'sure doldu'
        print(f'Bolum {ep + 1}: {env.steps} adim, odul {env.episode_return:.1f} ({sonuc})')
    env.close()


if __name__ == '__main__':
    main()
