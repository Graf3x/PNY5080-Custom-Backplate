"""v94 production files: out/production_v94/ (annotated) and its upload/ copies.

    backplate_interference_v94.dxf   v93 plate, no tab slots, no taps, plus the
    backplate_bit_plane_v94.dxf      skins' clearance holes on CUT
    carcass_v94.dxf                  hat with no brim: roof, 9 walls, end cap
    skin_show_v94.dxf                L-section strip: wall, foot pieces, taps
    skin_far_v94.dxf
    ORDER_SHEET_v94.txt
"""

from __future__ import annotations

import math
import os
import sys

from shapely.geometry import Polygon as _SPoly

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backplate_v3 as B                                     # noqa: E402
import cover_ribbon as RB                                    # noqa: E402
import make_production as MP                                 # noqa: E402
import v94 as V                                              # noqa: E402
from die_window import POLY as DIE_POLY                      # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out",
                   "production_v94")
STOCK = MP.STOCK.replace("gloss", "gloss or matte")
PLATES = MP.PLATES


def _plate_name(design_name):
    return "backplate_%s_%s.dxf" % (
        design_name.split("/")[0].strip().lower().replace(" ", "_"), V.VERSION)


def backplate(design_name):
    doc, msp = MP._doc()
    msp.add_lwpolyline(B.outline(), close=True, dxfattribs={"layer": "CUT"})
    msp.add_lwpolyline(DIE_POLY, close=True, dxfattribs={"layer": "CUT"})
    closed, _slotted = B.classify()
    for x, y, _t, _s in closed:
        msp.add_circle((x, y), B.BORE / 2.0, dxfattribs={"layer": "CUT"})
    for sl in B.relief_slots():
        msp.add_lwpolyline(list(sl.exterior.coords), close=True,
                           dxfattribs={"layer": "CUT"})
    vents, _dropped = V.plate_vents(design_name)
    n_vent = MP._poly(msp, vents, "CUT")
    holes = V.plate_holes()
    for p in holes:
        msp.add_circle(p, V.CLEAR_HOLE / 2.0, dxfattribs={"layer": "CUT"})
    MP._notes(msp, [
        "BACKPLATE %s  -  %s" % (V.VERSION, design_name.replace(", OCR", "")),
        STOCK,
        "OUTSIDE face, viewed from outside.  %.1f x %.1f mm" % (B.L, B.H),
        "%d vents  |  %d card fasteners dia %.1f  |  NO slots, NO taps"
        % (n_vent, len(closed), B.BORE),
        "COVER HARDWARE: %d clearance dia %.2f for %s flat heads, driven"
        % (len(holes), V.CLEAR_HOLE, V.SCREW),
        "  from the BACK and countersunk BY HAND (90 deg) after coating -",
        "  the vendor does not countersink 0.080 in. The skins' feet are tapped.",
        "DIE WINDOW is a real traced profile - do not simplify",
    ])
    p = os.path.join(OUT, _plate_name(design_name))
    MP._finish(doc, p)
    return p, dict(vents=n_vent, clear=len(holes))


def carcass(pth):
    doc, msp = MP._doc()
    top, flaps = V.carcass_blank(pth)
    blank = MP._destitch(MP._weld([_SPoly(top.exterior)] + [f["poly"] for f in flaps]))
    n = MP._poly(msp, blank, "CUT")
    if n != 1:
        raise RuntimeError("carcass blank must be ONE contour, got %d" % n)
    n_roof = sum(MP._poly(msp, _SPoly(r), "CUT") for r in top.interiors)
    folds = 0
    for f in flaps:
        c = list(f["poly"].exterior.coords)
        msp.add_line(c[0], c[1], dxfattribs={"layer": "BEND_DOWN_90", "linetype": "DASHED"})
        folds += 1
    dv = RB.carcass_dev()
    MP._notes(msp, [
        "CARCASS %s  -  roof, walls, end cap. NO FEET." % V.VERSION,
        STOCK,
        "%d contours on CUT (%d roof vents), %d folds, all BEND_DOWN_90, all"
        % (n + n_roof, n_roof, folds),
        "  the same way: roof down to the walls, roof down to the end cap.",
        "It STANDS ON THE SKINS' FEET (2 mm up) and is BONDED to the skins'",
        "  inner faces with %s." % RB.BOND_TAPE,
        "Walls hang %.2f from the fold to a free edge; the end cap %.2f."
        % (dv["down_flat_free"], V.CAP_FLAT),
        "Folds at %.3f from the centreline." % dv["fold1"],
        "DATUM FACE: drawn OUTSIDE-UP; every fold goes AWAY from the reader.",
        "Corner gaps are RELIEF, sized per corner from angle and flap depth.",
    ], y=RB.PATH[0][1] - 14)
    p = os.path.join(OUT, "carcass_%s.dxf" % V.VERSION)
    MP._finish(doc, p)
    return p, dict(contours=n + n_roof, folds=folds, roof=n_roof)


def skin(pth, sgn):
    doc, msp = MP._doc()
    r = V.skin_dev(sgn, pth)
    g = V.skin_outline(sgn, pth)
    MP._poly(msp, g, "CUT")
    tn = RB.turns(pth)
    dirs = []
    # the four 45 deg folds, the full height of the wall (deep edge included)
    for k, f in enumerate(r["folds"]):
        lay = RB.fold_layer(tn[k], r["angles"][k])
        dirs.append((f, r["angles"][k], lay.split("_")[1]))
        msp.add_line((f, -V.FREE_DROP), (f, V.SKIN_WALL_FLAT),
                     dxfattribs={"layer": lay, "linetype": "DASHED"})
    # the foot folds: one per piece, INWARD = away from the reader
    pieces = V.foot_pieces(sgn, pth)
    for x0, x1, _leg in pieces:
        msp.add_line((x0, 0.0), (x1, 0.0),
                     dxfattribs={"layer": "BEND_DOWN_90", "linetype": "DASHED"})
    holes = V.skin_holes(sgn, pth)
    for x, y in holes:
        msp.add_circle((x, y), V.TAP_DRILL / 2.0, dxfattribs={"layer": "TAP"})
    lab = "SHOW" if sgn == RB.SHOW else "FAR"
    minx, miny, maxx, maxy = g.bounds
    MP._notes(msp, [
        "SKIN %s, %s SIDE  -  L-section: wall + feet" % (V.VERSION, lab),
        STOCK,
        "%.2f x %.2f mm blank: wall %.3f above the foot fold, feet %.3f below."
        % (maxx - minx, maxy - miny, V.SKIN_WALL_FLAT, V.SKIN_FOOT_FLAT),
        "  Formed: wall %.2f, foot %.2f from the outer face, tip %.2f from the"
        % (V.SKIN_WALL, V.SKIN_FOOT, V.FOOT_TIP),
        "  route centreline. The wall's free stretches hang %.3f deeper." % V.FREE_DROP,
        "FOLDS: %d x 45 deg across the strip (layer = direction + angle) and"
        % len(r["angles"]),
        "  %d x 90 deg foot folds on BEND_DOWN_90 (INWARD, away from the reader)." % len(pieces),
        "  45 deg schedule from x=0: " + " | ".join("%.1f %s" % (f, d) for f, a, d in dirs),
        "%d TAPPED %s on layer TAP (drill %.2f) - drill+tap, do NOT laser."
        % (len(holes), V.SCREW, V.TAP_DRILL),
        "Relief slots %.1f x %.2f at every foot end - required, a foot is a"
        % (V.RELIEF_W, V.RELIEF_DEPTH),
        "  partial-width flange. The fold gaps are %.2f each side of a 45 fold." % V.FOLD_CLEAR,
        "NO other holes in the face.",
    ], y=-V.SKIN_FOOT_FLAT - 8.0)
    p = os.path.join(OUT, "skin_%s_%s.dxf" % (lab.lower(), V.VERSION))
    MP._finish(doc, p)
    return p, dict(w=maxx - minx, h=maxy - miny, folds=len(r["angles"]) + len(pieces),
                   taps=len(holes))


def order_sheet(stats):
    s = V.summary()
    L = []
    L.append("PG147 COVER - ORDER SHEET %s  (%s)" % (V.VERSION, "SendCutSend"))
    L.append("")
    L.append("MATERIAL  5052-H32 aluminium, 0.080 in (2.0 mm), all five parts.")
    L.append("FINISH    powder coat RAL 9003 signal white, matte or gloss - the")
    L.append("          same on all five. Every part is now over the 1 in powder")
    L.append("          minimum: skins %.2f mm (%.3f in) wide in the flat."
             % (V.SKIN_FLAT_H, V.SKIN_FLAT_H / 25.4))
    L.append("QUANTITY  1 of each: %s" % ", ".join(sorted(os.path.basename(p) for p in stats)))
    L.append("")
    L.append("LAYERS    CUT = laser.  BEND_UP_45 / BEND_DOWN_45 / BEND_DOWN_90 =")
    L.append("          dashed fold lines, direction + angle in the name. UP =")
    L.append("          toward the reader of the file. TAP = drill + tap, not laser.")
    L.append("")
    L.append("BACKPLATES  2, interchangeable. %d x dia %.2f clearance for the"
             % (len(V.plate_holes()), V.CLEAR_HOLE))
    L.append("          cover screws, on CUT. No slots, no taps. The owner")
    L.append("          countersinks these from the BACK by hand after coating")
    L.append("          (90 deg, %s flat head) - the vendor countersinks" % V.SCREW)
    L.append("          0.125 in and thicker only.")
    L.append("")
    L.append("CARCASS   one piece, %d folds, all 90 deg, all BEND_DOWN_90: nine"
             % s["carcass"]["folds"])
    L.append("          walls and the end cap, all away from the reader. NO feet.")
    L.append("          %d roof vents on CUT. It stands on the skins' feet and is"
             % s["carcass"]["roof_cells"])
    L.append("          bonded to the skins with %s." % RB.BOND_TAPE)
    L.append("")
    for lab in ("show", "far"):
        d = s[lab]
        L.append("SKIN %-4s  %.2f x %.2f mm flat. 4 x 45 deg folds (two each way) +"
                 % (lab.upper(), d["flat"], d["extents"][1]))
        L.append("          %d foot folds at 90 deg on BEND_DOWN_90, INWARD. %d tapped"
                 % (len(d["pieces"]), d["screws"]))
        L.append("          %s on layer TAP. %d relief slots %.1f x %.2f on the"
                 % (V.SCREW, d["reliefs"], V.RELIEF_W, V.RELIEF_DEPTH))
        L.append("          bottom edge, one at each foot end - required.")
    L.append("")
    L.append("ASSEMBLY  1. Countersink the plate's %d holes from the back." % len(V.plate_holes()))
    L.append("          2. Stand each skin on the plate, feet inward, and drive")
    L.append("             %s x %.0f flat heads from the back into the feet." % (V.SCREW, V.SCREW_LEN))
    L.append("          3. Apply %s to the skins' inner faces," % RB.BOND_TAPE)
    L.append("             drop the carcass in between them onto the feet, press.")
    L.append("          Stack: plate %.2f + skin foot %.2f (+coats) = carcass wall"
             % (V.PLATE_T, V.T))
    L.append("          bottom at %.2f; roof top at %.2f; cable clear height %.2f."
             % (V.Z_CARC, V.Z_ROOF_TOP, V.BUNDLE_CLEAR))
    L.append("HARDWARE  %d x %s x %.0f mm flat head (90 deg), stainless or black."
             % (len(V.plate_holes()), V.SCREW, V.SCREW_LEN))
    return chr(10).join(L)


def build():
    os.makedirs(os.path.join(OUT, "upload"), exist_ok=True)
    pth = V.path()
    made = []
    print("PRODUCTION %s  -  %s\n" % (V.VERSION, STOCK))
    for name in PLATES:
        p, st = backplate(name)
        made.append(p)
        print("  %-34s %d vents, %d clearance" % (os.path.basename(p), st["vents"], st["clear"]))
    p, st = carcass(pth)
    made.append(p)
    print("  %-34s %d contours, %d folds, %d roof vents"
          % (os.path.basename(p), st["contours"], st["folds"], st["roof"]))
    for sgn in (RB.SHOW, RB.FAR):
        p, st = skin(pth, sgn)
        made.append(p)
        print("  %-34s %.2f x %.2f, %d folds, %d taps"
              % (os.path.basename(p), st["w"], st["h"], st["folds"], st["taps"]))
    sheet = os.path.join(OUT, "upload", "ORDER_SHEET_%s.txt" % V.VERSION)
    with open(sheet, "w", encoding="utf-8") as fh:
        fh.write(order_sheet(made) + chr(10))
    print("  %-34s order sheet" % os.path.basename(sheet))
    return made


if __name__ == "__main__":
    build()
