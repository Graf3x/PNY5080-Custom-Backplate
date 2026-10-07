"""v94 (2026-09-04): the SKINS grow feet and carry the cover; the carcass rides.

WHY (in the owner's words): the skins are the show piece, and SendCutSend will
not powder coat a part under 1.000 in (25.4 mm) wide. The v93 skin blank is
14.50 mm. The owner's own sketch: fold the bottom of the skin UNDER, fasten
that to the backplate, stop using tape on the feet, and let the carcass stand
on top of the skins' feet - "if we stacked it on top of the show walls that's
fine".

WHAT WAS CHECKED BEFORE BUILDING IT THIS WAY
    The carcass CANNOT take its own screwed inward feet as well. A screw needs
    5.99 + 2.9 + 2.0 = 10.9 mm of flat past its bend, a 12.4 mm formed foot,
    and a return flange on a 12.5 wall breaks the vendor's return <= half its
    base rule - the exact rule that turned the v93 feet outward. So the
    carcass has NO feet. It is a hat with no brim: roof, walls, end cap, ten
    folds, standing on the skins' feet, bonded to the skins' inner faces with
    the same 2.30 mm VHB that already carried the skins in v93. The screws are
    in the SKIN feet.
    SendCutSend countersinks only 0.125 in and thicker, so the plate's holes
    are plain 2.90 clearance and the owner countersinks them from the BACK by
    hand after coating - six to ten holes, hidden under the heads.
    A foot that stops short of the part's end is a partial-width flange and
    needs a bend relief cut PAST the fold into the wall: 2.0 wide, 3.47 deep.
    Those reliefs sit on the bottom edge of the show face, one at each end of
    every foot piece. They are the one visible cost of this design, and they
    are counted and drawn, not hidden.

THE STACK, plate outer face = z 0, bare metal unless said
    plate 2.00 + coat 0.15            2.15   skin foot's underside sits here
    skin foot 2.00 + coat 0.15        4.30   carcass wall stands here (+coat)
    carcass wall 12.50 (v93 down_oml) 16.95  roof top (metal), coat above
    skin wall, foot underside to top edge:   16.95 - 2.15 = 14.80 formed
    bundle clear: roof underside 14.95 - floor 4.30 = 10.65 >= CABLE_D 10.5

THE SKIN, one part, one L-section strip with four 45 deg folds
    wall  14.80 formed (13.325 flat, free top edge)
    foot  15.50 formed from the skin's OUTER face, tip 3.10 from the centre;
          the two sides' tips are 6.20 apart, the bundle lies on the feet
    flat  27.35 mm = 1.077 in, over the powder line's 1.000
    feet are cut back FOLD_CLEAR (5.99 + 0.05) from each 45 deg fold mark so
    a standing foot is outside the die when the wall is folded; they stop
    over the connector notch, the die window, the card washers and the plate
    edge; each piece carries one or two tapped M2.5 holes at plan radius
    SCREW_R from the route's centreline, 5.99 clear of the foot's bend in
    the flat and >= 2.0 of web to the tip.

NOT CHANGED from v93: the route, the plate outline and bores, the vent
fields' lattice, the carcass top face and its reliefs, the roof vents, the
end cap's width, the skin's position (CARCASS_RIB_IN/OUT), the tape between
skin and carcass wall.
"""

from __future__ import annotations

import math
import os
import sys

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backplate_v3 as B                                     # noqa: E402
import cover_ribbon as RB                                    # noqa: E402
from config import HARDWARE as HWc, MFG                      # noqa: E402
from hole_pattern import HOLES                               # noqa: E402

VERSION = "v94"
T = RB.T                          # 2.0
BD = RB.BEND_DEDUCT               # 2.95, the vendor's 90 deg deduction
RAD = RB.BEND_RADIUS              # 0.97 inside
BA = 2.0 * (RAD + T) - BD         # 2.99 bend allowance, consistent with BD
KEEP = RB.BEND_KEEPOUT            # 5.99 half die, flat-pattern rule
COAT = MFG.COAT_ALLOWANCE         # 0.15 per surface
MINF = MFG.MIN_FEATURE            # 2.0
RELIEF_W = RB.RELIEF_W            # 2.0
RELIEF_DEPTH = RB.RELIEF_DEPTH    # 3.47
CORNER_GAP = RB.CORNER_GAP        # 0.40
POWDER_MIN_W = 25.4               # SendCutSend: minimum width for powder, 1 in
MIN_FLANGE = RB.FOOT_MIN_FORMED   # 7.95 formed, 0.080 in 5052 at 90 deg

# ---- the stack ---------------------------------------------------------------
PLATE_T = RB.PLATE_T                          # 2.0
Z_PLATE = PLATE_T + COAT                      # 2.15  skin foot underside
Z_FOOT_TOP = Z_PLATE + T + COAT               # 4.30  coated top of the skin foot
Z_CARC = Z_FOOT_TOP + COAT                    # 4.45  carcass wall's bottom edge, metal
CARC_WALL = RB.CLEAR_D + T                    # 12.5  v93 down_oml, unchanged
Z_ROOF_TOP = Z_CARC + CARC_WALL               # 16.95 roof top, metal
Z_ROOF_UNDER = Z_ROOF_TOP - T                 # 14.95
BUNDLE_CLEAR = Z_ROOF_UNDER - Z_FOOT_TOP      # 10.65 >= 10.5
assert BUNDLE_CLEAR >= RB.CLEAR_D - 1e-9

# ---- the skin ---------------------------------------------------------------
SKIN_OUT = RB.CARCASS_RIB_OUT                 # 18.6 outer face, as v93
SKIN_IN = RB.CARCASS_RIB_IN                   # 16.6 inner face, as v93
SKIN_MID = SKIN_IN + T / 2.0                  # 17.6 developed on the mid surface
SKIN_WALL = Z_ROOF_TOP - Z_PLATE              # 14.80 formed, foot underside to top
SKIN_WALL_FLAT = SKIN_WALL - BD / 2.0         # 13.325 (one bend, free top edge)
SKIN_FOOT = 15.5                              # formed, from the OUTER face
SKIN_FOOT_FLAT = SKIN_FOOT - BD / 2.0         # 14.025
SKIN_FLAT_H = SKIN_WALL_FLAT + SKIN_FOOT_FLAT  # 27.35
FOOT_TIP = SKIN_OUT - SKIN_FOOT               # 3.1 from the centreline
FOOT_FLAT_START = SKIN_OUT - (RAD + T)        # 15.63: where the foot goes flat
assert SKIN_FLAT_H >= POWDER_MIN_W
assert SKIN_FOOT >= MIN_FLANGE and SKIN_WALL >= MIN_FLANGE
FOLD_CLEAR = KEEP + 0.05                      # foot cut back from each 45 fold mark
# WHERE THERE IS NO FOOT THE WALL HANGS TO THE PLATE. A free edge cut level
# with the fold mark ends up BA/2 short of the bend's tangent, 1.5 mm above
# the plate - v93 met the same thing on the carcass (down_flat_free). So the
# footless stretches, the fold gaps included, carry the wall BD/2 deeper,
# less 0.30 so the coated edge clears the coated plate.
FREE_DROP = BD / 2.0 - 0.30                   # 1.175

# ---- the screws -------------------------------------------------------------
SCREW = "M2.5 x 0.45"
SCREW_LEN = 4.0                               # flat head; plate 2 + foot 2, flush tip
SCREW_HEAD = 4.7                              # 90 deg flat head, countersunk BY HAND
CLEAR_HOLE = 2.9                              # in the plate, opened for powder
TAP_DRILL = 2.05                              # in the skin foot; the vendor taps
SCREW_R = 8.0                                 # plan radius of the screw line
SCREW_END = 7.0                               # first/last screw this far from a piece end
SCREW_PITCH = 12.0                            # two only if this far apart
BORE_CLEAR = RB.SCREW_BORE_CLEAR              # 8.0 from every card bore (hardware.py)
FOOT_SEG_MIN = 2 * SCREW_END                  # a piece must hold at least one screw
# in the FLAT, from the foot's fold mark down: BA/2 to the tangent, then the
# formed distance from FOOT_FLAT_START in to the screw line
SCREW_FLAT = BA / 2.0 + (FOOT_FLAT_START - SCREW_R)       # 9.125
assert SCREW_FLAT - TAP_DRILL / 2.0 >= KEEP, "tap inside the bend keep-out"
assert SKIN_FOOT_FLAT - SCREW_FLAT - TAP_DRILL / 2.0 >= MINF, "no web to the tip"

# ---- the carcass ------------------------------------------------------------
CAP_OML = Z_ROOF_TOP - Z_PLATE - 0.30         # 14.5: hangs to 0.30 over the coated plate
CAP_FLAT = CAP_OML - BD / 2.0                 # 13.025

# ---- keep-outs on the plate, for the feet --------------------------------------
NOTCH_CLEAR = RB.FOOT_NOTCH_CLEAR             # 1.0
EDGE_CLEAR = 1.0                              # foot stays this far inside the plate


def path():
    return RB.route45()


def _leg(pth, i):
    (ax, ay), (bx, by) = pth[i], pth[i + 1]
    L = math.hypot(bx - ax, by - ay) or 1.0
    return (ax, ay), (bx, by), L, ((bx - ax) / L, (by - ay) / L)


def _normal(u, sgn):
    """Outward normal of side sgn for travel direction u (RB's convention)."""
    return (u[1] * sgn, -u[0] * sgn)


# ============================================================================
# THE CARCASS: v93's blank with no feet and a longer end cap
# ============================================================================
def _cap_flap(pth, d):
    """The end cap, hanging CAP_OML to the plate (the walls stop 2 mm short,
    on the skin feet; the cap is where there are no feet)."""
    (ax, ay), (bx, by), L, (ux, uy) = _leg(pth, 0)
    ox, oy = -ux, -uy
    ex, ey = uy, -ux
    f1 = d["fold1"]
    w = RB.CARCASS_RIB_IN - RB.END_CAP_CLEAR
    df = CAP_FLAT
    rd = RELIEF_DEPTH
    ax0, ay0 = ax + ox * RB.END_CAP_Y, ay + oy * RB.END_CAP_Y

    def P(s, t):
        return (ax0 + ex * s + ox * t, ay0 + ey * s + oy * t)
    ring = [P(-f1, 0.0), P(f1, 0.0), P(f1, rd), P(w, rd), P(w, df),
            P(-w, df), P(-w, rd), P(-f1, rd)]
    return dict(kind="endcap", sgn=0, leg=0, poly=Polygon(ring))


_CARC = {}


def carcass_blank(pth=None, roof_vents=True):
    """(top, flaps): v93's carcass_blank with FOOT_SIDES emptied - every wall
    is a plain footless downstand - and the end cap rebuilt to CAP_FLAT.
    The relief notches come out of RB.relief_notches exactly as before."""
    pth = path() if pth is None else pth
    key = bool(roof_vents)
    if key in _CARC:
        return _CARC[key]
    saved = (RB.FOOT_SIDES, RB.END_CAP)
    try:
        RB.FOOT_SIDES = {}
        RB.END_CAP = False
        top, flaps = RB.carcass_blank(pth, roof_vents=False)
    finally:
        RB.FOOT_SIDES, RB.END_CAP = saved
    d = RB.carcass_dev()
    flaps = [f for f in flaps if f["kind"] == "downstand"]
    flaps.append(_cap_flap(pth, d))
    if roof_vents:
        g = roof_cells()
        if g is not None and not g.is_empty:
            top = top.difference(g)
    _CARC[key] = (top, flaps)
    return top, flaps


# ============================================================================
# THE SKIN: L-section strip, feet in pieces, tapped
# ============================================================================
def skin_dev(sgn, pth=None):
    """Flat width and fold marks - v93's development, the skin has not moved."""
    pth = path() if pth is None else pth
    return RB.carcass_ribbon(sgn, pth, flush=True)


def flat_to_plan(sgn, x, pth=None):
    """A flat x on the skin -> (plan point on the mid surface, travel dir), or
    None inside a bend allowance."""
    import export_solids as ES
    pth = path() if pth is None else pth
    mid = RB.offset(pth, SKIN_MID, sgn)
    return ES._plan_at(mid, pth, x)


def _obstacles():
    """Where a foot may NOT lie: the connector notch, the die window, the card
    washers, and outside the plate. All buffered."""
    from die_window import POLY as DIE
    obs = [RB.notch_box().buffer(NOTCH_CLEAR), Polygon(DIE).buffer(EDGE_CLEAR)]
    wr = HWc.WASHER_OD / 2.0 + COAT + NOTCH_CLEAR
    obs += [Point(x, y).buffer(wr) for x, y, _t, _s in HOLES]
    plate = Polygon(B.outline()).buffer(-EDGE_CLEAR)
    return unary_union(obs), plate


def _foot_segment_plan(sgn, x, pth):
    """The folded foot's footprint at flat x: a line from the outer face in to
    the tip, in plan. None inside a bend."""
    q = flat_to_plan(sgn, x, pth)
    if q is None:
        return None, None
    (px, py), (ux, uy) = q
    nx, ny = _normal((ux, uy), sgn)
    a = (px + nx * (SKIN_OUT - SKIN_MID), py + ny * (SKIN_OUT - SKIN_MID))
    b = (px + nx * (FOOT_TIP - SKIN_MID), py + ny * (FOOT_TIP - SKIN_MID))
    return LineString([a, b]), ((px, py), (ux, uy))


def foot_pieces(sgn, pth=None):
    """[(x0, x1, leg)] in the skin's flat mm: between the fold cut-backs, off
    every obstacle, at least FOOT_SEG_MIN long."""
    pth = path() if pth is None else pth
    r = skin_dev(sgn, pth)
    w, folds = r["flat"], r["folds"]
    ob, plate = _obstacles()
    out = []
    n = len(folds) + 1
    for i in range(n):
        lo = folds[i - 1] + FOLD_CLEAR if i > 0 else 0.0
        hi = folds[i] - FOLD_CLEAR if i < n - 1 else w
        step = 0.25
        xs, ok = [], []
        x = lo
        while x <= hi + 1e-9:
            seg, _q = _foot_segment_plan(sgn, min(x, hi), pth)
            good = (seg is not None and not seg.intersects(ob)
                    and plate.contains(seg))
            xs.append(min(x, hi)); ok.append(good)
            x += step
        k = 0
        while k < len(xs):
            if not ok[k]:
                k += 1
                continue
            j = k
            while j + 1 < len(xs) and ok[j + 1]:
                j += 1
            x0 = xs[k] if k == 0 else xs[k] + step        # one step of margin
            x1 = xs[j] if j == len(xs) - 1 else xs[j] - step
            if x1 - x0 >= FOOT_SEG_MIN:
                out.append((x0, x1, i))
            k = j + 1
    return out


def _taper(sgn, i, at_start, pth):
    """Tip taper where two folded feet converge at a fold: the flap on the
    OUTSIDE of the turn points its foot at the turn's centre."""
    tn, ang = RB.turns(pth), RB.deflections(pth)
    k = i - 1 if at_start else i
    if k < 0 or k >= len(tn):
        return 0.0
    if tn[k] * sgn <= 0:
        return 0.0                                  # feet splay: nothing to trim
    reach = SKIN_MID - FOOT_TIP                     # from the fold axis to the tip
    return max(0.0, RB.folded_corner_trim(ang[k], reach) - FOLD_CLEAR)


def foot_screws(sgn, pth=None):
    """[(flat x, plan (px, py), piece index)] - one or two per piece, slid off
    the card bores."""
    pth = path() if pth is None else pth
    out = []
    for pi, (x0, x1, leg) in enumerate(foot_pieces(sgn, pth)):
        lo, hi = x0 + SCREW_END, x1 - SCREW_END
        if hi < lo:
            continue
        wants = [lo, hi] if hi - lo >= SCREW_PITCH else [(lo + hi) / 2.0]

        def plan(x):
            _seg, q = _foot_segment_plan(sgn, x, pth)
            if q is None:
                return None
            (px, py), (ux, uy) = q
            nx, ny = _normal((ux, uy), sgn)
            return (px + nx * (SCREW_R - SKIN_MID), py + ny * (SCREW_R - SKIN_MID))

        def ok(x):
            p = plan(x)
            return p is not None and all(
                math.hypot(p[0] - hx, p[1] - hy) >= BORE_CLEAR for hx, hy, _t, _s in HOLES)
        for want in wants:
            best = None
            for k in range(0, 200):
                for x in (want + 0.25 * k, want - 0.25 * k):
                    if lo - 1e-9 <= x <= hi + 1e-9 and ok(x):
                        best = x
                        break
                if best is not None:
                    break
            if best is None:
                continue
            if out and out[-1][2] == pi and abs(best - out[-1][0]) < SCREW_PITCH:
                continue
            out.append((best, plan(best), pi))
    return out


def _piece_tapers(sgn, x0, x1, leg, r, pth):
    """(e0, e1): tip tapers at the piece's ends that sit on a fold cut-back."""
    folds = r["folds"]
    at0 = leg > 0 and abs(x0 - (folds[leg - 1] + FOLD_CLEAR)) < 0.3
    at1 = leg < len(folds) and abs(x1 - (folds[leg] - FOLD_CLEAR)) < 0.3
    return (_taper(sgn, leg, True, pth) if at0 else 0.0,
            _taper(sgn, leg, False, pth) if at1 else 0.0)


def skin_outline(sgn, pth=None):
    """The blank in its flat frame: x along the strip, y up; the foot fold at
    y = 0, wall above to SKIN_WALL_FLAT, feet below to -SKIN_FOOT_FLAT; a
    relief slot RELIEF_W x RELIEF_DEPTH into the wall at every foot end that
    is not the strip's end."""
    pth = path() if pth is None else pth
    r = skin_dev(sgn, pth)
    w = r["flat"]
    g = box(0.0, -FREE_DROP, w, SKIN_WALL_FLAT)
    reliefs = []
    for x0, x1, leg in foot_pieces(sgn, pth):
        e0, e1 = _piece_tapers(sgn, x0, x1, leg, r, pth)
        foot = Polygon([(x0, 0.0), (x1, 0.0),
                        (x1 - e1, -SKIN_FOOT_FLAT), (x0 + e0, -SKIN_FOOT_FLAT)])
        g = g.union(foot)
        # RELIEF at each end that is inside the strip: the fold dies here
        for xe, sg in ((x0, -1.0), (x1, +1.0)):
            if xe <= 1e-6 or xe >= w - 1e-6:
                continue
            xa, xb = (xe - RELIEF_W, xe) if sg < 0 else (xe, xe + RELIEF_W)
            # THROUGH THE FREE EDGE. Drawn from y = -1.0 the slot stopped
            # 0.175 above the wall's deeper free edge (-FREE_DROP) and became
            # an enclosed hole with a sliver under it - the gate's thinnest
            # metal read 0.175 mm and "no relief" at every foot end.
            reliefs.append(box(xa, -FREE_DROP - 1.0, xb, RELIEF_DEPTH))
    if reliefs:
        g = g.difference(unary_union(reliefs))
    g = g.buffer(0)
    if g.geom_type != "Polygon":
        raise ValueError("skin %d: outline is not one piece" % sgn)
    return g


def skin_holes(sgn, pth=None):
    """Tap-drill holes in the flat: (x, y) with y = -SCREW_FLAT."""
    return [(x, -SCREW_FLAT) for x, _p, _pi in foot_screws(sgn, pth)]


def plate_holes(pth=None):
    """Every cover screw through the plate: [(x, y)] in plate coordinates."""
    pth = path() if pth is None else pth
    return [p for sgn in (RB.SHOW, RB.FAR) for _x, p, _pi in foot_screws(sgn, pth)]


def folded_feet(sgn, pth=None):
    """Each foot piece as it lies on the plate: [(piece, plan polygon)]."""
    pth = path() if pth is None else pth
    out = []
    r = skin_dev(sgn, pth)
    for pi, (x0, x1, leg) in enumerate(foot_pieces(sgn, pth)):
        e0, e1 = _piece_tapers(sgn, x0, x1, leg, r, pth)
        pts = []
        for x, rr in ((x0, SKIN_OUT), (x1, SKIN_OUT), (x1 - e1, FOOT_TIP), (x0 + e0, FOOT_TIP)):
            q = flat_to_plan(sgn, x, pth)
            (px, py), (ux, uy) = q
            nx, ny = _normal((ux, uy), sgn)
            pts.append((px + nx * (rr - SKIN_MID), py + ny * (rr - SKIN_MID)))
        out.append((pi, Polygon(pts).buffer(0)))
    return out


# ============================================================================
# THE PLATE: v93 outline and bores, no slots, no taps, clearance for the skins
# ============================================================================
_FIELD = {}


def plate_field():
    """vent_kit's expanded field with THIS cover's hardware kept out (the
    clearance holes, at MIN_WEB) and nothing else: no tab slots, no feet on
    the plate's face."""
    if "f" in _FIELD:
        return _FIELD["f"]
    import hardware as HW
    import vent_kit as K
    holes = plate_holes()
    saved = HW.holes

    def fake(path=None):
        return [dict(part="backplate", kind="clearance", d=CLEAR_HOLE, at=p,
                     joint="skin %d" % i, geom=None) for i, p in enumerate(holes)]
    try:
        HW.holes = fake
        f = K.expanded_field(x0=K.INSET)[0]
    finally:
        HW.holes = saved
    _FIELD["f"] = f
    return f


_ROOF = {}


def roof_cells():
    """The roof's vents on the plate field's lattice, as vent_ocr.roof_cells
    does it, but on THIS carcass's top face (its reliefs differ)."""
    if "g" in _ROOF:
        return _ROOF["g"]
    import vent_kit as K
    import vent_ocr as VO
    pth = path()
    d = RB.carcass_dev()
    top, _flaps = carcass_blank(pth, roof_vents=False)
    inner = d["fold1"] - KEEP
    a = RB.offset(pth, inner, RB.SHOW)
    b = RB.offset(pth, inner, RB.FAR)
    band = Polygon(a + b[::-1]).buffer(0)
    (ax, ay), (bx, by), L, (ux, uy) = _leg(pth, 0)
    k = KEEP
    endkeep = Polygon([(ax + uy * 40, ay - ux * 40), (ax - uy * 40, ay + ux * 40),
                       (ax - uy * 40 + ux * k, ay + ux * 40 + uy * k),
                       (ax + uy * 40 + ux * k, ay - ux * 40 + uy * k)])
    rf = band.intersection(top.buffer(-K.MIN_WEB)).difference(endkeep)
    fn = dict(VO.DESIGNS)[VO.ROOF_DESIGN]
    cells = fn(rf, origin_field=plate_field())
    keep = [c for c in cells if not c.is_empty and rf.contains(c) and c.area >= 3.0]
    g = K.enforce(unary_union(keep), max(MINF, K.MIN_WEB))[0] if keep else None
    _ROOF["g"] = g
    return g


def plate_vents(design_name):
    import vent_ocr as VO
    fn = dict(VO.DESIGNS)[design_name]
    return VO.build_one(fn, plate_field())


# ============================================================================
# REPORT
# ============================================================================
def summary(pth=None):
    pth = path() if pth is None else pth
    out = dict(version=VERSION, stack=dict(z_plate=Z_PLATE, z_foot_top=Z_FOOT_TOP,
               z_carc=Z_CARC, z_roof_top=Z_ROOF_TOP, bundle_clear=BUNDLE_CLEAR),
               skin=dict(wall=SKIN_WALL, foot=SKIN_FOOT, flat_h=SKIN_FLAT_H,
                         tip=FOOT_TIP, screw_r=SCREW_R, screw_flat=SCREW_FLAT))
    for sgn, lab in ((RB.SHOW, "show"), (RB.FAR, "far")):
        r = skin_dev(sgn, pth)
        pcs = foot_pieces(sgn, pth)
        scr = foot_screws(sgn, pth)
        g = skin_outline(sgn, pth)
        minx, miny, maxx, maxy = g.bounds
        reliefs = sum(1 for x0, x1, _l in pcs for xe in (x0, x1)
                      if 1e-6 < xe < r["flat"] - 1e-6)
        out[lab] = dict(flat=r["flat"], folds=r["folds"], pieces=pcs,
                        screws=len(scr), reliefs=reliefs,
                        extents=(maxx - minx, maxy - miny))
    top, flaps = carcass_blank(pth)
    out["carcass"] = dict(folds=len(flaps), walls=sum(1 for f in flaps if f["kind"] == "downstand"),
                          roof_cells=len(top.interiors))
    return out


if __name__ == "__main__":
    import json
    s = summary()
    print(json.dumps(dict((k, v) for k, v in s.items() if k != "show" and k != "far"), indent=1))
    for lab in ("show", "far"):
        d = s[lab]
        print("%s skin: flat %.2f x %.2f, folds %s" % (lab, d["flat"], d["extents"][1],
              ", ".join("%.1f" % f for f in d["folds"])))
        for x0, x1, leg in d["pieces"]:
            print("   foot leg %d  x %.2f..%.2f  (%.1f mm)" % (leg, x0, x1, x1 - x0))
        print("   %d screws, %d relief slots" % (d["screws"], d["reliefs"]))
