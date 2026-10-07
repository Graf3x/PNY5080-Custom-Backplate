"""Every part, every variant, as DXFs a vendor can actually cut.

WHY THIS EXISTS
    out/production/ held five files dated 11 August: a backplate with NO VENTS
    in it, and a cable channel from an architecture abandoned twice over. No
    carcass, no skins, no notch cap, no per-variant export. The design was
    finished and the manufacturing files did not exist.

WHAT COMES OUT, into out/production/
    backplate_<design>.dxf      outline, die window, 13 fastener holes, relief
                                slots, the vent field, and the cover's own
                                hardware - clearance, tab slots, tapped
    carcass.dxf                 flat pattern: top face, downstands, feet, with
                                every fold on the BEND layer
    skin_show_<h>.dxf           flat strip, folds on BEND
    skin_far_<h>.dxf
    notch_cap.dxf

LAYERS
    CUT     everything the laser follows
    BEND    fold lines, for the press brake. Never cut these.
    NOTES   text, ignored by the machine

TAPPED HOLES are drawn at the TAP DRILL diameter (1.65 mm) on their own layer
and called out in the notes. They are under the 2.0 mm laser minimum on
purpose: the vendor drills and taps them, they are not cut features.
"""

from __future__ import annotations

import math
import os
import sys

from shapely.geometry import Polygon as _SPoly
import ezdxf
from shapely.geometry import Point, Polygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backplate_v3 as B                                     # noqa: E402
import cover_ribbon as RB                                    # noqa: E402
import hardware as HW                                        # noqa: E402
import vent_ocr as VO                                        # noqa: E402
from config import HARDWARE, MFG                             # noqa: E402
from die_window import POLY as DIE_POLY                      # noqa: E402
from hole_pattern import HOLES                               # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out",
                   "production")
STOCK = "2 mm (0.080 in) 5052-H32  |  RAL 9003 gloss white powder coat"


def _doc():
    d = ezdxf.new("R2010", setup=True)
    d.units = ezdxf.units.MM
    # BEND is split by DIRECTION. route45 turns right, right, left, left, so a
    # skin bonded to one side folds one way at the first two corners and the
    # other way at the last two. Four bare LINEs on one layer and a note reading
    # "45/45/45/45" tells a brake operator nothing, and folding all four the
    # same way scraps the one part that is the finished visible surface.
    for name, col in (("CUT", 7), ("BEND", 5), ("BEND_UP", 3),
                      ("BEND_DOWN", 6), ("BEND_UP_45", 3), ("BEND_DOWN_45", 6),
                      ("BEND_UP_90", 3), ("BEND_DOWN_90", 6),
                      ("TAP", 1), ("NOTES", 4)):
        # SENDCUTSEND READS BEND LINES BY LINETYPE, NOT BY LAYER (2026-09-03).
        # Their DXF rule: "bends should be indicated with a dashed line - not
        # Hidden". These were continuous lines on layers named BEND_*, which
        # their app took for cut paths: a line has no width, so carcass.dxf
        # failed "minimum width 0.248 in", and the shortest fold, 4.00 mm,
        # failed "minimum length 0.373 in". The layer names stay - the gates
        # read direction and angle from them - and the lines go dashed.
        d.layers.add(name, color=col,
                     linetype="DASHED" if name.startswith("BEND") else "Continuous")
    return d, d.modelspace()


def _destitch(poly, tol=1e-3):
    """Drop vertices a micron apart, and the collinear ones between them.

    A union leaves stitches: sixteen segments in the carcass ring were under
    a micron long. They cut nothing - the beam is 0.2 mm wide - but they are
    noise in a file a person has to read, they make a vertex count meaningless
    as a check, and a CAM post that tries to honour them can stall on a
    zero-length move. Nothing here moves an edge: only vertices that are
    already indistinguishable from their neighbour, or already on the line
    between them, are removed.
    """
    from shapely.geometry import Polygon

    def clean(ring):
        out = []
        for p in ring:
            if out and math.dist(out[-1], p) < tol:
                continue
            out.append(p)
        while len(out) > 3 and math.dist(out[0], out[-1]) < tol:
            out.pop()
        keep = []
        n = len(out)
        for i in range(n):
            a, b, c = out[i - 1], out[i], out[(i + 1) % n]
            ux, uy = b[0] - a[0], b[1] - a[1]
            vx, vy = c[0] - b[0], c[1] - b[1]
            lu, lv = math.hypot(ux, uy), math.hypot(vx, vy)
            if lu < tol or lv < tol:
                continue
            cross = abs(ux * vy - uy * vx) / (lu * lv)
            if cross < 1e-9 and (ux * vx + uy * vy) > 0:
                continue                      # dead straight, no information
            # AND NO FURTHER. I tried dropping vertices whose triangle with
            # their neighbours was under a thousandth of a square millimetre,
            # to clear a 0.041 mm step on the notch cap. On a traced profile
            # that is sixty near-collinear vertices, not one, and the area
            # guard below rejected the whole pass every time - so the rule
            # never fired once and only looked like coverage. Removed. The
            # cap's shortest segment is 0.041 mm, a fifth of the kerf, and
            # the beam cannot express it either way.
            keep.append(b)
        return keep

    def despur(ring):
        """Drop zero-width spikes: a vertex you arrive at and leave along the
        SAME line. Two panel corners meeting at a point make the union grow a
        spur - here a 24.8 mm one - and a spur has no area, so nothing that
        measures area sees it. It also cuts nothing: a zero-width slit is not
        a thing a 0.2 mm beam can make. But it is a real degeneracy in the
        file, it trips the retrace guard, and some CAM tools choke on it.
        Removing it changes no area and no edge.
        """
        changed = True
        while changed and len(ring) > 3:
            changed = False
            n = len(ring)
            for i in range(n):
                a, b, c = ring[i - 1], ring[i], ring[(i + 1) % n]
                ux, uy = b[0] - a[0], b[1] - a[1]
                vx, vy = c[0] - b[0], c[1] - b[1]
                lu, lv = math.hypot(ux, uy), math.hypot(vx, vy)
                if lu < tol or lv < tol:
                    continue
                cs = (ux * vx + uy * vy) / (lu * lv)
                if cs < -0.999999:
                    del ring[i]
                    changed = True
                    break
        return ring

    def settle(ring):
        """clean() until it stops changing. Area-neutral, nothing more.

        ONE PASS IS NOT ENOUGH: dropping a vertex makes its neighbours
        collinear with each other, so a single pass leaves collinear points
        behind. Everything here is AREA-NEUTRAL by construction.

        AND NOTHING MORE THAN THAT. The merged corner reliefs leave a
        four-tooth sawtooth of 0.163 mm segments at each corner - alternating
        turn directions, confirmed by measurement - and a 0.2 mm beam cannot
        render a 0.163 mm tooth either way. I tried removing them twice, and
        both times the removal changed area enough to trip the guard below,
        which then reverted the WHOLE clean-up and left the file dirtier than
        if I had not tried. The teeth stay. They cut nothing, the thinnest
        metal on this part is 2.45 mm, and they are 16 vertices in 120.
        """
        prev = None
        while prev != len(ring):
            prev = len(ring)
            ring = despur(clean(ring))
        return ring

    ext = settle(list(poly.exterior.coords)[:-1])
    ins = [settle(list(r.coords)[:-1]) for r in poly.interiors]
    out = Polygon(ext, [q for q in ins if len(q) >= 3])
    if not out.is_valid or abs(out.area - poly.area) > 1e-4:
        return poly                            # never trade validity for tidy
    return out


def _finish(doc, path):
    """Save the annotated drawing, and an upload copy with no text on it.

    THE NOTES ARE OUTSIDE THE PART. They have to be - over the geometry they
    would be unreadable - but a quoting system reads what is in the file, and
    with the notes in it the notch cap measures 167.9 x 60.9 mm for a
    43.7 x 38.5 part, and a tall skin 199.6 x 71.0 for a 199.6 x 17.0 one.

    So the annotated file keeps its notes for a person and a stripped copy
    goes to upload/ with nothing in it but the part. The upload copy is made
    by DELETING text from the saved file, never by regenerating it, so the two
    cannot drift apart.

    I also tried setting $EXTMIN/$EXTMAX to the cut geometry. ezdxf resets
    them to its invalid sentinel on every save, by design - it does not
    maintain extents and leaves the reader to recompute - so that code did
    nothing at all, which is the same failure as any other rule that never
    fires. Removed. zoom.extents() is the supported call and it does stick:
    the file opens framed on the part.
    """
    from ezdxf import zoom
    import ezdxf as _ez
    zoom.extents(doc.modelspace())
    doc.saveas(path)

    up = os.path.join(os.path.dirname(path), "upload")
    os.makedirs(up, exist_ok=True)
    doc2 = _ez.readfile(path)
    m2 = doc2.modelspace()
    for e in list(m2):
        if e.dxf.layer == "NOTES":
            m2.delete_entity(e)
    zoom.extents(m2)
    doc2.saveas(os.path.join(up, os.path.basename(path)))
    return path


def _poly(msp, geom, layer="CUT"):
    """Write a polygon to a layer, de-stitched.

    EVERY part, not just the carcass. The notch cap had a 0.04 mm leg at a
    corner and the vent fields carry the same kind of debris - all of it left
    by booleans, none of it cuttable, all of it noise in a file a person has
    to read. _destitch refuses to change area or validity, so this cannot
    quietly reshape a part.
    """
    gs = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    n = 0
    for g in gs:
        g = _destitch(g)
        msp.add_lwpolyline(list(g.exterior.coords)[:-1], close=True,
                           dxfattribs={"layer": layer})
        n += 1
        for r in g.interiors:
            msp.add_lwpolyline(list(r.coords)[:-1], close=True,
                               dxfattribs={"layer": layer})
            n += 1
    return n


def _notes(msp, lines, x=5.0, y=-8.0, h=3.2):
    for i, t in enumerate(lines):
        msp.add_text(t, height=h, dxfattribs={"layer": "NOTES"}
                     ).set_placement((x, y - i * (h + 1.6)))


# THE TWO PLATES THIS BUILD EMITS. release_gate reads this rather
# than a second copy of the names - typing them twice already cost
# one silent lookup failure.
PLATES = ("Interference / Graf3X, OCR", "Bit Plane / Graf3X, OCR")


def backplate(design_name):
    doc, msp = _doc()
    pts = B.outline()
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "CUT"})
    msp.add_lwpolyline(DIE_POLY, close=True, dxfattribs={"layer": "CUT"})

    closed, slotted = B.classify()
    for x, y, _t, _s in closed:
        msp.add_circle((x, y), B.BORE / 2.0, dxfattribs={"layer": "CUT"})
    for sl in B.relief_slots():
        msp.add_lwpolyline(list(sl.exterior.coords), close=True,
                           dxfattribs={"layer": "CUT"})

    fn = dict(VO.DESIGNS)[design_name]
    vents, _dropped = VO.build_one(fn, VO.plate_field())
    n_vent = _poly(msp, vents, "CUT")

    n_clear = n_slot = n_tap = 0
    _slot_lengths = []
    for h in HW.holes():
        if h["part"] != "backplate":
            continue
        if h["kind"] == "slot":
            _poly(msp, h["geom"], "CUT")
            n_slot += 1
            # THE MINIMUM ROTATED RECTANGLE, not the axis-aligned bounds.
            # Five of these slots lie at 45 deg and their bounding box is
            # (L + W) / sqrt(2) - the note read 11.03 mm for a 12.80 slot.
            r = list(h["geom"].minimum_rotated_rectangle.exterior.coords)
            e = [math.dist(r[i], r[i + 1]) for i in range(4)]
            _slot_lengths.append(max(e))
        elif h["kind"] == "clearance":
            msp.add_circle(h["at"], h["d"] / 2.0, dxfattribs={"layer": "CUT"})
            n_clear += 1
        else:
            msp.add_circle(h["at"], h["d"] / 2.0, dxfattribs={"layer": "TAP"})
            n_tap += 1

    _notes(msp, [
        "BACKPLATE  -  %s" % design_name.replace(", OCR", ""),
        STOCK,
        "OUTSIDE face, viewed from outside.  %.1f x %.1f mm" % (B.L, B.H),
        "%d vents  |  %d card fasteners dia %.1f  |  %d slots"
        % (n_vent, len(closed), B.BORE, len(slotted)),
        # THE SLOTS ARE NOT ALL ONE SIZE. Five of the nine are lengthened
        # where the tab crosses a fold, and quoting the nominal made the
        # drawing disagree with its own geometry.
        "COVER HARDWARE: %d clearance dia %.2f, %d tab slots %s x %.2f,"
        % (n_clear, HW.CLEAR_D, n_slot,
           " / ".join("%.2f" % v for v in
                      sorted(set(round(q, 2) for q in _slot_lengths))),
           RB.SLOT_W),
        "  %d TAPPED %s on layer TAP - drill+tap, do NOT laser"
        % (n_tap, RB.SCREW),
        "DIE WINDOW is a real traced profile - do not simplify",
    ])
    p = os.path.join(OUT, "backplate_%s.dxf"
                     % design_name.split("/")[0].strip().lower().replace(" ", "_"))
    _finish(doc, p)
    return p, dict(vents=n_vent, clear=n_clear, slots=n_slot, tap=n_tap)


def _degeneracies(poly):
    """Zero-length edges and zero-width spurs in a ring.

    A union of panels that touch at a POINT grows a spur: the boundary runs
    out along a line and straight back. It has no area, so nothing that
    measures area sees it; it cuts nothing, because a 0.2 mm beam cannot make
    a zero-width slit; and it is the reason a blank suddenly "retraces itself"
    when some other dimension moves half a millimetre.

    Cleaning it up AFTERWARDS does not work - removing a spur can leave a ring
    shapely calls invalid, and the tidy-up then refuses the whole result and
    silently changes nothing, which is what was happening. The fix belongs at
    the weld: count them, and let _weld walk on to a snap grid that does not
    produce any.
    """
    bad = 0
    gs = [poly] if poly.geom_type == "Polygon" else list(poly.geoms)
    for g in gs:
        for ring in [g.exterior] + list(g.interiors):
            r = list(ring.coords)[:-1]
            n = len(r)
            for i in range(n):
                a, b, c = r[i - 1], r[i], r[(i + 1) % n]
                ux, uy = b[0] - a[0], b[1] - a[1]
                vx, vy = c[0] - b[0], c[1] - b[1]
                lu, lv = math.hypot(ux, uy), math.hypot(vx, vy)
                if lu < 1e-9 or lv < 1e-9:
                    bad += 1
                    continue
                if (ux * vx + uy * vy) / (lu * lv) < -0.999999:
                    bad += 1
    return bad


def _weld(parts):
    """Union coincident-edged parts into ONE contour, choosing the snap grid.

    Returns the welded polygon, or raises with what each grid produced so the
    failure says which seam did not close rather than just a count.
    """
    from shapely.ops import unary_union
    from shapely import set_precision
    exact = unary_union(parts)
    tried = []
    for grid in (0.0, 1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3):
        g = [set_precision(q, grid) for q in parts] if grid else list(parts)
        u = unary_union(g)
        n = 1 if u.geom_type == "Polygon" else len(u.geoms)
        moved = abs(u.area - exact.area)
        deg = _degeneracies(u) if n == 1 else 99
        tried.append((grid, n, moved, deg))
        if n == 1 and not u.interiors and moved < 1e-3 and not deg:
            return u
    lines = ["    grid %-8g -> %d contour(s), area moved %.2e, "
             "%d degeneracies" % t for t in tried]
    raise RuntimeError("carcass blank will not weld into one contour:"
                       + "\n" + "\n".join(lines))


def carcass(path):
    doc, msp = _doc()
    top, flaps = RB.carcass_blank(path)
    # SNAP BEFORE UNIONING. The relief-trimmed flap edges are collinear with
    # the top face's edge only to about 1e-14 mm, so GEOS declines to dissolve
    # them: the union came back as FIVE closed contours, with 26% of the blank
    # cut clean off along its own fold line, and the main ring retracing itself
    # down three more folds as zero-width slits.
    #
    # AND THE GRID IS NOT A CONSTANT. A hard-coded 1e-6 worked until a route
    # change moved one seam onto a rounding boundary, whereupon snapping
    # SEPARATED two flaps that touch exactly - 1e-7 and 1e-5 were both fine and
    # 1e-6 alone was not. Walk a ladder instead and take the first grid that
    # welds the blank into one contour without moving any edge more than a
    # tenth of a micron of area. A magic number that happens to work is not the
    # same thing as a correct one.
    blank = _destitch(_weld([_SPoly(top.exterior)] + [f["poly"] for f in flaps]))
    # THE ROOF HAS OPENINGS NOW - the plate's vent pattern continues across
    # it. The weld wants one ring, so it gets the top face's EXTERIOR; the
    # roof's openings are cut as their own contours after it, like the
    # plate's.
    roof_holes = [_SPoly(r) for r in top.interiors]
    n = _poly(msp, blank, "CUT")
    if n != 1:
        raise RuntimeError(
            "carcass blank must be ONE contour, got %d - the flaps have come "
            "away from the top face" % n)
    n_roof = sum(_poly(msp, h, "CUT") for h in roof_holes)
    # the far feet's screw clearance holes, on CUT
    n_screw = 0
    for f in flaps:
        for (bx_, by_), _plan in f.get("screws", []):
            msp.add_circle((bx_, by_), RB.FOOT_SCREW_CLEAR / 2.0,
                           dxfattribs={"layer": "CUT"})
            n_screw += 1
    ring = list(blank.exterior.coords)[:-1]
    for i in range(len(ring)):
        ax, ay = ring[i - 1]; bx, by = ring[i]; cx, cy = ring[(i + 1) % len(ring)]
        u = (bx - ax, by - ay); v = (cx - bx, cy - by)
        lu = (u[0] ** 2 + u[1] ** 2) ** .5; lv = (v[0] ** 2 + v[1] ** 2) ** .5
        if lu < 1e-9 or lv < 1e-9:
            continue
        cs = (u[0] * v[0] + u[1] * v[1]) / (lu * lv)
        if cs < -0.999:
            raise RuntimeError(
                "carcass blank retraces itself at (%.3f, %.3f) - a zero-width "
                "slit down a fold line" % (bx, by))

    dv = RB.carcass_dev()
    # THE FOLD LINES COME FROM THE FLAPS, not from a second derivation.
    # This block used to recompute every relief trim itself, with the single
    # pre-per-flap depth, and it fell out of step twice: once when relief was
    # sized per flap, and again when the foot picked up its own convex-corner
    # trim - which left 2.148 mm of BEND line running along a CUT edge, a
    # fold line drawn across fresh air. A flap's attachment edge IS its fold
    # line: it is the first edge of the polygon carcass_blank built.
    folds = 0
    for f in flaps:
        c = list(f["poly"].exterior.coords)
        # A HAT, NOT A C. The top-to-wall folds turn DOWN; the wall-to-foot
        # folds now turn the OTHER way, the foot going OUT, so they go on
        # BEND_UP_90. This is the line the brake reads; the wrong layer here
        # folds the feet into the channel and rebuilds the return lip.
        lay = "BEND_UP_90" if f["kind"] == "foot" else "BEND_DOWN_90"
        msp.add_line(c[0], c[1], dxfattribs={"layer": lay, "linetype": "DASHED"})
        folds += 1
    # a hat's two bends turn the SAME way - top face down to the wall, wall in
    # to the foot - so the carcass is all one sense, unlike the skins.

    tapped = 0          # nothing tapped in the carcass; the plate is tapped
    _screws = n_screw

    _notes(msp, [
        "CARCASS  -  cover: top face, downstands, feet",
        STOCK,
        "%d contours on CUT, %d folds: walls on BEND_DOWN_90, feet on BEND_UP_90, all %.0f deg, THE"
        % (n, folds, 90.0),
        "  SAME WAY: top face down to the wall, wall in to the foot.",
        "FEET BOND WITH %s," % RB.FOOT_TAPE,
        "  a strip along each of the five. NOT the skins' 2.30 mm VHB: the",
        "  tab engagement is PLATE_T - tape, so anything over 2.00 mm lifts",
        "  the cover until no tab reaches its slot.",
        "%d x dia %.2f clearance in the FAR feet for %s button heads; the SHOW"
        % (_screws, RB.FOOT_SCREW_CLEAR, RB.FOOT_SCREW),
        "  clear of the 5.99 bend keep-out AND lets a 22 x 6 cable past.",
        "Developed section %.2f mm at every station: a foot on ONE side"
        % dv["flat_staggered"],
        "  and a free downstand on the other. The feet are STAGGERED, so",
        "  the both-feet figure of %.2f mm occurs nowhere on this blank."
        % dv["flat"],
        "Folds at %.3f and %.3f from the centreline."
        % (dv["fold1"], dv["fold2"]),
        "DATUM FACE: the blank is drawn OUTSIDE-UP, and every fold goes",
        "  AWAY from the reader. Folded the other way the feet point",
        "  outward and nothing lands on the plate.",
        "Corner gaps are RELIEF, sized per corner from angle and flap depth.",
        "They are required: at 1.60 mm the flat pattern overlapped itself.",
    ], y=RB.PATH[0][1] - 14)
    p = os.path.join(OUT, "carcass.dxf")
    _finish(doc, p)
    return p, dict(contours=n, folds=folds, tapped=tapped, roof=n_roof)


def skin(path, sgn, flush):
    doc, msp = _doc()
    r = RB.carcass_ribbon(sgn, path, flush=flush)
    w, h = r["flat"], r["height"]
    tabs = RB.skin_tabs(sgn, path)
    # the outline, with a locating tab dropped below y=0 at each station
    # THE ONE OUTLINE: body, tabs, and the bottom edge stepped up over every
    # outward foot. See cover_ribbon.skin_outline.
    pts = list(RB.skin_outline(sgn, flush, path).exterior.coords)[:-1]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "CUT"})
    # folds come from the SAME development as the width - never re-walked
    tn = RB.turns(path)
    dirs = []
    for k, f in enumerate(r["folds"]):
        # NO sgn FACTOR. Both skins are offsets of the SAME route, so both
        # polylines turn the same way in plan - [-1,-1,+1,+1] for each - and
        # both blanks are unrolled the same way, walking the route, with no
        # mirror. So the same fold mark must produce the same plan turn and
        # the two files must carry the SAME sequence.
        #
        # Multiplying by sgn made them opposite. It is the right test for
        # whether a skin's OUTSIDE face is on the inside of a bend, which is
        # what "concave" means - but that is not what a fold mark encodes when
        # both blanks are laid out identically. Folded as drawn, both far skins
        # came out mirror-image and their tabs landed up to 12.4 mm out.
        lay = RB.fold_layer(tn[k], r["angles"][k])
        dirs.append((f, r["angles"][k], lay.split("_")[1]))
        msp.add_line((f, 0), (f, h), dxfattribs={"layer": lay, "linetype": "DASHED"})
    lab = "SHOW" if sgn == RB.SHOW else "FAR"
    _notes(msp, [
        "SKIN, %s SIDE  -  %s facade" % (lab, "flush" if flush else "tall"),
        STOCK,
        # THE BLANK, INCLUDING THE TABS. This quoted the body height and the
        # blank is 2.00 mm taller, because the tabs hang below y=0 - the same
        # note says so three lines further down. The order sheet measured the
        # file and got it right, so the drawing and the sheet disagreed by
        # 2.00 mm on all four skins.
        "%.2f x %.2f mm blank (%.2f body + %.2f of tab below y=0). %d folds,"
        % (w, h + RB.PLATE_T, h, RB.PLATE_T, len(r["angles"])),
        "  all FULL WIDTH - no relief needed.",
        "FOLD SCHEDULE, from x=0, with the blank lying AS DRAWN:",
        "  UP  = the run turns RIGHT here.  DOWN = it turns LEFT.",
        "  Same sense as the carcass: UP is toward the reader of this",
        "  view, DOWN is away from it.",
        "  " + " | ".join("%.1f mm %s %.1f deg" % (f, d, a)
                          for f, a, d in dirs),
        "  The LAYER NAME carries both: BEND_UP_45 / BEND_DOWN_45.",
        "  The uploaded copy has no text on it, so the layer name is the",
        "  whole instruction - direction and angle.",
        "  THEY ARE NOT ALL THE SAME WAY - the route turns both ways.",
        "NO HOLES. This face is the finished surface - nothing is cut into it.",
        "%d locating TABS %.1f x %.1f below y=0, into slots in the backplate."
        % (len(tabs), RB.TAB_L, RB.PLATE_T),
        "A tab is outline, not a hole - which is why it is allowed here.",
        "TAPE BAND: %.2f to %.2f mm up the INSIDE face, %.2f wide. The wall"
        % (RB.BEND_RADIUS + RB.T, RB.ZP - (RB.BEND_RADIUS + RB.T) - RB.Z0,
           RB.ZP - 2 * (RB.BEND_RADIUS + RB.T) - RB.Z0),
        "  behind it is flat only between its own two bend radii; lower down",
        "  the gap opens to 5.27 mm and the tape carries nothing.",
    ], y=-8.0)
    p = os.path.join(OUT, "skin_%s_%s.dxf"
                     % (lab.lower(), "flush" if flush else "tall"))
    _finish(doc, p)
    return p, dict(flat=w, height=h, folds=len(r["angles"]))


def notch_cap(path):
    doc, msp = _doc()
    cap = RB.notch_cap(path)["cap"]
    n = _poly(msp, cap, "CUT")
    for at in RB.cap_screws(path):
        msp.add_circle(at, HW.CLEAR_D / 2.0, dxfattribs={"layer": "CUT"})
    _notes(msp, [
        "NOTCH CAP  -  laps BEHIND the backplate",
        STOCK,
        "%d contours, %d clearance dia %.2f" % (n, len(RB.cap_screws(path)),
                                                HW.CLEAR_D),
        "Its face sits 2.00 mm below the backplate's, by design.",
    ], y=-8.0)
    p = os.path.join(OUT, "notch_cap.dxf")
    _finish(doc, p)
    return p, dict(contours=n)


def build():
    os.makedirs(OUT, exist_ok=True)
    # blocker 15: five superseded DXFs from 9-11 August sat alongside the new
    # ones, including a full-size backplate with no vent field in it. Uploading
    # the folder wholesale would have quoted and cut the wrong parts.
    import glob, shutil
    arch = os.path.join(OUT, "..", "archive")
    stale = [f for f in glob.glob(os.path.join(OUT, "*"))
             if os.path.basename(f) in (
                 "backplate_PROD.dxf", "cable_channel_bent.dxf",
                 "cable_channel_bent.png", "cable_channel_metal.dxf",
                 "cable_channel_metal.png", "cable_lid.png",
                 "cable_lid_PROD.dxf", "production.png", "shroud_PROD.dxf")]
    if stale:
        os.makedirs(arch, exist_ok=True)
        for f in stale:
            shutil.move(f, os.path.join(arch, os.path.basename(f)))
        print("  archived %d superseded files" % len(stale))
    path = RB.route45()
    made = []
    print("PRODUCTION  -  %s\n" % STOCK)
    for name in PLATES:
        p, st = backplate(name)
        made.append(p)
        print("  %-34s %d vents, %d clear, %d slots, %d tapped"
              % (os.path.basename(p), st["vents"], st["clear"], st["slots"],
                 st["tap"]))
    p, st = carcass(path)
    made.append(p)
    print("  %-34s %d contours, %d folds, %d tapped"
          % (os.path.basename(p), st["contours"], st["folds"], st["tapped"]))
    for flush in RB.ordered_facades():
        for sgn in (RB.SHOW, RB.FAR):
            p, st = skin(path, sgn, flush)
            made.append(p)
            print("  %-34s %.2f x %.2f, %d folds"
                  % (os.path.basename(p), st["flat"], st["height"], st["folds"]))
    # AND TAKE THE OTHER FACADE OUT OF THE FOLDER. A DXF that is not in the
    # order must not sit next to the ones that are - upload/ is what gets
    # zipped and sent.
    for flush in (False, True):
        if flush in RB.ordered_facades():
            continue
        for lab in ("show", "far"):
            nm = "skin_%s_%s.dxf" % (lab, "flush" if flush else "tall")
            for f in (os.path.join(OUT, nm), os.path.join(OUT, "upload", nm)):
                if os.path.exists(f):
                    os.remove(f)
                    print("  %-34s removed - not in the order" % nm)
    if RB.CAP_IN_ORDER:
        p, st = notch_cap(path)
        made.append(p)
        print("  %-34s %d contours" % (os.path.basename(p), st["contours"]))
    else:
        print("  notch cap                          NOT IN THE ORDER - the "
              "cover covers 100% of the notch,")
        print("                                     the cap would hand back "
              "3.85 of the 4.00 mm adapter")
        print("                                     relief, and 3.60 mm of "
              "cap and screw head do not fit")
        print("                                     a 2.40 mm standoff gap.")
    # THE ORDER SHEET IS REGENERATED WITH THE FILES, not maintained
    # beside them. A sheet that can go stale against the geometry it
    # describes is worse than no sheet at all.
    import make_order_sheet as _OS
    with open(os.path.join(OUT, "upload", "ORDER_SHEET.txt"), "w",
              encoding="utf-8") as _fh:
        _fh.write(_OS.report() + chr(10))
    print("  upload/ORDER_SHEET.txt             material, finish, quantities")

    # AND WHICH ARTEFACTS ARE CURRENT. out/ holds 150 files across three
    # superseded architectures; eight come from this build, and two of the
    # stale ones are named like templates you would print.
    import make_manifest as _MF
    with open(os.path.join(OUT, "..", "WHAT_IS_CURRENT.txt"), "w",
              encoding="utf-8") as _fh:
        _fh.write(_MF.report() + chr(10))
    print("  ../WHAT_IS_CURRENT.txt             which build aids are this design")

    # THE STOP TRAVELS WITH THE FOLDER. upload/ is self-contained and
    # send-ready by design - DXFs plus an order sheet - and the DO_NOT_CUT
    # notice sat one directory up, where nobody zipping the send-ready folder
    # would see it. Copied in while it exists, removed with it.
    _stop = os.path.join(OUT, "DO_NOT_CUT.txt")
    _upstop = os.path.join(OUT, "upload", "DO_NOT_CUT.txt")
    if os.path.exists(_stop):
        with open(_stop, encoding="utf-8") as _a,                 open(_upstop, "w", encoding="utf-8") as _b:
            _b.write(_a.read())
        print("  upload/DO_NOT_CUT.txt              the stop, travelling with "
              "the files")
    elif os.path.exists(_upstop):
        os.remove(_upstop)

    print("\n  %d files in %s" % (len(made), os.path.normpath(OUT)))
    return made


if __name__ == "__main__":
    build()
