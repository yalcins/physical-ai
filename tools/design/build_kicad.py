"""KiCad proje dosyalarini (design/pcb/kicad/) pcb_design.py'den uretir: footprint kutuphanesi, sema, proje.

    python3 tools/design/build_kicad.py          # KiCad 7 kurulu olmali (dogrulama icin kicad-cli)

  pico-carrier.pretty/RaspberryPi_Pico_THT.kicad_mod   KiCad 7 kutuphanesinde olmayan Pico footprint'i (2 x 20 soket)
  fp-lib-table, pico-carrier.kicad_pro
  pico-carrier.kicad_sch                               net etiketli sema (her pin etiketle baglanir)
"""
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'design' / 'pcb'))
import pcb_design as P  # noqa: E402

KDIR = ROOT / 'design' / 'pcb' / 'kicad'
FP_NAME = 'RaspberryPi_Pico_THT'
FP_LIB = 'pico-carrier'


def u():
    return str(uuid.uuid4())


def wire_link_footprint(pitch):
    """Iki delikli tel kopru: pad araligi `pitch` mm (X ekseninde); pedler arasi tel kartin DISINDAN dolanir."""
    half = pitch / 2
    name = f'WireLink_P{pitch:.2f}mm'
    txt = (f'(footprint "{name}" (version 20221018) (generator pcb_design)\n  (layer "F.Cu")\n  (descr "Tel kopru, {pitch:.2f} mm")\n  (attr through_hole)\n'
           f'  (fp_text reference "REF**" (at 0 -2.2) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))\n'
           f'  (fp_text value "{name}" (at 0 2.2) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))\n'
           f'  (pad "1" thru_hole rect (at {-half:.3f} 0) (size 1.8 1.8) (drill 0.9) (layers "*.Cu" "*.Mask"))\n'
           f'  (pad "2" thru_hole circle (at {half:.3f} 0) (size 1.8 1.8) (drill 0.9) (layers "*.Cu" "*.Mask"))\n)\n')
    return name, txt


def pico_footprint():
    """Pico: 2 sira x 20 pin, sira araligi 17,78 mm (0,7 inc), pin 1 sol ust, 21 sag alt, 40 sag ust."""
    pads = []
    for n in range(1, 41):
        x, y = (0.0, (n - 1) * 2.54) if n <= 20 else (17.78, (40 - n) * 2.54)
        shape = 'rect' if n == 1 else 'circle'
        pads.append(f'  (pad "{n}" thru_hole {shape} (at {x:.2f} {y:.2f}) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))')
    outline = '(start -1.61 -1.37) (end 19.39 49.63)'
    court = '(start -2.0 -1.8) (end 19.8 50.1)'
    return (f'(footprint "{FP_NAME}" (version 20221018) (generator pcb_design)\n  (layer "F.Cu")\n'
            '  (descr "Raspberry Pi Pico / Pico 2 W, 2 x 20 THT soket (USB ust kenarda)")\n  (attr through_hole)\n'
            '  (fp_text reference "REF**" (at 8.89 -3.2) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))\n'
            f'  (fp_text value "{FP_NAME}" (at 8.89 52.0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))\n'
            f'  (fp_rect {outline} (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))\n'
            f'  (fp_rect {court} (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))\n'
            '  (fp_text user "USB" (at 8.89 1.5) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))\n'
            + '\n'.join(pads) + '\n)\n')


def sym_geometry(ref):
    """Sembol govdesi: pinler soldan sag a dagitilir. (sol pinler, sag pinler, genislik, yukseklik)"""
    names = P.COMPONENTS[ref][3]
    n = len(names)
    half = (n + 1) // 2
    left, right = names[:half], names[half:]
    h = max(len(left), len(right)) * 2.54 + 2.54
    return left, right, 40.64, h          # genislik 16 x 2.54


def pin_no(ref, pin):
    if ref == 'U1':
        return P.PICO_PINS[pin]
    if ref == 'D1':
        return 1 if pin == 'K' else 2
    return P.COMPONENTS[ref][3].index(pin) + 1


def lib_symbol(ref):
    left, right, w, h = sym_geometry(ref)
    name = f'{FP_LIB}:{ref}'
    top = h / 2
    lines = [f'    (symbol "{name}" (pin_names (offset 0.762)) (in_bom yes) (on_board yes)',
             f'      (property "Reference" "{ref[0]}" (at 0 {top + 1.27:.2f} 0) (effects (font (size 1.27 1.27))))',
             f'      (property "Value" "{ref}" (at 0 {-top - 1.27:.2f} 0) (effects (font (size 1.27 1.27))))',
             '      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
             '      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
             f'      (symbol "{ref}_0_1" (rectangle (start {-w / 2 + 5.08:.2f} {top:.2f}) (end {w / 2 - 5.08:.2f} {-top:.2f}) (stroke (width 0.254) (type default)) (fill (type background))))',
             f'      (symbol "{ref}_1_1"']
    for i, pin in enumerate(left):
        y = top - 2.54 - i * 2.54
        lines.append(f'        (pin passive line (at {-w / 2:.2f} {y:.2f} 0) (length 5.08) (name "{pin}" (effects (font (size 1.27 1.27)))) (number "{pin_no(ref, pin)}" (effects (font (size 1.27 1.27)))))')
    for i, pin in enumerate(right):
        y = top - 2.54 - i * 2.54
        lines.append(f'        (pin passive line (at {w / 2:.2f} {y:.2f} 180) (length 5.08) (name "{pin}" (effects (font (size 1.27 1.27)))) (number "{pin_no(ref, pin)}" (effects (font (size 1.27 1.27)))))')
    lines += ['      )', '    )']
    return '\n'.join(lines)


def schematic():
    nets = P.nets()
    pin_net = {p: n for n, pins in nets.items() for p in pins}
    root = u()
    out = ['(kicad_sch (version 20230121) (generator pcb_design)', f'  (uuid {root})', '  (paper "A1")', '  (lib_symbols']
    out += [lib_symbol(r) for r in P.COMPONENTS]
    out.append('  )')
    # yerlesim: sutunlar halinde, 2,54 izgarasina oturt
    cols = [['U1'], ['J9', 'D1', 'R1', 'R2', 'C1', 'C2'], ['J1', 'J7', 'J8'], ['J3', 'J4', 'J5', 'C4'], ['W2']]
    x0 = 76.2
    for ci, col in enumerate(cols):
        x = x0 + ci * 127.0
        y = 50.8
        for ref in col:
            left, right, w, h = sym_geometry(ref)
            cy = y + h / 2
            cy = round(cy / 2.54) * 2.54
            val, fp, desc, pins = P.COMPONENTS[ref]
            out.append(f'  (symbol (lib_id "{FP_LIB}:{ref}") (at {x:.2f} {cy:.2f} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {u()})')
            out.append(f'    (property "Reference" "{ref}" (at {x:.2f} {cy - h / 2 - 1.27:.2f} 0) (effects (font (size 1.27 1.27))))')
            out.append(f'    (property "Value" "{val}" (at {x:.2f} {cy + h / 2 + 1.27:.2f} 0) (effects (font (size 1.27 1.27))))')
            out.append(f'    (property "Footprint" "{fp}" (at {x:.2f} {cy:.2f} 0) (effects (font (size 1.27 1.27)) hide))')
            out.append(f'    (property "Datasheet" "" (at {x:.2f} {cy:.2f} 0) (effects (font (size 1.27 1.27)) hide))')
            for pin in pins:
                out.append(f'    (pin "{pin_no(ref, pin)}" (uuid {u()}))')
            out.append(f'    (instances (project "pico-carrier" (path "/{root}" (reference "{ref}") (unit 1))))')
            out.append('  )')
            top = h / 2
            for side, plist in ((-1, left), (1, right)):
                for i, pin in enumerate(plist):
                    py = cy + (-(top - 2.54 - i * 2.54))          # sembolde y yukari, sayfada asagi
                    px = x + side * w / 2
                    net = pin_net.get((ref, pin))
                    ang = 180 if side < 0 else 0
                    if net:
                        just = 'right' if side < 0 else 'left'
                        out.append(f'  (label "{net}" (at {px:.2f} {py:.2f} {ang}) (effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid {u()}))')
                    else:
                        out.append(f'  (no_connect (at {px:.2f} {py:.2f}) (uuid {u()}))')
            y += h + 12.7
    out.append('  (sheet_instances (path "/" (page "1")))')
    out.append(')')
    return '\n'.join(out) + '\n'


def project_files():
    (KDIR / 'pico-carrier.pretty').mkdir(parents=True, exist_ok=True)
    (KDIR / 'pico-carrier.pretty' / f'{FP_NAME}.kicad_mod').write_text(pico_footprint(), encoding='utf-8')
    for pitch in (30.48,):
        name, txt = wire_link_footprint(pitch)
        (KDIR / 'pico-carrier.pretty' / f'{name}.kicad_mod').write_text(txt, encoding='utf-8')
    (KDIR / 'fp-lib-table').write_text(f'(fp_lib_table\n  (version 7)\n  (lib (name "{FP_LIB}") (type "KiCad") (uri "${{KIPRJ_DIR}}/pico-carrier.pretty") (options "") (descr "Pico tasiyici karti"))\n)\n', encoding='utf-8')
    (KDIR / 'pico-carrier.kicad_pro').write_text(json.dumps({'meta': {'filename': 'pico-carrier.kicad_pro', 'version': 1}, 'board': {}, 'sheets': [[u(), '']]}, indent=2), encoding='utf-8')
    (KDIR / 'pico-carrier.kicad_sch').write_text(schematic(), encoding='utf-8')


def netlist_from_kicad():
    """KiCad'in kendi okuyucusuyla semadan netleri cikarir: {net: {(ref, pad)}}."""
    out = KDIR / 'build' / 'from-kicad.net'
    out.parent.mkdir(exist_ok=True)
    r = subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '-o', str(out), str(KDIR / 'pico-carrier.kicad_sch')], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    import re
    txt = out.read_text(encoding='utf-8')
    nets = {}
    for chunk in txt.split('(net (code ')[1:]:
        name = re.search(r'\(name "([^"]+)"\)', chunk).group(1).lstrip('/')
        nets[name] = {(a, b) for a, b in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', chunk)}
    return nets


if __name__ == '__main__':
    project_files()
    print('yazildi:', KDIR)
