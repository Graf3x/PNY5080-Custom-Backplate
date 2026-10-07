"""Release gate for v94: the files in out/production_v94/upload, measured.

Every check here reads the DXF the vendor gets, or the folded geometry the
model derives from the same numbers, and says what it measured. A check
whose every branch is a `continue` is a check that measured nothing, so the
counts are printed. Planted defects at the end prove the checks can fail.
"""

from __future__ import annotations

import math
import os
import sys

import ezdxf
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backplate_v3 as B                                     # noqa: E402
import cover_ribbon as RB                                    # noqa: E402
import release_gate as G                                     # noqa: E402
import v94 as V                                              # noqa: E402
from config import MFG                                       # noqa: E402
from hole_pattern import HOLES                               # noqa: E402

UP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out",
                  "production_v94", "upload")
FILES = ["backplate_interference_v94.dxf", "backplate_bit_plane_v94.dxf",
         "carcass_v94.dxf", "skin_show_v94.dxf", "skin_far_v94.dxf"]
POWDER_MIN = 25.4
MIN_PART = RB.MIN_PART


def _read(name):
    d = ezdxf.readfile(os.path.join(UP, name))
    msp = d.modelspace()
    polys, circles, lines, other = [], [], [], 0
    for e in msp:
        t = e.dxftype()
        if t == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points()]
            polys.append((e.dxf.layer, Polygon(pts)))
        elif t == "CIRCLE":
            circles.append((e.dxf.layer, (e.dxf.center.x, e.dxf.center.y), 2 * e.dxf.radius))
        elif t == "LINE":
            lines.append((e.dxf.layer, e.dxf.linetype,
                          (e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)))
        else:
            other += 1
    return dict(doc=d, polys=polys, circles=circles, lines=lines, other=other,
                units=d.header.get("$INSUNITS", 0))


def check_common(name, f, declared=()):
    """What every file must satisfy: units, closed valid contours, no text,
    min feature in metal and in openings, knife edges, dashed bends."""
    fails, notes = [], []
    if f["units"] != 4:
        fails.append("%s: $INSUNITS %s, not 4 (mm)" % (name, f["units"]))
    if f["other"]:
        fails.append("%s: %d entities that are neither contour, circle nor "
                     "bend line (text left in the upload copy?)" % (name, f["other"]))
    polys = [p for lay, p in f["polys"]]
    for lay, p in f["polys"]:
        if lay != "CUT":
            fails.append("%s: a contour on layer %s" % (name, lay))
        if not p.is_valid or p.area < 1e-6:
            fails.append("%s: an invalid or empty contour" % name)
    outline = max(polys, key=lambda g: g.area)
    holes = [g for g in polys if g is not outline]
    for g in holes:
        if not outline.contains(g.representative_point()):
            fails.append("%s: a contour outside the outline" % name)
    circs = [Point(c).buffer(dia / 2.0, resolution=32) for lay, c, dia in f["circles"]]
    allp = polys + circs
    tm, at = G.thinnest_metal(allp)
    notes.append("thinnest metal %.3f mm%s" % (tm, "" if at is None else " at (%.1f, %.1f)" % at))
    if tm < MFG.MIN_FEATURE - 1e-6:
        # the carcass's mitres are declared; everything else is a defect
        ok = any(g["region"].distance(Point(at)) <= G.DECLARED_NEAR for g in declared) if at else False
        if not ok or tm < G.CORNER_GAP - 1e-6:
            fails.append("%s: thinnest metal %.3f mm at (%.1f, %.1f), under %.2f"
                         % (name, tm, at[0], at[1], MFG.MIN_FEATURE))
    no, nat = G.narrowest_opening(holes)
    notes.append("narrowest opening %.3f mm" % no)
    if no < MFG.MIN_FEATURE - 1e-6:
        fails.append("%s: an opening narrows to %.3f mm at (%.1f, %.1f)"
                     % (name, no, nat[0], nat[1]))
    pf, worst, sharp = G._acute_and_pinch(name, polys, declared)
    fails += pf
    notes.append("sharpest cut vertex %.1f deg, tightest self-pinch %.3f mm"
                 % (sharp[0], worst[0]))
    for lay, lt, a, b in f["lines"]:
        if lt != "DASHED":
            fails.append("%s: a bend line with linetype %s, not DASHED" % (name, lt))
        if not lay.startswith("BEND_"):
            fails.append("%s: a line on layer %s - only bend lines may be lines" % (name, lay))
        if math.dist(a, b) < 5.0:
            fails.append("%s: a %.2f mm bend line" % (name, math.dist(a, b)))
    minx, miny, maxx, maxy = outline.bounds
    w, h = maxx - minx, maxy - miny
    notes.append("extents %.2f x %.2f mm" % (w, h))
    if min(w, h) < MIN_PART[0] or max(w, h) < MIN_PART[1]:
        fails.append("%s: under the vendor's minimum part %s" % (name, MIN_PART))
    if min(w, h) < POWDER_MIN - 1e-6:
        fails.append("%s: %.2f mm wide, under the 1 in powder minimum" % (name, min(w, h)))
    return fails, notes, outline, holes


def check_holes_vs_bends(name, f, keep=V.KEEP):
    """Every circle's EDGE at least `keep` from every bend line, and MIN_FEATURE
    of metal to the outline. The flat-pattern rule, measured in the flat."""
    fails, n = [], 0
    outline = max((p for lay, p in f["polys"]), key=lambda g: g.area)
    for lay, c, dia in f["circles"]:
        n += 1
        for blay, lt, a, b in f["lines"]:
            dd = LineString([a, b]).distance(Point(c)) - dia / 2.0
            if dd < keep - 1e-6:
                fails.append("%s: hole at (%.2f, %.2f) is %.2f from a bend line, under %.2f"
                             % (name, c[0], c[1], dd, keep))
        web = outline.exterior.distance(Point(c)) - dia / 2.0
        if web < MFG.MIN_FEATURE - 1e-6:
            fails.append("%s: hole at (%.2f, %.2f) leaves %.2f of web to the edge"
                         % (name, c[0], c[1], web))
    return fails, n


def check_skin(name, sgn, f=None, outline=None, pieces=None, holes=None, lines=None):
    """The skin's own rules, on the file (or on planted geometry)."""
    fails, notes = [], []
    pth = V.path()
    r = V.skin_dev(sgn, pth)
    if f is not None:
        outline = max((p for lay, p in f["polys"]), key=lambda g: g.area)
        lines = f["lines"]
        holes = [(c, dia) for lay, c, dia in f["circles"]]
        for lay, c, dia in f["circles"]:
            if lay != "TAP" or abs(dia - V.TAP_DRILL) > 1e-3:
                fails.append("%s: a %.2f circle on %s - only %.2f taps belong on a skin"
                             % (name, dia, lay, V.TAP_DRILL))
        pieces = [(a[0], b[0]) for lay, lt, a, b in lines if lay == "BEND_DOWN_90"]
        v45 = [(lay, a, b) for lay, lt, a, b in lines if lay.endswith("_45")]
        if len(v45) != len(r["folds"]):
            fails.append("%s: %d 45-degree fold lines, model has %d" % (name, len(v45), len(r["folds"])))
        for lay, a, b in v45:
            k = min(range(len(r["folds"])), key=lambda q: abs(r["folds"][q] - a[0]))
            want = RB.fold_layer(RB.turns(pth)[k], r["angles"][k])
            if lay != want or abs(a[0] - r["folds"][k]) > 1e-3:
                fails.append("%s: fold at x=%.2f on %s, model says %s at %.2f"
                             % (name, a[0], lay, want, r["folds"][k]))
            if min(a[1], b[1]) > -V.FREE_DROP + 1e-3 or max(a[1], b[1]) < V.SKIN_WALL_FLAT - 1e-3:
                fails.append("%s: the 45 fold at x=%.2f does not span the wall" % (name, a[0]))
    minx, miny, maxx, maxy = outline.bounds
    if maxy - miny < POWDER_MIN:
        fails.append("%s: flat %.2f under the powder minimum" % (name, maxy - miny))
    # every foot fold that ends inside the strip ends in a relief slot
    reliefs = 0
    for x0, x1 in pieces:
        for xe, sg in ((x0, -1.0), (x1, +1.0)):
            if xe <= minx + 1e-6 or xe >= maxx - 1e-6:
                continue
            probe = Point(xe + sg * V.RELIEF_W / 2.0, V.RELIEF_DEPTH / 2.0)
            if outline.contains(probe):
                fails.append("%s: foot fold ends at x=%.2f with NO relief slot past it"
                             % (name, xe))
            else:
                reliefs += 1
        if x1 - x0 < V.FOOT_SEG_MIN - 1e-6:
            fails.append("%s: a %.2f mm foot piece, under %.1f" % (name, x1 - x0, V.FOOT_SEG_MIN))
    # fold gaps: no foot fold within FOLD_CLEAR of a 45 fold mark
    for x0, x1 in pieces:
        for fx in r["folds"]:
            if x0 - 1e-6 < fx < x1 + 1e-6 or min(abs(fx - x0), abs(fx - x1)) < V.FOLD_CLEAR - 1e-6:
                fails.append("%s: a foot fold reaches within %.2f of the 45 fold at %.2f"
                             % (name, min(abs(fx - x0), abs(fx - x1)), fx))
    # the wall reaches the plate everywhere: the bottom edge is at -FREE_DROP
    # wherever there is no foot and no relief slot
    x = minx + 0.5
    misses = 0
    while x < maxx - 0.5:
        in_piece = any(x0 + 1e-6 < x < x1 - 1e-6 for x0, x1 in pieces)
        near_relief = any(abs(x - xe) <= V.RELIEF_W + 0.05 for x0, x1 in pieces for xe in (x0, x1))
        if not in_piece and not near_relief:
            if not outline.contains(Point(x, -V.FREE_DROP + 0.05)):
                misses += 1
        x += 0.5
    if misses:
        fails.append("%s: the wall's free edge is short of the plate at %d stations" % (name, misses))
    # each tap sits in a piece, SCREW_END from its ends
    for c, dia in holes:
        if not any(x0 + V.SCREW_END - 1e-6 <= c[0] <= x1 - V.SCREW_END + 1e-6 for x0, x1 in pieces):
            fails.append("%s: tap at x=%.2f is not %.1f inside a foot piece" % (name, c[0], V.SCREW_END))
        if abs(c[1] + V.SCREW_FLAT) > 1e-3:
            fails.append("%s: tap at y=%.3f, model says %.3f" % (name, c[1], -V.SCREW_FLAT))
    notes.append("%d foot pieces, %d relief slots, %d taps, flat %.2f x %.2f"
                 % (len(pieces), reliefs, len(holes), maxx - minx, maxy - miny))
    return fails, notes


def check_folded(feet_by_side=None, plate_holes=None):
    """The feet on the plate: no two overlap, none off the plate, over the
    notch, the die window or a washer; every screw clear of the card bores and
    inside its foot with web; the plate's holes agree with the skins' taps."""
    fails, notes = [], []
    pth = V.path()
    feet = feet_by_side if feet_by_side is not None else {
        sgn: [g for _pi, g in V.folded_feet(sgn, pth)] for sgn in (RB.SHOW, RB.FAR)}
    allfeet = [(sgn, g) for sgn in feet for g in feet[sgn]]
    n_pairs = 0
    for i in range(len(allfeet)):
        for j in range(i + 1, len(allfeet)):
            n_pairs += 1
            dd = allfeet[i][1].distance(allfeet[j][1])
            if dd < V.CORNER_GAP - 1e-6:
                fails.append("two folded feet %.3f mm apart (min %.2f) near (%.1f, %.1f)"
                             % (dd, V.CORNER_GAP, *allfeet[i][1].centroid.coords[0]))
    ob, plate = V._obstacles()
    for sgn, g in allfeet:
        if not plate.contains(g):
            fails.append("a %s foot runs off the plate" % ("show" if sgn > 0 else "far"))
        if g.intersects(ob):
            fails.append("a %s foot lies over the notch, the die window or a washer"
                         % ("show" if sgn > 0 else "far"))
    holes = plate_holes if plate_holes is not None else V.plate_holes(pth)
    for p in holes:
        dmin = min(math.hypot(p[0] - x, p[1] - y) for x, y, _t, _s in HOLES)
        if dmin < V.BORE_CLEAR - 1e-6:
            fails.append("screw at (%.1f, %.1f) is %.2f from a card bore, under %.1f"
                         % (p[0], p[1], dmin, V.BORE_CLEAR))
        disc = Point(p).buffer(V.CLEAR_HOLE / 2.0)
        host = [g for _s, g in allfeet if g.contains(Point(p))]
        if not host:
            fails.append("screw at (%.1f, %.1f) is under no foot" % p)
        elif host[0].exterior.distance(disc) < MFG.MIN_FEATURE - 1e-6:
            fails.append("screw at (%.1f, %.1f) leaves %.2f of foot around it"
                         % (p[0], p[1], host[0].exterior.distance(disc)))
    notes.append("%d feet, %d pairs tested, %d screws" % (len(allfeet), n_pairs, len(holes)))
    return fails, notes


def check_plate(name, f):
    fails, notes = [], []
    polys = [p for lay, p in f["polys"]]
    outline = max(polys, key=lambda g: g.area)
    want = Polygon(B.outline())
    if outline.symmetric_difference(want).area > 1e-3:
        fails.append("%s: outline differs from the plate" % name)
    circ = f["circles"]
    bores = [c for lay, c, dia in circ if abs(dia - B.BORE) < 1e-3]
    clear = [c for lay, c, dia in circ if abs(dia - V.CLEAR_HOLE) < 1e-3]
    taps = [c for lay, c, dia in circ if lay == "TAP"]
    if taps:
        fails.append("%s: %d TAP circles - v94 plates are not tapped" % (name, len(taps)))
    if len(bores) != 10:
        fails.append("%s: %d card bores, expected 10" % (name, len(bores)))
    want_h = V.plate_holes()
    if len(clear) != len(want_h):
        fails.append("%s: %d clearance holes, model has %d" % (name, len(clear), len(want_h)))
    for p in want_h:
        if min(math.dist(p, c) for c in clear) > 1e-3:
            fails.append("%s: no clearance hole at (%.2f, %.2f)" % (name, p[0], p[1]))
    # no slots: every non-outline contour is a vent, the die window or a relief slot
    # web between vents and the cover holes
    vents = [g for g in polys if g is not outline]
    vu = unary_union(vents)
    for p in want_h:
        dd = vu.distance(Point(p).buffer(V.CLEAR_HOLE / 2.0))
        if dd < 2.2 - 1e-6:
            fails.append("%s: a vent %.2f from the cover hole at (%.1f, %.1f)" % (name, dd, p[0], p[1]))
    # the wordmark still reads
    try:
        import ocr_check as OC
        import vent_ocr as VO
        design = [n for n in VO.DESIGNS if _plate_key(n[0]) in name][0][0]
        g, _d = V.plate_vents(design)
        txt, det = OC.read(g, V.plate_field(), VO.OCR_BOX)
        ok, why = OC.verdict(txt, det)
        notes.append("OCR %r %s" % (txt, "PASS" if ok else "FAIL"))
        if not ok:
            fails.append("%s: wordmark OCR failed - %s" % (name, why))
    except Exception as e:
        fails.append("%s: OCR check did not run (%s)" % (name, str(e)[:80]))
    notes.append("%d contours, %d bores, %d clearance" % (len(polys), len(bores), len(clear)))
    return fails, notes


def _plate_key(design_name):
    return design_name.split("/")[0].strip().lower().replace(" ", "_")


def check_carcass(name, f):
    fails, notes = [], []
    lines = f["lines"]
    if len(lines) != 10 or any(lay != "BEND_DOWN_90" for lay, lt, a, b in lines):
        fails.append("%s: %d bend lines on %s - expected 10 on BEND_DOWN_90"
                     % (name, len(lines), sorted(set(l[0] for l in lines))))
    polys = [p for lay, p in f["polys"]]
    outline = max(polys, key=lambda g: g.area)
    inner = [g for g in polys if g is not outline]
    top, flaps = V.carcass_blank()
    if len(inner) != len(top.interiors):
        fails.append("%s: %d roof openings, model has %d" % (name, len(inner), len(top.interiors)))
    # every fold line is an edge of the blank and every roof cell keeps the
    # bend keep-out from every fold
    for lay, lt, a, b in lines:
        seg = LineString([a, b])
        if seg.distance(outline.exterior) > 1e-3 and not outline.buffer(1e-3).contains(seg):
            fails.append("%s: a fold line is not on the blank" % name)
        for g in inner:
            if g.distance(seg) < V.KEEP - 1e-6:
                fails.append("%s: a roof vent %.2f from a fold, under %.2f" % (name, g.distance(seg), V.KEEP))
    if f["circles"]:
        fails.append("%s: %d circles - the carcass has no holes" % (name, len(f["circles"])))
    # the end cap: its fold is the roof's end edge; its width
    cap = [q for q in flaps if q["kind"] == "endcap"][0]["poly"]
    minx, miny, maxx, maxy = cap.bounds
    notes.append("end cap %.2f wide, %.3f deep; %d walls" % (maxx - minx, maxy - miny,
                 sum(1 for q in flaps if q["kind"] == "downstand")))
    return fails, notes


def declared_for_carcass():
    saved = (RB.FOOT_SIDES, RB.END_CAP)
    try:
        RB.FOOT_SIDES = {}
        RB.END_CAP = False
        return RB.declared_gaps(V.path())
    finally:
        RB.FOOT_SIDES, RB.END_CAP = saved


def selftest():
    """Plant defects in memory and require the checks to reject them."""
    out = []
    pth = V.path()
    sgn = RB.SHOW
    r = V.skin_dev(sgn, pth)
    outline = V.skin_outline(sgn, pth)
    pieces = [(x0, x1) for x0, x1, _l in V.foot_pieces(sgn, pth)]
    holes = [(c, V.TAP_DRILL) for c in V.skin_holes(sgn, pth)]
    lines = []
    # 1. a foot end with its relief filled back in
    x0, x1 = pieces[0]
    filled = outline.union(Polygon([(x1, -0.5), (x1 + V.RELIEF_W, -0.5),
                                    (x1 + V.RELIEF_W, V.RELIEF_DEPTH + 0.5), (x1, V.RELIEF_DEPTH + 0.5)])).buffer(0)
    fl, _n = check_skin("planted-relief", sgn, outline=filled, pieces=pieces, holes=holes, lines=lines)
    out.append(("relief slot removed", any("NO relief" in q for q in fl)))
    # 2. a foot piece pushed into a 45 fold's die window
    bad = list(pieces); bad[1] = (bad[1][0] - 4.0, bad[1][1])
    fl, _n = check_skin("planted-gap", sgn, outline=outline, pieces=bad, holes=holes, lines=lines)
    out.append(("foot inside the fold's die window", any("within" in q for q in fl)))
    # 3. a tap outside its piece
    fl, _n = check_skin("planted-tap", sgn, outline=outline, pieces=pieces,
                        holes=[((pieces[0][0] + 2.0, -V.SCREW_FLAT), V.TAP_DRILL)], lines=lines)
    out.append(("tap too close to a foot end", any("not" in q and "inside" in q for q in fl)))
    # 4. a tap in the bend keep-out, in a fake file
    fake = dict(polys=[("CUT", outline)], circles=[("TAP", (pieces[0][0] + 10.0, -4.0), V.TAP_DRILL)],
                lines=[("BEND_DOWN_90", "DASHED", (pieces[0][0], 0.0), (pieces[0][1], 0.0))])
    fl, _n = check_holes_vs_bends("planted-keepout", fake)
    out.append(("tap inside the bend keep-out", any("under" in q for q in fl)))
    # 5. two feet overlapping, folded
    feet = {s: [g for _pi, g in V.folded_feet(s, pth)] for s in (RB.SHOW, RB.FAR)}
    g0 = feet[RB.SHOW][0]
    feet[RB.SHOW] = feet[RB.SHOW] + [g0.buffer(0.2)]
    fl, _n = check_folded(feet_by_side=feet, plate_holes=[])
    out.append(("two feet overlapping", any("apart" in q for q in fl)))
    # 6. a screw on a card bore
    x, y = HOLES[0][0], HOLES[0][1]
    fl, _n = check_folded(plate_holes=[(x + 1.0, y)])
    out.append(("screw on a card bore", any("card bore" in q for q in fl)))
    # 7. a skin blank under the powder width
    thin = Polygon([(0, 0), (199, 0), (199, 20), (0, 20)])
    fl, _n = check_skin("planted-narrow", sgn, outline=thin, pieces=[], holes=[], lines=[])
    out.append(("skin under 1 in wide", any("powder" in q for q in fl)))
    return out


def main():
    allf = []
    print("RELEASE GATE %s  -  %s\n" % (V.VERSION, os.path.normpath(UP)))
    missing = [n for n in FILES if not os.path.exists(os.path.join(UP, n))]
    if missing:
        print("  MISSING:", missing)
        return 1
    declared = declared_for_carcass()
    for name in FILES:
        f = _read(name)
        dec = declared if name.startswith("carcass") else ()
        fails, notes, outline, holes = check_common(name, f, dec)
        if name.startswith("skin"):
            sgn = RB.SHOW if "show" in name else RB.FAR
            fl, nt = check_skin(name, sgn, f=f)
            fails += fl; notes += nt
            fl, n = check_holes_vs_bends(name, f)
            fails += fl; notes.append("%d holes tested against %d bend lines" % (n, len(f["lines"])))
        elif name.startswith("carcass"):
            fl, nt = check_carcass(name, f)
            fails += fl; notes += nt
        else:
            fl, nt = check_plate(name, f)
            fails += fl; notes += nt
        print("  %-32s %s" % (name, "FAIL" if fails else "ok"))
        for q in notes:
            print("      %s" % q)
        for q in fails:
            print("      FAIL  %s" % q)
        allf += fails
    fl, nt = check_folded()
    print("  %-32s %s" % ("folded feet on the plate", "FAIL" if fl else "ok"))
    for q in nt:
        print("      %s" % q)
    for q in fl:
        print("      FAIL  %s" % q)
    allf += fl
    print("  stack: plate %.2f, foot top %.2f, carcass %.2f, roof top %.2f, bundle clear %.2f"
          % (V.Z_PLATE, V.Z_FOOT_TOP, V.Z_CARC, V.Z_ROOF_TOP, V.BUNDLE_CLEAR))
    sheet = os.path.join(UP, "ORDER_SHEET_%s.txt" % V.VERSION)
    if not os.path.exists(sheet):
        allf.append("order sheet missing")
    print("\n  SELF-TEST - plant each defect, require the check to reject it:")
    st = selftest()
    for what, ok in st:
        print("      %-36s %s" % (what, "rejected" if ok else "NOT REJECTED"))
        if not ok:
            allf.append("self-test: %s was not rejected" % what)
    print("\n  %s" % ("ALL CHECKS PASS" if not allf else "%d FAILURE(S)" % len(allf)))
    return 0 if not allf else 1


if __name__ == "__main__":
    sys.exit(main())
