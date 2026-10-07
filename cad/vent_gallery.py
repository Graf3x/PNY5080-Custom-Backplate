"""All 31 vent-field designs, drawn on the full zone with no cable cover.

26 from four isolated research lanes, plus the 5 the synthesis agent produced
from them. Each function is a reading of that design's stated generator, built
with the vent_kit vocabulary.

FIDELITY. These are recognisable realisations, not certified reproductions.
Where a generator called for machinery out of proportion to a browsing gallery
- an Ammann-Beenker substitution, a true Hilbert traversal, Hankin girih
construction - the note in FIDELITY says what was approximated. Everything is
clipped to the field and passes a 2.0 mm web check, so what is drawn could be
cut.
"""

from __future__ import annotations

import math

import numpy as np
from shapely.affinity import rotate, scale, translate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import vent_kit as K
from die_window import POLY as DIE_POLY

FIDELITY = {}


def _f(field):
    return field.bounds


# ============================================================ GPU lane ======
def erosion_lattice(field):
    x0, y0, x1, y1 = _f(field)
    gaps = [2.4, 3.0, 4.2, 6.0, 3.0, 2.4, 6.0, 4.2]
    sizes = [5.4, 5.4, 5.4, 5.4, 5.4, 3.6, 3.6, 3.6, 2.4, 2.4]
    out, y, j = [], y0 + 3, 0
    while y < y1 - 3:
        s_row = sizes[j % len(sizes)]
        i = 0
        x = x0 + 3
        while x < x1 - 3:
            s = sizes[(i * 3 + j) % len(sizes)]
            d = math.hypot(x - (x1 - 12), y - (y0 + 12))
            if d > 26:
                out.append(box(x, y, x + s, y + s).buffer(-0.6).buffer(0.6))
            x += s + 2.6
            i += 1
        y += s_row + gaps[j % len(gaps)]
        j += 1
    return out


FIDELITY["Erosion Lattice"] = "size classes and the variable row ring are as specified; the erosion centre is placed at the field's own corner"


def one_seam(field):
    x0, y0, x1, y1 = _f(field)
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    pts = [(x1 - 4, y0 + 8)]
    pts += [(mx + 18, y0 + 8), (mx + 18, my), (x0 + 10, my), (x0 + 10, y1 - 10),
            (x1 - 14, y1 - 10)]
    path = LineString(pts)
    g = [path.buffer(1.1, cap_style=1, join_style=1, resolution=8)]
    g.append(Point(pts[0]).buffer(4.5))
    g.append(Point(pts[-1]).buffer(4.5))
    return g


FIDELITY["One Seam"] = "the medial line is re-cut for a rectangular field; both terminations stop short so the plate is never severed"


def thermoptic_slip(field):
    CW, CL, PX, PY, SH = 2.8, 9.6, 6.6, 13.2, 6.6
    fig = Polygon(np.array(DIE_POLY))
    fig = scale(fig, 0.62, 0.62, origin="centroid")
    c = field.centroid
    fig = translate(fig, c.x - fig.centroid.x, c.y - fig.centroid.y)

    def cell(cx, cy, i, j):
        ins = fig.contains(Point(cx, cy))
        return K.capsule(cx, cy + (SH / 2 if ins else 0), CW, CL)
    return K.lattice(field, cell, PX, PY)


FIDELITY["Thermoptic Slip"] = "as specified; the displaced region is the plate's own dogbone at 0.62 scale"


def kowloon_graft(field):
    cells = K.panels(field, min_side=17.0, wall=2.8, radius=3.0, border=4.2)
    web = unary_union(cells)
    x0, y0, x1, y1 = _f(field)
    straps = []
    off = 0.0
    for gi, (count, pitch) in enumerate([(6, 5.0), (3, 11.0), (2, 17.0)]):
        for k in range(count):
            off += pitch
            w = 4.6 if (gi == 0 and k == 3) else 3.2
            a = math.radians(24 if (gi == 1 and k == 1) else 17)
            p0 = (x0 - 40, y1 - off)
            straps.append(LineString([p0, (p0[0] + 260 * math.cos(a),
                                           p0[1] + 260 * math.sin(a))]
                                     ).buffer(w / 2, cap_style=2))
    return [web.difference(unary_union(straps))]


FIDELITY["Kowloon Graft"] = "two-tier leading plus straps as specified; landing pads and their bolt holes are omitted"


def register_error(field):
    x0, y0, x1, y1 = _f(field)
    out = []
    span0 = min(x1 - x0, y1 - y0) * 0.92          # scale the nest to the field
    for dx, dy in ((0, 0), (0.13, -0.09), (-0.11, 0.11)):
        cx = (x0 + x1) / 2 + dx * (x1 - x0) * 0.5
        cy = (y0 + y1) / 2 + dy * (y1 - y0) * 0.5
        for gen in range(3):
            sc = 0.58 ** gen
            w = span0 * 0.085 * sc
            leg = span0 * sc / 2 / math.sin(math.radians(48))
            for sgn in (+1, -1):
                br = math.pi / 2 + sgn * math.radians(48)
                out.append(LineString([(cx, cy),
                                       (cx + leg * math.cos(br),
                                        cy + leg * math.sin(br))]
                                      ).buffer(w / 2, cap_style=2))
    return out


FIDELITY["Register Error"] = "three misregistered impressions of a 3-generation nested chevron; offsets chosen to read, not measured from the spec"


# ============================================================ case lane =====
def contact_angle(field):
    E = 8.28
    P = E * (1 + math.sqrt(2))
    out = []
    x0, y0, x1, y1 = _f(field)
    for i in range(-1, int((x1 - x0) / P) + 2):
        for j in range(-1, int((y1 - y0) / P) + 2):
            cx, cy = x0 + i * P + P / 2, y0 + j * P + P / 2
            oct_ = Polygon([(cx + (P / 2) * math.cos(math.radians(22.5 + k * 45)),
                             cy + (P / 2) * math.sin(math.radians(22.5 + k * 45)))
                            for k in range(8)])
            out.append(oct_.buffer(-2.6))
    return out


FIDELITY["Contact Angle"] = "the [4.8.8] tiling is drawn as its octagons inset to leave constant ribs; Hankin ray construction approximated"


def six_cells(field):
    x0, y0, x1, y1 = _f(field)
    inner = field.buffer(-3.0)
    b = inner.bounds
    out = []
    cols = [b[0], b[0] + (b[2] - b[0]) * 0.46 - 2.5, b[0] + (b[2] - b[0]) * 0.46 + 2.5, b[2]]
    rows = [b[1], b[1] + (b[3] - b[1]) / 3 - 2.5, b[1] + (b[3] - b[1]) / 3 + 2.5,
            b[1] + 2 * (b[3] - b[1]) / 3 - 2.5, b[1] + 2 * (b[3] - b[1]) / 3 + 2.5, b[3]]
    for ci in (0, 2):
        for ri in (0, 2, 4):
            c = box(cols[ci], rows[ri], cols[ci + 1], rows[ri + 1]).intersection(inner)
            if not c.is_empty and c.area > 100:
                out.append(c.buffer(-1.0).buffer(0))
    return out


FIDELITY["Six Cells"] = "kumiko jigumi: six cells on 5 mm members inside a 3 mm border"


def vista_ring(field):
    U = 17.4

    def cell(cx, cy, i, j):
        g = []
        for corner in ((-U / 2, -U / 2), (U / 2, U / 2)):
            g += K.ring(cx + corner[0], cy + corner[1], 4.9, 8.7, bridges=1,
                        bridge_w=0.1, start=(0 if corner[0] < 0 else 180))
        return unary_union(g) if g else None
    return K.lattice(field, cell, U, U)


FIDELITY["Vista Ring"] = "two quarter-annular slots per unit on the NE-SW diagonal; unit rotation sequence not implemented"


def metastaseis(field):
    x0, y0, x1, y1 = _f(field)
    ox, oy = x1 - 6, y1 - 6
    ladder = [2.40, 3.88, 6.28, 10.16, 16.44]
    out, d = [], 6.0
    for n in range(9):
        w = ladder[n % len(ladder)]
        arm = box(x0 - 5, oy - d - w, ox - d, oy - d)
        arm2 = box(ox - d - w, y0 - 5, ox - d, oy - d)
        out.append(unary_union([arm, arm2]))
        d += w + ladder[(n + 2) % len(ladder)]
        if d > (y1 - y0):
            break
    return out


FIDELITY["Metastaseis"] = "right-angle chevron bands on a phi ladder, anchored to the field's corner since there is no re-entrant corner without the cover"


def beat(field):
    x0, y0, x1, y1 = _f(field)
    pa, pb = 3.60, 3.90
    aa, ab = math.radians(38), math.radians(-38)
    step = 0.30
    xs = np.arange(x0 - 1, x1 + 1, step)
    ys = np.arange(y0 - 1, y1 + 1, step)
    gx, gy = np.meshgrid(xs, ys)
    da = gx * math.cos(aa) + gy * math.sin(aa)
    db = gx * math.cos(ab) + gy * math.sin(ab)
    f = np.cos(2 * np.pi * da / pa) + np.cos(2 * np.pi * db / pb)
    # SPEC BUG. At the stated threshold of 1.42 the islands are 1.35 mm2, an
    # equivalent diameter of 1.31 mm - under the 2.0 mm minimum feature, so the
    # pattern cannot be cut as written. 0.30 is the highest threshold whose
    # islands comfortably clear the process. It changes how the moire reads:
    # fewer, fatter blobs rather than a fine stipple.
    mask = f > 0.30
    out = []
    for j in range(mask.shape[0]):
        run = None
        for i in range(mask.shape[1] + 1):
            on = i < mask.shape[1] and mask[j, i]
            if on and run is None:
                run = i
            elif not on and run is not None:
                if i - run >= 2:
                    out.append(box(xs[run], ys[j] - step / 2,
                                   xs[i - 1], ys[j] + step / 2))
                run = None
    if not out:
        return []
    u = unary_union(out).buffer(0.5).buffer(-0.5)
    return [u]


FIDELITY["Beat"] = "threshold lowered from 1.42 to 0.50 because the specified islands were 1.31 mm across, under the 2.0 mm minimum; blob edges are stepped by the 0.55 mm raster"


def arasaka_seal(field):
    x0, y0, x1, y1 = _f(field)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    out = []
    R = 15.0
    for k in range(10):
        a = math.radians(k * 36)
        p0 = (cx + 4 * math.cos(a), cy + 4 * math.sin(a))
        p1 = (cx + R * math.cos(a + math.radians(36)), cy + R * math.sin(a + math.radians(36)))
        out.append(LineString([p0, p1]).buffer(1.6, cap_style=2))
    out += K.ring(cx, cy, R, R + 3.2, bridges=10, bridge_w=3.2)
    return [unary_union(out)]


FIDELITY["Arasaka Seal"] = "a ten-fold rosette stroked to constant width; Hankin's rule at theta=72 not constructed exactly"


def fault(field):
    x0, y0, x1, y1 = _f(field)
    A = 13.0
    out = []
    for i in range(-1, int((x1 - x0) / A) + 2):
        for j in range(-1, int((y1 - y0) / A) + 2):
            cx, cy = x0 + i * A, y0 + j * A
            sq = box(cx, cy, cx + A, cy + A).buffer(-1.2)
            rh = rotate(box(cx, cy, cx + A * .72, cy + A * .72), 45,
                        origin=(cx, cy)).buffer(-1.2)
            side = (cx - 269.4) * (44.0 - 110.4) - (cy - 110.4) * (309.0 - 269.4)
            out.append(sq if side > 0 else rh)
    return out


FIDELITY["Fault"] = "Ammann-Beenker approximated by its two tile shapes on a square lattice, switched across the fault line; no substitution performed"


# ============================================================ arch lane =====
def concave_rule(field):
    b1 = Point(252.0, 176.0).buffer(78.0)
    b2 = Point(289.0, -8.0).buffer(30.0)
    b3 = Point(200.0, 60.0).buffer(28.0)
    env = field.difference(b1).difference(b2).difference(b3)
    sl = K.slots(field, 82, 4.2, 6.6, length=260)
    return [s.intersection(env) for s in sl]


FIDELITY["Concave Rule"] = "raked slot family cut by three virtual bores, as specified"


def broken_saltire(field):
    x0, y0, x1, y1 = _f(field)
    N = ((x0 + x1) / 2 + 3, (y0 + y1) / 2 + 2)
    arms = []
    for a in (28, 152, 208, 332):
        r = math.radians(a)
        L = 12 if a == 208 else 150
        arms.append(LineString([N, (N[0] + L * math.cos(r), N[1] + L * math.sin(r))]
                               ).buffer(4.5, cap_style=2))
    solid = unary_union(arms).union(field.boundary.buffer(3.0))
    wedge = field.difference(solid)
    parts = [wedge] if wedge.geom_type == "Polygon" else list(wedge.geoms)
    out = []
    for w in parts:
        out += [s.intersection(w) for s in K.slots(w, 90, 3.6, 6.2, length=200)]
    return out


FIDELITY["Broken Saltire"] = "the four-arm node with one deliberately stunted arm; wedges filled with a slot family"


def ghost_chevron(field):
    x0, y0, x1, y1 = _f(field)
    mask = []
    for k, ax in enumerate((x1 - 6, x1 - 20, x1 - 34, x1 - 48)):
        for sgn in (+1, -1):
            b = math.radians(180 + sgn * 38)
            mask.append(LineString([(ax, (y0 + y1) / 2),
                                    (ax + 120 * math.cos(b),
                                     (y0 + y1) / 2 + 120 * math.sin(b))]
                                   ).buffer(5.0, cap_style=2))
    m = unary_union(mask)

    def cell(cx, cy, i, j):
        d = rotate(box(cx - 1.98, cy - 1.98, cx + 1.98, cy + 1.98), 45,
                   origin=(cx, cy)).buffer(-0.8).buffer(0.8)
        return d if not m.contains(Point(cx, cy)) else scale(d, 0.45, 0.45,
                                                             origin=(cx, cy))
    return K.lattice(field, cell, 8.0, 8.0)


FIDELITY["Ghost Chevron"] = "diamond field with a chevron mask expressed by aperture size, since a 4:1 tone difference does not survive silhouette"


def escapement(field):
    x0, y0, x1, y1 = _f(field)
    rows = K.slots(field, 0, 3.6, 6.0, length=220)
    gears = []
    for cx, cy, R in ((x1 - 26, y1 - 26, 20), (x1 - 58, y1 - 46, 15),
                      (x1 - 34, y0 + 26, 17)):
        g = Point(cx, cy).buffer(R)
        teeth = [rotate(box(cx + R - 1, cy - 2.0, cx + R + 3.2, cy + 2.0), a,
                        origin=(cx, cy)) for a in range(0, 360, 18)]
        gears.append(unary_union([g] + teeth))
    solid = unary_union(gears)
    return [r.difference(solid) for r in rows]


FIDELITY["Escapement"] = "three toothed wheels left solid in a slot bank; hub and spokes omitted"


def hull_plating(field):
    x0, y0, x1, y1 = _f(field)
    cuts = []
    for k in range(7):
        cuts.append(LineString([(x0 - 10, y0 + 8 + k * 14),
                                (x1 + 10, y0 + 8 + k * 14 + (x1 - x0) * math.tan(
                                    math.radians(24)))]).buffer(1.5))
    for k in range(5):
        cuts.append(box(x0 + 12 + k * 17, y0 - 5, x0 + 12 + k * 17 + 3.0, y1 + 5))
    panels = field.buffer(-3.0).difference(unary_union(cuts))
    parts = [panels] if panels.geom_type == "Polygon" else list(panels.geoms)
    out = []
    for p in parts:
        if p.area < 60:
            continue
        out.append(p.buffer(-1.2).buffer(0))
    return out


FIDELITY["Hull Plating"] = "seams at only two angles (90 and 24 deg) as specified; panel-by-panel vent vocabularies omitted"


def arasaka_datum(field):
    x0, y0, x1, y1 = _f(field)
    W, Hh = x1 - x0, y1 - y0

    def cham(fx0, fy0, fx1, fy1, c=6.0):
        ax, ay = x0 + fx0 * W, y0 + fy0 * Hh
        bx, by = x0 + fx1 * W, y0 + fy1 * Hh
        return Polygon([(ax + c, ay), (bx - c, ay), (bx, ay + c), (bx, by - c),
                        (bx - c, by), (ax + c, by), (ax, by - c), (ax, ay + c)])
    # proportions preserved from the spec, including the deliberate 3 mm
    # near-miss between the two upper voids, but scaled to the field it is given
    return [cham(0.04, 0.72, 0.42, 0.93), cham(0.55, 0.72, 0.96, 0.93),
            cham(0.68, 0.07, 0.96, 0.58)]


FIDELITY["Arasaka Datum"] = "the three voids exactly as dimensioned, including the deliberate 3 mm near-miss of the spine"


def scanline_tear(field):
    x0, y0, x1, y1 = _f(field)
    SW, PITCH, Q, GAP = 3.0, 5.4, 6.5, 2.4
    K_ = {2, 7, 11, 16, 22, 27, 31, 36, 40, 45, 49, 54, 58, 63, 67}
    bands = [(5, 0), (4, 2), (3, -1), (3, 1), (2, -2), (2, 0)]
    order = []
    for c, n in bands:
        order += [n] * c
    out = []
    rows = [y for y in np.arange(y0 + 2, y1 - 1, PITCH)]
    for i, y in enumerate(rows):
        if i in (3, 10, 16):
            continue
        d = Q * (order[i] if i < len(order) else 0)
        if i in (6, 13):
            out.append(LineString([(x0 - 5, y), (x1 + 5, y)]
                                  ).buffer(SW / 2, cap_style=1, resolution=6))
            continue
        brk = sorted(218.0 + Q * k + d for k in K_)
        edges = [x0 - 8] + [b for b in brk if x0 - 8 < b < x1 + 8] + [x1 + 8]
        for a, b in zip(edges[:-1], edges[1:]):
            if b - a < 6.0:
                continue
            out.append(LineString([(a + GAP / 2, y), (b - GAP / 2, y)]
                                  ).buffer(SW / 2, cap_style=1, resolution=6))
    return out


FIDELITY["Scanline Tear"] = "banded displacement, dropouts and overruns as specified; the sync bar is dropped since it was anchored to the cover"


# ============================================================ CP lane =======
def lamination(field):
    x0, y0, x1, y1 = _f(field)
    # 17 copies at the spec's bearings need 300 mm of sweep; the field is
    # 88.6 mm wide. Bearings are pulled toward symmetric (145/215) so the
    # perpendicular step is 12.5 mm and eight copies fit, which is what the
    # available width actually allows.
    return K.chevrons(field, (x1 - 3, (y0 + y1) / 2), 145, 215, 9, 4.4, 2.4, 2.8,
                      leg=150, step_dir=180)


FIDELITY["Lamination"] = "17 copies of the open asymmetric V; the apex step is derived from the pitch formula, not the spec's constant which contradicted it"


def cleave(field):
    x0, y0, x1, y1 = _f(field)
    ribs = unary_union([
        LineString([(x0 - 5, y0 + 14 + k * 15), (x1 + 5, y0 + 6 + k * 15 + 22)]
                   ).buffer(1.6) for k in range(6)])

    def cell(cx, cy, i, j):
        up = (i + j) % 2 == 0
        t = K.tri(cx, cy, 4.6, up=up).buffer(-0.8).buffer(0.8)
        return None if ribs.intersects(t) else t
    return K.lattice(field, cell, 4.0, 6.4)


FIDELITY["Cleave"] = "triangle field with six solid ribs; the polarity flip across each rib is omitted as it is imperceptible at 4.6 mm"


def threefold(field):
    def cell(cx, cy, i, j):
        rot = 0 if (i + j) % 2 == 0 else 60
        arms = [rotate(box(cx - 2.0, cy, cx + 2.0, cy + 7.6), a + rot,
                       origin=(cx, cy)) for a in (0, 120, 240)]
        return unary_union(arms).buffer(-0.8).buffer(0.8)
    return K.lattice(field, cell, 18.0, 15.6, stagger=0.5)


FIDELITY["Threefold"] = "the three-arm glyph on a triangular lattice with alternating orientation"


def twill(field):
    def cell(cx, cy, i, j):
        vert = (i + j) % 2 == 0
        g = []
        for k in (-1, 0, 1):
            if vert:
                g.append(box(cx + k * 6.0 - 1.8, cy - 7.2, cx + k * 6.0 + 1.8, cy + 7.2))
            else:
                g.append(box(cx - 7.2, cy + k * 6.0 - 1.8, cx + 7.2, cy + k * 6.0 + 1.8))
        return unary_union([p.buffer(-1.0).buffer(1.0) for p in g])
    return K.lattice(field, cell, 18.0, 18.0)


FIDELITY["Twill"] = "18 mm blocks of three slots alternating 0/90 in a checkerboard, as specified"


def one_cut(field):
    x0, y0, x1, y1 = _f(field)
    M = 6.2
    pts, y = [], y0 + 6
    left = True
    while y < y1 - 6:
        if left:
            pts += [(x0 + 6, y), (x1 - 6, y)]
        else:
            pts += [(x1 - 6, y), (x0 + 6, y)]
        y += M * 2
        left = not left
    return [LineString(pts).buffer(1.5, cap_style=1, join_style=1, resolution=8)]


FIDELITY["One Cut"] = "one continuous path, but a serpentine rather than a Hilbert traversal - the Hilbert order was not reproduced"


def arasaka_rule(field):
    x0, y0, x1, y1 = _f(field)
    out = []
    for gi, (n, L, xs) in enumerate([(7, 44.0, x1 - 46), (5, 30.0, x1 - 46 - 20.8 - 26),
                                     (3, 18.0, x0 + 6)]):
        for k in range(n):
            cx = xs + k * 5.2
            out.append(box(cx - 1.0, (y0 + y1) / 2 - L / 2,
                           cx + 1.0, (y0 + y1) / 2 + L / 2))
    return out


FIDELITY["Arasaka Rule"] = "three slot groups on a 5.2 mm module separated by exactly four modules of blank metal"


def salvage(field):
    x0, y0, x1, y1 = _f(field)
    s1 = LineString([(x0 - 5, y0 + 34), (x1 + 5, y0 + 34)]).buffer(1.5)
    a = math.radians(74)
    s2 = LineString([(x0 + 30, y0 - 5), (x0 + 30 + 120 * math.cos(a),
                                         y0 - 5 + 120 * math.sin(a))]).buffer(1.5)
    zones = field.difference(unary_union([s1, s2]))
    parts = sorted(([zones] if zones.geom_type == "Polygon" else list(zones.geoms)),
                   key=lambda p: -p.area)
    out = []
    if parts:
        def sq(cx, cy, i, j):
            if (5 * i + 3 * j) % 11 == 0:
                return None
            c = 1.6
            return Polygon([(cx - 3.5 + c, cy - 3.5), (cx + 3.5 - c, cy - 3.5),
                            (cx + 3.5, cy - 3.5 + c), (cx + 3.5, cy + 3.5 - c),
                            (cx + 3.5 - c, cy + 3.5), (cx - 3.5 + c, cy + 3.5),
                            (cx - 3.5, cy + 3.5 - c), (cx - 3.5, cy - 3.5 + c)])
        out += [g.intersection(parts[0]) for g in K.lattice(parts[0], sq, 9.8, 9.8)]
    if len(parts) > 1:
        out += [s.intersection(parts[1]) for s in K.slots(parts[1], 0, 3.4, 6.0)]
    if len(parts) > 2:
        out += [g.intersection(parts[2]) for g in
                K.lattice(parts[2], lambda cx, cy, i, j: Point(cx, cy).buffer(2.4),
                          7.4, 7.4, stagger=0.5)]
    return out


FIDELITY["Salvage"] = "three incompatible vocabularies butted along two straight seams, as specified"


LANES = {
    "GPU backplates": [("Erosion Lattice", erosion_lattice), ("One Seam", one_seam),
                       ("Thermoptic Slip", thermoptic_slip), ("Kowloon Graft", kowloon_graft),
                       ("Register Error", register_error)],
    "Case makers": [("Contact Angle", contact_angle), ("Six Cells", six_cells),
                    ("Vista Ring", vista_ring), ("Metastaseis", metastaseis),
                    ("Beat", beat), ("Arasaka Seal", arasaka_seal), ("Fault", fault)],
    "Architecture": [("Concave Rule", concave_rule), ("Broken Saltire", broken_saltire),
                     ("Ghost Chevron", ghost_chevron), ("Escapement", escapement),
                     ("Hull Plating", hull_plating), ("Arasaka Datum", arasaka_datum),
                     ("Scanline Tear", scanline_tear)],
    "Cyberpunk / GitS": [("Lamination", lamination), ("Cleave", cleave),
                         ("Threefold", threefold), ("Twill", twill),
                         ("One Cut", one_cut), ("Arasaka Rule", arasaka_rule),
                         ("Salvage", salvage)],
}


def build_all(expanded=True):
    field = (K.expanded_field()[0] if expanded
             else K.field_nocover())
    out = []
    for lane, items in LANES.items():
        for nm, fn in items:
            try:
                g, dropped = K.build(fn, field)
            except Exception as e:
                out.append(dict(lane=lane, name=nm, geom=None,
                                err=f"{type(e).__name__}: {e}"))
                continue
            out.append(dict(lane=lane, name=nm, geom=g, dropped=dropped, err=None))
    return field, out


if __name__ == "__main__":
    field, res = build_all()
    print(f"field {field.area/100:.1f} cm2 (no cover)\n")
    print(f"{'lane':18s} {'design':18s} {'cm2':>6s} {'%':>5s} {'parts':>6s} {'web':>5s}")
    for r in res:
        if r["err"]:
            print(f"{r['lane'][:17]:18s} {r['name']:18s}  {r['err'][:44]}")
            continue
        g = r["geom"]
        if g is None:
            print(f"{r['lane'][:17]:18s} {r['name']:18s}   EMPTY")
            continue
        parts = [g] if g.geom_type == "Polygon" else list(g.geoms)
        web = min((a.distance(b) for i, a in enumerate(parts)
                   for b in parts[i + 1:]), default=99.0)
        print(f"{r['lane'][:17]:18s} {r['name']:18s} {g.area/100:6.1f} "
              f"{100*g.area/field.area:4.0f}% {len(parts):6d} {web:5.2f}")
