"""Round two: 20 more vent-field designs, on the expanded 161.2 cm2 field.

Five agents working in parallel and isolated - two mining the project archive
(the 8 backplate_variants treatments and the 5 gradient x isotherm hybrids),
three free to innovate along briefs they could not see each other's copy of.

Every design in this round declared its own minimum web and all cleared 2.0 mm,
which is a change from round one where three specs were uncuttable.

FIDELITY as before: recognisable realisations, not certified reproductions.
Several of these call for real simulation - a Laplace stream function, a
constrained Delaunay triangulation, dendritic growth, granular settling. Those
are approximated by cheaper constructions that produce the same read; the note
in FID2 says which.
"""

from __future__ import annotations

import math

import numpy as np
from shapely.affinity import rotate, scale, translate
from shapely.geometry import LineString, MultiPoint, Point, Polygon, box
from shapely.ops import unary_union

import vent_kit as K
from die_window import CENTRE as DIE_C, POLY as DIE_POLY

FID2 = {}
RNG = np.random.default_rng(7)


def obstacles():
    """The keep-out set several of these designs are generated FROM."""
    from config import SCANNED as S
    from hole_pattern import HOLES
    import backplate_v3 as B
    cx, cy = DIE_C
    out = [Polygon(DIE_POLY).buffer(K.DIE_CLEAR)]
    for nm, w, h, along, across, n in S.PADS_VS_DIE:
        px, py = cx + along, cy + across
        out.append(box(px - h / 2, py - w / 2, px + h / 2, py + w / 2)
                   .buffer(K.PAD_CLEAR))
    nx0 = B.NOTCH_CX - B.NOTCH_W / 2 - B.NOTCH_EXTRA_BRACKET
    out.append(box(nx0, -5, B.NOTCH_CX + B.NOTCH_W / 2, B.NOTCH_D)
               .buffer(K.NOTCH_CLEAR))
    for x, y, t, s in HOLES:
        out.append(Point(x, y).buffer(K.SCREW_CLEAR))
    return unary_union(out)


def bands(seed, field, r0, widths, gaps, n):
    """Nested offset bands of a seed geometry - a printed distance map."""
    out, r = [], r0
    for k in range(n):
        w = widths(k)
        g = gaps(k)
        try:
            ring = seed.buffer(r + w).difference(seed.buffer(r))
        except Exception:
            break
        if not ring.is_empty:
            out.append(ring)
        r += w + g
        if r > 260:
            break
    return out


def dashify(geoms, run, gap, field):
    """Break bands into runs along X so contours dissolve into dashes."""
    x0, y0, x1, y1 = field.bounds
    cutters = []
    x = x0 - 20
    while x < x1 + 20:
        cutters.append(box(x + run, y0 - 20, x + run + gap, y1 + 20))
        x += run + gap
    cut = unary_union(cutters)
    return [g.difference(cut) for g in geoms]


# ------------------------------------------------------------ archive-a ----
def standoff_contours(field):
    S = obstacles()
    b = bands(S, field, 4.0,
              lambda k: 2.6 + min(1.8, 0.20 * k),
              lambda k: 5.4 + min(3.6, 0.42 * k), 16)
    return dashify(b, 60.0, 3.2, field)


FID2["Standoff Contours"] = "offset bands of the real keep-out set, dashed; the per-ring tie bearings and the fastener ring cull are not implemented"


def load_path_truss(field):
    x0, y0, x1, y1 = field.bounds
    NB = 8
    step = (x1 - x0) / NB
    mid = (y0 + y1) / 2
    members = []
    for k in range(NB + 1):
        xk = x0 + step * k
        members.append(box(xk - 3.0, y0, xk + 3.0, y1))
    for k in range(NB):
        a, b = x0 + step * k, x0 + step * (k + 1)
        lo, hi = (y0, y1) if k % 2 == 0 else (y1, y0)
        members.append(LineString([(a, lo), (b, mid)]).buffer(2.4, cap_style=2))
        members.append(LineString([(a, hi), (b, mid)]).buffer(2.4, cap_style=2))
    frame = unary_union(members).buffer(2.0).buffer(-2.0)
    voids = field.difference(frame)
    return [voids]


FID2["Load Path"] = "eight-bay chevron truss with the rails as chords; the quadratic member taper and node migration are simplified to a constant width"


def escape_route(field):
    x0, y0, x1, y1 = field.bounds
    S = obstacles()
    out = []
    for k in range(11):
        y = 17.0 + 8.6 * k
        if y < y0 or y > y1:
            continue
        out.append(LineString([(x0 - 6, y), (x1 + 6, y)]).buffer(1.5, cap_style=2))
    for j in range(6):
        x = 133.0 + 6.2 * j
        out.append(LineString([(x, 30.5), (x, 17.0 + 8.6 * j)]
                              ).buffer(1.5, cap_style=2))
    for k in range(0, 11, 3):
        y = 17.0 + 8.6 * k
        for x in (x0 + 34, x0 + 96, x0 + 150):
            out.append(Point(x, y).buffer(3.5))
    return [g.difference(S.buffer(1.0)) for g in out]


FID2["Escape Route"] = "escape fan from the plug into eleven lanes with via swellings; doglegs around obstacles are done by subtraction rather than by re-routing"


def interference(field):
    a = 10.2

    def cell(cx, cy, i, j):
        u = (cx - 133.1) * math.cos(math.radians(20)) + (cy - 47.6) * math.sin(math.radians(20))
        v = -(cx - 133.1) * math.sin(math.radians(20)) + (cy - 47.6) * math.cos(math.radians(20))
        s = 4.4 + 1.2 * (math.cos(2 * math.pi * u / 71) + math.cos(2 * math.pi * v / 47))
        if s < 2.2:
            return None
        r = s / math.sqrt(3)
        return Polygon([(cx + r * math.cos(math.radians(30 + 60 * q)),
                         cy + r * math.sin(math.radians(30 + 60 * q)))
                        for q in range(6)])
    return K.lattice(field, cell, a, a * math.sqrt(3) / 2, stagger=0.5)


FID2["Interference"] = "hexagon size driven by two crossed sine waves, as specified"


# ------------------------------------------------------------ archive-b ----
def truss(field):
    from scipy.spatial import Delaunay
    x0, y0, x1, y1 = field.bounds
    inner = field.buffer(-4.0)
    pts = []
    for _ in range(4000):                       # capped: the rejection loop
        if len(pts) >= 90:                      # could otherwise never satisfy
            break
        p = (RNG.uniform(x0, x1), RNG.uniform(y0, y1))
        if not inner.contains(Point(p)):
            continue
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > 169.0 for q in pts):
            pts.append(p)
    if len(pts) < 4:
        return []
    P = np.array(pts)
    tri = Delaunay(P)
    out = []
    for s in tri.simplices:
        poly = Polygon(P[s]).buffer(-1.6)
        if not poly.is_empty and poly.area > 8:
            out.append(poly)
    return out


FID2["Truss"] = "Delaunay of a Poisson-disc point set inside the field; the spec's constrained triangulation and graded density are approximated"


def fanout(field):
    x0, y0, x1, y1 = field.bounds
    segs, frontier = [], [(137.1, 37.0, 0)]
    for depth in range(5):
        nxt = []
        for (px, py, d) in frontier:
            run = 26.0 - 3.0 * depth
            spread = 26.0 / (depth + 1)
            for sgn in (+1, -1):
                qx, qy = px + run, py + sgn * spread
                qy = min(max(qy, y0 + 4), y1 - 4)
                segs.append(LineString([(px, py), (px + run * .45, py)]
                                       ).buffer(1.4, cap_style=2))
                segs.append(LineString([(px + run * .45, py), (qx, qy)]
                                       ).buffer(1.4, cap_style=2))
                segs.append(Point(qx, qy).buffer(2.6))
                nxt.append((qx, qy, depth + 1))
        frontier = nxt
        if frontier and frontier[0][0] > x1:
            break
    return segs


FID2["Fanout"] = "binary fanout from the gate the pad and plug leave open, with a via pad at every branch; 45-degree-only routing relaxed"


def ghost_bone(field):
    seed = Polygon(DIE_POLY)
    out, o = [], 12.0
    for k in range(17):
        try:
            ring = seed.buffer(o)
        except Exception:
            break
        pts = []
        L = ring.exterior.length
        step = 5.4
        n = max(int(L / step), 8)
        rad = 1.35 + 0.055 * k
        for t in range(n):
            p = ring.exterior.interpolate(t / n, normalized=True)
            pts.append(Point(p.x, p.y).buffer(min(rad, 2.6)))
        out += pts
        o += 8.0 + 0.42 * k
        if o > 220:
            break
    return out


FID2["Ghost Bone"] = "the die window's own silhouette echoed outward as halftone rings of dots, as specified"


def crossover(field):
    cx, cy = DIE_C
    P = 9.0
    out = []
    for k in range(4, 26):
        r = P * k
        t = max(0.0, min((r - 45) / 175.0, 1.0))
        duty = 0.27 + 0.46 * (t ** 1.25)
        w = P * duty
        if w < 2.4:
            continue
        ring = Point(cx, cy).buffer(r + w / 2).difference(Point(cx, cy).buffer(r - w / 2))
        out.append(ring)
    return out


FID2["Crossover"] = "polar bands about the die with the duty cycle sweeping 27 to 73 per cent, as specified"


# --------------------------------------------------------------- free-a ----
def plume(field):
    x0, y0, x1, y1 = field.bounds
    src = (137.0, 37.0)
    out = []
    for k in range(26):
        a = math.radians(-52 + k * 4.2)
        pts, px, py = [], src[0], src[1]
        for step in range(60):
            px += 3.4 * math.cos(a)
            py += 3.4 * math.sin(a)
            a += math.radians(1.6 * math.sin(step * 0.28 + k))
            pts.append((px, py))
            if px > x1 + 6 or py < y0 - 6 or py > y1 + 6:
                break
        if len(pts) > 3:
            w = 2.4 + 2.2 * (k % 3) / 2.0
            out.append(LineString(pts).buffer(w / 2, cap_style=1))
    return out


FID2["Plume"] = "streamlines fanning from the gate; traced by a steered walk rather than by relaxing a Laplace stream function"


def quench(field):
    S = obstacles()
    seeds = []
    for g in ([S] if S.geom_type == "Polygon" else list(S.geoms)):
        c = g.centroid
        seeds.append((c.x, c.y))
    out = []
    for order, (w, reach, forks) in enumerate([(4.8, 78, 2), (3.4, 44, 2), (2.6, 22, 1)]):
        for si, (sx, sy) in enumerate(seeds):
            for f in range(2 + order):
                a = RNG.uniform(0, 2 * math.pi)
                pts, px, py = [(sx, sy)], sx, sy
                for step in range(int(reach / 4)):
                    px += 4.0 * math.cos(a)
                    py += 4.0 * math.sin(a)
                    a += RNG.uniform(-0.42, 0.42)
                    pts.append((px, py))
                out.append(LineString(pts).buffer(w / 2, cap_style=1))
    return out


FID2["Quench"] = "a hierarchical crack network launched from the real keep-out corners; the widths follow the spec's three orders but the walk is stochastic"


def chill_front(field):
    x0, y0, x1, y1 = field.bounds
    out = []
    mis = [0, 6, -4, 9, -7, 3, -9, 5, -2, 8, -6, 1]
    for n in range(12):
        sx = 143.0 + 14.0 * n
        if sx > x1 - 4:
            break
        a = math.radians(270 + mis[n % len(mis)])
        pts, px, py = [(sx, y1)], sx, y1
        for step in range(40):
            px += 2.8 * math.cos(a)
            py += 2.8 * math.sin(a)
            pts.append((px, py))
            if py < y0:
                break
        out.append(LineString(pts).buffer(1.8, cap_style=2))
        for b in range(1, 7):
            t = b / 7.0
            bx = sx + (px - sx) * t
            by = y1 + (py - y1) * t
            for sgn in (+1, -1):
                ba = a + sgn * math.radians(58)
                out.append(LineString([(bx, by),
                                       (bx + 13 * math.cos(ba), by + 13 * math.sin(ba))]
                                      ).buffer(1.3, cap_style=2))
    return out


FID2["Chill Front"] = "columnar dendrites nucleating on the far edge with a misorientation sequence and side branches, as specified"


def angle_of_repose(field):
    x0, y0, x1, y1 = field.bounds
    sizes = [(18.0, 9.0)] * 3 + [(12.0, 9.0)] * 4 + [(9.0, 9.0)] * 3
    placed, out = [], []
    for attempt in range(900):
        w, h = sizes[RNG.integers(len(sizes))]
        bx = RNG.uniform(x0 + 4, x1 - w - 4)
        talus = (x1 - bx) / (x1 - x0)
        by = RNG.uniform(y0 + 3, y0 + 6 + 96 * talus)
        b = box(bx, by, bx + w, by + h).buffer(-1.5).buffer(1.5)
        if not field.buffer(-2.0).contains(b):
            continue
        if any(b.distance(p) < 2.6 for p in placed):
            continue
        placed.append(b)
        out.append(b)
        if len(out) > 130:
            break
    return out


FID2["Angle of Repose"] = "three block sizes jammed against the plate end with a talus surface; settled by rejection sampling rather than simulation"


# --------------------------------------------------------------- free-b ----
def control_bar(field):
    x0, y0, x1, y1 = field.bounds
    out = []
    cw, ch = (x1 - x0) / 8.0, (y1 - y0) / 4.0
    for i in range(8):
        for j in range(4):
            cx0, cy0 = x0 + i * cw + 1.2, y0 + j * ch + 1.2
            cx1, cy1 = cx0 + cw - 2.4, cy0 + ch - 2.4
            t = (i + 3 * j) % 6
            if t == 0:
                for k in range(4):
                    out.append(box(cx0, cy0 + k * (ch - 2.4) / 4 + 1.0,
                                   cx1, cy0 + k * (ch - 2.4) / 4 + 3.6))
            elif t == 1:
                for k in range(5):
                    out.append(box(cx0 + k * (cw - 2.4) / 5 + 1.0, cy0,
                                   cx0 + k * (cw - 2.4) / 5 + 3.6, cy1))
            elif t == 2:
                out.append(Point((cx0 + cx1) / 2, (cy0 + cy1) / 2).buffer(7.0))
            elif t == 3:
                for k in range(3):
                    r = 3.0 + 3.4 * k
                    out += K.ring((cx0 + cx1) / 2, (cy0 + cy1) / 2, r, r + 2.4,
                                  bridges=4, bridge_w=2.6)
            elif t == 4:
                for k in range(4):
                    out.append(rotate(box(cx0 + 2 + k * 4.6, cy0 + 2,
                                          cx0 + 4.6 + k * 4.6, cy1 - 2),
                                      22, origin="centroid"))
            else:
                out.append(box(cx0 + 2, cy0 + 2, cx1 - 2, cy1 - 2)
                           .buffer(-2.0).buffer(2.0))
    return out


FID2["Control Bar"] = "an 8x4 grid of prepress targets on a 2.4 mm gutter; six tile types rather than the full set of printer's measurement patches"


def datum(field):
    x0, y0, x1, y1 = field.bounds
    out = []
    chains = [(y0 + 12, [0.10, 0.26, 0.40, 0.62, 0.86]),
              (y0 + 44, [0.16, 0.44, 0.70]),
              (y0 + 74, [0.08, 0.30, 0.52, 0.74, 0.94])]
    for cy, stops in chains:
        for a, b in zip(stops[:-1], stops[1:]):
            ax, bx = x0 + a * (x1 - x0), x0 + b * (x1 - x0)
            out.append(box(ax + 2.0, cy - 1.3, bx - 2.0, cy + 1.3))
            for xx in (ax, bx):
                out.append(Polygon([(xx, cy), (xx + 5.0, cy - 1.8),
                                    (xx + 5.0, cy + 1.8)]))
        for sx in stops:
            xx = x0 + sx * (x1 - x0)
            out.append(box(xx - 1.3, cy + 3.0, xx + 1.3, cy + 16.0))
    out.append(box(x0 + 8, y1 - 14, x1 - 8, y1 - 11.5))
    return out


FID2["Datum"] = "dimension chains, arrowheads and witness lines as a forest of cuts, never a loop, so no metal can drop out"


def stave(field):
    x0, y0, x1, y1 = field.bounds
    out = []
    stations = [x0 + s for s in (18, 46, 63, 96, 118, 141, 158)]
    for y in (16, 29, 42, 55, 68, 81, 94, 107):
        if y < y0 or y > y1:
            continue
        cuts = [x0 - 6]
        for s in stations:
            cuts += [s - 2.0, s + 2.0]
        cuts.append(x1 + 6)
        for a, b in zip(cuts[0::2], cuts[1::2]):
            if b - a > 5:
                out.append(box(a, y - 1.3, b, y + 1.3))
    return out


FID2["Stave"] = "eight ruled lines interrupted by aligned white barline bridges, as specified"


def tabular(field):
    x0, y0, x1, y1 = field.bounds
    widths = [4.6 * n + 6.0 for n in (4, 2, 6, 3, 4, 2, 3, 6, 4)]
    xs, x = [], x0
    for w in widths:
        xs.append((x, x + w))
        x += w + 3.6
        if x > x1:
            break
    rows = [(y0 + 6, 6.0), (y0 + 20, 2.4), (y0 + 33, 2.4), (y0 + 46, 2.4),
            (y0 + 59, 3.6), (y0 + 72, 2.4), (y0 + 85, 2.4), (y0 + 96, 6.0)]
    solid = []
    for (ry, rw) in rows:
        solid.append(box(x0, ry - rw / 2, x1, ry + rw / 2))
    for (a, b) in xs:
        solid.append(box(a - 1.2, y0, a + 1.2, y1))
    keep = unary_union(solid)
    return [field.difference(keep.buffer(0.0))]


FID2["Tabular"] = "figure/ground inverted: the field is open and the remaining metal is a ruled table on three weights"


# --------------------------------------------------------------- free-c ----
def load_path_nodes(field):
    from hole_pattern import HOLES
    x0, y0, x1, y1 = field.bounds
    nodes = [(x, y) for x, y, t, s in HOLES
             if field.buffer(20).contains(Point(x, y))]
    nodes += [(x0 + 8, y0 + 8), (x1 - 8, y0 + 8), (x0 + 8, y1 - 8), (x1 - 8, y1 - 8),
              ((x0 + x1) / 2, (y0 + y1) / 2)]
    mem = []
    for i, a in enumerate(nodes):
        d = sorted(((math.hypot(a[0] - b[0], a[1] - b[1]), b)
                    for b in nodes if b != a))
        for dist, b in d[:3]:
            t = min(dist / 120.0, 1.0)
            w = 6.5 - 3.3 * t
            mem.append(LineString([a, b]).buffer(w / 2, cap_style=2))
    frame = unary_union(mem)
    return [field.difference(frame)]


FID2["Load Path (nodes)"] = "a truss whose nodes are the fastener positions and whose members thicken toward anchors; three nearest neighbours per node"


def micro_joint(field):
    x0, y0, x1, y1 = field.bounds
    blanks, out = [], []
    specs = [(34, 26), (26, 26), (20, 20), (44, 18), (26, 18), (18, 18),
             (30, 22), (22, 30), (18, 26), (36, 20), (24, 24), (20, 32),
             (28, 18), (16, 20)]
    ry = y0 + 4
    rx = x0 + 4
    rowh = 0
    for (w, h) in specs:
        if rx + w > x1 - 4:
            rx = x0 + 4
            ry += rowh + 3.2
            rowh = 0
        b = box(rx, ry, rx + w, ry + h).buffer(-4.0).buffer(4.0)
        if field.buffer(-3.0).contains(b):
            blanks.append(b)
            out.append(b.buffer(1.6).difference(b.buffer(-1.6)))
        rx += w + 3.2
        rowh = max(rowh, h)
    # micro-joints: three ties per blank
    ties = []
    for b in blanks:
        L = b.exterior.length
        for t in (0.12, 0.47, 0.79):
            p = b.exterior.interpolate(t, normalized=True)
            ties.append(Point(p.x, p.y).buffer(2.2))
    cut = unary_union(out).difference(unary_union(ties)) if out else None
    return [cut] if cut is not None else []


FID2["Micro-Joint"] = "a nesting layout: blanks outlined by a common-line kerf, each held by three micro-joints so nothing drops out"


def isobath(field):
    S = obstacles()
    bnd = unary_union([field.boundary, S.boundary.intersection(field.buffer(2))])
    out = []
    for lvl in (6.0, 17.0, 28.0, 39.0):
        try:
            band = bnd.buffer(lvl + 1.4).difference(bnd.buffer(lvl - 1.4))
        except Exception:
            continue
        if not band.is_empty:
            out.append(band)
    return out


FID2["Isobath"] = "channels at level sets of distance to the field's own boundary, so the lines are a contour map of the shape itself"


def arrest(field):
    x0, y0, x1, y1 = field.bounds
    S = obstacles()
    seeds = []
    for g in ([S] if S.geom_type == "Polygon" else list(S.geoms)):
        b = g.bounds
        seeds += [(b[0], b[3]), (b[2], b[1])]
    seeds = [s for s in seeds if field.buffer(6).contains(Point(s))][:8]
    out = []
    for si, (sx, sy) in enumerate(seeds):
        a = RNG.uniform(0, 2 * math.pi)
        stack = [(sx, sy, a, 0)]
        while stack:
            px, py, ang, gen = stack.pop()
            pts = [(px, py)]
            for step in range(14):
                px += 3.6 * math.cos(ang)
                py += 3.6 * math.sin(ang)
                ang += RNG.uniform(-0.3, 0.3)
                pts.append((px, py))
            out.append(LineString(pts).buffer(1.2, cap_style=1))
            if gen < 2:
                for sgn in (+1, -1):
                    stack.append((px, py, ang + sgn * math.radians(34), gen + 1))
        out.append(Point(px, py).buffer(2.6))       # arrest hole
    return out


FID2["Arrest"] = "cracks seeded at the real re-entrant corners, forking twice and terminating in a drilled arrest hole; the walk is stochastic"


AGENTS2 = {
    "Archive A": [("Standoff Contours", standoff_contours), ("Load Path", load_path_truss),
                  ("Escape Route", escape_route), ("Interference", interference)],
    "Archive B": [("Truss", truss), ("Fanout", fanout), ("Ghost Bone", ghost_bone),
                  ("Crossover", crossover)],
    "Free: process": [("Plume", plume), ("Quench", quench),
                      ("Chill Front", chill_front), ("Angle of Repose", angle_of_repose)],
    "Free: notation": [("Control Bar", control_bar), ("Datum", datum),
                       ("Stave", stave), ("Tabular", tabular)],
    "Free: structure": [("Load Path (nodes)", load_path_nodes),
                        ("Micro-Joint", micro_joint), ("Isobath", isobath),
                        ("Arrest", arrest)],
}


def build_round2(field=None, verbose=False):
    import time
    if field is None:
        field = K.expanded_field()[0]
    out = []
    for lane, items in AGENTS2.items():
        for nm, fn in items:
            t0 = time.time()
            try:
                g, dropped = K.build(fn, field)
                out.append(dict(lane=lane, name=nm, geom=g, dropped=dropped, err=None))
            except Exception as e:
                out.append(dict(lane=lane, name=nm, geom=None, dropped=0,
                                err=f"{type(e).__name__}: {e}"))
            if verbose:
                print("   %-22s %5.1fs" % (nm, time.time() - t0), flush=True)
    return field, out


if __name__ == "__main__":
    field, res = build_round2(verbose=True)
    print(f"field {field.area/100:.1f} cm2\n")
    print(f"{'agent':16s} {'design':20s} {'cm2':>6s} {'%':>5s} {'parts':>6s} {'web':>5s}")
    for r in res:
        if r["err"] or r["geom"] is None:
            print(f"{r['lane']:16s} {r['name']:20s}   {r['err'] or 'EMPTY'}")
            continue
        g = r["geom"]
        parts = [g] if g.geom_type == "Polygon" else list(g.geoms)
        web = min((a.distance(b) for i, a in enumerate(parts)
                   for b in parts[i + 1:]), default=99.0)
        print(f"{r['lane']:16s} {r['name']:20s} {g.area/100:6.1f} "
              f"{100*g.area/field.area:4.0f}% {len(parts):6d} {web:5.2f}")
