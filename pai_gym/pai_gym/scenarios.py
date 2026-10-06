"""Senaryo dosyalari: arenadaki engelleri JSON ile tanimla (pai_gym/scenarios/*.json).

Engel turleri:
  box     sabit kutu              x, y, w, h
  circle  sabit silindir          x, y, r
  bouncer duvardan seken engel    x, y, r, vx, vy
  pico    gercek Pico robot       x, y, theta  (firmware'deki rastgele dolasma, yaricap 7,5 cm)
Kullanim:  ArenaEnv(scenario='pico2')   ya da   ArenaEnv(scenario='yol/dosya.json')
"""
import json
from pathlib import Path

from .world import Box, Circle, PicoBot

SCENARIO_DIR = Path(__file__).resolve().parent.parent / 'scenarios'


def build_obstacle(d):
    kind = d['type']
    if kind == 'box':
        return Box(d['x'], d['y'], d['w'], d['h'])
    if kind == 'circle':
        return Circle(d['x'], d['y'], d['r'])
    if kind == 'bouncer':
        return Circle(d['x'], d['y'], d['r'], vx=d['vx'], vy=d['vy'])
    if kind == 'pico':
        return PicoBot(d['x'], d['y'], d.get('theta', 0.0))
    raise ValueError(f"Bilinmeyen engel turu: {kind!r} (box, circle, bouncer, pico)")


def load_scenario(name_or_path):
    """Senaryoyu oku. Dondurur: (metadata sozlugu, engel listesi). Her cagrida yeni nesneler uretir."""
    path = Path(name_or_path)
    if not path.suffix:
        path = SCENARIO_DIR / f'{name_or_path}.json'
    if not path.exists():
        names = sorted(p.stem for p in SCENARIO_DIR.glob('*.json'))
        raise FileNotFoundError(f'Senaryo bulunamadi: {name_or_path}. Hazir olanlar: {names}')
    data = json.loads(path.read_text(encoding='utf-8'))
    return data, [build_obstacle(o) for o in data['obstacles']]
