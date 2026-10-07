"""Every hole and slot the assembly needs, on BOTH sides of every joint.

WHY THIS EXISTS
    cover_ribbon.fasteners() and carcass_fasteners() return where the screws
    go. They do not put a hole anywhere. Nothing in the project did: the
    backplate had no clearance holes for the cover, the carcass foot had no
    tapped holes, and the ribbon tabs had no slots to drop into. Every part
    would have arrived blank and the assembly would have been undrillable
    after powder coat.

    So this enumerates the holes themselves, per part, and then checks the
    thing that actually matters - that both halves of every joint have one.

THE RULES IT ENFORCES
    a screw needs a CLEARANCE hole in the near part and a TAPPED hole in the
    far one, and they have to be at the same place;
    every hole clears MIN_HOLE_DIA and keeps MIN_FEATURE of web to any edge,
    to the plate outline, and to every other hole;
    a hole in the BACKPLATE must sit under the cover's footprint, because the
    backplate is the show face and a 2 mm circle in the open is a defect;
    nothing lands in the connector notch's void or within 8 mm of one of the
    13 fasteners that hold the plate to the card.
"""

from __future__ import annotations

import math

from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

import backplate_v3 as B
from config import HARDWARE as _HWCFG
from config import MEASURED as _MEAS
MFG_CONN_W = _MEAS.CONNECTOR_W
import cover_ribbon as RB
from config import MFG
from hole_pattern import HOLES

CLEAR_D = RB.CLEAR_HOLE          # 2.30, M2 clearance opened for powder
TAP_D = RB.TAP_DIA               # 1.60, M2 x 0.4 tap drill
STRAP_SCREWS = 2                 # per strap: one into the cap, one into the plate


def cover_footprint(path=None):
    path = RB.route45() if path is None else path
    return Polygon(RB.offset(path, RB.CARCASS_RIB_OUT, RB.SHOW)
                   + RB.offset(path, RB.CARCASS_RIB_OUT, RB.FAR)[::-1]).buffer(0)


def holes(path=None):
    """Every hole and slot in the assembly, tagged with the part it is in."""
    path = RB.route45() if path is None else path
    out = []

    # 1. carcass feet -> backplate. Clearance in the plate, tapped in the foot.
    # 50/50 (2026-09-02): the FAR feet are screwed from ABOVE - the head sits
    # on the foot's lip outside the skin - so the clearance hole is in the
    # FOOT and the tapped hole is in the PLATE, the reverse of the old
    # bolted-from-below scheme. M2.5 x 0.45; the vendor taps the plate.
    for i, f in enumerate(RB.carcass_fasteners(path)):
        out.append(dict(part="backplate", kind="tapped", d=RB.FOOT_SCREW_TAP,
                        at=f["at"], joint="foot %d" % i, geom=None))
        out.append(dict(part="carcass foot", kind="clearance",
                        d=RB.FOOT_SCREW_CLEAR, at=f["at"],
                        joint="foot %d" % i, geom=None))

    # 2. skin tabs -> backplate slots. The skin carries no HOLE: a tab is
    #    outline. Only the plate is cut.
    # sized PER TAB from its distance in bends to the datum tab - see the note
    # at SLOT_W in cover_ribbon. A single global size is either unassemblable
    # or 1.5 mm loose everywhere.
    stations = {(round(t["at"][0], 4), round(t["at"][1], 4)): t
                for sgn in (RB.SHOW, RB.FAR) for t in RB.skin_tabs(sgn, path)}
    for i, t in enumerate(RB.tab_stations(path)):
        ux, uy = t["dir"]
        px, py = t["at"]
        st = stations.get((round(px, 4), round(py, 4)))
        sl_l = st["slot_l"] if st else RB.SLOT_L_MIN
        sl_w = st["slot_w"] if st else RB.SLOT_W
        nx, ny = -uy * t["sgn"], ux * t["sgn"]      # inward, into the channel
        px += nx * RB.SLOT_BIAS
        py += ny * RB.SLOT_BIAS
        sl = Polygon([(px - ux * sl_l / 2 - nx * sl_w / 2,
                       py - uy * sl_l / 2 - ny * sl_w / 2),
                      (px + ux * sl_l / 2 - nx * sl_w / 2,
                       py + uy * sl_l / 2 - ny * sl_w / 2),
                      (px + ux * sl_l / 2 + nx * sl_w / 2,
                       py + uy * sl_l / 2 + ny * sl_w / 2),
                      (px - ux * sl_l / 2 + nx * sl_w / 2,
                       py - uy * sl_l / 2 + ny * sl_w / 2)])
        out.append(dict(part="backplate", kind="slot", d=sl_w,
                        at=(px, py), joint="tab %d" % i, geom=sl))

    # 3. notch cap -> backplate. The cap laps BEHIND, so the clearance hole is
    #    in the cap and the tapped hole is in the plate.
    for i, at in enumerate(RB.cap_screws(path) if RB.CAP_IN_ORDER else []):
        out.append(dict(part="notch cap", kind="clearance", d=CLEAR_D,
                        at=at, joint="cap %d" % i, geom=None))
        out.append(dict(part="backplate", kind="tapped", d=TAP_D,
                        at=at, joint="cap %d" % i, geom=None))
    return out


def check(path=None):
    path = RB.route45() if path is None else path
    hs = holes(path)
    plate = Polygon(B.outline())
    cov = cover_footprint(path)
    notch = RB.notch_box()
    cap = RB.notch_cap(path)["cap"]
    fails, warns = [], []

    # -- every joint has a hole on BOTH sides -----------------------------
    joints = {}
    for h in hs:
        joints.setdefault(h["joint"], []).append(h)
    for j, group in joints.items():
        kinds = {g["kind"] for g in group}
        if j.startswith("tab"):
            continue                       # a tab is outline, by design
        if not ({"clearance", "tapped"} <= kinds):
            fails.append("joint %s has only %s - a screw needs a clearance "
                         "hole one side and a tapped hole the other"
                         % (j, "/".join(sorted(kinds))))
        pts = {(round(g["at"][0], 3), round(g["at"][1], 3)) for g in group}
        if len(pts) > 1:
            fails.append("joint %s: the two halves are not at the same place "
                         "(%s)" % (j, pts))

    # -- per hole ----------------------------------------------------------
    for h in hs:
        p = Point(h["at"])
        tag = "%s %s @ (%.1f, %.1f)" % (h["part"], h["kind"],
                                        h["at"][0], h["at"][1])
        if h["kind"] != "slot" and h["d"] < MFG.MIN_HOLE_DIA:
            # a TAP drill is legitimately under min hole dia - it is drilled
            # and tapped, not lasered - but say so rather than pass silently
            if h["kind"] == "tapped":
                warns.append("%s is %.2f mm, under the %.2f mm laser minimum: "
                             "must be a tapped feature, not a cut hole"
                             % (tag, h["d"], MFG.MIN_HOLE_DIA))
            else:
                fails.append("%s is %.2f mm, under %.2f"
                             % (tag, h["d"], MFG.MIN_HOLE_DIA))
        if h["part"] == "backplate":
            g = h["geom"] if h["geom"] is not None else p.buffer(h["d"] / 2)
            if not plate.contains(g):
                fails.append("%s is not on plate metal" % tag)
            if notch.intersects(g):
                fails.append("%s lands in the notch void" % tag)
            # A TAB SLOT IS ALLOWED TO SHOW, by exactly its own clearance. The
            # skin stands IN the slot, so half the clearance is outboard of the
            # skin by construction. Biasing it all inboard to hide it is what
            # made the joint interfere after coating. Everything else - any
            # hole - must still be fully under the cover.
            # THIS SLOT'S OWN WIDTH. Taking the allowance from the global
            # RB.SLOT_W is the same mistake one level up: once the two far
            # leg-2 slots widened to 5.678 mm - they are three bends from a
            # bonded foot, not one - they were measured against a 4.154 mm
            # allowance and read as protruding onto the visible face when they
            # protrude by exactly their own clearance, like every other slot.
            _sw = RB.SLOT_W
            if h["kind"] == "slot" and h["geom"] is not None:
                _r = list(h["geom"].minimum_rotated_rectangle.exterior.coords)
                _sw = min(math.dist(_r[k], _r[k + 1]) for k in range(4))
            allow = ((_sw - RB.TAB_W) / 2.0 + 1e-6
                     if h["kind"] == "slot" else 1e-6)
            # A FOOT SCREW'S TAPPED HOLE IS UNDER THE FOOT, not under the
            # skins: the head sits on the foot's lip outside the skin by
            # design. So the cover it must hide under is the folded foot.
            _cover = cov
            if str(h.get("joint", "")).startswith("foot"):
                _top, _fl = RB.carcass_blank(path, roof_vents=False)
                _cover = unary_union([RB.folded_foot(f, path) for f in _fl
                                      if f["kind"] == "foot"])
            if not _cover.buffer(allow).contains(g):
                fails.append("%s is NOT under the cover - it would show on the "
                             "backplate's face" % tag)
            web = plate.exterior.distance(g)
            if web < MFG.MIN_FEATURE:
                fails.append("%s leaves %.2f mm to the plate edge, under %.2f"
                             % (tag, web, MFG.MIN_FEATURE))
            # FROM THE FEATURE, NOT FROM ITS CENTRE. Every other test in this
            # loop uses the geometry - plate.contains(g), notch.intersects(g),
            # the cover footprint, the edge web - and this one used h["at"].
            # The nine tab slots are 12.80 and 13.56 mm long, so measuring
            # from the middle overstates the clearance by up to 6.8 mm: a slot
            # whose END is 1.2 mm from a fastener reads as 8.0 and passes.
            near = min(g.distance(Point(hx, hy)) for hx, hy, _t, _s in HOLES)
            if near < 8.0:
                fails.append("%s comes within %.2f mm of a backplate fastener"
                             % (tag, near))
        if h["part"] == "notch cap":
            for g in ([cap] if cap.geom_type == "Polygon" else list(cap.geoms)):
                if g.buffer(1e-6).contains(p.buffer(h["d"] / 2)):
                    web = g.exterior.distance(p.buffer(h["d"] / 2))
                    if web < MFG.MIN_FEATURE:
                        fails.append("%s leaves %.2f mm of cap web, under %.2f"
                                     % (tag, web, MFG.MIN_FEATURE))
                    break
            else:
                fails.append("%s is not on the cap" % tag)

    # -- hole to hole, within a part ---------------------------------------
    byp = {}
    for h in hs:
        byp.setdefault(h["part"], []).append(h)
    for part, group in byp.items():
        for i in range(len(group)):
            for k in range(i + 1, len(group)):
                a, b_ = group[i], group[k]
                ga = a["geom"] or Point(a["at"]).buffer(a["d"] / 2)
                gb = b_["geom"] or Point(b_["at"]).buffer(b_["d"] / 2)
                d = ga.distance(gb)
                if d < MFG.MIN_FEATURE:
                    fails.append("%s: two holes %.2f mm apart, under the "
                                 "%.2f mm minimum web" % (part, d, MFG.MIN_FEATURE))
    return hs, fails, warns


def report(path=None):
    path = RB.route45() if path is None else path
    hs, fails, warns = check(path)
    print("MOUNTING HARDWARE - every hole, both sides of every joint\n")
    byp = {}
    for h in hs:
        byp.setdefault(h["part"], []).append(h)
    for part in sorted(byp):
        g = byp[part]
        kinds = {}
        for h in g:
            kinds[(h["kind"], h["d"])] = kinds.get((h["kind"], h["d"]), 0) + 1
        print("  %-14s %d features" % (part, len(g)))
        for (k, d), n in sorted(kinds.items()):
            # THE SLOTS ARE TWO LENGTHS, and a rotated rectangle's BOUNDS
            # are not its edges - five of these lie at 45 degrees, where
            # the box is (L + W) / sqrt(2). Measure the edges, and list
            # every distinct length rather than one representative.
            if k == "slot":
                ls = set()
                for q in g:
                    if q["kind"] != "slot" or q["d"] != d:
                        continue
                    r = list(q["geom"].minimum_rotated_rectangle.exterior.coords)
                    ls.add(round(max(math.dist(r[t], r[t + 1])
                                     for t in range(4)), 2))
                lab = ("%s x %.2f slot"
                       % (" / ".join("%.2f" % v for v in sorted(ls)), d))
            else:
                lab = "%.2f dia" % d
            print("       %2d x %-9s %s" % (n, k, lab))
    print("\n  SKINS: 0 holes, either side. The show skin carries tabs, which")
    print("  are outline; the far skin is bonded, not screwed.")
    print("\n  cover is now %.1f mm wide, so every backplate hole has to sit"
          % RB.CARCASS_W)
    print("  inside that footprint or it shows on the face.")
    if warns:
        print("\n  NOTES")
        for w in warns:
            print("    - %s" % w)
    # CAN THE BRAKE CLOSE THE SECTION? The inward return lip could not be
    # bent: SendCutSend's return-flange rule (base >= 2 x return; 12.5/8.0 =
    # 1.56) and their same-direction adjacent-bend rule (>= 2 x flat minimum
    # flange = 12.95 between bend lines; the wall is 9.55) both failed, and
    # the foot was already at the 7.95 mm minimum so could not shrink. The
    # feet were turned OUTWARD on 2026-09-01: a hat section, opposite-sense
    # bends, no return, nothing in the punch's way. What remains to check is
    # the vendor's plain flange rules, from their 0.080 in 5052 table.
    _minf = 7.95                                   # min formed flange @ 90
    _wall = RB.CLEAR_D + RB.T                      # formed outer height
    _top = 2 * RB.CARCASS_HALF_DS                  # top face, outer
    print("\n  PRESS BRAKE, HAT SECTION WITH OUTWARD FEET (vendor rules, 2 mm "
          "5052):")
    for _sg, _nm in ((RB.SHOW, "show, taped"), (RB.FAR, "far, screwed")):
        print("    foot %s %.2f vs min formed flange %.2f .... %s"
              % (_nm, RB.foot_len(_sg), _minf,
                 "ok" if RB.foot_len(_sg) >= _minf - 1e-6 else "UNDER"))
    print("    wall %.2f vs min formed flange %.2f ........ %s"
          % (_wall, _minf, "ok" if _wall >= _minf - 1e-6 else "UNDER"))
    print("    top / wall %.2f / %.2f = %.2f vs U-channel 2:1  %s"
          % (_top, _wall, _top / _wall,
             "ok" if _top >= 2 * _wall - 1e-6 else "FAILS"))
    print("    wall-to-foot bend turns the OPPOSITE way to top-to-wall: no "
          "return lip, no adjacent same-direction rule.")
    for _sg in (RB.SHOW, RB.FAR):
        if RB.foot_len(_sg) < _minf - 1e-6:
            fails.append("the %.2f mm foot is under the %.2f mm minimum formed "
                         "flange for 2 mm 5052" % (RB.foot_len(_sg), _minf))
    if _wall < _minf - 1e-6:
        fails.append("the %.2f mm wall is under the %.2f mm minimum formed "
                     "flange" % (_wall, _minf))
    if _top < 2 * _wall - 1e-6:
        fails.append("top face %.2f is under 2 x the %.2f wall - the vendor's "
                     "U-channel ratio" % (_top, _wall))

    # a card fastener's washer stands proud on the face the cover lands on
    cov = cover_footprint(path)
    from config import HARDWARE as _HW
    from hole_pattern import HOLES as _H
    # COATED, not bare. Powder grows the skin and the washer alike, so the gap
    # loses 2 x COAT_ALLOWANCE; measuring bare metal reported 0.21 mm on a
    # joint that actually closes to 0.06.
    wr = _HW.WASHER_OD / 2.0 + MFG.COAT_ALLOWANCE
    cov = cov.buffer(MFG.COAT_ALLOWANCE)
    for x, y, _t, _s in _H:
        d = cov.distance(Point(x, y))
        if d < wr:
            fails.append("card fastener (%.2f, %.2f): its %.1f mm washer "
                         "overlaps the cover footprint by %.2f mm - the skin "
                         "cannot seat" % (x, y, _HW.WASHER_OD, wr - d))
    _wx, _wy, _t, _s = min(_H, key=lambda h: cov.distance(Point(h[0], h[1])))
    _cw = cov.distance(Point(_wx, _wy)) - wr
    print("\n  WASHER CLEARANCE, COATED BOTH SIDES: %.2f mm at the closest "
          "card fastener. The washer is bought steel and is not actually "
          "coated, so the true gap is %.2f - this is the pessimistic read."
          % (_cw, _cw + MFG.COAT_ALLOWANCE))
    # AGAINST THE STACK AT THIS WALL, not the one global SLOT_ACROSS. That
    # constant carries CARCASS_TOL = one bend, "from the bonded foot to the
    # wall", which is true only on the side the leg's staggered foot is on.
    # The closest fastener, (171.28, 32.02), is beside leg 0 on the SHOW
    # side and leg 0's foot is FAR: foot -> far wall -> top face -> show
    # wall is three bends, 1.143 mm, and the stack is 1.539 - against which
    # this guard was passing 0.810 by 0.033 on a number 1.9x too small.
    _leg, _sgn = RB.nearest_wall(_wx, _wy, path)
    _need = RB.slot_across_for(_leg, _sgn)
    print("  that wall is leg %d %s, %d bend(s) from its bonded foot: the "
          "stack there is %.3f mm (bond %.2f + tilt %.2f + %d x %.3f)."
          % (_leg, "show" if _sgn == RB.SHOW else "far",
             RB.carcass_bends_to_foot(_leg, _sgn), _need, RB.BOND_TOL,
             RB.SKIN_TILT, RB.carcass_bends_to_foot(_leg, _sgn), RB.BEND_TOL))
    if _cw < _need:
        fails.append("coated washer clearance %.3f mm at (%.2f, %.2f) - under "
                     "the %.3f mm lateral stack of the wall beside it (leg %d "
                     "%s, %d bends from its foot); short by %.3f"
                     % (_cw, _wx, _wy, _need, _leg,
                        "show" if _sgn == RB.SHOW else "far",
                        RB.carcass_bends_to_foot(_leg, _sgn), _need - _cw))

    # THE SLOT AGAINST THE STACK IT HAS TO SWALLOW.
    #
    # AND THIS PARTICULAR COMPARISON IS AN IDENTITY. SLOT_W is DEFINED as
    # T + 4*COAT + 2*SLOT_ACROSS, so _side is SLOT_ACROSS by construction and
    # this can never fail. It is worth PRINTING - the stack is the interesting
    # part and it is how the 0.360-against-0.360 was spotted - but it is not
    # evidence of anything. release_gate.check_slot_width() measures the slots
    # in the FILE against the same stack, which is the comparison that can
    # actually disagree.
    _c = MFG.COAT_ALLOWANCE
    _side = ((RB.SLOT_W - 2 * _c) - (RB.T + 2 * _c)) / 2.0
    print("\n  TAB SLOT, ACROSS: %.3f mm per side coated, against a "
          "declared stack of %.3f (bond %.2f + tilt %.2f + carcass %.2f)"
          % (_side, RB.SLOT_ACROSS, RB.BOND_TOL, RB.SKIN_TILT,
             RB.CARCASS_TOL))
    if _side < RB.SLOT_ACROSS - 1e-9:
        fails.append("tab slot gives %.3f mm per side, stack needs %.3f"
                     % (_side, RB.SLOT_ACROSS))

    # THE CONNECTOR, IN PLAN. Nothing had ever checked it: entry_height.py
    # tests the connector's HEIGHT and says so, notch_box() models the notch
    # as absent plate metal rather than as a 9.89 mm tall obstruction, and
    # CONNECTOR_W appeared nowhere outside a superseded module.
    _lat, _vert = RB.fastener_clearance(path)
    print("\n  CARD FASTENER, in two axes: lateral %+.2f mm coated, vertical %s"
          % (_lat, ("%+.2f mm" % _vert) if _vert is not None
             else "UNKNOWN (screw head height not measured)"))

    # IS THERE A POSITION AT ALL? Every version of this check until now asked
    # only "how far left can the connector sit", which presumes a window wide
    # enough to hold it somewhere. The leg-0 foot folded straight across the
    # notch - 212.0 mm2 of it, 0.40 to 2.40 mm above the plate's coated face -
    # and cut the window to 15.70 mm against an 18.20 mm body, so there was NO
    # position, and the guard went on reporting the problem as one measurement
    # from solved because it only ever looked at the two walls.
    _free, _lo, _hi = RB.connector_free_window(path)
    print("\n  CONNECTOR WINDOW ACROSS THE NOTCH, COATED: %.2f mm "
          "(x %.2f..%.2f)" % (_free, _lo, _hi))
    print("  against a %.1f mm body - every folded panel counted, not just "
          "the walls." % MFG_CONN_W)
    if _free < MFG_CONN_W:
        fails.append("the cover leaves a %.2f mm coated window across the "
                     "connector notch and the body is %.1f mm - it does not "
                     "fit at ANY position, so no measurement of the card can "
                     "rescue it" % (_free, MFG_CONN_W))

    # THE ADAPTER, against whatever now bounds the notch. Its along-card
    # axis and exact position are the owner's readings; print both cases
    # from the edge it was seen to just clear (x 135.22) so the answer is on
    # the page the moment the readings are in.
    from config import SCANNED as _SC
    _ref = 135.22
    print("  ADAPTER (30.18 x 25.10, from x %.2f) against that window:" % _ref)
    for _al in (_SC.ADAPTER_B, _SC.ADAPTER_A):
        _x1 = _ref + _al
        print("    %.2f along the card -> x %.2f..%.2f: bracket side %+.2f, "
              "show side %+.2f" % (_al, _ref, _x1, _ref - _lo, _hi - _x1))
    # the case the observations point to: centred on the connector, the
    # 25.10 side along the card
    _al = _SC.ADAPTER_ALONG_CARD
    _x0, _x1 = RB.CONNECTOR_CX - _al / 2.0, RB.CONNECTOR_CX + _al / 2.0
    print("  ESTIMATED (centred on the connector, %.2f along): x %.2f..%.2f "
          "-> bracket side %+.2f, show side %+.2f"
          % (_al, _x0, _x1, _x0 - _lo, _hi - _x1))
    _h = _SC.ADAPTER_TOP_ABOVE_PLATE
    print("  its top, from the owner's PCB-up reading: %.2f above the plate "
          "face; roof at %.2f -> %+.2f" % (_h, RB.ZT - RB.PLATE_T,
                                           RB.ZT - RB.PLATE_T - _h))
    if _x0 < _lo or _x1 > _hi:
        fails.append("the adapter, centred on the connector with %.2f along "
                     "the card, spans %.2f..%.2f against a %.2f..%.2f window"
                     % (_al, _x0, _x1, _lo, _hi))
    if _h > RB.ZT - RB.PLATE_T - 1e-6:
        fails.append("the adapter's top at %.2f above the plate face is under "
                     "the roof by %.2f" % (_h, RB.ZT - RB.PLATE_T - _h))

    _sh, _fr, _brk = RB.connector_clearance(path)
    if _sh is None:
        print("\n  CONNECTOR IN PLAN: NOT KNOWN. The channel centreline is at "
              "%.2f and the" % path[0][0])
        print("  notch centre at %.2f, so a %.1f mm connector body clears the "
              % (153.07, MFG_CONN_W))
        print("  show wall only if its centre is at or below %.2f. It does "
              "not sit" % _brk)
        print("  centred - the card says the tight side is the bracket, which "
              "is the way")
        print("  that clears - but nobody has measured it. Set "
              "cover_ribbon.CONNECTOR_CX.")
        print("  ONE measurement closes it: the connector's centre must be "
              "at or below %.2f." % _brk)
        print("  There is no second way round. The cover sits %.2f mm above "
              "the plate's" % (RB.Z0 - RB.PLATE_T))
        print("  outer face - a bond line - so it cannot pass OVER the card "
              "fastener,")
        print("  whose washer alone is %.2f mm thick." % _HWCFG.WASHER_T)
        fails.append("connector position is unmeasured: the show wall clears "
                     "only if the connector centre is at or below %.2f "
                     "(153.07 if it sits centred in the notch)" % _brk)
    else:
        print("\n  CONNECTOR IN PLAN, COATED: show %+.2f mm, far %+.2f mm"
              % (_sh, _fr))
        if min(_sh, _fr) < 0:
            fails.append("the channel wall lands on the connector by %.2f mm"
                         % -min(_sh, _fr))

    # THE FOOT BOND AGAINST THE TAB IT HAS TO LEAVE ROOM FOR. Engagement
    # is PLATE_T - FOOT_BOND exactly, the four coat allowances cancelling,
    # so a foot tape as thick as the plate leaves nothing in the slot at
    # all. The skins' 2.30 mm VHB under a foot would give -0.30.
    _eng = RB.PLATE_T - RB.FOOT_BOND
    print("\n  TAB ENGAGEMENT: %.2f mm of tab inside the plate, with %s"
          % (_eng, RB.FOOT_TAPE))
    if _eng <= 0:
        fails.append("the foot bond is %.2f mm against a %.2f mm plate - "
                     "the tabs finish proud and none enters its slot"
                     % (RB.FOOT_BOND, RB.PLATE_T))
    elif _eng < RB.PLATE_T / 2.0:
        fails.append("the foot bond leaves only %.2f mm of tab engagement"
                     % _eng)

    fold_hits = check_folded(path)
    print("\n  FOLDED INTERFERENCE: %d panel pair(s) sharing a space"
          % len(fold_hits))
    for a, b, ar, at in fold_hits:
        fails.append("folded: %s hits %s, %.3f mm2 at (%.1f, %.1f)"
                     % (a, b, ar, at[0], at[1]))

    print("\n  NARROWEST CUT OPENING, by exact distances - the vanish"
          " test misses a waist and the split test misses a dead-end arm:")
    for nm, w in check_pinch():
        print("     %-38s %.3f mm" % (nm, w))
        if w < MFG.MIN_FEATURE:
            fails.append("%s pinches to %.3f mm, under the %.2f minimum"
                         % (nm, w, MFG.MIN_FEATURE))

    tot, worst = check_flat_pattern(path)
    print("\n  FLAT PATTERN, carcass: %.3f mm2 of self-overlap (worst pair "
          "%.3f)" % (tot, worst))
    if tot > 1e-6:
        fails.append("the carcass flat pattern overlaps itself by %.2f mm2 - "
                     "it cannot be cut" % tot)

    print("\n  %s" % ("ALL CHECKS PASS" if not fails
                      else "%d FAILURES" % len(fails)))
    for f in fails:
        print("    FAIL  %s" % f)
    return not fails


# ---- self-tests -----------------------------------------------------------
# A checker that has never failed is not evidence of anything. These two put
# known-bad hardware through it and require it to object.
def _selftest():
    ok = True
    path = RB.route45()

    # 1. a backplate hole out in the open must be rejected
    import copy
    real = holes(path)
    bad = copy.deepcopy(real)
    bad.append(dict(part="backplate", kind="clearance", d=CLEAR_D,
                    at=(60.0, 60.0), joint="planted", geom=None))
    bad.append(dict(part="carcass foot", kind="tapped", d=TAP_D,
                    at=(60.0, 60.0), joint="planted", geom=None))
    g = globals()
    orig = g["holes"]
    g["holes"] = lambda p=None: bad
    _hs, fails, _w = check(path)
    g["holes"] = orig
    caught = any("planted" in f or "(60.0, 60.0)" in f for f in fails)
    print("  hole in the open, away from the cover ....... %s"
          % ("REJECTED, correct" if caught else "PASSED - the check is blind"))
    ok &= caught

    # 2. a screw with a hole on only one side must be rejected.
    #    IT PLANTS ITS OWN JOINT NOW. This used to delete the backplate half
    #    of joint "cap 0" from the real schedule - and when the notch cap left
    #    the order there was no "cap 0" to delete, so it planted nothing, the
    #    check correctly found nothing, and the self-test reported itself
    #    blind. It was right to: with the feet bonded and the cap gone, the
    #    assembly has no screwed joints left at all, so a test that borrows one
    #    from the design can only decay. This one brings its own.
    at = (60.0, 90.0)
    bad2 = list(real) + [dict(part="carcass", kind="clearance", d=CLEAR_D,
                              at=at, joint="planted screw", geom=None)]
    g["holes"] = lambda p=None: bad2
    _hs, fails2, _w = check(path)
    g["holes"] = orig
    caught2 = any("planted screw" in f for f in fails2)
    print("  screw with a hole on one side only .......... %s"
          % ("REJECTED, correct" if caught2 else "PASSED - the check is blind"))
    ok &= caught2

    # PUT BACK THE GEOMETRY THAT SHIPPED. Zeroing the folded corner trim
    # restores the blank that passed every check in this repo and collides on
    # the brake. If this stops firing, the folded check has gone blind again.
    # THE PLANT HAS TO BE POSSIBLE. With the feet outward and on the
    # outside of every turn they diverge at each corner, so disabling the
    # taper alone produces nothing to catch and this test went "blind" for
    # the wrong reason. Put every foot on the FAR side - the inside of the
    # two left turns, at legs 1->2 and 3->4 - and disable the taper: two
    # pairs of outward feet then sweep into each other, and check_folded()
    # must see both.
    import cover_ribbon as _RB
    # ...and the corner RELIEF too: it already pulls every flap 6.87 mm
    # back from a concave corner in the blank, which alone keeps inside feet
    # apart, so a plant that only removes the taper still has nothing to
    # catch. Remove both and the feet overlap; the check has to say so.
    keep = _RB.folded_corner_trim
    keep_rel = _RB.relief_for
    keep_sides = dict(_RB.FOOT_SIDES)
    _RB.folded_corner_trim = lambda th, reach: 0.0
    _RB.relief_for = lambda th, depth, concave: 0.0
    _RB.FOOT_SIDES.update({k: _RB.FAR for k in _RB.FOOT_SIDES})
    try:
        hits = check_folded(path)
    finally:
        _RB.folded_corner_trim = keep
        _RB.relief_for = keep_rel
        _RB.FOOT_SIDES.clear()
        _RB.FOOT_SIDES.update(keep_sides)
    caught3 = len(hits) >= 2
    print("  feet folded into each other at two corners .. %s"
          % ("REJECTED, correct" if caught3 else "PASSED - the check is blind"))
    ok &= caught3

    # AND THE SKINS ARE IN THAT CHECK NOW, so plant one in the wall. Until
    # this round check_folded() tested the carcass against itself and did not
    # know the skins existed - half the cover, and the half bonded to the
    # outside of the panels being tested.
    keep_in = _RB.CARCASS_RIB_IN
    _RB.CARCASS_RIB_IN = _RB.CARCASS_HALF_IN        # skin inside the wall
    try:
        hits4 = check_folded(path)
    finally:
        _RB.CARCASS_RIB_IN = keep_in
    caught4 = any("skin" in a or "skin" in b for a, b, _ar, _at in hits4)
    print("  a skin standing where the wall is .......... %s"
          % ("REJECTED, correct" if caught4 else "PASSED - the check is blind"))
    ok &= caught4
    return ok




def check_flat_pattern(path=None):
    """A flat pattern may not overlap itself. Nothing checked this until the
    first template was drawn, and the carcass overlapped by 266 mm2."""
    path = RB.route45() if path is None else path
    top, flaps = RB.carcass_blank(path)
    # THE TOP FACE IS A PANEL TOO, and the biggest one - 4848 mm2 that all
    # fifteen flaps fold away from. This compared flap to flap only, so a flap
    # lying ON the top face, which is the most likely way a flat pattern
    # overlaps itself, was invisible to the one check written for it.
    panels = [f["poly"] for f in flaps] + [top]
    worst, tot = 0.0, 0.0
    for i in range(len(panels)):
        for j in range(i + 1, len(panels)):
            a = panels[i].intersection(panels[j]).area
            tot += a
            worst = max(worst, a)
    return tot, worst


def check_pinch():
    """Narrowest CUT opening in each vent field, by EXACT DISTANCES.

    The obvious test - does the contour vanish under a negative buffer - is
    wrong and passed three sub-minimum glyphs for weeks. A shape with a thin
    waist does not vanish; it splits. So this asked when the piece count
    changes instead - and that is wrong in its own way, because a dead-end arm
    can be narrower than anything and closing it disconnects nothing. On the
    shipped plates the split test said 2.400 mm where the truth is 2.220.

    release_gate.narrowest_opening() measures it exactly, and this now reports
    the same number the gate does rather than a second opinion.
    """
    import release_gate as RG
    import vent_iterate as VI
    import vent_ocr as VO
    f = VO.narrow_field()
    out = []
    for name, fn in VO.DESIGNS:
        g, _d = VO.build_one(fn, f)
        ps = [g] if g.geom_type == "Polygon" else list(g.geoms)
        exact, _at = RG.narrowest_opening(ps)
        # the split test as well: it catches a waist that SEVERS a contour,
        # which the pairwise measure reaches by a different route. Whichever
        # is smaller is the answer.
        out.append((name.replace(", OCR", ""),
                    min(exact, min(VI._neck(p) for p in ps))))
    return out



def check_folded(path=None):
    """Fold the carcass and look for two panels trying to occupy one space.

    NOTHING IN THIS PROJECT DID THIS. The flat pattern is checked for overlap,
    the DXF is checked for min feature, the exported solid is SLICED - and a
    slice is taken across the run, so two panels that meet ALONG the run, at a
    corner, never appear in one. The two feet at the convex show-side corners
    overlapped by 9.00 mm2 each while the same two panels sat 10.27 mm apart
    in the flat with a clean gap on every drawing.

    Returns [(a, b, area, at)] for every genuine 3D interference.
    """
    import cover_ribbon as _RB
    pans = _RB.folded_panels(path)
    out = []
    for i in range(len(pans)):
        for j in range(i + 1, len(pans)):
            ka, ia, sa, ga, za0, za1 = pans[i]
            kb, ib, sb, gb, zb0, zb1 = pans[j]
            if min(za1, zb1) - max(za0, zb0) <= 1e-9:
                continue                      # different heights, no contact
            if ka == kb and ia == ib and sa == sb:
                continue
            if not (ga.is_valid and gb.is_valid):
                continue
            ov = ga.intersection(gb)
            if ov.area > 1e-3:
                out.append(("%s leg%d %s" % (ka, ia, "show" if sa > 0 else "far"),
                            "%s leg%d %s" % (kb, ib, "show" if sb > 0 else "far"),
                            ov.area, (ov.centroid.x, ov.centroid.y)))
    return out

if __name__ == "__main__":
    import sys
    good = report()
    print("\nSELF-TESTS")
    good &= _selftest()
    sys.exit(0 if good else 1)
