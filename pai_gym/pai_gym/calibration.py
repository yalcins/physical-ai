"""Kalibrasyon dosyasi (design/calibration.json): gercek olcumlerden gelen simulasyon ayarlari.

ArenaEnv(calibration=True)  ya da  ArenaEnv(calibration='yol/calibration.json')
Yalnizca ArenaEnv'de VARSAYILANDA birakilan ayarlar doldurulur; kodda acikca verdigin deger her zaman kazanir.
Dosyayi tools/calibrate.py uretir (olcum CSV'lerinden).
"""
import json
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / 'design' / 'calibration.json'


def load(path=True):
    p = DEFAULT_PATH if path is True else Path(path)
    return json.loads(p.read_text(encoding='utf-8'))


def apply_calibration(env, path):
    cfg = load(path)
    if tuple(env.motor_scale) == (1.0, 1.0) and cfg.get('motor_scale'):
        env.motor_scale = tuple(cfg['motor_scale'])
    if env.latency == 0 and cfg.get('latency_steps'):
        env.latency = int(cfg['latency_steps'])
    if env.sensor_bias == 0.0 and cfg.get('sensor_bias_m'):
        env.sensor_bias = float(cfg['sensor_bias_m'])
    if env.sensor_dropout == 0.0 and cfg.get('sensor_dropout'):
        env.sensor_dropout = float(cfg['sensor_dropout'])
    if env.robot_radius is None and cfg.get('robot_radius_m'):
        env.robot_radius = float(cfg['robot_radius_m'])
    if env.sensor_noise_std is None and cfg.get('sensor_noise_std_m') is not None:
        env.sensor_noise_std = float(cfg['sensor_noise_std_m'])
    env.pico_cal = dict(cfg.get('pico') or {})
    env.calibration_status = cfg.get('status', '?')
