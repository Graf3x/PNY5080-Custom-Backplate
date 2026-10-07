"""The real usable vent field, as a polygon, with its flange bands.

The synthesis agent reconstructed an L from the 57.3 cm2 area figure alone -
far arm X 269.4-309.0 plus top bar X 214.4-269.4 above Y 77.0 - and called the
area match "not a coincidence". It IS a coincidence: it back-solved a plausible
L that happens to total 57.3 cm2. The actual cover crosses the zone in two
places, so the true free region is not that L.

This module computes the real thing from the real cover footprint, so the
designs get clipped to the boundary that exists rather than the one that was
inferred. The designs survive that substitution precisely because the flange
requirement forced every generator to be a global function of plate
coordinates - they can be sampled anywhere and clipped to anything.
"""

from __future__ import annotations

import os
import sys

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backplate_v3 as B                                    # noqa: E402
import cable_route_v3 as R                                  # noqa: E402
import cover_footprint as CF                                # noqa: E402
from config import MEASURED as M                            # noqa: E402

ZONE = R.VENT                       # x0 214.4, x1 309.0, y0 12.0, y1 110.4
EDGE_INSET = 3.0                    # designs stay this far off a true plate edge
SHUT_RELIEF = 1.2                   # and this far off a cover shut line


def cover_solid():
    """The cover's footprint, clipped to the plate as the real part is."""
    co, _ = CF.outlines()
    return Polygon(co).buffer(0)


def field(inset=EDGE_INSET, shut=SHUT_RELIEF):
    """Usable vent area: the zone, minus the cover and its relief, inset."""
    z = box(ZONE["x0"], ZONE["y0"], ZONE["x1"], ZONE["y1"])
    free = z.difference(cover_solid().buffer(shut))
    free = free.buffer(-inset).buffer(0)
    if free.geom_type != "Polygon":
        free = max(free.geoms, key=lambda g: g.area)
    return free


def regions(min_area_mm2=100.0):
    """Every separate piece the cover leaves, largest first."""
    z = box(ZONE["x0"], ZONE["y0"], ZONE["x1"], ZONE["y1"])
    free = z.difference(cover_solid().buffer(SHUT_RELIEF))
    parts = [free] if free.geom_type == "Polygon" else list(free.geoms)
    parts = [p for p in parts if p.area >= min_area_mm2]
    return sorted(parts, key=lambda p: -p.area)


def flange_bands():
    """The two 9 mm cover flanges, which carry the same pattern.

    Cut from the same global field so the design reads across the joint.
    """
    cl_w = M.CABLE_W / 2.0 + M.CABLE_WALL
    co, _ = CF.outlines()
    outer = Polygon(co).buffer(0)
    from shapely.geometry import LineString
    inner = LineString(CF.chamfered(R.ROUTES[R.CHOSEN])).buffer(
        cl_w, cap_style=2, join_style=2)
    band = outer.difference(inner)
    z = box(ZONE["x0"] - 60, ZONE["y0"] - 20, ZONE["x1"] + 20, ZONE["y1"] + 20)
    band = band.intersection(z)
    parts = [band] if band.geom_type == "Polygon" else list(band.geoms)
    return [p for p in parts if p.area >= 50.0]


if __name__ == "__main__":
    f = field()
    print(f"vent zone      {ZONE['x1']-ZONE['x0']:.1f} x {ZONE['y1']-ZONE['y0']:.1f}"
          f" = {(ZONE['x1']-ZONE['x0'])*(ZONE['y1']-ZONE['y0'])/100:.1f} cm2")
    print(f"free of cover  {sum(p.area for p in regions())/100:.1f} cm2"
          f"  in {len(regions())} piece(s)")
    for i, p in enumerate(regions(), 1):
        x0, y0, x1, y1 = p.bounds
        print(f"   piece {i}: {p.area/100:5.1f} cm2   bbox X {x0:.1f}-{x1:.1f}"
              f"  Y {y0:.1f}-{y1:.1f}")
    print(f"\nusable after {EDGE_INSET} mm inset: {f.area/100:.1f} cm2")
    x0, y0, x1, y1 = f.bounds
    print(f"   bbox X {x0:.1f}-{x1:.1f}  Y {y0:.1f}-{y1:.1f}"
          f"   {len(f.exterior.coords)} vertices")
    print("\nWHAT THE SYNTHESIS ASSUMED:")
    far = box(269.4, 12.0, 309.0, 110.4)
    bar = box(214.4, 77.0, 269.4, 110.4)
    print(f"   far arm {far.area/100:.1f} + top bar {bar.area/100:.1f}"
          f" = {(far.area+bar.area)/100:.1f} cm2")
    real = unary_union(regions())
    print(f"   overlap with the real free region:"
          f" {unary_union([far,bar]).intersection(real).area/100:.1f} cm2")
    print(f"   assumed-but-not-free: "
          f"{unary_union([far,bar]).difference(real).area/100:.1f} cm2")
    print(f"   free-but-not-assumed: "
          f"{real.difference(unary_union([far,bar])).area/100:.1f} cm2")
    for i, b in enumerate(flange_bands(), 1):
        bx0, by0, bx1, by1 = b.bounds
        print(f"flange band {i}: {b.area/100:.1f} cm2  X {bx0:.1f}-{bx1:.1f}"
              f"  Y {by0:.1f}-{by1:.1f}")
