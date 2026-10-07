"""The cable cover's footprint on the plate, as outlines to print and check.

Purpose: verify the ROUTE in two dimensions before anything is committed to a
cross-section. The cross-section is blocked on three measurements off the
assembled card; the route is not, and it is the more expensive thing to get
wrong - a bad cross-section is a reprint, a bad route means the cover crosses
the vent zone in the wrong place or fouls the shroud.

Route ACROSS, chosen 2026-08-23 because it is the only one that delivers the
cable downward toward a bottom-mounted PSU.

The corner is CHAMFERED, not square: config.MEASURED.CABLE_CHAMFER cuts 30 mm
back along each leg and joins them, giving two 45 degree turns rather than one
90. A 12V-2x6 should not be folded, and the printed cover cannot be moulded
around a sharp corner without a crease either.
"""

from __future__ import annotations

import os
import sys

import numpy as np
from shapely.geometry import LineString

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cable_route_v3 as R                                  # noqa: E402
from config import MEASURED as M                            # noqa: E402


def chamfered(path, cut=None):
    """Cut each interior corner back by `cut` along both legs."""
    cut = M.CABLE_CHAMFER if cut is None else cut
    P = [np.array(p, float) for p in path]
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        u = (a - b) / np.linalg.norm(a - b)
        v = (c - b) / np.linalg.norm(c - b)
        t = min(cut, np.linalg.norm(a - b) * .9, np.linalg.norm(c - b) * .9)
        out += [b + u * t, b + v * t]
    out.append(P[-1])
    return out


def outlines(name=R.CHOSEN, clip=True):
    """(cover outer edge, channel interior) as closed point lists.

    FLANGES ARE CLIPPED TO THE PLATE.  Beyond the plate edge the flanges have
    nothing to sit on - they are contact surfaces - and at full 47 mm width
    they foul the motherboard and the CPU fans where the cable drops past the
    PCIe edge. Past the plate only the channel and its walls continue, 29 mm
    instead of 47, which is 9 mm back on each side.

    The same rule tidies the connector end for free: the stub that rises above
    the connector edge loses its flanges too, because there is no plate there
    either.
    """
    from shapely.geometry import Polygon
    cl = LineString(chamfered(R.ROUTES[name]))
    full = cl.buffer(R.COVER_W / 2.0, cap_style=2, join_style=2)
    walls = cl.buffer(M.CABLE_W / 2.0 + M.CABLE_WALL, cap_style=2, join_style=2)
    chan = cl.buffer(M.CABLE_W / 2.0, cap_style=2, join_style=2)
    if clip:
        import backplate_v3 as B
        from shapely.geometry import box as _box
        plate = Polygon(B.outline()).buffer(0)
        # FILL THE CONNECTOR NOTCH BACK IN before clipping. The clip exists
        # because past the plate's outer edge a flange has nothing to sit on.
        # The notch is not that - it is an interior bite with metal on both
        # sides, so a flange bridges it perfectly well. Clipping against the
        # raw outline treated the two as the same thing and cut the cover back
        # to its 29 mm walls exactly where it is meant to be capping the
        # connector, leaving 3.4 mm of the notch showing on the bracket side.
        nx0 = B.NOTCH_CX - B.NOTCH_W / 2.0 - B.NOTCH_EXTRA_BRACKET
        nx1 = B.NOTCH_CX + B.NOTCH_W / 2.0
        plate = plate.union(_box(nx0, -1.0, nx1, B.NOTCH_D + 0.001))
        full = full.intersection(plate).union(walls)
        if full.geom_type != "Polygon":
            full = max(full.geoms, key=lambda g: g.area)
    return (list(full.exterior.coords), list(chan.exterior.coords))


def segmented_outline(name=R.CHOSEN):
    """The cover as actually built now: 28 mm walls, no continuous flanges.

    Dropping the 9 mm flange each side takes the cover from 47 mm to 28 mm and
    frees 36.5 cm2 of plate - 43% less coverage, 14-20 points more of the vent
    pattern visible, and the fastener at (171.28, 32.02) is no longer under
    anything, which retires its 6.5 mm relief.

    ONE FLANGE SURVIVES, on piece 1 only. The connector notch is 31.7 mm wide
    and sits 2.00 mm off the route centreline, because it was opened 4 mm
    toward the bracket earlier in the project. A 28 mm cover therefore leaves a
    3.85 mm strip of it showing. Piece 1 is straight, so a flange along it is a
    straight bend line and costs nothing - and it lands where the cover wants
    fixing down anyway.
    """
    from shapely.geometry import box as _box
    import backplate_v3 as B
    from config import MFG as _MFG
    half = M.CABLE_W / 2.0 + _MFG.THICKNESS            # 14.0
    cl = LineString(chamfered(R.ROUTES[name]))
    body = cl.buffer(half, cap_style=2, join_style=2)
    nx0 = B.NOTCH_CX - B.NOTCH_W / 2.0 - B.NOTCH_EXTRA_BRACKET
    pts = chamfered(R.ROUTES[name])
    y_end = pts[1][1]                                   # end of the first leg
    hood = _box(nx0 - 2.0, -1.0, B.NOTCH_CX - half, y_end)
    return list(body.union(hood).exterior.coords)


def screw_reliefs(name=R.CHOSEN):
    """Plate fasteners the cover lands on, with the relief each one needs.

    Head plus washer plus a little: the washer is 5.0 mm OD, so 6.5 mm of
    clearance hole in the flange. Countersinking is not available on 2 mm
    stock (SendCutSend need 0.125 in) and would not help anyway.
    """
    holes, _ = R.conflicts(R.ROUTES[name])
    return [(x, y, 6.5, s) for x, y, s in holes]


if __name__ == "__main__":
    cover, chan = outlines()
    from shapely.geometry import Polygon
    print(f"route {R.CHOSEN.upper()}   corner chamfer {M.CABLE_CHAMFER:.0f} mm")
    print(f"   cover outline   {len(cover):4d} pts   area "
          f"{Polygon(cover).area/100:6.1f} cm2")
    print(f"   channel outline {len(chan):4d} pts   area "
          f"{Polygon(chan).area/100:6.1f} cm2")
    for x, y, d, s in screw_reliefs():
        print(f"   relief  dia {d} at X {x:.2f} Y {y:.2f}   ({s})")
