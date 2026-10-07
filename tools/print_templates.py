"""1:1 paper templates, drawn straight from the DXF files you would upload.

Because it reads the cut files rather than the model, the paper always shows
exactly what the laser would cut - including after you customize the design.

    python tools/print_templates.py                      # Letter paper
    python tools/print_templates.py --paper a4
    python tools/print_templates.py --dir path/to/upload --out my_templates.pdf

PRINT AT 100% / "Actual size". Never "Fit to page". Every sheet has a 100 mm
bar: measure it with a ruler before you trust anything else on the page.

    solid black   cut line
    dashed red    fold line, labelled UP or DOWN and the angle.
                  UP = toward you, the printed side.
    blue circle   tapped hole (the vendor drills and taps these)

Parts wider than the page are split into tiles that OVERLAP. Line the tiles
up on the dashed seam marks. Do not butt the paper edges together.
"""
import argparse
import glob
import math
import os

import ezdxf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                              # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(HERE, "..", "out", "production_v94", "upload")
PAPER = {"letter": (279.4, 215.9), "a4": (297.0, 210.0)}   # landscape, mm
MARGIN = 12.0          # mm kept clear of the paper edge (printer margins)
HEAD = 22.0            # mm reserved at the top for the title block
FOOT = 22.0            # mm reserved at the bottom for the scale bar
OVERLAP = 15.0         # mm of part repeated on neighbouring tiles
INK, FOLD, TAP, MUTED = "#111418", "#c0392b", "#1f5fbf", "#5b6874"


def read_part(path):
    """Cut polylines, cut circles, tap circles and fold lines, in mm."""
    part = dict(cut=[], circles=[], taps=[], folds=[])
    for e in ezdxf.readfile(path).modelspace():
        t, layer = e.dxftype(), e.dxf.layer.upper()
        if t == "LWPOLYLINE" and layer == "CUT":
            pts = [tuple(p) for p in e.get_points("xy")]
            if e.closed:
                pts.append(pts[0])
            part["cut"].append(pts)
        elif t == "CIRCLE":
            c = (e.dxf.center.x, e.dxf.center.y, e.dxf.radius)
            (part["taps"] if layer == "TAP" else part["circles"]).append(c)
        elif t == "LINE" and layer.startswith("BEND"):
            bits = layer.split("_")             # BEND_UP_45 -> UP, 45
            label = " ".join(b for b in bits[1:])
            if len(bits) == 3:
                label = "%s %s°" % (bits[1], bits[2])
            part["folds"].append(((e.dxf.start.x, e.dxf.start.y),
                                  (e.dxf.end.x, e.dxf.end.y), label))
    xs = [x for pl in part["cut"] for x, _ in pl]
    ys = [y for pl in part["cut"] for _, y in pl]
    part["box"] = (min(xs), min(ys), max(xs), max(ys))
    return part


def draw_geometry(ax, part):
    for pl in part["cut"]:
        ax.plot([p[0] for p in pl], [p[1] for p in pl], color=INK, lw=0.6)
    for x, y, r in part["circles"]:
        ax.add_patch(plt.Circle((x, y), r, fill=False, color=INK, lw=0.6))
    for x, y, r in part["taps"]:
        ax.add_patch(plt.Circle((x, y), r, fill=False, color=TAP, lw=0.8))
    for (x0, y0), (x1, y1), label in part["folds"]:
        ax.plot([x0, x1], [y0, y1], color=FOLD, lw=0.8, ls=(0, (4, 3)))
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        if ang > 90:
            ang -= 180
        if ang < -90:
            ang += 180
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, " " + label + " ", color=FOLD,
                fontsize=6.5, rotation=ang, ha="center", va="bottom",
                rotation_mode="anchor", family="sans-serif", fontweight="bold")


def scale_bar(page, x, y):
    page.plot([x, x + 100], [y, y], color=INK, lw=1.2)
    for i in range(11):
        h = 3.0 if i % 5 == 0 else 1.8
        page.plot([x + 10 * i, x + 10 * i], [y, y + h], color=INK, lw=0.8)
    page.text(x + 104, y, "100 mm  -  MEASURE THIS FIRST", fontsize=8,
              va="center", family="sans-serif", fontweight="bold", color=INK)


def pages_for(part, name, pw, ph, pdf):
    x0, y0, x1, y1 = part["box"]
    pad = 3.0
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    w, h = x1 - x0, y1 - y0
    if h > ph - 2 * MARGIN - HEAD - FOOT:      # too tall for landscape: try portrait
        pw, ph = ph, pw
    usable_w = pw - 2 * MARGIN
    usable_h = ph - 2 * MARGIN - HEAD - FOOT
    if h > usable_h:
        raise SystemExit("%s is %.0f mm tall; it does not fit this paper either way up."
                         % (name, h))
    n = 1 if w <= usable_w else math.ceil((w - OVERLAP) / (usable_w - OVERLAP))
    step = (w - OVERLAP) / n + OVERLAP if n > 1 else w
    for k in range(n):
        tx0 = x0 + k * (step - OVERLAP)
        tw = min(step, x1 - tx0)
        fig = plt.figure(figsize=(pw / 25.4, ph / 25.4))
        page = fig.add_axes([0, 0, 1, 1])
        page.set_xlim(0, pw)
        page.set_ylim(0, ph)
        page.axis("off")
        title = name if n == 1 else "%s   -   sheet %d of %d" % (name, k + 1, n)
        page.text(MARGIN, ph - MARGIN - 4, title, fontsize=11, fontweight="bold",
                  family="sans-serif", color=INK)
        page.text(MARGIN, ph - MARGIN - 10,
                  "PRINT AT 100% (actual size). Solid = cut. Dashed red = fold, UP = toward you. "
                  "Blue = tapped hole.", fontsize=7.5, family="sans-serif", color=MUTED)
        if name.startswith("backplate"):
            page.text(MARGIN, ph - MARGIN - 15,
                      "Outside face, seen from outside: lay it on the card INK UP.",
                      fontsize=7.5, family="sans-serif", color=MUTED)
        scale_bar(page, MARGIN, MARGIN + 6)
        # the part, at exactly 1:1: axes size in inches == window size in mm / 25.4
        left, bottom = MARGIN, MARGIN + FOOT + (usable_h - h) / 2
        ax = fig.add_axes([left / pw, bottom / ph, tw / pw, h / ph])
        ax.set_xlim(tx0, tx0 + tw)
        ax.set_ylim(y0, y1)
        ax.axis("off")
        draw_geometry(ax, part)
        if n > 1:
            for sx, txt in ((tx0 + OVERLAP, "overlap from previous sheet") if k else (None, None),
                            (tx0 + tw - OVERLAP, "overlap onto next sheet") if k < n - 1 else (None, None)):
                if sx is None:
                    continue
                ax.axvline(sx, color=MUTED, lw=0.7, ls=(0, (2, 2)))
                ax.text(sx, y1, " " + txt + " - align here, DO NOT BUTT", fontsize=6,
                        color=MUTED, rotation=90, va="top", ha="left", family="sans-serif")
        pdf.savefig(fig)
        plt.close(fig)
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default=DEFAULT_DIR, help="folder of DXF cut files")
    ap.add_argument("--out", default=None, help="output PDF path")
    ap.add_argument("--paper", choices=sorted(PAPER), default="letter")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.dir, "*.dxf")))
    if not files:
        raise SystemExit("no .dxf files in %s - run cad/make_v94.py first" % a.dir)
    out = a.out or os.path.join(os.path.dirname(os.path.normpath(a.dir)), "templates_1to1_%s.pdf" % a.paper)
    pw, ph = PAPER[a.paper]
    total = 0
    with PdfPages(out) as pdf:
        for f in files:
            name = os.path.splitext(os.path.basename(f))[0]
            n = pages_for(read_part(f), name, pw, ph, pdf)
            total += n
            print("  %-34s %d sheet%s" % (name, n, "" if n == 1 else "s"))
    print("wrote %s  (%d sheets, %s)" % (os.path.normpath(out), total, a.paper))


if __name__ == "__main__":
    main()
