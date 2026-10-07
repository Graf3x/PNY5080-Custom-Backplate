"""Iterations on the eight shortlisted vent fields, their groups, and Graf3X.

SHORTLIST (owner, 2026-08-24): Ghost Bone, Truss, Crossover, Interference,
Lamination, Kowloon Graft rotated 180, Twill, Ghost Chevron.

WHAT THE EIGHT HAVE IN COMMON
    Not a look - a method. Every one is a SINGLE GLOBAL RULE SAMPLED ACROSS
    THE FIELD. None is a composition; none has a focal point placed by hand.
    The design lives in the rule, and what differs is only what the rule reads:

      a lattice reads a modulating figure or field   (Ghost Bone, Ghost
                                                      Chevron, Interference,
                                                      Twill)
      a band family reads a scalar that sweeps       (Crossover, Lamination)
      a network reads a set of nodes                 (Truss, Kowloon Graft)

    So the plate is a READOUT OF A FUNCTION, not an arrangement of shapes.
    That is the thread, and it is also why these eight sit together while the
    minimal compositions and the one-off gestures did not make the cut.

WHAT THAT IMPLIES FOR THE WORDMARK
    If the thread holds, Graf3X must not be a shape cut into the plate - that
    would be the one composed object in a field of sampled rules, and it would
    read as a sticker. It has to be WHAT THE RULE READS: the letters become the
    modulating field, and the lattice, bands or network resolve them. That is
    also exactly what the project archive already discovered twice, in
    'ghost-x' (halftone screen behind the wordmark) and 'inverse' (mesh cut
    away, letters left as solid metal).
"""

from __future__ import annotations

import math

import numpy as np
from shapely.affinity import rotate, scale, translate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import vent_kit as K
import vent_gallery as G1
import vent_gallery2 as G2
from die_window import CENTRE as DIE_C, POLY as DIE_POLY

NOTE = {}


# Where the wordmark sits. Moved 2026-08-24 from the field's centre to the
# bottom-right corner, below the cable cover's horizontal leg.
#
# The cover crosses the field at Y 52.9-99.9 (its horizontal leg) and again at
# X 239.5-286.5 (the leg dropping to the PSU). That leaves a clear band along
# the connector side, Y 12.0-52.9, 40.9 mm tall and running the full length.
# The mark is set in the right-hand end of it, so it reads under the cover
# rather than being crossed by it.
TRACK_BUMP = 2.2      # extra letter-spacing. At 82 mm the G and the r sit
                      # 3.78 mm apart, and a usable clearance takes the web
                      # between them under 2.0 mm - they would fuse in metal
                      # whatever the buffer does. Spacing them is the fix.
MARK_CLEAR = 1.4      # clearance round the letters. Was 2.0, which closed the
                      # 3.78 mm gap between the G and the r and blobbed them
                      # into one shape - a 2.0 buffer shuts any gap under 4.0.
MARK_W = 90.0                   # 82 -> 90 with the font change; see the
                               # sweep in config.BRAND. At 82 Bahnschrift
                               # cuts and webs fine but the X reads weakly.
MARK_CENTRE = (252.0, 31.0)   # X toward the plate end, Y below the cover


from config import MFG

MARK_NECK_MIN = 2.05
NECK_DILATE_CAP = 1.20          # most a single glyph may be fattened before
                                # the answer is a bigger mark, not a fatter one
PINCH_SKIP = 2.0                # arc below which two edges of one ring
                                # are merely going round a corner together           # a hair over MFG.MIN_FEATURE


def _neck(poly):
    """The width at which a contour SPLITS - not the width at which it vanishes.

    That distinction is the whole bug. Testing buffer(-w/2).is_empty only fires
    when the entire shape disappears, so a big glyph with a thin waist sails
    through: it does not vanish, it splits in two. Three glyphs were 1.547,
    1.729 and 1.738 mm and nothing had ever seen them.
    """
    lo, hi = 0.0, 4.0
    for _ in range(44):
        m = (lo + hi) / 2.0
        b = poly.buffer(-m / 2.0)
        n = 0 if b.is_empty else (1 if b.geom_type == "Polygon" else len(b.geoms))
        if n != 1:
            hi = m
        else:
            lo = m
    return lo


def _pinch(poly):
    """Narrowest OPENING between two non-adjacent edges of the same boundary.

    The split test above and this one fail in opposite directions and neither
    subsumes the other. _neck() finds a waist that SEVERS a contour. It cannot
    find a tooth reaching back toward its own root, because closing that throat
    changes no piece count - a C stays a C. That is how a 1.889 mm throat
    inside one glyph passed _neck at 2.09, passed the erosion test, passed the
    OCR, and went into a production DXF: every check in the project measured
    something the defect was not.
    """
    from shapely.geometry import LineString, Point
    from shapely.ops import nearest_points
    best = 99.0
    for g in ([poly] if poly.geom_type == "Polygon" else poly.geoms):
        rings = [list(g.exterior.coords)[:-1]]
        rings += [list(r.coords)[:-1] for r in g.interiors]
        for ring in rings:
            n = len(ring)
            if n < 6:
                continue
            segs = [LineString([ring[i], ring[(i + 1) % n]]) for i in range(n)]
            cum = [0.0]
            for sg in segs:
                cum.append(cum[-1] + sg.length)
            tot = cum[-1]
            for i in range(n):
                for j in range(i + 2, n):
                    if i == 0 and j == n - 1:
                        continue
                    fwd = cum[j] - cum[i + 1]
                    bwd = tot - cum[j + 1] + cum[i]
                    if min(fwd, bwd) < PINCH_SKIP:
                        continue        # just rounding a corner together
                    d = segs[i].distance(segs[j])
                    if d >= best:
                        continue
                    # WHICH SIDE OF THE THROAT IS AIR. A pair of edges this
                    # close is either a narrow OPENING (dilating the glyph
                    # widens it) or a TOOTH of metal poking into the glyph
                    # (dilating THINS it). Every sub-millimetre pair in this
                    # face is the second kind, and dilating on those numbers
                    # made two glyphs worse - 1.389 to 1.252 - while the real
                    # 1.889 opening went untouched. Metal is the plate's
                    # problem and the erosion test already owns it; here we
                    # only widen air.
                    p1, p2 = nearest_points(segs[i], segs[j])
                    mid = Point((p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0)
                    if not g.contains(mid):
                        continue
                    best = d
    return best


def _open_necks(g):
    """Thicken ONLY the glyphs that pinch, and only by what they need.

    Dilating every glyph the same amount does clear the necks, but it also
    rounds the X until the recogniser prefers a lowercase x: at a uniform
    0.20 mm the mark still read Graf3X and the X's margin over its runner-up
    fell to +0.00, which the verdict rejects. Per-glyph, the X is never
    touched and its score stays where it was.
    """
    from shapely.ops import unary_union as _uu
    out = []
    for p in (g.geoms if g.geom_type != "Polygon" else [g]):
        # BOTH measures. A glyph can be wide everywhere it would split and
        # still have a throat that no laser will cut.
        #
        # AND IT TAKES MORE THAN ONE PASS. One buffer of (MIN - w)/2 assumes
        # the two walls of the throat move apart by the full 2r. They do not:
        # where the throat is flanked by a re-entrant tooth the tip advances
        # with the buffer and eats most of the gain, so a single pass aimed at
        # 2.05 landed at 1.99 and the DXF shipped a 1.889 mm opening. Iterate
        # on the MEASUREMENT until it is actually met, and cap the total so a
        # pathological glyph cannot silently fatten past legibility.
        total = 0.0
        for _ in range(12):
            w = min(_neck(p), _pinch(p))
            if w >= MARK_NECK_MIN:
                break
            r = max((MARK_NECK_MIN - w) / 2.0, 0.01)
            if total + r > NECK_DILATE_CAP:
                r = NECK_DILATE_CAP - total
            if r <= 0:
                break
            p = p.buffer(r, join_style=2)
            total += r
        else:
            pass
        w = min(_neck(p), _pinch(p))
        if w < MFG.MIN_FEATURE:
            raise RuntimeError(
                "a glyph will not open past %.3f mm within the %.2f mm "
                "dilation cap - the mark needs to be larger or the face "
                "changed, not fattened further" % (w, NECK_DILATE_CAP))
        out.append(p)
    return _uu(out)


def wordmark(field, width=None, centre=None, frac=None):
    """Graf3X as geometry, sized and placed in the bottom-right of the field.

    `frac` is accepted and ignored - it was the old centred sizing, kept in the
    signature so the six Graf3X designs did not all need editing.
    """
    import backplate as BP
    from config import BRAND
    w = MARK_W if width is None else width
    cx, cy = MARK_CENTRE if centre is None else centre
    g = BP.text_polygons(BRAND.TEXT, BRAND.FONT, 20.0,
                         tracking=BRAND.TRACKING + TRACK_BUMP)
    gx0, gy0, gx1, gy1 = g.bounds
    sc = w / (gx1 - gx0)
    g = scale(g, sc, sc, origin="centroid")
    # DILATE THE STROKES. Arial Bold at this size necks to 1.547 mm inside the
    # 'a', 1.729 in the '3' and 1.738 in the 'f' - all under the 2.0 mm the
    # laser can cut, and all invisible to a check that only asks whether a
    # contour VANISHES under a negative buffer. A shape with a narrow neck does
    # not vanish, it SPLITS, which is what the corrected test looks for.
    #
    # 0.25 mm opens the worst neck to 2.242 and leaves 3.61 mm between glyphs,
    # against a 2.0 mm minimum. Scaling the mark up instead would have made it
    # wider than the 82 mm it is composed at.
    g = _open_necks(g)
    gx0, gy0, gx1, gy1 = g.bounds
    return translate(g, cx - (gx0 + gx1) / 2, cy - (gy0 + gy1) / 2)


def mark_mask(field, clear=None):
    """The wordmark with clearance, WITHOUT merging glyphs or filling counters.

    Buffering the whole mark at once did both: it closed the 3.78 mm gap
    between the first two glyphs, and it filled the only counter in the word
    (the a, 4.2 x 3.8 mm). Buffering glyph by glyph and re-cutting the counter
    fixes the first. The second cannot be fixed at this size - see below.
    """
    c = MARK_CLEAR if clear is None else clear
    wm = wordmark(field)
    out = []
    for g in (wm.geoms if wm.geom_type != "Polygon" else [wm]):
        # mitre joins, not round: a round buffer at 1.4 mm turns every corner
        # of the letterform into a fillet and the mark reads as blobs
        outer = Polygon(g.exterior).buffer(c, join_style=2, mitre_limit=3.0)
        for r in g.interiors:
            inner = Polygon(r).buffer(-c, join_style=2, mitre_limit=3.0)
            if not inner.is_empty and inner.area > 4.0:
                outer = outer.difference(inner)
        out.append(outer)
    return unary_union(out)


def counter_report(field):
    """Whether the one counter in Graf3X can be cut, and at what mark width."""
    wm = wordmark(field)
    for g in wm.geoms:
        for r in g.interiors:
            b = Polygon(r).bounds
            small = min(b[2] - b[0], b[3] - b[1])
            return small, 6.0 / small * MARK_W
    return None, None


# ==================================================== ITERATIONS ============
def ghost_bone_v(field, pitch0=8.0, ramp=0.42, dot0=1.35, dgrow=0.055, rings=17):
    seed = Polygon(DIE_POLY)
    out, o = [], 12.0
    for k in range(rings):
        ring = seed.buffer(o)
        L = ring.exterior.length
        n = max(int(L / 5.4), 8)
        rad = min(dot0 + dgrow * k, 2.8)
        for t in range(n):
            p = ring.exterior.interpolate(t / n, normalized=True)
            out.append(Point(p.x, p.y).buffer(rad))
        o += pitch0 + ramp * k
        if o > 230:
            break
    return out


def ghost_bone_i1(field):
    """Dots become dashes: the ring reads as a broken contour, not a stipple."""
    seed = Polygon(DIE_POLY)
    out, o = [], 12.0
    for k in range(15):
        ring = seed.buffer(o)
        L = ring.exterior.length
        seg = 9.0 + 0.9 * k
        n = max(int(L / (seg + 3.4)), 6)
        w = min(1.5 + 0.10 * k, 3.0)
        for t in range(n):
            a = ring.exterior.interpolate(t / n, normalized=True)
            b = ring.exterior.interpolate((t / n) + seg / L, normalized=True)
            out.append(LineString([(a.x, a.y), (b.x, b.y)]).buffer(w, cap_style=1))
        o += 8.0 + 0.42 * k
        if o > 230:
            break
    return out


NOTE["Ghost Bone / dashes"] = "same echo, but each ring is a broken contour whose dash length grows outward - h3-dissolve applied to the bone instead of the die"


def ghost_bone_i2(field):
    """Alternate rings invert: dots, then the ring left as solid, alternating."""
    seed = Polygon(DIE_POLY)
    out, o = [], 12.0
    for k in range(16):
        ring = seed.buffer(o)
        if k % 2 == 0:
            L = ring.exterior.length
            n = max(int(L / 5.0), 8)
            rad = min(1.5 + 0.07 * k, 2.9)
            for t in range(n):
                p = ring.exterior.interpolate(t / n, normalized=True)
                out.append(Point(p.x, p.y).buffer(rad))
        else:
            band = seed.buffer(o + 3.0).difference(seed.buffer(o))
            out.append(band)
        o += 9.0 + 0.4 * k
        if o > 230:
            break
    return out


NOTE["Ghost Bone / banded"] = "alternating rings: a stippled ring, then a continuous band. Two textures reading the same silhouette"


def truss_i1(field):
    """Denser, graded: node spacing tightens toward the plate end."""
    from scipy.spatial import Delaunay
    x0, y0, x1, y1 = field.bounds
    inner = field.buffer(-4.0)
    pts = []
    for _ in range(9000):
        if len(pts) >= 150:
            break
        p = (K.np.random.default_rng(3).uniform(x0, x1) if False else
             np.random.default_rng().uniform(x0, x1),
             np.random.default_rng().uniform(y0, y1))
        if not inner.contains(Point(p)):
            continue
        t = (p[0] - x0) / (x1 - x0)
        rmin = 16.0 - 7.0 * t
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > rmin ** 2 for q in pts):
            pts.append(p)
    if len(pts) < 4:
        return []
    P = np.array(pts)
    out = []
    for s in Delaunay(P).simplices:
        poly = Polygon(P[s]).buffer(-1.5)
        if not poly.is_empty and poly.area > 6:
            out.append(poly)
    return out


NOTE["Truss / graded"] = "node spacing tightens toward the plate end, so the lattice densifies where the eye lands last"


def truss_i2(field):
    """Heavier members, fewer cells - reads as structure not mesh."""
    from scipy.spatial import Delaunay
    x0, y0, x1, y1 = field.bounds
    inner = field.buffer(-5.0)
    rng = np.random.default_rng(11)
    pts = []
    for _ in range(6000):
        if len(pts) >= 42:
            break
        p = (rng.uniform(x0, x1), rng.uniform(y0, y1))
        if inner.contains(Point(p)) and all(
                (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > 24.0 ** 2 for q in pts):
            pts.append(p)
    if len(pts) < 4:
        return []
    P = np.array(pts)
    out = []
    for s in Delaunay(P).simplices:
        poly = Polygon(P[s]).buffer(-3.2)
        if not poly.is_empty and poly.area > 20:
            out.append(poly)
    return out


NOTE["Truss / heavy"] = "half the nodes and a 6.4 mm member, so it reads as a frame rather than a mesh"


def crossover_i1(field):
    """Duty sweeps the other way: open near the die, closing outward."""
    cx, cy = DIE_C
    out = []
    for k in range(4, 26):
        r = 9.0 * k
        t = max(0.0, min((r - 45) / 175.0, 1.0))
        duty = 0.73 - 0.46 * (t ** 1.1)
        w = 9.0 * duty
        if w < 2.4:
            continue
        out.append(Point(cx, cy).buffer(r + w / 2)
                   .difference(Point(cx, cy).buffer(r - w / 2)))
    return out


NOTE["Crossover / reversed"] = "the sweep runs the other way - open beside the die, closing toward the plate end. Tests which direction reads as intended"


def crossover_i2(field):
    """Bands broken into radial segments whose length also sweeps."""
    cx, cy = DIE_C
    out = []
    for k in range(4, 26):
        r = 9.0 * k
        t = max(0.0, min((r - 45) / 175.0, 1.0))
        duty = 0.27 + 0.46 * (t ** 1.25)
        w = 9.0 * duty
        if w < 2.4:
            continue
        ring = Point(cx, cy).buffer(r + w / 2).difference(Point(cx, cy).buffer(r - w / 2))
        nseg = max(int(2 * math.pi * r / (16.0 + 22.0 * t)), 6)
        cutters = []
        for q in range(nseg):
            a = 2 * math.pi * q / nseg
            cutters.append(rotate(box(cx, cy - 1.6, cx + r + w, cy + 1.6),
                                  math.degrees(a), origin=(cx, cy)))
        out.append(ring.difference(unary_union(cutters)))
    return out


NOTE["Crossover / segmented"] = "the same duty sweep, but each band is broken into radial segments that lengthen outward - two variables on one polar field"


def interference_i1(field):
    """Longer wavelengths: broad blooms instead of a fine breathing texture."""
    a = 11.4

    def cell(cx, cy, i, j):
        u = (cx - 133.1) * math.cos(math.radians(20)) + (cy - 47.6) * math.sin(math.radians(20))
        v = -(cx - 133.1) * math.sin(math.radians(20)) + (cy - 47.6) * math.cos(math.radians(20))
        s = 5.0 + 2.2 * (math.cos(2 * math.pi * u / 122) + math.cos(2 * math.pi * v / 88))
        if s < 2.4:
            return None
        r = s / math.sqrt(3)
        return Polygon([(cx + r * math.cos(math.radians(30 + 60 * q)),
                         cy + r * math.sin(math.radians(30 + 60 * q)))
                        for q in range(6)])
    return K.lattice(field, cell, a, a * math.sqrt(3) / 2, stagger=0.5)


NOTE["Interference / long wave"] = "wavelengths roughly doubled, so the field breathes in a few broad blooms rather than a fine ripple"


def interference_i2(field):
    """The modulation deletes rather than shrinks - a lattice with holes in it."""
    a = 9.4

    def cell(cx, cy, i, j):
        u = (cx - 133.1) * math.cos(math.radians(20)) + (cy - 47.6) * math.sin(math.radians(20))
        v = -(cx - 133.1) * math.sin(math.radians(20)) + (cy - 47.6) * math.cos(math.radians(20))
        f = math.cos(2 * math.pi * u / 84) + math.cos(2 * math.pi * v / 61)
        if f < -0.35:
            return None
        r = 4.6 / math.sqrt(3)
        return Polygon([(cx + r * math.cos(math.radians(30 + 60 * q)),
                         cy + r * math.sin(math.radians(30 + 60 * q)))
                        for q in range(6)])
    return K.lattice(field, cell, a, a * math.sqrt(3) / 2, stagger=0.5)


NOTE["Interference / dropout"] = "constant aperture, but the wave DELETES cells instead of shrinking them - the figure appears as absence"


def lamination_i1(field):
    x0, y0, x1, y1 = field.bounds
    return K.chevrons(field, (x1 - 3, (y0 + y1) / 2), 148, 212, 14, 5.6, 2.4, 2.8,
                      leg=190, step_dir=180)


NOTE["Lamination / deeper"] = "a steeper V and a wider width ramp, so the nest reads as one swept section rather than a set of stripes"


def lamination_i2(field):
    x0, y0, x1, y1 = field.bounds
    out = K.chevrons(field, (x1 - 3, (y0 + y1) / 2), 145, 215, 11, 4.4, 2.4, 3.4,
                     leg=190, step_dir=180)
    cut = []
    for k in range(9):
        cut.append(box(x0 - 5, y0 + 9 + k * 11.6, x1 + 5, y0 + 12.4 + k * 11.6))
    c = unary_union(cut)
    return [g.difference(c) for g in out]


NOTE["Lamination / laddered"] = "the chevrons are crossed by horizontal ties, so the nest is held by a visible ladder - answers the flex worry structurally"


def kowloon_180(field):
    """Rotated 180 as requested - the cell hierarchy runs the other way."""
    g = G1.kowloon_graft(field)
    u = unary_union(K.clip(g, field))
    c = field.centroid
    return [rotate(u, 180, origin=c).intersection(field)]


NOTE["Kowloon Graft / 180"] = "rotated as requested: the dense cluster of straps now falls at the plate end rather than beside the die"


def kowloon_i1(field):
    cells = K.panels(field, min_side=21.0, wall=3.6, radius=5.0, border=5.0)
    web = unary_union(cells)
    x0, y0, x1, y1 = field.bounds
    straps = []
    off = 0.0
    for gi, (count, pitch) in enumerate([(5, 7.0), (3, 14.0), (2, 20.0)]):
        for k in range(count):
            off += pitch
            a = math.radians(24 if (gi == 1 and k == 1) else 17)
            p0 = (x0 - 40, y0 + off)
            straps.append(LineString([p0, (p0[0] + 300 * math.cos(a),
                                           p0[1] + 300 * math.sin(a))]
                                     ).buffer(1.8, cap_style=2))
    return [web.difference(unary_union(straps))]


NOTE["Kowloon Graft / bigger cells"] = "fewer, larger cells on a heavier 3.6 mm leading, straps thinned to 3.6 - the two tiers separate more clearly"


def twill_i1(field):
    def cell(cx, cy, i, j):
        vert = (i + j) % 2 == 0
        g = []
        for k in (-1.5, -0.5, 0.5, 1.5):
            if vert:
                g.append(box(cx + k * 5.4 - 1.7, cy - 8.6, cx + k * 5.4 + 1.7, cy + 8.6))
            else:
                g.append(box(cx - 8.6, cy + k * 5.4 - 1.7, cx + 8.6, cy + k * 5.4 + 1.7))
        return unary_union([p.buffer(-1.0).buffer(1.0) for p in g])
    return K.lattice(field, cell, 21.6, 21.6)


NOTE["Twill / four-up"] = "four slots per block instead of three, on a larger module - a coarser weave with a longer repeat"


def twill_i2(field):
    def cell(cx, cy, i, j):
        state = (i + j) % 3
        ang = state * 60
        g = []
        for k in (-1, 0, 1):
            g.append(rotate(box(cx - 7.2, cy + k * 6.0 - 1.8, cx + 7.2,
                                cy + k * 6.0 + 1.8), ang, origin=(cx, cy)))
        return unary_union([p.buffer(-1.0).buffer(1.0) for p in g])
    return K.lattice(field, cell, 18.0, 18.0)


NOTE["Twill / three-state"] = "the checkerboard becomes a three-state rotation at 0/60/120, so the weave never resolves into stripes"


def ghost_chevron_i1(field):
    x0, y0, x1, y1 = field.bounds
    mask = []
    for ax in (x1 - 8, x1 - 26, x1 - 44, x1 - 62, x1 - 80):
        for sgn in (+1, -1):
            b = math.radians(180 + sgn * 38)
            mask.append(LineString([(ax, (y0 + y1) / 2),
                                    (ax + 150 * math.cos(b),
                                     (y0 + y1) / 2 + 150 * math.sin(b))]
                                   ).buffer(6.5, cap_style=2))
    m = unary_union(mask)

    def cell(cx, cy, i, j):
        inside = m.contains(Point(cx, cy))
        s = 5.4 if inside else 2.6
        d = rotate(box(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2), 45,
                   origin=(cx, cy))
        return d.buffer(-0.7).buffer(0.7)
    return K.lattice(field, cell, 8.4, 8.4)


NOTE["Ghost Chevron / positive"] = "the mask now ENLARGES the diamonds instead of shrinking them, so the chevron reads dark on light rather than as a ghost"


def ghost_chevron_i2(field):
    x0, y0, x1, y1 = field.bounds
    mask = []
    for ax in (x1 - 10, x1 - 32, x1 - 54, x1 - 76):
        for sgn in (+1, -1):
            b = math.radians(180 + sgn * 38)
            mask.append(LineString([(ax, (y0 + y1) / 2),
                                    (ax + 150 * math.cos(b),
                                     (y0 + y1) / 2 + 150 * math.sin(b))]
                                   ).buffer(5.5, cap_style=2))
    m = unary_union(mask)

    def cell(cx, cy, i, j):
        if m.contains(Point(cx, cy)):
            return None
        d = rotate(box(cx - 2.3, cy - 2.3, cx + 2.3, cy + 2.3), 45, origin=(cx, cy))
        return d.buffer(-0.7).buffer(0.7)
    return K.lattice(field, cell, 7.6, 7.6)


NOTE["Ghost Chevron / carved"] = "cells inside the chevron are deleted outright, leaving the mark as solid white metal - the archive's 'inverse' move applied here"


# ==================================================== GROUPS ================
def group_lattice(field):
    """A: modulated lattice. One aperture, one field, three things modulated."""
    cx, cy = DIE_C
    seed = Polygon(DIE_POLY)

    def cell(px, py, i, j):
        d = seed.distance(Point(px, py))
        t = min(d / 150.0, 1.0)
        u = (px - 133.1) * math.cos(math.radians(20)) + (py - 47.6) * math.sin(math.radians(20))
        wave = math.cos(2 * math.pi * u / 96)
        s = 3.0 + 3.2 * t + 0.9 * wave
        if s < 2.4:
            return None
        ang = 45 + 40 * t
        r = s / 2
        return rotate(box(px - r, py - r, px + r, py + r), ang, origin=(px, py)
                      ).buffer(-0.7).buffer(0.7)
    return K.lattice(field, cell, 9.0, 9.0, stagger=0.5)


NOTE["Modulated Lattice"] = "the group's common move made explicit: one aperture whose SIZE reads distance from the bone, whose ORIENTATION reads the same scalar, and whose presence reads a wave. Ghost Bone + Interference + Twill in one rule"


def group_bands(field):
    """B: swept band family. Polar structure, chevron section, one sweep."""
    cx, cy = DIE_C
    out = []
    for k in range(5, 27):
        r = 8.6 * k
        t = max(0.0, min((r - 50) / 180.0, 1.0))
        w = 2.6 + 4.4 * t
        if w < 2.4:
            continue
        ring = Point(cx, cy).buffer(r + w / 2).difference(Point(cx, cy).buffer(r - w / 2))
        keep = box(cx, cy - 400, cx + 400, cy + 400)
        wedge = rotate(box(cx, cy - 400, cx + 400, cy + 400), 0, origin=(cx, cy))
        out.append(ring.intersection(wedge))
    return out


NOTE["Swept Bands"] = "Crossover's polar origin with Lamination's width ramp, restricted to the half-plane beyond the die so the bands arrive as a chevron rather than a bullseye"


def group_network(field):
    """C: structural network. Nodes from the real fasteners, cells between."""
    from scipy.spatial import Delaunay
    from hole_pattern import HOLES
    x0, y0, x1, y1 = field.bounds
    nodes = [(x, y) for x, y, t, s in HOLES if field.buffer(26).contains(Point(x, y))]
    rng = np.random.default_rng(5)
    inner = field.buffer(-5.0)
    for _ in range(4000):
        if len(nodes) >= 26:
            break
        p = (rng.uniform(x0, x1), rng.uniform(y0, y1))
        if inner.contains(Point(p)) and all(
                (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > 28.0 ** 2 for q in nodes):
            nodes.append(p)
    P = np.array(nodes)
    out = []
    for s in Delaunay(P).simplices:
        poly = Polygon(P[s]).buffer(-3.0)
        if not poly.is_empty and poly.area > 25:
            out.append(poly)
    return out


NOTE["Fastener Net"] = "Truss and Kowloon share a rule - cells between nodes. Here the nodes are the REAL fastener positions, so the frame is generated by the part rather than laid over it"


# ==================================================== THE THREAD ============
def the_thread(field):
    """One rule, three readouts, all reading the same scalar."""
    seed = Polygon(DIE_POLY)
    x0, y0, x1, y1 = field.bounds
    out = []
    for px in np.arange(x0 + 4, x1 - 2, 8.6):
        for py in np.arange(y0 + 4, y1 - 2, 8.6):
            d = seed.distance(Point(px, py))
            t = min(max((d - 10) / 150.0, 0.0), 1.0)
            if t < 0.33:                                  # near: dots
                r = 1.3 + 2.0 * (t / 0.33)
                out.append(Point(px, py).buffer(r))
            elif t < 0.66:                                # mid: capsules
                u = (t - 0.33) / 0.33
                out.append(K.capsule(px, py, 2.8, 5.0 + 5.0 * u,
                                     vertical=False))
            else:                                          # far: bars
                u = (t - 0.66) / 0.34
                out.append(box(px - 4.2 - 1.6 * u, py - 1.6 - 0.5 * u,
                               px + 4.2 + 1.6 * u, py + 1.6 + 0.5 * u))
    return out


NOTE["The Thread"] = "the shortlist's shared method, stated plainly: ONE scalar - distance from the bone - read three ways as it grows. Dots become capsules become bars. h4-banded-to-dots, run in reverse and generalised"


# ==================================================== GRAF3X ================
def graf_halftone(field):
    """The lattice reads the letters as a size map. ghost-x, generalised."""
    wm = mark_mask(field, 0.6)          # tight: this one tests containment

    def cell(px, py, i, j):
        inside = wm.contains(Point(px, py))
        # Contrast has to be large for a dot field to spell letters, but the
        # background dots still have to EXIST: at 1.6 mm they fall under the
        # 3 mm2 sliver cull and the field vanishes, leaving the letters
        # floating on blank metal. 2.8 vs 6.6 is a 5.6x area ratio and both
        # survive.
        s = 6.6 if inside else 2.8
        return Point(px, py).buffer(s / 2)
    return K.lattice(field, cell, 8.6, 8.6, stagger=0.5)


NOTE["Graf3X / halftone"] = "the dot field grows inside the letters. AT THIS SIZE IT CANNOT SPELL: a halftone needs about 8 rows across a cap height, and 82 mm of mark is 17 mm tall = 4.2 rows at the smallest pitch a 2.0 mm web allows. It needs a 150 mm mark to resolve"


def graf_inverse(field):
    """Mesh cut away, letters left as solid metal. The archive's 'inverse'."""
    wm = mark_mask(field)

    def cell(px, py, i, j):
        if wm.contains(Point(px, py)):
            return None
        d = rotate(box(px - 2.6, py - 2.6, px + 2.6, py + 2.6), 45, origin=(px, py))
        return d.buffer(-0.8).buffer(0.8)
    return K.lattice(field, cell, 8.0, 8.0)


NOTE["Graf3X / inverse"] = "figure/ground flipped - the mesh is cut, the letters survive as solid white metal. Same resolution limit as halftone: at 82 mm the diamond lattice samples the letters too coarsely to read. The IDEA is the strongest of the six; it needs a bigger mark"


def graf_bands(field):
    """Swept bands interrupted by the letters - the mark as a barline."""
    wm = mark_mask(field)
    cx, cy = DIE_C
    out = []
    for k in range(5, 27):
        r = 8.6 * k
        t = max(0.0, min((r - 50) / 180.0, 1.0))
        w = 2.6 + 4.0 * t
        if w < 2.4:
            continue
        ring = Point(cx, cy).buffer(r + w / 2).difference(Point(cx, cy).buffer(r - w / 2))
        out.append(ring.difference(wm))
    return out


NOTE["Graf3X / bands"] = "Swept Bands with the wordmark subtracted. THE ONE THAT WORKS AT THIS SIZE: a band family is CONTINUOUS, so an interruption in it reads directly without being sampled. No resolution limit applies"


def graf_lamination(field):
    wm = mark_mask(field)
    x0, y0, x1, y1 = field.bounds
    # Finer than the standalone Lamination: at an 82 mm mark only about two
    # chevrons crossed each letter, so the gap read as a smudge. 3.0 mm bands
    # on a 2.4 mm web put roughly four across a cap height, which resolves.
    ch = K.chevrons(field, (x1 - 3, (y0 + y1) / 2), 145, 215, 20, 3.0, 2.4, 2.4,
                    leg=190, step_dir=180)
    return [g.difference(wm) for g in ch]


NOTE["Graf3X / lamination"] = "the nested chevrons stop at the letters. Also a continuous carrier, so it survives the small mark - but the bands were re-pitched from 4.6 to 3.0 mm to get enough of them across a 17 mm cap"


def graf_truss(field):
    """The wordmark densifies the network - letters as node attractors."""
    from scipy.spatial import Delaunay
    wm = wordmark(field, frac=0.74)
    x0, y0, x1, y1 = field.bounds
    rng = np.random.default_rng(17)
    inner = field.buffer(-4.0)
    pts = []
    for _ in range(9000):
        if len(pts) >= 130:
            break
        p = (rng.uniform(x0, x1), rng.uniform(y0, y1))
        if not inner.contains(Point(p)):
            continue
        rmin = 6.5 if wm.contains(Point(p)) else 27.0
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > rmin ** 2 for q in pts):
            pts.append(p)
    if len(pts) < 4:
        return []
    P = np.array(pts)
    out = []
    for s in Delaunay(P).simplices:
        poly = Polygon(P[s]).buffer(-1.6)
        if not poly.is_empty and poly.area > 6:
            out.append(poly)
    return out


NOTE["Graf3X / truss"] = "the letters triple the node density. HONEST RESULT: the mark does NOT resolve - a Delaunay lattice has no orientation to carry a letterform, so it reads only as a denser patch. Kept to show where the approach fails"


def graf_thread(field):
    """The thread design, with the letters as the scalar instead of the bone."""
    wm = wordmark(field, frac=0.80)
    x0, y0, x1, y1 = field.bounds
    out = []
    for px in np.arange(x0 + 4, x1 - 2, 8.2):
        for py in np.arange(y0 + 4, y1 - 2, 8.2):
            d = wm.distance(Point(px, py))
            t = min(max(d / 16.0, 0.0), 1.0)   # tighter, so the letters read
            if t < 0.30:
                out.append(Point(px, py).buffer(1.4 + 2.1 * (t / 0.30)))
            elif t < 0.66:
                u = (t - 0.30) / 0.36
                out.append(K.capsule(px, py, 2.8, 5.4 + 5.0 * u, vertical=False))
            else:
                u = (t - 0.66) / 0.34
                out.append(box(px - 4.0 - 1.8 * u, py - 1.6, px + 4.0 + 1.8 * u,
                               py + 1.6))
    return out


NOTE["Graf3X / the thread"] = "The Thread with the wordmark as its scalar. HONEST RESULT: the mark does not resolve either - three aperture families reading one scalar cannot also spell, because the shape change reads before the shape does"


ITERATIONS = [
    ("Ghost Bone / dashes", ghost_bone_i1), ("Ghost Bone / banded", ghost_bone_i2),
    ("Truss / graded", truss_i1), ("Truss / heavy", truss_i2),
    ("Crossover / reversed", crossover_i1), ("Crossover / segmented", crossover_i2),
    ("Interference / long wave", interference_i1),
    ("Interference / dropout", interference_i2),
    ("Lamination / deeper", lamination_i1), ("Lamination / laddered", lamination_i2),
    ("Kowloon Graft / 180", kowloon_180),
    ("Kowloon Graft / bigger cells", kowloon_i1),
    ("Twill / four-up", twill_i1), ("Twill / three-state", twill_i2),
    ("Ghost Chevron / positive", ghost_chevron_i1),
    ("Ghost Chevron / carved", ghost_chevron_i2),
]
GROUPS = [("Modulated Lattice", group_lattice), ("Swept Bands", group_bands),
          ("Fastener Net", group_network)]
THREAD = [("The Thread", the_thread)]
def graf_cut(field):
    """Letters CUT, not reserved - so the counter is an island, held by bridges.

    This is the version that works at an 82 mm mark, and the reason is a
    reversal worth stating. With the letters SOLID, the counter is a HOLE and
    needs 2.0 clearance + 2.0 hole + 2.0 clearance = 6.0 mm; the a's counter is
    3.8 mm, so the mark would have to be 131 mm.

    With the letters CUT, the counter becomes an ISLAND of metal. An island
    only has to be 2.0 mm wide itself - 3.8 mm clears easily - and it stays
    attached by bridges across the cut stroke. So cutting the letters buys the
    detail that reserving them cannot.
    """
    x0, y0, x1, y1 = field.bounds
    wm = wordmark(field)
    band = box(x0, y0, x1, 52.0)
    # generous quiet zone: an OCR window has to contain the mark and
    # nothing else, and the plaque's own corners were fragmenting into it
    plaque = wm.buffer(11.0).convex_hull.intersection(band)

    # the carrier: swept bands everywhere except the plaque
    cx, cy = DIE_C
    carrier = []
    for k in range(5, 27):
        r = 8.6 * k
        t = max(0.0, min((r - 50) / 180.0, 1.0))
        w = 2.6 + 4.0 * t
        if w < 2.4:
            continue
        ring = Point(cx, cy).buffer(r + w / 2).difference(Point(cx, cy).buffer(r - w / 2))
        carrier.append(ring.difference(plaque))

    # the letters, cut, with bridges holding every counter island
    letters = []
    for g in (wm.geoms if wm.geom_type != "Polygon" else [wm]):
        cut = Polygon(g.exterior)
        for r in g.interiors:
            isl = Polygon(r)
            b = isl.bounds
            mx = (b[0] + b[2]) / 2
            # ONE bridge, and only long enough to cross the stroke.
            #
            # Two bridges (or one spanning the whole glyph) splits the letter's
            # cut into separate components, and an OCR then segments the a as
            # two marks and reads neither. One tab at the foot leaves the cut
            # connected as a C around the island, and the island - 11.5 mm2 of
            # 2 mm aluminium, about 0.06 g - needs no more than that.
            br = box(mx - 1.2, b[1] - 5.0, mx + 1.2, b[1] + 1.5)
            cut = cut.difference(isl.union(br))
        letters.append(cut)
    return carrier + letters


NOTE["Graf3X / cut"] = "the letters are CUT, not reserved, so they read dark. That reverses the counter problem: reserved letters need a 131 mm mark before the a's counter can be cut as a hole, but CUT letters make that counter an ISLAND, which only has to be 2 mm wide - and two 2.4 mm bridges hold it. Detail the reserved versions cannot have at this size"


GRAF = [("Graf3X / cut", graf_cut),
        ("Graf3X / halftone", graf_halftone), ("Graf3X / inverse", graf_inverse),
        ("Graf3X / bands", graf_bands), ("Graf3X / lamination", graf_lamination),
        ("Graf3X / truss", graf_truss), ("Graf3X / the thread", graf_thread)]

SETS = [("Iteration", ITERATIONS), ("Group", GROUPS),
        ("The thread", THREAD), ("Graf3X", GRAF)]


def build_iterations(field=None, verbose=False):
    import time
    if field is None:
        field = K.expanded_field()[0]
    out = []
    for lane, items in SETS:
        for nm, fn in items:
            t0 = time.time()
            try:
                g, dropped = K.build(fn, field)
                out.append(dict(lane=lane, name=nm, geom=g, dropped=dropped, err=None))
            except Exception as e:
                out.append(dict(lane=lane, name=nm, geom=None, dropped=0,
                                err=f"{type(e).__name__}: {e}"))
            if verbose:
                print("   %-28s %5.1fs" % (nm, time.time() - t0), flush=True)
    return field, out


if __name__ == "__main__":
    field, res = build_iterations(verbose=True)
    print(f"\nfield {field.area/100:.1f} cm2\n")
    print(f"{'set':11s} {'design':28s} {'cm2':>6s} {'%':>5s} {'parts':>6s} {'web':>5s}")
    for r in res:
        if r["err"] or r["geom"] is None:
            print(f"{r['lane']:11s} {r['name']:28s}   {r['err'] or 'EMPTY'}")
            continue
        g = r["geom"]
        parts = [g] if g.geom_type == "Polygon" else list(g.geoms)
        web = min((a.distance(b) for i, a in enumerate(parts)
                   for b in parts[i + 1:]), default=99.0)
        print(f"{r['lane']:11s} {r['name']:28s} {g.area/100:6.1f} "
              f"{100*g.area/field.area:4.0f}% {len(parts):6d} {web:5.2f}")
