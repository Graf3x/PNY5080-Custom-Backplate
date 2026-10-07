"""The one command that says whether the files may be uploaded.

Two audit rounds, twelve agents each, found blockers my local checks could not
see - because my checks looked at the MODEL and the vendor cuts the FILE. This
reads the emitted DXFs and re-derives everything from them.

Every check below exists because something got through:

    contour validity            a blank that was five parts, not one
    contour retrace             zero-width slits down three fold lines
    BEND coincident with CUT    the laser following a fold line
    web between contours        a 0.632 mm rib, and vents over a slot
    opening WITHIN a contour    three glyphs at 1.547 mm, by the SPLIT test -
                                the vanish test passed them for weeks
    layer discipline            tapped holes are under the laser minimum on
                                purpose and must never appear on CUT
    minimum flat part           a 14.96 x 18.08 offcut nobody had measured
    feature to bend line        a tap 4 mm from a fold against a 5.99 keep-out
    washer footprint            a card screw the cover could not clear
    cap over a card hole        a screw that could not be driven

Run:  py release_gate.py     exit 0 means uploadable.
"""

from __future__ import annotations

import glob
import math
import os
import re
import sys

import ezdxf
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shapely.ops import nearest_points
from config import MFG                                       # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out",
                   "production")
LAYERS_RE = re.compile(r"^(CUT|TAP|NOTES|BEND(_(UP|DOWN))?(_\d+)?)$")
LAYERS_OK = {"CUT", "BEND", "BEND_UP", "BEND_DOWN", "TAP", "NOTES"}
MIN_PART = (9.53, 38.1)
WEB_REPORT = 6.0       # how far to look when REPORTING the tightest web;
                       # the failure threshold is still MIN_FEATURE
BEND_KEEPOUT = 5.99


def _read(path):
    d = ezdxf.readfile(path)
    msp = d.modelspace()
    cut, bend, tap, other = [], [], [], []
    for e in msp:
        lay = e.dxf.layer
        if not LAYERS_RE.match(lay):
            other.append((lay, e.dxftype()))
            continue
        if lay == "NOTES":
            # TEXT ONLY. Everything on NOTES was discarded before the type
            # dispatch, so a closed contour drawn there reached no check at
            # all - not contour validity, not minimum feature, not thinnest
            # metal, not the part-size test - and the upload copies' "no text"
            # guarantee only rejects TEXT and MTEXT, so annotation drawn as
            # GEOMETRY survived the strip and went to the vendor as a cut.
            if e.dxftype() not in ("TEXT", "MTEXT"):
                other.append((lay, e.dxftype()))
            continue
        if e.dxftype() == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points()]
            if lay == "CUT":
                # AN OPEN PROFILE IS NOT A CONTOUR. Polygon() closes any ring
                # you hand it, so an unclosed polyline on CUT was silently
                # made into one and every downstream check then agreed it was
                # fine - on the layer whose stated guarantee is "closed
                # contours". A laser given an open path cuts an open path.
                if not e.closed:
                    other.append((lay, "UNCLOSED LWPOLYLINE"))
                # AND A BULGE IS AN ARC. get_points() hands back (x, y, ...,
                # bulge); taking only x and y turns an arc into its chord, so
                # a bulged segment measures as something it is not.
                if any(abs(p[4]) > 1e-9 for p in e.get_points()):
                    other.append((lay, "LWPOLYLINE with arc bulges"))
                cut.append(Polygon(pts))
            else:
                # A CLOSED PROFILE ON A NON-CUT LAYER IS NOT A BEND LINE. This
                # dropped any LWPOLYLINE that was not on CUT into `bend`, and
                # every consumer of `bend` filters for LineString - so a
                # 0.50 mm slot drawn on TAP was read by nothing at all and
                # passed. Bends are LINEs in this project; a polyline anywhere
                # but CUT is reported.
                other.append((lay, "LWPOLYLINE"))
        elif e.dxftype() == "CIRCLE":
            c = Point(e.dxf.center.x, e.dxf.center.y).buffer(
                e.dxf.radius, resolution=48)
            rec = dict(geom=c, d=e.dxf.radius * 2,
                       at=(e.dxf.center.x, e.dxf.center.y))
            if lay == "CUT":
                cut.append(rec)
            elif lay == "TAP":
                tap.append(rec)
            else:
                # A CIRCLE ON A BEND LAYER IS NOT A TAPPED HOLE. Anything not
                # on CUT went into `tap`, so a hole drawn on BEND_DOWN_90 was
                # quietly reclassified as a drill-and-tap feature and exempted
                # from the minimum hole diameter, the web, the edge distance
                # and the bend keep-out all at once.
                other.append((lay, "CIRCLE"))
        elif e.dxftype() != "LINE":
            # ANYTHING THIS READER DOES NOT HANDLE. Listing the types I could
            # think of is the same mistake one level up: a type absent from
            # the list falls through in silence, and silence reads as
            # approval. The reader handles LWPOLYLINE, CIRCLE and LINE; every
            # other type is reported, named, whatever it is.
            # AN ENTITY TYPE THE GATE DOES NOT UNDERSTAND IS NOT AN ENTITY THE
            # GATE HAS CHECKED. This reader handled LWPOLYLINE, CIRCLE and
            # LINE and let everything else fall through in silence, so an
            # 0.80 mm ARC hole or a 0.40 mm old-style POLYLINE slot on CUT
            # went to the vendor with the gate reporting exit 0. Nothing in
            # this order uses them; that is exactly why it was invisible.
            other.append((lay, e.dxftype()))
        elif e.dxftype() == "LINE":
            seg = LineString([(e.dxf.start.x, e.dxf.start.y),
                              (e.dxf.end.x, e.dxf.end.y)])
            if lay.startswith("BEND"):
                bend.append(seg)
            else:
                # A BARE LINE ON CUT OR TAP IS A DEFECT, NOT A CRASH. It used
                # to land in `other` as a LineString, and `other` is unpacked
                # as (layer, kind) pairs downstream, so the gate died with a
                # ValueError instead of saying what was wrong. An open line on
                # CUT is an unclosed profile - exactly the thing a gate exists
                # to catch.
                other.append((lay, "LINE"))
    return d, cut, bend, tap, other


def _neck(poly):
    """Width at which a contour SPLITS. Not the width at which it vanishes."""
    lo, hi = 0.0, 6.0
    for _ in range(44):
        m = (lo + hi) / 2.0
        b = poly.buffer(-m / 2.0)
        n = 0 if b.is_empty else (1 if b.geom_type == "Polygon" else len(b.geoms))
        if n != 1:
            hi = m
        else:
            lo = m
    return lo


CORNER_GAP = 0.40      # SCS published min gap where two
                       # flanges MEET at a folded corner
DECLARED_NEAR = 0.20    # the declared region is now the narrow tip itself, so this
                       # only has to absorb rounding, not span a whole V
MIN_ANGLE = 20.0        # included angle at a cut vertex, degrees
SLIVER_LEN = 1.0        # a sharp vertex whose BOTH edges are shorter than
                        # this is a boolean artefact, not a feature
PINCH_SKIP = 3.0        # along-ring arc below which two edges are simply
                        # rounding a corner together, not pinching


def _rings(poly):
    yield list(poly.exterior.coords)[:-1]
    for r in poly.interiors:
        yield list(r.coords)[:-1]


def _acute_and_pinch(name, polys, declared=()):
    """Two failures no other check in this file can see.

    KNIFE EDGES. A vertex with a small included angle is a wedge that tapers
    to a point. It is not a narrow OPENING, so the split test misses it, and
    it is not thin METAL by erosion either - eroding inward from every edge
    at once only shortens a wedge, it never detaches one. Nothing here looked
    at angles at all, which is how four 45 degree ears survived every pass.

    NOTCH AND TOOTH. Two NON-ADJACENT edges of the SAME ring passing close.
    The split test finds a neck that severs a contour; a tooth reaching back
    toward its own root does not sever anything, so cutting there changes no
    piece count and the test stays silent. Measure the ring against itself.
    """
    fails, worst, sharp = [], (1e9, None), (999.0, None, 0.0)
    tight = []
    for p in polys:
        for ring in _rings(p):
            n = len(ring)
            for k in range(n):
                ax, ay = ring[k - 1]
                bx, by = ring[k]
                cx, cy = ring[(k + 1) % n]
                ux, uy = ax - bx, ay - by
                vx, vy = cx - bx, cy - by
                lu, lv = math.hypot(ux, uy), math.hypot(vx, vy)
                if lu < 1e-9 or lv < 1e-9:
                    continue
                cs = max(-1.0, min(1.0, (ux * vx + uy * vy) / (lu * lv)))
                deg = math.degrees(math.acos(cs))
                if max(lu, lv) >= SLIVER_LEN and deg < sharp[0]:
                    sharp = (deg, (bx, by), min(lu, lv))
                if deg < MIN_ANGLE and max(lu, lv) >= SLIVER_LEN:
                    fails.append(
                        "%s: %.1f deg knife edge at (%.2f, %.2f) - a wedge "
                        "tapering to a point, min included angle %.0f"
                        % (name, deg, bx, by, MIN_ANGLE))
            if n < 6:
                continue
            segs = [LineString([ring[i], ring[(i + 1) % n]]) for i in range(n)]
            cum = [0.0]
            for sg in segs:
                cum.append(cum[-1] + sg.length)
            total = cum[-1]
            for i in range(n):
                for j in range(i + 2, n):
                    if i == 0 and j == n - 1:
                        continue
                    # ARC BETWEEN THEM, both ways round, and the two segments
                    # are not part of either arc. Writing the backward one as
                    # total - forward includes both segments in it, so a
                    # 0.35 mm closing stitch next to a 132 mm edge measured as
                    # 132 mm apart and every rounded slot end reported itself
                    # as a notch.
                    fwd = cum[j] - cum[i + 1]
                    bwd = total - cum[j + 1] + cum[i]
                    if min(fwd, bwd) < PINCH_SKIP:
                        continue
                    dd = segs[i].distance(segs[j])
                    if dd >= MFG.MIN_FEATURE and dd >= worst[0]:
                        continue
                    q = nearest_points(segs[i], segs[j])[0]
                    if dd < worst[0]:
                        worst = (dd, (q.x, q.y))
                    if dd < MFG.MIN_FEATURE:
                        tight.append((dd, (q.x, q.y)))
    # THE FLOOR IS NOT ALWAYS MIN_FEATURE. Where two flanges meet at a folded
    # corner the flat pattern has to carry a mitre slit between them, and the
    # vendor's own figure for that is CORNER_GAP - a quarter of min feature.
    # It is not a slot: it opens into a corner the moment the part is folded.
    # A mitre starts at the point where two bend lines meet, so that is how
    # this tells the two apart rather than by trusting the number.
    if sharp[1]:
        # REPORTED, NOT JUST GATED. A round-five reviewer called four corners
        # "knife-edge ears tapering to a point". They are 45.00 deg with a
        # 3.47 mm leg - an ordinary sheet-metal corner. Printing the number
        # settles that kind of claim in one line instead of an argument.
        fails.append(None)
        fails.pop()
    if worst[1] is None:
        return fails, worst, sharp
    # EVERY sub-minimum pinch, not just the tightest one. A single global
    # `worst` meant the carcass's 0.400 mm declared mitre - always the
    # tightest thing on that part - was the only pinch ever floor-tested, so
    # any other pinch on the same file could not be seen at all. A feature
    # that is there on purpose was switching the check off for a whole part.
    seen = set()
    for dd, at in sorted(tight):
        key = (round(at[0], 2), round(at[1], 2))
        if key in seen:
            continue
        seen.add(key)
        floor, why = MFG.MIN_FEATURE, ""
        for g in declared:
            reg = g.get("region")
            near = (reg is not None
                    and not reg.is_empty
                    and reg.distance(Point(at)) <= DECLARED_NEAR)
            if near or math.hypot(at[0] - g["at"][0],
                                  at[1] - g["at"][1]) <= DECLARED_NEAR:
                floor = CORNER_GAP
                why = " (declared: %s)" % g["why"]
                break
        if dd < floor - 1e-6:
            fails.append("%s: a contour pinches against ITSELF to %.3f mm "
                         "near (%.1f, %.1f) - notch and tooth, under %.2f%s"
                         % (name, dd, at[0], at[1], floor, why))
    return fails, worst, sharp


def thinnest_metal(polys):
    """The narrowest metal anywhere, exactly, with no morphology.

    ONE FUNCTION, so the self-test cannot measure something the check does
    not. Two attempts before this were wrong and the second was wrong in a
    way I had asserted was impossible.

    Counting pieces under erosion is not monotone: islands detach, then
    vanish one by one, and the count passes back through its starting value,
    so a bisection latches onto whatever crossing it brackets.

    Replacing it with a morphological opening, I wrote that "the area it
    destroys rises monotonically from zero". It does not. A mitre join PUTS
    AREA BACK at a convex corner, so on the shipped backplate the destroyed
    area runs 0.218, 3.013, 2.900, MINUS 4.243, 19.251 as r grows - neither
    monotone nor non-negative. That version reported 2.400 mm for a planted
    1.95 mm neck and passed it.

    None of it was necessary. Thin metal is one of exactly two things and both
    are plain distances: two different openings (or an opening and the
    outline) passing close, or ONE opening's boundary passing close to itself
    across metal - which is the island-on-a-neck case that no
    contour-to-contour distance can see.

    Returns (width, (x, y)) or (99.0, None).
    """
    if not polys:
        return 99.0, None
    outline = max(polys, key=lambda g: g.area)
    holes = [g for g in polys if g is not outline]
    mat = outline.difference(unary_union(holes)) if holes else outline
    lo, at = 99.0, None
    # BOUNDARIES, not filled polygons. Every opening lies INSIDE the outline,
    # so Polygon.distance between them is 0 by containment, and measuring it
    # that way collapsed the whole result to 0.000 mm.
    for a in range(len(polys)):
        ea = polys[a].exterior
        for b in range(a + 1, len(polys)):
            eb = polys[b].exterior
            dd = ea.distance(eb)
            if dd < lo:
                q = nearest_points(ea, eb)[0]
                lo, at = dd, (q.x, q.y)
    for g in polys:
        ring = list(g.exterior.coords)[:-1]
        n = len(ring)
        if n < 6:
            continue
        segs = [LineString([ring[t], ring[(t + 1) % n]]) for t in range(n)]
        cum = [0.0]
        for sg in segs:
            cum.append(cum[-1] + sg.length)
        tot = cum[-1]
        for a in range(n):
            for b in range(a + 2, n):
                if a == 0 and b == n - 1:
                    continue
                if min(cum[b] - cum[a + 1],
                       tot - cum[b + 1] + cum[a]) < PINCH_SKIP:
                    continue
                dd = segs[a].distance(segs[b])
                if dd >= lo:
                    continue
                p1, p2 = nearest_points(segs[a], segs[b])
                mid = Point((p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0)
                # STRICTLY INSIDE, by a margin. Two segments joined by a
                # COLLINEAR third are `dd` apart where dd is just the length
                # of the straight run between them, and the midpoint lands
                # exactly ON the boundary - where contains() is a
                # floating-point coin flip. It reported 3.470 mm of "thinnest
                # metal" on the carcass, which is the length of an edge, not a
                # thickness. Real metal of width dd has its midpoint dd/2 from
                # the boundary; anything under a quarter of that is not a neck.
                if not mat.contains(mid):
                    continue              # that gap is air, not metal
                if mat.boundary.distance(mid) < dd / 4.0:
                    continue              # collinear run, not a thickness
                lo, at = dd, (mid.x, mid.y)
    return lo, at


def narrowest_opening(holes):
    """The narrowest CUT opening, exactly. The mirror of thinnest_metal().

    _neck() asks at what width a contour SPLITS, and that is blind in exactly
    the way it was blind for metal: a C-shaped opening pinched at its throat
    does not split when you close the throat, so the width it reports is the
    width somewhere else. It said 2.400 mm where the real narrowest is 2.220.

    Same method as the metal: every pair of non-adjacent boundary segments of
    one contour, keeping the ones whose midpoint lies INSIDE the opening -
    which is the half thinnest_metal() throws away.

    Returns (width, (x, y)) or (99.0, None).
    """
    lo, at = 99.0, None
    for g in holes:
        ring = list(g.exterior.coords)[:-1]
        n = len(ring)
        if n < 6:
            continue
        segs = [LineString([ring[t], ring[(t + 1) % n]]) for t in range(n)]
        cum = [0.0]
        for sg in segs:
            cum.append(cum[-1] + sg.length)
        tot = cum[-1]
        for a in range(n):
            for b in range(a + 2, n):
                if a == 0 and b == n - 1:
                    continue
                if min(cum[b] - cum[a + 1],
                       tot - cum[b + 1] + cum[a]) < PINCH_SKIP:
                    continue
                dd = segs[a].distance(segs[b])
                if dd >= lo:
                    continue
                p1, p2 = nearest_points(segs[a], segs[b])
                mid = Point((p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0)
                if not g.contains(mid):
                    continue              # that gap is metal, not opening
                if g.boundary.distance(mid) < dd / 4.0:
                    continue              # collinear run, not a width
                lo, at = dd, (mid.x, mid.y)
    return lo, at


def check_file(path):
    name = os.path.basename(path)
    fails, notes = [], []
    d, cut, bend, tap, other = _read(path)

    if d.dxfversion != "AC1024":
        fails.append("%s: not R2010 (%s)" % (name, d.dxfversion))
    if d.header.get("$INSUNITS", 0) != 4:
        fails.append("%s: $INSUNITS is not 4 (mm)" % name)
    for lay, kind in other:
        if kind == "UNCLOSED LWPOLYLINE":
            fails.append("%s: an UNCLOSED polyline on layer %r - CUT's whole "
                         "guarantee is closed contours, and a laser given an "
                         "open path cuts an open path" % (name, lay))
        elif kind == "LWPOLYLINE with arc bulges":
            fails.append("%s: a polyline on %r carries arc bulges - this gate "
                         "measures vertices, so every arc would be checked as "
                         "its chord and would measure as something it is not"
                         % (name, lay))
        elif kind in ("LWPOLYLINE", "CIRCLE"):
            fails.append("%s: a closed %s on layer %r - profiles belong on "
                         "CUT, and nothing reads one anywhere else, so it "
                         "would be UNCHECKED rather than approved"
                         % (name, kind, lay))
        else:
            fails.append("%s: a %s on layer %r - the gate reads LWPOLYLINE, "
                         "CIRCLE and LINE, so any other type is UNCHECKED, "
                         "not approved" % (name, kind, lay))

    polys = [c if isinstance(c, Polygon) else c["geom"] for c in cut]
    for i, p in enumerate(polys):
        if not p.is_valid:
            fails.append("%s: CUT contour %d is invalid" % (name, i))
        if not p.is_simple:
            fails.append("%s: CUT contour %d self-intersects" % (name, i))
        ring = list(p.exterior.coords)[:-1]
        for k in range(len(ring)):
            a, b, c = ring[k - 1], ring[k], ring[(k + 1) % len(ring)]
            u = (b[0] - a[0], b[1] - a[1])
            v = (c[0] - b[0], c[1] - b[1])
            lu = math.hypot(*u)
            lv = math.hypot(*v)
            if lu < 1e-9 or lv < 1e-9:
                continue
            if (u[0] * v[0] + u[1] * v[1]) / (lu * lv) < -0.999:
                fails.append("%s: CUT contour %d retraces itself at "
                             "(%.3f, %.3f)" % (name, i, b[0], b[1]))
                break

    # THE MODEL DECLARES ITS MITRES; the file is checked against that. Every
    # declared gap must itself clear CORNER_GAP, so declaring cannot hide a
    # pinch that has genuinely closed up.
    declared = []
    if name == "carcass.dxf":
        import cover_ribbon as _RB
        declared = _RB.declared_gaps()
        for g in declared:
            if g["gap"] < CORNER_GAP - 1e-6:
                fails.append("%s: a DECLARED gap has closed to %.3f mm (%s) - "
                             "under the %.2f mm two flanges may meet at"
                             % (name, g["gap"], g["why"], CORNER_GAP))
    _af, _aw, _as = _acute_and_pinch(name, polys, declared)
    fails += _af
    if _aw[1]:
        notes.append("%s: closest a contour comes to itself %.3f mm"
                     % (name, _aw[0]))
    if _as[1]:
        notes.append("%s: sharpest corner %.2f deg at (%.1f, %.1f), shortest "
                     "leg there %.2f mm" % (name, _as[0], _as[1][0],
                                            _as[1][1], _as[2]))

    # a hole diameter on CUT must clear the laser minimum
    for c in cut:
        if isinstance(c, dict) and c["d"] < MFG.MIN_HOLE_DIA:
            fails.append("%s: CUT circle dia %.3f at (%.1f, %.1f), under %.2f"
                         % (name, c["d"], c["at"][0], c["at"][1],
                            MFG.MIN_HOLE_DIA))
    for t in tap:
        if t["d"] >= MFG.MIN_HOLE_DIA:
            notes.append("%s: TAP circle dia %.3f is at or over the laser "
                         "minimum - is it meant to be cut?" % (name, t["d"]))
    # A TAPPED HOLE IS STILL A HOLE. It got a diameter note and nothing else:
    # no web to its neighbours, no distance to an edge, no test that it lands
    # on metal at all. Two tapped holes could overlap, or one could sit in
    # fresh air, and the gate had no opinion. Nothing in THIS order has a
    # tapped feature - which is exactly why it stayed invisible.
    for i, t in enumerate(tap):
        c = Point(t["at"])
        if polys:
            outline = max(polys, key=lambda g: g.area)
            if not outline.contains(c):
                fails.append("%s: a TAP hole at (%.1f, %.1f) is outside the "
                             "part" % (name, t["at"][0], t["at"][1]))
            elif outline.exterior.distance(c) < t["d"] / 2 + MFG.MIN_FEATURE:
                fails.append("%s: a TAP hole at (%.1f, %.1f) leaves %.3f mm to "
                             "the edge, under %.2f"
                             % (name, t["at"][0], t["at"][1],
                                outline.exterior.distance(c) - t["d"] / 2,
                                MFG.MIN_FEATURE))
            for g in polys:
                if g is outline:
                    continue
                if g.distance(c) < t["d"] / 2 + MFG.MIN_FEATURE:
                    fails.append("%s: a TAP hole at (%.1f, %.1f) leaves %.3f "
                                 "mm to a cut opening, under %.2f"
                                 % (name, t["at"][0], t["at"][1],
                                    g.distance(c) - t["d"] / 2,
                                    MFG.MIN_FEATURE))
                    break
        for j, u in enumerate(tap):
            if j <= i:
                continue
            d = math.hypot(t["at"][0] - u["at"][0], t["at"][1] - u["at"][1])
            if d < (t["d"] + u["d"]) / 2 + MFG.MIN_FEATURE:
                fails.append("%s: two TAP holes %.3f mm apart at (%.1f, %.1f) "
                             "- under %.2f of metal between them"
                             % (name, d - (t["d"] + u["d"]) / 2,
                                t["at"][0], t["at"][1], MFG.MIN_FEATURE))

    # THE MATERIAL, not the contours. The biggest contour is the outline and
    # every other one is a hole INSIDE it - testing raw contour intersection
    # calls all 130 of those a crossing. What actually has to be true is that
    # the remaining METAL is valid and never thinner than the minimum web, and
    # that no interior contour crosses the outline rather than sitting in it.
    if polys:
        outline = max(polys, key=lambda g: g.area)
        holes = [g for g in polys if g is not outline]
        for i, g in enumerate(holes):
            if not outline.contains(g):
                fails.append("%s: an interior CUT contour is not inside the "
                             "outline (crosses it, or lies outside)" % name)
                break
        tree = STRtree(holes) if holes else None
        worst_web, worst_pair = 1e9, None
        for i, g in enumerate(holes):
            if tree is None:
                break
            # SEARCH WIDER THAN THE THRESHOLD. Querying at MIN_FEATURE finds
            # every pair that FAILS - so the verdict was right - but it can
            # never see a pair further apart than that, and the number printed
            # as "tightest metal" was therefore whatever the outline happened
            # to contribute. A reported figure that cannot exceed the pass
            # mark tells the reader nothing about how much margin there is.
            for j in tree.query(g.buffer(WEB_REPORT)):
                if int(j) <= i:
                    continue
                q = holes[int(j)]
                if g.intersects(q):
                    fails.append("%s: two interior CUT contours overlap at "
                                 "(%.1f, %.1f)" % (name, g.centroid.x,
                                                   g.centroid.y))
                    continue
                dd = g.distance(q)
                if dd < worst_web:
                    worst_web, worst_pair = dd, (g.centroid.x, g.centroid.y)
            dd = outline.exterior.distance(g)
            if dd < worst_web:
                worst_web, worst_pair = dd, (g.centroid.x, g.centroid.y)
        if worst_pair and worst_web < MFG.MIN_FEATURE:
            fails.append("%s: %.3f mm of metal near (%.1f, %.1f), under %.2f"
                         % (name, worst_web, worst_pair[0], worst_pair[1],
                            MFG.MIN_FEATURE))
        # THE METAL, not just the gaps between openings. An island of plate
        # trapped inside one opening and held by a thin neck is invisible to
        # every distance test here, because the failure is inside a single
        # contour. Erode the material and see if anything falls off: that is
        # what found 0.986 mm inside the 'a' and 1.337 inside the '3'.
        mat = outline
        if holes:
            mat = outline.difference(unary_union(holes))
        lo, at = thinnest_metal(polys)
        if lo < MFG.MIN_FEATURE:
            fails.append("%s: metal necks to %.3f mm near (%.1f, %.1f), "
                         "under %.2f"
                         % (name, lo, at[0], at[1], MFG.MIN_FEATURE))
        notes.append("%s: thinnest metal anywhere %.3f mm%s"
                     % (name, lo,
                        " at (%.1f, %.1f)" % at if at else ""))

        worst_neck, neck_at = narrowest_opening(holes)
        worst_neck = min(worst_neck, min([_neck(g) for g in holes],
                                         default=99.0))
        if worst_neck < MFG.MIN_FEATURE:
            fails.append("%s: a CUT opening pinches to %.3f mm%s, under %.2f"
                         % (name, worst_neck,
                            " near (%.1f, %.1f)" % neck_at if neck_at else "",
                            MFG.MIN_FEATURE))
        # NOT "tightest metal" - that quantity is reported ONCE, above, by an
        # exhaustive measure. This neighbour query only ever looked within its
        # own threshold and disagreed with the exhaustive figure by 0.06 mm.
        notes.append("%s: outline + %d openings, nearest-pair web %.3f, "
                     "tightest opening %.3f"
                     % (name, len(holes),
                        worst_web if worst_pair else 99.0, worst_neck))

    # BEND must never be on the laser's path, and features must clear it
    segs = [b for b in bend if isinstance(b, LineString)]
    if segs and polys:
        boundary = unary_union([p.exterior for p in polys])
        for s in segs:
            ov = s.intersection(boundary.buffer(1e-6)).length
            if ov > 1e-3:
                fails.append("%s: a BEND line runs %.3f mm along a CUT path"
                             % (name, ov))
                break
        # TAPPED HOLES TOO, AND NO AREA EXEMPTION. This walked `cut` only, so
        # the tapped holes - the features that care most about a nearby bend,
        # because tapping into deformed metal is what fails - were never
        # tested at all. And it exempted anything over 40 mm2, which was meant
        # to skip the outline and skipped every large opening with it.
        # Identify the outline by being the largest, and test everything else.
        outer = max(polys, key=lambda q: q.area) if polys else None
        feats = [(g, "opening") for g in polys if g is not outer]
        feats += [(t["geom"], "tapped hole") for t in tap]
        n_tested = 0
        for g, what in feats:
            for s in segs:
                n_tested += 1
                if g.distance(s) < BEND_KEEPOUT:
                    fails.append("%s: a %s sits %.2f mm from a bend line, "
                                 "under the %.2f keep-out"
                                 % (name, what, g.distance(s), BEND_KEEPOUT))
                    break
        notes.append("%s: bend keep-out tested %d feature/bend pairs%s"
                     % (name, n_tested,
                        "  - NOTHING TO TEST: this part has bends but no "
                        "holes, so this check is silent here, not satisfied"
                        if not n_tested else ""))

    # minimum flat part
    if polys:
        b = unary_union(polys).bounds
        w, h = b[2] - b[0], b[3] - b[1]
        if min(w, h) < MIN_PART[0] or max(w, h) < MIN_PART[1]:
            fails.append("%s: %.2f x %.2f is under the %.2f x %.2f minimum "
                         "flat part" % (name, w, h, MIN_PART[0], MIN_PART[1]))
    return fails, notes


def main():
    # THE FOLDER THAT GETS SENT IS CHECKED TOO. check_file ran on the
    # annotated drawings only, and upload/ was compared to them by a
    # GEOMETRY SIGNATURE - which hashes contours and says nothing about
    # layers, units, DXF version, minimum feature, part size, fold ends,
    # or anything else the file check exists for. The copies are made by
    # deleting text from the saved drawing so they SHOULD be identical;
    # "should" is what a gate is for.
    drawings = sorted(glob.glob(os.path.join(OUT, "*.dxf")))
    sent = sorted(glob.glob(os.path.join(OUT, "upload", "*.dxf")))
    files = drawings + sent
    print("RELEASE GATE  -  %d drawings + %d as uploaded, in %s\n"
          % (len(drawings), len(sent), os.path.normpath(OUT)))
    allf, alln = [], []
    for f in files:
        fails, notes = check_file(f)
        allf += fails
        alln += notes
    for n in alln:
        print("   %s" % n)

    # the carcass must be exactly one contour
    carc = os.path.join(OUT, "carcass.dxf")
    if os.path.exists(carc):
        _d, cut, _b, _t, _o = _read(carc)
        polys = [c for c in cut if isinstance(c, Polygon)]
        n = len(polys)
        # ONE OUTLINE, plus the roof's vent openings (2026-09-02), each of
        # which must lie INSIDE that outline and match the model's count.
        import cover_ribbon as _RBc
        _want_holes = len(_RBc.carcass_blank(_RBc.route45())[0].interiors)
        outer = max(polys, key=lambda g: g.area) if polys else None
        inner = [g for g in polys if g is not outer]
        stray = [g for g in inner if not outer.contains(g)] if outer else inner
        print("\n   carcass.dxf: 1 outline + %d roof opening%s (model: %d)"
              % (len(inner), "" if len(inner) == 1 else "s", _want_holes))
        if not polys or stray or len(inner) != _want_holes:
            allf.append("carcass.dxf is %d contours: %d outside the outline, "
                        "%d openings against the model's %d - the flaps have "
                        "come away or the roof is wrong"
                        % (n, len(stray), len(inner), _want_holes))

    # A CHECK THAT DID NOT RUN IS NOT A CHECK THAT PASSED. Both of these used
    # to print "not checked (No module named 'trimesh')" and let the gate exit
    # 0 - so uninstalling one library silently turned off the two heaviest
    # checks in the file and the verdict still read ALL CHECKS PASS.
    try:
        se = check_exported_solids()
        print("\n   exported solids: section %s the design"
              % ("matches" if not se else "DISAGREES with"))
        allf += se
    except Exception as e:
        print("\n   exported solids: DID NOT RUN (%s)" % str(e)[:60])
        allf.append("exported-solid check did not run: %s" % str(e)[:80])

    try:
        fe, fe_n = check_fold()
        print("   fold check: %d leg/side stations, every panel folds to its "
              "design dimension" % fe_n if not fe
              else "   fold check: %d panel(s) DISAGREE across %d stations"
              % (len(fe), fe_n))
        allf += fe
    except Exception as e:
        print("   fold check: DID NOT RUN (%s)" % str(e)[:60])
        allf.append("fold check did not run: %s" % str(e)[:80])

    allf += check_fold_sequence()
    fd = check_fold_direction()
    print("   fold direction: skins carry UP and DOWN on separate layers "
          "with a schedule" if not fd else "   fold direction: %d problem(s)"
          % len(fd))
    allf += fd

    print("\n   geometry signatures (metadata-independent):")
    for k, v in geometry_signature().items():
        print("     %-32s %s" % (k, v))

    cf = check_carcass_folds()
    print("\n   carcass folds: walls on BEND_DOWN_90, feet on BEND_UP_90, "
          "each on a flap's own fold line" if not cf
          else "\n   carcass folds: %d problem(s)" % len(cf))
    allf += cf

    sw = check_slot_width()
    print("\n   tab slots: as cut, they swallow the declared "
          "tolerance stack" if not sw else
          "\n   tab slots: %d problem(s)" % len(sw))
    allf += sw


    pf = check_plate_features()
    print("\n   plate features: outline, die window and card bores match "
          "the model on both plates" if not pf
          else "\n   plate features: %d problem(s)" % len(pf))
    allf += pf

    vf = check_vent_fields()
    print("\n   vent fields: both plates carry their own art, "
          "identical everywhere else" if not vf
          else "\n   vent fields: %d problem(s)" % len(vf))
    allf += vf

    fe2 = check_fold_ends()
    print("\n   fold ends: every bend terminates at an edge or a relief"
          if not fe2 else "\n   fold ends: %d die in solid metal" % len(fe2))
    allf += fe2

    tl = check_tabs_land()
    print("\n   tabs: every skin, folded to its own marks, lands its tabs in "
          "the plate's slots" if not tl
          else "\n   tabs: %d skin(s) do NOT land" % len(tl))
    allf += tl

    uc = check_upload_copies()
    print("\n   upload copies: geometry identical to the drawings, no text"
          if not uc else "\n   upload copies: %d problem(s)" % len(uc))
    allf += uc

    pd = check_part_dims()
    print("\n   part sizes: every blank matches the model that generated it"
          if not pd else "\n   part sizes: %d DISAGREE" % len(pd))
    allf += pd

    print("\n   SELF-TEST - plant each defect, require the check to reject it:")
    if not selftest():
        allf.append("a release-gate self-test did not fire - the check is dead")

    gate = os.path.join(OUT, "DO_NOT_CUT.txt")
    print("\n%s" % ("=" * 62))
    if allf:
        print("  NOT SAFE TO UPLOAD  -  %d failure%s\n"
              % (len(allf), "" if len(allf) == 1 else "s"))
        for f in allf:
            print("    FAIL  %s" % f)
        return 1
    print("  ALL FILE-LEVEL CHECKS PASS")
    if os.path.exists(gate):
        print("  (%s is still present - remove it deliberately, not by script)"
              % os.path.basename(gate))
    return 0


def check_exported_solids():
    """Slice the exported assembly and compare the section to the design.

    An independent path: it reads the MESH, not the polygons that made it. That
    is how a 2 mm-per-side error in the render export was found - the skins sat
    proud because upright()'s two callers pass segments on OPPOSITE faces, and
    nothing in the code reads as wrong.
    """
    import math
    import trimesh
    import cover_ribbon as RB
    import export_solids as _ES
    class ES_DESIGN:
        name = ('backplate_%s.dxf'
                % _ES.build.__defaults__[0].split('/')[0]
                .strip().lower().replace(' ', '_'))
    p = os.path.join(OUT, "..", "render", "assembly_tall.glb")
    if not os.path.exists(p):
        return ["render/assembly_tall.glb missing - not exported"]
    s = trimesh.load(os.path.abspath(p))
    path = RB.route45()
    (ax, ay), (bx, by) = path[2], path[3]
    L = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / L, (by - ay) / L
    ox, oy = ax + ux * L * 0.5, ay + uy * L * 0.5
    px, py = -uy, ux
    c = ox * px + oy * py
    # THE FOOT IS OUTWARD NOW, so on the leg this plane cuts (leg 2) the
    # carcass reaches CARCASS_FOOT past the wall on the foot's side. SHOW is
    # the negative side of this plane's transverse axis, as the skin rows say.
    _fs = RB.foot_side_for(2)
    want = {"carcass": (-(RB.CARCASS_HALF_DS
                          + (RB.foot_len(RB.SHOW) if _fs == RB.SHOW else 0.0)),
                        RB.CARCASS_HALF_DS
                        + (RB.foot_len(RB.FAR) if _fs == RB.FAR else 0.0)),
            "skin_show": (-RB.CARCASS_RIB_OUT, -RB.CARCASS_RIB_IN),
            "skin_far": (RB.CARCASS_RIB_IN, RB.CARCASS_RIB_OUT)}
    out = []

    # THE FEET, ON EVERY LEG. Comparing transverse EXTENTS cannot see them:
    # the feet live inboard at +/-4.0 and move neither extreme, so this check
    # passed happily on a solid that carried a foot on BOTH sides of every leg
    # - ten where the part has five - and showed an 8.0 mm channel aperture
    # instead of 16.0. That 16.0 is the number the 8 mm foot size was chosen
    # against, so the render was contradicting the design rationale by a
    # factor of two while a verification path called it correct.
    for i in range(len(path) - 1):
        (aax, aay), (bbx, bby) = path[i], path[i + 1]
        LL = math.hypot(bbx - aax, bby - aay)
        uux, uuy = (bbx - aax) / LL, (bby - aay) / LL
        oox, ooy = aax + uux * LL * 0.5, aay + uuy * LL * 0.5
        ppx, ppy = -uuy, uux
        cc = oox * ppx + ooy * ppy
        sec = s.geometry["carcass"].section(plane_origin=[oox, ooy, 0],
                                            plane_normal=[uux, uuy, 0.0])
        if sec is None:
            continue
        low = [vx * ppx + vy * ppy - cc for vx, vy, vz in sec.vertices
               if vz < RB.Z0 + RB.T + 0.01]
        if not low:
            continue
        tip = RB.CARCASS_HALF_DS + RB.foot_len(RB.foot_side_for(i))   # outward foot, this leg's side
        sides = sum(1 for sgn in (1, -1)
                    if any(abs(t - sgn * tip) < 0.05 for t in low))
        if sides > 1:
            out.append("exported carcass has a foot on BOTH sides of leg %d - "
                       "the part has one per station, and two halves the "
                       "channel aperture" % i)

    # THE PLATE'S OPENINGS. Extents at one station cannot see a hole, so the
    # exported plate had the DIE WINDOW and all nine tab slots filled in -
    # 3094 mm2 of solid metal where the cut file has openings, and the die
    # window is the largest opening on the part. Compare the exported top face
    # with the net area of the file that gets cut.
    try:
        from shapely.ops import unary_union as _uu
        tri = [Polygon([(v[0], v[1]) for v in t])
               for t in s.geometry["backplate"].triangles
               if all(abs(v[2] - RB.PLATE_T) < 1e-6 for v in t)]
        got = _uu(tri).area
        # THE PLATE THAT WAS EXPORTED, whichever it is. export_solids builds
        # from the Interference design today; hardcoding that name here means
        # the comparison silently stops being about the exported solid the
        # moment anyone exports the other one.
        _bpn = getattr(ES_DESIGN, "name", "backplate_interference.dxf")
        d2, cut2, _b2, tap2, _o2 = _read(os.path.join(OUT, _bpn))
        ps = [c if isinstance(c, Polygon) else c["geom"] for c in cut2]
        o2 = max(ps, key=lambda g: g.area)
        net = o2.difference(_uu([g for g in ps if g is not o2]))
        if abs(got - net.area) > 30.0:
            out.append("exported backplate's face is %.0f mm2 against the cut "
                       "file's %.0f - openings are missing from the solid"
                       % (got, net.area))
    except Exception as e:
        out.append("could not compare the exported plate to its cut file: %s"
                   % str(e)[:60])

    for nm, (e0, e1) in want.items():
        sec = s.geometry[nm].section(plane_origin=[ox, oy, 0],
                                     plane_normal=[ux, uy, 0.0])
        t = [vx * px + vy * py - c for vx, vy, _vz in sec.vertices]
        if abs(min(t) - e0) > 0.01 or abs(max(t) - e1) > 0.01:
            out.append("exported %s sections %+.3f..%+.3f, design says "
                       "%+.3f..%+.3f" % (nm, min(t), max(t), e0, e1))
    return out


def check_fold():
    """Read the FLAT from the DXF, fold it, and see if it lands on the design.

    The strongest check here, because it runs the development BACKWARDS. It
    found the free-edge downstands 1.475 mm short: down_flat subtracts a whole
    bend deduction because it assumes a fold at each end, and where the foot is
    staggered away the downstand ends at a free edge with only one.
    """
    import math
    import ezdxf as _e
    import cover_ribbon as RB
    from shapely.geometry import LineString as _L, Polygon as _P
    d = _e.readfile(os.path.join(OUT, "carcass.dxf"))
    msp = d.modelspace()
    # the OUTLINE is the first polyline on CUT; the roof openings and the
    # feet's screw holes (circles) come after it and are not the blank
    blank = [_P([(p[0], p[1]) for p in x.get_points()])
             for x in msp if x.dxf.layer == "CUT"
             and x.dxftype() == "LWPOLYLINE"][0]
    # EVERY BEND LAYER. This read `== "BEND"` and the carcass has carried its
    # folds on BEND_DOWN since the layer was split by direction, so `bends`
    # was empty, every leg hit `continue`, and the check reported "every panel
    # folds to its design dimension" without measuring a single panel. It was
    # dead for three rounds while being counted as one of five independent
    # verification paths.
    bends = [_L([(x.dxf.start.x, x.dxf.start.y), (x.dxf.end.x, x.dxf.end.y)])
             for x in msp if x.dxf.layer.startswith("BEND")]
    if not bends:
        return (["carcass.dxf: no BEND lines found - the fold check cannot "
                 "run"], 0)
    BD = RB.BEND_DEDUCT
    path = RB.route45()
    out = []
    # COUNT WHAT WAS ACTUALLY MEASURED. A check whose every branch is a
    # `continue` returns the same empty list as a check that measured
    # everything and found nothing, and for three rounds this one returned the
    # first while being read as the second.
    stations = 0
    done = set()
    # SAMPLE MORE THAN THE MIDPOINT. A wall on the inside of a turn has a
    # SHORTER fold line than its route leg, so the route midpoint can fall
    # past the end of it: leg 4's far wall runs 5.73 mm of a 10.51 mm fold
    # line and the midpoint sample missed it, leaving that station unmeasured
    # while the geometry was fine. Try several stations and take the first
    # that lands on the panel.
    for i, frac in [(i, f) for i in range(len(path) - 1)
                    for f in (0.5, 0.3, 0.7, 0.15, 0.85)]:
        if (i, 1) in done and (i, -1) in done:
            continue
        (ax, ay), (bx, by) = path[i], path[i + 1]
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        ox, oy = ax + ux * L * frac, ay + uy * L * frac
        # THE LEFT NORMAL. Worth naming, because the messages below used to
        # call the sgn>0 side "show" and SHOW is defined as the RIGHT of
        # travel, so every side label was the wrong one.
        px, py = -uy, ux            # left of travel, i.e. the FAR side
        cl = _L([(ox - px * 80, oy - py * 80), (ox + px * 80, oy + py * 80)])
        sec = cl.intersection(blank)
        # A SECTION IN TWO PIECES IS STILL A SECTION. Leg 4's far downstand is
        # short enough that the cut line leaves the blank and re-enters it, so
        # `!= "LineString"` skipped BOTH of that leg's stations silently - two
        # of the ten, on the leg nearest the cable exit.
        if sec.is_empty:
            continue
        if sec.geom_type != "LineString":
            parts = [q for q in getattr(sec, "geoms", []) if q.length > 1e-6]
            if not parts:
                continue
            sec = min(parts, key=lambda q: q.distance(Point(ox, oy)))
        c = ox * px + oy * py
        xs = sorted(v[0] * px + v[1] * py - c for v in sec.coords)
        folds = sorted({round(s.intersection(cl).x * px
                              + s.intersection(cl).y * py - c, 3)
                        for s in bends
                        if s.intersection(cl).geom_type == "Point"})
        for sgn in (1, -1):
            if (i, sgn) in done:
                continue
            f = [abs(x) for x in folds if x * sgn > 0]
            if not f:
                continue
            done.add((i, sgn))
            stations += 1
            edge = abs(xs[-1] if sgn > 0 else xs[0])
            top = min(f) + BD / 2
            if abs(top - RB.CARCASS_HALF_DS) > 0.01:
                out.append("leg %d: top face folds to %.3f, design %.3f"
                           % (i, top, RB.CARCASS_HALF_DS))
            if len(f) == 2:
                down = (max(f) - min(f)) + BD
                foot = (edge - max(f)) + BD / 2
                # OUTWARD: the foot's formed length IS CARCASS_FOOT, the
                # vendor's own definition, measured from the wall's outer face.
                _want = RB.foot_len(RB.foot_side_for(i))
                if abs(foot - _want) > 0.01:
                    out.append("leg %d: foot folds to %.3f, design %.3f"
                               % (i, foot, _want))
            else:
                down = (edge - min(f)) + BD / 2
            if abs(down - (RB.CLEAR_D + RB.T)) > 0.01:
                out.append("leg %d side %s: downstand folds to %.3f, "
                           "design %.3f"
                           % (i, "far" if sgn > 0 else "show", down,
                              RB.CLEAR_D + RB.T))
    # THE MODEL SAYS WHICH STATIONS HAVE A WALL. Since WALL_SEG_MIN dropped
    # leg 4's 4.0 mm far stub there are 9, not 2 x legs; a station measured
    # that the model says is empty is as wrong as one missed.
    # MIRRORED SIGN. This check's sgn is +1 LEFT of travel (far); the blank's
    # flap sgn is its outward normal (uy, -ux) * sgn, +1 RIGHT of travel. Every
    # leg had both walls until leg 4 lost its far one, so the mirror was never
    # visible before.
    expect = {(i, -s) for i, s in RB.wall_stations(path)}
    if done != expect:
        out.append("carcass.dxf: the fold check reached stations %s, the "
                   "model has walls at %s - it is not measuring the part"
                   % (sorted(done), sorted(expect)))
    return out, stations


def check_fold_direction():
    """A skin's folds do NOT all go the same way, and the file must say so.

    route45 turns right, right, left, left, so a skin bonded to one side folds
    one way at the first two corners and the other at the last two. Four bare
    lines on one BEND layer and a note reading 45/45/45/45 gives a brake
    operator nothing to work from, and folding them all the same way scraps the
    one part that IS the finished visible surface.
    """
    out = []
    for f in sorted(glob.glob(os.path.join(OUT, "skin_*.dxf"))):
        d = ezdxf.readfile(f)
        lays = [e.dxf.layer for e in d.modelspace() if e.dxftype() == "LINE"]
        name = os.path.basename(f)
        if "BEND" in lays:
            out.append("%s: folds on an undirected BEND layer" % name)
        ups = sum(1 for x in lays if x.startswith("BEND_UP"))
        dns = sum(1 for x in lays if x.startswith("BEND_DOWN"))
        if not (ups and dns):
            out.append("%s: every fold is the same direction (%s) - the route "
                       "turns both ways, so this is wrong"
                       % (name, sorted(set(lays))))
        txt = " ".join(e.dxf.text for e in d.modelspace()
                       if e.dxftype() == "TEXT")
        if "FOLD SCHEDULE" not in txt:
            out.append("%s: no fold schedule in the notes" % name)
    return out


def geometry_signature(where=None):
    """A hash of the GEOMETRY only, ignoring DXF metadata.

    Two exports are never byte-identical: ezdxf stamps a fresh handle seed and
    timestamp on every write. Checked it again after the order dropped from
    eight parts to seven: rebuilt back to back, all fourteen DXFs (seven
    drawings and seven upload copies) differ in $TDCREATE, $TDUPDATE,
    $FINGERPRINTGUID, $VERSIONGUID, the ezdxf version comment and the order
    two CLASS records are written in - and every parsed entity is identical.
    So the build is GEOMETRY-reproducible, not byte-reproducible; anyone
    diffing two exports would see every file change and reasonably conclude
    the part had moved. This is the number to compare instead.

    Pinning those header fields before saveas() does not work - ezdxf rewrites
    TDUPDATE and VERSIONGUID during the save - so there is no version of this
    that ends in matching digests, and a check that promised one would be
    promising something the writer cannot deliver.
    """
    import hashlib
    sigs = {}
    for f in sorted(glob.glob(os.path.join(where or OUT, "*.dxf"))):
        d = ezdxf.readfile(f)
        out = []
        for e in d.modelspace():
            t = e.dxftype()
            if t == "LWPOLYLINE":
                out.append((e.dxf.layer, "P",
                            tuple(round(v, 6) for pt in e.get_points()
                                  for v in pt[:2])))
            elif t == "CIRCLE":
                out.append((e.dxf.layer, "C", round(e.dxf.center.x, 6),
                            round(e.dxf.center.y, 6), round(e.dxf.radius, 6)))
            elif t == "LINE":
                out.append((e.dxf.layer, "L", round(e.dxf.start.x, 6),
                            round(e.dxf.start.y, 6), round(e.dxf.end.x, 6),
                            round(e.dxf.end.y, 6)))
            # NOT the notes. A GEOMETRY signature that hashes the annotation
            # is not a geometry signature: it made all eight upload copies,
            # which are the same parts with the text stripped, look like
            # different geometry.
            elif t == "TEXT" and e.dxf.layer != "NOTES":
                out.append((e.dxf.layer, "T", e.dxf.text))
        sigs[os.path.basename(f)] = hashlib.md5(
            repr(sorted(map(repr, out))).encode()).hexdigest()[:12]
    return sigs


def check_fold_sequence():
    """Both skins must carry the SAME marks, and they must agree with the model.

    THIS CHECK IS CIRCULAR AND SAYS SO. It compares the file against
    skin_fold_layer(), which is also what wrote the file, so it can catch the
    two skins disagreeing with each other or with the model - a real failure,
    and the one it was written for - but it cannot catch the shared rule being
    wrong. When the sense itself was inverted this returned clean, and so did
    check_fold_direction: I proved it by flipping every mark in all four files
    and running both, which reported zero problems while the parts folded into
    mirror images.

    check_tabs_land() is the non-circular one. It folds the blank by whatever
    the file says and asks whether the tabs reach the slots in the plate. On
    that same planted case it reports 77.69 mm.
    """
    import cover_ribbon as RB
    ang = RB.deflections(RB.route45())
    want = [RB.fold_layer(t, a) for t, a in zip(RB.turns(RB.route45()), ang)]
    out = []
    for f in sorted(glob.glob(os.path.join(OUT, "skin_*.dxf"))):
        d = ezdxf.readfile(f)
        ls = sorted((e.dxf.start.x, e.dxf.layer) for e in d.modelspace()
                    if e.dxftype() == "LINE")
        got = [lay for _x, lay in ls]
        if got != want:
            out.append("%s: folds read %s, expected %s"
                       % (os.path.basename(f), got, want))
        # AND WHERE THEY ARE. The x was read only to sort the list and then
        # thrown away, so this compared an ordered list of LAYER NAMES and
        # nothing else. check_tabs_land was supposed to be the answer to that,
        # but its only assertion is that tabs land in slots - so a fold with
        # no tab downstream of it constrains nothing measured, and three of
        # the eight marks in this order are in that position. One of them
        # moved 10 mm with the gate printing ALL FILE-LEVEL CHECKS PASS.
        sgn = RB.SHOW if "show" in os.path.basename(f) else RB.FAR
        wf = RB.carcass_ribbon(sgn, RB.route45())["folds"]
        gx = [x for x, _lay in ls]
        if len(gx) == len(wf):
            for a, b in zip(gx, wf):
                if abs(a - b) > 0.02:
                    out.append("%s: a fold line is at %.3f, the model says "
                               "%.3f" % (os.path.basename(f), a, b))
                    break
    return out



def selftest():
    """Plant each defect and require the check to reject it.

    A check that is written, wired in, and never fires is worth less than no
    check at all, because it reads as coverage. This project has already
    shipped one of those. Both of these are shapes the OTHER checks in this
    file provably cannot see, so if these two ever stop firing nothing else
    will notice.
    """
    from shapely.geometry import Polygon
    ok = True

    # 1. a tooth reaching back toward its own root. Closing the throat does
    #    not split the piece, so _neck() and the erosion test both pass it.
    w = 0.9
    tooth = Polygon([(0, 0), (40, 0), (40, 20), (0, 20), (0, 12),
                     (30, 12), (30, 12 - w), (0, 12 - w)])
    f, _, _ = _acute_and_pinch("planted.dxf", [tooth])
    hit = any("pinches against ITSELF" in x for x in f)
    print("     notch and tooth, %.1f mm throat .......... %s"
          % (w, "REJECTED, correct" if hit else "MISSED - the check is dead"))
    ok &= hit

    # 2. a wedge tapering to a point. Not a narrow opening and not thin metal:
    #    eroding a wedge from every edge at once only shortens it.
    knife = Polygon([(0, 0), (60, 2), (60, -2)])   # 3.8 deg at the tip
    f, _, _ = _acute_and_pinch("planted.dxf", [knife])
    hit = any("knife edge" in x for x in f)
    print("     knife edge, 3.8 deg at the tip ......... %s"
          % ("REJECTED, correct" if hit else "MISSED - the check is dead"))
    ok &= hit

    # 3. thin metal, both shapes it comes in. The morphological version of
    #    this measure passed a planted 1.95 mm neck as 2.400, so these plant
    #    both classes at 1.95: a web between two openings, and an island held
    #    inside ONE opening, which no contour-to-contour distance can see.
    from shapely.geometry import box as _box
    for lbl, ps in (
            ("web between two openings",
             [_box(0, 0, 60, 60), _box(10, 10, 30, 50), _box(31.95, 10, 50, 50)]),
            ("island inside one opening",
             [_box(0, 0, 60, 60),
              _box(10, 10, 50, 50).difference(_box(20, 20, 40, 40))
              .difference(_box(29, 40, 30.95, 50))])):
        _lo, _at = thinnest_metal(ps)
        hit = _lo < MFG.MIN_FEATURE
        print("     1.95 mm %-26s ......... %s"
              % (lbl, "REJECTED, correct" if hit else "MISSED"))
        ok &= hit

    # 4. a narrow OPENING, the mirror of the thin-metal case. _neck() is
    #    blind to a C-shaped opening pinched at its throat for the same reason
    #    it was blind to metal - closing the throat splits nothing.
    #    An L-shaped opening with one narrow DEAD-END arm: closing that arm
    #    shortens the opening, it does not disconnect it, so the split test
    #    never sees the 1.95 and reports whatever the wide part measures.
    _op = unary_union([_box(10, 10, 40, 20), _box(10, 20, 11.95, 40)])
    _ps = [_op] if _op.geom_type == "Polygon" else list(_op.geoms)
    _lo, _at = narrowest_opening(_ps)
    hit = _lo < MFG.MIN_FEATURE
    print("     1.95 mm opening pinched at its throat ... %s"
          % ("REJECTED, correct" if hit else "MISSED - the check is dead"))
    ok &= hit

    # 5. bend relief, at and under the rule. The vendor asks RELIEF_W wide by
    #    RELIEF_DEPTH deep; two earlier versions of this probe accepted a
    #    0.40 mm nick and then a 0.867 mm notch.
    Y = 40.0
    for dep, wid, want in ((FOLD_END_D, FOLD_END_W, False),
                           (3.00, FOLD_END_W, True),
                           (FOLD_END_D, 0.50, True),
                           (0.40, FOLD_END_W, True)):
        bl = _box(0, 0, 60, Y).difference(_box(30, Y - dep, 30 + wid, Y))
        got = _fold_dies_in_metal(bl, (10, Y - 1e-3), (30, Y - 1e-3), True)
        lbl = "%.2f deep x %.2f wide" % (dep, wid)
        print("     relief %-22s ......... %s"
              % (lbl, ("REJECTED, correct" if got else "MISSED") if want
                 else ("accepted, correct" if not got
                       else "FALSE POSITIVE on the rule itself")))
        ok &= (got == want)

    # 6. a hole inside a bend keep-out. Nothing in THIS order exercises the
    #    real check - the parts with bends have no holes - so without a
    #    planted case there would be no evidence it works at all.
    from shapely.geometry import Point as _Pt
    import ezdxf as _ez
    import tempfile as _tf
    _p = os.path.join(_tf.gettempdir(), "planted_bend.dxf")
    _d = _ez.new("R2010", setup=False)
    _d.header["$INSUNITS"] = 4
    for _lay in ("CUT", "BEND_UP", "BEND_DOWN", "TAP", "NOTES"):
        if _lay not in _d.layers:
            _d.layers.add(_lay)
    _m = _d.modelspace()
    _m.add_lwpolyline([(0, 0), (60, 0), (60, 40), (0, 40)], close=True,
                      dxfattribs={"layer": "CUT"})
    _m.add_line((30, 0), (30, 40), dxfattribs={"layer": "BEND_UP"})
    _m.add_line((45, 0), (45, 40), dxfattribs={"layer": "BEND_DOWN"})
    _m.add_circle((32, 20), 1.5, dxfattribs={"layer": "CUT"})
    _d.saveas(_p)
    _f, _n = check_file(_p)
    hit = any("keep-out" in x for x in _f)
    print("     a hole 0.5 mm from a bend line ......... %s"
          % ("REJECTED, correct" if hit else "MISSED - the check is dead"))
    ok &= hit

    # 7. and it must NOT fire on an honest part
    square = Polygon([(0, 0), (40, 0), (40, 40), (0, 40)])
    f, _, _ = _acute_and_pinch("planted.dxf", [square])
    print("     a plain rectangle ....................... %s"
          % ("clean, correct" if not f else "FALSE POSITIVE: %s" % f))
    ok &= not f
    return ok


def check_part_dims():
    """Every part's blank measured against the model that generated it.

    NOTHING DID THIS. The gate checked layers, contours, minimum feature,
    folds and fold directions - and never once asked whether the outline was
    the size it was supposed to be. A tall skin cut to the flush height, or
    the two variants swapped, passed the entire gate: same layers, same four
    folds, same fold sequence, valid contours throughout. The only thing wrong
    with it would be that it is the wrong part.

    Filenames carry the variant, so the filename is the claim being tested.
    """
    import cover_ribbon as _RB
    out = []
    want = {}
    for sgn, lab in ((_RB.SHOW, "show"), (_RB.FAR, "far")):
        for flush in _RB.ordered_facades():
            r = _RB.carcass_ribbon(sgn, _RB.route45(), flush)
            nm = "skin_%s_%s.dxf" % (lab, "flush" if flush else "tall")
            want[nm] = (r["flat"], r["height"] + _RB.PLATE_T)
    p = _RB.route45()
    top, flaps = _RB.carcass_blank(p)
    from shapely.ops import unary_union as _uu
    b = _uu([top] + [f["poly"] for f in flaps]).bounds
    want["carcass.dxf"] = (b[2] - b[0], b[3] - b[1])
    if _RB.CAP_IN_ORDER:
        cap = _RB.notch_cap(p)["cap"].bounds
        want["notch_cap.dxf"] = (cap[2] - cap[0], cap[3] - cap[1])
    import backplate_v3 as _B
    for nm in ("backplate_interference.dxf", "backplate_bit_plane.dxf"):
        want[nm] = (_B.L, _B.H)

    for nm, (ew, eh) in sorted(want.items()):
        path = os.path.join(OUT, nm)
        if not os.path.exists(path):
            out.append("%s: expected but missing" % nm)
            continue
        _d, cut, _b, _t, _o = _read(path)
        polys = [c if isinstance(c, Polygon) else c["geom"] for c in cut]
        if not polys:
            out.append("%s: no CUT geometry" % nm)
            continue
        bb = unary_union(polys).bounds
        gw, gh = bb[2] - bb[0], bb[3] - bb[1]
        if abs(gw - ew) > 0.02 or abs(gh - eh) > 0.02:
            out.append("%s: blank is %.2f x %.2f, the model says %.2f x %.2f"
                       % (nm, gw, gh, ew, eh))
    return out


def check_upload_copies():
    """The upload/ copies are the files that actually get sent. Check those.

    Everything else in this gate reads the annotated drawings. Those are for a
    person; what goes to the vendor is the stripped copy, and a gate that
    never opens the file being uploaded is checking the wrong artefact. Both
    must exist, carry identical geometry, and the copy must carry no text.
    """
    up = os.path.join(OUT, "upload")
    out = []
    if not os.path.isdir(up):
        return ["out/production/upload is missing - nothing to send"]
    # THE SHEET IS PART OF THE ORDER. The upload DXFs carry no text at all, so
    # material, temper, finish, quantities and which variant to order exist
    # nowhere in the geometry. A folder of anonymous outlines is not an order.
    if not os.path.exists(os.path.join(up, "ORDER_SHEET.txt")):
        out.append("upload/ORDER_SHEET.txt is missing - the DXFs carry no "
                   "material, finish or quantity")
    # THE FOLDER IS THE ORDER. Nothing enumerated it, so a superseded or
    # stray DXF left in upload/ passed every check in this file - each part
    # was verified individually and the SET was never verified at all. What
    # gets uploaded is the folder, not the parts you happened to think about.
    import cover_ribbon as _RB
    import make_production as _MP
    # THE ORDER, not a list typed here. The tall skins left the order on
    # 2026-09-01 and this set went on demanding them - the same hardcoded
    # list that once let a stale file pass, now failing on a correct folder.
    want_files = {_MP_NAME(n) for n in _MP.PLATES} | {"carcass.dxf"} | {
        "skin_%s_%s.dxf" % (lab, "flush" if fl else "tall")
        for lab in ("show", "far") for fl in _RB.ordered_facades()}
    if _RB.CAP_IN_ORDER:
        want_files.add("notch_cap.dxf")
    got_files = {f for f in os.listdir(up) if f.lower().endswith(".dxf")}
    for extra in sorted(got_files - want_files):
        out.append("%s is in upload/ and is not part of the order - remove it "
                   "or add it to the manifest" % extra)
    for missing in sorted(want_files - got_files):
        out.append("%s is missing from upload/" % missing)

    a = geometry_signature(OUT)
    b = geometry_signature(up)
    for nm in sorted(set(a) | set(b)):
        if nm not in b:
            out.append("%s: no upload copy" % nm)
        elif nm not in a:
            out.append("%s: an upload copy with no drawing behind it" % nm)
        elif a[nm] != b[nm]:
            out.append("%s: the upload copy's geometry differs from the "
                       "drawing (%s vs %s)" % (nm, a[nm], b[nm]))
    for nm in sorted(b):
        d = ezdxf.readfile(os.path.join(up, nm))
        txt = [e for e in d.modelspace() if e.dxftype() in ("TEXT", "MTEXT")]
        if txt:
            out.append("%s: the upload copy still carries %d text entities"
                       % (nm, len(txt)))
        # VERSION AND UNITS ON THE COPY TOO. Only the geometry was compared,
        # so a copy in the wrong DXF version or with $INSUNITS unset would
        # have matched perfectly and been quoted in inches.
        if d.dxfversion != "AC1024":
            out.append("%s: upload copy is not R2010 (%s)"
                       % (nm, d.dxfversion))
        if d.header.get("$INSUNITS", 0) != 4:
            out.append("%s: upload copy's $INSUNITS is not 4 (mm)" % nm)
    return out


# HOW CLOSE A FOLDED TAB MUST COME TO ITS SLOT CENTRE. 0.60 was a round
# number and it is six times the play the joint actually has: a slot is
# SLOT_L_MIN long against a 12.00 mm tab, which after coating leaves 0.10 mm
# per end. A check that certifies a fit has to be tighter than the fit.
TAB_LAND_TOL = 0.10


def _slot_widths():
    """Every tab-slot width the model draws. There is no longer just one."""
    import cover_ribbon as _RB
    ws = set()
    for sgn in (_RB.SHOW, _RB.FAR):
        for t in _RB.skin_tabs(sgn, _RB.route45()):
            ws.add(round(t["slot_w"], 4))
    return sorted(ws)


def check_tabs_land():
    """Fold each skin BY ITS OWN MARKS and see whether the tabs reach a slot.

    THE POINT IS THAT THIS CANNOT BE FOOLED BY A RESTATED RULE.
    check_fold_sequence() compares the marks in the file against the same
    expression that wrote them, so when the sense itself was inverted it
    agreed with the mistake and returned clean. Round seven found both skins
    marked to fold into mirror images of the parts needed, and this gate had
    nothing to say about it.

    So: take the bend positions and layers OUT OF THE FILE, walk the strip in
    plan turning whichever way each layer says, and land the tabs. Then read
    the slot positions out of the BACKPLATE file. If the marks are inverted
    the strip curls the wrong way and the tabs finish tens of millimetres from
    any slot. The only things borrowed from the model are where the strip
    starts and how many degrees each fold turns - neither of which is the
    thing under test.
    """
    import cover_ribbon as _RB
    out = []
    # BOTH PLATES. Only one was opened, so the other backplate's nine slots -
    # a whole alternative part the buyer may well choose - were never the ones
    # the tabs were landed in. They are generated from the same model and
    # should be identical; "should" is what a gate is for, and if the two ever
    # diverge the tabs fit one plate and not the other.
    out = []
    bps = [os.path.join(OUT, n) for n in ("backplate_interference.dxf",
                                          "backplate_bit_plane.dxf")]
    bps = [b for b in bps if os.path.exists(b)]
    if not bps:
        return ["no backplate on disk - cannot locate the slots"]
    per_plate = []
    for bp in bps:
        slots = []
        for e in ezdxf.readfile(bp).modelspace():
            if e.dxftype() != "LWPOLYLINE" or e.dxf.layer != "CUT":
                continue
            pts = [(p[0], p[1]) for p in e.get_points()]
            if len(pts) != 4:
                continue
            g = Polygon(pts)
            r = list(g.minimum_rotated_rectangle.exterior.coords)
            ed = sorted(math.hypot(r[i + 1][0] - r[i][0], r[i + 1][1] - r[i][1])
                        for i in range(4))
            # ANY WIDTH THE MODEL DRAWS, not the one global constant. The
            # two far leg-2 slots are 5.678 mm - three bends from a bonded
            # foot, not one - so matching on SLOT_W alone found 7 of 9 and
            # then reported the file as short of slots.
            if any(abs(ed[0] - w) < 0.05 for w in _slot_widths()):
                # KEEP THE SHAPE. Reducing a slot to its centroid and a tab to
                # its midpoint means the check compares two POINTS: a tab too
                # long for its slot, or a slot rotated on the plate, lands its
                # midpoint in exactly the right place and passes.
                slots.append(g)
        _n = sum(len(_RB.skin_tabs(_s, _RB.route45()))
                 for _s in (_RB.SHOW, _RB.FAR))
        if len(slots) < _n:
            return ["found %d tab slots in %s, expected %d"
                    % (len(slots), os.path.basename(bp), _n)]
        per_plate.append((os.path.basename(bp),
                          sorted(slots, key=lambda g: (round(g.centroid.x, 3),
                                                       round(g.centroid.y, 3)))))
    if len(per_plate) > 1:
        a, b = per_plate[0][1], per_plate[1][1]
        # SHAPES, NOT CENTROIDS. Comparing centroid to centroid is invariant
        # under rotating a slot about its own centre - and so is
        # check_slot_width(), which measures minimum_rotated_rectangle edge
        # lengths. Between them they were the whole of the second backplate's
        # coverage, so all nine of its slots could be spun 90 degrees, laying
        # a 12.80 mm slot across a 4.15 mm tab, and the gate exited 0. I cut
        # that file and measured it: both checks returned clean.
        for g, h in zip(a, b):
            d = g.symmetric_difference(h).area
            if d > 0.01:
                out.append("the two backplates' tab slots are not the same "
                           "shape in the same place - %.2f mm2 apart at "
                           "(%.1f, %.1f); the tabs cannot fit both"
                           % (d, g.centroid.x, g.centroid.y))
                break
    # AND LAND THE TABS IN WHAT EVERY PLATE LEAVES OPEN, not in plate[0]'s
    # slots. The second plate is a part the buyer may well choose; reached
    # only by the comparison above, it was never a surface a tab had to pass
    # through. Intersecting the plates' slots station by station makes the
    # landing below a statement about all of them at once: if one plate's
    # slot is turned, moved or shrunk, the common opening no longer holds the
    # tab's coated footprint and the landing fails.
    slots = []
    for i in range(len(per_plate[0][1])):
        g = per_plate[0][1][i]
        for pl in per_plate[1:]:
            g = g.intersection(pl[1][i])
        slots.append(g if not g.is_empty else per_plate[0][1][i].buffer(-99))

    path = _RB.route45()
    ang = _RB.deflections(path)
    Rm = _RB.BEND_RADIUS + _RB.T / 2.0
    Rn = _RB.BEND_RADIUS + _RB.K_FACTOR * _RB.T
    for sgn, lab in ((_RB.SHOW, "show"), (_RB.FAR, "far")):
        for flush in _RB.ordered_facades():
            nm = "skin_%s_%s.dxf" % (lab, "flush" if flush else "tall")
            fp = os.path.join(OUT, nm)
            if not os.path.exists(fp):
                continue
            d = ezdxf.readfile(fp)
            msp = d.modelspace()
            marks = sorted((e.dxf.start.x, e.dxf.layer) for e in msp
                           if e.dxftype() == "LINE"
                           and e.dxf.layer.startswith("BEND"))
            tabs = []
            for e in msp:
                if e.dxftype() != "LWPOLYLINE" or e.dxf.layer != "CUT":
                    continue
                ring = [(p[0], p[1]) for p in e.get_points()]
                # EACH TAB CONTRIBUTES EXACTLY TWO POINTS below y=0 - its
                # left and right bottom corners - so pair them. Grouping by a
                # gap threshold does not work here: neighbouring tabs are only
                # 8 mm apart, closer than a tab is wide, and a threshold big
                # enough to span a tab merges two of them.
                # EACH TAB'S OWN TWO POINTS, in ring order. I took the
                # blank's GLOBAL minimum y and stamped it into every tab as
                # its depth, so the depth term tested one constant equal to
                # the DEEPEST tab - and a single tab cut 0.2 mm deep passed
                # the whole gate at exit 0, which is exactly the case the
                # comment beside it named. It could only ever fire when the
                # bounding box had already moved, i.e. when check_part_dims
                # would catch it anyway.
                pair = []
                for k, q in enumerate(ring):
                    if q[1] >= -1e-6:
                        if len(pair) == 2:
                            xs = sorted(p[0] for p in pair)
                            tabs.append(((xs[0] + xs[1]) / 2.0,
                                         xs[1] - xs[0],
                                         -max(p[1] for p in pair)))
                        pair = []
                    else:
                        pair.append(q)
                if len(pair) == 2:
                    xs = sorted(p[0] for p in pair)
                    tabs.append(((xs[0] + xs[1]) / 2.0, xs[1] - xs[0],
                                 -max(p[1] for p in pair)))
            # COUNT THEM. This landed whatever tabs it found and never asked
            # how many there should be, so a skin cut with a tab MISSING - the
            # cover's plan location, on a joint whose lateral budget is at its
            # limit - passed the whole gate at exit 0.
            want_n = len(_RB.skin_tabs(sgn, path))
            if len(tabs) != want_n:
                out.append("%s: %d tabs on the blank, the model says %d"
                           % (nm, len(tabs), want_n))
            if len(marks) != len(ang) or not tabs:
                out.append("%s: %d bend lines and %d tabs - cannot fold it"
                           % (nm, len(marks), len(tabs)))
                continue

            # EVERYTHING FROM THE FILE EXCEPT WHERE THE PART GOES.
            # The first version of this walk took each straight's length from
            # the model and only the layer NAME from the file, so a bend line
            # in the wrong POSITION folded to exactly the right shape and the
            # check said nothing. Now the flat positions come from the bend
            # lines, the angles come from their layer names - which is why the
            # angle is in the layer name - and the blank's length comes from
            # its outline. Only the starting point and direction are borrowed,
            # and those say where the part sits, not what it is.
            W = max(q[0] for e in msp
                    if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "CUT"
                    for q in e.get_points())
            fs, angs = [], []
            for x, lay in marks:
                fs.append(x)
                try:
                    angs.append(float(lay.rsplit("_", 1)[1]))
                except (IndexError, ValueError):
                    out.append("%s: bend layer %r carries no angle" % (nm, lay))
                    angs.append(0.0)
            if any(a <= 0 for a in angs):
                continue
            Rm = _RB.BEND_RADIUS + _RB.T / 2.0
            Rn = _RB.BEND_RADIUS + _RB.K_FACTOR * _RB.T
            SB = [Rm * math.tan(math.radians(a) / 2.0) for a in angs]
            BA = [math.radians(a) * Rn for a in angs]

            mid = _RB.offset(path, _RB.CARCASS_RIB_IN + _RB.T / 2.0, sgn)
            px, py = mid[0]
            ux = mid[1][0] - mid[0][0]
            uy = mid[1][1] - mid[0][1]
            L = math.hypot(ux, uy)
            ux, uy = ux / L, uy / L
            runs, flat = [], 0.0
            for k in range(len(fs) + 1):
                lo = fs[k - 1] + BA[k - 1] / 2.0 if k > 0 else 0.0
                hi = fs[k] - BA[k] / 2.0 if k < len(fs) else W
                seg = hi - lo
                if seg < 0:
                    out.append("%s: bend lines are out of order or overlap"
                               % nm)
                    seg = 0.0
                runs.append((flat, flat + seg, (px, py), (ux, uy)))
                flat += seg
                px, py = px + ux * seg, py + uy * seg
                if k < len(fs):
                    vx = px + ux * SB[k]
                    vy = py + uy * SB[k]
                    th = math.radians(angs[k])
                    st = (-1.0 if marks[k][1].startswith("BEND_UP")
                          else +1.0)
                    c, sn = math.cos(st * th), math.sin(st * th)
                    ux, uy = ux * c - uy * sn, ux * sn + uy * c
                    px, py = vx + ux * SB[k], vy + uy * SB[k]
                    flat += BA[k]

            for _c, _len, _dep in tabs:
                if abs(_len - _RB.TAB_L) > 0.02:
                    out.append("%s: a tab is %.2f mm long, the model says %.2f"
                               % (nm, _len, _RB.TAB_L))
                    break
            for _c, _len, _dep in tabs:
                if abs(_dep - _RB.PLATE_T) > 0.02:
                    out.append("%s: a tab protrudes %.2f mm, against a %.2f mm "
                               "plate to pass through"
                               % (nm, _dep, _RB.PLATE_T))
                    break
            worst = 0.0
            for t, _len, _dep in tabs:
                q = None
                for f0, f1, (sx, sy), (ux2, uy2) in runs:
                    if f0 - 1e-6 <= t <= f1 + 1e-6:
                        q = (sx + ux2 * (t - f0), sy + uy2 * (t - f0))
                        break
                if q is None:
                    continue
                # the tab's own rectangle, laid where it lands, must sit
                # inside a slot - with the coated sizes, since that is what
                # has to go together.
                ux2, uy2 = None, None
                for f0, f1, (sx, sy), (u0, u1) in runs:
                    if f0 - 1e-6 <= t <= f1 + 1e-6:
                        ux2, uy2 = u0, u1
                        break
                dd = 99.0
                if ux2 is not None:
                    nx2, ny2 = -uy2, ux2
                    hl = _len / 2.0 + MFG.COAT_ALLOWANCE
                    hw = _RB.T / 2.0 + MFG.COAT_ALLOWANCE
                    foot = Polygon([
                        (q[0] - ux2 * hl - nx2 * hw, q[1] - uy2 * hl - ny2 * hw),
                        (q[0] + ux2 * hl - nx2 * hw, q[1] + uy2 * hl - ny2 * hw),
                        (q[0] + ux2 * hl + nx2 * hw, q[1] + uy2 * hl + ny2 * hw),
                        (q[0] - ux2 * hl + nx2 * hw, q[1] - uy2 * hl + ny2 * hw)])
                    for g in slots:
                        gg = g.buffer(-MFG.COAT_ALLOWANCE)
                        if gg.contains(foot):
                            dd = 0.0
                            break
                        dd = min(dd, foot.difference(gg).area)
                worst = max(worst, dd)
            if worst > 0.0:
                out.append("%s: folded to its own marks, a tab's coated "
                           "footprint hangs %.3f mm2 outside every slot"
                           % (nm, worst))
            # AND THE FAR END OF THE STRIP. Tabs only constrain the folds
            # upstream of them; the last fold on the show skin and the last
            # two on the far skin have no tab after them at all. Where the
            # strip FINISHES is a physical statement about every fold in it.
            if runs:
                f0, f1, (sx, sy), (ux2, uy2) = runs[-1]
                ex, ey = sx + ux2 * (f1 - f0), sy + uy2 * (f1 - f0)
                wx, wy = mid[-1]
                if math.hypot(ex - wx, ey - wy) > TAB_LAND_TOL:
                    out.append("%s: folded to its own marks, the strip ends "
                               "%.2f mm from where the run does"
                               % (nm, math.hypot(ex - wx, ey - wy)))
    return out


# A RELIEF IS A SIZE, NOT A GAP. The first version of this stepped 0.30 mm
# past a fold end and looked 0.30 mm to each side, so a 0.40 mm nick counted as
# relief - a tenth of what the vendor asks. Their rule, and this project's own
# constants, are RELIEF_W wide by RELIEF_DEPTH deep. Probe THAT footprint.
FOLD_END_W = 1.00          # vendor minimum relief width, t/2
FOLD_END_D = 3.47          # t + bend radius + 0.020 in
FOLD_END_FILL = 0.05       # of the relief's footprint that may still be metal


def _fold_dies_in_metal(blank, a, b, at_end):
    """Is there metal where the relief has to be, at this end of the fold?

    A RELIEF IS CUT INTO THE PARENT, NOT STRADDLED ACROSS THE FOLD. My first
    version probed 0.30 mm each way, which accepted a 0.40 mm nick. The second
    laid a box across the fold line, half of it on the side where there is no
    material anyway - so a relief only 0.867 mm deep filled just 25% of the
    box and squeaked past a 25% threshold, four times looser than the 3.47 mm
    the constant beside it names.

    The region that must be CLEAR is: past the fold's end by RELIEF_W, and
    from the fold line INTO THE PARENT by RELIEF_DEPTH. The parent is
    whichever side of the fold carries the material, which the blank itself
    answers - no need to know the flap's handedness.
    """
    (ax, ay), (bx, by) = a, b
    L = math.hypot(bx - ax, by - ay)
    if L < 1e-9:
        return False
    ux, uy = (bx - ax) / L, (by - ay) / L
    if not at_end:
        ux, uy = -ux, -uy
        px, py = ax, ay
    else:
        px, py = bx, by
    # BOTH SIDES, PAST THE END. Asking which side is "the parent" at a point
    # ON the fold line is meaningless - both sides are metal there, which is
    # what a fold IS. Past the END is where it is decided: with a proper
    # relief neither side has material, and with none, whichever side carries
    # on is the one that tears. So probe both and fail on either.
    w, d = FOLD_END_W, FOLD_END_D
    for sx, sy in ((-uy, ux), (uy, -ux)):
        box = Polygon([(px, py),
                       (px + ux * w, py + uy * w),
                       (px + ux * w + sx * d, py + uy * w + sy * d),
                       (px + sx * d, py + sy * d)])
        if blank.intersection(box).area > FOLD_END_FILL * box.area:
            return True
    return False


def check_fold_ends():
    """A fold may not die in solid metal. Every end needs an edge or a relief.

    This is the condition bend relief exists for: if a bend stops while the
    sheet carries on across its line, the metal tears at that point. It caught
    nothing for seven rounds because it was never written - and then a fix of
    mine created seven of them at once. Trimming a foot back from its corner
    left the wall-to-foot bend 2.148 mm shorter than the wall it folds off, so
    at seven of the ten ends the fold stopped and the blank did not.

    Probed from the FILE, not the model: step a little past each end of each
    bend line and look for material on both sides of the fold's continuation.
    """
    out = []
    for f in sorted(glob.glob(os.path.join(OUT, "*.dxf"))):
        d = ezdxf.readfile(f)
        msp = d.modelspace()
        polys = [Polygon([(p[0], p[1]) for p in e.get_points()])
                 for e in msp if e.dxftype() == "LWPOLYLINE"
                 and e.dxf.layer == "CUT"]
        if not polys:
            continue
        outline = max(polys, key=lambda g: g.area)
        holes = [g for g in polys if g is not outline]
        blank = (outline.difference(unary_union(holes)) if holes else outline)
        bad = 0
        for e in msp:
            if e.dxftype() != "LINE" or not e.dxf.layer.startswith("BEND"):
                continue
            a = (e.dxf.start.x, e.dxf.start.y)
            b = (e.dxf.end.x, e.dxf.end.y)
            for at_end in (False, True):
                if _fold_dies_in_metal(blank, a, b, at_end):
                    bad += 1
                    p = b if at_end else a
                    out.append("%s: a fold ends at (%.2f, %.2f) with metal on "
                               "both sides of its line - no relief there"
                               % (os.path.basename(f), p[0], p[1]))
        if bad > 3:
            del out[-(bad - 3):]
            out.append("%s: ...and %d more fold ends like it"
                       % (os.path.basename(f), bad - 3))
    return out


def _MP_NAME(design_name):
    """The filename make_production gives a design. One derivation, not two."""
    return ("backplate_%s.dxf"
            % design_name.split("/")[0].strip().lower().replace(" ", "_"))


def check_plate_features():
    """The backplate's own outline, die window and card bores, per plate.

    BOUND TO NOTHING. check_part_dims asserted 324.0 x 122.4 and nothing
    else about the outline; check_vent_fields covers the vent field and the
    tab slots are covered twice; the ten dia-3.2 card bores, the 2600 mm2 die
    window and the connector notch were compared to no model at all. Planted
    on a sandbox copy and run through main(), each at exit 0 with zero
    failures: all ten bores +1.5 mm in x; the same at +4.0 mm - a 3.2 bore
    displaced 4.0 cannot take its screw, so the plate does not bolt to the
    card; one bore deleted; one bore +5.0; the die window +4.0; the notch
    +3.0. The gate first spoke at +8.0, and then only as "metal necks to
    0.112 mm" from the generic web test.

    Three comparisons, each against the module that DRAWS the feature -
    backplate_v3.outline() and classify(), die_window.POLY - so a plate that
    was cut from something else, or edited by hand, cannot pass.
    """
    import backplate_v3 as _B
    import make_production as _MP
    from die_window import POLY as _DIE
    out = []
    want_out = Polygon(_B.outline())
    want_die = Polygon(_DIE)
    closed, _slotted = _B.classify()
    want_bores = sorted((round(x, 2), round(y, 2)) for x, y, _t, _s in closed)

    for design in _MP.PLATES:
        nm = _MP_NAME(design)
        p = os.path.join(OUT, nm)
        if not os.path.exists(p):
            out.append("%s is not on disk" % nm)
            continue
        _d, cut, _b, _tap, _o = _read(p)
        polys = [c for c in cut if isinstance(c, Polygon)]
        circs = [c for c in cut if isinstance(c, dict)]
        if not polys:
            out.append("%s has no closed CUT contour" % nm)
            continue
        shell = max(polys, key=lambda g: g.area)
        d_out = shell.symmetric_difference(want_out).area
        if d_out > 0.5:
            out.append("%s: outline differs from backplate_v3.outline() by "
                       "%.1f mm2 - notch, edge holes or edge have moved"
                       % (nm, d_out))
        holes = [g for g in polys if g is not shell]
        if holes:
            die = max(holes, key=lambda g: g.area)
            d_die = die.symmetric_difference(want_die).area
            if d_die > 0.5:
                out.append("%s: the die window differs from die_window.POLY "
                           "by %.1f mm2" % (nm, d_die))
        else:
            out.append("%s: no die window" % nm)
        got = sorted((round(c["at"][0], 2), round(c["at"][1], 2))
                     for c in circs if abs(c["d"] - _B.BORE) < 0.05)
        if len(got) != len(want_bores):
            out.append("%s: %d card bores of dia %.2f, the card has %d"
                       % (nm, len(got), _B.BORE, len(want_bores)))
        else:
            worst = max(math.hypot(a[0] - b[0], a[1] - b[1])
                        for a, b in zip(got, want_bores))
            if worst > 0.02:
                out.append("%s: a card bore is %.2f mm from where "
                           "backplate_v3 puts it - the plate will not bolt "
                           "to the card" % (nm, worst))
    return out


def check_vent_fields():
    """Both backplates' openings, against the model that drew each of them.

    NOTHING BOUND THE SECOND PLATE TO ANYTHING. check_exported_solids is the
    only check that compares a plate's openings to anything at all, and it
    reads ES_DESIGN - the ONE plate export_solids builds, Interference. The
    other three checks that open a backplate are blind to the art:
    check_part_dims asserts only the 324.0 x 122.4 outline, and
    check_slot_width and check_tabs_land look at the nine tab slots. So
    backplate_bit_plane.dxf could be anything with the right outline.

    Measured, three plants in a sandbox copy, each run through main():
      1. all 88 vent openings deleted            -> exit 0, zero failures
      2. the 2600 mm2 die window deleted         -> exit 0, zero failures
      3. the file replaced by a byte copy of the
         Interference plate                      -> exit 0, zero failures
    The identical three plants on backplate_interference.dxf all fail.

    Two questions here, and they fail differently on purpose:

    A. EACH PLATE AGAINST ITS OWN VENT MODEL - count and area. This one does
       re-run the generator, so on its own it would be the circular kind of
       check. It is not here to prove the art is right; it is to prove the
       FILE still holds the art, which is what plants 1 and 2 destroy.

    B. THE TWO PLATES AGAINST EACH OTHER. They must be identical everywhere
       except the vent field - same outline, same ten card fasteners, same
       nine tab slots, same die window - and they must DIFFER inside it.
       Nothing re-derives anything for this one, and it is what catches plant
       3: a copy of the other plate passes A perfectly and fails B.
    """
    import vent_ocr as _VO
    import make_production as _MP
    from shapely.ops import unary_union as _uu
    out = []
    # THE NAMES THE EMITTER USES, derived its way. Typing them here got
    # "Interference / Graf3X" against a real "Interference / Graf3X, OCR"
    # and the lookup raised - which this check reports, but a check that
    # can only ever report its own typo is not checking the part.
    plates = [(_MP_NAME(n), n) for n in _MP.PLATES]

    fields = {}
    for nm, design in plates:
        p = os.path.join(OUT, nm)
        if not os.path.exists(p):
            out.append("%s is not on disk" % nm)
            continue
        _d, cut, _b, _tap, _o = _read(p)
        ps = [c if isinstance(c, Polygon) else c["geom"] for c in cut]
        if not ps:
            out.append("%s has no CUT geometry at all" % nm)
            continue
        shell = max(ps, key=lambda g: g.area)
        holes = [g for g in ps if g is not shell]

        try:
            fn = dict(_VO.DESIGNS)[design]
            vents, _dropped = _VO.build_one(fn, _VO.plate_field())
            # build_one hands back a MultiPolygon, not a list
            vents = list(getattr(vents, "geoms", None) or
                         ([vents] if not isinstance(vents, list)
                          else vents))
        except Exception as e:
            out.append("%s: cannot rebuild its vent model: %s"
                       % (nm, str(e)[:60]))
            continue
        want_a = sum(g.area for g in vents)
        want_n = len(vents)

        # the vent field is the openings inside the field envelope
        env = _uu([g.buffer(0.6) for g in vents]).buffer(0.6)
        mine = [g for g in holes if env.contains(g.representative_point())]
        got_a = sum(g.area for g in mine)
        fields[nm] = (mine, holes, shell)

        if len(mine) != want_n:
            out.append("%s: %d vent openings in the file, the %s model draws "
                       "%d" % (nm, len(mine), design.split("/")[0].strip(),
                               want_n))
        elif abs(got_a - want_a) > 1.0:
            out.append("%s: vent field is %.0f mm2, the %s model draws %.0f"
                       % (nm, got_a, design.split("/")[0].strip(), want_a))

        # THE DIE WINDOW. Plant 2 filled it in solid and nothing noticed.
        # It is the single largest opening in the plate by a wide margin.
        big = max((g.area for g in holes), default=0.0)
        if big < 2000.0:
            out.append("%s: largest opening is %.0f mm2 - the die window "
                       "(about 2600) is missing" % (nm, big))

    # B. the two plates against each other, no model involved
    if len(fields) == 2:
        (na, (va, ha, sa)), (nb, (vb, hb, sb)) = list(fields.items())
        if sa.symmetric_difference(sb).area > 0.5:
            out.append("the two backplates' outlines differ by %.1f mm2 - "
                       "they are meant to be the same part with different art"
                       % sa.symmetric_difference(sb).area)
        # everything that is NOT a vent must match, one for one
        oa = _uu([g for g in ha if g not in va])
        ob = _uu([g for g in hb if g not in vb])
        d = oa.symmetric_difference(ob).area
        if d > 0.5:
            out.append("outside the vent field the two backplates differ by "
                       "%.1f mm2 - the die window, the ten card fasteners and "
                       "the nine tab slots must be identical on both" % d)
        # and the art must actually be different art
        fa, fb = _uu(va), _uu(vb)
        if fa.symmetric_difference(fb).area < 50.0:
            out.append("the two backplates' vent fields are the same to "
                       "within %.1f mm2 - one of them is a copy of the other, "
                       "and the order is paying for two designs"
                       % fa.symmetric_difference(fb).area)
    return out


def check_slot_width():
    """The slots as CUT, against the tolerance stack they have to swallow.

    hardware.py prints this comparison but cannot fail it: SLOT_W is defined
    as T + 4*COAT + 2*SLOT_ACROSS, so its "measured" clearance is the stack by
    construction. Measuring the rectangles in the backplate is a different
    question with a different answer whenever the emitter and the constant
    disagree.
    """
    import cover_ribbon as _RB
    from config import MFG as _M
    out = []
    for nm in ("backplate_interference.dxf", "backplate_bit_plane.dxf"):
        p = os.path.join(OUT, nm)
        if not os.path.exists(p):
            continue
        got, lens, ats, dirs = [], [], [], []
        for e in ezdxf.readfile(p).modelspace():
            if e.dxftype() != "LWPOLYLINE" or e.dxf.layer != "CUT":
                continue
            pts = [(q[0], q[1]) for q in e.get_points()]
            if len(pts) != 4:
                continue
            r = list(Polygon(pts).minimum_rotated_rectangle.exterior.coords)
            ed = sorted(math.hypot(r[i + 1][0] - r[i][0],
                                   r[i + 1][1] - r[i][1]) for i in range(4))
            if any(abs(ed[0] - w) < 0.5 for w in _slot_widths()):
                got.append(ed[0])
                lens.append(max(ed))
                _c = Polygon(pts).centroid
                ats.append((_c.x, _c.y))
                # WHICH WAY IT POINTS. Edge lengths off a rotated rectangle
                # are the same whichever way the rectangle lies, so a slot
                # spun 90 degrees on the plate measured 4.15 by 12.80 exactly
                # as intended and passed. The long axis has to run along the
                # cable route, because that is the way the tab lies.
                ii = max(range(4), key=lambda k: math.hypot(
                    r[k + 1][0] - r[k][0], r[k + 1][1] - r[k][1]))
                dirs.append(math.atan2(r[ii + 1][1] - r[ii][1],
                                       r[ii + 1][0] - r[ii][0]) % math.pi)
        _n = sum(len(_RB.skin_tabs(_s, _RB.route45()))
                 for _s in (_RB.SHOW, _RB.FAR))
        if len(got) != _n:
            out.append("%s: found %d tab slots, expected %d" % (nm, len(got), _n))
            continue
        # AND ITS LENGTH. Only the width was ever measured, so a slot cut
        # 4.20 mm long - a third of the 12.00 mm tab it has to swallow - read
        # as a perfectly good slot and the gate exited 0. Length is the
        # dimension that carries the bend-to-edge tolerance, which is why
        # five of the nine are longer than the other four.
        # EACH SLOT AGAINST ITS OWN TAB, not the multiset against the
        # multiset. Sorting both sides and comparing meant swapping two slots'
        # lengths between them passed - and those two lengths differ by the
        # bend-to-edge tolerance the longer one exists to swallow, so the swap
        # puts a tab that needs 13.56 into 12.80.
        want, wdir, _across = {}, {}, {}
        _pa = _RB.route45()
        for sgn in (_RB.SHOW, _RB.FAR):
            for t in _RB.skin_tabs(sgn, _pa):
                k = (round(t["at"][0], 2), round(t["at"][1], 2))
                want[k] = t["slot_l"]
                _across[k] = _RB.slot_across_for(t["leg"], sgn)
                (_ax, _ay), (_bx, _by) = _pa[t["leg"]], _pa[t["leg"] + 1]
                wdir[k] = math.atan2(_by - _ay, _bx - _ax) % math.pi
        # EACH SLOT AGAINST ITS OWN STACK. Taking the narrowest slot and
        # comparing it to the one global SLOT_ACROSS asked whether the
        # tightest slot swallows the loosest station's tolerance - which is
        # neither the question nor an answer to it. A slot three bends from a
        # bonded foot has to swallow 1.539 mm per side; one bend, 0.777.
        for at, w in zip(ats, got):
            key = (round(at[0], 2), round(at[1], 2))
            need = _across.get(key)
            if need is None:
                continue
            side = ((w - 2 * _M.COAT_ALLOWANCE)
                    - (_RB.TAB_W + 2 * _M.COAT_ALLOWANCE)) / 2.0
            if side < need - 1e-6:
                out.append("%s: the slot at (%.1f, %.1f) is %.3f wide, giving "
                           "%.3f mm per side coated, against a stack of %.3f"
                           % (nm, at[0], at[1], w, side, need))
        for at, ln, dr in zip(ats, lens, dirs):
            key = (round(at[0], 2), round(at[1], 2))
            if key not in want:
                out.append("%s: a tab slot at (%.1f, %.1f) is at no tab station"
                           % (nm, at[0], at[1]))
                continue
            if abs(ln - want[key]) > 0.02:
                out.append("%s: the slot at (%.1f, %.1f) is %.2f mm long, its "
                           "tab needs %.2f"
                           % (nm, at[0], at[1], ln, want[key]))
            dd = abs(dr - wdir[key]) % math.pi
            dd = min(dd, math.pi - dd)
            if dd > math.radians(0.5):
                out.append("%s: the slot at (%.1f, %.1f) lies %.1f degrees "
                           "off the route it has to let a tab through"
                           % (nm, at[0], at[1], math.degrees(dd)))
    return out


def check_carcass_folds():
    """The carcass's fifteen fold marks, against the model.

    check_fold_direction() and check_fold_sequence() both glob skin_*.dxf, so
    the part with FIFTEEN folds - three times as many as both skins together -
    had its direction and its angle checked by nothing at all. It is the one
    part whose folds all go the same way, which is exactly the kind of thing
    that looks too obvious to test until someone emits one of them the other
    way.
    """
    import cover_ribbon as _RB
    p = os.path.join(OUT, "carcass.dxf")
    if not os.path.exists(p):
        return ["carcass.dxf missing"]
    d = ezdxf.readfile(p)
    lines = [e for e in d.modelspace()
             if e.dxftype() == "LINE" and e.dxf.layer.startswith("BEND")]
    out = []
    _top, flaps = _RB.carcass_blank(_RB.route45())
    if len(lines) != len(flaps):
        out.append("carcass.dxf carries %d fold lines, the blank has %d flaps "
                   "and therefore %d folds"
                   % (len(lines), len(flaps), len(flaps)))
    # A HAT: walls fold DOWN from the top face, feet fold UP (outward)
    # from the walls. Count each layer against the flaps of that kind.
    n_up = sum(1 for e in lines if e.dxf.layer == "BEND_UP_90")
    n_dn = sum(1 for e in lines if e.dxf.layer == "BEND_DOWN_90")
    w_up = sum(1 for f in flaps if f["kind"] == "foot")
    w_dn = sum(1 for f in flaps if f["kind"] in ("downstand", "endcap"))
    if (n_up, n_dn) != (w_up, w_dn) or n_up + n_dn != len(lines):
        out.append("carcass.dxf has %d folds on BEND_UP_90 and %d on "
                   "BEND_DOWN_90; the blank has %d feet (UP) and %d walls "
                   "(DOWN)" % (n_up, n_dn, w_up, w_dn))
    # and each one must sit on a flap's attachment edge
    want = []
    for f in flaps:
        c = list(f["poly"].exterior.coords)
        want.append((c[0], c[1]))
    for e in lines:
        a = (e.dxf.start.x, e.dxf.start.y)
        b = (e.dxf.end.x, e.dxf.end.y)
        if not any(max(math.dist(a, w0), math.dist(b, w1)) < 0.01
                   or max(math.dist(a, w1), math.dist(b, w0)) < 0.01
                   for w0, w1 in want):
            out.append("carcass.dxf: a fold line from (%.2f, %.2f) to "
                       "(%.2f, %.2f) is not on any flap's attachment edge"
                       % (a[0], a[1], b[0], b[1]))
            break
    return out

if __name__ == "__main__":
    sys.exit(main())
