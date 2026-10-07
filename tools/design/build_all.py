"""Sanal tasarimdan TUM uretim dosyalarini uretir.

    python3 tools/design/build_all.py          # ROOT/design/design.py'den: SCAD, STL, lazer SVG/DXF, goruntuler, BOM, kablolama

Cikti:
  docs/media/design/laser-<varyant>.svg      lazer kesim (1:1 mm; kirmizi = kes, mavi = yerlesim cizgisi)
  docs/media/design/plate-<alt|ust>-<varyant>.dxf
  docs/media/design/robot-<varyant>.stl      tum robot (tek STL, indirilebilir)
  docs/media/design/render-<varyant>-sheet.png, -exploded.png
  docs/data/bom.json, docs/data/wiring.json
Gerekenler: openscad (komut satiri), python3 + numpy + Pillow.
"""
import json
import re
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'design'), str(ROOT / 'tools' / 'design')]
import design as D  # noqa: E402
import render as R  # noqa: E402

OUT = ROOT / 'docs' / 'media' / 'design'
BUILD = ROOT / 'design' / 'build'
OUT.mkdir(parents=True, exist_ok=True)


def openscad(variant, part, out):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(['openscad', '-D', f'part="{part}"', '-o', str(out), str(ROOT / 'design' / f'robot_{variant}.scad')],
                       capture_output=True, text=True)
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(f'openscad hatasi ({variant}/{part}): {r.stderr[-400:]}')
    return out


def export_parts(variant, d):
    bdir = BUILD / variant
    names = [p['name'] for p in d['parts']]
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda n: openscad(variant, n, bdir / f'{n}.stl'), names))
        two_d = ['plate_bottom_2d', 'plate_top_2d', 'bracket_2d']
        if d['plate_bottom']['marks']:
            two_d.append('plate_bottom_marks')
        if d['plate_top']['marks']:
            two_d.append('plate_top_marks')
        list(ex.map(lambda n: openscad(variant, n, bdir / f'{n}.svg'), two_d))
        for n, key in (('plate_bottom_marks', 'plate_bottom'), ('plate_top_marks', 'plate_top')):
            if not d[key]['marks']:                        # yerlesim cizgisi yok: bos SVG
                (bdir / f'{n}.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><path d=""/></svg>', encoding='utf-8')
        list(ex.map(lambda n: openscad(variant, n, bdir / f'{n}.dxf'), ['plate_bottom_2d', 'plate_top_2d', 'bracket_2d']))
    return bdir


def write_binary_stl(tris, path):
    with open(path, 'wb') as f:
        f.write(b'physical-ai robot'.ljust(80, b'\0'))
        f.write(struct.pack('<I', len(tris)))
        for t in tris:
            n = np.cross(t[1] - t[0], t[2] - t[0])
            ln = np.linalg.norm(n)
            n = n / ln if ln > 1e-12 else n
            f.write(struct.pack('<12fH', *n, *t.reshape(-1), 0))


_PATH = re.compile(r'<path d="(.*?)"', re.S)


def svg_paths(path):
    return ' '.join(_PATH.findall(Path(path).read_text(encoding='utf-8')))


def laser_svg(variant, d, bdir):
    """Alt plaka, (varsa) ust plaka ve 3 ToF dikmesi tek sayfada (1 birim = 1 mm). Mikro robotta ust plaka PCB oldugu icin kesilmez."""
    S = d['spec']
    pb, pt = d['plate_bottom']['outline'], d['plate_top']['outline']
    gap = 12.0
    wb, hb = pb['x1'] - pb['x0'], pb['y1'] - pb['y0']
    wt, ht = pt['x1'] - pt['x0'], pt['y1'] - pt['y0']
    cut_top = not S['top_is_pcb']
    bw, bh = S['tof_br_w'], S['tof_br_z1'] - S['plate_b_z0']
    width = wb + gap + (wt + gap if cut_top else 0) + 2 * gap
    height = (max(hb, ht) if cut_top else hb) + gap + bh + 2 * gap

    def group(name, dx, dy, cut, marks, color_cut='#ff0000', color_mark='#0000ff'):
        g = f'<g id="{name}" transform="translate({dx:.2f},{dy:.2f})">'
        g += f'<path d="{cut}" fill="none" stroke="{color_cut}" stroke-width="0.1"/>'
        if marks:
            g += f'<path d="{marks}" fill="none" stroke="{color_mark}" stroke-width="0.1"/>'
        return g + '</g>'
    ox_b, oy_b = gap - pb['x0'], gap - pb['y0']
    parts = [group('alt-plaka', ox_b, oy_b, svg_paths(bdir / 'plate_bottom_2d.svg'), svg_paths(bdir / 'plate_bottom_marks.svg'))]
    if cut_top:
        ox_t, oy_t = gap + wb + gap - pt['x0'], gap - pt['y0']
        parts.append(group('ust-plaka', ox_t, oy_t, svg_paths(bdir / 'plate_top_2d.svg'), svg_paths(bdir / 'plate_top_marks.svg')))
    for i in range(3):
        x = gap + i * (bw + 6)
        y = gap + (max(hb, ht) if cut_top else hb) + gap
        parts.append(f'<g id="tof-dikme-{i + 1}"><rect x="{x:.2f}" y="{y:.2f}" width="{bw:.2f}" height="{bh:.2f}" fill="none" stroke="#ff0000" stroke-width="0.1"/></g>')
    extra = ' Ust plaka PCB (design/pcb).' if not cut_top else ''
    notes = (f'<text x="{gap}" y="{height - 4:.1f}" font-size="3.2" font-family="sans-serif" fill="#555">'
             f'{variant}: kirmizi = KES, mavi = yerlesim cizgisi. 1 birim = 1 mm. {S["T"]:.0f} mm plaka.{extra} v0: parca olculeri varsayim, once karton/ince MDF ile dene.'
             '</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.1f}mm" height="{height:.1f}mm" viewBox="0 0 {width:.1f} {height:.1f}">'
           f'<title>Lazer kesim ({variant})</title>{"".join(parts)}{notes}</svg>')
    (OUT / f'laser-{variant}.svg').write_text(svg, encoding='utf-8')
    for nm, key in (('alt', 'plate_bottom_2d'), ('ust', 'plate_top_2d')):
        if nm == 'ust' and not cut_top:
            (OUT / f'plate-{nm}-{variant}.dxf').unlink(missing_ok=True)
            continue
        (OUT / f'plate-{nm}-{variant}.dxf').write_bytes((bdir / f'{key}.dxf').read_bytes())


EXPLODE = [('pico_socket', (0, 0, 66)), ('plate_top', (0, 0, 46)), ('pico', (0, 0, 66)), ('pi4', (0, 0, 60)), ('tb6612', (0, 0, 30)), ('mpu6050', (0, 0, 40)), ('regulator', (0, 0, 40)), ('j', (0, 0, 60)), ('sw1', (0, 0, 60)), ('d1', (0, 0, 60)), ('r1', (0, 0, 60)), ('r2', (0, 0, 60)), ('c', (0, 0, 60)),
           ('pico_spacer', (0, 0, 52)), ('pi4_spacer', (0, 0, 52)), ('standoff', (0, 0, 22)), ('battery', (0, 0, 14)), ('power', (0, 0, 14)),
           ('tof_bracket', (0, 0, 8)), ('tof_', (0, 0, 8)), ('motor_l', (0, 18, -16)), ('motor_r', (0, -18, -16)), ('wheel_l', (0, 30, 0)), ('wheel_r', (0, -30, 0)),
           ('caster', (0, 0, -22))]


def explode_offset(name):
    for key, off in EXPLODE:
        if name.startswith(key):
            return np.array(off, float)
    return np.zeros(3)


def _font(size):
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
              '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'):
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def renders(variant, d, bdir):
    parts = []
    for p in d['parts']:
        t = R.load_stl(bdir / f'{p["name"]}.stl')
        parts.append((p['name'], t, p['color']))
    # tek STL (indirilebilir)
    write_binary_stl(np.concatenate([t for _, t, _ in parts if len(t)]), OUT / f'robot-{variant}.stl')
    # ortak olcek: her gorunumde ayni piksel/mm olsun diye sabit pencere
    cell = (620, 440)
    views = [('Üstten', 'top'), ('Önden', 'front'), ('Yandan (sağ yan)', 'side'), ('Çapraz', 'iso')]
    sheet = Image.new('RGB', (cell[0] * 2, cell[1] * 2 + 56), (247, 245, 238))
    dr = ImageDraw.Draw(sheet)
    for i, (title, v) in enumerate(views):
        im = R.render(parts, v, cell)
        x, y = (i % 2) * cell[0], (i // 2) * cell[1] + 56
        sheet.paste(im, (x, y))
        dr.text((x + 12, y + 8), title, fill=(29, 43, 42), font=_font(16))
    e = D.envelope(d)
    dr.text((12, 8), f'Robot ({variant}) – 3B model (OpenSCAD)  |  sınır kutusu: {e["x"][1] - e["x"][0]:.0f} x {e["y"][1] - e["y"][0]:.0f} x {e["z"][1] - e["z"][0]:.1f} mm',
            fill=(29, 43, 42), font=_font(16))
    dr.text((12, 32), 'Renkler: bej = lazer plaka, siyah = tekerlek/pil, mavi = ToF, yeşil = kontrol kartı, mor = sürücü, gri = ara parça', fill=(80, 80, 80), font=_font(13))
    sheet.save(OUT / f'render-{variant}-sheet.png', optimize=True)
    ex = [(n, t + explode_offset(n), c) for n, t, c in parts]
    R.render(ex, 'iso', (1000, 760)).save(OUT / f'render-{variant}-exploded.png', optimize=True)
    return e


# ---------------- BOM ve kablolama ----------------
def bom(variant, d):
    if variant == 'pico':
        S = d['spec']
        items = [
            ('Tekerlek Ø22 × 8 (N20 mil tipine uygun)', 2, 'tahrik', False, 'Ölçü varsayım; mil D-tipi 3 mm olmalı, lastikli'),
            ('JGA12-N20B motor (6 V, ~300 dev/dk, enkoderli)', 2, 'tahrik', False, '1S LiPo (3,7 V) ile ~185 dev/dk, yaklaşık 0,2 m/s. Genişlik/yükseklik 12 × 10; enkoderli uzunluk 34 varsayıldı'),
            ('Bilyeli sarhoş teker Ø9,5 (ara parçayla)', 1, 'tahrik', False, 'Model seçilecek; ara parça yüksekliği tekere göre ayarlanır'),
            ('TB6612FNG motor sürücü modülü', 1, 'kontrol', False, 'Kartın dışında, alt katta; karta 10 telli kablo, motorlara doğrudan kablo. 20 × 20 varsayıldı'),
            ('TOF400C (VL53L1X) ToF modülü', 3, 'algı', False, 'Modül 13 × 18 × 2 varsayıldı; dikmeye yapıştırma/bant'),
            ('Raspberry Pi Pico 2 W', 1, 'kontrol', True, 'Delik düzeni datasheet\'ten; kartta 2 × 1×20 dişi soketle'),
            ('1S LiPo pil (≈30 × 20 × 5,5, korumalı) + harici şarj cihazı', 1, 'güç', False, 'Boyut varsayım (örn. 502030); kutup yönü JST-PH girişine göre DOĞRULANACAK. Kart şarj etmez'),
            ('1N5819 Schottky diyot (dikey)', 1, 'güç', True, 'Pil → VSYS'),
            ('Lazer kesim alt plaka (2 mm)', 1, 'mekanik', True, 'laser-' + variant + '.svg'),
            ('Lazer kesim ToF dikmesi (2 mm)', 3, 'mekanik', True, 'laser-' + variant + '.svg'),
            ('Tek katmanlı PCB (1,6 mm FR1/FR4, 55 × 58)', 1, 'kontrol', True, 'design/pcb; fab lab frezesi, bakır altta'),
            ('2,54 mm dişi soket 1×20 (Pico için)', 2, 'kontrol', True, ''),
            ('2,54 mm dişi soket 1×5 (ToF) ve erkek başlık 1×4 (enkoder), 1×10 (sürücü), 1×2 (anahtar)', 1, 'kontrol', True, '3 + 2 + 1 + 1 adet'),
            ('JST-PH 2 pin (kart konnektörü) + pil kablosu', 1, 'güç', True, ''),
            ('Kayar anahtar ya da toggle (pil + hattında)', 1, 'güç', False, 'pil kablosuna seri lehimlenir (kartta anahtar başlığı yok)'),
            ('Direnç 100 k (1/4 W) ×2, kondansatör 100 nF ×2 ve 100 µF/10 V ×1', 1, 'güç', True, 'pil bölücüsü, filtre, motor gücü'),
            ('Tel köprü (≈0,5 mm yalıtımlı tel, 1 adet)', 1, 'elektrik', True, 'W2 (3V3): Pico\'nun üstünden geçer (tek katmanlı kartta iki adayı birleştirir)'),
            ('M2 × 8 ara parça + M2 vida/somun', 4, 'mekanik', True, 'plakalar ve PCB arası'),
            ('Kablo bağı (motorları plakaya bağlamak)', 4, 'mekanik', True, 'her motora 2 adet'),
            ('Çift yüzlü bant', 1, 'mekanik', True, 'LiPo ve TB6612 modülü için'),
        ]
        return [dict(name=n, qty=q, group=g, verified=v, note=nt) for n, q, g, v, nt in items]
    items = [
        ('Tekerlek Ø43 × 19', 2, 'tahrik', True, 'Şartname: 43 mm çap, 19 mm genişlik; mil tipi motorla uyumlu olmalı'),
        ('JGA12-N20B motor (6 V, ~300 dev/dk, enkoderli)', 2, 'tahrik', False, 'Genişlik 12, yükseklik 10 standart; gövde uzunluğu 34 varsayıldı, ölçülecek'),
        ('Bilyeli sarhoş teker (yüksekliği ≈ 21 mm)', 1, 'tahrik', False, 'Model seçilecek; ara parça yüksekliği tekere göre ayarlanır'),
        ('TB6612FNG motor sürücü kartı', 1, 'kontrol', False, 'Kart boyutu 20 × 20 varsayıldı (çift yüzlü bant)'),
        ('TOF400C (VL53L1X) ToF modülü', 3, 'algı', False, 'Modül 13 × 18 × 2 varsayıldı; vida deliği düzeni bilinmiyor, yapıştırma/bant'),
        ('MPU6050 modülü', 1, 'algı', False, '20 × 16 varsayıldı'),
        ('Lazer kesim alt plaka (3 mm)', 1, 'mekanik', True, 'laser-' + variant + '.svg'),
        ('Lazer kesim üst plaka (3 mm)', 1, 'mekanik', True, 'laser-' + variant + '.svg'),
        ('Lazer kesim ToF dikmesi (3 mm)', 3, 'mekanik', True, 'laser-' + variant + '.svg'),
        ('M3 × 20 ara parça (dişi-dişi) ya da M3 cıvata + somun', 4, 'mekanik', True, 'plakalar arası'),
        ('M3 × 8 vida', 8, 'mekanik', True, 'ara parça uçları (yaklaşık)'),
        ('Kablo bağı (motorları plakaya bağlamak)', 4, 'mekanik', True, 'her motora 2 adet'),
        ('Dupont/jumper kablo seti', 1, 'elektrik', True, 'tezgâh ve ilk montaj'),
        ('Çift yüzlü bant (köpük)', 1, 'mekanik', True, 'kartları plakaya yapıştırmak için'),
        ('Raspberry Pi 4 (2 GB ya da üstü)', 1, 'kontrol', True, '85 × 56; M2.5 delik düzeni 58 × 49'),
        ('M2.5 × 5 ara parça + vida/somun', 4, 'mekanik', True, 'Pi 4 için'),
        ('microSD kart (Ubuntu 24.04 + ROS 2 Jazzy)', 1, 'kontrol', True, ''),
        ('Güç kaynağı modülü (KARAR BEKLİYOR)', 1, 'güç', False, '5 V yüksek akım + motor 6 V; yer tutucu 70 × 40 × 18. Seçilince boyut güncellenir'),
    ]
    return [dict(name=n, qty=q, group=g, verified=v, note=nt) for n, q, g, v, nt in items]


PICO_WIRING = [
    ('I2C SDA', 'GP4', 'ToF ×3', 'SDA', True), ('I2C SCL', 'GP5', 'ToF ×3', 'SCL', True),
    ('ToF sol XSHUT', 'GP6', 'TOF400C #1', 'XSHUT', True), ('ToF orta XSHUT', 'GP7', 'TOF400C #2', 'XSHUT', True), ('ToF sağ XSHUT', 'GP8', 'TOF400C #3', 'XSHUT', True),
    ('Enkoder sol A', 'GP10', 'Sol motor enkoderi', 'A', True), ('Enkoder sol B', 'GP11', 'Sol motor enkoderi', 'B', True),
    ('Enkoder sağ A', 'GP12', 'Sağ motor enkoderi', 'A', True), ('Enkoder sağ B', 'GP13', 'Sağ motor enkoderi', 'B', True),
    ('Sol motor PWM', 'GP16', 'TB6612FNG', 'PWMA', True), ('Sol motor yön 1', 'GP17', 'TB6612FNG', 'AIN1', True), ('Sol motor yön 2', 'GP18', 'TB6612FNG', 'AIN2', True),
    ('Sağ motor yön 1', 'GP19', 'TB6612FNG', 'BIN1', True), ('Sağ motor yön 2', 'GP20', 'TB6612FNG', 'BIN2', True), ('Sağ motor PWM', 'GP21', 'TB6612FNG', 'PWMB', True),
    ('Sürücü etkin', 'GP22', 'TB6612FNG', 'STBY', True), ('Pil ölçümü (ADC)', 'GP26', 'Pil bölücüsü', 'orta nokta', True),
]
PI4_WIRING = [   # BCM numaralari; fiziksel pin numarası parantez içinde. ÖNERİ: kablolamadan önce doğrulanacak.
    ('I2C SDA', 'GPIO2 (pin 3)', 'ToF ×3, MPU6050', 'SDA', False), ('I2C SCL', 'GPIO3 (pin 5)', 'ToF ×3, MPU6050', 'SCL', False),
    ('ToF sol XSHUT', 'GPIO5 (pin 29)', 'TOF400C #1', 'XSHUT', False), ('ToF orta XSHUT', 'GPIO6 (pin 31)', 'TOF400C #2', 'XSHUT', False), ('ToF sağ XSHUT', 'GPIO26 (pin 37)', 'TOF400C #3', 'XSHUT', False),
    ('Enkoder sol A', 'GPIO17 (pin 11)', 'Sol motor enkoderi', 'A', False), ('Enkoder sol B', 'GPIO27 (pin 13)', 'Sol motor enkoderi', 'B', False),
    ('Enkoder sağ A', 'GPIO22 (pin 15)', 'Sağ motor enkoderi', 'A', False), ('Enkoder sağ B', 'GPIO4 (pin 7)', 'Sağ motor enkoderi', 'B', False),
    ('Sol motor PWM', 'GPIO12 (pin 32)', 'TB6612FNG', 'PWMA', False), ('Sol motor yön 1', 'GPIO23 (pin 16)', 'TB6612FNG', 'AIN1', False), ('Sol motor yön 2', 'GPIO24 (pin 18)', 'TB6612FNG', 'AIN2', False),
    ('Sağ motor PWM', 'GPIO13 (pin 33)', 'TB6612FNG', 'PWMB', False), ('Sağ motor yön 1', 'GPIO25 (pin 22)', 'TB6612FNG', 'BIN1', False), ('Sağ motor yön 2', 'GPIO16 (pin 36)', 'TB6612FNG', 'BIN2', False),
    ('Sürücü etkin', 'GPIO20 (pin 38)', 'TB6612FNG', 'STBY', False),
]
POWER = {
    'pico': ['1S LiPo (3,0-4,2 V) → anahtar → motor gücü: TB6612 VM (kart J1 → sürücü kablosu)', 'LiPo → 1N5819 → Pico VSYS (Pico buck-boost ile 3,3 V üretir; regülatör YOK)', 'TB6612 VCC (mantık) pilden: 2,7-5,5 V aralığında; Pico 3,3 V çıkışı 0,7·VCC eşiğinin üstünde. ToF ve enkoder beslemesi Pico 3V3(OUT) (modül gerilim aralığı doğrulanacak)', 'Motor uçları kartta değil: TB6612 modülünden doğrudan motora', '3V3 iki ada (Pico\'nun iki yanı): W2 tel köprüsü birleştirir; GND adalarını Pico modülü kendi içinde birleştirir (her yanda tek GND pini kullanılır)', 'GP26: 100 k / 100 k bölücü (oran 2) → LiPo en çok 2,1 V; bölücüsüz bağlanmaz'],
    'pi4': ['GÜÇ YÖNTEMİ KARAR BEKLİYOR: Pi 4 için 5 V / 3 A, motorlar için 6 V', 'Pi 3V3 (pin 1) → TB6612 VCC, ToF ve MPU6050 besleme', 'Tüm GND\'ler ortak (Pi, pil/güç modülü, TB6612, sensörler)', 'ToF adresleri XSHUT ile ayrı atanır (pi4/tof.py); MPU6050 adresi 0x68'],
}


def wiring(variant):
    rows = PICO_WIRING if variant == 'pico' else PI4_WIRING
    return dict(rows=[dict(signal=s, mcu_pin=p, device=dv, device_pin=dp, verified=v) for s, p, dv, dp, v in rows], power=POWER[variant],
                note='Pi 4 pin planı ÖNERİdir; doğrulanana kadar kablolama yapılmaz.' if variant == 'pi4' else 'Pico pin planı CLAUDE.md ve firmware ile aynı; kart konnektörleri: J1 sürücü (10 pin), J3-J5 ToF, J7/J8 enkoder, J9 LiPo.')


def main():
    summary = {}
    bom_all, wir_all = {}, {}
    for v in D.VARIANTS:
        d = D.write_scad(v, ROOT / 'design' / 'generated')
        assert not D.collisions(d), D.collisions(d)
        bdir = export_parts(v, d)
        laser_svg(v, d, bdir)
        env = renders(v, d, bdir)
        bom_all[v] = bom(v, d)
        wir_all[v] = wiring(v)
        summary[v] = dict(envelope={k: [round(a, 1) for a in val] for k, val in env.items()}, parts=len(d['parts']))
    (ROOT / 'docs' / 'data' / 'bom.json').write_text(json.dumps(dict(updated='auto', variants=bom_all), ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'docs' / 'data' / 'wiring.json').write_text(json.dumps(dict(variants=wir_all), ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'design' / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    info = {}
    for v in D.VARIANTS:
        d = D.build(v)
        e = D.envelope(d)
        info[v] = dict(parts=len(d['parts']), unverified=sorted(p['name'] for p in d['parts'] if not p['verified']),
                       envelope_mm=dict(x=round(e['x'][1] - e['x'][0], 1), y=round(e['y'][1] - e['y'][0], 1), z=round(e['z'][1] - e['z'][0], 1)),
                       collisions=D.collisions(d), cut_problems=D.hole_problems(d['plate_bottom']) + D.hole_problems(d['plate_top']),
                       plate_mm=[round(d['spec']['plate_b'][1] - d['spec']['plate_b'][0], 1), round(2 * d['spec']['half_w'], 1), d['spec']['T']], deck_gap_mm=d['spec']['deck_gap'])
    (ROOT / 'docs' / 'data' / 'design.json').write_text(json.dumps(dict(variants=info, sim_radius_note='Simülasyon çarpışma dairesi 75 mm; tasarımda arka köşeler eksenden ≈96 mm (bulgu: carpisma-yaricapi).'),
                                                                   ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
