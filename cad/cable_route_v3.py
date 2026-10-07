"""Cable route, re-based on the measured plate - and a routing decision.

Supersedes the frame used by cable_route.py / config.MEASURED.CABLE_PATH,
which was drawn against PLATE_L 312 and PLATE_H 120 (both estimates) and a
connector position that was guessed. It also predates the vent zone being
identified, and that turns out to matter.

FRAME  (same as hole_pattern - X from the BRACKET end, Y from the CONNECTOR edge)
    The old path was given x-from-the-I/O-end, y-from-the-BOTTOM edge, so its
    y converts as  Y_new = PLATE_H - y_old.

WHAT IS NOW KNOWN
    connector centre     X 153.07, on the Y = 0 edge   (was guessed at 156)
    connector well       26.61 mm down from the card's top edge
    plate                324.0 x 122.40
    die window           X 69.7-121.4, Y 38.4-113.8
    vent zone            X 214.4-309.0, Y 12.0-110.4, about 93 cm2

THE PROBLEM WITH THE OLD ROUTE
    It leaves the connector, runs down the card to Y 76.4, turns, and crosses
    to X 284 before dropping off the PCIe edge. The cover is 47 mm wide, so
    that horizontal leg lands squarely across the middle of the vent zone and
    takes roughly half of it. When the route was drawn there was no known vent
    zone to conflict with; there is now.

TWO ROUTES, both starting at the same connector
    ACROSS  the original. Shortest run, cable drops off the PCIe edge near the
            far end, which suits a bottom-mounted PSU. Costs vent area.
    EDGE    hugs the connector edge to the far end, then turns down. Keeps the
            cover in a strip along the top, leaving the vent zone in one piece.
            Longer run and the turn happens at the far end.

CHOSEN 2026-08-23: ACROSS.
    It is the most expensive of the three in vent area - 43.1 cm2 of 93, where
    EDGE_FAR costs 33.0 - but it is the only one that delivers the cable
    DOWNWARD, toward a bottom-mounted PSU. The other two exit past the far end,
    which is the wrong place regardless of how much vent they save. Vent area
    can be designed around; where the cable has to arrive cannot.

    Two consequences to carry:
      * the vent zone is no longer one area. The horizontal leg splits it into
        a wide lower band and a thin upper strip - see free_regions().
      * the cover sits over ONE fastener, at X 171.28 Y 32.02 - but it lands
        in the FLANGE, not the channel. Zones on the vertical leg:
            channel  X 141.07-165.07
            wall     X 165.07-167.57
            flange   X 167.57-176.57   <- the screw, 3.71 mm in
        So the cable never touches it and only the flange needs relief: 6.5 mm
        for the head plus washer, in a flange 9 mm wide. Tight but it fits.

        COUNTERSINKING IS NOT AN OPTION, for two independent reasons.
        SendCutSend require 0.125 in (3.175 mm) of material to countersink at
        all and this plate is 2.0 mm. And the arithmetic would defeat it
        anyway: a 90 deg countersink taking our 3.2 mm clearance hole out to a
        3.8 mm head is only 0.30 mm of cone, against a button head about
        1.2 mm tall - the head would sit essentially proud. Tightening the
        hole to make room would give back the positional slack the pattern
        depends on. Relieve the flange instead.

STILL UNKNOWN, and these gate the CROSS-SECTION rather than the route:
    plug height above the plate, the 90 deg adapter's hood height, and whether
    a 35 mm straight run fits before the first bend. All three need the
    assembled card.
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import MEASURED                                 # noqa: E402
from die_window import POLY as DIE_POLY                     # noqa: E402
from hole_pattern import HOLES, PLATE_L, PLATE_W            # noqa: E402

CONN_X = 153.07
COVER_W = (MEASURED.CABLE_W + 2 * MEASURED.CABLE_WALL
           + 2 * MEASURED.CABLE_FLANGE)          # 47.0 mm overall

# the free zone, from the fastener gap beyond the PCB
VENT = dict(x0=214.4, x1=309.0, y0=12.0, y1=110.4)

ROUTES = {
    # EXIT MOVED 2026-08-23, from X 284 to 263, on a rule photo referenced to
    # the card's far end: the usable band is 2-3 in back from it. Read three
    # ways - our cut length 324, the measured 326.30, or the card's 329 - the
    # bands overlap at X 252.8-273.2, so the datum ambiguity does not matter.
    # 263.0 is the centre of that intersection.
    #
    # 284 was 10.8 mm outside the band. Going further toward the far end buys
    # nothing (the cable is already close to where it needs to be) and risks
    # fouling the case.
    "across": [(CONN_X, -8.0), (CONN_X, 76.4), (263.0, 76.4), (263.0, 132.0)],
    "across_old": [(CONN_X, -8.0), (CONN_X, 76.4), (284.0, 76.4), (284.0, 132.0)],
    "edge":   [(CONN_X, -8.0), (CONN_X, 26.0), (309.0, 26.0), (309.0, 132.0)],
    # Same idea as EDGE but it never turns down on the plate - it leaves past
    # the far end. The turn-down was what made EDGE expensive: a vertical leg
    # at X 309 is 47 mm of the vent zone's width AND its full height.
    "edge_far": [(CONN_X, -8.0), (CONN_X, COVER_W / 2), (340.0, COVER_W / 2)],
    # ---- the 90 degree era ------------------------------------------------
    # Every route above starts at y = -8, ABOVE the card's top edge, because a
    # straight plug needs 35 mm of run before its first bend and the cable had
    # to rise clear of the card and turn back down. A moulded 90 degree cable
    # puts that bend inside the hood, so the cable leaves through the notch
    # already lying on the plate and nothing stands proud of the top edge.
    #
    # NOTCH_EXIT is where the hood's cable exit sits within the 26.61 mm well.
    # It fed THIS route only, and this route was not chosen. See the note on
    # the constant at the bottom of the file: it is dead, not pending.
    "diag": [(CONN_X, 14.6), (CONN_X, 40.0), (263.0, 96.0), (263.0, 132.0)],
    # CHOSEN 2026-08-25. The ACROSS geometry - straight, 45, straight - kept
    # because of what it does for the WORDMARK, not for the cable: its
    # horizontal leg sits at y 76.4 and leaves a clean band along the connector
    # side for the mark to sit in. The shallow diagonal was shorter and hid
    # less pattern, but it ran straight through that band and broke the frame.
    #
    # It starts at y = 0.0, the card's top edge, not at -8.0 like the
    # straight-plug routes and not partway down the well like "diag". Two
    # reasons in one number: nothing stands proud of the card, and the cover
    # reaches far enough up to cap the connector notch and hide the plug.
    "across90": [(CONN_X, 0.0), (CONN_X, 76.4), (263.0, 76.4), (263.0, 132.0)],
}
# DEAD, not pending. This was carried for months as "a placeholder until the
# cable is in hand, and every number downstream moves with it" - and it was
# still being asked for on 2026-08-28. It is referenced by nothing:
#
#   grep -rn NOTCH_EXIT *.py  ->  this definition and its own comment
#   the chosen route is "across90", which starts at (CONN_X, 0.0), the card's
#   top edge, and never enters the well
#
# Only "diag" ever used it, by starting partway down the well at y 14.6, and
# "diag" lost to across90 on 2026-08-25 for what it did to the wordmark. The
# number stayed on the open list anyway. Kept here so the history is legible;
# delete it with "diag" if that route is ever removed for good.
NOTCH_EXIT = 14.6            # unused


def legs(path):
    return [(np.array(path[i]), np.array(path[i + 1])) for i in range(len(path) - 1)]


def corridor(path, width=COVER_W):
    """The cover's actual footprint: the chamfered centreline, buffered.

    Replaces the axis-aligned-box version for everything that needs to be
    right. That version assumed EVERY leg was horizontal or vertical - any
    other bearing fell through to the horizontal branch and produced a box
    spanning the whole diagonal. On the diag route that box reached from
    x 153 to 263 and y 16 to 120, and reported a fastener at (162.51, 116.12)
    as sitting under a cover that passes nowhere near it.
    """
    from shapely.geometry import LineString
    from cover_footprint import chamfered
    return LineString(chamfered(path)).buffer(width / 2.0, cap_style=2,
                                              join_style=2)


def footprint(path, width=COVER_W):
    """Axis-aligned boxes per leg. RECTILINEAR ROUTES ONLY - see corridor()."""
    out = []
    for a, b in legs(path):
        lo = np.minimum(a, b)
        hi = np.maximum(a, b)
        if abs(a[0] - b[0]) < 1e-9:                 # vertical leg
            out.append((lo[0] - width / 2, hi[0] + width / 2, lo[1], hi[1]))
        else:                                        # horizontal leg
            out.append((lo[0], hi[0], lo[1] - width / 2, hi[1] + width / 2))
    return out


def vent_loss(path, width=COVER_W):
    """How much of the vent zone the cover eats, by sampling the zone."""
    from shapely.geometry import box as _box
    zone = _box(VENT["x0"], VENT["y0"], VENT["x1"], VENT["y1"])
    return corridor(path, width).intersection(zone).area, zone.area


def conflicts(path, width=COVER_W):
    """Fasteners and the die window sitting under the cover."""
    from shapely.geometry import Point
    cor = corridor(path, width)
    holes = [(x, y, s) for x, y, t, s in HOLES if cor.contains(Point(x, y))]
    die = sum(1 for x, y in DIE_POLY if cor.contains(Point(x, y)))
    return holes, die


def report(name):
    path = ROUTES[name]
    lost, total = vent_loss(path)
    holes, die = conflicts(path)
    run = sum(float(np.hypot(*(b - a))) for a, b in legs(path))
    print(f"\n{name.upper():7s}  {' -> '.join('(%.0f,%.0f)' % tuple(p) for p in path)}")
    print(f"   cover run          {run:7.1f} mm   at {COVER_W:.0f} mm wide")
    print(f"   vent zone eaten    {lost/100:7.1f} cm2 of {total/100:.1f}"
          f"   ({100*lost/total:.0f}%)  -> {(total-lost)/100:.1f} cm2 left")
    print(f"   fasteners covered  {len(holes):7d}"
          + ("   " + ", ".join(s for _, _, s in holes) if holes else ""))
    print(f"   die window under it{'  yes' if die else '   no':>7s}")
    return dict(name=name, run=run, lost=lost, total=total, holes=holes, die=die)




CHOSEN = "across90"


def free_regions(name=CHOSEN, width=COVER_W, n=600):
    """The vent zone minus the cover, split into contiguous pieces.

    Worth doing because the answer is not one number: ACROSS cuts the zone in
    two, and a thin strip is not usable for the same things a wide band is.
    """
    from scipy import ndimage as ndi
    xs = np.linspace(VENT["x0"], VENT["x1"], n)
    ys = np.linspace(VENT["y0"], VENT["y1"], n)
    gx, gy = np.meshgrid(xs, ys)
    free = np.ones_like(gx, bool)
    for x0, x1, y0, y1 in [corridor(ROUTES[name], width).bounds] and             footprint(ROUTES[name], width):
        free &= ~((gx >= x0) & (gx <= x1) & (gy >= y0) & (gy <= y1))
    lab, k = ndi.label(free)
    cell = (xs[1] - xs[0]) * (ys[1] - ys[0])
    out = []
    for i in range(1, k + 1):
        m = lab == i
        yy, xx = np.where(m)
        out.append(dict(area=m.sum() * cell,
                        x0=xs[xx.min()], x1=xs[xx.max()],
                        y0=ys[yy.min()], y1=ys[yy.max()]))
    return sorted(out, key=lambda d: -d["area"])


if __name__ == "__main__":
    print(f"connector at X {CONN_X}   cover {COVER_W:.0f} mm wide"
          f"  ({MEASURED.CABLE_W} channel + 2x{MEASURED.CABLE_WALL} wall"
          f" + 2x{MEASURED.CABLE_FLANGE} flange)")
    print(f"vent zone  X {VENT['x0']}-{VENT['x1']}  Y {VENT['y0']}-{VENT['y1']}")
    for n in ROUTES:
        report(n)
