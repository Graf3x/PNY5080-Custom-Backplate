"""Ribbon and plate: no wall is ever bent off the top face, so relief cannot exist.

WHERE THIS CAME FROM
    Eight research agents were sent at the corner-gap problem from eight
    unrelated directions - press-brake corner practice, surface raceway and
    cable tray, architectural cladding, kerf bending, laser-cut joinery,
    industrial-design parting lines, post-process filling, and rerouting.
    SIX of the eight arrived here independently. Sign-making calls the
    continuous wall a return, raceway calls it base-and-cover, architecture
    calls it a fascia over a carcass, and cable tray builds horizontal elbows
    exactly this way: continuous side rails, separate bottom.

THE ARGUMENT
    A corner relief is not a corner problem. It is a symptom of the top face
    and the wall being THE SAME PIECE OF METAL. A press brake folds along a
    straight line; our top face turns in plan; so a wall hanging off it has a
    bend line that turns too, and relief is the only way to let it.

    Stop hanging the wall off the top face and the whole thing evaporates.

        the TOP PLATE becomes a flat laser-cut Z with ZERO bends. A part with
        no bend cannot have a bend relief, a kink, or a bend-tolerance stack.

        each WALL becomes a plain strip folded only about VERTICAL axes. Those
        bend lines run the full width of the strip with flat material on both
        sides of nothing - and SendCutSend's own relief guide says so outright:
        "Not all bends require relief. For example a bend along the full width
        of a part. There's no flat material out at the edges of the bend."

    It fixes the far wall by the same stroke as the show wall, and it deletes
    the two 28 mm turn openings that cover_corner could not close, because the
    walls now run continuously THROUGH each corner and the cable never has to
    cross one.

WHAT THE OWNER SEES FROM THE CHAIR
    One continuous piece of 2 mm aluminium, 236 mm of flat blank, wrapping both
    plan corners on 2.97 mm outside radii, powder coated as a single object
    with nothing cut into it but its own outline. The top plate is RECESSED
    below the ribbon's top edge, so from a seated eye it is not visible at all:
    the whole of the show side is folded metal, edge to edge.

WHAT IT COSTS
    Two corners are radiused 2.97 mm outside instead of sharp. Four cleats and
    a top plate instead of one bent hat. And the ribbon is a free-standing
    2 x 15 mm strip over 236 mm, which is limp in its weak axis - it has to be
    bonded continuously, not point-fixed, or it will bow visibly under gloss
    white.

THE HANDEDNESS RESULT, which is why the old options kept failing
    Along the route, the show side is the RIGHT side of travel throughout.
    Corner 1 turns right, so the show side is the INSIDE of that turn: concave.
    Corner 2 turns left, so the show side is the OUTSIDE: convex.

    That split is fatal to every fix that works on only one kind of corner. A
    convex corner can be mitred shut to the vendor's 0.4 mm; a concave one
    cannot, because there the two wall panels swing APART and the gap is
    missing material rather than colliding material. A ribbon does not care:
    both corners are ordinary folds, one left-hand and one right-hand.
"""

from __future__ import annotations

import math

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import cable_route_v3 as R
from config import MEASURED as M
from config import MFG

T = MFG.THICKNESS                       # 2.0
CLEAR_W = M.CABLE_W                     # 24.0 internal, side to side
CLEAR_D = M.CABLE_D                     # 10.5 internal, plate face to plate soffit
HALF_OUT = CLEAR_W / 2 + T              # 14.0 to the ribbon's OUTSIDE face
HALF_IN = CLEAR_W / 2                   # 12.0 to the ribbon's INSIDE face

BEND_DEDUCT = 2.95
BEND_RADIUS = 0.97
BEND_KEEPOUT = 5.99                     # half die width; features stay clear
MIN_PART = (9.53, 38.1)                 # SCS minimum flat part, 0.375 x 1.5 in
CORNER_GAP = 0.40                       # SCS published min gap where flanges meet
# t + bend radius + 0.020 in, the vendor's own relief DEPTH. A relief has to cut
# PAST the bend line into the parent by this much; stopping level with it leaves
# the blank's edge running along a live fold with solid metal inboard, which is
# the textbook partial-width-flange tear.
RELIEF_W = 2.0               # relief notch WIDTH along the fold. Vendor min is
                             # t/2 = 1.00; 2.0 is our own min-feature floor.
RELIEF_DEPTH = MFG.THICKNESS + 0.97 + 0.5

REVEAL = 2.5                            # top plate recessed below the ribbon top
SIDE_GAP = 0.40                         # plate edge to ribbon inner face
# THE FOOT BOND IS NOT THE SKIN BOND. The skins take 2.30 mm of VHB 4991
# because there that thickness IS the reveal. Putting 2.30 mm under the feet
# would lift the entire carcass by it and raise every height in the stack. The
# feet want a THIN high-strength transfer adhesive instead - both faces are the
# same alloy at the same temperature, so none of VHB's stress-absorbing
# thickness is doing anything there.
# A REAL PRODUCT, not a round number. 0.20 was a placeholder for "some thin
# transfer adhesive" and it is the last number in this design that was chosen
# because it looked reasonable.
#
#   3M VHB Adhesive Transfer Tape 9473PC
#   0.25 mm (10 mil), 100MP high-performance acrylic, no carrier
#   very high shear, sold specifically to replace rivets and spot welds
#
# It is the VHB family at a stocked thickness in the right range - the skins'
# 4991 is 2.30 mm of foam, which under a foot would lift the whole carcass.
# 468MP at 0.13 mm was the other candidate; 0.25 is chosen for wet-out, since
# both faces here are POWDER COATED and powder has orange peel to fill.
#
# STILL TO CONFIRM, and it is an adhesion question rather than a geometry one:
# 3M's guidance for painted and powder-coated substrates often calls for a
# primer or at minimum a solvent wipe and a peel test on the actual finish.
# That does not change any dimension in this file.
FOOT_BOND = 0.25               # 3M VHB 9473PC, 10 mil
FOOT_TAPE = "3M VHB Adhesive Transfer Tape 9473PC, 0.25 mm"
# THE TAB ENGAGEMENT IS PLATE_T - FOOT_BOND, exactly: the four coat
# allowances cancel. So the foot bond line must stay under PLATE_T or the tab
# tips finish PROUD of the plate and nothing enters anything.
FOOT_BOND_MAX = 2.0            # = PLATE_T; at this thickness engagement is 0
SIT = FOOT_BOND

PLATE_T = 2.0                           # the backplate itself
# AND THE POWDER UNDER THE FOOT. The foot does not sit on bare plate: the
# plate's outer face is coated and so is the foot's underside, so the stack is
# coat + adhesive + coat. At FOOT_BOND = 0.20 the coating is HALF AGAIN as
# thick as the glue line it is being ignored in favour of - 0.30 against 0.20.
# Everything above Z0 rides on it, so the flush skin, which is specified level
# with the top face, finished 0.20 mm low.
SIT_STACK = MFG.COAT_ALLOWANCE + SIT + MFG.COAT_ALLOWANCE
Z0 = PLATE_T + SIT_STACK                # ribbon foot, as built
ZT = Z0 + CLEAR_D                       # top plate UNDERSIDE
ZP = ZT + T                             # top plate upper surface
ZR = ZP + REVEAL                        # ribbon top edge

# The route, centreline, in plate coordinates.
#
# END_Y was 132.0, which ran 9.6 mm past the plate's bottom edge at 122.4.
# There is very little room on that side, so the run now stops 3.0 mm past -
# just enough for the cable to clear the edge and turn away, and no more.
PLATE_BOTTOM = 122.4
END_OVERHANG = 3.0
END_Y = PLATE_BOTTOM + END_OVERHANG          # 125.4
# EVERY FUNCTION THAT DESCRIBES THE BUILT PART DEFAULTS TO route45(), NOT to
# this. PATH is the original 90 degree centreline and it is neither shifted nor
# chamfered, so seventeen functions used to hand back geometry for a part that
# is not being made if you forgot the argument - silently, with no error, off
# by the whole 3.60 mm route shift. Every real caller passed route45()
# explicitly, so it never reached a file; it reached ME, in a diagnostic,
# where it cost an hour of chasing an 11 mm discrepancy that was not there.
PATH = [(R.CONN_X, 0.0), (R.CONN_X, 76.4), (263.0, 76.4), (263.0, END_Y)]


# THE NOTCH CAP IS NOT IN THE ORDER, and the reasoning below is kept because
# it is still the reasoning - the part is right, it is just not needed and
# cannot be fitted. Three measurements, any one of which is enough:
#
#   IT IS REDUNDANT. The cap exists to close the connector notch. Since the
#   cover was widened, the cover's own footprint covers 100.0% of the notch in
#   plan - not the 99.6% the note below estimated, all of it. There is nothing
#   left for the cap to cover.
#
#   IT BLOCKS THE ADAPTER. The notch was widened 4.00 mm on the BRACKET side
#   specifically so the EZDIYFAB 180-degree adapter clears - that is the one
#   thing the owner measured on the real card. The cap's opening is centred on
#   the notch and is 24.0 mm wide, so it starts at x 139.070 against the stock
#   notch edge at 139.220: it hands back 3.85 of the 4.00 mm and leaves
#   0.15 mm of relief. The cap sits between the PCB and the plate, in the same
#   space as the adapter.
#
#   IT DOES NOT FIT. STANDOFF_H is 2.40 mm. The cap is 2.00 mm of stock and
#   2.30 coated, and it is screwed from the PCB side, so an M2 pan head adds
#   about 1.30 more: 3.60 mm into a 2.40 mm gap. The backplate could not sit
#   down on its standoffs.
#
# Setting this False drops one part, two tapped M2 holes in the backplate's
# show face and two clearance holes, and removes the interference. Set it True
# to put the part back; everything downstream reads this flag.
CAP_IN_ORDER = False

# WHICH FACADE IS ORDERED. Decided 2026-09-01: FLUSH, both backplates. The
# tall skins were an alternative, not the other half of a cover, and leaving
# their DXFs in upload/ is exactly the "upload the folder wholesale and cut
# the wrong parts" hazard this build exists to prevent. Every emitter and
# every gate reads this tuple; the harness and templates still draw whatever
# it says, so the printed sheets match the order.
ORDER_FLUSH = (True,)          # (False,) for tall, (False, True) for both


def ordered_facades():
    """The flush flags the order actually contains, in emit order."""
    return tuple(ORDER_FLUSH)

# WHERE THE CONNECTOR ACTUALLY SITS INSIDE THE NOTCH. Nothing in this project
# has ever used it, and the whole channel-versus-connector question turns on
# it.
#
# The route is anchored on the NOTCH centre and then shifted 4.00 mm toward
# the bracket (WIDEN 2.0 + WASHER_CLEAR 2.00), so the channel centreline is at
# 149.07 while the notch centre is 153.07. The connector body is 18.2 mm wide
# (config MEASURED.CONNECTOR_W). Whether the show-side wall lands on it
# depends entirely on where the connector sits within a notch 9.5 mm wider
# than itself:
#
#   centred on the notch, 153.07  -> the wall FOULS it by 1.25 mm coated
#   at 151.82                     -> exactly touching, the break-even
#   hard against the stock notch's bracket edge, 148.32 -> clears by 3.50
#
# backplate_v3 records, from the card, that the connector does NOT sit centred
# and that the tight side is the BRACKET side - which is the direction that
# clears. So it probably clears. "Probably" is not a dimension, and I wrote
# "the connector itself is 18.2 and clears" into DO_NOT_CUT.txt without ever
# doing this arithmetic.
#
# None -> the gate fails and says what to measure. Put the measured number
# here and it checks it.
# PHOTO-DERIVED, 2026-09-01, and stated twice by the owner: the plug body
# sits hard against the BRACKET end of the stock 27.7 mm notch (edge 139.22),
# so its centre is 139.22 + 18.2/2. Not a calliper reading; written in
# because the margins it leaves to the cover walls - 3.0 mm far, 2.5 mm show -
# are an order of magnitude larger than a photo's uncertainty.
CONNECTOR_CX = 139.22 + 18.2 / 2.0        # 148.32
CONNECTOR_CX_MAX = None      # filled in by connector_clearance(), for reporting


def connector_free_window(path=None):
    """The clear width across the notch, COATED - EVERY part of the cover.

    THE WALLS WERE NOT THE ONLY THING IN THE WAY. connector_clearance() takes
    the channel's inner faces, CARCASS_HALF_IN either side, and asks where a
    CONNECTOR_W body fits between them. A foot is inboard of its wall by
    CARCASS_FOOT, and the leg-0 foot used to fold straight across the notch:
    212.0 mm2 of it, standing 0.40 to 2.40 mm above the plate's coated face,
    leaving a 15.70 mm window against an 18.20 mm connector. That is a 2.50 mm
    interference at EVERY position, and the guard reported the problem as one
    measurement away from solved because the foot was never in the comparison.

    So this walks the folded panels - walls, feet and all - keeps whatever
    overhangs the notch, and returns the widest clear span across it.
    """
    path = route45() if path is None else path
    nb = notch_box()
    lo, hi = nb.bounds[0], nb.bounds[2]
    for kind, _leg, _sgn, g, _z0, _z1 in folded_panels(path):
        # walls, feet AND skins: with the walls cut back over the notch band
        # the skins are what bounds the notch sideways, and a window that
        # ignored them read 34.70 mm - the bare notch - while the show skin's
        # inner face stood 2.4 mm inside that.
        if kind not in ("downstand", "foot", "skin"):
            continue                     # the end cap sits at y <= 0
        ov = g.buffer(MFG.COAT_ALLOWANCE).intersection(nb)
        if ov.is_empty:
            continue
        x0, x1 = ov.bounds[0], ov.bounds[2]
        mid = (nb.bounds[0] + nb.bounds[2]) / 2.0
        if x1 <= mid:
            lo = max(lo, x1)
        elif x0 >= mid:
            hi = min(hi, x0)
        else:
            return 0.0, lo, hi          # something spans the notch entirely
    return max(0.0, hi - lo), lo, hi


def connector_clearance(path=None):
    """Gap from each obstruction to the connector body, COATED. Plan only.

    Returns (show, far, break_even_centre). A negative gap is a hard
    collision: the connector stands 9.89 mm above the plate's outer face and
    the wall comes down to 0.20, so there is no height in which to miss.
    """
    from config import MEASURED as _M
    path = route45() if path is None else path
    w = _M.CONNECTOR_W
    # THE REAL WINDOW, not the nominal channel. See connector_free_window.
    _free, lo, hi = connector_free_window(path)
    ccx = CONNECTOR_CX
    brk = hi - w / 2.0
    if ccx is None:
        return None, None, brk
    return hi - (ccx + w / 2.0), (ccx - w / 2.0) - lo, brk


# THE CARD FASTENER IS A 3D OBSTACLE, AND THE VERTICAL PATH DOES NOT EXIST.
#
# WASHER_CLEAR exists so the skin passes BESIDE the card fastener at
# (171.28, 32.02), and an interference does need overlap in all three axes, so
# it is worth asking whether the cover could simply pass OVER the fastener
# instead. It cannot, and I got this wrong once by reading Z0 as a height
# above the plate.
#
# Z0 IS MEASURED FROM THE PLATE'S INNER FACE. The plate occupies z 0 to 2.00
# and Z0 = 2.55, so the cover's underside is 0.55 mm above the OUTER face -
# which is just the bond line, as it must be. The fastener above that same
# face is coat 0.15 + nylon washer 0.30 + head, so the cover would clear it
# only if the head were under 0.10 mm. No screw head is 0.10 mm.
#
# So the lateral clearance is the only path, and the two constraints pull
# opposite ways with nothing to trade between them: clearing the fastener
# pushes the channel toward the bracket, clearing the CONNECTOR pushes it
# away, and they are 1.22 mm apart if the connector sits centred in its notch.
# ONE measurement decides it - where the connector actually sits.
SCREW_HEAD_H = None          # M2: 1.6 if DIN 7985 pan, 2.0 if socket cap


def fastener_clearance(path=None):
    """(lateral, vertical) clearance from the cover to the card fastener.

    Lateral is the coated plan gap from the cover's edge to the washer's rim.
    Vertical is the cover's underside above the whole fastener stack, taking
    the worst-case M2 head when the height is unrecorded - and it is always
    negative here, by about 1.9 mm, because the cover sits only a bond line
    above the plate. It is returned anyway so the number is on the page
    instead of in an argument.
    """
    from shapely.geometry import Point as _Pt
    from hole_pattern import HOLES as _H
    from config import HARDWARE as _HW
    path = route45() if path is None else path
    import hardware as _HWM              # for the footprint, defined there
    cov = _HWM.cover_footprint(path).buffer(MFG.COAT_ALLOWANCE)
    wr = _HW.WASHER_OD / 2.0 + MFG.COAT_ALLOWANCE
    lat = min(cov.distance(_Pt(x, y)) for x, y, _t, _s in _H) - wr
    # ABOVE THE PLATE'S OUTER FACE, which is at z = PLATE_T. Z0 is measured
    # from the inner face; subtracting it directly reads the cover as 2.55 mm
    # up when it is 0.55.
    head = 2.0 if SCREW_HEAD_H is None else SCREW_HEAD_H   # worst case, cap
    stack = MFG.COAT_ALLOWANCE + _HW.WASHER_T + head
    return lat, (Z0 - PLATE_T) - stack


# ---- the notch cap --------------------------------------------------------
# The connector notch is a bite out of the plate's top edge, 31.7 x 26.5 mm,
# and the channel's first 26.5 mm runs straight over that void. Left open you
# look down past the cover and see the connector.
#
# HOW THE CAP IS HELD, and why it is not flush.
#
# Flush meant the cap sat IN the opening with 0.4 mm of clearance all round,
# supported by straps lapped across the back. It cannot be built:
#
#   the cap's own web is 3.85 mm at its widest. A tapped M2 needs 1.60 mm of
#   hole plus 2.0 mm of web each side - 5.60 mm. Screwing the cap is out.
#   the strap would have to cross the BACK of the notch, and the back of the
#   notch is the connector well. There is nothing to cross it with.
#   a screw beside the notch lands outside the cover's footprint, so
#   it would show on the backplate's face - the one thing forbidden.
#
# So the cap LAPS BEHIND the plate instead, overlapping the notch on its two
# sides and its deep end, and is screwed from the PCB side into tapped holes in
# the plate at the deep end, where there is solid metal and the cover is over
# the top. Its face then sits 2.00 mm below the backplate's rather than level
# with it - which was worth arguing about when the cover was 33.0 mm wide and
# left 4.3% of the notch showing, and stopped mattering once the widening put
# the cover over 99.6% of the notch on its own.
NOTCH_CAP_CLEAR = 0.40       # kept for the opening the cable rises through
CAP_LAP = 6.0                # overlap onto the plate, behind
CAP_SCREW_INSET = 3.0        # screw centres, past the notch's deep end
STRAP_LAP = 7.0
STRAP_W = 10.0


def notch_box():
    import backplate_v3 as B
    x0 = B.NOTCH_CX - B.NOTCH_W / 2.0 - B.NOTCH_EXTRA_BRACKET
    x1 = B.NOTCH_CX + B.NOTCH_W / 2.0
    return box(x0, 0.0, x1, B.NOTCH_D)


CAP_BRIDGE = 2.5             # material left at the deep end so the cap is one part


def notch_cap(path=None, half_out=None):
    """The flush filler, and the opening the cable comes up through.

    THE OPENING IS CENTRED ON THE NOTCH, NOT ON THE ROUTE. The notch was opened
    4 mm toward the bracket, so its centre sits 2.00 mm off the cable
    centreline. Centring the opening on the route instead leaves 5.85 mm of cap
    one side and 1.85 mm the other - and 1.85 mm is below the 2.0 mm minimum
    feature, so that cap cannot be cut. Centred on the notch it is 3.85 mm both
    sides, which can.

    A bridge is left across the deep end so the cap is ONE part rather than two
    loose slivers, and the whole opening is checked to sit inside the cover's
    outer footprint, because any part of it that stuck out would be a hole in
    the backplate in plain view.
    """
    path = route45() if path is None else path
    half_out = CARCASS_RIB_OUT if half_out is None else half_out
    nb = notch_box()
    x0, y0, x1, y1 = nb.bounds
    ncx = (x0 + x1) / 2.0
    n = nb.buffer(-NOTCH_CAP_CLEAR)
    op = box(ncx - CLEAR_W / 2, y0 - 1.0, ncx + CLEAR_W / 2, y1 - CAP_BRIDGE)
    # the cap laps BEHIND the plate: it is bigger than the notch on the two
    # sides and the deep end, which is what stops it falling through
    lap = box(x0 - CAP_LAP, y0, x1 + CAP_LAP, y1 + CAP_LAP + CAP_SCREW_INSET + 3.0)
    cap = lap.difference(op)
    # DEFECT 3: the lap ran over card fastener (171.28, 32.02) completely, so
    # that screw could not be driven. Notch the cap clear of every card hole it
    # reaches. The cap is hidden behind the plate, so an edge notch costs
    # nothing there - which is not true of any other part in this assembly.
    from hole_pattern import HOLES as _CARD
    import backplate_v3 as _B
    r = _B.BORE / 2.0 + MFG.COAT_ALLOWANCE + MFG.MIN_FEATURE
    for hx, hy, _t, _s in _CARD:
        c = Point(hx, hy).buffer(r, resolution=32)
        if cap.intersects(c):
            cap = cap.difference(c)
    web = min(op.bounds[0] - n.bounds[0], n.bounds[2] - op.bounds[2],
              n.bounds[3] - op.bounds[3])
    cover = box(path[0][0] - half_out, y0 - 2.0, path[0][0] + half_out, y1 + 2.0)
    outside = op.difference(cover).area
    return dict(cap=cap, opening=op, area=cap.area, web=web,
                covered=100.0 * cap.area / n.area,
                min_feature_ok=web >= MFG.MIN_FEATURE,
                opening_hidden=outside < 1e-6, outside=outside,
                cover_half=half_out)


def cap_screws(path=None, half_out=None):
    """Where the cap bolts up into the plate: past the notch, under the cover.

    Both must land on solid metal (y beyond the notch's depth), inside the
    cover's footprint, and clear of the 13 fasteners that hold the plate on.
    """
    path = route45() if path is None else path
    half_out = CARCASS_RIB_OUT if half_out is None else half_out
    nb = notch_box().bounds
    y = nb[3] + CAP_SCREW_INSET
    cx = path[0][0]
    out = []
    for dx in (-9.0, +9.0):
        out.append((cx + dx, y))
    return out


def notch_straps():
    """Kept only so older callers do not break; the cap laps behind now."""
    return []

SHOW = +1        # right of travel: the side the wordmark is read from
FAR = -1


# ---- offsetting the centreline ------------------------------------------
def _dirs(path):
    out = []
    for i in range(len(path) - 1):
        (ax, ay), (bx, by) = path[i], path[i + 1]
        L = math.hypot(bx - ax, by - ay)
        out.append(((bx - ax) / L, (by - ay) / L))
    return out


def offset(path, dist, sgn):
    """Offset a polyline of axis-aligned right-angle legs by dist on one side.

    sgn +1 is the RIGHT of travel. Each leg's offset line is intersected with
    its neighbour's, which for right angles is just a coordinate swap - but it
    is done by intersection so a non-orthogonal route would still be correct.
    """
    ds = _dirs(path)
    lines = []
    for (px, py), (dx, dy) in zip(path[:-1], ds):
        nx, ny = dy * sgn, -dx * sgn
        lines.append(((px + nx * dist, py + ny * dist), (dx, dy)))
    pts = [lines[0][0]]
    for i in range(len(lines) - 1):
        (p0, d0), (p1, d1) = lines[i], lines[i + 1]
        den = d0[0] * d1[1] - d0[1] * d1[0]
        t = ((p1[0] - p0[0]) * d1[1] - (p1[1] - p0[1]) * d1[0]) / den
        pts.append((p0[0] + d0[0] * t, p0[1] + d0[1] * t))
    (plast, dlast) = lines[-1]
    end = path[-1]
    nx, ny = dlast[1] * sgn, -dlast[0] * sgn
    pts.append((end[0] + nx * dist, end[1] + ny * dist))
    return pts


def turns(path):
    """+1 where the route turns LEFT, -1 where it turns RIGHT, per corner."""
    ds = _dirs(path)
    out = []
    for i in range(len(ds) - 1):
        (ax, ay), (bx, by) = ds[i], ds[i + 1]
        out.append(1 if (ax * by - ay * bx) > 0 else -1)
    return out


def deflections(path):
    """How far the route turns at each corner, in degrees."""
    ds = _dirs(path)
    out = []
    for i in range(len(ds) - 1):
        (ax, ay), (bx, by) = ds[i], ds[i + 1]
        out.append(abs(math.degrees(math.atan2(ax * by - ay * bx,
                                               ax * bx + ay * by))))
    return out


def chamfered(path, cut=None):
    """The same waypoints with each 90 replaced by two 45s."""
    cut = M.CABLE_CHAMFER if cut is None else cut
    ds = _dirs(path)
    out = [path[0]]
    for i in range(1, len(path) - 1):
        cx, cy = path[i]
        ux, uy = ds[i - 1]
        vx, vy = ds[i]
        out.append((cx - ux * cut, cy - uy * cut))
        out.append((cx + vx * cut, cy + vy * cut))
    out.append(path[-1])
    return out


# K factor, solved from the vendor's own published pair for this material:
# BD(90) = 2 x OSSB - BA, with OSSB = (R + T) tan(theta/2) and
# BA = theta_rad (R + K T). At 90 deg with R 0.97, T 2.00 and BD 2.95 that
# gives K = 0.4668. Needed because bend deduction is ANGLE DEPENDENT and 2.95
# is only the 90 degree figure - see deduction() below.
K_FACTOR = ((2 * (BEND_RADIUS + T) - BEND_DEDUCT) / (math.pi / 2)
            - BEND_RADIUS) / T


def deduction(theta_deg):
    """Bend deduction at an arbitrary bend angle.

    THIS IS WHY THE 45 QUESTION MATTERS BEYOND CORNER COUNT. 2.95 mm is the
    90 degree deduction. A 45 degree fold removes far less material from the
    flat, and developing a chamfered ribbon with the 90 degree number would
    cut every blank short by about 2 mm per fold.
    """
    th = math.radians(theta_deg)
    ossb = (BEND_RADIUS + T) * math.tan(th / 2.0)
    ba = th * (BEND_RADIUS + K_FACTOR * T)
    return 2 * ossb - ba


def ribbon(sgn, path=None):
    """One wall as a folded strip: its polyline, leg lengths, and flat blank.

    A strip folded only about vertical axes develops like any other bend: the
    flat length is the sum of the legs measured to the SHARP corners, less one
    bend deduction per fold. Nothing is attached along it, and each bend line
    runs the full width of the strip, so no bend needs relief - and that holds
    for ANY number of folds at ANY angle, which is the whole reason this
    architecture does not care whether the route turns 90 once or 45 twice.
    """
    path = route45() if path is None else path
    pts = offset(path, HALF_OUT, sgn)
    legs = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            for i in range(len(pts) - 1)]
    tn = turns(path)
    ang = deflections(path)
    # The side whose legs SHORTEN at a corner is the inside of the turn, so
    # it is concave there. t*sgn < 0 is exactly that case - checked against
    # the numbers: the show side goes 76.40 -> 62.40 at corner 1 (inside)
    # and 55.60 -> 69.60 at corner 2 (outside).
    kinds = ["concave" if t * sgn < 0 else "convex" for t in tn]
    bds = [deduction(a) for a in ang]
    flat = sum(legs) - sum(bds)
    return dict(pts=pts, legs=legs, kinds=kinds, flat=flat, angles=ang,
                deducts=bds, height=ZR - Z0, sgn=sgn,
                # bend-to-edge is +/-0.015 in and ADDITIVE per bend
                tol=0.381 * len(bds))


def top_plate(path=None):
    """The flat Z. No bends, therefore no relief, no kink, no bend tolerance."""
    path = route45() if path is None else path
    w = HALF_IN - SIDE_GAP
    a = offset(path, w, SHOW)
    b = offset(path, w, FAR)
    return Polygon(a + b[::-1]).buffer(0)


# ---- HOW IT STAYS TOGETHER ------------------------------------------------
# Every joint below was chosen against one rule that outranks the others: the
# show ribbon carries no hole, and no fastener head appears on any surface the
# owner can see from the chair. Everything else follows from that.
#
#   1  CLEAT -> BACKPLATE.  M2 x 4 driven from the PCB SIDE, up through a
#      2.30 mm clearance hole in the backplate, into an M2 x 0.4 tapped hole
#      in the cleat's foot. 2 mm of plate plus 2 mm of cleat is 4 mm, so the
#      tip finishes flush with the cleat's top face and nothing enters the
#      channel. The head sits under the backplate where the PCB is.
#      The other way round - tapping the backplate and driving from inside -
#      puts a head in the cable's way and a thread stub over the PCB.
#
#   2  FAR RIBBON -> CLEAT.  M2 x 4 driven from INSIDE the channel, through a
#      2.30 mm clearance hole in the cleat's upstand, into a tapped hole in
#      the far ribbon. 2 + 2 again, so it finishes flush on the outside face.
#      The far ribbon is allowed holes. The show ribbon is not, which is the
#      whole reason these two walls are fastened differently.
#
#   3  SHOW RIBBON -> CLEAT.  No fastener at all. 3M VHB over the cleat
#      upstand's full face, applied AFTER powder coat - every structural
#      adhesive worth using dies at cure temperature, and that constraint is
#      what forces the show ribbon to be finished as one uncut object before
#      anything touches it.
#
#   4  BOTH RIBBONS -> BACKPLATE, for position and shear.  Tabs on the
#      ribbon's bottom edge dropping into slots in the backplate. A tab is
#      OUTLINE, not a hole, so the show blank stays unbroken; the slot it
#      drops into is covered by the ribbon standing in it. The tabs locate;
#      the bond and the screws retain.
#
#   5  TOP PLATE.  SCREWED, at every cleat: M2 x 4 driven UP from beneath the
#      shelf into a tapped hole in the plate. Head inside the channel. On the
#      plate's upper face each one shows as a 2 mm circle - recessed 2.5 mm
#      below the ribbon tops, so invisible from a seated eye, and visible from
#      standing as four small dots down the middle of a recessed tray.
#
#      IT IS NOT CAPTURED MECHANICALLY, and an earlier version of this file
#      claimed it was. The idea was a return lip on the cleat that trapped the
#      plate's show edge. It cannot work here: the plate's edge sits at x 11.60
#      and the cleat's shelf only reaches out to x 10.00, so there is no plate
#      edge over the shelf to trap - and a lip rising from the shelf's INNER
#      end, where it was actually drawn, comes up through the middle of the
#      plate. Trapping the edge would need the shelf to reach past 11.60, which
#      means the upstand moves outboard into the ribbon. So: screws.
#
# The plate cannot lift (lip one side, screw the other), cannot slide (the
# screws), and cannot rack (the ribbons). Assembly order is forced and worth
# writing down: cleats to the backplate, far ribbon to the cleats, show ribbon
# bonded and tabbed, then the plate tilted in show-edge-first and screwed.

SCREW = "M2 x 0.4"
SCREW_LEN = 4.0
CLEAR_HOLE = 2.30       # M2 clearance, opened for powder coat build-up
# VERIFIED against sendcutsend.com/services/tapping/ : M2 x 0.4 is a listed
# sheet-metal thread and the hole they specify for it is 0.065 in = 1.651 mm.
# Their minimum material thickness for tapping is 0.059 in = 1.50 mm, so our
# 2.0 mm clears it by 0.50 mm. 2.0 / 0.4 = 5 full threads.
TAP_DIA = 1.65          # M2 x 0.4, the vendor's own 0.065 in
HEAD_H = 1.30           # M2 pan head, the figure that has to clear the PCB
VHB_T = 1.10            # 3M VHB, nominal


# ---- cleats ---------------------------------------------------------------
CLEAT_L = 40.0          # along the run; >= SCS 38.1 mm minimum part length
CLEAT_FOOT = 10.0       # lies flat on the backplate, one M2 through it
CLEAT_SHELF = 6.0       # reaches under the top plate
CLEAT_RISE = CLEAR_D - T


def cleat_flat(sgn=SHOW):
    """Foot + upstand + shelf. Two straight full-width bends, no relief.

    Both sides are the same part now. There is no return lip: see note 5 above
    for why one cannot reach the plate's edge from here.
    """
    across = CLEAT_FOOT + CLEAT_RISE + CLEAT_SHELF - 2 * BEND_DEDUCT
    return dict(across=across, length=CLEAT_L, bends=2, sgn=sgn, lip=False,
                ok=(min(across, CLEAT_L) >= MIN_PART[0]
                    and max(across, CLEAT_L) >= MIN_PART[1]))


def cleat_stations(path=None):
    """Where a cleat can sit: on a straight run, clear of both folds, on plate
    metal, clear of every backplate fastener and of the connector notch.

    Staggered - one side at a time - so the cable never loses shelf depth from
    both sides at the same station. It keeps CLEAR_W - CLEAT_SHELF at a cleat.
    """
    path = route45() if path is None else path
    import backplate_v3 as B
    from hole_pattern import HOLES
    nx0 = B.NOTCH_CX - B.NOTCH_W / 2.0 - B.NOTCH_EXTRA_BRACKET
    nx1 = B.NOTCH_CX + B.NOTCH_W / 2.0
    notch = box(nx0, -2.0, nx1, B.NOTCH_D + 2.0)
    plate = Polygon(B.outline())
    # A cleat is a SEPARATE part bonded or bolted to the ribbon's flat. It does
    # not have to respect BEND_KEEPOUT, which governs features on a part that
    # is itself being bent - it only has to clear the fold radius.
    clear = BEND_RADIUS + T + 4.0 + CLEAT_L / 2.0
    # MEASURE THE LEG THE CLEAT ACTUALLY SITS ON. A cleat bonds to the RIBBON,
    # and the ribbon's legs are not the centreline's: offsetting lengthens a
    # leg at a convex corner and shortens it at a concave one. On the 90 route
    # the show side runs 62.4/109.9/69.6 against a centreline 76.4/109.9/55.6,
    # and on the chamfered route the gap is wider still. Testing the centreline
    # rejects stations that fit and accepts stations that do not.
    inner = {s: offset(path, HALF_IN, s) for s in (SHOW, FAR)}
    out = []
    for i in range(len(path) - 1):
        sgn = SHOW if i % 2 == 0 else FAR
        pts = inner[sgn]
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        L = math.hypot(bx - ax, by - ay)
        room = L - 2 * clear
        if room < 0:
            out.append(dict(leg=i, sgn=sgn, short=L, need=2 * clear,
                            blocked=True, reason="leg too short for a cleat"))
            continue
        n = max(1, int(room // 55.0) + 1)
        dx, dy = (bx - ax) / L, (by - ay) / L
        nx, ny = -dy * sgn, dx * sgn            # inward, into the channel
        for k in range(n):
            t = (clear + room * (k + 0.5) / n) / L
            px, py = ax + (bx - ax) * t, ay + (by - ay) * t
            anchor = (px, py)                   # on the ribbon's inner face
            foot = (px + nx * CLEAT_FOOT / 2, py + ny * CLEAT_FOOT / 2)
            shelf = (px + nx * (T + CLEAT_SHELF / 2),
                     py + ny * (T + CLEAT_SHELF / 2))
            bad = (notch.contains(Point(foot)) or not plate.contains(Point(foot))
                   or min(math.hypot(foot[0] - hx, foot[1] - hy)
                          for hx, hy, _t, _s in HOLES) < 8.0)
            out.append(dict(leg=i, mid=(px, py), anchor=anchor, foot=foot,
                            shelf=shelf, sgn=sgn, dir=(dx, dy), blocked=bad,
                            reason="notch / fastener / off plate" if bad else "",
                            lip=False))
    return [c for c in out if not c["blocked"]]


def cleat_problems(path=None):
    """Legs that cannot take a cleat, and by how much they miss."""
    path = route45() if path is None else path
    import backplate_v3 as B
    from hole_pattern import HOLES
    clear = BEND_RADIUS + T + 4.0 + CLEAT_L / 2.0
    inner = {s: offset(path, HALF_IN, s) for s in (SHOW, FAR)}
    bad = []
    for i in range(len(path) - 1):
        sgn = SHOW if i % 2 == 0 else FAR
        pts = inner[sgn]
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        L = math.hypot(bx - ax, by - ay)
        if L < 2 * clear:
            bad.append(dict(leg=i + 1, side="show" if sgn == SHOW else "far",
                            have=L, need=2 * clear, short=2 * clear - L))
    return bad


def max_chamfer(path=None, want=3):
    """The largest chamfer that still leaves room for `want` cleats.

    Worth computing rather than guessing, because the chamfer size was chosen
    for the CABLE and it turns out to govern whether the cover can be held on
    at all: cut 30 mm and no leg on either ribbon is long enough for a 40 mm
    cleat, so the 45 route as currently dimensioned has nothing to bolt to.
    """
    path = route45() if path is None else path
    best = None
    c = 0.5
    while c <= 40.0:
        n = len(cleat_stations(chamfered(path, c)))
        if n >= want:
            best = (c, n)
        c += 0.5
    return best


def fasteners(path=None):
    """Every screw in the assembly, with what it joins and which way it goes.

    Direction matters more than position here. Each one is driven from the
    side that leaves its head on a surface nobody looks at, and each is 4 mm
    into 2 + 2 mm of stock so no tip ever stands proud.
    """
    path = route45() if path is None else path
    out = []
    for c in cleat_stations(path):
        side = "show" if c["sgn"] == SHOW else "far"
        out.append(dict(at=c["foot"], z=Z0, joins="cleat -> backplate",
                        drive="up from the PCB side", size=SCREW,
                        length=SCREW_LEN, clear_in="backplate",
                        tapped_in="cleat foot", side=side,
                        head="under the backplate"))
        out.append(dict(at=c["shelf"], z=ZT, joins="top plate -> cleat",
                        drive="up from under the shelf", size=SCREW,
                        length=SCREW_LEN, clear_in="cleat shelf",
                        tapped_in="top plate", side=side,
                        head="inside the channel"))
        if c["sgn"] == FAR:
            out.append(dict(at=c["anchor"], z=Z0 + CLEAR_D / 2,
                            joins="far ribbon -> cleat",
                            drive="outward from inside the channel",
                            size=SCREW, length=SCREW_LEN,
                            clear_in="cleat upstand", tapped_in="far ribbon",
                            side=side, head="inside the channel"))
    return out


def bonds(path=None):
    """The show ribbon's only attachment, and why it is not a screw."""
    return [dict(at=c["anchor"], area=CLEAT_L * (CLEAR_D - T),
                 tape="3M VHB %.1f mm" % VHB_T)
            for c in cleat_stations(path) if c["sgn"] == SHOW]


# ---- locating tabs on the ribbon foot -------------------------------------
TAB_L = 12.0
TAB_W = T
# SLOT SIZING, from the stack rather than from a round number.
#
# ACROSS the run the tab's position does NOT accumulate: it is set by where the
# skin bonds to the downstand, which is local. So across needs only clearance -
# four coated surfaces meet in this joint, so 4 x COAT_ALLOWANCE, symmetric.
#
# ALONG the run it DOES accumulate: the skin is one strip with four folds and
# bend-to-edge is +/-0.381 mm per bend, additive. carcass_ribbon() has computed
# and returned that number the whole time and no caller ever read it. Total
# slack was 0.30 mm against a tol of 1.524 - five times too tight - so the nine
# tabs could not all enter their nine slots.
#
# The old 0.30 mm was worse than it looked: SLOT_BIAS pushed ALL of it inboard
# to hide the slot, leaving the outboard faces line-to-line, and powder coat
# then took the fit 0.30 mm NEGATIVE.
# 4 x COAT_ALLOWANCE exactly CANCELS - coated tab 2.30 into coated slot 2.30 is
# zero, not a fit. A real clearance has to sit on top of it.
SLOT_FIT = 0.20                              # clearance remaining AFTER coating
# ACROSS THE SLOT, NOTHING WAS SIZED AT ALL. SLOT_FIT is a fit allowance, not
# a tolerance budget, and it left 0.100 mm per side once both faces are coated.
# What moves the tab sideways is the BOND LINE: the skin stands off the wall by
# the tape's thickness, so the tape's thickness tolerance goes straight into
# the tab's position. 2.30 mm of VHB at the usual +/-10% is +/-0.23 mm on its
# own - more than twice the clearance there was - and a degree of bend angle
# adds about 0.13 over the height of the skin.
#
# ASSUMPTION, STATED: +/-10% is the figure commonly quoted for VHB thickness
# and it is NOT taken from a datasheet here. If the real number is tighter this
# slot can shrink; if it is looser this slot is still not enough. It is written
# as a stack so it can be corrected in one place rather than re-derived.
# AND THE CARCASS MOVES TOO. The first version of this stack had the bond line
# and a bend angle in it and stopped there, which quietly assumed the wall the
# skin bonds to is exactly where the drawing puts it. It is not: the wall's
# lateral position relative to the plate is set by the foot that is bonded down
# and the ONE fold between that foot and the wall, and bend-to-edge on this
# material is +/-0.381 mm per bend. That is the largest term in the stack and
# it was missing, which is how the budget came out at 0.360 against a
# requirement of 0.360 - exactly zero margin, and the check passed.
BEND_TOL = 0.381                             # per bend, additive
BOND_TOL = 0.23              # +/-10% of the 2.30 mm tape - see above
BEND_ANGLE_TOL = 1.0         # degrees, typical press brake
SKIN_TILT = round(9.5 * math.tan(math.radians(BEND_ANGLE_TOL)), 3)   # 0.166
CARCASS_TOL = BEND_TOL       # one fold from the bonded foot to the wall
# WORST CASE, not root-sum-square. These are three independent tolerances and
# RSS would give 0.476 rather than 0.777, which is the honest number if you
# care about the average part. This joint has to go together on the first
# attempt with adhesive already curing, and the only cost of being wrong in
# the safe direction is a wider slot that is hidden under the cover.
SLOT_ACROSS = BOND_TOL + SKIN_TILT + CARCASS_TOL


def nearest_wall(x, y, path=None):
    """(leg, sgn) of the channel wall nearest a plan point.

    So a clearance measured at a point can be compared with the tolerance
    stack THAT wall actually carries - which depends on which leg it is and
    whether the leg's staggered foot is on this side or the other.
    """
    path = route45() if path is None else path
    best = None
    for i in range(len(path) - 1):
        (ax, ay), (bx, by) = path[i], path[i + 1]
        L = math.hypot(bx - ax, by - ay) or 1.0
        ux, uy = (bx - ax) / L, (by - ay) / L
        t = max(0.0, min(L, (x - ax) * ux + (y - ay) * uy))
        px, py = ax + ux * t, ay + uy * t
        dd = math.hypot(x - px, y - py)
        cross = ux * (y - ay) - uy * (x - ax)
        sgn = SHOW if cross < 0 else FAR
        if best is None or dd < best[0]:
            best = (dd, i, sgn)
    return best[1], best[2]


def carcass_bends_to_foot(leg, sgn):
    """Section bends between the leg's BONDED foot and the wall on side sgn.

    CARCASS_TOL is one BEND_TOL, described as "one fold from the bonded foot
    to the wall". That is true only on the side the foot is on. The feet are
    STAGGERED - one per station - so on the other side of the same leg the
    chain runs foot -> its own wall -> top face -> this wall: three bends, not
    one, and the tolerance is 1.143 mm rather than 0.381.

    Two of the nine tab slots sit on such a wall (far leg 2, at flat 129.40 and
    149.37), and so does the card washer at (171.28, 32.02) - which the guard
    passed by 0.033 mm against a stack that was 1.9x too small.
    """
    return 1 if sgn == foot_side_for(leg) else 3


def slot_across_for(leg, sgn):
    """The across-stack a slot at this station actually has to swallow."""
    return BOND_TOL + SKIN_TILT + BEND_TOL * carcass_bends_to_foot(leg, sgn)


def slot_w_for(leg, sgn):
    """The slot width that follows from it."""
    return TAB_W + 4 * MFG.COAT_ALLOWANCE + 2 * slot_across_for(leg, sgn)
SLOT_W = TAB_W + 4 * MFG.COAT_ALLOWANCE + 2 * SLOT_ACROSS   # 3.32
SLOT_L_MIN = TAB_L + 4 * MFG.COAT_ALLOWANCE + SLOT_FIT  # 12.80 at the datum
SLOT_L = SLOT_L_MIN                          # kept for older callers
# The slot has to be wider than the tab or the tab will not go in, so it can
# never hide completely under a skin of the tab's own thickness. Bias it INWARD
# by the whole difference: the slot's outer edge then lines up exactly with the
# skin's outer face, and all 0.30 mm of the clearance opens into the channel
# where nobody can see it, instead of 0.15 mm showing on each side.
# NO BIAS. It existed to hide the slot behind the skin, and it is exactly what
# made the joint interfere: all the clearance on one side means none on the
# other. Symmetric, and the 0.30 mm a side that now shows is the honest cost of
# a joint that can actually be assembled after coating.
SLOT_BIAS = 0.0


def tab_stations(path=None):
    """Tabs on the ribbon's BOTTOM edge, dropping into slots in the backplate.

    The show member carries the TAB and never the SLOT. A tab is outline, not a
    hole - the show ribbon keeps a blank face with nothing cut into it - and
    the slot it drops into is covered by the ribbon standing in it. The tabs
    set plan position and carry shear; the bond and the screws retain.
    """
    path = route45() if path is None else path
    import backplate_v3 as B
    from hole_pattern import HOLES
    plate = Polygon(B.outline())
    notch = notch_box()
    half = CARCASS_RIB_OUT - T / 2.0
    out = []
    for sgn in (SHOW, FAR):
        pts = offset(path, half, sgn)                   # mid-thickness
        for i in range(len(pts) - 1):
            # NOT ON THE FOOT'S SIDE. The feet are outward now and lie
            # exactly where a tab would drop through the plate.
            if sgn == foot_side_for(i):
                continue
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            L = math.hypot(bx - ax, by - ay)
            # TWO STATIONS ON A LONG LEG, ONE IN THE MIDDLE OF A SHORT ONE.
            # The tabs now sit opposite the feet, which is the INSIDE of each
            # turn, where a leg is 10.4 mm shorter than on the outside: legs
            # 1 and 3 are 27.8 mm there against the 33.98 two-station rule and
            # got nothing. A single centred tab on 27.8 mm still keeps 7.9 mm
            # to each corner, past the 5.99 keep-out.
            if L >= 2 * BEND_KEEPOUT + TAB_L + 10:
                fracs = (0.30, 0.70)
            elif L >= 2 * BEND_KEEPOUT + TAB_L:
                fracs = (0.50,)
            else:
                continue
            for t in fracs:
                px, py = ax + (bx - ax) * t, ay + (by - ay) * t
                # A SLOT NEEDS METAL. The first version placed tabs anywhere
                # along the skin, and three of them landed in the connector
                # notch's void - a slot cut in thin air, holding nothing.
                # Sized with THIS station's slot width, not the old global.
                g = Point(px, py).buffer(max(SLOT_L, slot_w_for(i, sgn)) / 2
                                         + MFG.MIN_FEATURE)
                if notch.intersects(g) or not plate.contains(g):
                    continue
                if min(math.hypot(px - hx, py - hy)
                       for hx, hy, _t, _s in HOLES) < 8.0:
                    continue
                out.append(dict(sgn=sgn, at=(px, py),
                                dir=((bx - ax) / L, (by - ay) / L)))
    return out


# ---- geometry for the 3D viewer ------------------------------------------
def _box(cx, cy, cz, ux, uy, along, across, height):
    """A small rectangular prism, used to draw a screw at viewer scale.

    A screw is not worth a cylinder here - four quads read correctly at the
    sizes this viewer works at, and the point is WHERE the hardware is and
    which way it points, not what its head looks like.
    """
    px, py = -uy, ux
    hx, hy = ux * along / 2, uy * along / 2
    gx, gy = px * across / 2, py * across / 2
    a = (cx - hx - gx, cy - hy - gy)
    b = (cx + hx - gx, cy + hy - gy)
    c = (cx + hx + gx, cy + hy + gy)
    d = (cx - hx + gx, cy - hy + gy)
    z0, z1 = cz, cz + height
    out = []
    for p, q in ((a, b), (b, c), (c, d), (d, a)):
        out.append(((p[0], p[1], z0), (q[0], q[1], z0),
                    (q[0], q[1], z1), (p[0], p[1], z1)))
    return out


def mesh(path=None, hardware=False):
    """(top polygons at ZP, body quads) - the same contract the other covers use.

    The ribbons are pure quads: they have no top face of their own, which is
    the whole point. The only horizontal surface in the assembly is the plate,
    and it is never bent.

    With hardware=True the cleats are drawn as the L or C they actually are -
    foot, upstand, shelf, and on the show side the return lip that traps the
    plate - and every screw is drawn on its real axis, so the viewer shows the
    thing that holds it together rather than implying it.
    """
    path = route45() if path is None else path
    tops = [top_plate(path)]
    body = []
    for sgn in (SHOW, FAR):
        pts = ribbon(sgn, path)["pts"]
        for i in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            body.append(((ax, ay, Z0), (bx, by, Z0),
                         (bx, by, ZR), (ax, ay, ZR)))
    for c in cleat_stations(path):
        ux, uy = c["dir"]
        nx, ny = -uy * c["sgn"], ux * c["sgn"]      # inward, into the channel
        ax, ay = c["anchor"]
        c0 = (ax - ux * CLEAT_L / 2, ay - uy * CLEAT_L / 2)
        c1 = (ax + ux * CLEAT_L / 2, ay + uy * CLEAT_L / 2)
        # upstand, standing on the backplate against the ribbon's inner face
        body.append(((c0[0], c0[1], Z0), (c1[0], c1[1], Z0),
                     (c1[0], c1[1], ZT), (c0[0], c0[1], ZT)))
        if not hardware:
            continue
        # foot, lying flat on the backplate and reaching into the channel
        f0 = (c0[0] + nx * CLEAT_FOOT, c0[1] + ny * CLEAT_FOOT)
        f1 = (c1[0] + nx * CLEAT_FOOT, c1[1] + ny * CLEAT_FOOT)
        body.append(((c0[0], c0[1], Z0), (c1[0], c1[1], Z0),
                     (f1[0], f1[1], Z0), (f0[0], f0[1], Z0)))
        # shelf, bent off the top of the upstand - whose inner face is one
        # thickness in from the ribbon, not at the ribbon face
        u0 = (c0[0] + nx * T, c0[1] + ny * T)
        u1 = (c1[0] + nx * T, c1[1] + ny * T)
        s0 = (u0[0] + nx * CLEAT_SHELF, u0[1] + ny * CLEAT_SHELF)
        s1 = (u1[0] + nx * CLEAT_SHELF, u1[1] + ny * CLEAT_SHELF)
        body.append(((u0[0], u0[1], ZT), (u1[0], u1[1], ZT),
                     (s1[0], s1[1], ZT), (s0[0], s0[1], ZT)))
    if hardware:
        for f in fasteners(path):
            x, y = f["at"]
            if f["joins"] == "far ribbon -> cleat":
                # driven sideways: draw it lying along the wall normal
                body += _box(x, y, f["z"] - 1.0, 1.0, 0.0,
                             SCREW_LEN, 2.0, 2.0)
            else:
                body += _box(x, y, f["z"] - SCREW_LEN, 1.0, 0.0,
                             2.0, 2.0, SCREW_LEN)
    return tops, body


# ---- report ---------------------------------------------------------------
def report():
    sh, fr = ribbon(SHOW), ribbon(FAR)
    tp = top_plate()
    print("RIBBON AND PLATE - no wall is bent off the top face\n")
    for nm, rb in (("SHOW ribbon (mark side)", sh), ("FAR  ribbon", fr)):
        print("  %s" % nm)
        print("     legs      %s mm" % "  ".join("%.2f" % L for L in rb["legs"]))
        print("     folds     %s" % "; ".join(
            "corner %d %s (route turns %s)"
            % (i + 1, k, "left" if t > 0 else "right")
            for i, (k, t) in enumerate(zip(rb["kinds"], turns(PATH)))))
        print("     FLAT BLANK  %.2f x %.2f mm   (%d legs - %d x %.2f deduction)"
              % (rb["flat"], rb["height"], len(rb["legs"]),
                 len(rb["legs"]) - 1, BEND_DEDUCT))
        print("     bend reliefs required: 0   (every bend is full-width)")
        print("     holes in the blank: %d" % (0 if rb["sgn"] == SHOW else 0))
    same = abs(sh["flat"] - fr["flat"]) < 1e-6
    print("\n  both blanks develop to the SAME length (%.2f mm): %s" %
          (sh["flat"], "yes" if same else "no"))
    print("     the +2d at a convex corner and the -2d at a concave one cancel")
    print("     exactly on a Z route. They are still two different parts -")
    print("     the legs split differently - but they nest as one strip.")

    print("\n  TOP PLATE   %.2f cm2, %.1f mm wide, ZERO bends" %
          (tp.area / 100, 2 * (HALF_IN - SIDE_GAP)))
    print("     a part with no bend has no relief, no kink, and no bend")
    print("     tolerance stack. It is a laser part end to end.")

    cf = cleat_flat()
    st = cleat_stations()
    live = [c for c in st if not c["blocked"]]
    print("\n  CLEATS      %d placed, %d blocked (notch / fastener / off plate)"
          % (len(live), len(st) - len(live)))
    print("     flat %.2f x %.2f mm, two straight full-width bends, 0 reliefs"
          % (cf["across"], cf["length"]))
    print("     SCS minimum flat part %.2f x %.2f mm ..... %s"
          % (MIN_PART[0], MIN_PART[1], "PASS" if cf["ok"] else "FAIL"))
    for c in live:
        print("       (%6.1f, %5.1f)  %s side" %
              (c["mid"][0], c["mid"][1], "show" if c["sgn"] == SHOW else "far "))
    print("     the shelf sits at the TOP of the channel, so over its %.1f mm"
          % CLEAT_SHELF)
    print("     reach it costs HEIGHT, not width: %.1f mm there against the"
          % (CLEAR_D - T))
    print("     full %.1f elsewhere. Staggered, so never both sides at once."
          % CLEAR_D)

    tb = tab_stations()
    print("\n  LOCATING TABS  %d, all on ribbon bottom edges" % len(tb))
    print("     %.1f x %.1f mm into slots in the BACKPLATE, %d on the show"
          % (TAB_L, TAB_W, sum(1 for t in tb if t["sgn"] == SHOW)))
    print("     ribbon. The show member carries TABS and never SLOTS - a tab")
    print("     is outline, not a hole, so the blank stays unbroken.")

    print("\n  HEIGHTS above the backplate face")
    print("     cable clear    %.2f mm" % CLEAR_D)
    print("     plate soffit   %.2f      plate top %.2f" % (ZT - PLATE_T, ZP - PLATE_T))
    print("     ribbon top     %.2f      reveal    %.2f mm deep, %.2f wide"
          % (ZR - PLATE_T, REVEAL, SIDE_GAP))
    print("     the one-piece hat stood %.2f. This stands %.2f - CHECK THE GLASS."
          % (CLEAR_D + T, ZR - PLATE_T))

    print("\n  DFM")
    print("     bend reliefs in the whole assembly ............ 0")
    print("     corner gaps on either wall .................... 0")
    print("     turn openings (cover_corner had two of 28 mm) . 0")
    print("     seams crossing the show wall ................. 0")
    print("     holes in the show ribbon ...................... 0")
    print("     outside corner radius ......................... %.2f mm"
          % (BEND_RADIUS + T))
    print("     bend-to-edge +/-0.381 mm, additive over 2 folds  +/-%.3f mm"
          % (2 * 0.381))
    print("     bend angle +/-1 deg leans a %.1f mm wall ....... +/-%.2f mm"
          % (ZR - Z0, (ZR - Z0) * math.tan(math.radians(1))))

    print("\n  DOES THE 45 ROUTE CHANGE ANY OF THIS?")
    print("     The eight researchers were briefed on the 90 route only, so")
    print("     none of them answered it. Run it and see.\n")
    ch = chamfered(PATH)
    for nm, pth in (("90 route (committed)", PATH),
                    ("45 route (chamfered %.0f mm)" % M.CABLE_CHAMFER, ch)):
        r = ribbon(SHOW, pth)
        print("     %-28s folds %d   angles %s deg"
              % (nm, len(r["angles"]),
                 " ".join("%.0f" % a for a in r["angles"])))
        print("        deduction per fold   %s mm"
              % "  ".join("%.2f" % d for d in r["deducts"]))
        print("        show blank           %.2f x %.2f mm"
              % (r["flat"], r["height"]))
        print("        bend-to-edge, added  +/-%.3f mm" % r["tol"])
        print("        bend reliefs         0")
    a, b = ribbon(SHOW, PATH), ribbon(SHOW, ch)
    print("\n     Both are ZERO relief. A fold is a fold, and every one of them")
    print("     is still full width, so the architecture does not care which")
    print("     route it follows. What the 45s cost is TOLERANCE: %d folds"
          % len(b["angles"]))
    print("     instead of %d, and bend-to-edge is additive, so +/-%.3f mm"
          % (len(a["angles"]), a["tol"]))
    print("     becomes +/-%.3f mm end to end on a %.0f mm strip."
          % (b["tol"], b["flat"]))
    print("     And watch the deduction: %.2f mm at 90, %.2f mm at 45."
          % (deduction(90), deduction(45)))
    print("     Developing a chamfered ribbon with the 90 figure would cut it")
    print("     %.2f mm short PER CORNER." % (2 * (deduction(90) - deduction(45))))

    print("\n  DOES THE CABLE FIT? Measured 2026-08-28, so this is no longer")
    print("  an assumption.")
    bw, bh = M.BUNDLE_W, M.BUNDLE_H
    cw, cd = CLEAR_W - 0.254, CLEAR_D - 0.254      # worst-case powder build-up
    print("     bundle  %.1f x %.1f mm      channel %.2f x %.2f after powder"
          % (bw, bh, cw, cd))
    print("     straight run   %+.2f mm on width (%.2f a side), %+.2f on height"
          % (cw - bw, (cw - bw) / 2, cd - bh))
    print("     over a foot    the foot sits at FLOOR level, so it costs")
    print("                    height, not width: %.2f clear, %+.2f spare"
          % (cd - T, cd - T - bh))
    area = bw * bh
    print("     through a corner, where it stops being flat: %.0f mm2 of"
          % area)
    print("     section, which fully round would be %.2f mm dia and fits"
          % (2 * math.sqrt(area / math.pi)))
    print("     NEITHER axis - so it stays partly flattened, and the height")
    print("     is where the extra goes. Area-preserving:")
    for h in (7.0, 8.0, 9.0, 10.0):
        w = area / h
        print("        %5.2f tall -> %5.2f wide   %s"
              % (h, w, "fits" if (w <= cw and h <= cd) else "FOULS"))
    print("     THAT is what the %.1f mm depth is for. It reads as slack next"
          % CLEAR_D)
    print("     to a 6 mm bundle and it is not: take it out and the corners")
    print("     have nowhere to put the material.")



# ---- the carcass variant, for routes whose legs are too short for a cleat --
# WHY THIS EXISTS
#     A 40 mm cleat needs 53.9 mm of straight ribbon to sit on. Chamfer the
#     route 30 mm and the longest leg on either ribbon is 52.4 mm - it misses
#     by 1.6 mm - and the other four miss by 4 to 23 mm. The 45 route has
#     NOTHING to bolt to. Shrinking the chamfer until three cleats fit takes it
#     down to 6.5 mm, which is not a chamfer anyone asked for, and the cleat
#     cannot be shortened either: SendCutSend's minimum flat part is
#     0.375 x 1.5 in, and a cleat's flat is only 18.6 mm across.
#
#     So for the 45 route the cleat goes, and rank 2 from the research takes
#     over: let the INNER part carry every relief, seam and fastener, and let
#     the outer skin be one continuous surface with nothing in it.
#
# WHAT CHANGES
#     The top plate stops being a bare flat Z and becomes a shallow carcass -
#     a top face with a continuous downstand flange each side, bent to the
#     backplate and footed. Those flanges DO have kinked bend lines, so they
#     DO take ordinary corner relief. Every one of those reliefs sits behind a
#     ribbon and cannot be seen. The ribbons stay exactly what they were:
#     strips folded about vertical axes, no relief, no holes on the show side.
#
#     It is better on the one risk entry 1 could not answer. A cleated ribbon
#     is bonded at two patches and is free to bow between them; a carcass gives
#     the show ribbon a continuous bonding face down its whole 236 mm.
#
# WHAT IT COSTS
#     Width. The cable still needs 24 mm clear, so the downstands sit at +/-12
#     and the ribbon lands outboard of them: 33.0 mm overall against 28.0. That
#     is 5 mm more of the vent field under cover, and it is the honest price.

# ---- the reveal, sized from the tolerance stack rather than from taste ----
# Research entry 3 specified a 2.5 x 2.5 mm groove and showed the arithmetic:
# a 1.0 mm nominal reveal ranges 0.2-1.8 mm once the stack is applied, a 9:1
# swing that reads unambiguously as a broken part, while 2.5 mm ranges 1.7-3.3,
# a 1.9:1 swing. The eye judges parallelism pre-consciously, so a wide gap held
# constant beats a narrow one that wanders. 1 arcmin at 300 mm resolves
# 0.087 mm - a 0.4 mm taper along the run is plainly visible.
#
# The first build took the 2.5 mm DEPTH and left the WIDTH at 0.50 mm, which is
# the bond line, i.e. a manufacturing minimum wearing the name of a designed
# reveal. This is the width put right.
# THE REVEAL WIDTH IS THE BOND LINE, and that is a real constraint, not a
# detail. The skin bonds flat to the downstand's outer face, so the open slot
# you see from above IS the gap the tape has to fill - they are the same
# dimension and cannot be set independently while the skin bonds that way.
#
# So it has to be a thickness tape is actually made in. VERIFIED against 3M:
#
#   VHB 4991   90 mil = 2.30 mm   GREY    "attaching metal panels to frames
#                                          and stiffener attachment"
#   VHB 4959  120 mil = 3.00 mm   WHITE ONLY - no grey or black version
#   VHB 5962   62 mil = 1.60 mm   black
#   VHB 5952   43 mil = 1.10 mm   black
#
# 2.30 it is. It clears entry 3's 2.0 mm floor, sits just under its 2.5 mm
# recommendation, and 3M's own stated application for it is the one we have.
#
# COLOUR DECIDED IT, not width. 3.0 mm scores better on entry 3's uniformity
# metric (+/-27% against +/-32%) but 4959 comes in white only, and a white line
# in a groove on a RAL 9003 gloss white part reads as a smear rather than a
# shadow. Grey reads as a shadow, which is what entry 4 asked for when it said
# to put something flat and dark behind every reveal. There is no black VHB at
# either 2.3 or 3.0 - black stops at 1.60 mm, below the floor.
#
# YOU WILL SEE THE TAPE'S EDGE. It sits 2.00 mm down the groove (the top face's
# own thickness), so in a 2.30 mm slot it comes into view past
# arctan(2.00/2.30) = 41 deg. Seated is 10-25 deg and sees nothing; standing is
# 50-65 deg and sees a grey line in the bottom of the reveal. That is a choice,
# not an accident - the alternative was white.
REVEAL_W = 2.3                 # the groove's width; equals the bond line here
BOND_TAPE = "3M VHB 4991, 2.30 mm, grey"

CARCASS_BOND = REVEAL_W        # the skin stands off the downstand by the reveal
# 8.0 -> 10.0 and STAGGERED, 2026-08-30.
#
# OUTWARD FEET ARE NOT AVAILABLE, which is what the audit's fix assumed. The
# skin bonds to the downstand's OUTER face across a 2.3 mm bond line, so a foot
# turned outward runs 14.0 -> 22.0 and passes straight through the skin. Making
# room means moving the skin out 8 mm a side: a 52.6 mm cover.
#
# So the feet stay inward and alternate sides instead, the way cover_split
# staggered its tabs. At any station there is one foot, not two:
#     both sides   24 - 2*10 =  4 mm aperture
#     staggered    24 - 10   = 14 mm aperture, against a 22 x 6 flexible bundle
# which is a roll-on rather than threading 200 mm through four corners.
#
# THE FOOT IS BONDED, NOT SCREWED, and 8.0 is what that allows. There is no
# foot size that does both:
#
#     foot   screw window   aperture   cable squeezed to it
#      8.0      -1.76 mm      16.0        8.25   fits, no legal screw
#     10.0      +0.24 mm      14.0        9.43   window under the +/-0.381
#                                                bend tolerance: a coin toss
#     12.0      +2.24 mm      12.0       11.00   screw fine, CABLE WILL NOT FIT
#
# Every foot big enough to carry an M2 clear of the 5.99 mm bend keep-out is
# too big for a 22 x 6 bundle to get past. So the feet take the same VHB as
# the skins, which also removes 8 tapped holes from the carcass and 8
# clearance holes from the backplate's show face.
# FEET OUT, decided 2026-09-01 (option b). The inward return lip broke two of
# SendCutSend's published bending rules for 0.080 in 5052 - return flange no
# more than half its base (12.5/8.0 = 1.56:1) and same-direction parallel
# bends at least 2 x the flat minimum flange apart (9.55 against 12.95) - and
# three independent punch models put a 30 degree sword 2.2-2.8 mm into the
# foot at 90 degrees. Turned OUTWARD the foot is a plain flange on a hat
# section: no return, opposite-sense bends, nothing in the punch's way.
#
# CARCASS_FOOT is now the foot's FORMED length measured from the wall's OUTER
# face to the tip - the vendor's own definition of a flange length - and 8.0
# sits on their 7.95 mm minimum. It cannot be shorter. In plan the foot
# occupies radius CARCASS_HALF_DS..CARCASS_HALF_DS + CARCASS_FOOT = 14.0..22.0,
# and the skin's outer face is at 18.6, so 3.40 mm of foot shows beyond the
# skin along every footed leg. That lip is part of this design.
CARCASS_FOOT = 8.0             # OUTWARD foot, formed, from the wall's outer face (SHOW side)
# 50/50, decided 2026-09-02: the SHOW side's feet stay on tape at 8.0; the
# FAR side's feet grow to take two M2.5 screws each and carry no tape. A
# screw needs the hole's edge BEND_KEEPOUT from the bend and MIN_FEATURE of
# web to the tip: 5.99 + 2.9 + 2.0 = 10.9, so 11.0. The head (4.7 button)
# lands 0.49 mm outside the skin's outer face; the lip beyond the skin is 6.4.
# ...except that the 5.99 keep-out is a FLAT-PATTERN rule (half the die
# width either side of the bend line in the blank), and the foot's flat is
# BD/2 shorter than its formed length. In the flat the far foot needs
# 5.99 + 2.9 + 2.0 = 10.89 past the bend line: formed, 10.89 + 1.475 = 12.4.
FOOT_LEN = {SHOW: 8.0, FAR: 12.5}
FOOT_SCREW = "M2.5 x 0.45"
FOOT_SCREW_CLEAR = 2.9         # clearance in the foot, opened for powder
FOOT_SCREW_TAP = 2.05          # tap drill in the plate; the vendor taps
FOOT_SCREW_HEAD = 4.7          # button head
FOOT_SCREW_END = 6.0           # first/last screw this far from the foot's ends
FOOT_SCREW_MIN_PITCH = 12.0    # two screws only if they can sit this far apart
SCREW_BORE_CLEAR = 8.0         # hardware.py's rule: keep this far from card bores


def foot_len(sgn):
    """Formed foot length on this side."""
    return FOOT_LEN[sgn]


def foot_dev(sgn):
    """(formed oml, developed flat, blank edge depth) for this side's foot."""
    d = carcass_dev()
    oml = foot_len(sgn)
    flat = oml - BEND_DEDUCT / 2.0
    return oml, flat, d["fold2"] + flat
FOOT_MIN_FORMED = 7.95         # SendCutSend, 0.080 in 5052, formed flange @ 90
assert CARCASS_FOOT >= FOOT_MIN_FORMED
TAB_FOOT_GAP = 1.0             # foot stops this far short of a tab's slot
FOOT_SEG_MIN = 8.0             # a foot piece shorter than this is dropped
WALL_SEG_MIN = 8.0             # ...and so is a wall whose fold is shorter: the
                               # leg-4 far wall came out 4.0 x 11.0 mm, a 44 mm2
                               # stub the skin covers anyway, and its 4.00 mm
                               # fold line was the shortest thing in the file
SKIN_FOOT_GAP = 0.3            # skin's stepped bottom edge clears the foot top
CARCASS_HALF_IN = CLEAR_W / 2                      # 12.0, downstand inner face
CARCASS_HALF_DS = CARCASS_HALF_IN + T              # 14.0, downstand outer face
# THE BOND LINE DOES NOT SIT ON BARE METAL. Both parts are powder coated
# before they are assembled, so the stack outward from the wall's outer face
# is: coat, tape, coat, and only then the skin's own metal. This constant read
# CARCASS_HALF_DS + CARCASS_BOND, which omits both coats - 0.30 mm - and the
# nine tab slots are placed from it. The coated tab is 2.30 mm thick and the
# coated slot opening is 2.50, so 0.30 of misplacement against 0.10 of side
# clearance means NONE of the nine tabs enters its slot. The tabs are the
# whole shear path on a cover with no screws.
#
# Same mistake as the washer clearance two rounds ago: a dimension taken on
# metal that will not exist by the time anything is assembled.
CARCASS_RIB_IN = (CARCASS_HALF_DS + MFG.COAT_ALLOWANCE
                  + CARCASS_BOND + MFG.COAT_ALLOWANCE)   # 16.60 bare inner face
CARCASS_RIB_OUT = CARCASS_RIB_IN + T                     # 18.60 outer face
CARCASS_W = 2 * CARCASS_RIB_OUT                          # 37.20 overall
CORNER_RELIEF = 1.60           # the VENDOR minimum, and NOT sufficient here -
                               # see relief_for() below


# THE FLAT PATTERN IS NOT THE ONLY PLACE TWO PANELS CAN MEET.
#
# relief_for() sizes a corner so the flaps do not OVERLAP WHEN UNFOLDED. That
# is a real constraint and it is the one a flat pattern shows you. It is not
# the only one. A foot does not stay in the flap's plane: it folds through
# ninety degrees at the wall and then lies horizontal, reaching back INBOARD
# to plan radius CARCASS_HALF_IN - CARCASS_FOOT.
#
# Everything inboard of the fold line behaves the opposite way round at a
# corner. At a CONVEX corner the unfolded flaps splay apart - which is why the
# flat only needs the mitre gap there - but the folded feet CONVERGE, by
# (fold1 - tip) * tan(theta/2) at the tip. On this part that is 3.53 mm
# against 1.60 mm of relief, so two feet drive 1.93 mm into each other and
# overlap by 9.00 mm2 at each of two corners. In the flat those same two
# panels are 10.27 mm apart with zero overlap, so nothing in the blank, the
# DXF or the drawing shows it. It appears for the first time on the brake,
# when the last foot bend will not close.
#
# The trim goes on the FOOT ONLY. Taking it out of the downstand as well would
# shorten the channel wall, which is both the side of the channel and the
# surface the skin bonds to; the foot only has to carry bond area.
def folded_corner_trim(theta_deg, reach):
    """How much a panel reaching `reach` inboard must lose at a convex corner."""
    th = math.radians(theta_deg)
    return reach * math.tan(th / 2.0) + CORNER_GAP / (2.0 * math.cos(th / 2.0))


FOOT_REACH = CARCASS_FOOT                                       # 8.0 outboard


def relief_for(theta_deg, depth, concave):
    """How far a flap must be cut back at a corner so the FLAT PATTERN works.

    1.60 mm is the vendor's minimum relief and it is the wrong number for a
    flap of any depth. Unfold two flaps from bend lines that meet at an angle
    and, at a CONCAVE corner, they sweep toward each other: they need
    d*tan(theta/2) of setback each or they occupy the same flat material.
    Ours are 16.5 mm deep - downstand plus foot - so at the 45 deg corners
    they need 6.83 mm, not 1.60, and the first flat pattern ever generated
    overlapped itself by 266 mm2.

    At a CONVEX corner the flaps sweep apart instead and the vendor minimum is
    genuinely all that is required.
    """
    if not concave:
        return CORNER_RELIEF
    # depth*tan(theta/2) is the value at which the two flaps TOUCH. Returned
    # bare it closes the relief to a 0.0000 mm cusp - two 90 deg wedges of
    # metal meeting at a mathematical point, and an interior cut ring touching
    # the exterior one. CORNER_GAP has been defined in this file the whole time
    # and used nowhere; this is what it is for.
    th = math.radians(theta_deg)
    return max(CORNER_RELIEF,
               depth * math.tan(th / 2.0)
               + CORNER_GAP / (2.0 * math.cos(th / 2.0)))

# ---- where the extra width goes ------------------------------------------
# ALL of it goes to the FAR side, so the show skin's outer face does not move
# and the wordmark stays framed exactly as it was. That is done by shifting the
# route centreline toward the far side by the amount the cover grew per side.
#
# It lands where it is wanted: far faces the BRACKET on both vertical legs and
# the PCIe EDGE on the horizontal one, so the growth covers the notch and the
# strap line rather than eating into the wordmark's air.
WIDEN = 2.0                    # (new half width 18.5) - (old 16.5)
# ...plus clearance for ONE washer. The card fastener at (171.28, 32.02) takes
# a mandatory M2 flat washer, OD 5.0, standing proud on the OUTSIDE face - the
# face the cover lands on. At WIDEN alone the cover's show edge passes 1.09 mm
# from that hole and the washer overlaps it by 1.41, so the skin cannot come
# down onto the plate. It needs 2.50 mm, so the shift grows by 0.78; 0.80 taken
# for a round number. The alternative was notching the show skin's bottom edge
# over one screw, on the one face that is supposed to be unbroken.
#
# 0.80 WAS MEASURED BARE AND THAT IS NOT THE PART THAT GETS BUILT. Both the
# skin and the washer are powder coated, so each grows COAT_ALLOWANCE and the
# gap loses twice that: 0.21 bare became 0.06 coated, which is a rub, not a
# clearance. Raised so the COATED gap is over half a millimetre, and the guard
# in hardware.check() now measures the coated geometry rather than the bare.
#
# 1.30 -> 1.60 when the skin moved 0.30 mm outboard, because CARCASS_RIB_IN had
# the same bare-metal bug: the skin going out by 0.30 takes the same 0.30 off
# this clearance, and it was measured at 0.410.
# AND IT HAS TO COVER THE PLAY THE SLOTS ALLOW. The tab slots are
# deliberately sized so the skin can sit up to SLOT_ACROSS off nominal - that
# is the whole point of the stack - and the washer clearance was 0.410 mm
# against 0.777 mm of that play. Sized to the play now, so the skin cannot
# reach the washer at either extreme of its own tolerance.
# 2.00 gave the show skin 0.810 mm coated to the card washer at (171.28,
# 32.02). The wall beside it is leg 0's SHOW wall and leg 0's foot is FAR,
# so that wall is three bends from a bonded foot: its lateral stack is
# 1.539 mm (bond 0.23 + tilt 0.17 + 3 x 0.381), not the 0.777 the guard was
# built on. Short by 0.729; so the route moves that much further toward the
# bracket. The connector has the room: from the photo its body sits hard
# against the notch's bracket end, centre about 148.3, and the far wall's
# bound after this shift is 145.59.
WASHER_CLEAR = 2.00 + 0.729 + 0.30      # and 0.30 of margin on top


def shifted(path, d=None):
    """The centreline moved toward the FAR side, so growth is one-sided."""
    d = (WIDEN + WASHER_CLEAR) if d is None else d
    # OFFSET, not per-vertex translate. Moving each vertex by the normal of ONE
    # adjacent leg SKEWS the polyline: at a corner the vertex has to go to the
    # INTERSECTION of the two offset lines. The first version did the former
    # and turned four 45.0000 deg corners into 44.6301 / 44.6301 / 46.2220 /
    # 46.2220, so nothing on the drawings was the angle it said it was.
    # offset() has done this correctly since the beginning.
    return offset(path, d, FAR)


# How far past the connector-notch void a foot has to start before it is
# allowed to exist. The notch is a hole in the backplate, so foot metal over
# it bonds to nothing - foot_bond_area() has always subtracted it - and the
# leg-0 foot was 56% dead by that measure, 238.5 of 423.3 mm2. The dead half
# was not merely useless: folded, it stands 0.40 to 2.40 mm above the plate's
# coated face directly across the connector's path, leaving a 15.70 mm coated
# window against an 18.20 mm connector body. That is a 2.50 mm interference at
# EVERY connector position, which no measurement of the card can rescue.
#
# connector_clearance() could not see it: it measures the two WALLS in plan
# and says the show wall clears if the connector centre is at or below 151.82.
# The foot is inboard of that wall and was never in the comparison, so the
# guard reported a solvable problem where there was an unsolvable one.
FOOT_NOTCH_CLEAR = 1.0
# THE WALLS STOP SHORT OF THE NOTCH TOO (2026-09-02). The 180-degree adapter
# fits the widened notch - the owner tested it on a print - but the cover's
# walls come down over that notch 12.0 mm either side of the route, 23.7 mm
# apart coated, and the adapter is 25.10 or 30.18 along the card. Over the
# notch band (y 0..26.5) the walls hang over a void and cover nothing; the
# skins still close the outside. So the walls start past the notch, and the
# adapter has the skins' inner faces to clear instead: 32.9 mm.
WALL_NOTCH_CLEAR = 1.0

# THE END CAP (2026-09-02). The first 3-D render showed what the plug end
# looks like with the walls cut back over the notch: an open tunnel with the
# adapter and cable in it. So the top face grows a fourth kind of flap at the
# route's start - folded DOWN across the channel, as wide as the space
# between the skins' inner faces - and the end reads as one closed face with
# the skins wrapping round it. No new part, no new adhesive.
#
# It is wider than the top face it hangs from (32.6 against 25.05), so its
# bend ends inside its own top edge; the two ears outside the bend are
# notched back RELIEF_DEPTH so the bend terminates in air, not metal.
# END_CAP_Y moves the whole cap outward (past the plate edge) if the adapter
# turns out to protrude past that edge - the one thing not yet seen.
END_CAP = True
END_CAP_Y = 0.0                 # outward offset from the plate edge, mm
END_CAP_CLEAR = 0.3             # to each skin's inner face


def _wall_start(a, b, i, sgn, path, d):
    """How far along a leg's fold edge the WALL has to start to miss the notch.

    Walks the edge and asks whether the folded wall - the band from
    CARCASS_HALF_IN to CARCASS_HALF_DS under this edge - lies over the notch
    void, buffered by WALL_NOTCH_CLEAR. Only a contiguous stretch from the
    leg's START is honoured; a notch in the middle of a leg would have to
    split the wall, and raises instead.
    """
    nb = notch_box().buffer(WALL_NOTCH_CLEAR)
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if L <= 0:
        return 0.0
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    (px, py), (qx, qy) = path[i], path[i + 1]
    PL = math.hypot(qx - px, qy - py) or 1.0
    rx, ry = (qx - px) / PL, (qy - py) / PL
    nx, ny = ry * sgn, -rx * sgn
    # the wall's plan band is inboard of the fold edge: from fold1 back to
    # HALF_IN and out to HALF_DS, i.e. offsets -(fold1-HALF_IN)..+(HALF_DS-fold1)
    offs = (CARCASS_HALF_IN - d["fold1"], CARCASS_HALF_DS - d["fold1"])
    step = 0.25
    t, t_end, seen_clear = 0.0, 0.0, False
    while t <= L + 1e-9:
        seg = LineString([(a[0] + ux * t + nx * offs[0], a[1] + uy * t + ny * offs[0]),
                          (a[0] + ux * t + nx * offs[1], a[1] + uy * t + ny * offs[1])])
        if seg.intersects(nb):
            if seen_clear:
                raise ValueError("leg %d: the connector notch lies in the "
                                 "MIDDLE of the wall - it would have to be "
                                 "split, not shortened" % i)
            t_end = min(L, t + step)
        else:
            seen_clear = True
        t += step
    return t_end


def _fold_foot_pt(x, y, i, sgn, path, d):
    """One blank point of a foot flap, mapped to where it folds to in plan.

    The same map folded_foot() applies, exposed for a single point so the
    notch trim can be measured in the folded position and applied in the
    blank.
    """
    (ax, ay), (bx, by) = path[i], path[i + 1]
    L = math.hypot(bx - ax, by - ay) or 1.0
    ux, uy = (bx - ax) / L, (by - ay) / L
    nx, ny = uy * sgn, -ux * sgn
    vx, vy = x - ax, y - ay
    t = vx * ux + vy * uy
    dd = vx * nx + vy * ny
    _oml, _flat, _edge = foot_dev(sgn)
    r = CARCASS_HALF_DS + ((dd - d["fold2"]) * _oml / (_edge - d["fold2"]))
    return (ax + ux * t + nx * r, ay + uy * t + ny * r)


def _end_cap_flap(path, d):
    """The end cap as a flap in the blank: fold edge first, then the outline.

    Fold edge = the top face's end edge at path[0], from the FAR fold line to
    the SHOW one (2 x fold1 long). The flap unfolds OUTWARD - opposite to the
    route's first leg - by down_flat_free (one bend, free edge below), and
    widens to +-(CARCASS_RIB_IN - END_CAP_CLEAR) below RELIEF_DEPTH, so the
    bend's two ends terminate in the relief and not in the ears.
    """
    (ax, ay), (bx, by) = path[0], path[1]
    L = math.hypot(bx - ax, by - ay) or 1.0
    ux, uy = (bx - ax) / L, (by - ay) / L
    ox, oy = -ux, -uy                                  # outward
    ex, ey = uy, -ux                                   # along the fold, FAR->SHOW
    f1 = d["fold1"]
    w = CARCASS_RIB_IN - END_CAP_CLEAR
    df = d["down_flat_free"]
    rd = RELIEF_DEPTH
    ax0, ay0 = ax + ox * END_CAP_Y, ay + oy * END_CAP_Y

    def P(s, t):
        return (ax0 + ex * s + ox * t, ay0 + ey * s + oy * t)
    ring = [P(-f1, 0.0), P(f1, 0.0), P(f1, rd), P(w, rd), P(w, df),
            P(-w, df), P(-w, rd), P(-f1, rd)]
    g = Polygon(ring)
    if not g.is_valid:
        raise ValueError("end cap outline is not a simple polygon")
    return dict(kind="endcap", sgn=0, leg=0, poly=g)


def _foot_screw_spots(a, ux, uy, nx, ny, t0, t1, e0, e1, i, sgn, path, d):
    """Where this foot piece's screws go: [(blank xy, plan xy), ...].

    Across the foot the hole sits BEND_KEEPOUT + half its own diameter past
    the bend, i.e. plan radius CARCASS_HALF_DS + 5.99 + 1.45 = 21.44; the
    blank depth is that radius put back through the foot's own map. Along
    the foot: two screws FOOT_SCREW_END in from each end when they can sit
    FOOT_SCREW_MIN_PITCH apart, one in the middle when they cannot, none on
    a piece too short for even that - and each position is slid along the
    piece until it is SCREW_BORE_CLEAR from every card bore, because the
    tapped hole in the plate has to obey hardware.py's rule too.
    """
    from hole_pattern import HOLES as _H
    _oml, _flat, _edge = foot_dev(sgn)
    # IN THE FLAT: the hole's edge BEND_KEEPOUT past the fold line, measured
    # from the fold1 line `a` sits on (fold2 - fold1 = down_flat to the foot's
    # own fold, then the keep-out, then the hole's radius); and it must still
    # leave MIN_FEATURE of web to the tip.
    dd = (d["fold2"] - d["fold1"]) + BEND_KEEPOUT + 0.05 + FOOT_SCREW_CLEAR / 2.0
    if dd + FOOT_SCREW_CLEAR / 2.0 + MFG.MIN_FEATURE > (_edge - d["fold1"]) + 1e-9:
        raise ValueError("far foot %.2f is too short for an M2.5 clear of the "
                         "bend keep-out" % _oml)
    lo, hi = t0 + max(e0, 0.0) + FOOT_SCREW_END, t1 - max(e1, 0.0) - FOOT_SCREW_END
    if hi < lo:
        return []
    wants = [lo, hi] if hi - lo >= FOOT_SCREW_MIN_PITCH else [(lo + hi) / 2.0]

    def plan(t):
        return _fold_foot_pt(a[0] + ux * t + nx * dd, a[1] + uy * t + ny * dd,
                             i, sgn, path, d)

    def ok(t):
        px, py = plan(t)
        return all(math.hypot(px - hx, py - hy) >= SCREW_BORE_CLEAR
                   for hx, hy, _t, _s in _H)
    out = []
    for w in wants:
        best = None
        for k in range(0, 200):
            for t in (w + 0.25 * k, w - 0.25 * k):
                if lo - 1e-9 <= t <= hi + 1e-9 and ok(t):
                    best = t
                    break
            if best is not None:
                break
        if best is None:
            continue
        if out and abs(best - out[-1][2]) < FOOT_SCREW_MIN_PITCH:
            continue
        out.append(((a[0] + ux * best + nx * dd, a[1] + uy * best + ny * dd),
                    plan(best), best))
    return [(b, p) for b, p, _t in out]


def _foot_exclusions(a, b, i, sgn, path, d):
    """Intervals along a foot's fold edge where NO foot may exist, in mm.

    Three kinds of obstruction, all tested in the FOLDED position of the foot
    (plan radius CARCASS_HALF_DS..+CARCASS_FOOT) and applied in the blank,
    which maps straight through because the along-leg coordinate survives
    the fold:

      the connector notch  a hole in the plate; foot over it bonds to nothing
                           and, inward, stood across the connector's path
      the card washers     stand proud of the face the foot lies on
      the tab stations     a skin's tab drops through the plate right where
                           an outward foot would lie - seven of nine did.
                           The foot stops TAB_FOOT_GAP short of the slot.

    Returns merged, sorted (t0, t1) pairs. The caller takes the complement
    as foot segments and drops any shorter than FOOT_SEG_MIN.
    """
    from config import HARDWARE as _HW
    from hole_pattern import HOLES as _H
    obst = [notch_box().buffer(FOOT_NOTCH_CLEAR)]
    wr = _HW.WASHER_OD / 2.0 + MFG.COAT_ALLOWANCE + FOOT_NOTCH_CLEAR
    obst += [Point(x, y).buffer(wr) for x, y, _t, _s in _H]
    (px, py), (qx, qy) = path[i], path[i + 1]
    PL = math.hypot(qx - px, qy - py) or 1.0
    rx, ry = (qx - px) / PL, (qy - py) / PL
    for t in skin_tabs(sgn, path):
        if t["leg"] != i:
            continue
        cx, cy = t["at"]
        hl = t["slot_l"] / 2.0 + TAB_FOOT_GAP
        hw = CARCASS_FOOT + 4.0
        nx_, ny_ = -ry, rx
        obst.append(Polygon([
            (cx - rx * hl - nx_ * hw, cy - ry * hl - ny_ * hw),
            (cx + rx * hl - nx_ * hw, cy + ry * hl - ny_ * hw),
            (cx + rx * hl + nx_ * hw, cy + ry * hl + ny_ * hw),
            (cx - rx * hl + nx_ * hw, cy - ry * hl + ny_ * hw)]))
    ob = unary_union(obst)
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if L <= 0:
        return []
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = ry * sgn, -rx * sgn
    lo, hi = d["down_flat"], d["down_flat"] + foot_dev(sgn)[1]
    step = 0.25
    bad, t = [], 0.0
    while t <= L + 1e-9:
        x0, y0 = a[0] + ux * t, a[1] + uy * t
        seg = LineString([
            _fold_foot_pt(x0 + nx * lo, y0 + ny * lo, i, sgn, path, d),
            _fold_foot_pt(x0 + nx * hi, y0 + ny * hi, i, sgn, path, d)])
        bad.append(seg.intersects(ob))
        t += step
    out, k = [], 0
    while k < len(bad):
        if bad[k]:
            j = k
            while j + 1 < len(bad) and bad[j + 1]:
                j += 1
            t0, t1 = max(0.0, k * step - step), min(L, j * step + step)
            out.append([t0, t1])
            k = j + 1
        else:
            k += 1
    merged = []
    for t0, t1 in out:
        if merged and t0 <= merged[-1][1] + 1e-9:
            merged[-1][1] = max(merged[-1][1], t1)
        else:
            merged.append([t0, t1])
    return [(t0, t1) for t0, t1 in merged]


def _foot_segments(exclusions, L):
    """Complement of the exclusions on [0, L], pieces under FOOT_SEG_MIN dropped."""
    segs, t = [], 0.0
    for t0, t1 in exclusions:
        if t0 - t >= FOOT_SEG_MIN:
            segs.append((t, t0))
        t = max(t, t1)
    if L - t >= FOOT_SEG_MIN:
        segs.append((t, L))
    return segs


def _stepped_wall(a, b, ux, uy, nx, ny, d0, d1, df, segs, L):
    """The wall's outline: fold line a->b, free edge stepped at every foot end.

    Footed stretches are d1 deep (down_flat: a bend at both ends), free
    stretches df (down_flat_free: half a deduction), and where a foot's bend
    STOPS the free edge is cut back RELIEF_DEPTH past that bend for RELIEF_W
    so the bend can terminate without tearing. No relief where a foot runs to
    the leg's end - the corner relief is there already.
    """
    dr = d1 - RELIEF_DEPTH
    pieces = []                                  # (t_start, t_end, depth)
    t = 0.0
    for t0, t1 in segs:
        if t0 > 1e-9:
            if t0 - RELIEF_W > t + 1e-9:
                pieces.append((t, t0 - RELIEF_W, df))
            pieces.append((max(t, t0 - RELIEF_W), t0, dr))
        pieces.append((t0, t1, d1))
        t = t1
        if t1 < L - 1e-9:
            pieces.append((t1, min(L, t1 + RELIEF_W), dr))
            t = min(L, t1 + RELIEF_W)
    if t < L - 1e-9:
        pieces.append((t, L, df))
    ring = [(a[0] + nx * d0, a[1] + ny * d0), (b[0] + nx * d0, b[1] + ny * d0)]
    for t0, t1, dep in reversed(pieces):
        ring.append((a[0] + ux * t1 + nx * dep, a[1] + uy * t1 + ny * dep))
        ring.append((a[0] + ux * t0 + nx * dep, a[1] + uy * t0 + ny * dep))
    g = Polygon(ring).buffer(0)
    # buffer(0) may roll the ring; the fold line must stay first
    c = list(g.exterior.coords)[:-1]
    fa = (a[0] + nx * d0, a[1] + ny * d0)
    k = min(range(len(c)), key=lambda q: math.hypot(c[q][0] - fa[0], c[q][1] - fa[1]))
    c = c[k:] + c[:k]
    nb = (b[0] + nx * d0, b[1] + ny * d0)
    if math.hypot(c[1][0] - nb[0], c[1][1] - nb[1]) > 1e-6:
        c = [c[0]] + c[1:][::-1]
    return Polygon(c)


def candidate_foot(i, sgn, path):
    """The foot leg `i` would get on side `sgn`, trimmed exactly as drawn.

    Standalone on purpose. It ASSUMES this leg is footed - which is the
    question being asked - and every trim it applies depends only on this
    leg's own two corners, so it never has to ask foot_side_for() about any
    leg and there is no recursion.
    """
    d = carcass_dev()
    tn, ang = turns(path), deflections(path)
    pts = offset(path, d["fold1"], sgn)
    n = len(pts) - 1
    (ax, ay), (bx, by) = pts[i], pts[i + 1]
    L = math.hypot(bx - ax, by - ay) or 1.0
    ux, uy = (bx - ax) / L, (by - ay) / L
    nx, ny = uy * sgn, -ux * sgn
    depth = d["down_flat"] + d["foot_flat"]
    reach = (CARCASS_HALF_DS + CARCASS_FOOT) - d["fold1"]
    r0 = relief_for(ang[i - 1], depth, tn[i - 1] * sgn < 0) if i > 0 else 0.0
    r1 = relief_for(ang[i], depth, tn[i] * sgn < 0) if i < n - 1 else 0.0
    e0 = (max(0.0, folded_corner_trim(ang[i - 1], reach) - r0)
          if i > 0 and tn[i - 1] * sgn < 0 else 0.0)
    e1 = (max(0.0, folded_corner_trim(ang[i], reach) - r1)
          if i < n - 1 and tn[i] * sgn < 0 else 0.0)
    a = (ax + ux * r0, ay + uy * r0)
    b = (bx - ux * r1, by - uy * r1)
    d0, d1 = d["down_flat"], d["down_flat"] + foot_dev(sgn)[1]
    return dict(kind="foot", sgn=sgn, leg=i, poly=Polygon([
        (a[0] + nx * d0, a[1] + ny * d0),
        (b[0] + nx * d0, b[1] + ny * d0),
        (b[0] - ux * e1 + nx * d1, b[1] - uy * e1 + ny * d1),
        (a[0] + ux * e0 + nx * d1, a[1] + uy * e0 + ny * d1)]))


def foot_usable(leg, sgn, path=None):
    """Bond area the foot on this side would really get, on plate metal.

    THIS USED TO BE A BAND: full leg length, full foot width, clipped to the
    plate and the notch. As a way of comparing two sides that was defensible
    until the corner trims grew, and then it was not - it reported 161.5 mm2
    for a foot that actually lands 84.9, about double, and on that basis kept
    leg 0 on the side with LESS metal by a 75.3% margin against a 75% rule.
    It measures the foot that would be cut, folded into place.
    """
    path = route45() if path is None else path
    import backplate_v3 as B
    plate = Polygon(B.outline())
    f = candidate_foot(leg, sgn, path)
    return folded_foot(f, path).intersection(plate).difference(notch_box()).area


# ON THE OUTSIDE OF EVERY TURN. On the inside the fold line is shorter by
# 2 x 12.525 x tan(22.5) = 10.4 mm and the concave-corner relief takes 6.87
# off each end, so a foot there is 18 mm at best and leg 4's is 2 mm; on the
# outside the same foot is 45. The tabs therefore go on the OTHER side of
# each leg - see tab_stations() - because an outward foot and a tab cannot
# share a side.
FOOT_SIDES = {0: FAR, 1: FAR, 2: SHOW, 3: SHOW, 4: SHOW}


def foot_side_for(leg):
    """Which side carries the foot on this leg. ONE definition of the stagger.

    It was implemented twice - once in carcass_bonds() and once in the blank -
    and a third place, the DXF writer, did not know about it at all and drew a
    downstand-to-foot fold line on legs that have no foot, landing it on the
    blank's free edge. A bend line on a cut path is the laser following a fold.
    """
    # ALTERNATE, but not into thin air. Leg 0 runs off the connector notch, so
    # its whole show-side foot band - 367 mm2 - sat over the void and bonded to
    # nothing. Where the alternating choice has materially less metal under it
    # than the other side, take the other side; the stagger survives everywhere
    # it can.
    # AN EXPLICIT TABLE, decided with the feet turned OUT (2026-09-01). An
    # outward foot lies exactly where a tab drops through the plate, so a foot
    # and a tab cannot share a side of a leg. Alternating from SHOW on leg 0
    # put feet under seven of the nine tabs and, once the tab stations were
    # cut out of them, no leg kept an 8 mm piece. Alternating from FAR
    # collides only on leg 2, which has tabs on BOTH sides - so leg 2 carries
    # no foot at all, and the other four legs carry one each. It also puts a
    # bonded foot on leg 0's SHOW wall, the one beside the card washer.
    return FOOT_SIDES.get(leg, None)


def carcass_dev():
    """THE ONE development of the carcass section. Everything reads this.

    The blank was drawn at the raw inside-mould-line sum with NO bend
    compensation - 57.00 mm against a correct 61.20 at the old foot size - and
    carcass_flat() reported 45.20, subtracting an outside-mould-line deduction
    from inside-mould-line legs. Three places computed the section three ways.
    Now there is one.

    Measured along the OUTER surface, foot free edge to foot free edge:

        foot        CARCASS_FOOT + T
        downstand   CLEAR_D + T
        top face    2*CARCASS_HALF_IN + 2*T
        downstand   CLEAR_D + T
        foot        CARCASS_FOOT + T

    flat = sum(those) - 4 * BEND_DEDUCT, and each fold sits half a deduction
    inboard of its own sharp corner.
    """
    # OUTWARD: the formed foot from the wall's outer face IS CARCASS_FOOT.
    # (Inward it was CARCASS_FOOT + T, the reach past the inner face plus the
    # wall's own thickness.)
    foot_oml = CARCASS_FOOT
    down_oml = CLEAR_D + T
    top_oml = 2 * CARCASS_HALF_IN + 2 * T
    oml = [foot_oml, down_oml, top_oml, down_oml, foot_oml]
    flat = sum(oml) - 4 * BEND_DEDUCT
    half = top_oml / 2.0                       # 14.0, the downstand's outer face
    fold1 = half - BEND_DEDUCT / 2.0           # top face -> downstand
    down_flat = down_oml - BEND_DEDUCT
    # A DOWNSTAND WITH NO FOOT HAS ONLY ONE BEND. down_flat subtracts a whole
    # deduction because it assumes a fold at each end. Where the foot is
    # staggered away the downstand ends at a free edge, so it takes half a
    # deduction, not a whole one - and folded back it came out 11.025 mm
    # against a design 12.500, short by exactly BD/2 on every footless side.
    down_flat_free = down_oml - BEND_DEDUCT / 2.0
    fold2 = fold1 + down_flat                  # downstand -> foot
    foot_flat = foot_oml - BEND_DEDUCT / 2.0
    edge = fold2 + foot_flat
    # THE SECTION THAT ACTUALLY EXISTS. `flat` is the both-feet sum, and no
    # station on this part has two feet - they are staggered, one per station,
    # so the real developed width is a foot on one side and a free downstand
    # on the other. Quoting 61.20 on the drawing described a cross-section
    # that occurs nowhere on the blank; the true figure is 54.15.
    flat_staggered = (fold1 + down_flat + foot_flat) + (fold1 + down_flat_free)
    return dict(oml=oml, flat=flat, flat_staggered=flat_staggered,
                half=half, fold1=fold1, fold2=fold2,
                down_flat=down_flat, down_flat_free=down_flat_free,
                foot_flat=foot_flat, edge=edge)


def foot_screw_offsets():
    """Where the foot's screw goes, in BOTH coordinate systems.

    The flat is what constrains it: the hole must clear BEND_KEEPOUT from the
    fold it sits next to, and MIN_FEATURE from the free edge. On an 8 mm foot
    that window was empty, which is why the foot went to 10.
    """
    d = carcass_dev()
    lo = d["fold2"] + BEND_KEEPOUT + CLEAR_HOLE / 2.0
    hi = d["edge"] - MFG.MIN_FEATURE - CLEAR_HOLE / 2.0
    if lo > hi:
        raise RuntimeError(
            "no legal screw position on the foot: window %.2f..%.2f is empty. "
            "CARCASS_FOOT %.1f is too short for a %.2f mm bend keep-out."
            % (lo, hi, CARCASS_FOOT, BEND_KEEPOUT))
    flat = (lo + hi) / 2.0
    # map back to the folded part: the foot runs inward from CARCASS_HALF_IN
    inward = (flat - d["fold2"]) - (d["foot_flat"] - CARCASS_FOOT)
    return dict(flat=flat, folded=CARCASS_HALF_IN - inward,
                window=(lo, hi), inward=inward)


def carcass(path=None):
    """Top face plus a relieved downstand each side, FROM THE BLANK.

    THIS USED TO BE A SECOND DERIVATION and it outlived three of the artefacts
    that consumed it. It computed its own relief at one depth for every corner
    - CLEAR_D - T + CARCASS_FOOT = 16.5 - where the blank uses the real
    per-flap depths, so its walls were 2.27 mm short at every footless concave
    corner and 0.65 mm long at every footed one. The exported solid was built
    on it, and so was the 2D section, and both were wrong in the same way for
    the same reason.

    There is one derivation of this part and it is carcass_blank(). This
    function is now a view of it: the wall segments ARE the flaps' attachment
    edges, slid from the developed fold line to where the folded wall's inner
    face actually stands.
    """
    path = route45() if path is None else path
    top, flaps = carcass_blank(path)
    d = carcass_dev()
    shift = d["fold1"] - CARCASS_HALF_IN     # developed -> folded, 0.525
    walls = {SHOW: [], FAR: []}
    feet = {SHOW: [], FAR: []}
    for f in flaps:
        i, sgn = f["leg"], f["sgn"]
        (ax, ay), (bx, by) = path[i], path[i + 1]
        L = math.hypot(bx - ax, by - ay) or 1.0
        ux, uy = (bx - ax) / L, (by - ay) / L
        nx, ny = uy * sgn, -ux * sgn
        c = list(f["poly"].exterior.coords)
        a = (c[0][0] - nx * shift, c[0][1] - ny * shift)
        b = (c[1][0] - nx * shift, c[1][1] - ny * shift)
        if f["kind"] == "downstand":
            walls[sgn].append((a, b))
        else:
            feet[sgn].append((i, folded_foot(f, path)))
    return dict(top=top, walls=walls, feet=feet, flaps=flaps,
                reliefs=sum(len(v) - 1 for v in walls.values()) * 2,
                gap=2 * CORNER_RELIEF, width=CARCASS_W)


def carcass_ribbon(sgn, path=None, flush=False):
    """The skin, sitting outboard of the downstand.

    DEVELOPED ON THE MID SURFACE, not the outer face. Measuring apex legs on
    CARCASS_RIB_OUT and subtracting one deduction per fold is only right where
    that face is the OUTSIDE of the bend. This route turns both ways, so at two
    of each skin's four folds it is the INSIDE: those apex legs are already
    short by the setback, and taking a deduction off as well double-counts.
    The blanks came out 3.3 mm short.

    On the mid surface the arithmetic is datum-neutral and needs no convexity
    test at all:

        setback_i = (R + T/2) * tan(theta_i / 2)
        allowance_i = theta_i * (R + K*T)
        flat = sum(mid legs) - 2*sum(setback) + sum(allowance)

    The fold POSITIONS come out of the same walk, so the blank width and the
    marks on it can never be computed on different rules again.
    """
    path = route45() if path is None else path
    pts = offset(path, CARCASS_RIB_OUT, sgn)          # for drawing only
    mid = offset(path, CARCASS_RIB_IN + T / 2.0, sgn)  # for development
    legs = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            for i in range(len(pts) - 1)]
    mlegs = [math.hypot(mid[i + 1][0] - mid[i][0], mid[i + 1][1] - mid[i][1])
             for i in range(len(mid) - 1)]
    ang = deflections(path)
    Rm = BEND_RADIUS + T / 2.0
    Rn = BEND_RADIUS + K_FACTOR * T
    SB = [Rm * math.tan(math.radians(a) / 2.0) for a in ang]
    BA = [math.radians(a) * Rn for a in ang]
    folds, run = [], 0.0
    for i, L in enumerate(mlegs):
        lo = SB[i - 1] if i > 0 else 0.0
        hi = SB[i] if i < len(SB) else 0.0
        run += L - lo - hi
        if i < len(SB):
            folds.append(run + BA[i] / 2.0)       # mark the arc's centre
            run += BA[i]
    flat = run
    return dict(pts=pts, legs=legs, mid_legs=mlegs, flat=flat, angles=ang,
                folds=folds, height=skin_top(flush) - Z0, sgn=sgn, flush=flush,
                tol=0.381 * len(ang))


def carcass_fasteners(path=None, pitch=60.0):
    """The far-side foot screws: one entry per screw, plan position.

    Read off the blank (built without the roof vents, which would otherwise
    pull in the plate's vent field and, through hardware.holes(), this very
    function). The show side's feet carry no screws - they are on tape.
    """
    path = route45() if path is None else path
    _top, flaps = carcass_blank(path, roof_vents=False)
    out = []
    for f in flaps:
        if f["kind"] != "foot":
            continue
        for b, p in f.get("screws", []):
            out.append(dict(at=p, blank=b, leg=f["leg"], sgn=f["sgn"]))
    return out


def folded_foot(f, path):
    """One foot flap rotated into the horizontal, in plate coordinates."""
    d = carcass_dev()
    i, sgn = f["leg"], f["sgn"]
    _oml, _flat, _edge = foot_dev(sgn)
    (ax, ay), (bx, by) = path[i], path[i + 1]
    L = math.hypot(bx - ax, by - ay) or 1.0
    ux, uy = (bx - ax) / L, (by - ay) / L
    nx, ny = uy * sgn, -ux * sgn
    pts = []
    for x, y in f["poly"].exterior.coords[:-1]:
        vx, vy = x - ax, y - ay
        t = vx * ux + vy * uy
        dd = vx * nx + vy * ny
        r = CARCASS_HALF_DS + (dd - d["fold2"]) * _oml / (_edge - d["fold2"])
        pts.append((ax + ux * t + nx * r, ay + uy * t + ny * r))
    return Polygon(pts).buffer(0)


def flat_foot_band(path, sgn):
    """The part of a foot that is FLAT and can actually touch the plate.

    A foot does not become horizontal at the fold line. The wall-to-foot bend
    has an outside radius of BEND_RADIUS + T = 2.97 mm, so the foot's underside
    is still curving until plan radius CARCASS_HALF_DS - 2.97 = 11.03, and
    everything outboard of that is the outside of its own bend, standing clear
    of the plate. Counting it as bond area overstated every foot by 12%.
    """
    # OUTWARD: the bend's outside radius sits against the wall, the flat
    # runs from its tangent out to the tip.
    inner = CARCASS_HALF_DS + (BEND_RADIUS + T)
    outer = CARCASS_HALF_DS + foot_len(sgn)
    a = offset(path, outer, sgn)
    b = offset(path, inner, sgn)
    return Polygon(a + b[::-1]).buffer(0)


def foot_bond_area(f, path=None):
    """How much of a DRAWN foot actually lands on plate metal.

    foot_usable() answers a different question and has to: it is what
    foot_side_for() consults, so it cannot depend on the blank without the
    blank depending on it. It compares two candidate sides using the full
    untrimmed band, which is fair for a comparison and wrong as an area - it
    reported more bond than the foot even has, once the corner trims came in.
    This one measures the foot that is really cut.
    """
    import backplate_v3 as B
    path = route45() if path is None else path
    plate = Polygon(B.outline())
    return (folded_foot(f, path).intersection(flat_foot_band(path, f["sgn"]))
            .intersection(plate).difference(notch_box()).area)


def carcass_bonds(path=None):
    """The foot's bond footprint, staggered one side at a time.

    Staggered so the cable can be rolled in: at any station there is one foot,
    not two, which leaves 16.0 mm of a 24.0 mm channel rather than 8.0.
    """
    # ONE SOURCE FOR THE STAGGER, and one for the area. This carried its own
    # `i % 2` rule, which stopped agreeing with the blank the moment
    # foot_side_for() started avoiding the connector-notch void: it reported a
    # far-side foot on leg 3 where the blank and the DXF both cut a SHOW one.
    # It also reported width x raw leg length, which is neither the foot that
    # is drawn - the corner trims take metal off both ends - nor the part of
    # it that lands on plate metal.
    path = route45() if path is None else path
    _, flaps = carcass_blank(path)
    out = []
    for f in sorted((q for q in flaps if q["kind"] == "foot"),
                    key=lambda q: q["leg"]):
        i, sgn = f["leg"], f["sgn"]
        out.append(dict(leg=i, sgn=sgn,
                        side="show" if sgn == SHOW else "far",
                        area=f["poly"].area,
                        usable=foot_bond_area(f, path),
                        width=CARCASS_FOOT,
                        tape="thin transfer adhesive %.2f mm - NOT the 2.30 VHB"
                             % FOOT_BOND))
    return out


def _unused_carcass_fasteners(path=None, pitch=60.0):
    """The old screwed version, kept only so the reasoning is legible."""
    path = route45() if path is None else path
    import backplate_v3 as B
    from hole_pattern import HOLES
    nx0 = B.NOTCH_CX - B.NOTCH_W / 2.0 - B.NOTCH_EXTRA_BRACKET
    nx1 = B.NOTCH_CX + B.NOTCH_W / 2.0
    notch = box(nx0, -2.0, nx1, B.NOTCH_D + 2.0)
    plate = Polygon(B.outline())
    out = []
    # STAGGERED: alternate which side carries the foot, so the cable can be
    # rolled in rather than threaded. And place the screw at the bend keep-out
    # rather than on the foot's mid-line, which an 8 mm foot could never do.
    inset = CARCASS_FOOT - (BEND_KEEPOUT + CLEAR_HOLE / 2.0)
    inset = max(2.0, min(inset, CARCASS_FOOT - 2.0))
    k = 0
    for sgn in (SHOW, FAR):
        pts = offset(path, CARCASS_HALF_IN - inset, sgn)
        for i in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            L = math.hypot(bx - ax, by - ay)
            n = max(1, int(L // pitch))
            for k in range(n):
                t = (k + 0.5) / n
                px, py = ax + (bx - ax) * t, ay + (by - ay) * t
                p = Point(px, py)
                if notch.contains(p) or not plate.contains(p):
                    continue
                if min(math.hypot(px - hx, py - hy)
                       for hx, hy, _t, _s in HOLES) < 8.0:
                    continue
                out.append(dict(at=(px, py), z=Z0,
                                side="show" if sgn == SHOW else "far",
                                joins="carcass foot -> backplate",
                                drive="up from the PCB side", size=SCREW,
                                length=SCREW_LEN, head="under the backplate"))
    return out


def carcass_mesh(path=None, hardware=True):
    """Viewer geometry for the carcass variant."""
    path = route45() if path is None else path
    cc = carcass(path)
    tops = [cc["top"]]
    body = []
    for sgn in (SHOW, FAR):
        for (ax, ay), (bx, by) in cc["walls"][sgn]:          # relieved downstand
            body.append(((ax, ay, Z0), (bx, by, Z0),
                         (bx, by, ZT), (ax, ay, ZT)))
        pts = carcass_ribbon(sgn, path)["pts"]               # continuous skin
        for i in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            body.append(((ax, ay, Z0), (bx, by, Z0),
                         (bx, by, ZR), (ax, ay, ZR)))
    if hardware:
        for f in carcass_fasteners(path):
            x, y = f["at"]
            body += _box(x, y, f["z"] - SCREW_LEN, 1.0, 0.0, 2.0, 2.0, SCREW_LEN)
    return tops, body


def assembled_mesh(path=None, half_out=None, flush=False):
    """What it actually looks like once it is together. No layering drawn.

    The hardware view draws the downstand, the bond line and the skin as three
    separate surfaces, because that is what they are and the point of that view
    is to show how it holds together. It reads as air between walls, which is
    misleading: the downstand and the skin are in contact through 0.50 mm of
    tape, and none of it is visible on the finished part.

    This one draws only what light reaches: the two outer skins, the top plate
    at its recessed level, and the flush notch cap. One object.
    """
    path = route45() if path is None else path
    half_out = CARCASS_RIB_OUT if half_out is None else half_out
    half_in = half_out - T
    tops = [Polygon(offset(path, half_in, SHOW)
                    + offset(path, half_in, FAR)[::-1]).buffer(0)]
    nc = notch_cap(path, half_out)
    tops.append(nc["cap"])
    body = []
    top_z = skin_top(flush)
    for sgn in (SHOW, FAR):
        pts = offset(path, half_out, sgn)
        for i in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            body.append(((ax, ay, Z0), (bx, by, Z0),
                         (bx, by, top_z), (ax, ay, top_z)))
    # close both ends of the run so it does not read as an open tube
    for end in (0, -1):
        a = offset(path, half_out, SHOW)[end]
        b = offset(path, half_out, FAR)[end]
        body.append(((a[0], a[1], Z0), (b[0], b[1], Z0),
                     (b[0], b[1], ZP), (a[0], a[1], ZP)))
    return tops, body


# ---- the two routes the carcass is actually built on ----------------------
def route90():
    """The 90 route, shifted so all the added width lands on the far side."""
    return shifted(PATH)


def route45(cut=None):
    """The chamfered route, shifted the same way."""
    return chamfered(shifted(PATH), cut)



def relief_notches(path, flaps, d):
    """The relief cuts, as polygons. ONE derivation, two consumers.

    carcass_blank() subtracts these from the top face; declared_gaps()
    needs to know where they are, because two of them meeting at a corner
    leave a gap in AIR that is narrower than min feature and is the same
    flanges-meet-at-a-corner case as a mitre. Recomputing them there would
    have been a second derivation of the thing this project keeps getting
    wrong by having two of.
    """
    notches = []
    # the end cap's fold runs ACROSS the top face's end; it is not a wall
    # ending at the corner, and counting it there cut a relief into the top
    # face at both corners for a bend that does not exist.
    fu = unary_union([f["poly"] for f in flaps if f["kind"] != "endcap"])
    for sgn in (SHOW, FAR):
        pts = offset(path, d["fold1"], sgn)
        for i in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            L = math.hypot(bx - ax, by - ay) or 1.0
            ux, uy = (bx - ax) / L, (by - ay) / L
            nx, ny = -uy * sgn, ux * sgn            # inboard, into the top face
            fold = LineString([(ax, ay), (bx, by)])
            bare = fold.difference(fu.buffer(1e-6))
            for seg in ([bare] if bare.geom_type == "LineString"
                        else list(getattr(bare, "geoms", []))):
                if seg.is_empty or seg.length < 1e-6:
                    continue
                (sx, sy), (ex, ey) = seg.coords[0], seg.coords[-1]
                # RELIEF GOES AT THE FOLD'S ENDS, NOT ACROSS THE WHOLE GAP.
                # Notching the entire bare span cut twelve 7.2 mm slots
                # through the cover's visible top face - 244 mm2 of holes
                # looking straight down into the channel, on a face that is
                # in plain view from standing. A relief only has to let the
                # bend TERMINATE: a notch of RELIEF_W at each end where the
                # fold actually dies. The metal in between carries no bend,
                # so it stays, and it stays in the top plane flush with the
                # inside of the wall - it fouls nothing.
                cuts = []
                for t, sg in ((0.0, +1.0), (seg.length, -1.0)):
                    px, py = sx + ux * t, sy + uy * t
                    # only where a flap really ends here. At the outer end of
                    # the run the fold has already stopped at the blank edge
                    # and there is nothing to tear.
                    if fu.distance(Point(px, py)) > 1e-3:
                        continue
                    cuts.append((t, t + sg * min(RELIEF_W, seg.length)))
                if not cuts:
                    continue
                spans = sorted((min(c), max(c)) for c in cuts)
                if seg.length <= 2 * RELIEF_W + MFG.MIN_FEATURE:
                    # too short to leave an ear that is itself cuttable
                    spans = [(0.0, seg.length)]
                else:                                    # merge if they touch
                    merged = [list(spans[0])]
                    for t0, t1 in spans[1:]:
                        if t0 <= merged[-1][1] + 1e-9:
                            merged[-1][1] = max(merged[-1][1], t1)
                        else:
                            merged.append([t0, t1])
                    spans = [tuple(m) for m in merged]
                for t0, t1 in spans:
                    ax2, ay2 = sx + ux * t0, sy + uy * t0
                    bx2, by2 = sx + ux * t1, sy + uy * t1
                    # RUN THE NOTCH OUTWARD PAST THE FOLD LINE TOO. At a
                    # chamfer corner the top face's boundary is the MITRE,
                    # which lies inboard of the leg's own fold line, so a
                    # notch drawn only from the fold line INWARDS could sit
                    # entirely inside the face and come out as an enclosed
                    # hole instead of an edge relief. The top face does not
                    # exist outboard of its boundary, so the overhang cuts
                    # nothing - it just guarantees the notch breaks the edge
                    # it is there to break.
                    notches.append(Polygon([
                        (ax2 - nx * RELIEF_DEPTH, ay2 - ny * RELIEF_DEPTH),
                        (bx2 - nx * RELIEF_DEPTH, by2 - ny * RELIEF_DEPTH),
                        (bx2 + nx * RELIEF_DEPTH, by2 + ny * RELIEF_DEPTH),
                        (ax2 + nx * RELIEF_DEPTH, ay2 + ny * RELIEF_DEPTH)]))
    # TWO RELIEFS THAT NEARLY MEET LEAVE METAL NOTHING CAN CUT. At one route
    # position a pair of corner notches touched at a single point, which
    # pinches the metal between them to ZERO width and makes the blank retrace
    # itself down its own fold line. Half a millimetre of route shift either
    # way and they overlapped cleanly instead, which is the kind of thing that
    # only shows up when something else moves. Where two reliefs come within
    # min feature of each other, merge them: the sliver between them could
    # never have been cut anyway, and removing it costs a few square
    # millimetres of a face that is already relieved there.
    merged = True
    while merged:
        merged = False
        for i in range(len(notches)):
            for j in range(i + 1, len(notches)):
                if notches[i].distance(notches[j]) >= MFG.MIN_FEATURE:
                    continue
                h = unary_union([notches[i], notches[j]]).convex_hull
                # NOT ACROSS A FLAP'S ATTACHMENT. The hull bridges the gap
                # between two reliefs, and if that gap is where a flap joins
                # the top face the bridge cuts the flap off - 878 mm2 of the
                # blank came away as a separate piece the first time. A relief
                # may swallow a sliver of bare edge; it may never swallow a
                # fold line that is carrying a panel.
                if h.intersects(fu.buffer(-1e-6)):
                    continue
                notches = ([notches[k] for k in range(len(notches))
                            if k not in (i, j)] + [h])
                merged = True
                break
            if merged:
                break
    return notches


ROOF_VENTS = True               # the plate's vent pattern continues across the roof


def carcass_blank(path=None, roof_vents=None):
    """The carcass as it is actually cut: a flat Z with flaps, not a rectangle.

    The bend lines here run ALONG the route, so they kink at every corner -
    which is the whole reason the carcass has relief and the skins do not. The
    flat pattern is therefore the top face's Z, with a downstand panel and then
    a foot panel unfolded outward from each LEG of each edge, and a relief gap
    between consecutive panels at every corner.

    Returned as (top polygon, [flap dicts]) in plate coordinates, 1:1.
    """
    path = route45() if path is None else path
    d = carcass_dev()
    # DEVELOPED, not 3D. The top face runs to the FOLD LINE, half a bend
    # deduction inboard of its own sharp corner, and each flap unfolds by its
    # developed length - not by the height it ends up at.
    top = Polygon(offset(path, d["fold1"], SHOW)
                  + offset(path, d["fold1"], FAR)[::-1]).buffer(0)
    tn, ang = turns(path), deflections(path)
    # PER-FLAP DEPTH. A footless flap is only down_flat_free deep; relieving it
    # as if it carried a foot over-cuts by about 2.9 mm and left the far leg-4
    # downstand a 3.31 mm sliver against 16-58 mm for every other one.
    depth_footed = d["down_flat"] + d["foot_flat"]
    depth_free = d["down_flat_free"]
    flaps = []
    for sgn in (SHOW, FAR):
        pts = offset(path, d["fold1"], sgn)
        n = len(pts) - 1
        for i in range(n):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            L = math.hypot(bx - ax, by - ay) or 1.0
            ux, uy = (bx - ax) / L, (by - ay) / L
            depth = (depth_footed if sgn == foot_side_for(i) else depth_free)
            r0 = (relief_for(ang[i - 1], depth, tn[i - 1] * sgn < 0)
                  if i > 0 else 0.0)
            r1 = (relief_for(ang[i], depth, tn[i] * sgn < 0)
                  if i < n - 1 else 0.0)
            a = (ax + ux * r0, ay + uy * r0)
            b = (bx - ux * r1, by - uy * r1)
            nx, ny = uy * sgn, -ux * sgn          # outward from the top face
            # STAGGER THE FOOT. carcass_bonds() alternated sides but the BLANK
            # did not, so feet were cut on both sides of every leg and the
            # channel closed to 8.0 mm against a 22 mm bundle. The downstand
            # stays on both sides - it is the wall - only the foot alternates.
            foot_side = foot_side_for(i)
            _legL = math.hypot(b[0] - a[0], b[1] - a[1])
            # THE FOOT IS WHATEVER IS LEFT after the notch, the card washers
            # and the tab stations have taken their intervals out of it. Each
            # piece is its own flap with its own fold; the wall's free edge
            # steps between footed and free depth and carries a relief where
            # every foot bend ends.
            segs = []
            if sgn == foot_side:
                segs = _foot_segments(
                    _foot_exclusions(a, b, i, sgn, path, d), _legL)
            d0 = 0.0
            # the wall itself starts past the connector notch
            ws = _wall_start(a, b, i, sgn, path, d)
            if _legL - ws < WALL_SEG_MIN:
                continue                     # no stub: the top face just ends here
            segs = [(max(t0, ws), t1) for t0, t1 in segs if t1 - max(t0, ws) >= FOOT_SEG_MIN]
            aw = (a[0] + ux * ws, a[1] + uy * ws)
            if segs:
                flaps.append(dict(kind="downstand", sgn=sgn, leg=i,
                                  poly=_stepped_wall(aw, b, ux, uy, nx, ny, d0,
                                                     d["down_flat"],
                                                     d["down_flat_free"],
                                                     [(t0 - ws, t1 - ws) for t0, t1 in segs],
                                                     _legL - ws)))
            else:
                df = d["down_flat_free"]
                flaps.append(dict(kind="downstand", sgn=sgn, leg=i, poly=Polygon([
                    (aw[0] + nx * d0, aw[1] + ny * d0),
                    (b[0] + nx * d0, b[1] + ny * d0),
                    (b[0] + nx * df, b[1] + ny * df),
                    (aw[0] + nx * df, aw[1] + ny * df)])))
            _oml, _flat, _edge = foot_dev(sgn)
            reach = (CARCASS_HALF_DS + _oml) - d["fold1"]
            fd0, fd1 = d["down_flat"], d["down_flat"] + _flat
            for t0, t1 in segs:
                # THE CORNER TAPER, at a leg end only, and now at CONCAVE
                # corners: outward flaps converge where the route turns
                # toward them, which is the opposite corner to inward ones.
                e0 = e1 = 0.0
                if t0 <= 1e-9 and i > 0 and tn[i - 1] * sgn < 0:
                    e0 = max(0.0, folded_corner_trim(ang[i - 1], reach) - r0)
                if t1 >= _legL - 1e-9 and i < n - 1 and tn[i] * sgn < 0:
                    e1 = max(0.0, folded_corner_trim(ang[i], reach) - r1)
                fl = dict(kind="foot", sgn=sgn, leg=i, poly=Polygon([
                    (a[0] + ux * t0 + nx * fd0, a[1] + uy * t0 + ny * fd0),
                    (a[0] + ux * t1 + nx * fd0, a[1] + uy * t1 + ny * fd0),
                    (a[0] + ux * (t1 - e1) + nx * fd1,
                     a[1] + uy * (t1 - e1) + ny * fd1),
                    (a[0] + ux * (t0 + e0) + nx * fd1,
                     a[1] + uy * (t0 + e0) + ny * fd1)]), screws=[])
                if sgn == FAR:
                    fl["screws"] = _foot_screw_spots(a, ux, uy, nx, ny, t0, t1,
                                                     e0, e1, i, sgn, path, d)
                flaps.append(fl)
    if END_CAP:
        flaps.append(_end_cap_flap(path, d))
    notches = relief_notches(path, flaps, d)
    if notches:
        top = top.difference(unary_union(notches).buffer(0))
    # THE PATTERN CONTINUES ACROSS THE ROOF (2026-09-02, the owner's original
    # intent): the same arc field, same lattice origin, cut through the top
    # face between the bend keep-outs. vent_ocr is imported here, lazily -
    # vent_kit imports hardware, which imports this module.
    if (ROOF_VENTS if roof_vents is None else roof_vents):
        import vent_ocr as _VO
        g = _VO.roof_cells()
        if g is not None and not g.is_empty:
            top = top.difference(g)
    return top, flaps


def wall_stations(path=None):
    """The (leg, side) pairs that carry a WALL, read off the blank itself.

    A leg/side whose wall would be shorter than WALL_SEG_MIN along its fold
    has none (leg 4 far: 4.0 mm). The gate's "every station measured" rule
    and the order sheet's fold count take this set, not 2 x legs.
    """
    _top, flaps = carcass_blank(path, roof_vents=False)
    return {(f["leg"], f["sgn"]) for f in flaps if f["kind"] == "downstand"}


def carcass_fold_counts(path=None):
    """(walls, feet, endcap) fold counts, from the blank."""
    _top, flaps = carcass_blank(path, roof_vents=False)
    kinds = [f["kind"] for f in flaps]
    return (kinds.count("downstand"), kinds.count("foot"), kinds.count("endcap"))




# ---- the two facade heights ----------------------------------------------
# TALL   the skin runs past the top face and stands REVEAL proud of it. The
#        groove is a recess with a floor, and from a seated eye the top face
#        is not visible at all.
# FLUSH  the skin stops level with the top face. The 2.30 mm bond line then
#        opens as a slot at the top instead of a recess, and what the eye has
#        to judge changes: not one deliberate depth, but whether two edges
#        that are meant to be level actually are.
def skin_top(flush=False):
    return ZP if flush else ZR


def carcass_flat():
    """DELETED. It was a sixth derivation of the carcass section and wrong.

    It summed inside-mould-line legs, subtracted an OUTSIDE-mould-line
    deduction from them, ignored the staggered foot entirely - it has feet on
    both sides, a section that occurs nowhere - and its docstring claimed
    "four bends, all of them straight and full width, so none needs relief"
    for a part with fifteen folds that turn at every corner and are the reason
    the relief exists.

    It was already recorded as wrong: the note in carcass_dev() says
    "carcass_flat() reported 45.20" against the correct development, and cites
    it as one of the three places that computed this three ways. It was left
    in the file anyway, callable, for anyone who went looking for a function
    with this name.

    carcass_dev() is the derivation. It returns `flat_staggered`, which is the
    section this part actually has.
    """
    raise NotImplementedError(
        "carcass_flat() was a wrong second derivation - use carcass_dev(), "
        "whose flat_staggered is the section that exists")


def plan_to_flat(sgn, px, py, path=None):
    """A plan point -> (flat coordinate on the skin of side sgn, leg index).

    Projected onto the skin's mid-surface polyline and walked to the flat
    through the same bend-allowance bookkeeping that sets the blank's width.
    This was skin_tabs()'s private helper; hoisted so the feet can be placed
    on the skin's bottom edge with the same mapping the tabs use.
    """
    path = route45() if path is None else path
    r = carcass_ribbon(sgn, path)
    mid = offset(path, CARCASS_RIB_IN + T / 2.0, sgn)
    Rm = BEND_RADIUS + T / 2.0
    Rn = BEND_RADIUS + K_FACTOR * T
    ang = r["angles"]
    SB = [Rm * math.tan(math.radians(a) / 2.0) for a in ang]
    BA = [math.radians(a) * Rn for a in ang]
    best, bl, ba = 1e9, 0, 0.0
    for i in range(len(mid) - 1):
        (ax, ay), (bx, by) = mid[i], mid[i + 1]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        u = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        qx, qy = ax + dx * u, ay + dy * u
        dd = math.hypot(px - qx, py - qy)
        if dd < best:
            best, bl, ba = dd, i, u * math.sqrt(L2)
    run = 0.0
    for i in range(bl):
        lo = SB[i - 1] if i > 0 else 0.0
        hi = SB[i] if i < len(SB) else 0.0
        run += r["mid_legs"][i] - lo - hi
        if i < len(BA):
            run += BA[i]
    lo = SB[bl - 1] if bl > 0 else 0.0
    return run + (ba - lo), bl


def foot_spans_flat(sgn, path=None):
    """Where the feet lie under the skin of side sgn, in the skin's flat mm.

    Each outward foot piece of this side, mapped by its two fold-edge ends
    through plan_to_flat, widened by SKIN_FOOT_GAP each way.
    """
    path = route45() if path is None else path
    _top, flaps = carcass_blank(path)
    out = []
    for f in flaps:
        if f["kind"] != "foot" or f["sgn"] != sgn:
            continue
        c = list(f["poly"].exterior.coords)
        f0, _ = plan_to_flat(sgn, c[0][0], c[0][1], path)
        f1, _ = plan_to_flat(sgn, c[1][0], c[1][1], path)
        lo, hi = sorted((f0, f1))
        out.append((lo - SKIN_FOOT_GAP, hi + SKIN_FOOT_GAP))
    return sorted(out)


def skin_outline(sgn, flush=False, path=None):
    """THE skin blank as cut, in its own flat coordinates: body, tabs, steps.

    ONE derivation. make_production, make_templates and make_harness each
    built this themselves - a rectangle plus a rectangle per tab - and each
    drew a solid CUT line across every tab root. Now the outward feet add a
    second feature: over every foot the bottom edge STEPS UP by
    T + SKIN_FOOT_GAP so the skin clears the foot it would otherwise stand
    on; between feet - which is where the tabs are, by construction - it
    reaches the plate as before.
    """
    from shapely.geometry import box as _box
    path = route45() if path is None else path
    r = carcass_ribbon(sgn, path, flush=flush)
    w, h = r["flat"], r["height"]
    g = _box(0.0, 0.0, w, h)
    step = T + SKIN_FOOT_GAP
    # BRIDGE THE CORNER GAPS. Two feet on the same side meet at a corner
    # with a 6.7 mm relief gap between them, and that gap straddles the
    # skin's own 45-degree fold. Left as two spans, the skin kept a 2.3 mm
    # tooth reaching the plate exactly on its bend line - a feature inside
    # the keep-out, and a tooth for no reason. One raised run across it.
    spans = []
    for lo, hi in foot_spans_flat(sgn, path):
        if spans and lo - spans[-1][1] < 2 * BEND_KEEPOUT:
            spans[-1] = (spans[-1][0], hi)
        else:
            spans.append((lo, hi))
    for lo, hi in spans:
        g = g.difference(_box(max(0.0, lo), -1.0, min(w, hi), step))
    for t in skin_tabs(sgn, path):
        g = g.union(_box(t["flat"] - TAB_L / 2.0, -PLATE_T,
                         t["flat"] + TAB_L / 2.0, 0.0))
    g = g.buffer(0)
    if g.geom_type != "Polygon":
        raise ValueError("skin %s: outline is not one piece" % sgn)
    return g


def skin_tabs(sgn, path=None):
    """Where the locating tabs sit ALONG THE FLAT BLANK.

    The tab slots have been cut in the backplate since the ribbon architecture
    and the tabs themselves were never drawn - the skins went out as bare
    rectangles, so the plate would have shipped with nine openings into the
    channel for tabs that did not exist. The skins are also bond-only without
    them, which is the bowing risk that was never actually answered.

    A tab is OUTLINE, not a hole, so it is the one form of mechanical location
    that does not break the no-holes rule on the show face.

    Positions are converted through the SAME mid-surface walk the blank width
    uses, so a tab cannot land somewhere the fold marks disagree with.
    """
    path = route45() if path is None else path
    r = carcass_ribbon(sgn, path)
    mid = offset(path, CARCASS_RIB_IN + T / 2.0, sgn)
    Rm = BEND_RADIUS + T / 2.0
    Rn = BEND_RADIUS + K_FACTOR * T
    ang = r["angles"]
    SB = [Rm * math.tan(math.radians(a) / 2.0) for a in ang]
    BA = [math.radians(a) * Rn for a in ang]

    out = []
    for t in tab_stations(path):
        if t["sgn"] != sgn:
            continue
        f, bl = plan_to_flat(sgn, t["at"][0], t["at"][1], path)
        if TAB_L / 2 < f < r["flat"] - TAB_L / 2:
            out.append(dict(flat=f, at=t["at"], leg=bl))
    if not out:
        return out
    # ONE DATUM, the tab nearest the middle of the strip. Its slot is the tight
    # one; every other slot grows by the bend tolerance accumulated between it
    # and the datum. Sizing them all for the worst case would put 1.5 mm of
    # visible slot around every tab; sizing them all tight makes the part
    # unassemblable. This is the middle, and it is what a datum is for.
    mid = r["flat"] / 2.0
    datum = min(range(len(out)), key=lambda k: abs(out[k]["flat"] - mid))
    folds = r["folds"]
    for k, t in enumerate(out):
        a, b = sorted((out[datum]["flat"], t["flat"]))
        n = sum(1 for f in folds if a < f < b)
        t["bends_from_datum"] = n
        t["slot_l"] = SLOT_L_MIN + 2.0 * BEND_TOL * n
        # PER STATION, like slot_l above. SLOT_W was one global number built
        # from CARCASS_TOL = one bend; the two far leg-2 tabs sit on the wall
        # OPPOSITE that leg's staggered foot, three bends from it, and need
        # 5.678 mm rather than 4.154.
        t["slot_w"] = slot_w_for(t["leg"], sgn)
        t["datum"] = (k == datum)
    return out



def declared_gaps(path=None):
    """Slits in the carcass blank that are under min feature ON PURPOSE.

    There is one kind: the mitre where two downstand flaps of the same wall
    meet at a corner. In the flat pattern it is a slit; the moment the part is
    folded it is a corner joint with air on both sides, and SendCutSend's own
    figure for a gap where two flanges MEET is CORNER_GAP - a fifth of the min
    feature that governs a slot with metal all round it.

    THIS DOES NOT CLASSIFY THE CORNER. I tried to declare only the convex ones
    and the numbers said no: the gap at a corner is set by the flap DEPTH as
    much as by the turn, and depth now differs per leg because the foot
    alternates, so two mirror-image corners came out 3.67 and 0.40. Rather
    than assert a rule the geometry does not follow, declare every adjacent
    pair and let the gate enforce the two things that actually matter - a
    declared gap must itself clear CORNER_GAP, and a pinch anywhere else is
    still judged against min feature. Declaring cannot wave a real defect
    through, because a mitre that had closed up would fail the declaration.
    """
    from shapely.ops import nearest_points
    path = route45() if path is None else path
    _, flaps = carcass_blank(path)
    out = []
    # THE RELIEF CUTS MEET EACH OTHER AT A CORNER TOO. Two notches from
    # adjacent legs converge on the top face and leave a gap in AIR of 1.73 to
    # 1.91 mm - under min feature, with 4.87 mm of metal on both sides of it,
    # which the erosion test confirms. That is the same flanges-meet case the
    # vendor allows CORNER_GAP for, not a slot, so it is declared rather than
    # excused by loosening a threshold. Taken from relief_notches() so there is
    # no second derivation of where they are.
    ns = unary_union(relief_notches(path, flaps, carcass_dev()))
    for g in ([ns] if ns.geom_type == "Polygon" else list(ns.geoms)):
        r = list(g.exterior.coords)[:-1]
        n = len(r)
        segs = [LineString([r[a], r[(a + 1) % n]]) for a in range(n)]
        cum = [0.0]
        for sg in segs:
            cum.append(cum[-1] + sg.length)
        tot = cum[-1]
        w, wx, wy = 99.0, g.centroid.x, g.centroid.y
        for a in range(n):
            for b in range(a + 2, n):
                if a == 0 and b == n - 1:
                    continue
                # SKIP THE PAIRS THAT ARE MERELY ROUNDING A CORNER TOGETHER,
                # the same rule the gate uses. Without it this measured 0.163
                # mm between two edges of one right angle.
                if min(cum[b] - cum[a + 1], tot - cum[b + 1] + cum[a]) < 2.0:
                    continue
                if segs[a].distance(segs[b]) < w:
                    w = segs[a].distance(segs[b])
                    _q = nearest_points(segs[a], segs[b])[0]
                    wx, wy = _q.x, _q.y
        if w < MFG.MIN_FEATURE:
            # THE WAIST, NOT THE WHOLE COMPONENT. Declaring the entire merged
            # relief excused 11.4% of the carcass perimeter - the exemption is
            # for the narrow throat where two cuts meet, and everything else
            # in that component is ordinary cut edge that should still be
            # judged at min feature.
            # THE NARROW PART OF THE COMPONENT, computed rather than
            # guessed. Declaring the whole merged relief excused 11.4% of the
            # carcass perimeter; a disc around the tightest point was too
            # small and missed the rest of the same throat. A morphological
            # opening removes everything narrower than min feature, so what it
            # takes away IS the throat - exactly the region where two relief
            # cuts are running close to each other, and nothing else.
            wide = (g.buffer(-MFG.MIN_FEATURE / 2.0, join_style=2)
                     .buffer(MFG.MIN_FEATURE / 2.0, join_style=2))
            out.append(dict(at=(wx, wy),
                            region=g.difference(wide),
                            gap=w,
                            why="relief cuts merging at a corner, %.2f mm "
                                "of open cut with metal on both sides" % w))
    for sgn in (SHOW, FAR):
        legs = {f["leg"]: f for f in flaps
                if f["kind"] == "downstand" and f["sgn"] == sgn}
        for i in sorted(legs):
            if i + 1 not in legs:
                continue
            a, b = legs[i]["poly"], legs[i + 1]["poly"]
            p1, p2 = nearest_points(a, b)
            # THE WHOLE SLIT, not the single point where it is narrowest. A
            # mitre is a V, and its two flanks stay close to each other along
            # their whole length, so a checker that walks every pair of edges
            # finds the SAME opening again at 1.73 and 1.91 mm a couple of
            # millimetres from the tip. Declaring a point made those look like
            # eight fresh defects on a feature that is there on purpose.
            # ONLY WHERE THEY ARE ACTUALLY CLOSE. My first version took the
            # convex hull of the two flaps minus the flaps - the whole V - and
            # that excused 46.8% of the carcass outline: a 0.6 mm slit almost
            # anywhere on the part would have passed. The mitre is the narrow
            # tip, so the region is exactly the set of points within min
            # feature of BOTH flaps, and nothing else.
            slit = (a.buffer(MFG.MIN_FEATURE)
                    .intersection(b.buffer(MFG.MIN_FEATURE)))
            out.append(dict(
                at=((p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0),
                region=slit,
                gap=a.distance(b),
                why="mitre between legs %d and %d on the %s side"
                    % (i, i + 1, "show" if sgn == SHOW else "far")))
    return out


def folded_panels(path=None):
    """Every carcass panel as it sits AFTER folding, in plate coordinates.

    Each entry is (kind, leg, sgn, plan polygon, z0, z1). Folding about a fold
    line leaves the ALONG-LEG coordinate untouched and maps the perpendicular
    developed distance to a plan radius and a height:

        top face    d in [0, fold1]      radius d,            z = 0
        wall        d in [fold1, fold2]  radius HALF_IN..DS,  z 0 down to -CLEAR_D
        foot        d in [fold2, edge]   radius HALF_IN..tip, z = -CLEAR_D

    This exists because the flat pattern cannot show an interference and the
    section slice cannot either - a section is taken across the run, and these
    two panels meet ALONG it, at a corner.
    """
    path = route45() if path is None else path
    d = carcass_dev()
    f1, f2, ed = d["fold1"], d["fold2"], d["edge"]
    tip = None                                   # per side now, see below
    _, flaps = carcass_blank(path)
    out = []
    for f in flaps:
        i, sgn = f["leg"], f["sgn"]
        (ax, ay), (bx, by) = path[i], path[i + 1]
        L = math.hypot(bx - ax, by - ay) or 1.0
        ux, uy = (bx - ax) / L, (by - ay) / L
        nx, ny = uy * sgn, -ux * sgn
        pts = []
        for x, y in f["poly"].exterior.coords[:-1]:
            vx, vy = x - ax, y - ay
            t = vx * ux + vy * uy
            dd = vx * nx + vy * ny
            if f["kind"] == "foot":
                _oml, _flat, _edge = foot_dev(sgn)
                r = CARCASS_HALF_DS + (dd - f2) * _oml / (_edge - f2)
            else:
                r = CARCASS_HALF_IN + ((dd - f1)
                                       * (CARCASS_HALF_DS - CARCASS_HALF_IN)
                                       / (f2 - f1))
            pts.append((ax + ux * t + nx * r, ay + uy * t + ny * r))
        z0, z1 = ((-CLEAR_D, -CLEAR_D + T) if f["kind"] == "foot"
                  else (-CLEAR_D, 0.0))
        out.append((f["kind"], i, sgn, Polygon(pts).buffer(0), z0, z1))

    # AND THE SKINS. check_folded() tested the carcass against itself and did
    # not know the skins existed - which is half the cover, and the half that
    # is bonded to the outside of the panels being tested. A skin is a plain
    # prism: the band between CARCASS_RIB_IN and CARCASS_RIB_OUT along the
    # route, standing from Z0 to the top. In this function's frame the top
    # face is z = 0 and everything hangs below it, so the skin runs from
    # -(ZP - Z0) up to the reveal.
    if END_CAP:
        (ax, ay), (bx, by) = path[0], path[1]
        L = math.hypot(bx - ax, by - ay) or 1.0
        ux, uy = (bx - ax) / L, (by - ay) / L
        ex, ey = uy, -ux                           # along the cap's fold
        w = CARCASS_RIB_IN - END_CAP_CLEAR
        o0, o1 = END_CAP_Y, END_CAP_Y + T           # outward, past the edge
        cap = Polygon([(ax + ex * w - ux * o0, ay + ey * w - uy * o0),
                       (ax - ex * w - ux * o0, ay - ey * w - uy * o0),
                       (ax - ex * w - ux * o1, ay - ey * w - uy * o1),
                       (ax + ex * w - ux * o1, ay + ey * w - uy * o1)])
        out.append(("endcap", 0, 0, cap, -CLEAR_D, 0.0))
    # ONE FRAME. The walls and feet hang from the top face's UNDERSIDE
    # (z = 0, feet at -CLEAR_D); the skins were placed from its UPPER
    # surface (-(ZP - Z0) = -12.5), two millimetres lower in the same picture.
    # That never showed against a wall, which a skin overlaps in z anyway; it
    # would have hidden every foot-to-skin collision now that the feet are
    # outward and under the skins. Skin bottom = plate face = the feet's
    # underside; over a foot the skin's bottom edge steps up T + SKIN_FOOT_GAP.
    for sgn in (SHOW, FAR):
        a = offset(path, CARCASS_RIB_IN, sgn)
        b = offset(path, CARCASS_RIB_OUT, sgn)
        band = Polygon(a + b[::-1]).buffer(0)
        feet = unary_union([g for k, _i, s2, g, _z0, _z1 in out
                            if k == "foot" and s2 == sgn] or [Polygon()])
        over = feet.buffer(SKIN_FOOT_GAP)
        raised = band.intersection(over)
        rest = band.difference(over)
        z_top = T + (ZR - ZP)
        if not rest.is_empty:
            out.append(("skin", -1, sgn, rest, -CLEAR_D, z_top))
        if not raised.is_empty:
            out.append(("skin", -1, sgn, raised,
                        -CLEAR_D + T + SKIN_FOOT_GAP, z_top))
    return out


def skin_fold_layer(turn):
    """Which layer a skin's fold goes on. UP on a RIGHT turn. Here is why.

    A DXF is read from +z, so "up" means the flange rotates TOWARD the reader.
    That is the convention the carcass already fixes, unambiguously: the
    carcass is drawn 1:1 in PLATE coordinates and the plate is drawn as its
    OUTSIDE face viewed from outside, so the reader is outside the cover. Its
    walls have to fold toward the plate - away from the reader - and all
    fifteen of its folds are on BEND_DOWN. So in this project, UP is toward
    the reader.

    Now place a skin blank. Its tabs are drawn below y=0 and they drop into
    slots in the plate, so blank +y is away from the plate, world +Z. Its
    length runs along the route, so blank +x is the travel direction T. A
    right-handed frame then puts the drawn face's normal at

        n = T x Z = the RIGHT of travel

    which is corroborated by SHOW = +1 being "right of travel": the show
    skin's drawn face is its finished outer face, exactly as you would draw
    it. A fold toward the reader swings the downstream travel direction
    toward +n, and a swing toward the right of travel is a RIGHT turn.

        BEND_UP  == right turn == turns()[k] == -1
        BEND_DOWN == left turn == turns()[k] == +1

    THE CODE HAD THIS BACKWARDS, and so did the guard in the gate, which
    restated the same rule and therefore could never disagree with it. Folded
    to the layers as drawn, both skins came out mirror images: the show skin
    is the one finished visible surface on the assembly, and 5052-H32 that
    has been folded, coated and folded back cracks, so there is no rework.

    Round five made both skins carry the SAME marks, which was right and is
    still right - both blanks are laid out the same way, so the same mark must
    mean the same turn. It did not question whether the shared sense was the
    correct one. It was not.
    """
    return "BEND_UP" if turn < 0 else "BEND_DOWN"


def fold_layer(turn, angle):
    """The layer a fold goes on, WITH ITS ANGLE IN THE NAME.

    The uploaded files carry no text - that was deliberate, because notes
    outside the part inflate the envelope a quoting system reads - and a bend
    LINE with no angle is not a manufacturing instruction. A brake operator
    given four unlabelled bend lines on a 200 mm strip has no way to know they
    are 45 degrees and not 90, and the blank is only correct at 45.

    So the angle goes where it cannot be stripped: in the layer name.
    BEND_UP_45, BEND_DOWN_90. Direction and angle, machine-readable, in the
    file that actually gets sent.
    """
    return "%s_%d" % (skin_fold_layer(turn), round(angle))

if __name__ == "__main__":
    report()
