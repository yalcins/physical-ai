"""Sanal tasarimin (design/design.py) mekanik tutarlilik testleri. Calistir: python3 tests/test_design.py"""
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'design'))
import design as D  # noqa: E402


def test_no_collisions_and_no_cut_problems():
    for v in D.VARIANTS:
        d = D.build(v)
        assert D.collisions(d) == [], (v, D.collisions(d))
        assert D.hole_problems(d['plate_bottom']) == [], (v, 'alt plaka')
        assert D.hole_problems(d['plate_top']) == [], (v, 'ust plaka')


def test_matches_simulation_geometry():
    d = D.build('pico')
    by = {p['name']: p for p in d['parts']}
    # tekerlek: simulasyondaki cap ve aralik
    assert abs((by['wheel_l']['x1'] - by['wheel_l']['x0']) - 43.0) < 1e-6
    centers = [(by[f'wheel_{s}']['y0'] + by[f'wheel_{s}']['y1']) / 2 for s in 'lr']
    assert abs(centers[0] - 57.5) < 1e-6 and abs(centers[1] + 57.5) < 1e-6          # iz genisligi 115
    # ToF acikliklari world.py'deki konumlarda; yukseklik 51.5
    for t in d['tofs']:
        m = by[f'tof_{t["name"]}']
        assert abs((m['z0'] + m['z1']) / 2 - D.TOF_Z) < 1e-6
    assert abs(D.TOF_Z - 51.5) < 1e-6
    # BILINEN FARK: tasarimin en uzak kosesi (arka kose) eksenden ~96 mm; simulasyonun carpisma dairesi 75 mm.
    # Bu, tasarimin simulasyondan buyuk oldugunu gosterir (bkz. site bulgusu 'carpisma-yaricapi'). Burada yalnizca sinirlari sabitliyoruz.
    r = max(math.hypot(x, y) for x in (D.BODY_X0, D.BODY_X1) for y in (-D.BODY_HALF_W, D.BODY_HALF_W))
    assert 90 < r < 100
    sim_r = 75.0
    assert r > sim_r
    front = max(math.hypot(D.BODY_X1, D.BODY_HALF_W), 0)
    assert front < sim_r                                         # on kisim simulasyon dairesinin icinde


def test_decks_and_heights():
    for v in D.VARIANTS:
        d = D.build(v)
        e = D.envelope(d)
        assert e['z'][0] == 0.0                                 # zemine degen en alt nokta (tekerlek/teker)
        # motorlar plakanin altina sigar: motor tepesi = alt plaka tabani
        by = {p['name']: p for p in d['parts']}
        assert abs(by['motor_l']['z1'] - by['plate_bottom']['z0']) < 1e-6
        # alt kattaki en yuksek parca ust plakanin altina degmez
        low = max(p['z1'] for p in d['parts'] if p['z0'] >= D.PLATE_B_Z1 - 1e-6 and p['z1'] <= D.PLATE_T_Z0 + 1e-6 and not p['name'].startswith(('standoff', 'tof')))
        assert low < D.PLATE_T_Z0
    assert D.envelope(D.build('pico'))['z'][1] < 62.0           # simulasyondaki govde tepesi 61.5
    assert D.envelope(D.build('pi4'))['z'][1] > D.envelope(D.build('pico'))['z'][1]


def test_board_holes_match_datasheets():
    # Pico: 47 x 11.4 mm; Pi 4: 58 x 49 mm
    h = D.PICO['holes']
    assert abs(max(x for x, _ in h) - min(x for x, _ in h) - 47.0) < 1e-9 and abs(max(y for _, y in h) - min(y for _, y in h) - 11.4) < 1e-9
    h = D.PI4['holes']
    assert abs(max(x for x, _ in h) - min(x for x, _ in h) - 58.0) < 1e-9 and abs(max(y for _, y in h) - min(y for _, y in h) - 49.0) < 1e-9


def test_standoffs_hit_both_plates():
    d = D.build('pico')
    holes_b = {(round(x, 3), round(y, 3)) for x, y, _ in d['plate_bottom']['holes']}
    holes_t = {(round(x, 3), round(y, 3)) for x, y, _ in d['plate_top']['holes']}
    for x, y in D.STANDOFFS:
        assert (x, y) in holes_b and (x, y) in holes_t


def test_tof_slots_face_sensor_directions():
    d = D.build('pico')
    slots = [s for s in d['plate_bottom']['slots'] if abs(s[2] - (D.TOF_BR_W + D.SLOT_FIT)) < 1e-9]
    assert len(slots) == 3
    angs = sorted(round((s[4] - 90 + 180) % 360 - 180) for s in slots)
    assert angs == [-30, 0, 30]                                  # yuvalar sensor yonlerine dik


def test_openscad_exports_match_plate_size():
    if not shutil.which('openscad'):
        return
    d = D.build('pico')
    with tempfile.TemporaryDirectory() as t:
        D.write_scad('pico', t)
        scad = Path(t) / 'robot.scad'
        scad.write_text(f'include <{t}/pico.scad>\ninclude <{ROOT}/design/lib.scad>\nrender_part("plate_bottom_2d");\n')
        out = Path(t) / 'p.svg'
        subprocess.run(['openscad', '-o', str(out), str(scad)], capture_output=True, check=True)
        head = out.read_text()[:300]
    o = d['plate_bottom']['outline']
    assert f'width="{o["x1"] - o["x0"]:g}mm"' in head and f'height="{o["y1"] - o["y0"]:g}mm"' in head


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
