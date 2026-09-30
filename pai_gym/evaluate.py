"""Modelleri ve temel kontrolculeri AYNI test setinde olcer, sonuclari siteye yazar.

Sonuclar docs/data/experiments.json dosyasina eklenir (ayni id varsa guncellenir).
ArenaEnv'e yeni bir secenek eklediginde bu dosyayi DEGISTIRME: secenegi
--env-kwargs ile ver, sitede "ayarlar" olarak otomatik gorunur.

Ornekler:
  python evaluate.py --id rule   --name "Kuralli kontrolcu" --policy rule
  python evaluate.py --id random --name "Rastgele"          --policy random
  python evaluate.py --id ppo-500k-f3 --name "PPO, 3 kare hafiza" \
      --model models/ppo_500k_f3 --steps 500000 --env-kwargs '{"frames": 3}' \
      --notes "Son 3 sensor okumasi gozleme eklendi" --export --publish
  python evaluate.py --id ppo-yan --name "PPO, yan sensorlu" --model models/ppo_yan \
      --env-kwargs '{"side_sensors": true}' --layout side5 --export --publish
"""
import argparse
import datetime
import json
import subprocess
from pathlib import Path

import numpy as np

from pai_gym.arena_env import ArenaEnv

ROOT = Path(__file__).resolve().parent.parent
DOCS_DATA = ROOT / 'docs' / 'data'


def make_env(moving, kwargs):
    try:
        return ArenaEnv(moving_obstacles=moving, **kwargs)
    except TypeError as e:
        raise SystemExit(f'ArenaEnv bu ayarlari kabul etmiyor {kwargs}: {e}')


def make_actor(args):
    if args.policy == 'random':
        return lambda obs, env: env.action_space.sample(), None
    if args.policy == 'rule':
        from play import rule_policy
        # Gozlemde en yeni karenin ilk 3 degeri = on sol/orta/sag sensorler olmali.
        return lambda obs, env: rule_policy(obs[:3]), None
    from stable_baselines3 import PPO
    model = PPO.load(args.model, device='cpu')
    return (lambda obs, env: int(model.predict(obs, deterministic=True)[0])), model


def evaluate(act, moving, kwargs, episodes, seed0):
    env = make_env(moving, kwargs)
    crashes, steps, returns = 0, [], []
    for i in range(episodes):
        obs, _ = env.reset(seed=seed0 + i)
        env.action_space.seed(seed0 + i)
        total, n, done, info = 0.0, 0, False, {}
        while not done:
            obs, r, term, trunc, info = env.step(act(obs, env))
            total += r
            n += 1
            done = term or trunc
        crashes += bool(info.get('crashed'))
        steps.append(n)
        returns.append(total)
    env.close()
    return {
        'crash_rate': round(crashes / episodes, 3),
        'mean_steps': round(float(np.mean(steps)), 1),
        'mean_return': round(float(np.mean(returns)), 2),
    }


def export_policy(model, kwargs, layout, name, exp_id, out):
    """PPO politika agini tarayicida calisacak JSON'a cevirir ve kendini dogrular."""
    import torch.nn as nn

    layers = []

    def add(module):
        mods = list(module) if isinstance(module, nn.Sequential) else [module]
        for m in mods:
            if isinstance(m, nn.Linear):
                layers.append({
                    'W': np.round(m.weight.detach().cpu().numpy(), 5).tolist(),
                    'b': np.round(m.bias.detach().cpu().numpy(), 5).tolist(),
                    'act': 'none',
                })
            elif isinstance(m, nn.Tanh):
                layers[-1]['act'] = 'tanh'
            elif isinstance(m, nn.ReLU):
                layers[-1]['act'] = 'relu'

    add(model.policy.mlp_extractor.policy_net)
    add(model.policy.action_net)

    def forward(x):
        for L in layers:
            x = np.array(L['W']) @ x + np.array(L['b'])
            if L['act'] == 'tanh':
                x = np.tanh(x)
            elif L['act'] == 'relu':
                x = np.maximum(x, 0)
        return int(np.argmax(x))

    rng = np.random.default_rng(0)
    obs_dim = len(layers[0]['W'][0])
    mismatch = sum(
        forward(o) != int(model.predict(o, deterministic=True)[0])
        for o in (rng.uniform(0, 1, obs_dim).astype(np.float32) for _ in range(500)))
    if mismatch > 5:
        raise SystemExit(f'Disa aktarma hatali: 500 ornekten {mismatch} tanesi uyusmadi.')

    out.write_text(json.dumps({
        'id': exp_id, 'name': name, 'frames': kwargs.get('frames', 1),
        'sensor_layout': layout, 'obs_dim': obs_dim,
        'frame_order': 'newest_first', 'layers': layers,
    }, separators=(',', ':')))
    print(f'Politika disa aktarildi: {out} (uyusmazlik {mismatch}/500)')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--id', required=True, help='deney kimligi, ornek: ppo-500k-f3')
    p.add_argument('--name', required=True, help='sitede gorunecek ad')
    p.add_argument('--policy', choices=['model', 'rule', 'random'], default='model')
    p.add_argument('--model', help='model dosyasi (.zip uzantisiz)')
    p.add_argument('--env-kwargs', default='{}', help='ArenaEnv secenekleri (JSON)')
    p.add_argument('--frames', type=int, default=1, help='kisayol: env-kwargs icindeki frames')
    p.add_argument('--layout', default='front3', help="docs/data/robot.json'daki sensor duzeni kimligi")
    p.add_argument('--steps', type=int, default=0, help='egitim adim sayisi (bilgi icin)')
    p.add_argument('--notes', default='')
    p.add_argument('--episodes', type=int, default=100)
    p.add_argument('--seed', type=int, default=1000)
    p.add_argument('--export', action='store_true', help="sitedeki 'Ogrenmis' modu icin disa aktar")
    p.add_argument('--publish', action='store_true', help='bitince publish.sh ile siteyi guncelle')
    a = p.parse_args()
    if a.policy == 'model' and not a.model:
        raise SystemExit('--policy model icin --model gerekli.')
    kwargs = json.loads(a.env_kwargs)
    if a.frames != 1:
        kwargs['frames'] = a.frames

    act, model = make_actor(a)
    results = {}
    for key, moving in (('static', False), ('moving', True)):
        results[key] = evaluate(act, moving, kwargs, a.episodes, a.seed)
        r = results[key]
        print(f'{key:7s} carpisma %{r["crash_rate"] * 100:5.1f}  '
              f'ort. adim {r["mean_steps"]:6.1f}  ort. odul {r["mean_return"]:7.2f}')

    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    path = DOCS_DATA / 'experiments.json'
    data = json.loads(path.read_text()) if path.exists() else {'experiments': []}
    entry = {
        'id': a.id, 'name': a.name,
        'kind': 'baseline' if a.policy != 'model' else 'learned',
        'date': datetime.date.today().isoformat(),
        'notes': a.notes, 'layout': a.layout,
        'params': {'steps': a.steps, **kwargs},
        'results': results,
    }
    data['experiments'] = [e for e in data['experiments'] if e['id'] != a.id] + [entry]
    data['experiments'].sort(key=lambda e: (e['kind'] != 'baseline', e['params'].get('steps', 0), e['id']))
    data['episodes'] = a.episodes
    data['updated'] = datetime.datetime.now().isoformat(timespec='minutes')
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f'Sonuclar yazildi: {path}')

    if a.export:
        if model is None:
            raise SystemExit('--export sadece egitilmis modeller icin.')
        export_policy(model, kwargs, a.layout, a.name, a.id, DOCS_DATA / 'policy_latest.json')
    if a.publish:
        subprocess.run([str(ROOT / 'publish.sh'), f'Deney: {a.name}'], check=False)


if __name__ == '__main__':
    main()
