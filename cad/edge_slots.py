"""Open-sided slots for fastener holes that sit too close to a plate edge.

THE PROBLEM
-----------
Three of the thirteen holes sit in the column 3.07-3.20 mm from the PCIe edge.
On a 3.2 mm clearance hole that leaves a web of 1.47-1.60 mm, under the 2.0 mm
minimum feature SendCutSend enforces on 2 mm 5052. Shrinking the hole does not
rescue it: you would need a 2.0 mm hole on a 2.0 mm screw - zero clearance - to
reach a 2.07 mm web. The holes cannot move, because they have to meet the
card's standoffs.

    hole X    Y      to edge   web
    120.69  119.33    3.07     1.47
     54.60  119.25    3.15     1.55
     15.84  119.20    3.20     1.60

THE FIX
-------
Open the hole to the edge instead of leaving a web that thin. The mouth is
sized to retain 75% of the bore, so the screw still bears on three quarters of
its annulus and the part gains a slide-on assembly instead of a fragile sliver
that can crack in handling or in the powder-coat line.

A retained fraction f leaves a mouth subtending (1 - f) * 360 deg. At f = 0.75
that is 90 deg, and the parallel walls sit at

    half_width = r * sin(45 deg) = 0.7071 * r

which for r = 1.6 gives a 2.26 mm mouth - itself above the 2.0 mm minimum
feature, so the slot is cuttable in its own right.

The slot MUST be spliced into the plate outline, never emitted as a separate
closed contour overlapping the edge. Overlapping contours double-cut the edge
and DFM checkers reject them.

WASHERS
-------
Already mandatory (config.HARDWARE.WASHER_REQUIRED) because a 3.8 mm head on a
3.2 mm hole bears on only 0.3 mm of annulus. With a slot they matter more, not
less: the 5.0 mm washer bridges the 2.26 mm mouth and is supported on both
sides of it.
"""

from __future__ import annotations

import numpy as np

SLOT_RETAIN = 0.75          # fraction of the bore kept


def needs_slot(dist_to_edge, r, min_feature):
    """True when the web between bore and edge is thinner than the cutter allows."""
    return (dist_to_edge - r) < min_feature


def half_width(r, retain=SLOT_RETAIN):
    """Half the mouth width that leaves `retain` of the circle."""
    return r * np.sin(np.radians((1.0 - retain) * 360.0 / 2.0))


def slot_points(cx, cy, r, edge_y=0.0, retain=SLOT_RETAIN, n=48, side="bottom"):
    """Outline points for one slot opening through the y = edge_y edge.

    side="bottom"  edge BELOW the bore, mouth opens -y. Ordered for a
                   counter-clockwise outline traversed in the +x direction.
    side="top"     edge ABOVE the bore, mouth opens +y. Ordered for a
                   counter-clockwise outline traversed in the -x direction,
                   which is how a CCW outline crosses its upper edge.

    Either way the traversal is: approach along the edge, in along the near
    wall, 270 deg CLOCKWISE around the bore so the material stays on the left,
    back out along the far wall.
    """
    hw = half_width(r, retain)
    dy = np.sqrt(max(r * r - hw * hw, 0.0))      # wall meets circle here
    if side == "bottom":
        a0 = np.degrees(np.arctan2(-dy, -hw))    # 225 deg at f = 0.75
        a1 = np.degrees(np.arctan2(-dy, +hw))    # 315 deg, reached clockwise
    else:
        a0 = np.degrees(np.arctan2(+dy, +hw))    # 45 deg
        a1 = np.degrees(np.arctan2(+dy, -hw))    # 135 deg, reached clockwise
        hw = -hw                                 # walls met in -x order
    if a1 > a0:
        a1 -= 360.0
    a = np.linspace(np.radians(a0), np.radians(a1), n)
    # The arc's own endpoints ARE the tops of the two walls, so do not emit
    # them separately. Doing so leaves a duplicate point differing by ~1e-15,
    # which is a zero-length segment - harmless to look at, but it makes any
    # self-intersection check report a crossing, and some CAM tools choke.
    pts = [(cx - hw, edge_y)]
    pts += [(cx + r * np.cos(t), cy + r * np.sin(t)) for t in a]
    pts += [(cx + hw, edge_y)]
    return pts


def splice(outline_pts, slots, edge_y=0.0, tol=1e-6):
    """Insert slot profiles into the run of `outline_pts` that lies on y = edge_y.

    Only the segment travelling in +x along that edge is touched.
    """
    slots = sorted(slots, key=lambda s: s[0])
    out, done = [], False
    for i, (x, y) in enumerate(outline_pts):
        out.append((x, y))
        if done or abs(y - edge_y) > tol:
            continue
        nxt = outline_pts[(i + 1) % len(outline_pts)]
        if abs(nxt[1] - edge_y) > tol or nxt[0] <= x:
            continue
        for cx, cy, r in slots:
            if x < cx < nxt[0]:
                out += slot_points(cx, cy, r, edge_y)
        done = True
    return out


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from hole_pattern import HOLES, PLATE_W
    from config import HARDWARE, MFG

    r = HARDWARE.SCREW_CLEAR_DIA / 2.0
    hw = half_width(r)
    print(f"retain {SLOT_RETAIN:.0%}  ->  mouth {2*hw:.2f} mm"
          f"   (min feature {MFG.MIN_FEATURE})")
    assert 2 * hw >= MFG.MIN_FEATURE, "mouth narrower than the cutter allows"
    n = 0
    for x, y, ty, src in HOLES:
        d = PLATE_W - y
        if needs_slot(d, r, MFG.MIN_FEATURE):
            n += 1
            print(f"   SLOT  X {x:7.2f}  web {d-r:.2f} mm  ({src})")
    print(f"{n} slotted, {len(HOLES)-n} closed")
