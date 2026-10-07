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
sys.path[:0] = [str(Path(__file__).resolve().parent), str(ROOT / 'pai_gym')]

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


def robot(kind):
    pico = kind == 'pico'
    name = 'Küçük robot (Raspberry Pi Pico 2 W)' if pico else 'Büyük robot (Raspberry Pi 4)'
    d = Svg(1700, 1000, f'{name} teknik resim',
            'Üst, ön ve yan görünüş; ölçüler milimetre. Tekerlek, gövde ve sensör ölçüleri simülasyonla aynıdır.')

    # ================= ÜSTTEN =================
    ox, oy = 380, 500
    sx = lambda y: ox - y * S           # robotun solu (y>0) ekranin solunda
    sy = lambda x: oy - x * S           # on yukari
    d.text(ox, 52, 'ÜSTTEN GÖRÜNÜŞ', 17, 'middle', INK, '700')
    for sgn in (1, -1):                 # tekerlekler
        d.rect(sx(sgn * TRACK / 2 + WHEEL_W / 2), sy(WR), WHEEL_W * S, 2 * WR * S, WHEEL, INK, 1.2)
    d.circle(sx(0), sy(CASTER_X), CASTER_R * S, '#cfcfcf', INK, 1, '5 3')              # sarhos teker (govdenin altinda)
    d.rect(sx(45), sy(BODY_X1), 90 * S, bx * S, BODY, INK, 2)                           # govde

    # bilesenler: (no, merkez x, merkez y, x boyu, y boyu, dolgu, alt kat mi)
    if pico:
        parts = [(6, 0, 31.5, 12, 27, '#d9d9d9', True), (6, 0, -31.5, 12, 27, '#d9d9d9', True),
                 (5, -65, 0, 35, 76, '#e9e4d4', True), (2, -30, 22, 16, 20, '#c9b8e8', True),
                 (4, -55, 18, 12, 17, '#f3e08a', True),
                 (1, 10, 0, 51, 21, '#9bd49b', False), (3, -28, -22, 20, 16, '#f0c0a0', False)]
    else:
        parts = [(6, 0, 31.5, 12, 27, '#d9d9d9', True), (6, 0, -31.5, 12, 27, '#d9d9d9', True),
                 (2, -40, -22, 16, 20, '#c9b8e8', True), (3, -40, 22, 20, 16, '#f0c0a0', True),
                 (4, -72, -28, 14, 24, '#f3e08a', True),
                 (1, -20, 0, 85, 56, '#9bd49bb8', False)]
    done = set()
    for n, px_, py_, lx_, ly_, col, low in parts:
        d.rect(sx(py_ + ly_ / 2), sy(px_ + lx_ / 2), ly_ * S, lx_ * S, col, INK, 1.2, '5 3' if low else None)
        if n not in done:
            done.add(n)
            d.circle(sx(py_), sy(px_), 10, PAPER, INK, 1.2)
            d.text(sx(py_), sy(px_) + 5, str(n), 13, 'middle', INK, '700')
    for (n, f, s_, ang) in TOFS:                                                        # ToF konileri + sensorler
        a0 = math.radians(ang)
        pts = [(sx(s_), sy(f))]
        for k in (-1, 1):
            aa = a0 + k * math.radians(FOV / 2)
            pts.append((sx(s_ + 55 * math.sin(aa)), sy(f + 55 * math.cos(aa))))
        d.poly(pts, SENSOR, SENSOR, 0.8, 0.12)
        d.add(f'<g transform="translate({sx(s_):.1f},{sy(f):.1f}) rotate({-ang})"><rect x="{-5 * S:.1f}" y="{-1.5 * S:.1f}" '
              f'width="{10 * S:.1f}" height="{3 * S:.1f}" fill="{SENSOR}" stroke="{INK}" stroke-width="1"/></g>')
    d.circle(sx(0), sy(47), 10, PAPER, INK, 1.2)
    d.text(sx(0), sy(47) + 5, '7', 13, 'middle', INK, '700')
    d.circle(sx(0), sy(CASTER_X), 10, PAPER, INK, 1.2)
    d.text(sx(0), sy(CASTER_X) + 5, '8', 13, 'middle', INK, '700')
    d.line(sx(78), sy(0), sx(-78), sy(0), INK, 1, '14 4 2 4')                           # tekerlek ekseni
    d.text(sx(-78) + 6, sy(0) - 8, 'tekerlek ekseni', 12, 'start', '#555')
    # olculer (disarida, tekerleklere carpmayacak sekilde)
    d.dim_v(sy(BODY_X1), sy(BODY_X0), sx(-TOTAL_W / 2) + 44, f'gövde boyu {bx:.0f}', ext_from=sx(45), side='right', rot=True)
    d.dim_h(sx(TOTAL_W / 2), sx(-TOTAL_W / 2), sy(BODY_X0) + 50, f'toplam genişlik {TOTAL_W:.0f}', ext_from=sy(BODY_X0))
    d.dim_h(sx(TRACK / 2), sx(-TRACK / 2), sy(BODY_X0) + 88, f'tekerlek aralığı {TRACK:.0f}', ext_from=sy(BODY_X0) + 20)

    # ================= ÖNDEN =================
    fx, fg = 1000, 380
    fsx = lambda y: fx + y * S          # onden bakinca robotun solu (y>0) sagda
    fsz = lambda z: fg - z * S
    d.text(fx, 52, 'ÖNDEN GÖRÜNÜŞ', 17, 'middle', INK, '700')
    d.line(fx - 300, fsz(0), fx + 300, fsz(0), INK, 1.5)
    d.circle(fsx(0), fsz(CASTER_R), CASTER_R * S, '#cfcfcf', INK, 1, '5 3')
    for sgn in (1, -1):
        d.rect(fsx(sgn * TRACK / 2 - WHEEL_W / 2), fsz(2 * WR), WHEEL_W * S, 2 * WR * S, WHEEL, INK, 1.2)
    d.rect(fsx(-45), fsz(BODY_Z1), 90 * S, bz * S, BODY, INK, 2)
    for (n, f, s_, ang) in TOFS:
        d.rect(fsx(s_) - 5 * S, fsz(TOF_Z + 3), 10 * S, 6 * S, SENSOR, INK, 1)
    d.dim_h(fsx(-TOTAL_W / 2), fsx(TOTAL_W / 2), fsz(0) + 50, f'toplam genişlik {TOTAL_W:.0f}', ext_from=fsz(0))
    d.dim_h(fsx(-45), fsx(45), fsz(BODY_Z1) - 34, f'gövde genişliği {by:.0f}', ext_from=fsz(BODY_Z1))
    d.dim_v(fsz(BODY_Z1), fsz(0), fsx(TOTAL_W / 2) + 44, f'{BODY_Z1:.1f}', ext_from=fsx(TOTAL_W / 2) - 2, side='right')
    d.dim_v(fsz(TOF_Z), fsz(0), fsx(-TOTAL_W / 2) - 44, f'ToF {TOF_Z:.1f}', ext_from=fsx(-TOTAL_W / 2) + 2, side='left')

    # ================= YANDAN =================
    yx, yg = 1100, 800
    ysx = lambda x: yx + x * S           # sag yan: on sagda
    ysz = lambda z: yg - z * S
    d.text(yx, 545, 'YANDAN GÖRÜNÜŞ (sağ yan, ön sağda)', 17, 'middle', INK, '700')
    d.line(yx - 340, ysz(0), yx + 300, ysz(0), INK, 1.5)
    d.rect(ysx(BODY_X0), ysz(BODY_Z1), bx * S, bz * S, BODY, INK, 2)
    d.circle(ysx(0), ysz(AXLE_Z), WR * S, WHEEL, INK, 1.5)
    d.circle(ysx(0), ysz(AXLE_Z), 3, PAPER, PAPER, 1)
    d.text(ysx(0), ysz(AXLE_Z) + 38, f'Ø{2 * WR:.0f}', 13, 'middle', PAPER, '700')
    d.circle(ysx(CASTER_X), ysz(CASTER_R), CASTER_R * S, '#cfcfcf', INK, 1.5)
    d.rect(ysx(BODY_X1), ysz(TOF_Z + 3), 4 * S, 6 * S, SENSOR, INK, 1)
    d.dim_h(ysx(BODY_X0), ysx(BODY_X1), ysz(0) + 42, f'gövde boyu {bx:.0f}', ext_from=ysz(0))
    d.dim_h(ysx(CASTER_X), ysx(0), ysz(0) + 78, f'eksen → sarhoş teker {-CASTER_X:.0f}', ext_from=ysz(0) + 10)
    d.dim_v(ysz(BODY_Z1), ysz(0), ysx(BODY_X1) + 100, f'{BODY_Z1:.1f}', ext_from=ysx(BODY_X1) + 4, side='right')
    d.dim_v(ysz(BODY_Z0), ysz(0), ysx(BODY_X0) - 50, f'{BODY_Z0:.1f}', ext_from=ysx(BODY_X0), side='left')
    d.dim_v(ysz(TOF_Z), ysz(0), ysx(BODY_X1) + 30, f'ToF {TOF_Z:.1f}', ext_from=ysx(BODY_X1) + 4, side='right')

    # ================= LEJANT =================
    lx, ly = 1430, 60
    d.text(lx, ly, 'BİLEŞENLER (yerleşim ÖNERİ)', 15, 'start', INK, '700')
    d.text(lx, ly + 20, 'kesik çizgili = alt kat', 12, 'start', '#555')
    if pico:
        items = ['1  Raspberry Pi Pico 2 W (51×21)', '2  TB6612FNG motor sürücü', '3  MPU6050 (IMU)',
                 '4  S7V7F5 5 V regülatör', '5  4×AA pil yuvası', '6  N20 motor + enkoder ×2',
                 '7  TOF400C ToF ×3 (+30°, 0°, -30°)', '8  Bilyeli sarhoş teker']
    else:
        items = ['1  Raspberry Pi 4 (85×56, üst kat)', '2  TB6612FNG motor sürücü', '3  MPU6050 (IMU)',
                 '4  Güç kaynağı: KARAR BEKLİYOR', '6  N20 motor + enkoder ×2', '7  TOF400C ToF ×3 (+30°, 0°, -30°)',
                 '8  Bilyeli sarhoş teker']
    for i, t in enumerate(items):
        d.text(lx, ly + 48 + i * 23, t, 14)
    yy = ly + 48 + len(items) * 23 + 24
    d.text(lx, yy, 'TEMEL ÖLÇÜLER (mm)', 15, 'start', INK, '700')
    rows = [f'Tekerlek: Ø{2 * WR:.0f} × {WHEEL_W:.0f}', f'Tekerlek aralığı: {TRACK:.0f}', f'Gövde: {bx:.0f} × {by:.0f} × {bz:.0f}',
            f'Yerden yükseklik: {BODY_Z0:.1f}', f'Sarhoş teker: eksenin {-CASTER_X:.0f} arkasında',
            f'ToF: yerden ≈ {TOF_Z:.0f}, {FOV:.0f}° görüş', f'Çarpışma dairesi (sim): yarıçap {W.ROBOT_RADIUS * MM:.0f}']
    for i, t in enumerate(rows):
        d.text(lx, yy + 25 + i * 21, t, 14)
    note_y = yy + 25 + len(rows) * 21 + 28
    if pico:
        notes = ['Pil yuvası, kartlar ve motorların yeri', 've boyutları yer tutucudur; gerçek', 'parçalar gelince kontrol edilip', 'güncellenecek.']
    else:
        notes = ['Pi 4 gövdeye sığıyor (85×56 < 130×90).', 'Yükseklik kontrol edilecek: Pi ≈ 17 mm;', 'altta motor + sürücü de olacak.', 'Güç yöntemi seçilince çizilecek.']
    d.rect(lx - 8, note_y - 20, 262, 14 + 18 * len(notes), 'none', DIM, 1, '4 3')
    for i, t in enumerate(notes):
        d.text(lx, note_y + i * 18, t, 12.5, 'start', DIM)

    d.title_block(name + ' – teknik resim', 'Ölçüler milimetre; üç görünüş (üst, ön, yan)',
                  f'Ölçek: ekranda {S:.1f} px = 1 mm (yaklaşık)', 'Kaynak: pai_gym/world.py, pai_bot.urdf', width=640)
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
