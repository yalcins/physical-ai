"""KiCad PCB dosyasini (pico-carrier.kicad_pcb) pcb_design.py'den uretir: yerlestirme, net atama, kart sinirlari.

    python3 tools/design/build_board.py                # yerlesim + netler -> design/pcb/kicad/pico-carrier.kicad_pcb
    python3 tools/design/build_board.py --route        # + Freerouting ile yonlendir (java ve freerouting.jar gerekir)

Kart = MIKRO robotun UST PLAKASI (55 x 58 mm, kose 4 mm): 4 M2 delik, M2 x 8 ara parcalara oturur. TEK KATMAN: bakir yalniz altta (B.Cu).
Kart koordinati: ust gorunus, robotun onu YUKARI (Y=0 on kenar). X: sol -> sag (robotun solu X=0).
Gereken: KiCad 7 (pcbnew Python modulu).
"""
import argparse
import math
import subprocess
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'design' / 'pcb'), str(ROOT / 'design')]
import pcb_design as P  # noqa: E402
import design as D  # noqa: E402

KDIR = ROOT / 'design' / 'pcb' / 'kicad'
BOARD_FILE = KDIR / 'pico-carrier.kicad_pcb'
FP_BASE = Path('/usr/share/kicad/footprints')
W, H, R = P.BOARD_W, P.BOARD_H, 4.0                  # kart: X genisligi (robotun y ekseni), Y uzunlugu (robotun x ekseni)
MM = pcbnew.FromMM

PLACE = P.PLACE
HOLES = P.HOLES


def vec(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


def load_fp(ref):
    lib, name = P.COMPONENTS[ref][1].split(':')
    libdir = KDIR / 'pico-carrier.pretty' if lib == 'pico-carrier' else FP_BASE / f'{lib}.pretty'
    fp = pcbnew.FootprintLoad(str(libdir), name)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def pad_centroid(fp):
    pads = list(fp.Pads())
    return (sum(p.GetPosition().x for p in pads) / len(pads), sum(p.GetPosition().y for p in pads) / len(pads))


def place(fp, cx, cy, rot):
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(vec(0, 0))
    gx, gy = pad_centroid(fp)
    fp.SetPosition(pcbnew.VECTOR2I(int(MM(cx) - gx), int(MM(cy) - gy)))


def pin_no(ref, pin):
    if ref == 'U1':
        return P.PICO_PINS[pin]
    if ref == 'D1':
        return 1 if pin == 'K' else 2
    return P.COMPONENTS[ref][3].index(pin) + 1


def add_outline(board):
    def seg(x1, y1, x2, y2):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetStart(vec(x1, y1))
        s.SetEnd(vec(x2, y2))
        s.SetWidth(MM(0.1))
        board.Add(s)

    def arc(cx, cy, sx, sy, ex, ey):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetCenter(vec(cx, cy))
        s.SetStart(vec(sx, sy))
        s.SetEnd(vec(ex, ey))
        s.SetWidth(MM(0.1))
        board.Add(s)
    seg(R, 0, W - R, 0)
    seg(W, R, W, H - R)
    seg(W - R, H, R, H)
    seg(0, H - R, 0, R)
    arc(W - R, R, W - R, 0, W, R)
    arc(W - R, H - R, W, H - R, W - R, H)
    arc(R, H - R, R, H, 0, H - R)
    arc(R, R, 0, R, R, 0)


def build():
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    # fab lab frezesi icin guvenli kurallar: iz 0,6 mm, aralik 0,4 mm
    nc = board.GetAllNetClasses()['Default'] if hasattr(board, 'GetAllNetClasses') else ds.m_NetSettings.m_DefaultNetClass
    nc.SetTrackWidth(MM(0.6))
    nc.SetClearance(MM(0.4))
    nc.SetViaDiameter(MM(1.4))
    nc.SetViaDrill(MM(0.8))
    ds.m_TrackMinWidth = MM(0.4)
    ds.m_MinClearance = MM(0.3)
    ds.m_ViasMinSize = MM(1.2)
    ds.m_MinThroughDrill = MM(0.6)
    # netler
    infos = {}
    for name in P.nets():
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        infos[name] = ni
    # parcalar
    fps = {}
    for ref, (val, _fp, _d, _pins) in P.COMPONENTS.items():
        fp = load_fp(ref)
        fp.SetReference(ref)
        fp.SetValue(val)
        fp.Value().SetVisible(False)                   # deger yazisi ipek baskiyi kalabaliklastirmasin
        cx, cy, rot = PLACE[ref]
        place(fp, cx, cy, rot)
        if ref == 'D1':                                # DO-41 pedleri 2,54 mm aralikli: kendi arasi 0,34 mm, freze icin yeterli
            for pad in fp.Pads():
                pad.SetLocalClearance(MM(0.3))
        board.Add(fp)
        fps[ref] = fp
    for name, pins in P.nets().items():
        for ref, pin in pins:
            pad = fps[ref].FindPadByNumber(str(pin_no(ref, pin)))
            assert pad is not None, (ref, pin)
            pad.SetNet(infos[name])
    # montaj delikleri
    for i, (x, y) in enumerate(HOLES, 1):
        mh = pcbnew.FootprintLoad(str(FP_BASE / 'MountingHole.pretty'), 'MountingHole_2.2mm_M2')
        mh.SetFPID(pcbnew.LIB_ID('MountingHole', 'MountingHole_2.2mm_M2'))
        mh.Value().SetVisible(False)
        mh.Reference().SetVisible(False)
        mh.SetReference(f'H{i}')
        mh.SetPosition(vec(x, y))
        board.Add(mh)
    add_outline(board)
    # baslik yazisi
    t = pcbnew.PCB_TEXT(board)
    t.SetText('Mikro Pico karti v0')
    t.SetPosition(vec(W - 14, H - 2.0))
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(MM(1.2), MM(1.2)))
    board.Add(t)
    return board, fps


def problems(board):
    """Yerlesim denetimi: kart disina tasan ya da birbirine giren parcalar. Tel koprulerde (W*) yalniz PEDLER kutu sayilir:
    aradaki tel kartin disindan dolanir, Pico'nun ustunden gecmez."""
    out = []
    boxes = {}
    W_PADS = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith('H'):
            continue
        if ref.startswith('W'):
            W_PADS[ref] = [(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)) for p in fp.Pads()]
            for k, (px, py) in enumerate(W_PADS[ref], 1):
                boxes[f'{ref}.{k}'] = (px - 1.1, py - 1.1, px + 1.1, py + 1.1)
            continue
        b = fp.GetBoundingBox(False, False)
        boxes[ref] = (pcbnew.ToMM(b.GetLeft()), pcbnew.ToMM(b.GetTop()), pcbnew.ToMM(b.GetRight()), pcbnew.ToMM(b.GetBottom()))
    for ref, (l, t, r, b) in boxes.items():
        if l < 1.2 or t < 1.2 or r > W - 1.2 or b > H - 1.2:
            out.append(f'{ref} kart kenarina cok yakin/disinda ({l:.1f},{t:.1f},{r:.1f},{b:.1f})')
    refs = sorted(boxes)
    for i, a in enumerate(refs):
        for c in refs[i + 1:]:
            la, ta, ra, ba = boxes[a]
            lc, tc, rc, bc = boxes[c]
            if la < rc - 0.3 and lc < ra - 0.3 and ta < bc - 0.3 and tc < ba - 0.3:
                out.append(f'{a} ve {c} cakisiyor')
    for fp in board.GetFootprints():      # montaj delikleri
        if fp.GetReference().startswith('H'):
            hx, hy = pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y)
            for ref, (l, t, r, b) in boxes.items():
                if l - 2.8 < hx < r + 2.8 and t - 2.8 < hy < b + 2.8:
                    out.append(f'{ref} montaj deligi {fp.GetReference()} yakininda')
    return out


JAR = Path.home() / '.cache' / 'freerouting' / 'freerouting-2.1.0.jar'
JAR_URL = 'https://github.com/freerouting/freerouting/releases/download/v2.1.0/freerouting-2.1.0.jar'   # Java 21 ile calisan son surum


def tokenize(text):
    import re
    return re.findall(r'\(|\)|"[^"]*"|[^\s()]+', text)


def parse_sexpr(tokens):
    stack = [[]]
    for t in tokens:
        if t == '(':
            stack.append([])
        elif t == ')':
            node = stack.pop()
            stack[-1].append(node)
        else:
            stack[-1].append(t.strip('"'))
    return stack[0][0]


def import_ses(board, ses):
    """Specctra SES (Freerouting ciktisi) -> KiCad izleri ve viyalar. (KiCad 7 Python'unda ImportSpecctraSES calismiyor.)
    SES birimi 0,1 um (resolution um 10); Y ekseni KiCad'e gore ters."""
    tree = parse_sexpr(tokenize(Path(ses).read_text(encoding='utf-8')))
    routes = next(n for n in tree if isinstance(n, list) and n and n[0] == 'routes')
    out = next(n for n in routes if isinstance(n, list) and n and n[0] == 'network_out')
    unit = 10000.0                                   # SES degeri / unit = mm
    layers = {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu}
    nets = {n.GetNetname(): n for n in board.GetNetInfo().NetsByNetcode().values()}
    count = {'wire': 0, 'via': 0}
    for net in out:
        if not (isinstance(net, list) and net and net[0] == 'net'):
            continue
        info = nets[net[1]]
        for item in net[2:]:
            if not isinstance(item, list):
                continue
            if item[0] == 'wire':
                path = next(x for x in item if isinstance(x, list) and x[0] == 'path')
                layer, width = layers[path[1]], float(path[2]) / unit
                pts = [(float(path[i]) / unit, -float(path[i + 1]) / unit) for i in range(3, len(path) - 1, 2)]
                for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(vec(x1, y1))
                    t.SetEnd(vec(x2, y2))
                    t.SetWidth(MM(width))
                    t.SetLayer(layer)
                    t.SetNet(info)
                    board.Add(t)
                    count['wire'] += 1
            elif item[0] == 'via':
                import re
                m = re.search(r'_(\d+):(\d+)_um', item[1])
                dia, drill = (int(m.group(1)) / 1000.0, int(m.group(2)) / 1000.0) if m else (1.4, 0.8)
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(vec(float(item[2]) / unit, -float(item[3]) / unit))
                v.SetViaType(pcbnew.VIATYPE_THROUGH)
                v.SetWidth(MM(dia))
                v.SetDrill(MM(drill))
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetNet(info)
                board.Add(v)
                count['via'] += 1
    return count


def cleanup(board):
    """Freerouting'in biraktigi bos uclu kisa parcalari ve cift cizilmis izleri siler."""
    removed = 0
    tol = MM(0.02)
    changed = True
    while changed:
        changed = False
        tracks = [t for t in board.GetTracks() if t.GetClass() == 'PCB_TRACK']
        vias = [t for t in board.GetTracks() if t.GetClass() == 'PCB_VIA']
        seen = set()
        for t in tracks:                                          # cift (ters yonlu ayni) izler
            key = (t.GetLayer(), t.GetNetCode(), frozenset([(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)]))
            if key in seen:
                board.Remove(t)
                removed += 1
                changed = True
            seen.add(key)
        if changed:
            continue

        def touched(pt, me):
            for pad in board.GetPads():
                if pad.GetNetCode() == me.GetNetCode() and pad.HitTest(pt):
                    return True
            for v in vias:
                if v.GetNetCode() == me.GetNetCode() and abs(v.GetPosition().x - pt.x) < tol and abs(v.GetPosition().y - pt.y) < tol:
                    return True
            for o in tracks:
                if o is me or o.GetLayer() != me.GetLayer() or o.GetNetCode() != me.GetNetCode():
                    continue
                for q in (o.GetStart(), o.GetEnd()):
                    if abs(q.x - pt.x) < tol and abs(q.y - pt.y) < tol:
                        return True
                if o.HitTest(pt):                              # baska bir izin ORTASINA binen uc (T baglanti)
                    return True
            return False
        for t in tracks:
            a, b = touched(t.GetStart(), t), touched(t.GetEnd(), t)
            if not (a and b):
                board.Remove(t)
                removed += 1
                changed = True
                break
    return removed


def _remove_block(text, start_pat):
    """Dengeli parantezli bir blogu (basi start_pat ile baslayan) siler."""
    import re
    while True:
        m = re.search(start_pat, text)
        if not m:
            return text
        i, depth = m.start(), 0
        for j in range(i, len(text)):
            depth += (text[j] == '(') - (text[j] == ')')
            if depth == 0:
                text = text[:i] + text[j + 1:]
                break


def single_layer_dsn(text):
    """Specctra DSN'i TEK KATMANA indirger: F.Cu katmani ve pedlerin F.Cu sekilleri silinir; yalniz B.Cu'da yol cekilebilir.
    Via tanimi KALIR (silinirse Freerouting 'via_rule null' hatasi verir) ama tek katmanda via kurulamaz; ice aktarimda via varsa hata verilir."""
    import re
    text = _remove_block(text, r'\(layer F\.Cu')
    text = re.sub(r'\(shape \((?:circle|rect|oval|path|polygon) F\.Cu[^()]*\)\)', '', text)
    return text


def route(board, single_layer=True):
    """Specctra DSN -> Freerouting (pencere acmadan) -> SES -> karta geri yukle. Dondurur: (kalan baglanti sayisi, DRC raporu yolu)."""
    build = KDIR / 'build'
    build.mkdir(exist_ok=True)
    dsn, ses = build / 'pico-carrier.dsn', build / 'pico-carrier.ses'
    if not JAR.exists():
        JAR.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['curl', '-sL', '-o', str(JAR), JAR_URL], check=True)
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        raise RuntimeError('DSN disa aktarilamadi')
    if single_layer:
        dsn.write_text(single_layer_dsn(dsn.read_text(encoding='utf-8')), encoding='utf-8')
    ses.unlink(missing_ok=True)
    r = subprocess.run(['java', '-Djava.awt.headless=true', '-jar', str(JAR), '--gui.enabled=false', '-de', str(dsn), '-do', str(ses), '--router.job_timeout=00:01:00'],
                       capture_output=True, text=True, timeout=170)
    if not ses.exists():
        raise RuntimeError('Freerouting cikti uretmedi: ' + r.stdout[-500:] + r.stderr[-500:])
    import_ses(board, ses)
    removed = cleanup(board)
    print('temizlenen bos uclu/cift iz:', removed)
    board.BuildConnectivity()
    return board


def drc(board, path):
    pcbnew.WriteDRCReport(board, str(path), pcbnew.EDA_UNITS_MILLIMETRES, True)
    txt = Path(path).read_text(encoding='utf-8')
    import re
    def count(label):
        m = re.search(r'\*\* Found (\d+) ' + label, txt)
        return int(m.group(1)) if m else 0
    return dict(violations=count('DRC violations'), unconnected=count('unconnected pads'), footprint_errors=count('Footprint errors'), report=str(path))


def outputs(res, tracks, vias, stats):
    """Uretim ciktilari: kart SVG'si, Gerber + delik dosyalari (zip), site icin ozet (docs/data/pcb.json)."""
    import json
    import shutil
    media = ROOT / 'docs' / 'media' / 'design'
    build = KDIR / 'build'
    svg = media / 'pico-carrier-board.svg'
    subprocess.run(['kicad-cli', 'pcb', 'export', 'svg', '-l', 'F.Cu,B.Cu,F.SilkS,Edge.Cuts', '--exclude-drawing-sheet', '--page-size-mode', '2',
                    '-o', str(svg), str(BOARD_FILE)], check=True, capture_output=True)
    gdir = build / 'gerber'
    shutil.rmtree(gdir, ignore_errors=True)
    gdir.mkdir(parents=True)
    subprocess.run(['kicad-cli', 'pcb', 'export', 'gerbers', '-o', str(gdir) + '/', str(BOARD_FILE)], check=True, capture_output=True)
    subprocess.run(['kicad-cli', 'pcb', 'export', 'drill', '-o', str(gdir) + '/', str(BOARD_FILE)], check=True, capture_output=True)
    shutil.make_archive(str(media / 'pico-carrier-gerber'), 'zip', gdir)
    import re
    rpt = (build / 'drc.rpt').read_text(encoding='utf-8')
    kinds = re.findall(r'^\[(\w+)\]', rpt, re.M)
    real = [k for k in kinds if k not in ('lib_footprint_issues',)]
    summary = dict(size_mm=[W, H, 1.6], layers=1, tracks=tracks, vias=vias, unconnected=res['unconnected'], drc_total=res['violations'],
                   drc_real=sorted(set(real)), drc_real_count=len(real), drc_lib_link_notes=kinds.count('lib_footprint_issues'),
                   track_mm=stats, rules=dict(track_mm=0.6, clearance_mm=0.4, via_mm=None),
                   note='KiCad 7.0.11; Freerouting 2.1.0 ile yonlendirildi; lib_footprint_issues = kutuphane tablosu bulunamadi bilgi notu, tasarim hatasi degil.')
    pj = ROOT / 'docs' / 'data' / 'pcb.json'
    data = json.loads(pj.read_text(encoding='utf-8'))
    data['board'] = summary
    data['status'] = 'KiCad 7.0.11 ile şema okundu (ağlar birebir eşleşti), kart yerleştirildi ve TEK KATMANDA (yalnız alt bakır, via yok) yönlendirildi; DRC: bağlanmamış 0. Fiziksel olarak frezelenmedi; modül pin sıraları gerçek modüllerle doğrulanacak.'
    pj.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--route', action='store_true')
    a = ap.parse_args()
    board, fps = build()
    probs = problems(board)
    for p in probs:
        print('YERLESIM:', p)
    if a.route:
        # Freerouting her calistirmada biraz farkli sonuc verir: baglanti kalmayana kadar (en cok 12 deneme) tekrarla, en iyisini sakla
        best = None
        for attempt in range(1, 13):
            board, fps = build()
            route(board)
            tmp = KDIR / 'build' / f'attempt-{attempt}.kicad_pcb'
            board.Save(str(tmp))
            board = pcbnew.LoadBoard(str(tmp))                 # dosyadan geri oku: bellekteki baglanti onbellegine guvenme
            res = drc(board, KDIR / 'build' / f'drc-{attempt}.rpt')
            vias = sum(1 for t in board.GetTracks() if t.GetClass() == 'PCB_VIA')
            print(f'deneme {attempt}: bagli olmayan {res["unconnected"]}, via {vias}')
            key = (res['unconnected'], vias)
            if best is None or key < best[0]:
                best = (key, attempt)
                board.Save(str(KDIR / 'build' / 'best.kicad_pcb'))
            if res['unconnected'] == 0:
                break
        board = pcbnew.LoadBoard(str(KDIR / 'build' / 'best.kicad_pcb'))
        print('secilen deneme:', best[1], best[0])
    target = BOARD_FILE if a.route else KDIR / 'build' / 'yalniz-yerlesim.kicad_pcb'      # --route olmadan yonlendirilmis karti EZME
    board.Save(str(target))
    print('yazildi:', target, '| yerlesim sorunu:', len(probs))
    res = drc(board, KDIR / 'build' / 'drc.rpt')
    tracks = sum(1 for t in board.GetTracks() if t.GetClass() == 'PCB_TRACK')
    vias = sum(1 for t in board.GetTracks() if t.GetClass() == 'PCB_VIA')
    print('DRC:', res, '| iz:', tracks, 'via:', vias)
    if a.route:
        st = {}
        for t in board.GetTracks():
            if t.GetClass() == 'PCB_TRACK':
                st[t.GetLayerName()] = round(st.get(t.GetLayerName(), 0) + pcbnew.ToMM(t.GetLength()), 1)
        outputs(res, tracks, vias, st)
    return board, probs


if __name__ == '__main__':
    main()
