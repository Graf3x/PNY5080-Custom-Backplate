"""The order sheet: everything a vendor needs that a geometry-only DXF cannot say.

The files in out/production/upload carry no text, on purpose - notes outside a
part inflate the envelope a quoting system reads, and the notch cap's drawing
measured 167.9 x 60.9 mm for a 43.7 x 38.5 part. What a stripped DXF still has
to convey it conveys in the LAYER NAMES: CUT, BEND_UP_45, BEND_DOWN_90, TAP.

Everything else - material, temper, thickness, finish, quantities, which
variant to order, and what each part is - belongs on a sheet like this one,
because it belongs in the order form rather than in the geometry.
"""

from __future__ import annotations

import collections
import os

import ezdxf

import cover_ribbon as RB
from config import MFG

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "out", "production")
UPLOAD = os.path.join(OUT, "upload")

WHAT = {
    "backplate_interference.dxf":
        "backplate, Interference vent design - PICK ONE OF THE TWO BACKPLATES",
    "backplate_bit_plane.dxf":
        "backplate, Bit Plane vent design - PICK ONE OF THE TWO BACKPLATES",
    "carcass.dxf":
        "cable-cover carcass: top face, two downstands, five staggered feet",
    "skin_show_tall.dxf":
        "show-side skin, TALL facade (stands 2.5 mm proud of the top face)",
    "skin_far_tall.dxf":
        "far-side skin, TALL facade",
    "skin_show_flush.dxf":
        "show-side skin, FLUSH facade (level with the top face)",
    "skin_far_flush.dxf":
        "far-side skin, FLUSH facade",
}

CHOOSE = """  FLUSH facade, decided. The tall skins are not in this order and their
  DXFs are not in this folder. Both backplates ARE in the order - they are
  interchangeable, and the choice between them is made at assembly."""


def rows():
    out = []
    for fn in sorted(os.listdir(UPLOAD)):
        if not fn.endswith(".dxf"):
            continue
        d = ezdxf.readfile(os.path.join(UPLOAD, fn))
        msp = d.modelspace()
        xs, ys = [], []
        for e in msp:
            if e.dxftype() == "LWPOLYLINE":
                for p in e.get_points():
                    xs.append(p[0])
                    ys.append(p[1])
        bends = collections.Counter(e.dxf.layer for e in msp
                                    if e.dxftype() == "LINE")
        taps = sum(1 for e in msp if e.dxf.layer == "TAP")
        tabs = 0
        for e in msp:
            if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "CUT":
                ring = [(q[0], q[1]) for q in e.get_points()]
                lo = min(q[1] for q in ring)
                if lo < -1e-6:
                    tabs += sum(1 for q in ring if abs(q[1] - lo) < 1e-6) // 2
        out.append(dict(file=fn, w=max(xs) - min(xs), h=max(ys) - min(ys),
                        bends=dict(bends), taps=taps, tabs=tabs,
                        what=WHAT.get(fn, "")))
    return out


def report():
    L = []
    L.append("ORDER SHEET  -  PNY RTX 5080 backplate and cable cover")
    L.append("")
    L.append("MATERIAL   2.0 mm (0.080 in) 5052-H32 aluminium, every part")
    L.append("FINISH     powder coat, RAL 9003 gloss white, every part,")
    L.append("           both faces. The design allows %.2f mm per surface."
             % MFG.COAT_ALLOWANCE)
    L.append("FILES      out/production/upload/*.dxf - geometry only, no text.")
    L.append("           The annotated drawings in the parent directory are")
    L.append("           for reading, not for cutting: their notes sit outside")
    L.append("           the part and would be quoted as part of the envelope.")
    L.append("")
    L.append("LAYERS     CUT          the profile and every opening")
    L.append("           BEND_UP_nn   fold toward the reader of the file, nn deg")
    L.append("           BEND_DOWN_nn fold away from the reader, nn deg")
    L.append("           TAP          drill and tap - NOT to be lasered")
    L.append("")
    L.append("PARTS")
    for r in rows():
        L.append("  %-28s %7.2f x %-7.2f mm   qty 1" % (r["file"], r["w"], r["h"]))
        if r["what"]:
            L.append("      %s" % r["what"])
        if r["bends"]:
            L.append("      bends: %s"
                     % ", ".join("%d on %s" % (v, k)
                                 for k, v in sorted(r["bends"].items())))
        if r["taps"]:
            L.append("      %d tapped features on layer TAP" % r["taps"])
    L.append("")
    L.append("CHOICES TO MAKE BEFORE ORDERING")
    L.append("  The two backplates are alternative vent designs. Order ONE.")
    L.append(CHOOSE)
    L.append("")
    L.append("NOT IN THIS ORDER")
    L.append("  The notch cap was designed and then dropped: the cover covers")
    L.append("  100% of the connector notch on its own, the cap would hand")
    L.append("  back 3.85 of the 4.00 mm of adapter relief, and 3.60 mm of cap")
    L.append("  plus screw head does not fit a 2.40 mm standoff gap.")
    L.append("")
    L.append("ASSEMBLY, so the bend directions can be sanity-checked")
    # "TWICE PER SIDE" IS THE BOTH-FEET SECTION, which occurs nowhere: the
    # feet are staggered one per station, so a cross-section has two folds on
    # one side and one on the other. The sheet's own parts table says 15.
    # THE FOOT ADHESIVE WAS IN NO DOCUMENT THAT REACHES THE BENCH. It was
    # chosen and reasoned about at length - 9473PC over 468MP, for wet-out on
    # powder's orange peel - and that decision lived in a developer follow-up
    # list and in DO_NOT_CUT.txt, which the process has a person DELETE before
    # the parts are ordered. Meanwhile the one adhesive the assembler was
    # given, in the sentence next to "the feet are BONDED", was the skins'
    # 2.30 mm VHB. Substituting it is not a tolerance problem: tab engagement
    # is exactly PLATE_T - t, so 2.30 mm of tape leaves the tab tips 0.30 mm
    # PROUD of the plate, no tab enters its slot and no foot touches.
    L.append("TWO DIFFERENT ADHESIVES, and they are not interchangeable:")
    L.append("")
    L.append("  FEET, SHOW SIDE ->  3M VHB Adhesive Transfer Tape 9473PC,")
    L.append("  BACKPLATE           0.25 mm (10 mil), 100MP acrylic, no carrier.")
    L.append("                      A strip along each of the THREE show-side")
    L.append("                      feet (legs 2, 3, 4; 8.0 mm feet).")
    L.append("  FEET, FAR SIDE ->   NO tape. Screwed: %d x %s x 4 mm button"
             % (len(RB.carcass_fasteners()), RB.FOOT_SCREW))
    L.append("  BACKPLATE           head, through dia %.2f clearance holes in"
             % RB.FOOT_SCREW_CLEAR)
    L.append("                      the 12.5 mm far feet (legs 0, 1), into the")
    L.append("                      plate's TAP holes (drill %.2f, tapped by"
             % RB.FOOT_SCREW_TAP)
    L.append("                      the vendor, layer TAP, %d per plate). Heads"
             % len(RB.carcass_fasteners()))
    L.append("                      sit on the foot's lip outside the skin.")
    L.append("                      The taped side sits 0.25 mm higher than the")
    L.append("                      screwed side: 0.6 deg across the cover.")
    L.append("                      Tab engagement is PLATE_T - tape, so this")
    L.append("                      bond line must stay UNDER 2.00 mm or the")
    L.append("                      tabs never reach their slots. 0.25 leaves")
    L.append("                      1.75 mm of tab in a 2.30 mm slot.")
    L.append("")
    L.append("  SKIN -> WALL        %s," % RB.BOND_TAPE)
    L.append("                      on the band described on each skin drawing.")
    L.append("                      NOT under the feet: 2.30 mm there lifts the")
    L.append("                      whole cover off the plate.")
    L.append("")
    L.append("  Both faces of every bond are powder coated. Wipe with IPA.")
    L.append("  The owner intends to stack the FOOT tape if adhesion wants it:")
    L.append("  that is fine on the feet - each 0.25 mm layer takes 0.25 mm off")
    L.append("  the tab engagement (1.75 -> 1.50 -> 1.25 mm) and lifts the cover")
    L.append("  the same amount. Do NOT stack the SKIN tape: a second 2.30 mm")
    L.append("  layer moves the show skin 2.30 mm outward and puts it 1.49 mm")
    L.append("  INTO the card washer at (171.28, 32.02).")
    L.append("")
    _nw, _nf, _ne = RB.carcass_fold_counts()
    L.append("  CARCASS: one piece, %d folds, all 90 deg. The %d WALL folds and"
             % (_nw + _nf + _ne, _nw))
    L.append("  the END CAP at the plug end turn DOWN (BEND_DOWN_90); the %d" % _nf)
    L.append("  FOOT folds turn the OTHER way, OUT (BEND_UP_90): a HAT with a")
    L.append("  closed plug end. Leg 4 has NO far-side wall: the one the")
    L.append("  geometry gave was a 4.0 x 11.0 mm stub, dropped (WALL_SEG_MIN);")
    L.append("  the far skin covers that stretch. Bend lines are DASHED lines")
    L.append("  on the BEND_* layers, as SendCutSend's DXF rule wants.")
    L.append("  closed plug end. Feet flat on the plate")
    L.append("  outside the walls, under the skins, one foot per station on the")
    L.append("  outside of each turn. Fold the feet FIRST, then the walls. The")
    L.append("  whole 24 mm channel is clear for the cable; each foot shows")
    L.append("  3.4 mm beyond its skin, by design (7.95 mm minimum flange).")
    _scr = RB.carcass_fasteners()
    L.append("  SHOW-side feet are BONDED to the backplate; FAR-side feet are")
    L.append("  SCREWED, %d x %s into tapped holes in the plate (TAP layer,"
             % (len(_scr), RB.FOOT_SCREW))
    L.append("  %.2f mm drill), %.2f mm clearance holes in the feet."
             % (RB.FOOT_SCREW_TAP, RB.FOOT_SCREW_CLEAR))
    L.append("  Each skin folds four times, TWICE EACH WAY, and bonds to the")
    L.append("  outside of a carcass wall with %s;" % RB.BOND_TAPE)
    # COUNTED, NOT ASSERTED. This read "its nine tabs" - nine is the PAIR
    # total; the show skins carry four and the far skins five. It was the one
    # number on this sheet that was a literal rather than a measurement, and
    # it was the one number that was wrong.
    nt = {r["file"]: r["tabs"] for r in rows()}
    # WHERE THE TAPE GOES, which existed nowhere. The wall's outer face is
    # only FLAT between its two bend radii, and on a footed leg the lower bend
    # eats 2.97 mm more. One tape width and one placement have to work on both
    # kinds of leg, and the obvious thing - lay it on the skin's bottom edge,
    # the only visible datum - puts half of it over a void that opens to
    # 5.57 mm on every footed span.
    _r = RB.BEND_RADIUS + RB.T
    _lo, _hi = _r, RB.ZP - _r - RB.Z0
    L.append("  THE TAPE GOES ON A BAND, not on the bottom edge: from %.2f mm"
             % _lo)
    L.append("  to %.2f mm up the skin's inside face, %.2f mm wide. Below %.2f"
             % (_hi, _hi - _lo, _lo))
    L.append("  the carcass curves away into its own bend radius and the gap")
    L.append("  behind the skin opens from 2.30 to 5.27 mm.")
    _n_show = max(v for k, v in nt.items() if k.startswith("skin_show")) if any(
        k.startswith("skin_show") for k in nt) else 0
    _n_far = max(v for k, v in nt.items() if k.startswith("skin_far")) if any(
        k.startswith("skin_far") for k in nt) else 0
    L.append("  its tabs drop through slots already cut in the backplate: %d on"
             % _n_show)
    L.append("  a show skin and %d on a far skin, %d for the pair."
             % (_n_far, _n_show + _n_far))
    return "\n".join(L)


if __name__ == "__main__":
    txt = report()
    p = os.path.join(UPLOAD, "ORDER_SHEET.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(txt + "\n")
    print(txt)
    print("\nwrote %s" % p)
