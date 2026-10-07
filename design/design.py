"""Robotun TEK KAYNAKLI sanal tasarimi (v0): plakalar, delikler, parcalar, carpisma kontrolu.

Buradan uretilenler:
  - generated/<varyant>.scad  : OpenSCAD icin diziler (3B model, lazer kesim SVG/DXF, STL)
  - BOM (parca listesi) ve kablolama verisi (tools/design/build_all.py kullanir)
Olculer milimetre; robot koordinati: x ileri, y sol, z yukari, z=0 zemin, x=0 tekerlek ekseni.

Her parcanin `verified` alani var:
  True  = sartnamede / datasheet'te belli (tekerlek, Pico ve Pi 4 delik duzeni, AA pil boyutu...)
  False = VARSAYIM (gercek parca gelince OLC ve burada degistir; her sey yeniden uretilir)
Simulasyonla ortak olanlar (tekerlek, gövde ayak izi 130x90, ToF konumlari) world.py ve URDF'ten okunur.
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pai_gym'))
from pai_gym import world as W  # noqa: E402

VARIANTS = ('pico', 'pi4')      # pico = MIKRO robot (65 x 55 mm), pi4 = buyuk robot
MM = 1000.0

# ---------------- Simulasyonla ortak (dogrulanmis) ----------------
WHEEL_D = 2 * W.WHEEL_RADIUS * MM          # 43
WHEEL_W = 19.0
TRACK = W.WHEEL_SEPARATION * MM            # 115
AXLE_Z = W.WHEEL_RADIUS * MM               # 21.5
BODY_X0, BODY_X1, BODY_HALF_W = -85.0, 48.0, 45.0   # on kenar 45 -> 48: orta ToF dikmesinin yuvasi icin et payi
CASTER_X, CASTER_R = -65.0, 10.7
TOF_Z = AXLE_Z + 30.0                      # 51.5 (URDF)
TOFS = [(n, f * MM, s * MM, math.degrees(a)) for n, f, s, a in W.TOF_SENSORS]   # (ad, ileri, yan, aci)

# ---------------- Tasarim secimleri (KARAR ONERISI: lazer kesim, 3 mm) ----------------
T = 3.0                                    # plaka kalinligi (3 mm kontrplak/MDF/akrilik)
MOTOR_W, MOTOR_H = 12.0, 10.0              # N20: 12 genislik x 10 yukseklik (standart; uzunluk varsayim)
MOTOR_Y_IN, MOTOR_Y_OUT = 12.0, 46.0       # motor govdesi y araligi (uzunluk 34 = VARSAYIM)
PLATE_B_Z0 = AXLE_Z + MOTOR_H / 2          # 26.5: motorlar plakanin altina asilir
PLATE_B_Z1 = PLATE_B_Z0 + T                # 29.5
DECK_GAP = 20.0
PLATE_T_Z0 = PLATE_B_Z1 + DECK_GAP         # 49.5
PLATE_T_Z1 = PLATE_T_Z0 + T                # 52.5
TOP_X0, TOP_X1 = -85.0, 28.0               # ust plaka on kenari ToF'lardan once biter
STANDOFFS = [(23.0, 38.0), (23.0, -38.0), (-80.0, 38.0), (-80.0, -38.0)]
STANDOFF_D, HOLE_M3 = 6.0, 3.2
CORNER_R = 6.0
SLOT_FIT = 0.2                             # kesim toleransi (plaka kalinligina eklenir)

# ToF dikmeleri
TOF_BR_W, TOF_BR_Z1 = 20.0, 60.5           # dikme genisligi; ustu (modul 18 mm, merkez 51.5)
TOF_MOD = (13.0, 18.0, 2.0)                # genislik, yukseklik, kalinlik (VARSAYIM)
TOF_APERTURE_BACK = T / 2 + 2.0 + 0.0      # dikme orta-yuzeyi -> sensor acikligi

# Kart olculeri (dogrulanmis: Pico 2 W ve Pi 4 delik duzeni)
PICO = dict(size=(51.0, 21.0), holes=[(2.0, 4.8), (2.0, 16.2), (49.0, 4.8), (49.0, 16.2)], hole_d=2.1, thick=1.0)
PI4 = dict(size=(85.0, 56.0), holes=[(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)], hole_d=2.75, thick=1.4, height=17.0)


def rrect(x0, x1, y0, y1):
    return dict(x0=x0, x1=x1, y0=y0, y1=y1, r=CORNER_R)


def tof_geometry():
    """Her ToF icin: dikme merkezi, aci. Dikme, sensor acikliginin 'arkasinda' durur."""
    out = []
    for name, fwd, side, ang in TOFS:
        a = math.radians(ang)
        back = TOF_APERTURE_BACK
        cx, cy = fwd - back * math.cos(a), side - back * math.sin(a)
        out.append(dict(name=name, cx=cx, cy=cy, ang=ang, ax=fwd, ay=side))
    return out


def box(name, x0, x1, y0, y1, z0, z1, color, verified, group, note=''):
    return dict(kind='box', name=name, x0=x0, x1=x1, y0=y0, y1=y1, z0=z0, z1=z1, color=color, verified=verified, group=group, note=note)


def rbox(name, cx, cy, w, d, z0, z1, ang, color, verified, group, note=''):
    """z etrafinda donmus kutu: w = acinin dik yonundeki genislik, d = kalinlik (acinin yonunde)."""
    a = math.radians(ang)
    ex = abs(w / 2 * math.sin(a)) + abs(d / 2 * math.cos(a))
    ey = abs(w / 2 * math.cos(a)) + abs(d / 2 * math.sin(a))
    return dict(kind='rbox', name=name, cx=cx, cy=cy, w=w, d=d, z0=z0, z1=z1, ang=ang, x0=cx - ex, x1=cx + ex, y0=cy - ey, y1=cy + ey,
                color=color, verified=verified, group=group, note=note)


def cylz(name, cx, cy, d, z0, z1, color, verified, group, note=''):
    return dict(kind='cylz', name=name, cx=cx, cy=cy, d=d, x0=cx - d / 2, x1=cx + d / 2, y0=cy - d / 2, y1=cy + d / 2, z0=z0, z1=z1,
                color=color, verified=verified, group=group, note=note)


def cyly(name, cx, cz, y0, y1, d, color, verified, group, note=''):
    return dict(kind='cyly', name=name, cx=cx, cz=cz, d=d, x0=cx - d / 2, x1=cx + d / 2, y0=min(y0, y1), y1=max(y0, y1), z0=cz - d / 2, z1=cz + d / 2,
                color=color, verified=verified, group=group, note=note)


def sphere(name, cx, cy, cz, r, color, verified, group, note=''):
    return dict(kind='sphere', name=name, cx=cx, cy=cy, cz=cz, r=r, x0=cx - r, x1=cx + r, y0=cy - r, y1=cy + r, z0=cz - r, z1=cz + r,
                color=color, verified=verified, group=group, note=note)


def board_holes(origin, spec):
    ox, oy = origin
    return [(ox + hx, oy + hy, spec['hole_d'] + 0.3) for hx, hy in spec['holes']]


# build_pcb/ drawings/ build_all gibi araclar varyanta ozgu olculeri buradan (des['spec']) okur
BIG_SPEC = dict(name='Büyük robot (Raspberry Pi 4)', T=T, plate_b=(BODY_X0, BODY_X1, BODY_HALF_W), top=(TOP_X0, TOP_X1, BODY_HALF_W), top_is_pcb=False,
                plate_b_z0=PLATE_B_Z0, plate_b_z1=PLATE_B_Z1, plate_t_z0=PLATE_T_Z0, plate_t_z1=PLATE_T_Z1, deck_gap=DECK_GAP, axle_z=AXLE_Z,
                wheel_d=WHEEL_D, wheel_w=WHEEL_W, track=TRACK, wheel_x=(0.0, 0.0), caster_x=CASTER_X, standoffs=STANDOFFS, tof_z=TOF_Z,
                tof_br_w=TOF_BR_W, tof_br_z1=TOF_BR_Z1, slot_fit=SLOT_FIT, tofs=TOFS, half_w=BODY_HALF_W, sim='learner')


def _build_big(variant):
    """Buyuk robot (Pi 4) gövdesi: 133 x 90 mm, O43 tekerlek. (Eski 'pico' sürümü de buradaydı; mikro Pico artik build_micro.)"""
    assert variant in ('pi4',)
    tofs = tof_geometry()
    parts, bottom_holes, bottom_slots, bottom_marks = [], [], [], []
    top_holes, top_slots, top_marks = [], [], []

    # ---- plakalar ----
    bottom = rrect(BODY_X0, BODY_X1, -BODY_HALF_W, BODY_HALF_W)
    top = rrect(TOP_X0, TOP_X1, -BODY_HALF_W, BODY_HALF_W)
    for x, y in STANDOFFS:
        bottom_holes.append((x, y, HOLE_M3))
        top_holes.append((x, y, HOLE_M3))
        parts.append(cylz(f'standoff_{len(parts)}', x, y, STANDOFF_D, PLATE_B_Z1, PLATE_T_Z0, '#c0c0c0', True, 'mekanik', 'M3 x 20 ara parca'))
    # motor kablo bagi yuvalari (her motor icin 2 cift)
    for s in (1, -1):
        for yy in (18.0, 38.0):
            for xx in (-8.0, 8.0):
                bottom_slots.append((xx, s * yy, 3.4, 1.8, 0.0))
    # sarhos teker: 2 delik
    for yy in (8.0, -8.0):
        bottom_holes.append((CASTER_X, yy, HOLE_M3))
    # ToF dikme yuvalari
    for t in tofs:
        bottom_slots.append((t['cx'], t['cy'], TOF_BR_W + SLOT_FIT, T + SLOT_FIT, t['ang'] + 90.0))

    # ---- ortak parcalar ----
    parts.append(box('plate_bottom', BODY_X0, BODY_X1, -BODY_HALF_W, BODY_HALF_W, PLATE_B_Z0, PLATE_B_Z1, '#d9b77e', True, 'mekanik', '3 mm lazer kesim'))
    parts.append(box('plate_top', TOP_X0, TOP_X1, -BODY_HALF_W, BODY_HALF_W, PLATE_T_Z0, PLATE_T_Z1, '#d9b77e', True, 'mekanik', '3 mm lazer kesim'))
    for s, nm in ((1, 'l'), (-1, 'r')):
        parts.append(cyly(f'wheel_{nm}', 0.0, AXLE_Z, s * (TRACK / 2 - WHEEL_W / 2), s * (TRACK / 2 + WHEEL_W / 2), WHEEL_D, '#2b2b2b', True, 'tahrik', 'Ø43 x 19'))
        parts.append(box(f'motor_{nm}', -MOTOR_W / 2, MOTOR_W / 2, min(s * MOTOR_Y_IN, s * MOTOR_Y_OUT), max(s * MOTOR_Y_IN, s * MOTOR_Y_OUT),
                         AXLE_Z - MOTOR_H / 2, AXLE_Z + MOTOR_H / 2, '#7d8aa0', False, 'tahrik', 'JGA12-N20B: genislik/yukseklik standart, uzunluk varsayim'))
    parts.append(sphere('caster_ball', CASTER_X, 0.0, CASTER_R, CASTER_R, '#bdbdbd', False, 'tahrik', 'bilyeli sarhos teker (model secilecek)'))
    for yy in (8.0, -8.0):
        parts.append(cylz(f'caster_spacer_{"p" if yy > 0 else "n"}', CASTER_X, yy, 6.0, 2 * CASTER_R, PLATE_B_Z0, '#c0c0c0', False, 'mekanik', 'teker yuksekligine gore ara parca'))
    for t, (_n, _f, _s, _a) in zip(tofs, TOFS):
        nm = t['name']
        parts.append(rbox(f'tof_bracket_{nm}', t['cx'], t['cy'], TOF_BR_W, T, PLATE_B_Z0, TOF_BR_Z1, t['ang'], '#d9b77e', True, 'algi', 'lazer kesim dikme'))
        a = math.radians(t['ang'])
        mcx, mcy = t['ax'] - TOF_MOD[2] / 2 * math.cos(a), t['ay'] - TOF_MOD[2] / 2 * math.sin(a)
        parts.append(rbox(f'tof_{nm}', mcx, mcy, TOF_MOD[0], TOF_MOD[2], TOF_Z - TOF_MOD[1] / 2, TOF_Z + TOF_MOD[1] / 2, t['ang'], '#2f6fbd', False, 'algi', 'TOF400C modul boyutu varsayim'))

    if variant == 'pico':
        # alt kat: pil
        parts.append(box('battery', -83.0, -25.0, -26.0, 26.0, PLATE_B_Z1, PLATE_B_Z1 + 16.0, '#4a4a4a', False, 'guc', '4xAA yuva (tek sira) boyutu varsayim: 58 x 52 x 16'))
        for yy in (-31.0, 31.0):
            bottom_slots.append((-54.0, yy, 20.0, 3.0, 90.0))          # pil bagi
        bottom_marks.append((-83.0, -26.0, -25.0, 26.0))
        # ust kat: Pico, TB6612, MPU6050, regulator
        px0, py0 = -1.0 - PICO['size'][0] / 2, -PICO['size'][1] / 2
        top_holes += board_holes((px0, py0), PICO)
        for (hx, hy) in PICO['holes']:
            parts.append(cylz(f'pico_spacer_{len(parts)}', px0 + hx, py0 + hy, 4.0, PLATE_T_Z1, PLATE_T_Z1 + 4.0, '#c0c0c0', True, 'mekanik', 'M2 x 4 ara parca'))
        parts.append(box('pico', px0, px0 + PICO['size'][0], py0, py0 + PICO['size'][1], PLATE_T_Z1 + 4.0, PLATE_T_Z1 + 4.0 + PICO['thick'] + 1.0, '#2e8b57', True, 'kontrol', 'Pico 2 W 51 x 21'))
        for nm, (cx, cy, w, d, h, col, ver) in {'tb6612': (-32.0, 22.0, 20.0, 20.0, 3.0, '#7b4fc9', False), 'mpu6050': (-28.0, -22.0, 20.0, 16.0, 3.0, '#d9822b', False),
                                                'regulator': (-62.0, -20.0, 15.0, 17.0, 4.0, '#e6d34a', False)}.items():
            parts.append(box(nm, cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2, PLATE_T_Z1, PLATE_T_Z1 + h, col, ver, 'kontrol', 'modul boyutu varsayim (cift yuzlu bantla)'))
            top_marks.append((cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2))
        top_slots.append((-70.0, 0.0, 8.0, 20.0, 0.0))                 # kablo gecidi
    else:
        # alt kat: guc modulu (KARAR BEKLIYOR), TB6612, MPU6050
        parts.append(box('power_placeholder', -83.0, -13.0, -20.0, 20.0, PLATE_B_Z1, PLATE_B_Z1 + 18.0, '#4a4a4a', False, 'guc', 'GUC KAYNAGI KARARI BEKLIYOR: 70 x 40 x 18 yer tutucu'))
        bottom_marks.append((-83.0, -20.0, -13.0, 20.0))
        for nm, (cx, cy, w, d, h, col) in {'tb6612': (2.0, 22.0, 20.0, 20.0, 3.0, '#7b4fc9'), 'mpu6050': (2.0, -22.0, 20.0, 16.0, 3.0, '#d9822b')}.items():
            parts.append(box(nm, cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2, PLATE_B_Z1, PLATE_B_Z1 + h, col, False, 'kontrol', 'modul boyutu varsayim (cift yuzlu bantla)'))
            bottom_marks.append((cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2))
        # ust kat: Pi 4
        px0, py0 = -20.0 - PI4['size'][0] / 2, -PI4['size'][1] / 2
        top_holes += board_holes((px0, py0), PI4)
        for (hx, hy) in PI4['holes']:
            parts.append(cylz(f'pi4_spacer_{len(parts)}', px0 + hx, py0 + hy, 5.0, PLATE_T_Z1, PLATE_T_Z1 + 5.0, '#c0c0c0', True, 'mekanik', 'M2.5 x 5 ara parca'))
        parts.append(box('pi4', px0, px0 + PI4['size'][0], py0, py0 + PI4['size'][1], PLATE_T_Z1 + 5.0, PLATE_T_Z1 + 5.0 + PI4['height'], '#2e8b57', True, 'kontrol', 'Raspberry Pi 4 85 x 56 x 17'))
        top_slots.append((-76.0, 0.0, 6.0, 14.0, 0.0))

    # ---- ad cakismalarini onle ----
    seen = set()
    for p in parts:
        base, k = p['name'], 1
        while p['name'] in seen:
            k += 1
            p['name'] = f'{base}_{k}'
        seen.add(p['name'])

    return dict(variant=variant, tofs=tofs, spec=BIG_SPEC,
                plate_bottom=dict(outline=bottom, holes=bottom_holes, slots=bottom_slots, marks=bottom_marks, z0=PLATE_B_Z0, z1=PLATE_B_Z1),
                plate_top=dict(outline=top, holes=top_holes, slots=top_slots, marks=top_marks, z0=PLATE_T_Z0, z1=PLATE_T_Z1),
                parts=parts)


# ---------------- kontroller ----------------
def overlaps(a, b, eps=0.05):
    """Iki parcanin sinir kutulari ic ice mi (eps mm'den fazla)?"""
    return (min(a['x1'], b['x1']) - max(a['x0'], b['x0']) > eps and min(a['y1'], b['y1']) - max(a['y0'], b['y0']) > eps
            and min(a['z1'], b['z1']) - max(a['z0'], b['z0']) > eps)


# izinli ic ice gecmeler: plakadaki delik/yuvadan gecen parcalar (plaka ile sinir kutusu ortusur)
ALLOWED = [('tof_bracket', 'plate_bottom'), ('tof_bracket', 'tof_'), ('standoff', 'plate'), ('pico_spacer', 'plate'), ('pi4_spacer', 'plate'), ('caster_spacer', 'plate_bottom')]


def allowed(a, b):
    for x, y in ALLOWED:
        if (a['name'].startswith(x) and b['name'].startswith(y)) or (b['name'].startswith(x) and a['name'].startswith(y)):
            return True
    return False


def collisions(design):
    ps = design['parts']
    bad = []
    for i, a in enumerate(ps):
        for b in ps[i + 1:]:
            if overlaps(a, b) and not allowed(a, b):
                bad.append((a['name'], b['name']))
    return bad


def envelope(design):
    ps = design['parts']
    return dict(x=(min(p['x0'] for p in ps), max(p['x1'] for p in ps)), y=(min(p['y0'] for p in ps), max(p['y1'] for p in ps)),
                z=(min(p['z0'] for p in ps), max(p['z1'] for p in ps)))


def _feature_polys(plate):
    """Delik ve yuvalari nokta kumeleri (kenar ornekleri) olarak dondurur: [(ad, merkez, noktalar)]."""
    feats = []
    for x, y, d in plate['holes']:
        pts = [(x + d / 2 * math.cos(t * math.pi / 12), y + d / 2 * math.sin(t * math.pi / 12)) for t in range(24)]
        feats.append(('delik', (x, y), pts))
    for x, y, l, w, ang in plate['slots']:
        a = math.radians(ang)
        ca, sa = math.cos(a), math.sin(a)
        pts = []
        for i in range(0, 11):
            u = -l / 2 + l * i / 10
            for v in (-w / 2, w / 2):
                pts.append((x + u * ca - v * sa, y + u * sa + v * ca))
        for j in range(0, 5):
            v = -w / 2 + w * j / 4
            for u in (-l / 2, l / 2):
                pts.append((x + u * ca - v * sa, y + u * sa + v * ca))
        feats.append(('yuva', (x, y), pts))
    return feats


def hole_problems(plate, min_edge=2.0):
    """Delik/yuva plaka kenarina ya da birbirine cok yakin mi? (lazer kesimde en az ~2 mm et payi)"""
    o = plate['outline']
    probs = []
    feats = _feature_polys(plate)
    for i, (kind, c, pts) in enumerate(feats):
        if (min(p[0] for p in pts) < o['x0'] + min_edge or max(p[0] for p in pts) > o['x1'] - min_edge
                or min(p[1] for p in pts) < o['y0'] + min_edge or max(p[1] for p in pts) > o['y1'] - min_edge):
            probs.append(('kenar', kind, round(c[0], 1), round(c[1], 1)))
        for (kind2, c2, pts2) in feats[i + 1:]:
            if min(math.hypot(p[0] - q[0], p[1] - q[1]) for p in pts for q in pts2) < min_edge:
                probs.append(('birbirine yakin', kind, round(c[0], 1), round(c[1], 1), kind2, round(c2[0], 1), round(c2[1], 1)))
    return probs


if __name__ == '__main__':
    for v in VARIANTS:
        d = build(v)
        e = envelope(d)
        print(v, 'parca:', len(d['parts']), 'zarf x', [round(t, 1) for t in e['x']], 'y', [round(t, 1) for t in e['y']], 'z', [round(t, 1) for t in e['z']])
        print('  carpisma:', collisions(d) or 'yok')
        print('  alt plaka sorun:', hole_problems(d['plate_bottom']) or 'yok', '| ust plaka sorun:', hole_problems(d['plate_top']) or 'yok')


# ======================= MIKRO PICO ROBOT (65 x 55 mm, 1S LiPo) =======================
# Referans noktasi = iki tekerlegin orta noktasi. Tekerlekler arkali onlu (motorlar y'de ust uste biner, x'te 14 mm kayik):
# diferansiyel surus kinematigi tekerleklerin x konumuna bagli degildir (v_x = v - w*y).
MICRO = dict(
    name='Mikro robot (Raspberry Pi Pico 2 W)', T=2.0, t_top=1.6, top_is_pcb=True, corner_r=4.0,
    plate_b=(-36.0, 31.0, 27.5), top=(-40.0, 18.0, 27.5),                  # PCB arkada 4 mm tasar (tel koprulerin yolu)
    axle_z=11.0, wheel_d=22.0, wheel_w=8.0, track=65.0, wheel_x=(7.0, -7.0),          # (sol tekerlek x, sag tekerlek x)
    motor=dict(w=12.0, h=10.0, length=34.0, y_shaft=28.0),                             # sol motor: x = +7, y = 28 -> -6
    caster_x=-30.0, caster_r=4.75, deck_gap=8.0,
    standoffs=[(14.0, 24.0), (14.0, -24.0), (-32.0, 24.0), (-32.0, -24.0)], standoff_d=4.0, hole_d=2.2,
    tof_z=27.0, tof_br_w=12.0, tof_br_z1=36.0, slot_fit=0.2, half_w=27.5, sim='pico_obstacle',
    tofs=[('left', 26.0, 16.5, 30.0), ('center', 30.0, 0.0, 0.0), ('right', 26.0, -16.5, -30.0)],
)
MICRO['plate_b_z0'] = MICRO['axle_z'] + MICRO['motor']['h'] / 2                 # 16
MICRO['plate_b_z1'] = MICRO['plate_b_z0'] + MICRO['T']                          # 18
MICRO['plate_t_z0'] = MICRO['plate_b_z1'] + MICRO['deck_gap']                   # 26
MICRO['plate_t_z1'] = MICRO['plate_t_z0'] + MICRO['t_top']                      # 27.6
MICRO_PARTS_ON_PCB = {      # PCB uzerindeki parcalarin sinir kutulari (KiCad footprint'lerinden olculdu): (X boyu, Y boyu, yukseklik), kart koordinatinda donme 0
    'J1': (3.6, 26.5, 8.5), 'J3': (3.6, 13.8, 8.5), 'J4': (3.6, 13.8, 8.5), 'J5': (3.6, 13.8, 8.5), 'J7': (3.6, 11.2, 8.5), 'J8': (3.6, 11.2, 8.5),
    'J9': (7.0, 5.5, 6.0), 'D1': (5.7, 3.5, 9.0), 'R1': (5.1, 3.0, 7.0), 'R2': (5.1, 3.0, 7.0),
    'C1': (7.2, 3.0, 6.0), 'C2': (7.0, 6.8, 11.0), 'C4': (7.2, 3.0, 6.0),
}


def _micro_tofs(S):
    out = []
    back = S['T'] / 2 + 2.0
    for name, fwd, side, ang in S['tofs']:
        a = math.radians(ang)
        out.append(dict(name=name, cx=fwd - back * math.cos(a), cy=side - back * math.sin(a), ang=ang, ax=fwd, ay=side))
    return out


def build_micro():
    S = MICRO
    sys.path.insert(0, str(ROOT / 'design' / 'pcb'))
    import pcb_design as PCB
    T_, cr = S['T'], S['corner_r']
    bx0, bx1, hw = S['plate_b']
    tx0, tx1, _ = S['top']
    rr = lambda x0, x1: dict(x0=x0, x1=x1, y0=-hw, y1=hw, r=cr)
    tofs = _micro_tofs(S)
    parts, b_holes, b_slots, b_marks, t_holes, t_slots, t_marks = [], [], [], [], [], [], []
    m = S['motor']
    z0b, z1b, z0t, z1t, az = S['plate_b_z0'], S['plate_b_z1'], S['plate_t_z0'], S['plate_t_z1'], S['axle_z']
    parts.append(box('plate_bottom', bx0, bx1, -hw, hw, z0b, z1b, '#d9b77e', True, 'mekanik', '2 mm lazer kesim'))
    parts.append(box('plate_top', tx0, tx1, -hw, hw, z0t, z1t, '#2e7d32', True, 'kontrol', 'tek katmanli PCB (1,6 mm), lazer plakanin yerine gecer'))
    for i, (x, y) in enumerate(S['standoffs'], 1):
        b_holes.append((x, y, S['hole_d']))
        t_holes.append((x, y, S['hole_d']))
        parts.append(cylz(f'standoff_{i}', x, y, S['standoff_d'], z1b, z0t, '#c0c0c0', True, 'mekanik', 'M2 x 8 ara parca'))
    # tekerlekler + motorlar (sol: x = +wheel_x[0], y > 0)
    for sgn, nm, wx in ((1, 'l', S['wheel_x'][0]), (-1, 'r', S['wheel_x'][1])):
        yc = sgn * S['track'] / 2
        parts.append(cyly(f'wheel_{nm}', wx, az, yc - S['wheel_w'] / 2, yc + S['wheel_w'] / 2, S['wheel_d'], '#2b2b2b', False, 'tahrik', 'O22 x 8 (varsayim; mil tipi motora uymali)'))
        y_out, y_in = sgn * m['y_shaft'], sgn * (m['y_shaft'] - m['length'])
        parts.append(box(f'motor_{nm}', wx - m['w'] / 2, wx + m['w'] / 2, min(y_out, y_in), max(y_out, y_in), az - m['h'] / 2, az + m['h'] / 2,
                         '#7d8aa0', False, 'tahrik', 'JGA12-N20B: genislik/yukseklik standart, uzunluk (enkoderli) varsayim 34'))
        for k, yy in enumerate((4.0, 16.0)):
            for dx in (-7.0, 7.0):
                b_slots.append((wx + dx, sgn * yy, 3.4, 1.8, 0.0))
    parts.append(sphere('caster_ball', S['caster_x'], 0.0, S['caster_r'], S['caster_r'], '#bdbdbd', False, 'tahrik', 'bilyeli sarhos teker O9,5 (model secilecek)'))
    for yy in (5.0, -5.0):
        b_holes.append((S['caster_x'], yy, S['hole_d']))
        parts.append(cylz(f'caster_spacer_{"p" if yy > 0 else "n"}', S['caster_x'], yy, 4.0, 2 * S['caster_r'], z0b, '#c0c0c0', False, 'mekanik', 'teker yuksekligine gore ara parca'))
    for t in tofs:
        b_slots.append((t['cx'], t['cy'], S['tof_br_w'] + S['slot_fit'], T_ + S['slot_fit'], t['ang'] + 90.0))
        parts.append(rbox(f'tof_bracket_{t["name"]}', t['cx'], t['cy'], S['tof_br_w'], T_, z0b, S['tof_br_z1'], t['ang'], '#d9b77e', True, 'algi', 'lazer kesim dikme'))
        a = math.radians(t['ang'])
        mw, mh, mt = TOF_MOD
        parts.append(rbox(f'tof_{t["name"]}', t['ax'] - mt / 2 * math.cos(a), t['ay'] - mt / 2 * math.sin(a), mw, mt, S['tof_z'] - mh / 2, S['tof_z'] + mh / 2, t['ang'],
                          '#2f6fbd', False, 'algi', 'TOF400C modul boyutu varsayim'))
    # alt kat: LiPo + TB6612 modulu (kartin disinda)
    parts.append(box('battery', -34.0, -4.0, -10.0, 10.0, z1b, z1b + 5.5, '#4a4a4a', False, 'guc', '1S LiPo 30 x 20 x 5,5 (varsayim; ornegin 502030)'))
    parts.append(box('tb6612', -1.0, 19.0, -10.0, 10.0, z1b, z1b + 3.0, '#7b4fc9', False, 'kontrol', 'TB6612FNG modulu 20 x 20 (varsayim); karta 10 telli kablo, motorlara dogrudan'))
    b_marks += [(-34.0, -10.0, -4.0, 10.0), (-1.0, -10.0, 19.0, 10.0)]
    # kart: Pico ve yardimci parcalar (yerlesim pcb_design.PLACE'ten)
    to_robot = lambda X, Y: (tx1 - Y, hw - X)
    ux, uy, _rot = PCB.PLACE['U1']
    cx, cy = to_robot(ux, uy)
    for side, nm in ((1, 'l'), (-1, 'r')):
        parts.append(box(f'pico_socket_{nm}', cx - 25.4, cx + 25.4, cy + side * 8.89 - 1.27, cy + side * 8.89 + 1.27, z1t, z1t + 8.5, '#222222', True, 'kontrol', '1x20 dişi soket'))
    parts.append(box('pico', cx - 25.5, cx + 25.5, cy - 10.5, cy + 10.5, z1t + 8.5, z1t + 8.5 + 1.0 + 2.5, '#2e8b57', True, 'kontrol', 'Pico 2 W 51 x 21 (soketli)'))
    for ref, (sx_, sy_, h) in MICRO_PARTS_ON_PCB.items():
        X, Y, rot = PCB.PLACE[ref]
        w_, d_ = (sy_, sx_) if rot % 180 == 90 else (sx_, sy_)
        x, y = to_robot(X, Y)
        parts.append(box(ref.lower() + '_part', x - d_ / 2, x + d_ / 2, y - w_ / 2, y + w_ / 2, z1t, z1t + h, '#6b6b6b', True, 'kontrol', f'{ref} (yaklasik sinir kutusu)'))
    seen = set()
    for p in parts:
        base, k = p['name'], 1
        while p['name'] in seen:
            k += 1
            p['name'] = f'{base}_{k}'
        seen.add(p['name'])
    return dict(variant='pico', tofs=tofs, spec=S,
                plate_bottom=dict(outline=rr(bx0, bx1), holes=b_holes, slots=b_slots, marks=b_marks, z0=z0b, z1=z1b),
                plate_top=dict(outline=rr(tx0, tx1), holes=t_holes, slots=t_slots, marks=t_marks, z0=z0t, z1=z1t),
                parts=parts)


def build(variant):
    """Bir varyantin tum tasarimini sozluk olarak dondurur (des['spec'] varyanta ozgu olculer)."""
    assert variant in VARIANTS
    return build_micro() if variant == 'pico' else _build_big(variant)


# ---------------- OpenSCAD'e aktarim ----------------
def _f(v):
    return f'{v:.4f}'.rstrip('0').rstrip('.') if isinstance(v, float) else str(v)


def _list(rows):
    return '[' + ', '.join('[' + ', '.join(_f(c) if not isinstance(c, str) else f'"{c}"' for c in r) + ']' for r in rows) + ']'


def scad_arrays(design):
    """lib.scad'in bekledigi dizileri yazar (generated/<varyant>.scad)."""
    pb, pt = design['plate_bottom'], design['plate_top']
    o = lambda pl: [pl['outline']['x0'], pl['outline']['x1'], pl['outline']['y0'], pl['outline']['y1'], pl['outline']['r']]
    rows = []
    for p in design['parts']:
        k = p['kind']
        if k == 'box':
            rows.append(['box', p['name'], p['x0'], p['x1'], p['y0'], p['y1'], p['z0'], p['z1']])
        elif k == 'rbox':
            rows.append(['rbox', p['name'], p['cx'], p['cy'], p['w'], p['d'], p['z0'], p['z1'], p['ang']])
        elif k == 'cylz':
            rows.append(['cylz', p['name'], p['cx'], p['cy'], p['d'], p['z0'], p['z1']])
        elif k == 'cyly':
            rows.append(['cyly', p['name'], p['cx'], p['cz'], p['y0'], p['y1'], p['d']])
        elif k == 'sphere':
            rows.append(['sphere', p['name'], p['cx'], p['cy'], p['cz'], p['r']])
    lines = [f'// OTOMATIK URETILDI (design/design.py, varyant: {design["variant"]}); elle degistirme.',
             f'OUT_B = {_list([o(pb)])}[0];', f'HOLES_B = {_list(pb["holes"])};', f'SLOTS_B = {_list(pb["slots"])};',
             f'MARKS_B = {_list(pb["marks"])};', f'Z_B = [{_f(pb["z0"])}, {_f(pb["z1"])}];',
             f'OUT_T = {_list([o(pt)])}[0];', f'HOLES_T = {_list(pt["holes"])};', f'SLOTS_T = {_list(pt["slots"])};',
             f'MARKS_T = {_list(pt["marks"])};', f'Z_T = [{_f(pt["z0"])}, {_f(pt["z1"])}];',
             f'BRACKET = [{_f(design["spec"]["tof_br_w"])}, {_f(design["spec"]["tof_br_z1"] - design["spec"]["plate_b_z0"])}];',
             f'PARTS = {_list(rows)};']
    return '\n'.join(lines) + '\n'


def write_scad(variant, outdir):
    d = build(variant)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f'{variant}.scad').write_text(scad_arrays(d), encoding='utf-8')
    (ROOT / 'design' / f'robot_{variant}.scad').write_text(
        f'// Robot ({variant}) 3B modeli. Diziler generated/{variant}.scad dosyasindan gelir.\ninclude <generated/{variant}.scad>\ninclude <lib.scad>\npart = "plate_bottom";\nrender_part(part);\n',
        encoding='utf-8')
    return d
