"""Kalibrasyon hattini sentetik 'olcumlerle' sinar: bilinen gercek degerler -> CSV -> calibrate.py -> ArenaEnv."""
import csv
import json
import math
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'pai_gym'), str(ROOT / 'tools')]

import numpy as np  # noqa: E402
import calibrate  # noqa: E402
from pai_gym.arena_env import ArenaEnv  # noqa: E402
from pai_gym.world import PicoBot  # noqa: E402

SL, SR, L = 0.90, 1.05, 0.115


def write(d, name, header, rows):
    with open(Path(d) / name, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def make_measurements(d):
    a, drift = (SL + SR) / 2, (SR - SL) / L                     # sentetik gercek: v = a*v_komut, sapma = (sr-sl)/L rad/m
    rows = []
    for v, t in ((0.2, 5.0), (0.15, 4.0), (0.2, 6.0)):
        dist = a * v * t
        rows.append([v, t, round(dist, 5), round(math.degrees(drift * dist), 5)])
    write(d, 'straight.csv', ['commanded_v_m_s', 'seconds', 'distance_m', 'heading_change_deg'], rows)
    write(d, 'turn.csv', ['commanded_w_rad_s', 'seconds_for_360'], [[2.5, round(2 * math.pi / (2.5 * a), 4)]])
    write(d, 'wheel.csv', ['side', 'duty', 'rad_s'], [['sol', 0.5, 15.0], ['sag', 0.5, 16.0], ['sol', 1.0, 31.0]])
    write(d, 'encoder.csv', ['side', 'ticks_per_rev'], [['sol', 700], ['sol', 702], ['sag', 698]])
    rng = np.random.default_rng(1)
    res = rng.normal(0.02, 0.005, 400)
    rows = [[t, round(t + r, 5), 1] for t, r in zip(np.tile([0.1, 0.5, 1.0, 2.0], 100), res)] + [[1.0, 4.0, 0]] * 4
    write(d, 'tof.csv', ['true_m', 'reading_m', 'valid'], rows)
    write(d, 'latency.csv', ['seconds'], [[0.11], [0.09]])
    write(d, 'geometry.csv', ['name', 'value_mm'], [['max_extent_from_axle_mm', 96]])
    write(d, 'pico.csv', ['max_speed_m_s', 'radius_mm'], [[0.16, 74], [0.16, 76]])


def test_recovers_synthetic_truth():
    with tempfile.TemporaryDirectory() as d:
        make_measurements(d)
        cfg = calibrate.calibrate(d)
    assert abs(cfg['motor_scale'][0] - SL) < 1e-3 and abs(cfg['motor_scale'][1] - SR) < 1e-3
    assert cfg['firmware']['max_wheel_rad_s'] == 30.0 or abs(cfg['firmware']['max_wheel_rad_s'] - 30.0) <= 1.0     # medyan(30, 32, 31)
    assert cfg['firmware']['ticks_per_rev'] == [701.0, 698.0]
    assert abs(cfg['sensor_bias_m'] - 0.02) < 0.002 and abs(cfg['sensor_noise_std_m'] - 0.005) < 0.002
    assert 0.005 < cfg['sensor_dropout'] < 0.02                  # 4 / 404 = %1
    assert cfg['latency_steps'] == 2
    assert cfg['robot_radius_m'] == 0.096
    assert abs(cfg['pico']['speed_scale'] - 0.8) < 1e-9 and abs(cfg['pico']['radius_m'] - 0.075) < 1e-9
    assert cfg['status'] == 'measured' and 'straight.csv' in cfg['sources']
    assert not cfg['warnings']                                   # donus ile duz gitme olcegi tutarli


def test_warns_on_inconsistent_turn_scale():
    with tempfile.TemporaryDirectory() as d:
        make_measurements(d)
        write(d, 'turn.csv', ['commanded_w_rad_s', 'seconds_for_360'], [[2.5, 4.0]])    # cok yavas donus
        cfg = calibrate.calibrate(d)
    assert cfg['warnings']


def test_env_uses_calibration_and_explicit_kwargs_win():
    with tempfile.TemporaryDirectory() as d:
        make_measurements(d)
        cfg = calibrate.calibrate(d)
        path = Path(d) / 'cal.json'
        path.write_text(json.dumps(cfg))
        env = ArenaEnv(calibration=str(path), scenario='pico2')
        env.reset(seed=0)
        pt = env.perturbation
        assert pt['motor_scale'] == tuple(cfg['motor_scale']) and pt['latency'] == 2
        assert abs(env.world.robot_radius - 0.096) < 1e-9 and abs(env.world.sensor_noise_std - cfg['sensor_noise_std_m']) < 1e-9
        picos = [o for o in env.world.obstacles if isinstance(o, PicoBot)]
        assert picos and all(abs(p.speed_scale - 0.8) < 1e-9 and abs(p.r - 0.075) < 1e-9 for p in picos)
        env2 = ArenaEnv(calibration=str(path), latency=1)        # acik deger kazanir
        env2.reset(seed=0)
        assert env2.perturbation['latency'] == 1


def test_nominal_calibration_changes_nothing():
    def run(**kw):
        env = ArenaEnv(frames=3, **kw)
        obs, _ = env.reset(seed=4)
        out = []
        for i in range(80):
            obs, r, *_ = env.step(i % 5)
            out.append((round(r, 6), tuple(np.round(obs, 6))))
        return out
    assert run() == run(calibration=True)                        # design/calibration.json nominal iken davranis ayni


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
