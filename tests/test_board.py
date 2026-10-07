"""KiCad PCB dosyasinin (design/pcb/kicad/pico-carrier.kicad_pcb) testleri. KiCad 7 (pcbnew) yoksa atlanir.
Calistir: python3 tests/test_board.py"""
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'design' / 'pcb'), str(ROOT / 'design'), str(ROOT / 'tools' / 'design')]
try:
    import pcbnew
except ImportError:
    pcbnew = None
import pcb_design as P  # noqa: E402

BOARD = ROOT / 'design' / 'pcb' / 'kicad' / 'pico-carrier.kicad_pcb'


def pin_no(ref, pin):
    if ref == 'U1':
        return P.PICO_PINS[pin]
    if ref == 'D1':
        return 1 if pin == 'K' else 2
    return P.COMPONENTS[ref][3].index(pin) + 1


def drc_kinds(board, path):
    pcbnew.WriteDRCReport(board, str(path), pcbnew.EDA_UNITS_MILLIMETRES, True)
    return re.findall(r'^\[(\w+)\]', Path(path).read_text(encoding='utf-8'), re.M)


def test_board_matches_netlist():
    if not pcbnew:
        return
    b = pcbnew.LoadBoard(str(BOARD))
    got = {}
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname():
                got.setdefault(pad.GetNetname(), set()).add((fp.GetReference(), pad.GetNumber()))
    exp = {n: {(r, str(pin_no(r, p))) for r, p in pins} for n, pins in P.nets().items()}
    assert got == exp
    assert {fp.GetReference() for fp in b.GetFootprints()} == set(P.COMPONENTS) | {'H1', 'H2', 'H3', 'H4'}


def test_outline_and_mounting_holes_match_design():
    if not pcbnew:
        return
    import design as D
    b = pcbnew.LoadBoard(str(BOARD))
    bb = b.GetBoardEdgesBoundingBox()
    w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
    assert abs(w - 2 * D.BODY_HALF_W) < 0.3 and abs(h - (D.TOP_X1 - D.TOP_X0)) < 0.3          # ust plaka boyutu
    holes = sorted((round(pcbnew.ToMM(fp.GetPosition().x), 1), round(pcbnew.ToMM(fp.GetPosition().y), 1)) for fp in b.GetFootprints() if fp.GetReference().startswith('H'))
    # kart (X, Y) -> robot (x ileri, y sol): x = TOP_X1 - Y, y = BODY_HALF_W - X
    robot = sorted((round(D.TOP_X1 - y, 1), round(D.BODY_HALF_W - x, 1)) for x, y in holes)
    assert robot == sorted((round(x, 1), round(y, 1)) for x, y in D.STANDOFFS)


def test_drc_clean_of_real_problems():
    if not pcbnew:
        return
    b = pcbnew.LoadBoard(str(BOARD))
    with tempfile.TemporaryDirectory() as t:
        kinds = drc_kinds(b, Path(t) / 'drc.rpt')
    real = [k for k in kinds if k not in ('lib_footprint_issues', 'silk_overlap', 'silk_over_copper')]
    assert real == [], real                                      # baglanti eksigi, kisa devre, aralik ihlali, bos uclu iz yok


def test_track_rules():
    if not pcbnew:
        return
    b = pcbnew.LoadBoard(str(BOARD))
    widths = [pcbnew.ToMM(t.GetWidth()) for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
    assert widths and min(widths) >= 0.4 - 1e-6                  # fab lab frezesi icin en az 0,4 mm
    vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
    assert all(pcbnew.ToMM(v.GetDrillValue()) >= 0.6 - 1e-6 for v in vias)


def test_drc_detects_a_short():
    """DRC'nin gercekten calistigini kanitlar: farkli iki neti kesistiren iz kisa devre bildirmeli."""
    if not pcbnew:
        return
    b = pcbnew.LoadBoard(str(BOARD))
    nets = b.GetNetInfo().NetsByName()
    pads = {n: [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname() == n][0] for n in ('PWMA', 'PWMB')}
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pads['PWMA'].GetPosition())
    t.SetEnd(pads['PWMB'].GetPosition())
    t.SetWidth(pcbnew.FromMM(0.6))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(nets['PWMA'])
    b.Add(t)
    with tempfile.TemporaryDirectory() as td:
        kinds = drc_kinds(b, Path(td) / 'drc.rpt')
    assert any(k in ('shorting_items', 'clearance') for k in kinds), kinds


if __name__ == '__main__':
    if not pcbnew:
        print('pcbnew yok: atlandi')
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
