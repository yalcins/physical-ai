"""STL dosyalarini bagimsiz (OpenGL'siz) bir z-tamponlu ortografik cizici ile PNG yapar.

Teknik gorunum: duz golgeleme + siluet/kenar cizgileri. Gorunumler robot koordinatinda tanimlidir
(x ileri, y sol, z yukari): ust (on yukari), on, yan (sag yan, on sagda), capraz (izometrik).
"""
import math
import re

import numpy as np
from PIL import Image

_VERTEX = re.compile(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)')


def load_stl(path):
    txt = open(path, encoding='utf-8', errors='ignore').read()
    v = np.array(_VERTEX.findall(txt), dtype=float)
    return v.reshape(-1, 3, 3) if len(v) else np.zeros((0, 3, 3))


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def view_matrix(name):
    """Dunya (x,y,z) -> ekran (sag, yukari, kameraya dogru). Satirlar ekran eksenleri."""
    if name == 'top':        # yukaridan: on yukari, robotun sagi ekranin sagi
        return np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], float)
    if name == 'front':      # onden: robotun solu ekranin sagi
        return np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)
    if name == 'side':       # sag yandan: on sagda
        return np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)
    if name == 'iso':        # on-sol-ust capraz
        az, el = math.radians(-35), math.radians(28)           # on-sol-ust: robotun on yuzu ve SOL yani gorunur
        rz = np.array([[math.cos(az), -math.sin(az), 0], [math.sin(az), math.cos(az), 0], [0, 0, 1]])
        base = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)        # kamera robotun ONUNDE (onden gorunum)
        rx = np.array([[1, 0, 0], [0, math.cos(el), -math.sin(el)], [0, math.sin(el), math.cos(el)]])
        return rx @ base @ rz
    raise ValueError(name)


def render(parts, view, size=(900, 700), ss=2, margin=0.06, bg=(247, 245, 238), fit=None):
    """parts: [(ad, ucgenler (N,3,3), renk)] -> PIL.Image. fit: (min, max) ekran siniri verilirse sabit olcek."""
    R = view_matrix(view)
    W, H = size[0] * ss, size[1] * ss
    tris, cols, ids = [], [], []
    for i, (_n, t, c) in enumerate(parts):
        if len(t) == 0:
            continue
        tris.append(t @ R.T)
        cols.append(np.tile(np.array(hex_rgb(c) if isinstance(c, str) else c, float), (len(t), 1)))
        ids.append(np.full(len(t), i))
    T = np.concatenate(tris)
    C = np.concatenate(cols)
    I = np.concatenate(ids)
    if fit is None:
        lo, hi = T[..., :2].reshape(-1, 2).min(0), T[..., :2].reshape(-1, 2).max(0)
    else:
        lo, hi = np.array(fit[0]), np.array(fit[1])
    scale = min(W * (1 - 2 * margin) / (hi[0] - lo[0]), H * (1 - 2 * margin) / (hi[1] - lo[1]))
    off = np.array([W / 2 - scale * (lo[0] + hi[0]) / 2, H / 2 + scale * (lo[1] + hi[1]) / 2])
    px = T[..., 0] * scale + off[0]
    py = -T[..., 1] * scale + off[1]
    pz = T[..., 2]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(n, axis=1)
    ok = ln > 1e-9
    n[ok] /= ln[ok, None]
    light = np.array([-0.35, 0.55, 0.75])
    light /= np.linalg.norm(light)
    shade = 0.45 + 0.55 * np.clip(np.abs(n @ light) * 0.6 + np.clip(n @ light, 0, 1) * 0.4, 0, 1)
    zbuf = np.full((H, W), -1e18)
    img = np.empty((H, W, 3))
    img[:] = bg
    idb = np.full((H, W), -1, np.int32)
    for k in range(len(T)):
        if not ok[k]:
            continue
        x0, x1, x2 = px[k]
        y0, y1, y2 = py[k]
        xa, xb = int(max(math.floor(min(x0, x1, x2)), 0)), int(min(math.ceil(max(x0, x1, x2)), W - 1))
        ya, yb = int(max(math.floor(min(y0, y1, y2)), 0)), int(min(math.ceil(max(y0, y1, y2)), H - 1))
        if xb < xa or yb < ya:
            continue
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-9:
            continue
        gx, gy = np.meshgrid(np.arange(xa, xb + 1) + 0.5, np.arange(ya, yb + 1) + 0.5)
        l0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / den
        l1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / den
        l2 = 1 - l0 - l1
        inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        if not inside.any():
            continue
        z = l0 * pz[k, 0] + l1 * pz[k, 1] + l2 * pz[k, 2]
        sub = zbuf[ya:yb + 1, xa:xb + 1]
        upd = inside & (z > sub)
        if not upd.any():
            continue
        sub[upd] = z[upd]
        img[ya:yb + 1, xa:xb + 1][upd] = C[k] * shade[k]
        idb[ya:yb + 1, xa:xb + 1][upd] = I[k]
    # kenarlar: parca kimligi degisen ya da derinlik atlayan pikseller
    edge = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0)):
        a, b = idb[:H - dy, :W - dx], idb[dy:, dx:]
        e = a != b
        edge[:H - dy, :W - dx] |= e
        edge[dy:, dx:] |= e
        za, zb = zbuf[:H - dy, :W - dx], zbuf[dy:, dx:]
        valid = (a >= 0) & (b >= 0)
        jump = valid & (np.abs(za - zb) > 0.9 * (hi - lo).max() * 0.02)
        edge[:H - dy, :W - dx] |= jump
    img[edge] = img[edge] * 0.35
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return out.resize(size, Image.LANCZOS) if ss > 1 else out
