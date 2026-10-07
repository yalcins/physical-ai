"""Teknik resimleri uretir (SVG): robotlar, arena, sistem semasi -> docs/media/drawings/

    python3 tools/drawings/make_drawings.py

Olculer TEK KAYNAKTAN okunur: pai_gym/world.py (tekerlek, sensor) ve src/arena_sim/urdf/pai_bot.urdf (govde),
src/arena_sim/worlds/arena.sdf (arena). Parca yerlesimi (Pico, TB6612, pil...) bir ONERIDIR; yer tutucu ozelligi taslar.
"""
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(Path(__file__).resolve().parent), str(ROOT / 'pai_gym'), str(ROOT / 'design')]

from svgkit import BODY, DIM, GRID, INK, PAPER, SENSOR, WHEEL, Svg  # noqa: E402
from pai_gym import world as W  # noqa: E402

OUT = ROOT / 'docs' / 'media' / 'drawings'
OUT.mkdir(parents=True, exist_ok=True)
MM = 1000.0

# ---- olculer (mm) ----
urdf = (ROOT / 'src/arena_sim/urdf/pai_bot.urdf').read_text(encoding='utf-8')
bx, by, bz = [float(v) * MM for v in re.search(r'<box size="([^"]+)"', urdf).group(1).split()]
cx, cy, cz = [float(v) * MM for v in re.search(r'<visual>\s*<origin xyz="([^"]+)"', urdf).group(1).split()]
AXLE_Z = float(re.search(r'<joint name="base_joint".*?xyz="0 0 ([0-9.]+)"', urdf, re.S).group(1)) * MM   # 21.5
WR = W.WHEEL_RADIUS * MM                       # 21.5
TRACK = W.WHEEL_SEPARATION * MM                # 115
WHEEL_W = 19.0
CASTER_X, CASTER_R = -65.0, 10.7
BODY_X0, BODY_X1 = cx - bx / 2, cx + bx / 2    # -85 .. 45
BODY_Z0, BODY_Z1 = AXLE_Z + cz - bz / 2, AXLE_Z + cz + bz / 2   # 21.5 .. 61.5
TOFS = [(n, f * MM, s * MM, math.degrees(a)) for n, f, s, a in W.TOF_SENSORS]
TOF_Z = AXLE_Z + 30.0                          # URDF: sensor 0.03 m (eksen ustunde)
FOV = math.degrees(W.TOF_FOV)
TOTAL_W = TRACK + WHEEL_W                      # 134

S = 3.8   # px / mm


def rot_rect_pts(cx, cy, w, d, ang):
    """z etrafinda donmus dikdortgenin kosegen noktalari (w: acinin dik yonu, d: kalinlik)."""
    a = math.radians(ang)
    ux, uy = -math.sin(a), math.cos(a)          # genislik yonu
    vx, vy = math.cos(a), math.sin(a)           # kalinlik yonu
    return [(cx + sx * w / 2 * ux + sy * d / 2 * vx, cy + sx * w / 2 * uy + sy * d / 2 * vy) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def robot(kind):
    """Teknik resim, TASARIMDAN (design/design.py) uretilir: ayni parcalar 3B modelde de kullanilir."""
    import design as DS
    pico = kind == 'pico'
    des = DS.build(kind)
    SP_NAME = des['spec']['name']
    parts = des['parts']
    env = DS.envelope(des)
    name = SP_NAME
    d = Svg(1700, 1020, f'{name} teknik resim',
            'Üst, ön ve yan görünüş; ölçüler milimetre. Parçalar sanal tasarım modelinden (design/design.py) çizilir; yıldızlı ölçüler varsayımdır.')
    S = 7.0 if pico else 3.7
    CONE = 22 if pico else 55          # gorus konisi cizim uzunlugu (mm)
    SP = des['spec']
    YH = env['y'][1]
    by = {p['name']: p for p in parts}
    pb, pt = des['plate_bottom'], des['plate_top']

    def fill_of(p):
        return p['color']

    # ================= ÜSTTEN =================
    ox, oy = 360, 520
    sx = lambda y: ox - y * S
    sy = lambda x: oy - x * S
    d.text(ox, 52, 'ÜSTTEN GÖRÜNÜŞ', 17, 'middle', INK, '700')

    def plate_shape(pl, fill, opacity_hex=''):
        o = pl['outline']
        d.rect(sx(o['y1']), sy(o['x1']), (o['y1'] - o['y0']) * S, (o['x1'] - o['x0']) * S, fill + opacity_hex, INK, 1.6, None, o['r'] * S)
        for (x, y, dia) in pl['holes']:
            d.circle(sx(y), sy(x), dia / 2 * S, PAPER, INK, 1)
        for (x, y, l, w, ang) in pl['slots']:
            d.poly([(sx(py_), sy(px_)) for px_, py_ in rot_rect_pts(x, y, w, l, ang - 90 if False else ang)], PAPER, INK, 1)

    def footprint(p, dash=None, opacity=1.0, outline=INK):
        k = p['kind']
        if k == 'cyly':
            d.rect(sx(p['y1']), sy(p['x1']), (p['y1'] - p['y0']) * S, (p['x1'] - p['x0']) * S, fill_of(p), outline, 1.2)
        elif k == 'box':
            d.rect(sx(p['y1']), sy(p['x1']), (p['y1'] - p['y0']) * S, (p['x1'] - p['x0']) * S, fill_of(p), outline, 1.2, dash)
        elif k == 'rbox':
            d.poly([(sx(py_), sy(px_)) for px_, py_ in rot_rect_pts(p['cx'], p['cy'], p['w'], p['d'], p['ang'])], fill_of(p), outline, 1.2, opacity)
        elif k in ('cylz', 'sphere'):
            d.circle(sx(p['cy']), sy(p['cx']), (p['d'] / 2 if k == 'cylz' else p['r']) * S, fill_of(p), outline, 1.2, dash)

    for p in parts:                                   # tekerlekler, motorlar, sarhos teker (alt)
        if p['name'].startswith(('wheel', 'caster')):
            footprint(p, '5 3' if p['name'].startswith('caster') else None)
    plate_shape(pb, '#d9b77e')
    for p in parts:                                   # alt kat
        if p['z0'] >= SP['plate_b_z1'] - 1e-6 and p['z1'] <= SP['plate_t_z0'] + 1e-6 and not p['name'].startswith(('standoff', 'tof')):
            footprint(p, '5 3')
    for p in parts:
        if p['name'].startswith('motor'):
            footprint(p, '4 3')
    plate_shape(pt, '#d9b77e', 'b0')                   # ust plaka (yari saydam)
    for p in parts:                                   # ust kat + ToF + ara parcalar
        if p['z0'] >= SP['plate_t_z1'] - 1e-6 or p['name'].startswith(('tof', 'standoff')):
            footprint(p)
    for t in des['tofs']:                              # gorus konileri
        a0 = math.radians(t['ang'])
        pts = [(sx(t['ay']), sy(t['ax']))]
        for k in (-1, 1):
            aa = a0 + k * math.radians(FOV / 2)
            pts.append((sx(t['ay'] + CONE * math.sin(aa)), sy(t['ax'] + CONE * math.cos(aa))))
        d.poly(pts, SENSOR, SENSOR, 0.8, 0.12)
    ax = YH + 8
    d.line(sx(ax), sy(0), sx(-ax), sy(0), INK, 1, '14 4 2 4')
    d.text(sx(-ax) + 6, sy(0) - 8, 'tekerlek orta hatti (referans noktasi)' if pico else 'tekerlek ekseni', 12, 'start', '#555')
    # numaralar
    marks = {}
    for p in parts:
        n = p['name']
        key = ('pico' if n == 'pico' else 'pi4' if n == 'pi4' else 'tb6612' if n == 'tb6612' else 'mpu6050' if n == 'mpu6050' else
               'regulator' if n == 'regulator' else 'battery' if n in ('battery',) else 'power' if n == 'power_placeholder' else
               'motor' if n == 'motor_l' else 'caster' if n == 'caster_ball' else 'tof' if n == 'tof_center' else None)
        if key:
            marks[key] = p
    order = ['pico', 'tb6612', 'battery', 'motor', 'tof', 'caster'] if pico else ['pi4', 'tb6612', 'mpu6050', 'power', 'motor', 'tof', 'caster']
    num = {k: i + 1 for i, k in enumerate(order)}
    for k, p in marks.items():
        if k in num:
            cx = (p['x0'] + p['x1']) / 2
            cy = (p['y0'] + p['y1']) / 2
            d.circle(sx(cy), sy(cx), 10, PAPER, INK, 1.2)
            d.text(sx(cy), sy(cx) + 5, str(num[k]), 13, 'middle', INK, '700')
    # olculer
    X0, X1, HW = SP['plate_b'][0], SP['plate_b'][1], SP['half_w']
    d.dim_v(sy(X1), sy(X0), sx(-YH) + 44, f'plaka boyu {X1 - X0:.0f}', ext_from=sx(-HW), side='right', rot=True)
    d.dim_h(sx(YH), sx(-YH), sy(X0) + 50, f'toplam genişlik {2 * YH:.0f}', ext_from=sy(X0))
    d.dim_h(sx(SP['track'] / 2), sx(-SP['track'] / 2), sy(X0) + 88, f'tekerlek aralığı {SP['track']:.0f}', ext_from=sy(X0) + 20)
    d.dim_h(sx(HW), sx(-HW), sy(X1) - 78, f'plaka genişliği {2 * HW:.0f}', ext_from=sy(X1))

    # ================= ÖNDEN =================
    fx, fg = 1020, 400
    fsx = lambda y: fx + y * S
    fsz = lambda z: fg - z * S
    d.text(fx, 52, 'ÖNDEN GÖRÜNÜŞ', 17, 'middle', INK, '700')
    d.line(fx - 300, fsz(0), fx + 300, fsz(0), INK, 1.5)
    for p in sorted(parts, key=lambda q: q['x1']):
        if p['kind'] == 'sphere':
            d.circle(fsx(p['cy']), fsz(p['cz']), p['r'] * S, fill_of(p), INK, 1)
        else:
            d.rect(fsx(p['y0']), fsz(p['z1']), (p['y1'] - p['y0']) * S, (p['z1'] - p['z0']) * S, fill_of(p), INK, 1)
    top = env['z'][1]
    d.dim_h(fsx(-YH), fsx(YH), fsz(0) + 50, f'toplam genişlik {2 * YH:.0f}', ext_from=fsz(0))
    d.dim_v(fsz(top), fsz(0), fsx(YH) + 40, f'{top:.1f}', ext_from=fsx(YH) - 2, side='right')
    d.dim_v(fsz(SP['tof_z']), fsz(0), fsx(-YH) - 44, f'ToF {SP['tof_z']:.1f}', ext_from=fsx(-YH) + 2, side='left')

    # ================= YANDAN =================
    yx, yg = 1090, 815
    ysx = lambda x: yx + x * S
    ysz = lambda z: yg - z * S
    d.text(yx, 500, 'YANDAN GÖRÜNÜŞ (sağ yan, ön sağda)', 17, 'middle', INK, '700')
    d.line(yx - 340, ysz(0), yx + 300, ysz(0), INK, 1.5)
    for p in sorted(parts, key=lambda q: -q['y0']):
        if p['kind'] in ('sphere',):
            d.circle(ysx(p['cx']), ysz(p['cz']), p['r'] * S, fill_of(p), INK, 1)
        elif p['kind'] == 'cyly':
            d.circle(ysx(p['cx']), ysz(p['cz']), p['d'] / 2 * S, fill_of(p), INK, 1.2)
        else:
            d.rect(ysx(p['x0']), ysz(p['z1']), (p['x1'] - p['x0']) * S, (p['z1'] - p['z0']) * S, fill_of(p), INK, 1)
    d.dim_h(ysx(X0), ysx(X1), ysz(0) + 42, f'plaka boyu {X1 - X0:.0f}', ext_from=ysz(0))
    d.dim_h(ysx(SP['caster_x']), ysx(0), ysz(0) + 78, f'eksen → sarhoş teker {-SP['caster_x']:.0f}', ext_from=ysz(0) + 10)
    d.dim_v(ysz(top), ysz(0), ysx(X1) + 80, f'{top:.1f} (toplam)', ext_from=ysx(X1) + 4, side='right')
    d.dim_v(ysz(SP['plate_b_z0']), ysz(0), ysx(X0) - 30, f'{SP['plate_b_z0']:.1f}', ext_from=ysx(X0), side='left')
    d.dim_v(ysz(SP['plate_t_z0']), ysz(SP['plate_b_z1']), ysx(X0) - 30 - 0, f'', ext_from=ysx(X0), side='left') if False else None
    d.dim_v(ysz(SP['plate_t_z0']), ysz(SP['plate_b_z1']), ysx(SP['standoffs'][0][0]) + 30, f'{SP['deck_gap']:.0f}', ext_from=ysx(SP['standoffs'][0][0]) + 10, side='right')
    d.dim_v(ysz(SP['tof_z']), ysz(0), ysx(X1) + 34, f'ToF {SP['tof_z']:.1f}', ext_from=ysx(X1) + 4, side='right')

    # ================= LEJANT =================
    lx, ly = 1430, 60
    d.text(lx, ly, 'BİLEŞENLER', 15, 'start', INK, '700')
    d.text(lx, ly + 20, 'kesik çizgi = alt kat; * = ölçü varsayım', 12, 'start', '#555')
    names = {'pico': 'Pico 2 W (soketli) + 1 katman PCB', 'pi4': 'Raspberry Pi 4 (85×56×17)', 'tb6612': 'TB6612FNG modülü (kartın dışında) *' if pico else 'TB6612FNG sürücü *', 'mpu6050': 'MPU6050 *',
             'regulator': 'S7V7F5 regülatör *', 'battery': '1S LiPo pil *', 'power': 'GÜÇ MODÜLÜ (karar bekliyor) *',
             'motor': 'N20 motor + enkoder ×2 *', 'tof': 'TOF400C ToF ×3 *', 'caster': 'Bilyeli sarhoş teker *'}
    for i, k in enumerate(order):
        d.text(lx, ly + 48 + i * 22, f'{num[k]}  {names[k]}', 14)
    yy = ly + 48 + len(order) * 22 + 22
    d.text(lx, yy, 'TASARIM (mm)', 15, 'start', INK, '700')
    rows = [f'Plaka: {X1 - X0:.0f} × {2 * HW:.0f} × {SP["T"]:.0f} (lazer kesim)', f'Tekerlek: Ø{SP['wheel_d']:.0f} × {SP['wheel_w']:.0f}, aralık {SP['track']:.0f}',
            f'Alt plaka altı: {SP['plate_b_z0']:.1f} (motorlar altında)', f'Kat arası: {SP["deck_gap"]:.0f} (' + ('M2 × 8' if pico else 'M3 × 20') + ')', f'ToF: yerden {SP['tof_z']:.1f}, {FOV:.0f}° görüş',
            f'Toplam yükseklik: {top:.1f}', f'Sarhoş teker: referansın {-SP["caster_x"]:.0f} gerisinde']
    for i, t in enumerate(rows):
        d.text(lx, yy + 24 + i * 21, t, 13.5)
    note_y = yy + 24 + len(rows) * 21 + 26
    notes = (['MİKRO robot: 1S LiPo, regülatör yok.', 'Tek katmanlı PCB üst plakadır.', 'Yıldızlı parça boyutları varsayım:', 'gerçek parça gelince design.py güncellenir.']
             if pico else ['Güç yöntemi seçilince yer tutucu', 'gerçek modülle değiştirilir.', 'Pi 4 üst katta (M2.5 ara parça),', 'toplam yükseklik Pico sürümünden büyük.'])
    d.rect(lx - 8, note_y - 20, 262, 14 + 18 * len(notes), 'none', DIM, 1, '4 3')
    for i, t in enumerate(notes):
        d.text(lx, note_y + i * 18, t, 12.5, 'start', DIM)

    d.title_block(name + ' – teknik resim', 'Ölçüler milimetre; üç görünüş (üst, ön, yan); kaynak: sanal tasarım v0',
                  f'Ölçek: ekranda {S:.1f} px = 1 mm (yaklaşık)', 'Kaynak: design/design.py (3B model ve lazer dosyalarıyla aynı)', width=700)
    d.save(OUT / f'{kind}-robot.svg')


# =============================== ARENA ===============================
def arena():
    d = Svg(1500, 1000, 'Arena teknik resim', 'Üstten plan, ön ve yan görünüş; ölçüler milimetre; koordinat merkezi arenanın ortasıdır.')
    s = 0.34
    ox, oy = 470, 520
    px = lambda x: ox + x * s
    py = lambda y: oy - y * s
    H = W.HALF * MM            # 1000 ic yaricap
    t = 18.0
    d.text(ox, 52, 'ÜSTTEN PLAN', 17, 'middle', INK, '700')
    # izgara 250 mm
    for k in range(-4, 5):
        d.line(px(k * 250), py(-H), px(k * 250), py(H), GRID, 0.6)
        d.line(px(-H), py(k * 250), px(H), py(k * 250), GRID, 0.6)
    d.rect(px(-H - t), py(H + t), (2 * H + 2 * t) * s, (2 * H + 2 * t) * s, '#c9a878', INK, 1.5)         # duvarlar
    d.rect(px(-H), py(H), 2 * H * s, 2 * H * s, '#efece2', INK, 1.5)                                    # ic alan
    # sabit engeller (arena.sdf ile ayni)
    d.rect(px(450 - 75), py(350 + 75), 150 * s, 150 * s, '#6fa8dc', INK, 1.5)
    d.circle(px(-350), py(500), 60 * s, '#e08a7b', INK, 1.5)
    # Pico baslangic (pico2 senaryosu) ve ogrenen robot baslangici
    for (x, y, ang) in ((300, -400, 2.0), (-500, 0, 0.5)):
        d.circle(px(x), py(y), W.ROBOT_RADIUS * MM * s, '#f3c1a4', INK, 1.2, '4 3')
        d.line(px(x), py(y), px(x + 75 * math.cos(ang)), py(y + 75 * math.sin(ang)), INK, 1.5)
    d.circle(px(-600), py(-600), 8, '#2f6fbd', INK, 1)
    d.line(px(-600), py(-600), px(-600 + 120 * math.cos(0.785)), py(-600 + 120 * math.sin(0.785)), '#2f6fbd', 2.2, extra='marker-end="url(#ar)"')
    # eksenler
    d.line(px(0), py(0), px(300), py(0), INK, 1.2, extra='marker-end="url(#ar)"')
    d.line(px(0), py(0), px(0), py(300), INK, 1.2, extra='marker-end="url(#ar)"')
    d.text(px(300) + 6, py(0) + 5, 'x', 14)
    d.text(px(0) + 6, py(300) - 4, 'y', 14)
    d.circle(px(0), py(0), 4, INK, INK, 1)
    d.text(px(0) + 8, py(0) + 18, '(0,0) merkez', 12)
    # etiketler
    d.text(px(450), py(350) - 55, 'kutu 150×150', 13, 'middle')
    d.text(px(450), py(350) - 42, '(450, 350)', 12, 'middle', '#555')
    d.text(px(-350), py(500) - 40, 'silindir Ø120', 13, 'middle')
    d.text(px(-350), py(500) - 27, '(-350, 500)', 12, 'middle', '#555')
    d.text(px(-600) + 12, py(-600) + 28, 'öğrenen robot başlangıcı (-600,-600), yön 45°', 12, 'start', '#2f6fbd')
    d.text(px(300) + 24, py(-400) + 4, 'Pico 1 (300,-400)', 12)
    d.text(px(-500) + 24, py(0) + 22, 'Pico 2 (-500, 0)', 12)
    # olculer
    d.dim_h(px(-H), px(H), py(-H - t) + 46, f'iç ölçü {2 * H:.0f}', ext_from=py(-H - t) + 4)
    d.dim_h(px(-H - t), px(H + t), py(-H - t) + 84, f'dış ölçü {2 * H + 2 * t:.0f}', ext_from=py(-H - t) + 4)
    d.dim_v(py(H), py(-H), px(-H - t) - 44, f'{2 * H:.0f}', ext_from=px(-H - t) + 2, side='left')
    # kesit
    kx, ky = 1000, 110
    ks = 2.2
    d.text(kx + 60, 52, 'DUVAR KESİTİ', 17, 'middle', INK, '700')
    d.rect(kx, ky, t * ks, 120 * ks, '#c9a878', INK, 2)
    d.line(kx - 60, ky + 120 * ks, kx + 200, ky + 120 * ks, INK, 1.5)
    d.dim_h(kx, kx + t * ks, ky - 16, f'{t:.0f}', ext_from=ky)
    d.dim_v(ky, ky + 120 * ks, kx + t * ks + 50, '120', ext_from=kx + t * ks, side='right')
    d.text(kx + 90, ky + 60, 'MDF', 14, 'start', '#555')
    d.text(kx - 56, ky + 120 * ks + 22, 'zemin', 12, 'start', '#555')
    # on ve yan goruntu (siluet)
    es = 0.30
    for (title, y0, items, axis) in (
        ('ÖNDEN GÖRÜNÜŞ (x ekseni boyunca)', 470, [(450, 150, 'kutu'), (-350, 120, 'silindir')], 'x'),
        ('YANDAN GÖRÜNÜŞ (y ekseni boyunca)', 700, [(350, 150, 'kutu'), (500, 120, 'silindir')], 'y'),
    ):
        ex = 1090
        d.text(ex, y0 - 46, title, 15, 'middle', INK, '700')
        d.line(ex - H * es - 30, y0 + 120 * es, ex + H * es + 30, y0 + 120 * es, INK, 1.5)
        d.rect(ex - H * es - t * es, y0, t * es, 120 * es, '#c9a878', INK, 1)
        d.rect(ex + H * es, y0, t * es, 120 * es, '#c9a878', INK, 1)
        for (pos, size, nm) in items:
            fill = '#6fa8dc' if nm == 'kutu' else '#e08a7b'
            d.rect(ex + (pos - size / 2) * es, y0, size * es, 120 * es, fill, INK, 1)
            d.text(ex + pos * es, y0 - 6, nm, 11, 'middle', '#555')
        d.dim_v(y0, y0 + 120 * es, ex + H * es + 40, '120', ext_from=ex + H * es + t * es, side='right')
    d.text(930, 820, 'Hareketli engeller: 2 Pico robot (Ø150, 0,20 m/s’ye kadar)', 13, 'start')
    d.text(930, 840, 'Duvar yüksekliği 120 mm: ToF (yerden ≈ 51 mm) duvarı görür.', 13, 'start')
    d.text(930, 860, 'Zemin: düz ve mat (parlak yüzey ToF’u bozabilir).', 13, 'start')
    d.title_block('Arena – teknik resim', 'Ölçüler milimetre; merkez (0,0), x sağa, y yukarı', f'Ölçek: plan {s} px = 1 mm', 'Kaynak: src/arena_sim/worlds/arena.sdf, pai_gym/scenarios/pico2.json')
    d.save(OUT / 'arena.svg')


# =============================== SISTEM SEMASI ===============================
def system():
    d = Svg(1500, 980, 'Sistem şeması', 'Ana bilgisayar ve sunucu, Wi-Fi yönlendirici, iki Pico robot, iki Pi 4 robot ve arena ile veri akışı.')

    def box(x, y, w, h, title, lines, fill):
        d.rect(x, y, w, h, fill, INK, 2, None, 8)
        d.text(x + w / 2, y + 28, title, 18, 'middle', INK, '700')
        for i, l in enumerate(lines):
            d.text(x + w / 2, y + 54 + i * 20, l, 14, 'middle')

    box(560, 60, 380, 190, 'Ana bilgisayar / sunucu', ['ThinkPad, Ubuntu 24.04', 'PPO eğitimi, deney ölçümü (evaluate.py)', 'host/fleet.py: izleme ve kontrol', 'Gazebo ikizi (ROS 2 Jazzy)', 'Site yayını (publish.sh)'], '#dbe9f6')
    box(580, 360, 340, 110, 'Wi-Fi yönlendirici (2,4 GHz)', ['Robot ağı, sabit IP (DHCP rezervasyonu)', 'Pico 2 W yalnızca 2,4 GHz'], '#f3e9c8')
    box(90, 580, 360, 190, 'Küçük robotlar ×2 (Pico 2 W)', ['MicroPython, firmware/pico2w', 'Rastgele dolaşır = hareketli engel', '3 ToF, 2 motor, enkoder', 'Komut: UDP 5005, JSON', 'Telemetri 20 Hz: mesafe, pil, mod'], '#f3c1a4')
    box(1050, 580, 360, 190, 'Büyük robotlar ×2 (Pi 4)', ['ROS 2 Jazzy, pi4/run.sh', 'Politika robotun üstünde çalışır', 'Sürücü düğümü: /cmd_vel, /tof_*/range', 'Dosya: scp, kontrol: ssh', 'pi4/tof.py: adres atama'], '#bfe3bf')
    box(570, 600, 360, 150, 'Arena (2 × 2 m)', ['MDF duvar 120 mm', 'Sabit engeller: kutu, silindir', 'Küçük robotlar hareketli engel', 'Büyük robot görev çözer'], '#e6dcc4')
    for (x1, y1, x2, y2, lab, lx, ly) in (
        (750, 250, 750, 360, 'Ethernet / Wi-Fi', 770, 310),
        (650, 470, 300, 580, 'UDP 5005 (JSON)', 380, 515),
        (850, 470, 1200, 580, 'ssh, scp, ROS 2', 1080, 515),
    ):
        d.line(x1, y1, x2, y2, INK, 2.2, extra='marker-end="url(#ar)" marker-start="url(#ar)"')
        d.text(lx, ly, lab, 14, 'start', DIM)
    d.line(450, 680, 570, 680, INK, 1.5, '6 4')
    d.line(930, 680, 1050, 680, INK, 1.5, '6 4')
    d.text(510, 670, 'sahada', 12, 'middle', '#555')
    d.text(990, 670, 'sahada', 12, 'middle', '#555')
    d.text(750, 815, 'Politika dosyası (policy_latest.json) bilgisayardan Pi 4’lere gönderilir; Pico’lar komut ve telemetri ile yönetilir.', 14, 'middle')
    d.title_block('Sistem şeması', 'Kim kime hangi yolla bağlanıyor', 'Şema; ölçekli değildir', 'Kaynak: host/fleet.py, pi4/run.sh, firmware/pico2w/')
    d.save(OUT / 'system.svg')


if __name__ == '__main__':
    robot('pico')
    robot('pi4')
    arena()
    system()
    print('yazildi:', ', '.join(sorted(p.name for p in OUT.glob('*.svg'))))
