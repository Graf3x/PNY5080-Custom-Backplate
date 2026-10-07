"""A period-correct template-matching OCR, used to VERIFY the wordmark is legible.

No OCR engine is installed on this machine and the Tesseract binary is not
installable here, so this is the kind of recogniser that actually predates
them: binarise, segment into connected components, normalise each to a fixed
grid, and correlate against a template set. That is how OCR worked from the
1960s through the 1980s, and it is font-specific by design - those systems
shipped templates per typeface, which is why OCR-A and OCR-B exist.

WHY THIS IS A REAL TEST AND NOT A RUBBER STAMP
    The template set is all 36 alphanumerics, not the six characters we are
    hoping to find. A glyph only counts as read if its best match ACROSS ALL
    36 is the correct class, with a margin over the runner-up. A design that
    merely leaves "something letter-shaped" fails, because the something has to
    beat 35 alternatives.

    The page is also rendered the way a flatbed would see the finished plate:
    metal light, cuts dark, at a scanner-like resolution, with no anti-aliasing
    help. If the carrier pattern breaks a stroke, the correlation drops and the
    character is misread - which is exactly the failure we are testing for.

WHAT IT DOES NOT PROVE
    It is font-matched, so it shows the letterform SURVIVES THE CARRIER. It
    does not prove an arbitrary modern OCR would read it, and it is not a
    substitute for looking at the thing.
"""

from __future__ import annotations

import os
import string
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CLASSES = (string.ascii_uppercase + string.ascii_lowercase
           + string.digits)                           # 62 templates
# Case matters: the mark is "Graf3X", with lowercase r, a and f. An
# uppercase-only set forces those onto the nearest capital and the read
# fails for a reason that has nothing to do with the design.
GRID = 28                                             # normalisation grid
DPI_MM = 6.0                                          # px per mm when rendering


def _font(size):
    from PIL import ImageFont
    from config import BRAND
    return ImageFont.truetype(BRAND.FONT, size)


def templates(grid=GRID):
    """One normalised bitmap per class, from the same face as the mark."""
    out = {}
    f = _font(96)
    for ch in CLASSES:
        im = Image.new("L", (160, 160), 0)
        d = ImageDraw.Draw(im)
        d.text((80, 80), ch, fill=255, font=f, anchor="mm")
        a = np.asarray(im)
        ys, xs = np.where(a > 60)
        if not len(xs):
            continue
        out[ch] = _norm(a[ys.min():ys.max() + 1, xs.min():xs.max() + 1], grid)
    return out


def _norm(patch, grid=GRID):
    im = Image.fromarray(patch.astype(np.uint8)).resize((grid, grid), Image.BILINEAR)
    a = np.asarray(im).astype(float)
    a -= a.mean()
    n = np.linalg.norm(a)
    return a / n if n > 1e-9 else a


def render(geom, field, mark_box, dpi_mm=DPI_MM):
    """Render the plate as a flatbed would see it: metal light, cuts dark."""
    x0, y0, x1, y1 = mark_box
    w = int((x1 - x0) * dpi_mm)
    h = int((y1 - y0) * dpi_mm)
    im = Image.new("L", (w, h), 255)                 # metal
    d = ImageDraw.Draw(im)
    parts = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    for p in parts:
        xs, ys = p.exterior.xy
        d.polygon([((x - x0) * dpi_mm, (y1 - y) * dpi_mm) for x, y in zip(xs, ys)],
                  fill=0)                            # cut
        for r in p.interiors:
            xs, ys = r.xy
            d.polygon([((x - x0) * dpi_mm, (y1 - y) * dpi_mm)
                       for x, y in zip(xs, ys)], fill=255)
    return im


def segment(im, min_px=40):
    """Connected dark components, left to right - the classic segmenter."""
    from scipy import ndimage as ndi
    a = np.asarray(im) < 128
    lab, n = ndi.label(a)
    boxes = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(xs) < min_px:
            continue
        boxes.append((xs.min(), ys.min(), xs.max(), ys.max(), i))
    boxes.sort(key=lambda b: b[0])
    return lab, boxes


def read(geom, field, mark_box, expect="Graf3X", verbose=False):
    """Segment, normalise, correlate against all 36. Returns (text, details)."""
    T = templates()
    im = render(geom, field, mark_box)
    lab, boxes = segment(im)
    got, detail = [], []
    for (bx0, by0, bx1, by1, i) in boxes:
        patch = (lab[by0:by1 + 1, bx0:bx1 + 1] == i).astype(float) * 255
        if patch.shape[0] < 6 or patch.shape[1] < 3:
            continue
        v = _norm(patch)
        scores = sorted(((float((v * t).sum()), ch) for ch, t in T.items()),
                        reverse=True)
        best, second = scores[0], scores[1]
        got.append(best[1])
        detail.append(dict(ch=best[1], score=best[0], margin=best[0] - second[0],
                           runner_up=second[1], box=(bx0, by0, bx1, by1)))
    text = "".join(got)
    if verbose:
        print(f"   segmented {len(boxes)} component(s) -> {text!r}")
        for d in detail:
            print(f"      {d['ch']}  score {d['score']:.3f}  "
                  f"margin {d['margin']:+.3f} over {d['runner_up']}")
    return text, detail


def verdict(text, detail, expect=None, min_score=0.55, min_margin=0.03):
    """Pass only if every expected character reads correctly and confidently.

    `expect` defaults to config.BRAND.TEXT, so changing the wordmark there is
    all it takes for the OCR to check the new text. Letters and digits only:
    the template set has no punctuation or spaces.
    """
    if expect is None:
        from config import BRAND
        expect = BRAND.TEXT
    if text != expect:
        return False, f"read {text!r}, expected {expect!r}"
    weak = [d for d in detail if d["score"] < min_score or d["margin"] < min_margin]
    if weak:
        return False, ("reads correctly but weakly: " +
                       ", ".join(f"{d['ch']} {d['score']:.2f}/{d['margin']:+.2f}"
                                 for d in weak))
    return True, "all %d read, with margin" % len(expect)


if __name__ == "__main__":
    T = templates()
    print(f"{len(T)} templates at {GRID}x{GRID}, from the wordmark's own face")
    # sanity: the templates must recognise themselves and not each other
    # Case-mates that differ only in size (C/c, S/s, X/x, W/w, Z/z, O/o, 0)
    # legitimately collide once each is normalised to the same grid - that is a
    # known limit of size-normalised template matching, not a fault. Assert on
    # the six characters we actually have to read.
    worst, bad = 1.0, []
    for ch in "Graf3X":
        t = T[ch]
        sc = sorted(((float((t * u).sum()), c) for c, u in T.items()), reverse=True)
        if sc[0][1] != ch:
            bad.append(f"{ch}->{sc[0][1]}")
        worst = min(worst, sc[0][0] - sc[1][0])
    print(f"the six mark characters: "
          f"{'all recognise themselves' if not bad else 'COLLIDE: ' + ','.join(bad)}")
    print(f"tightest margin among them {worst:.3f}")
