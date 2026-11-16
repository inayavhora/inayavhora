"""
wiredraw: the line-drawing kit for The Wire's weekly study sheets.

Every sheet follows the same rules, so the drawings read as one set:
  - Reported elements only: draw what the source reporting describes, nothing invented.
  - Plain line work: one ink, two weights, no fills except white to hide lines behind objects.
  - Numbered keynotes beside each element; descriptions live in the legend panel, not on the drawing,
    so no leader lines cross the drawing.
  - A system strip along the bottom shows how information flows (sensors -> analysis -> person).
  - A title block with the story, the place, the sources and "Reported elements only".

Sheet size 1200 x 800 (SVG units). Drawing area x 30..760, y 40..560; legend x 790..1170.

Usage:
    from wiredraw import Sheet
    s = Sheet()
    s.plot(...); s.mast(...); s.keynote(1, x, y) ...
    s.legend([...]); s.flow([...]); s.title_block(...)
    s.save("drawings/2026-11-baramati.svg")
"""
import math

INK = "#1c1c1b"
GREY = "#9a968e"
PAPER = "#ffffff"
MONO = "IBM Plex Mono, Menlo, Consolas, monospace"
SANS = "Instrument Sans, Helvetica Neue, Arial, sans-serif"


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Sheet:
    W, H = 1200, 800

    def __init__(self, scale=6.0, origin=(400, 170)):
        self.S, self.O = scale, origin
        self.out = []

    # ---------------------------------------------------------------- projection (isometric, metres)
    def p(self, x, y, z):
        """x east, z south (towards the viewer), y up -> screen point."""
        c30, s30 = math.cos(math.pi / 6), 0.5
        return (self.O[0] + (x - z) * c30 * self.S, self.O[1] + (x + z) * s30 * self.S - y * self.S)

    # ---------------------------------------------------------------- primitives (screen space)
    def line(self, a, b, w=1.0, col=INK, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{col}" stroke-width="{w}" stroke-linecap="round"{d}/>')

    def poly(self, pts, w=1.0, col=INK, fill="none", dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        pp = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.out.append(f'<polygon points="{pp}" fill="{fill}" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"{d}/>')

    def pline(self, pts, w=1.0, col=INK, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        pp = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.out.append(f'<polyline points="{pp}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"{d}/>')

    def circle(self, c, r, w=1.0, col=INK, fill=PAPER):
        self.out.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{r}" fill="{fill}" stroke="{col}" stroke-width="{w}"/>')

    def rect(self, x, y, w, h, sw=1.0, col=INK, fill=PAPER, rx=0):
        self.out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{col}" stroke-width="{sw}"/>')

    def text(self, x, y, t, size=11, col=INK, anchor="start", weight=400, font=MONO):
        self.out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{col}" font-size="{size}" font-family="{font}" font-weight="{weight}" text-anchor="{anchor}">{esc(t)}</text>')

    def arrow(self, a, b, w=1.0, col=INK):
        self.line(a, b, w, col)
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        for d in (2.6, -2.6):
            self.line(b, (b[0] - 7 * math.cos(ang + d / 6), b[1] - 7 * math.sin(ang + d / 6)), w, col)

    # ---------------------------------------------------------------- world-space helpers
    def wline(self, a, b, **k):
        self.line(self.p(*a), self.p(*b), **k)

    def wpoly(self, pts, **k):
        self.poly([self.p(*q) for q in pts], **k)

    def box(self, x0, y0, z0, x1, y1, z1, w=1.0):
        """A solid block; visible faces are top, south (z1) and east (x1)."""
        P = self.p
        self.poly([P(x0, y1, z0), P(x1, y1, z0), P(x1, y1, z1), P(x0, y1, z1)], w, fill=PAPER)
        self.poly([P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], w, fill=PAPER)
        self.poly([P(x1, y0, z0), P(x1, y0, z1), P(x1, y1, z1), P(x1, y1, z0)], w, fill=PAPER)

    def dim(self, a, b, label, off=(0, 0, 0)):
        """Dimension line between two world points, offset by `off` (world), label at the middle."""
        A = self.p(a[0] + off[0], a[1] + off[1], a[2] + off[2]); B = self.p(b[0] + off[0], b[1] + off[1], b[2] + off[2])
        self.line(A, B, 0.6, GREY)
        for q in (A, B):
            self.line((q[0] - 4, q[1] + 4), (q[0] + 4, q[1] - 4), 0.8, GREY)
        mx, my = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
        ang = math.degrees(math.atan2(B[1] - A[1], B[0] - A[0]))
        if ang > 90 or ang < -90:
            ang += 180
        self.out.append(f'<text x="{mx:.1f}" y="{my - 6:.1f}" fill="{GREY}" font-size="10" font-family="{MONO}" text-anchor="middle" transform="rotate({ang:.1f} {mx:.1f} {my - 6:.1f})">{esc(label)}</text>')

    # ---------------------------------------------------------------- annotation
    def keynote(self, n, at, to=None):
        """Numbered circle at screen point `at`; optional short tick to the element at `to`."""
        if to:
            self.line(to, at, 0.6)
            self.circle(to, 1.8, 0, INK, INK)
        self.circle(at, 9, 1.0)
        self.text(at[0], at[1] + 3.6, str(n), 10, anchor="middle", weight=500)

    def legend(self, items, x=790, y=60, width=380):
        """items: list of (n, title, detail) - detail may be a list of short lines."""
        self.text(x, y, "KEYNOTES", 10, GREY, weight=500)
        yy = y + 22
        for n, title, detail in items:
            self.circle((x + 9, yy - 4), 9, 1.0)
            self.text(x + 9, yy - 0.4, str(n), 10, anchor="middle", weight=500)
            self.text(x + 28, yy, title, 11.5, weight=500, font=SANS)
            lines = detail if isinstance(detail, list) else [detail]
            for i, t in enumerate(lines):
                self.text(x + 28, yy + 15 + i * 13.5, t, 10.5, GREY, font=SANS)
            yy += 24 + len(lines) * 13.5 + 6
        return yy

    def notes(self, heading, lines, x=790, y=500):
        self.text(x, y, heading.upper(), 10, GREY, weight=500)
        for i, t in enumerate(lines):
            self.text(x, y + 18 + i * 14.5, t, 11, font=SANS)
        return y + 18 + len(lines) * 14.5

    def flow(self, steps, y=600, x0=30, x1=760, h=58):
        """A left-to-right strip of boxes joined by arrows: how the information travels."""
        self.text(x0, y - 12, "HOW THE ADVICE TRAVELS", 10, GREY, weight=500)
        n, gap = len(steps), 22
        bw = (x1 - x0 - gap * (n - 1)) / n
        for i, step in enumerate(steps):
            bx = x0 + i * (bw + gap)
            self.rect(bx, y, bw, h, 1.0)
            lines = step if isinstance(step, list) else [step]
            for j, t in enumerate(lines):
                self.text(bx + bw / 2, y + 18 + j * 13, t, 10 if j else 10.5, INK if j == 0 else GREY, "middle", 500 if j == 0 else 400, SANS)
            if i < n - 1:
                self.arrow((bx + bw + 3, y + h / 2), (bx + bw + gap - 3, y + h / 2), 1.0)

    def title_block(self, number, title, place, source, credit="Inaya Vhora", date=""):
        y = 700
        self.line((30, y), (1170, y), 1.0)
        self.text(30, y + 22, f"THE WIRE · STUDY {number:02d}", 11, weight=500)
        self.text(30, y + 40, title, 12.5, font=SANS, weight=500)
        self.text(30, y + 58, place, 10.5, GREY)
        self.text(30, y + 76, "Reported elements only. Drawn from the sources listed; not to scale unless dimensioned.", 10.5, GREY)
        self.text(1170, y + 22, credit, 11, anchor="end", weight=500)
        self.text(1170, y + 40, date, 10.5, GREY, "end")
        for i, s in enumerate(source if isinstance(source, list) else [source]):
            self.text(1170, y + 58 + i * 15, s, 10, GREY, "end")

    def view(self, scale, origin):
        """Switch projection, e.g. for an enlarged detail. Returns the previous (scale, origin)."""
        prev = (self.S, self.O)
        self.S, self.O = scale, origin
        return prev

    def detail_frame(self, x, y, w, h, label, caption):
        self.rect(x, y, w, h, 0.8)
        self.circle((x + 16, y + 16), 10, 1.0)
        self.text(x + 16, y + 20, label, 11, anchor="middle", weight=500)
        self.text(x + 32, y + 20, caption, 10, GREY)

    def marker(self, label, at):
        """A lettered callout on the main drawing that points to a detail."""
        self.circle(at, 10, 1.0)
        self.text(at[0], at[1] + 4, label, 11, anchor="middle", weight=500)

    # ---------------------------------------------------------------- save
    def save(self, path):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" width="{self.W}" height="{self.H}">'
               f'<rect width="{self.W}" height="{self.H}" fill="{PAPER}"/>' + "".join(self.out) + "</svg>")
        with open(path, "w") as f:
            f.write(svg)
        return path
