"""pai_gym simulatorunun birim testleri. Calistir:  .venv/bin/python tests/test_pai_gym.py"""
import math
import os
import re
import sys
from pathlib import Path

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'pai_gym'))

import numpy as np  # noqa: E402
from pai_gym import world as W  # noqa: E402
from pai_gym.arena_env import ACTIONS, ArenaEnv  # noqa: E402
from pai_gym.scenarios import load_scenario  # noqa: E402


def same_obstacles(a, b):
    def key(o):
        return (type(o).__name__, *[round(getattr(o, k), 6) for k in ('x', 'y', 'r', 'w', 'h', 'vx', 'vy') if hasattr(o, k)])
    return [key(o) for o in a] == [key(o) for o in b]


# ---------- geometri ----------
def test_ray_segment_and_circle():
    assert abs(W.ray_segment(0, 0, 1, 0, ((2, -1), (2, 1))) - 2.0) < 1e-9
    assert W.ray_segment(0, 0, -1, 0, ((2, -1), (2, 1))) is None          # arkada kaldi
    assert W.ray_segment(0, 0, 1, 0, ((2, 1), (2, 3))) is None            # kacirdi
    assert abs(W.ray_circle(0, 0, 1, 0, W.Circle(2, 0, 0.5)) - 1.5) < 1e-9
    assert W.ray_circle(0, 0, 0, 1, W.Circle(2, 0, 0.5)) is None


def test_cast_hits_wall_and_obstacle():
    w = W.World(obstacles=[], sensor_noise=False)
    assert abs(w.cast(0, 0, 0.0) - 1.0) < 1e-9                             # duvar 1 m
    w.obstacles = [W.Circle(0.5, 0, 0.1)]
    assert abs(w.cast(0, 0, 0.0) - 0.4) < 1e-9                             # engel duvardan once
    assert abs(w.cast(0, 0, math.pi / 2) - 1.0) < 1e-9


def test_clearance_and_collision():
    w = W.World(obstacles=[W.Circle(0, 0, 0.1)], sensor_noise=False)
    w.place_robot(0.5, 0.0, 0.0)
    assert not w.collided()
    w.place_robot(0.1 + W.ROBOT_RADIUS - 0.001, 0.0, 0.0)                  # yaricaplar ic ice
    assert w.collided()
    w.place_robot(W.HALF - W.ROBOT_RADIUS + 0.001, 0.9, 0.0)               # duvara degdi
    assert w.collided()


def test_kinematics_straight_and_turn():
    w = W.World(obstacles=[], sensor_noise=False)
    w.place_robot(0, 0, 0)
    for _ in range(20):
        w.step(0.2, 0.0, 0.05)                                             # 1 sn, 0,2 m/s
    assert abs(w.x - 0.2) < 1e-9 and abs(w.y) < 1e-9
    w.place_robot(0, 0, 0)
    for _ in range(int(2 * math.pi / 2.5 / 0.05)):                         # bir tam tur ~2,51 sn
        w.step(0.0, 2.5, 0.05)
    assert abs(w.x) < 1e-9 and abs(w.y) < 1e-9


def test_wheel_speeds_roundtrip_and_motor_scale():
    wl, wr = W.World.wheel_speeds(0.2, 0.0)
    assert abs(wl - wr) < 1e-12 and abs(wl * W.WHEEL_RADIUS - 0.2) < 1e-12
    w = W.World(obstacles=[], sensor_noise=False, motor_scale=(0.5, 1.0))
    w.place_robot(0, 0, 0)
    w.step(0.2, 0.0, 0.05)
    assert w.w > 0                                                         # sol tekerlek yavas: sola doner
    assert abs(w.v - 0.15) < 1e-9                                          # ortalama hiz 0,75 kat


def test_sensor_bias_dropout_and_clip():
    w = W.World(obstacles=[], sensor_noise=False)
    w.place_robot(0, 0, 0)
    base = w.read_tof()[1]
    w.sensor_bias = 0.1
    assert abs(w.read_tof()[1] - (base + 0.1)) < 1e-9
    w.sensor_bias, w.sensor_dropout = 0.0, 1.0
    assert w.read_tof() == [W.TOF_MAX] * 3                                 # hep gecersiz -> bos
    w.sensor_dropout = 0.0
    w.place_robot(W.HALF - W.ROBOT_RADIUS, 0, 0)
    assert min(w.read_tof()) >= W.TOF_MIN


# ---------- ortam ----------
def test_env_shapes_and_bounds():
    for layout, n in (('front3', 3), ('side5', 5)):
        env = ArenaEnv(layout=layout, frames=3)
        obs, _ = env.reset(seed=0)
        assert obs.shape == (n * 3,) and obs.min() >= 0 and obs.max() <= 1
        obs, r, term, trunc, info = env.step(0)
        assert obs.shape == (n * 3,) and np.isfinite(r)


def test_env_is_deterministic_for_same_seed():
    def run(seed):
        env = ArenaEnv(frames=3)
        obs, _ = env.reset(seed=seed)
        out = []
        for i in range(60):
            obs, r, *_ = env.step(i % 5)
            out.append((round(r, 6), tuple(np.round(obs, 6))))
        return out
    assert run(7) == run(7) and run(7) != run(8)


def test_crash_gives_big_penalty_and_ends():
    env = ArenaEnv(random_start=False, moving_obstacles=False)
    env.reset(seed=0)
    env.world.place_robot(W.HALF - W.ROBOT_RADIUS - 0.005, 0.9, 0.0)       # duvara bakiyor
    done, total = False, 0.0
    for _ in range(50):
        _, r, term, trunc, info = env.step(0)
        total += r
        if term:
            break
    assert term and info['crashed'] and total < -5


def test_action_table_matches_robot_limits():
    assert len(ACTIONS) == 5
    assert max(v for _, v, _ in ACTIONS) <= 0.20 + 1e-9                    # Pico firmware en cok 0,20 m/s


def test_latency_delays_commands():
    env = ArenaEnv(random_start=False, moving_obstacles=False, latency=2, sensor_noise=False)
    env.reset(seed=0)
    x0, y0 = env.world.x, env.world.y
    env.step(0); env.step(0)                                               # ilk 2 adim robot durur
    assert (env.world.x, env.world.y) == (x0, y0)
    env.step(0)
    assert (env.world.x, env.world.y) != (x0, y0)


def test_randomize_stays_in_range_and_default_is_clean():
    env = ArenaEnv(randomize=True)
    for seed in range(20):
        env.reset(seed=seed)
        p = env.perturbation
        assert all(0.85 <= s <= 1.15 for s in p['motor_scale']) and p['latency'] in (0, 1, 2)
        assert abs(p['sensor_bias']) <= 0.02 and 0 <= p['sensor_dropout'] <= 0.03
    clean = ArenaEnv()
    clean.reset(seed=0)
    assert clean.perturbation == {'motor_scale': (1.0, 1.0), 'latency': 0, 'sensor_bias': 0.0, 'sensor_dropout': 0.0}


# ---------- senaryolar ----------
def test_default_scenario_equals_default_obstacles():
    meta, obs = load_scenario('default')
    assert same_obstacles(obs, W.default_obstacles())


def test_scenarios_load_and_errors():
    for name in ('default', 'pico2', 'empty'):
        meta, obs = load_scenario(name)
        assert meta['name'] == name
    assert load_scenario('empty')[1] == []
    try:
        load_scenario('yok-boyle-bir-senaryo')
        assert False
    except FileNotFoundError as e:
        assert 'default' in str(e)                                         # hazir olanlari listeler


def test_no_moving_filter_removes_pico_and_bouncers():
    env = ArenaEnv(scenario='pico2', moving_obstacles=False)
    env.reset(seed=0)
    assert not any(isinstance(o, W.PicoBot) for o in env.world.obstacles)
    assert len(env.world.obstacles) == 2                                   # kutu + silindir kaldi


# ---------- Pico robot engeli ----------
def test_picobot_rules_match_firmware():
    src = (ROOT / 'firmware' / 'pico2w' / 'main.py').read_text(encoding='utf-8')
    body = src[src.index('def random_command'):src.index('def main')]
    assert 'center < 0.20' in body and 'min(left, right) < 0.10' in body
    assert 'random.randint(1000, 3000)' in body                            # 1-3 sn
    nums = re.findall(r'\(([0-9.\-]+), ([0-9.\-]+)\)', body[body.index('random.choice'):])
    firmware_cmds = tuple((float(a), float(b)) for a, b in nums[:5])
    assert firmware_cmds == W.PicoBot.COMMANDS
    assert W.PicoBot.CENTER_STOP == 0.20 and W.PicoBot.SIDE_STOP == 0.10 and W.PicoBot.TURN_W == 2.5
    assert f'WHEEL_RADIUS = {W.PICO_WHEEL_RADIUS}' in src and f'WHEEL_SEPARATION = {W.PICO_TRACK}' in src       # mikro robot olculeri


def test_picobot_turns_when_blocked_and_stays_in_arena():
    rng = np.random.default_rng(0)
    p = W.PicoBot(0, 0, 0.0)
    assert p.command([1, 0.1, 1], rng) == (0.0, -2.5)                      # onde engel, left == right -> saga don
    assert p.command([1.0, 0.1, 0.5], rng) == (0.0, 2.5)                   # left > right -> sola don
    w = W.World(obstacles=[W.PicoBot(0.9, 0.0, 0.0)], sensor_noise=False)  # duvara bakiyor, kenarda
    w.place_robot(-0.8, -0.8, 0.0)
    for _ in range(2000):
        w.step(0.0, 0.0, 0.05)
        pb = w.obstacles[0]
        assert abs(pb.x) <= W.HALF - pb.r + 1e-9 and abs(pb.y) <= W.HALF - pb.r + 1e-9


def test_picobot_is_seen_by_learner_and_collides():
    w = W.World(obstacles=[W.PicoBot(0.5, 0.0, math.pi)], sensor_noise=False)
    w.place_robot(0.0, 0.0, 0.0)
    assert w.read_tof()[1] < 0.5                                           # orta sensor Pico'yu gordu
    w.place_robot(0.5 - W.ROBOT_RADIUS - W.PICO_RADIUS + 0.01, 0.0, 0.0)           # daireler ic ice
    assert w.collided()


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
