"""Three designs whose Graf3X is VERIFIED legible by OCR, not asserted.

Requested 2026-08-25: Bit Plane, Interference and Interference / long wave,
each carrying the wordmark bottom-right, confirmed readable by an old OCR.
And Bit Plane reworked so its apertures come in small and large sizes that
cluster, driven by the same interference idea.

HOW THE MARK IS MADE READABLE
    Every earlier attempt put the wordmark INTO the carrier - grown dots,
    deleted cells, interrupted bands - and none of them survived an OCR,
    because a sampled carrier at an 82 mm mark has about 4 rows across a cap
    height where a letterform needs 8.

    These use the construction that passes: a QUIET ZONE where the carrier is
    suppressed, and the letters CUT inside it so they read dark on light,
    which is what an OCR expects. The a's counter is an island held by ONE
    2.4 mm bridge at its foot - one, because two (or one spanning the glyph)
    splits the letter's cut into separate components and the segmenter then
    reads two marks instead of an a.

    ocr_check.py verifies it: 62 templates, upper and lower case plus digits,
    each glyph must beat all 61 alternatives. Run this module to see the read.
"""

from __future__ import annotations

import math

from shapely.geometry import Polygon, box
from shapely.ops import nearest_points, unary_union

import vent_kit as K
from config import MFG
from vent_iterate import wordmark

ONOTE = {}

# ---- the mark -------------------------------------------------------------
QUIET = 2.2           # halo around the letters - the part you actually see
QUIET_EXT = 2.2       # ...plus a square end cap at the line ends.
# Shrinking the zone to 20% never damages a letter - every size from 11.0 down
# to 1.6 mm still reads Graf3X - but it lets carrier cells into the reading
# crop, and they segment as extra characters. Those contaminants only ever
# appear off the LEFT and RIGHT ends of the line, because that is where the
# text band runs into the field.
#
# What clears them is not WIDTH but SQUARENESS. The convex hull tapers at the
# top and bottom of the G and the X, and cells tuck into those notches. A
# full-height end cap of the same 2.2 mm removes them, and the sweep confirms
# it: every extension from 10.0 down to 2.2 mm reads clean, only 0.0 fails.
# So the zone is uniform 2.2 mm all round, with square ends.

BRIDGE = 2.4          # tab holding the a's counter island
BRIDGE_DX = 1.2       # ...shifted right, to land under the a's stem rather
                      # than at the counter's midpoint

EM = 15.24            # one em of the wordmark at its final 82 mm width

# The lattice's COLUMN phase is pinned here, not taken from the field's own
# lower bound. Widening the field to take in the ground left of the die window
# moves that bound from 128.4 to 3.0, and a lattice hung off it would re-phase
# every column - the right-hand side of the plate would shift and the two
# versions would no longer be the same design on different amounts of metal.
ANCHOR_X = 128.40


def mark_parts(field):
    """(quiet zone, letter cuts). The carrier is removed inside the zone."""
    x0, y0, x1, y1 = field.bounds
    wm = wordmark(field)
    band = box(x0, y0, x1, 52.0)
    core = wm.buffer(QUIET).convex_hull
    cb = core.bounds
    quiet = core.union(box(cb[0] - QUIET_EXT, cb[1], cb[2] + QUIET_EXT, cb[3]))
    quiet = quiet.intersection(band)
    letters = []
    for g in (wm.geoms if wm.geom_type != "Polygon" else [wm]):
        cut = Polygon(g.exterior)
        for r in g.interiors:
            isl = Polygon(r)
            b = isl.bounds
            mx = (b[0] + b[2]) / 2 + BRIDGE_DX
            mx = min(mx, b[2] - BRIDGE / 2 - 0.2)      # stay inside the counter
            tab = box(mx - BRIDGE / 2, b[1] - 5.0, mx + BRIDGE / 2, b[1] + 1.5)
            cut = cut.difference(isl.union(tab))
        letters.append(cut)
    letters = _bridge_open_pockets(letters)
    return quiet, letters


def _bridge_open_pockets(letters, tries=12):
    """Widen any METAL neck under the minimum web, not just closed counters.

    The bridge loop above only walks `g.interiors` - CLOSED counters - and the
    wordmark has exactly one, the 'a' bowl. But a glyph's OPEN pockets trap
    islands of plate too, held by whatever the pocket's mouth happens to be:
    0.986 mm inside the '3' and 1.337 mm inside the 'a'. A check that measures
    distance BETWEEN cut contours cannot see it, because the failure is metal
    inside ONE contour.

    Note which way the two constraints pull. Thickening a glyph opens the CUT
    neck and CLOSES the metal neck. At zero dilation the metal web is already
    1.337 mm, so this was never a side effect of that - there is simply no
    stroke weight at which both pass, and the answer is a bridge, exactly as it
    already was for the closed counter.
    """
    import backplate_v3 as _B
    from shapely.geometry import Polygon as _P, box as _box
    from shapely.affinity import rotate as _rot
    from shapely.ops import unary_union as _uu
    from config import MFG as _M
    import math as _m
    plate = _P(_B.outline())
    r = _M.MIN_FEATURE / 2.0
    for _ in range(tries):
        cut = _uu(letters)
        mat = plate.difference(cut)
        er = mat.buffer(-r, join_style=1)
        comps = ([er] if er.geom_type == "Polygon" else list(er.geoms))
        comps = [c for c in comps if not c.is_empty]
        if len(comps) <= 1:
            return letters
        comps.sort(key=lambda c: -c.area)
        main, isl = comps[0], comps[1]
        a, b = nearest_points(main, isl)
        mx, my = (a.x + b.x) / 2.0, (a.y + b.y) / 2.0
        ang = _m.degrees(_m.atan2(b.y - a.y, b.x - a.x))
        span = max(a.distance(b) + 2 * r + 2.0, BRIDGE + 2.0)
        tab = _rot(_box(mx - span / 2, my - BRIDGE / 2,
                        mx + span / 2, my + BRIDGE / 2), ang,
                   origin=(mx, my))
        # subtract the tab from whichever letter it crosses
        letters = [(L.difference(tab) if L.intersects(tab) else L)
                   for L in letters]
    return letters


# ---- row alignment --------------------------------------------------------
def aligned(field, cell_fn, px, py, stagger=0.0, origin_field=None):
    """A lattice whose row stack is CENTRED in the field, not hung off y0.

    K.lattice hangs its rows off the lower bound of the field, which puts the
    first row half inside the boundary and leaves whatever remainder there is
    as a ragged partial row at the top. Both end rows then get cut, which is
    the thing that reads as unfinished.

    Two passes: generate once to measure how tall the cells actually are (they
    vary - that is the whole point of these designs), then work out how many
    whole rows fit between the rails and centre that stack, so the top and
    bottom rows sit fully inside with equal margin.
    """
    # ONE ORIGIN FOR TWO PARTS. The row stack is centred in the field's
    # y-bounds, so a second field with different bounds - the cover's roof -
    # would get a different first row and the pattern would not continue
    # across the plate/roof edge. origin_field says "centre the stack in
    # THAT field, then lay the lattice over this one".
    of = field if origin_field is None else origin_field
    bx0, y0, _, y1 = of.bounds
    ox = ANCHOR_X - math.ceil((ANCHOR_X - bx0) / px) * px
    probe = K.lattice(of, cell_fn, px, py, x0=ox, stagger=stagger)
    if not probe:
        return K.lattice(field, cell_fn, px, py, x0=ox, stagger=stagger)
    half = max((c.bounds[3] - c.bounds[1]) / 2 for c in probe)
    span = (y1 - y0) - 2 * half
    if span <= 0:
        return K.lattice(field, cell_fn, px, py, x0=ox, stagger=stagger)
    n = int(span // py)                       # gaps that fit -> n+1 rows
    first = y0 + half + (span - n * py) / 2
    # the roof lies above y1 of the plate field's rails: extend the lattice
    # start downward by whole rows so it still covers a field that reaches
    # lower than the origin field, and let K.lattice run up as far as needed
    fy0 = field.bounds[1]
    while first - py >= fy0 - py:
        if first - py < fy0:
            break
        first -= py
    return K.lattice(field, cell_fn, px, py, x0=ox, y0=first, stagger=stagger)


def build_one(fn, field, mark=True, min_feature=None):
    """Assemble a design: WHOLE cells only, letters clipped, web enforced.

    Cells are kept only if the field CONTAINS them. Intersecting instead - the
    default everywhere else in this project - shaves the cells the boundary
    crosses into half hexagons, stubs and dashes. The agent that wrote
    Interference specified the opposite in its own generator (delete, never
    trim; nothing is ever cut in half), and it was right - the pipeline simply
    had not been doing it.

    Letters are the exception: they are the subject, so they are clipped
    rather than dropped. In practice they sit well inside the field and the
    clip is a no-op, but a design change that moved them must not silently
    delete the wordmark.
    """
    mf = MFG.MIN_FEATURE if min_feature is None else min_feature
    cells = fn(field)
    keep = [c for c in cells if not c.is_empty and field.contains(c)]
    if mark:
        quiet, letters = mark_parts(field)
        # The READING CROP is kept clear too, not just the halo. Centring the
        # rows moved one to within 0.04 mm of the halo - legal, and 2.24 mm
        # from the nearest letter, so it cuts fine - but it pokes into the
        # window an OCR is handed and segments as a character. The halo stays
        # the 2.2 mm asked for; this adds 1.2 mm at the top and bottom of the
        # line only, and it makes "the crop is clean" a property of the
        # geometry instead of an accident of where the rows happened to land.
        quiet = quiet.union(box(OCR_BOX[0], OCR_BOX[1], OCR_BOX[2], OCR_BOX[3]))
        keep = [c for c in keep if not c.intersects(quiet)]
        keep += [g.intersection(field) for g in letters]
    keep = [c for c in keep if not c.is_empty and c.area >= 3.0]
    if not keep:
        return None, 0
    # ENFORCE THE WEB AT THE WEB RULE, not at min feature. These are two
    # different numbers for two different things and this call used the wrong
    # one, so raising vent_kit.MIN_WEB changed nothing here and the tightest
    # web on the Interference plate stayed at 2.011 mm.
    return K.enforce(unary_union(keep), max(mf, K.MIN_WEB))


# ---- 1 & 2: interference --------------------------------------------------
def _interference(field, a, wu, wv, s0, amp, dy=0.0, floor=None, ceil=None,
                  origin_field=None):
    """dy translates the WAVE FIELD down; the lattice itself is uniform, so
    moving it would change nothing but which cells fall off the edges."""
    def cell(cx, cy, i, j):
        sy = cy + dy
        u = ((cx - 133.1) * math.cos(math.radians(20))
             + (sy - 47.6) * math.sin(math.radians(20)))
        v = (-(cx - 133.1) * math.sin(math.radians(20))
             + (sy - 47.6) * math.cos(math.radians(20)))
        s = s0 + amp * (math.cos(2 * math.pi * u / wu)
                        + math.cos(2 * math.pi * v / wv))
        if floor is not None:
            s = max(s, floor)                 # a trough still gets an aperture
        elif s < 2.4:
            return None
        if ceil is not None:
            s = min(s, ceil)                  # ...and a crest still fits the strip
        r = s / math.sqrt(3)
        return Polygon([(cx + r * math.cos(math.radians(30 + 60 * q)),
                         cy + r * math.sin(math.radians(30 + 60 * q)))
                        for q in range(6)])
    return aligned(field, cell, a, a * math.sqrt(3) / 2, stagger=0.5,
                   origin_field=origin_field)


def interference_ocr(field, floor=None, ceil=None, origin_field=None):
    return _interference(field, 10.2, 71, 47, 4.4, 1.2, floor=floor, ceil=ceil,
                         origin_field=origin_field)


ONOTE["Interference / Graf3X, OCR"] = "the original hexagon field, wavelengths 71 and 47 mm, with a quiet zone and the mark cut into it. OCR reads Graf3X, all six characters against 62 templates"


def interference_long_ocr(field, floor=None, ceil=None, origin_field=None):
    return _interference(field, 11.4, 122, 88, 5.0, 2.2, dy=EM, floor=floor,
                         ceil=ceil, origin_field=origin_field)


ONOTE["Interference long wave / Graf3X, OCR"] = "the long-wave variant - broad blooms rather than a fine ripple - with the same verified mark, and the wave field dropped one em (15.24 mm) so the bloom sits in the middle of the plate instead of riding the top edge"


# ---- 3: bit plane ---------------------------------------------------------
# The crest - where both cosines peak together and the pads go largest - is
# placed deliberately. Left at its natural origin it landed under the cable
# cover, hiding the one part of the design carrying the most removed material.
# CREST is where it goes instead: above the 3 and the X, in a region measured
# at 93% clear of the cover.
CREST = (280.0, 57.0)
_BP_ORIGIN = (133.1, 47.6)
BP_SHIFT = (CREST[0] - _BP_ORIGIN[0], CREST[1] - _BP_ORIGIN[1])


def bit_plane_ocr(field, floor=None, ceil=None, origin_field=None):
    """A bit plane whose cell SIZE is set by the interference field.

    The original was binary - a cell was on or off - so it read as static. Here
    the same interference function that drives Interference sets which of three
    size classes a cell takes, and because the field is smooth the classes
    arrive in patches: runs of small pads, runs of large ones, with the
    transition legible as a band. Small and large group because the field
    groups them, not because they were placed.
    """
    SIZES = [(2.4, 0.5), (4.0, 0.8), (5.8, 1.1)]      # (side, corner radius)
    dx, dy = BP_SHIFT

    def cell(cx, cy, i, j):
        sx, sy = cx - dx, cy - dy
        u = ((sx - 133.1) * math.cos(math.radians(20))
             + (sy - 47.6) * math.sin(math.radians(20)))
        v = (-(sx - 133.1) * math.sin(math.radians(20))
             + (sy - 47.6) * math.cos(math.radians(20)))
        f = (math.cos(2 * math.pi * u / 96) + math.cos(2 * math.pi * v / 63))
        if f < -0.75 and floor is None:
            return None                              # dropout, keeps it digital
        k = 0 if f < 0.10 else (1 if f < 1.05 else 2)
        side, rad = SIZES[k]
        if floor is not None and side < floor:
            side, rad = floor, min(rad, floor * 0.18)
        if ceil is not None and side > ceil:
            side, rad = ceil, min(rad, ceil * 0.18)
        return box(cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2
                   ).buffer(-rad).buffer(rad)
    return aligned(field, cell, 8.0, 8.0, origin_field=origin_field)


ONOTE["Bit Plane / Graf3X, OCR"] = "the bit plane rebuilt on the interference field: three pad sizes, chosen by quantising the same smooth function, so small and large arrive in patches rather than at random. The crest - the patch of largest pads - is placed above the 3 and the X, clear of the cable cover that was hiding it"


DESIGNS = [("Interference / Graf3X, OCR", interference_ocr),
           ("Interference long wave / Graf3X, OCR", interference_long_ocr),
           ("Bit Plane / Graf3X, OCR", bit_plane_ocr)]

OCR_BOX = (207, 20, 297, 42)


def narrow_field():
    """The field as shortlisted: everything right of the die window."""
    return K.expanded_field()[0]


def full_field():
    """...plus the ground LEFT of the window, wrapping it on both sides."""
    return K.expanded_field(x0=K.INSET)[0]


def plate_field():
    """THE field the plates are cut with (2026-09-02): the whole plate, both
    sides of the die window and under the cover, minus the FEET.

    The owner asked for the holes on the bracket side and under the carcass
    that the narrow field never had. The feet are kept out because tape does
    not bond over a hole: each foot's plan footprint - the untrimmed
    candidate, so this needs no carcass blank and cannot recurse - buffered
    1.0 mm.
    """
    import cover_ribbon as RB
    p = RB.route45()
    feet = unary_union([RB.folded_foot(RB.candidate_foot(i, RB.foot_side_for(i), p), p)
                        .buffer(1.0) for i in range(len(p) - 1)
                        if RB.foot_side_for(i) is not None])
    return full_field().difference(feet)


def roof_field():
    """Where the cover's top face may carry the same pattern.

    Between the fold lines less the vendor's 5.99 mm bend keep-out on each
    side (13.07 mm of the 25.05), MIN_WEB inside every free edge including
    the corner reliefs, and the keep-out again from the end cap's fold at the
    plug end.
    """
    import cover_ribbon as RB
    p = RB.route45()
    d = RB.carcass_dev()
    top, _flaps = RB.carcass_blank(p, roof_vents=False)
    inner = d["fold1"] - RB.BEND_KEEPOUT
    a = RB.offset(p, inner, RB.SHOW)
    b = RB.offset(p, inner, RB.FAR)
    band = Polygon(a + b[::-1]).buffer(0)
    (ax, ay), (bx, by) = p[0], p[1]
    L = math.hypot(bx - ax, by - ay) or 1.0
    ux, uy = (bx - ax) / L, (by - ay) / L
    k = RB.BEND_KEEPOUT
    endkeep = Polygon([(ax + uy * 40, ay - ux * 40), (ax - uy * 40, ay + ux * 40),
                       (ax - uy * 40 + ux * k, ay + ux * 40 + uy * k),
                       (ax + uy * 40 + ux * k, ay - ux * 40 + uy * k)])
    return band.intersection(top.buffer(-K.MIN_WEB)).difference(endkeep)


ROOF_DESIGN = "Interference / Graf3X, OCR"
_ROOF = {}


def roof_cells():
    """The roof's vent cells, from the SAME lattice origin as the plate's
    field, so the pattern continues across the edge. One design only: the
    carcass is one part and the plates are interchangeable, so it follows
    the primary plate, Interference. Cached - carcass_blank() is called by
    every gate and this costs a field build."""
    if "g" not in _ROOF:
        fn = dict(DESIGNS)[ROOF_DESIGN]
        pf = plate_field()
        rf = roof_field()
        cells = fn(rf, origin_field=pf)
        keep = [c for c in cells if not c.is_empty and rf.contains(c)
                and c.area >= 3.0]
        g = K.enforce(unary_union(keep), max(MFG.MIN_FEATURE, K.MIN_WEB))[0] if keep else None
        _ROOF["g"] = g
    return _ROOF["g"]


FULL_SUFFIX = " + full plate"


def build_ocr(field=None, lane="OCR-verified", suffix=""):
    if field is None:
        field = plate_field()
    out = []
    for nm, fn in DESIGNS:
        g, dropped = build_one(fn, field)
        out.append(dict(lane=lane, name=nm + suffix, geom=g, dropped=dropped,
                        err=None, field=field))
    return field, out


def build_full():
    """The same three, wrapped round both sides of the die window."""
    return build_ocr(full_field(), lane="Full plate", suffix=FULL_SUFFIX)


def fn_for(card_name):
    """The design function behind a card name, either lane."""
    base = card_name[:-len(FULL_SUFFIX)] if card_name.endswith(FULL_SUFFIX) else card_name
    return dict(DESIGNS)[base]


if __name__ == "__main__":
    import ocr_check as OC
    field, res = build_ocr()
    print("field %.1f cm2   OCR window %s\n" % (field.area / 100, OCR_BOX))
    for r in res:
        g = r["geom"]
        parts = [g] if g.geom_type == "Polygon" else list(g.geoms)
        web = min((a.distance(b) for i, a in enumerate(parts)
                   for b in parts[i + 1:]), default=99.0)
        txt, det = OC.read(g, field, OCR_BOX)
        ok, why = OC.verdict(txt, det)
        print(r["name"])
        print("   %.1f cm2   %.0f%% of field   %d cuts   min web %.2f mm"
              % (g.area / 100, 100 * g.area / field.area, len(parts), web))
        print("   OCR: %r  %s - %s" % (txt, "PASS" if ok else "FAIL", why))
        if ok:
            print("        " + "  ".join("%s:%.2f" % (d["ch"], d["score"])
                                         for d in det))
        print()
