"""KiCad'in KENDI okuyucusu semadan ayni netleri cikariyor mu? (kicad-cli yoksa atlanir) Calistir: python3 tests/test_kicad_schematic.py"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'design' / 'pcb'), str(ROOT / 'tools' / 'design')]
import pcb_design as P  # noqa: E402

SCH = ROOT / 'design' / 'pcb' / 'kicad' / 'pico-carrier.kicad_sch'


def test_kicad_reads_the_same_nets():
    if not shutil.which('kicad-cli'):
        return
    import build_kicad as K
    nets = K.netlist_from_kicad()
    exp = {n: {(r, str(K.pin_no(r, p))) for r, p in pins} for n, pins in P.nets().items()}
    for name, pins in exp.items():
        assert nets.get(name) == pins, name
    extra = [n for n in nets if n not in exp and not n.startswith('unconnected-')]
    assert extra == []                                           # fazladan net yok (NC pinler 'unconnected-' olur)
    nc = [n for n in nets if n.startswith('unconnected-')]
    assert len(nc) == len(P.NC_PINS)


def test_footprints_exist_in_installed_kicad():
    base = Path('/usr/share/kicad/footprints')
    if not base.exists():
        return
    for ref, (_v, fp, _d, _p) in P.COMPONENTS.items():
        lib, name = fp.split(':')
        if ref == 'U1':
            assert (ROOT / 'design' / 'pcb' / 'kicad' / 'pico-carrier.pretty' / 'RaspberryPi_Pico_THT.kicad_mod').exists()
            continue
        assert (base / f'{lib}.pretty' / f'{name}.kicad_mod').exists(), fp


def test_schematic_has_every_component_once():
    txt = SCH.read_text(encoding='utf-8')
    refs = re.findall(r'\(property "Reference" "([A-Z]+\d+)" \(at [^)]*\) \(effects \(font \(size 1.27 1.27\)\)\)\)\n    \(property "Value"', txt)
    assert sorted(refs) == sorted(P.COMPONENTS)


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
