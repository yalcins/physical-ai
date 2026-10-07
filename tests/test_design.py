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
    sys.path.insert(0, str(ROOT / 'pai_gym'))
    from pai_gym import world as W
    # --- buyuk robot (ogrenen, Pi 4): world.py'nin tekerlek/sensor sabitleri ---
    d = D.build('pi4')
    S = d['spec']
    by = {p['name']: p for p in d['parts']}
    assert abs((by['wheel_l']['x1'] - by['wheel_l']['x0']) - 2 * W.WHEEL_RADIUS * 1000) < 1e-6
    assert abs(S['track'] - W.WHEEL_SEPARATION * 1000) < 1e-6
    centers = [(by[f'wheel_{s}']['y0'] + by[f'wheel_{s}']['y1']) / 2 for s in 'lr']
    assert abs(centers[0] - S['track'] / 2) < 1e-6 and abs(centers[1] + S['track'] / 2) < 1e-6
    for t in d['tofs']:
        m = by[f'tof_{t["name"]}']
        assert abs((m['z0'] + m['z1']) / 2 - S['tof_z']) < 1e-6
    assert abs(S['tof_z'] - 51.5) < 1e-6
    # BILINEN FARK: buyuk robotun arka kosesi eksenden ~96 mm, simulasyon dairesi 75 mm (bulgu 'carpisma-yaricapi')
    r = max(math.hypot(x, y) for x in (S['plate_b'][0], S['plate_b'][1]) for y in (-S['half_w'], S['half_w']))
    assert 90 < r < 100 and r > W.ROBOT_RADIUS * 1000
    # --- MIKRO Pico: simulasyondaki hareketli engel (PicoBot) sabitleri ---
    d = D.build('pico')
    S = d['spec']
    by = {p['name']: p for p in d['parts']}
    assert abs((by['wheel_l']['x1'] - by['wheel_l']['x0']) / 2 - W.PICO_WHEEL_RADIUS * 1000) < 1e-6
    assert abs(S['track'] - W.PICO_TRACK * 1000) < 1e-6
    # sensor aciklik konumlari (referans noktasi = iki tekerlegin orta noktasi) PICO_TOF ile ayni
    sim = {n: (f * 1000, s * 1000, math.degrees(a)) for n, f, s, a in W.PICO_TOF}
    for n, fwd, side, ang in S['tofs']:
        assert all(abs(u - v) < 1e-6 for u, v in zip(sim[n], (fwd, side, ang))), n
    assert abs(sum(S['wheel_x']) / 2) < 1e-9                    # tekerlek merkezlerinin orta noktasi = referans
    # en uzak nokta (referanstan): plaka kosesi / tekerlek -> PICO_RADIUS'u asmamali (yuvarlak kose payi ile)
    far = 0.0
    for p in d['parts']:
        if p['name'].startswith(('plate', 'wheel')):
            far = max(far, max(math.hypot(x, y) for x in (p['x0'], p['x1']) for y in (p['y0'], p['y1'])))
    assert W.PICO_RADIUS * 1000 >= far - 2.0 and W.PICO_RADIUS * 1000 <= far + 4.0, (far, W.PICO_RADIUS)


def test_decks_and_heights():
    for v in D.VARIANTS:
        d = D.build(v)
        S = d['spec']
        e = D.envelope(d)
        assert e['z'][0] == 0.0                                 # zemine degen en alt nokta (tekerlek/teker)
        by = {p['name']: p for p in d['parts']}
        assert abs(by['motor_l']['z1'] - by['plate_bottom']['z0']) < 1e-6      # motorlar plakanin altina sigar
        top_z = S['plate_t_z0']
        low = max(p['z1'] for p in d['parts'] if p['z0'] >= S['plate_b_z1'] - 1e-6 and p['z1'] <= top_z + 1e-6 and not p['name'].startswith(('standoff', 'tof')))
        assert low < top_z                                      # alt kattaki en yuksek parca ust plakaya degmez
    assert D.envelope(D.build('pico'))['z'][1] < 45.0           # mikro robot: 45 mm'nin altinda
    assert D.envelope(D.build('pi4'))['z'][1] > D.envelope(D.build('pico'))['z'][1]
    micro = D.envelope(D.build('pico'))
    assert micro['x'][1] - micro['x'][0] < 75 and micro['y'][1] - micro['y'][0] < 75        # mikro: tekerlekler dahil 75 mm'nin altinda


def test_board_holes_match_datasheets():
    # Pico: 47 x 11.4 mm; Pi 4: 58 x 49 mm
    h = D.PICO['holes']
    assert abs(max(x for x, _ in h) - min(x for x, _ in h) - 47.0) < 1e-9 and abs(max(y for _, y in h) - min(y for _, y in h) - 11.4) < 1e-9
    h = D.PI4['holes']
    assert abs(max(x for x, _ in h) - min(x for x, _ in h) - 58.0) < 1e-9 and abs(max(y for _, y in h) - min(y for _, y in h) - 49.0) < 1e-9


def test_standoffs_hit_both_plates():
    for v in D.VARIANTS:
        d = D.build(v)
        holes_b = {(round(x, 3), round(y, 3)) for x, y, _ in d['plate_bottom']['holes']}
        holes_t = {(round(x, 3), round(y, 3)) for x, y, _ in d['plate_top']['holes']}
        for x, y in d['spec']['standoffs']:
            assert (x, y) in holes_b and (x, y) in holes_t


def test_tof_slots_face_sensor_directions():
    for v in D.VARIANTS:
        d = D.build(v)
        S = d['spec']
        slots = [s for s in d['plate_bottom']['slots'] if abs(s[2] - (S['tof_br_w'] + S['slot_fit'])) < 1e-9]
        assert len(slots) == 3
        angs = sorted(round((s[4] - 90 + 180) % 360 - 180) for s in slots)
        assert angs == [-30, 0, 30]                              # yuvalar sensor yonlerine dik


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
    import re as _re
    w, h = (float(v) for v in _re.search(r'width="([0-9.]+)mm" height="([0-9.]+)mm"', head).groups())
    # OpenSCAD SVG sinirini tam sayiya yuvarlar: gercek olcuden en cok 1 mm buyuk olabilir
    assert 0 <= w - (o['x1'] - o['x0']) <= 1.0 and 0 <= h - (o['y1'] - o['y0']) <= 1.0


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
