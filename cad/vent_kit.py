"""Primitives shared by the vent-field designs.

The 26 lane designs plus 5 synthesised ones reduce to a handful of generative
devices: parallel slot families, nested chevrons, lattices of a repeated
aperture, panel subdivisions, and rings. This is that vocabulary, so each
design is expressed as a short recipe rather than 30 lines of geometry.

FIELD WITHOUT THE COVER. These are drawn on the full vent zone, not the
L-shape the cable cover leaves. Zone X 214.4-309.0, Y 12.0-110.4, inset 3 mm
to X 217.4-306.0, Y 15.0-107.4 = 81.9 cm2.
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
from shapely.affinity import rotate, scale, translate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vent_field as VF                                     # noqa: E402

# 2.0 IS THE VENDOR'S FLOOR, NOT A TARGET. Generating exactly to it put the
# tightest web on the Interference plate at 2.011 mm - eleven microns of
# margin on a process whose own feature tolerance is about +/-0.13 mm, so a
# web drawn at 2.011 can arrive at 1.88 and be under the minimum it was
# designed to meet. Powder coat only helps here (it adds to both sides of a
# web), but the CUT happens on bare metal. 2.20 buys real margin; the cost is
# a handful of vents out of ninety-odd.
MIN_WEB = 2.20
INSET = 3.0


def field_nocover(inset=INSET):
    """The full rectangular zone, ignoring the cable cover entirely."""
    z = VF.ZONE
    return box(z["x0"] + inset, z["y0"] + inset, z["x1"] - inset, z["y1"] - inset)


def clip(geoms, field, min_area=3.0):
    out = []
    for g in geoms:
        if g is None or g.is_empty:
            continue
        g = g.intersection(field)
        if g.is_empty:
            continue
        for p in ([g] if g.geom_type == "Polygon" else list(getattr(g, "geoms", []))):
            if p.geom_type == "Polygon" and p.area >= min_area:
                out.append(p)
    return out


def enforce(geom, min_web=MIN_WEB):
    """Drop the smaller of any pair closer than min_web. Returns (geom, dropped).

    Spatially indexed: the naive all-pairs version is O(n^2) shapely distance
    calls, which on a design with 600 openings is minutes, not seconds. The
    tree query reduces it to the handful of genuine neighbours.
    """
    from shapely import STRtree
    if geom is None or geom.is_empty:
        return geom, 0
    parts = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    if len(parts) == 1:
        return geom, 0
    parts.sort(key=lambda p: -p.area)
    tree = STRtree(parts)
    kept_idx, dropped = set(), 0
    for i, c in enumerate(parts):
        near = tree.query(c.buffer(min_web))
        clash = False
        for j in near:
            j = int(j)
            if j != i and j in kept_idx and c.distance(parts[j]) < min_web:
                clash = True
                break
        if clash:
            dropped += 1
        else:
            kept_idx.add(i)
    kept = [parts[i] for i in sorted(kept_idx)]
    return (unary_union(kept) if kept else None), dropped


# --------------------------------------------------------------- families --
def slots(field, angle_deg, width, pitch, origin=None, length=400,
          seg=None, gap=2.4, width_fn=None, jitter_fn=None):
    """Parallel slots at an angle, optionally broken into segments."""
    x0, y0, x1, y1 = field.bounds
    cx = origin[0] if origin else (x0 + x1) / 2
    cy = origin[1] if origin else (y0 + y1) / 2
    a = math.radians(angle_deg)
    nx, ny = -math.sin(a), math.cos(a)          # normal
    span = math.hypot(x1 - x0, y1 - y0)
    n = int(span / pitch) + 3
    out = []
    for k in range(-n, n + 1):
        w = width_fn(k) if width_fn else width
        if w <= 0.4:
            continue
        d = k * pitch + (jitter_fn(k) if jitter_fn else 0.0)
        px, py = cx + nx * d, cy + ny * d
        if seg:
            steps = int(length / seg) + 1
            for j in range(-steps // 2, steps // 2 + 1):
                s0 = j * seg + gap / 2
                s1 = (j + 1) * seg - gap / 2
                if s1 - s0 < 4.0:
                    continue
                p0 = (px + math.cos(a) * s0, py + math.sin(a) * s0)
                p1 = (px + math.cos(a) * s1, py + math.sin(a) * s1)
                out.append(LineString([p0, p1]).buffer(w / 2, cap_style=1, resolution=6))
        else:
            p0 = (px - math.cos(a) * length / 2, py - math.sin(a) * length / 2)
            p1 = (px + math.cos(a) * length / 2, py + math.sin(a) * length / 2)
            out.append(LineString([p0, p1]).buffer(w / 2, cap_style=1, resolution=6))
    return out


def chevrons(field, apex, bear_a, bear_b, n, w0, w1, web, leg=140, step_dir=135):
    """Nested open chevrons marching along a direction."""
    out = []
    cx, cy = apex
    sd = math.radians(step_dir)
    for i in range(n):
        w = w0 + (w1 - w0) * (i / max(n - 1, 1))
        if i:
            prev = w0 + (w1 - w0) * ((i - 1) / max(n - 1, 1))
            adv = (prev + web) / math.sin(math.radians(abs(bear_a - bear_b) / 2))
            cx += adv * math.cos(sd)
            cy += adv * math.sin(sd)
        for b in (bear_a, bear_b):
            br = math.radians(b)
            p1 = (cx + leg * math.cos(br), cy + leg * math.sin(br))
            out.append(LineString([(cx, cy), p1]).buffer(w / 2, cap_style=2))
    return out


def lattice(field, cell_fn, px, py, x0=None, y0=None, stagger=0.0, keep=None):
    """A repeated aperture on a grid. cell_fn(cx, cy, i, j) -> geometry or None."""
    bx0, by0, bx1, by1 = field.bounds
    ox = x0 if x0 is not None else bx0
    oy = y0 if y0 is not None else by0
    out = []
    ni = int((bx1 - ox) / px) + 2
    nj = int((by1 - oy) / py) + 2
    for i in range(-1, ni):
        for j in range(-1, nj):
            cx = ox + i * px + (stagger * px if j % 2 else 0.0)
            cy = oy + j * py
            if keep and not keep(cx, cy, i, j):
                continue
            g = cell_fn(cx, cy, i, j)
            if g is not None:
                out.append(g)
    return out


def panels(field, ratios=(0.38, 0.5, 0.62), min_side=15.0, wall=2.8, radius=3.0,
           border=4.2, max_depth=4):
    """Guillotine-subdivide the field into cells, inset to leave walls."""
    counter = [0]

    def split(rect, depth=0):
        x0, y0, x1, y1 = rect
        w, h = x1 - x0, y1 - y0
        if depth >= max_depth or min(w, h) < min_side * 2:
            return [rect]
        r = ratios[counter[0] % len(ratios)]
        counter[0] += 1
        if w >= h:
            xm = x0 + w * r
            if min(xm - x0, x1 - xm) < min_side:
                return [rect]
            return split((x0, y0, xm, y1), depth + 1) + split((xm, y0, x1, y1), depth + 1)
        ym = y0 + h * r
        if min(ym - y0, y1 - ym) < min_side:
            return [rect]
        return split((x0, y0, x1, ym), depth + 1) + split((x0, ym, x1, y1), depth + 1)

    inner = field.buffer(-border)
    out = []
    for r in split(field.bounds):
        c = box(*r).intersection(inner)
        if c.is_empty or c.area < 100:
            continue
        c = c.buffer(-wall / 2).buffer(0)
        if c.is_empty:
            continue
        c = c.buffer(-radius).buffer(radius)
        for p in ([c] if c.geom_type == "Polygon" else list(getattr(c, "geoms", []))):
            if p.area >= 100:
                out.append(p)
    return out


def ring(cx, cy, r_in, r_out, bridges=3, bridge_w=2.6, start=90):
    """A ring broken into arcs by radial bridges."""
    out = []
    if r_in <= 0.2:
        return out
    half = math.degrees(math.asin(min(bridge_w / 2 / r_in, 0.99)))
    step = 360.0 / bridges
    for k in range(bridges):
        a0 = start + k * step + half
        a1 = start + (k + 1) * step - half
        if a1 <= a0:
            continue
        ts = np.linspace(math.radians(a0), math.radians(a1), 20)
        pts = [(cx + r_out * math.cos(t), cy + r_out * math.sin(t)) for t in ts]
        pts += [(cx + r_in * math.cos(t), cy + r_in * math.sin(t)) for t in ts[::-1]]
        p = Polygon(pts)
        if p.is_valid and p.area > 1.0:
            out.append(p)
    return out


def capsule(cx, cy, w, l, vertical=True):
    h = max(l - w, 0.01) / 2
    a = (cx, cy - h) if vertical else (cx - h, cy)
    b = (cx, cy + h) if vertical else (cx + h, cy)
    return LineString([a, b]).buffer(w / 2, cap_style=1, resolution=8)


def tri(cx, cy, side, up=True, rot=0.0):
    r = side / math.sqrt(3)
    a0 = 90 if up else 270
    pts = [(cx + r * math.cos(math.radians(a0 + rot + k * 120)),
            cy + r * math.sin(math.radians(a0 + rot + k * 120))) for k in range(3)]
    return Polygon(pts)


def build(fn, field, min_area=3.0, min_web=MIN_WEB):
    """Run a design function, clip, enforce the web, return (geom, dropped)."""
    raw = fn(field)
    parts = clip(raw if isinstance(raw, list) else [raw], field, min_area)
    if not parts:
        return None, 0
    return enforce(unary_union(parts), min_web)


# --------------------------------------------------------- expanded field --
DIE_CLEAR = 7.0        # stay near the bone, not at it
PAD_CLEAR = 4.0        # pad positions carry +-0.4 across, +-1.2-2.6 along, and
                       # config calls their SIZES the weak part - so be generous
NOTCH_CLEAR = 4.0
SCREW_CLEAR = 5.5      # as backplate_variants used
RAIL = 12.0            # edge rail, top and bottom


def expanded_field(inset=INSET, x0=None):
    """The vent area extended toward the die window and past the power plug.

    Requested 2026-08-24: reach over toward the bone (near it, not at it) and
    take the area beside the power plug, dropping below the screws under it.

    The binding constraint is NOT the fasteners - it is the THERMAL PADS.
    config is explicit that pad zones are keep-outs and must never be vented
    through, and the STRIP pad sits at X 116.6-133.1, Y 47.6-102.6, directly
    across the route toward the die window. So the expansion reaches the bone
    only along the low-Y and high-Y bands that pass either side of it.
    """
    from config import SCANNED as S
    from config import MFG
    from die_window import CENTRE, POLY as DP
    from hole_pattern import HOLES

    z = VF.ZONE
    # x0 defaults to the die window's right edge plus clearance. Passing
    # INSET instead opens the ground on the FAR side of the window as well -
    # the same keep-outs still apply, the pads and the window simply become
    # interior obstacles rather than the left-hand wall.
    left = (121.4 + DIE_CLEAR) if x0 is None else x0
    base = box(left, RAIL, z["x1"] - inset, 122.40 - RAIL)

    cuts = []
    cx, cy = CENTRE
    for nm, w, h, along, across, n in S.PADS_VS_DIE:
        px, py = cx + along, cy + across
        cuts.append(box(px - h / 2, py - w / 2, px + h / 2, py + w / 2)
                    .buffer(PAD_CLEAR))
    cuts.append(Polygon(DP).buffer(DIE_CLEAR))
    import backplate_v3 as B
    nx0 = B.NOTCH_CX - B.NOTCH_W / 2 - B.NOTCH_EXTRA_BRACKET
    nx1 = B.NOTCH_CX + B.NOTCH_W / 2
    cuts.append(box(nx0, -5, nx1, B.NOTCH_D).buffer(NOTCH_CLEAR))
    for x, y, t, src in HOLES:
        cuts.append(Point(x, y).buffer(SCREW_CLEAR))

    # THE COVER'S OWN HARDWARE. The field runs UNDER the cover deliberately -
    # the pattern reads across both parts - but the cover also bolts through
    # the plate, and nothing here ever excluded those features. Checked
    # 2026-08-29: 15 of 19 of them clashed with the Interference field and 13
    # of 19 with Bit Plane, several overlapping a vent hole outright. The
    # fasteners for the plate were cut out; the fasteners for the COVER were
    # not, because they did not exist when this was written.
    try:
        import hardware as _HW
        for h in _HW.holes():
            if h["part"] != "backplate":
                continue
            g = (h["geom"] if h["geom"] is not None
                 else Point(h["at"]).buffer(h["d"] / 2.0))
            # AT THE WEB RULE. Buffering the cover's hardware by MIN_FEATURE
            # left exactly MIN_FEATURE of metal between a vent and a tab slot
            # - 2.011 mm, eleven microns of margin - which is the vendor's
            # floor and not a target.
            cuts.append(g.buffer(MIN_WEB))
    except Exception as _e:
        # NOT "keep the field buildable". A field built without its keep-outs
        # is a valid DXF with holes through things that must not have holes,
        # and it would ship looking exactly like a good one.
        raise RuntimeError("vent_kit: cover hardware not excluded (%s)" % _e)

    # THE CHANNEL FLOOR. config states the rule outright - "Only the CHANNEL
    # needs to stay solid; the flanges sit over pattern deliberately" - and
    # nothing had ever implemented it. 234 mm2 of vent opening on Interference
    # and 278 on Bit Plane were cut straight through the floor the cable lies
    # on, so a 600 W bundle would rest on laser-cut hole edges with the fin
    # stack's exhaust, and at low x the bare PCB, on the other side.
    #
    # This band also SUPERSEDES the foot bond bands that used to be listed
    # here: the feet fold inboard from CARCASS_HALF_IN, so every one of them
    # lies inside the channel already.
    #
    # AND IT DOES NOT SWALLOW ITS OWN FAILURE. The old block printed
    # "not excluded (...)" and carried on, which would have produced a
    # perfectly valid DXF with the keep-out silently missing.
    # THE CHANNEL IS NOT A KEEP-OUT ANY MORE (2026-09-03, the owner's call:
    # the pattern must run under the channel so the plate stands on its own
    # if the cover is ever left off). The reason it WAS one is above and is
    # real - the bundle lies on the perforated floor and the fin stack's
    # exhaust can reach it - but the roof now carries the same vents by the
    # same decision, so air already moves through the channel; the cells
    # are 4-6 mm hexes under a 22 mm sleeved bundle; and 12V-2x6 cable is
    # rated well above GPU exhaust. This subtracted
    # the whole channel - route45() buffered to the wall line - from the
    # field, written when the feet folded INWARD and lay inside it. The feet
    # are outward now and are kept out by vent_ocr.plate_field() on their
    # own footprints, and the owner wants the pattern to run under the
    # channel so the plate stands on its own if the cover is ever left off.

    f = base.difference(unary_union(cuts))
    parts = [f] if f.geom_type == "Polygon" else list(f.geoms)
    parts = [p for p in parts if p.area >= 150.0]
    return unary_union(parts), sorted(parts, key=lambda p: -p.area)
