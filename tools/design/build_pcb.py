"""PCB sematigi dosyalarini uretir (design/pcb/pcb_design.py'den):

    python3 tools/design/build_pcb.py

  design/pcb/pico-carrier.net       KiCad netlist (pcbnew: Dosya > Ice Aktar > Netlist)
  design/pcb/netlist.csv, bom.csv   okunabilir tablolar
  docs/media/design/pcb-schematic.svg  net etiketli sematik (KiCad'siz okunabilir)
  docs/data/pcb.json                site icin ozet (parcalar, netler, kontroller)
"""
import csv
import datetime
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'design' / 'pcb'), str(ROOT / 'tools' / 'drawings')]
import pcb_design as P  # noqa: E402
from svgkit import INK, PAPER, Svg  # noqa: E402

OUT_DIR = ROOT / 'design' / 'pcb'
MEDIA = ROOT / 'docs' / 'media' / 'design'


def pin_number(ref, pin):
    pins = P.COMPONENTS[ref][3]
    if ref == 'U1':
        return P.PICO_PINS[pin]
    if ref == 'D1':
        return 1 if pin == 'K' else 2          # DO-41: pad 1 = katot
    return pins.index(pin) + 1


def kicad_netlist():
    N = P.nets()
    lines = ['(export (version "E")',
             f'  (design (source "pico-carrier") (date "{datetime.date.today().isoformat()}") (tool "pcb_design.py"))',
             '  (components']
    for i, (ref, (val, fp, desc, _pins)) in enumerate(P.COMPONENTS.items(), 1):
        lines.append(f'    (comp (ref "{ref}") (value "{val}") (footprint "{fp}") (description "{desc}") '
                     f'(sheetpath (names "/") (tstamps "/")) (tstamp "{i:08x}"))')
    lines.append('  )')
    lines.append('  (nets')
    for code, (name, pins) in enumerate(N.items(), 1):
        lines.append(f'    (net (code "{code}") (name "{name}")')
        for ref, pin in pins:
            lines.append(f'      (node (ref "{ref}") (pin "{pin_number(ref, pin)}") (pinfunction "{pin}"))')
        lines.append('    )')
    lines.append('  )')
    lines.append(')')
    return '\n'.join(lines) + '\n'


def tables():
    N = P.nets()
    with open(OUT_DIR / 'netlist.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['net', 'ref', 'pin_no', 'pin_name'])
        for name, pins in N.items():
            for ref, pin in pins:
                w.writerow([name, ref, pin_number(ref, pin), pin])
    with open(OUT_DIR / 'bom.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['ref', 'value', 'footprint', 'description'])
        for ref, (val, fp, desc, _p) in P.COMPONENTS.items():
            w.writerow([ref, val, fp, desc])


COLORS = {'GND': '#666666', '+3V3': '#d9822b', '+5V': '#c0392b', 'VSYS': '#c0392b', 'VBAT_SW': '#b03a2e', 'VBAT_RAW': '#b03a2e', '+SENS': '#d9822b',
          'I2C_SDA': '#2f6fbd', 'I2C_SCL': '#2f6fbd', 'VBAT_SENSE': '#8b5a2b'}


def net_color(name):
    if name in COLORS:
        return COLORS[name]
    if name.startswith('XSHUT'):
        return '#0e9aa7'
    if name.startswith('ENC'):
        return '#7b4fc9'
    if name.startswith('MOT'):
        return '#2e8b57'
    return '#1d2b2a'            # PWM / yon / STBY


def schematic():
    d = Svg(1800, 1240, 'Pico robot tasiyici karti sematigi', 'Net etiketli sematik: ayni adli etiketler birbirine bagli.')
    N = P.nets()
    pin_net = {}
    for name, pins in N.items():
        for p in pins:
            pin_net[p] = name

    def block(x, y, w, ref, title, pins=None, sub=None):
        comp = P.COMPONENTS[ref]
        plist = pins or comp[3]
        rows = []
        for pin in plist:
            net = pin_net.get((ref, pin), 'NC')
            rows.append((pin, net))
        h = 54 + 20 * len(rows)
        d.rect(x, y, w, h, '#fbfaf6', INK, 1.8, None, 6)
        d.text(x + 10, y + 22, f'{ref}  {title}', 15, 'start', INK, '700')
        if sub:
            d.text(x + 10, y + 40, sub, 11.5, 'start', '#555')
        for i, (pin, net) in enumerate(rows):
            yy = y + 62 + 20 * i
            d.line(x + w - 90, yy - 4, x + w, yy - 4, net_color(net) if net != 'NC' else '#bbb', 2)
            d.text(x + 10, yy, pin if ref != 'U1' else f'{pin}  ({P.PICO_PINS[pin]})', 13)
            d.text(x + w - 94, yy, net, 12.5, 'end', net_color(net) if net != 'NC' else '#999', '700' if net != 'NC' else '400')
        return h

    # Pico (yalniz bagli olanlar + GND'ler)
    used = [k for k in P.PICO_PINS if ('U1', k) in pin_net and not k.startswith('GND')]
    used.sort(key=lambda k: P.PICO_PINS[k])
    block(40, 60, 330, 'U1', 'Raspberry Pi Pico 2 W', used + ['GND_3'], 'yalniz bagli pinler; 8 GND pini ortak GND\'ye; kalanlar NC')
    # guc
    y = 60
    for ref, title, pins in (('J_BAT', 'Pil girisi', None), ('SW1', 'Guc anahtari', None), ('J_REG', 'S7V7F5 5 V regulator', None), ('D1', '1N5819', None), ('JP1', 'Sensor besleme secimi', None)):
        h = block(430, y, 300, ref, title, pins)
        y += h + 22
    # surucu + motor
    y = 60
    for ref, title in (('J_TB_A', 'TB6612FNG (sol sira)'), ('J_TB_B', 'TB6612FNG (sag sira)'), ('J_ML', 'Sol motor + enkoder'), ('J_MR', 'Sag motor + enkoder')):
        h = block(790, y, 310, ref, title, None, 'modul pin sirasi DOGRULANACAK' if ref.startswith('J_TB') else None)
        y += h + 22
    # sensorler
    y = 60
    for ref, title in (('J_TOF1', 'ToF sol'), ('J_TOF2', 'ToF orta'), ('J_TOF3', 'ToF sag'), ('J_IMU', 'MPU6050')):
        h = block(1160, y, 290, ref, title)
        y += h + 22
    # pasif
    y = 60
    for ref, title in (('R1', 'Pil bolucu ust 20 k'), ('R2', 'Pil bolucu alt 10 k'), ('C1', 'ADC filtre 100 nF'), ('C2', 'VM 470 uF'), ('C3', '5 V 10 uF'), ('C4', 'Sensor 100 nF'),
                       ('TP1', 'Test 3V3'), ('TP2', 'Test 5 V'), ('TP3', 'Test VM'), ('TP4', 'Test GND')):
        h = block(1500, y, 250, ref, title)
        y += h + 14
    d.text(40, 1215, 'Renkler: kirmizi/turuncu = guc, mavi = I2C, yesil = motor, mor = enkoder, camgobegi = XSHUT, kahve = ADC. Ayni adli netler birbirine baglidir.', 13, 'start', '#444')
    d.title_block('Pico tasiyici karti sematigi (v0)', f'{len(P.COMPONENTS)} parca, {len(N)} net; ADC en cok {P.summary()["adc_max_v"]} V; bolucu orani 3',
                  'KiCad\'de henuz acilmadi (KiCad kurulu degil)', 'Kaynak: design/pcb/pcb_design.py', width=760)
    d.save(MEDIA / 'pcb-schematic.svg')


def main():
    probs = P.checks()
    assert not probs, probs
    (OUT_DIR / 'pico-carrier.net').write_text(kicad_netlist(), encoding='utf-8')
    tables()
    schematic()
    N = P.nets()
    info = dict(components=[dict(ref=r, value=v[0], footprint=v[1], description=v[2], pins=len(v[3])) for r, v in P.COMPONENTS.items()],
                nets=[dict(name=n, pins=len(p)) for n, p in N.items()], summary=P.summary(), problems=probs,
                status='KiCad\'de açılmadı/doğrulanmadı (KiCad kurulu değil). Modül pin sıraları gerçek modüllerle doğrulanacak.',
                board_mm_proposal=[85, 65, 1.6])
    (ROOT / 'docs' / 'data' / 'pcb.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    print('tamam:', P.summary())


if __name__ == '__main__':
    main()
