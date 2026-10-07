"""Gercek olcumlerden simulasyon ve firmware ayarlarini uretir (kalibrasyon).

    python3 tools/calibrate.py                         # design/measurements/*.csv -> design/calibration.json
    python3 tools/calibrate.py --firmware              # + firmware/pico2w/calibration.py
    python3 tools/calibrate.py --dir yol --out dosya.json --dry-run

Olcum dosyalari (hepsi istege bagli; olmayan icin varsayilan degerler kalir). Sutun adlari ilk satirda:
  straight.csv  commanded_v_m_s, seconds, distance_m, heading_change_deg   duz gitme (sola donus +)
  turn.csv      commanded_w_rad_s, seconds_for_360                          yerinde 360 derece donus suresi
  wheel.csv     side (sol|sag), duty (0-1), rad_s                           sabit gucte tekerlek hizi (enkoderden)
  encoder.csv   side (sol|sag), ticks_per_rev                               tekerlegi elle 1 tur cevirince darbe
  tof.csv       true_m, reading_m, valid (1|0, istege bagli)                bilinen mesafede ToF okumalari
  latency.csv   seconds                                                     komuttan harekete gecen sure
  geometry.csv  name, value_mm   (max_extent_from_axle_mm: eksenden en uzak nokta)
  pico.csv      max_speed_m_s, radius_mm                                    gercek Pico: olculen en yuksek hiz ve yaricap
"""
import argparse
import csv
import datetime
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACK_M = 0.115          # tekerlek araligi (world.py ile ayni)
DT = 0.05                # simulasyon adimi
PICO_CMD_SPEED = 0.20    # firmware'deki en yuksek komut hizi


def rows(path):
    if not Path(path).exists():
        return []
    with open(path, encoding='utf-8', newline='') as f:
        return [{k.strip(): v.strip() for k, v in r.items()} for r in csv.DictReader(f) if any(v.strip() for v in r.values())]


def fl(r, k):
    return float(r[k].replace(',', '.'))


def mean(xs):
    return sum(xs) / len(xs)


def calibrate(directory):
    d = Path(directory)
    cfg = json.loads((ROOT / 'design' / 'calibration.json').read_text(encoding='utf-8')) if (ROOT / 'design' / 'calibration.json').exists() else {}
    cfg.setdefault('firmware', {})
    cfg.setdefault('pico', {})
    src, warn = {}, []

    st = rows(d / 'straight.csv')
    if st:
        a = mean([fl(r, 'distance_m') / (fl(r, 'commanded_v_m_s') * fl(r, 'seconds')) for r in st])
        drift = mean([math.radians(fl(r, 'heading_change_deg')) / fl(r, 'distance_m') for r in st])   # rad/m
        sl, sr = a - drift * TRACK_M / 2, a + drift * TRACK_M / 2
        cfg['motor_scale'] = [round(sl, 4), round(sr, 4)]
        cfg['firmware']['motor_scale'] = cfg['motor_scale']
        src['straight.csv'] = len(st)
    tu = rows(d / 'turn.csv')
    if tu:
        b = mean([2 * math.pi / (fl(r, 'commanded_w_rad_s') * fl(r, 'seconds_for_360')) for r in tu])
        cfg['turn_scale'] = round(b, 4)
        src['turn.csv'] = len(tu)
        if st and abs(b - a) > 0.1:
            warn.append(f'Donus olcegi ({b:.2f}) duz gitme olcegiyle ({a:.2f}) %10\'dan fazla farkli: tekerlek kayiyor olabilir.')
    wh = rows(d / 'wheel.csv')
    if wh:
        per = [fl(r, 'rad_s') / fl(r, 'duty') for r in wh]
        cfg['firmware']['max_wheel_rad_s'] = round(statistics.median(per), 2)       # duty = rad_s / bu deger
        src['wheel.csv'] = len(wh)
    en = rows(d / 'encoder.csv')
    if en:
        tl = [fl(r, 'ticks_per_rev') for r in en if r['side'] == 'sol']
        tr = [fl(r, 'ticks_per_rev') for r in en if r['side'] == 'sag']
        cfg['firmware']['ticks_per_rev'] = [round(mean(tl), 2) if tl else None, round(mean(tr), 2) if tr else None]
        src['encoder.csv'] = len(en)
    tf = rows(d / 'tof.csv')
    if tf:
        res = [fl(r, 'reading_m') - fl(r, 'true_m') for r in tf if r.get('valid', '1') not in ('0', '')]
        cfg['sensor_bias_m'] = round(mean(res), 4)
        cfg['sensor_noise_std_m'] = round(statistics.pstdev(res), 4) if len(res) > 1 else cfg.get('sensor_noise_std_m', 0.01)
        if 'valid' in tf[0]:
            cfg['sensor_dropout'] = round(1 - mean([1.0 if r['valid'] not in ('0', '') else 0.0 for r in tf]), 4)
        src['tof.csv'] = len(tf)
    la = rows(d / 'latency.csv')
    if la:
        cfg['latency_steps'] = int(round(mean([fl(r, 'seconds') for r in la]) / DT))
        src['latency.csv'] = len(la)
    ge = rows(d / 'geometry.csv')
    if ge:
        ext = [fl(r, 'value_mm') for r in ge if r['name'] == 'max_extent_from_axle_mm']
        if ext:
            cfg['robot_radius_m'] = round(max(ext) / 1000.0, 4)
        src['geometry.csv'] = len(ge)
    pi = rows(d / 'pico.csv')
    if pi:
        cfg['pico']['speed_scale'] = round(mean([fl(r, 'max_speed_m_s') for r in pi]) / PICO_CMD_SPEED, 4)
        if 'radius_mm' in pi[0]:
            cfg['pico']['radius_m'] = round(mean([fl(r, 'radius_mm') for r in pi]) / 1000.0, 4)
        src['pico.csv'] = len(pi)
    if src:
        cfg['status'] = 'measured'
        cfg['note'] = 'Gercek olcumlerden uretildi (tools/calibrate.py).'
        cfg['sources'] = src
        cfg['date'] = datetime.date.today().isoformat()
    cfg['warnings'] = warn
    return cfg


FIRMWARE_TEMPLATE = '''"""OTOMATIK URETILDI (tools/calibrate.py); elle degistirme. Kaynak: design/calibration.json ({date})."""
MAX_WHEEL_RAD_S = {max_w}
MOTOR_SCALE_L = {sl}
MOTOR_SCALE_R = {sr}
TICKS_PER_REV_L = {tl}
TICKS_PER_REV_R = {tr}
'''


def write_firmware(cfg, path):
    fw = cfg['firmware']
    sl, sr = fw.get('motor_scale', [1.0, 1.0])
    tl, tr = fw.get('ticks_per_rev', [None, None])
    Path(path).write_text(FIRMWARE_TEMPLATE.format(date=cfg.get('date', 'nominal'), max_w=fw.get('max_wheel_rad_s', 31.0), sl=sl, sr=sr, tl=tl, tr=tr), encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--dir', default=str(ROOT / 'design' / 'measurements'))
    p.add_argument('--out', default=str(ROOT / 'design' / 'calibration.json'))
    p.add_argument('--firmware', action='store_true', help='firmware/pico2w/calibration.py de yaz')
    p.add_argument('--dry-run', action='store_true', help='dosya yazma, sonucu goster')
    a = p.parse_args()
    cfg = calibrate(a.dir)
    print(json.dumps(cfg, ensure_ascii=False, indent=2))
    for w in cfg['warnings']:
        print('UYARI:', w)
    if not a.dry_run:
        Path(a.out).write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
        (ROOT / 'docs' / 'data' / 'calibration.json').write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')   # site okur
        if a.firmware:
            write_firmware(cfg, ROOT / 'firmware' / 'pico2w' / 'calibration.py')
        print('yazildi:', a.out)


if __name__ == '__main__':
    main()
