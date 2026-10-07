"""Teknik resim cizimi icin kucuk SVG yardimcilari (bagimlilik yok)."""
from xml.sax.saxutils import escape

INK = '#1d2b2a'
PAPER = '#f7f5ee'
BODY = '#e6c88f'
WHEEL = '#2b2b2b'
SENSOR = '#2f6fbd'
DIM = '#b3261e'
GRID = '#d8d3c4'
FONT = "Atkinson Hyperlegible, 'Segoe UI', Arial, sans-serif"


class Svg:
    def __init__(self, w, h, title, desc):
        self.w, self.h = w, h
        self.parts = [f'<rect width="{w}" height="{h}" fill="{PAPER}"/>']
        self.title, self.desc = title, desc

    def add(self, s):
        self.parts.append(s)

    def line(self, x1, y1, x2, y2, stroke=INK, sw=1.5, dash=None, extra=''):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{d} {extra}/>')

    def rect(self, x, y, w, h, fill='none', stroke=INK, sw=1.5, dash=None, rx=0):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, cx, cy, r, fill='none', stroke=INK, sw=1.5, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def poly(self, pts, fill='none', stroke=INK, sw=1.5, opacity=1.0):
        p = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
        self.add(f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" fill-opacity="{opacity}"/>')

    def text(self, x, y, s, size=15, anchor='start', fill=INK, weight='400', rotate=None, italic=False):
        r = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate else ''
        st = ' font-style="italic"' if italic else ''
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" text-anchor="{anchor}" '
                 f'fill="{fill}" font-weight="{weight}"{st}{r}>{escape(s)}</text>')

    def arrow_defs(self):
        return (f'<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                f'<path d="M0 0 L10 5 L0 10 z" fill="{DIM}"/></marker></defs>')

    def dim_h(self, x1, x2, y, label, off=0, ext_from=None, size=14):
        """Yatay olcu cizgisi: x1..x2 arasi, y yuksekliginde. ext_from: uzatma cizgilerinin geldigi y."""
        if ext_from is not None:
            self.line(x1, ext_from, x1, y + (6 if y > ext_from else -6), DIM, 0.8)
            self.line(x2, ext_from, x2, y + (6 if y > ext_from else -6), DIM, 0.8)
        self.line(x1, y, x2, y, DIM, 1.1, extra='marker-start="url(#ar)" marker-end="url(#ar)"')
        self.text((x1 + x2) / 2 + off, y - 5, label, size, 'middle', DIM)

    def dim_v(self, y1, y2, x, label, ext_from=None, size=14, side='right', rot=False):
        if ext_from is not None:
            self.line(ext_from, y1, x + (6 if x > ext_from else -6), y1, DIM, 0.8)
            self.line(ext_from, y2, x + (6 if x > ext_from else -6), y2, DIM, 0.8)
        self.line(x, y1, x, y2, DIM, 1.1, extra='marker-start="url(#ar)" marker-end="url(#ar)"')
        if rot:
            self.text(x + (16 if side == 'right' else -8), (y1 + y2) / 2, label, size, 'middle', DIM, rotate=-90 if side == 'left' else 90)
            return
        tx = x + 6 if side == 'right' else x - 6
        self.text(tx, (y1 + y2) / 2 + 5, label, size, 'start' if side == 'right' else 'end', DIM)

    def title_block(self, name, sub, scale_note, source, width=510):
        w, h = self.w, self.h
        self.rect(10, 10, w - 20, h - 20, 'none', INK, 2)
        x, y, bw, bh = w - width - 10, h - 110, width, 100
        self.rect(x, y, bw, bh, PAPER, INK, 1.5)
        self.line(x, y + 38, x + bw, y + 38, INK, 1)
        self.text(x + 12, y + 28, name, 22, 'start', INK, '700')
        self.text(x + 12, y + 58, sub, 14)
        self.text(x + 12, y + 78, scale_note, 13)
        self.text(x + 12, y + 94, source, 12, fill='#555')

    def save(self, path):
        body = '\n'.join(self.parts)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
               f'role="img" aria-labelledby="t d"><title id="t">{escape(self.title)}</title><desc id="d">{escape(self.desc)}</desc>'
               f'{self.arrow_defs()}{body}</svg>')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(svg)
