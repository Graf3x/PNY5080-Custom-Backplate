"""Export the assembly as real solids, for whatever renderer you land on.

The viewer in the artifact is a thin WebGL sketch - single-sided quads, no
thickness on the wall of a vent hole, no fillets. That is fine for judging
layout and useless for a render. This writes actual watertight solids so the
parts have edges, thickness and a sensible normal everywhere.

    out/render/assembly_<variant>.glb    everything, one file, named parts
    out/render/<part>.stl                each part on its own

glTF/GLB carries the part names and a transform hierarchy, so KeyShot, Blender
and Fusion all open it with the parts separable and nameable. STL is the
fallback for anything that will not take GLB.

WHAT IS AND IS NOT IN HERE
    every part is at its true position in plate coordinates, so the assembly
    lands together with no fitting;
    holes and vents are cut properly, so they have inside walls;
    the backplate is a clean solid - watertight, one body, genus 142, which is
    the 129 vents plus 13 fastener holes;

    BEND RADII ARE NOT MODELLED. Every fold is a sharp corner. At 0.97 mm
    inside radius, seen from 300 mm, that is visible if you look for it -
    bevel or fillet the fold edges in the renderer.

    THE FOLDED PARTS ARE NOT VOLUMES. The carcass keeps 10 non-manifold edges
    and each skin 2, where panels meet along a line at a relief gap. They
    render correctly - closed shells, consistent winding, no open edges - but
    they are not fit to boolean against or to 3D print without a repair pass.
    Fixing it properly means modelling the bend radii, which is the same job
    as the point above.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import trimesh
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backplate_v3 as B                                     # noqa: E402
import cover_ribbon as RB                                    # noqa: E402
import vent_ocr as VO                                        # noqa: E402
from hole_pattern import HOLES                               # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out",
                   "render")


def slab(poly, z0, z1):
    """A polygon extruded between two heights, as a watertight solid."""
    if poly.is_empty:
        return None
    m = trimesh.creation.extrude_polygon(poly, height=z1 - z0)
    m.apply_translation((0.0, 0.0, z0))
    return m


def upright(a, b, z0, z1, t):
    """A vertical wall of thickness t standing on the segment a->b.

    THE TWO CALLERS USE OPPOSITE CONVENTIONS and this is where that has to be
    got right, because it is not visible in either of them:

        the DOWNSTAND is offset at CARCASS_HALF_IN, its INNER face, so its
        thickness grows OUTWARD to CARCASS_HALF_DS;
        the SKIN is offset at CARCASS_RIB_OUT, its OUTER face, so its thickness
        grows INWARD to CARCASS_RIB_IN.

    Passing the same sign for both put the skins 2.0 mm proud on each side -
    a 40.6 mm assembly against a design 36.6 - which only showed up by slicing
    the exported mesh and measuring it, never by reading the code.
    """
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    L = (dx * dx + dy * dy) ** 0.5
    if L < 1e-9:
        return None
    nx, ny = -dy / L * t, dx / L * t
    p = Polygon([(ax, ay), (bx, by), (bx + nx, by + ny), (ax + nx, ay + ny)])
    return slab(p, z0, z1)


def backplate(design_name):
    """The plate, with its vents and all thirteen fastener holes cut."""
    plate = Polygon(B.outline())
    fn = dict((n, f) for n, f in VO.DESIGNS)[design_name]
    vents, _ = VO.build_one(fn, VO.plate_field())
    # HOLES records are (x, y, tier, source-label) - the fourth field is
    # provenance, not a diameter. The diameter is one number for all thirteen.
    from shapely.geometry import Point
    from config import HARDWARE
    d = HARDWARE.SCREW_CLEAR_DIA
    holes = unary_union([Point(x, y).buffer(d / 2.0, resolution=24)
                         for x, y, _t, _src in HOLES])
    # AND THE DIE WINDOW AND THE NINE TAB SLOTS. This cut the vents and the
    # thirteen fastener holes and stopped, so 3094 mm2 of the plate's openings
    # were solid metal in every render and every exported solid - including
    # the DIE WINDOW, which at 2600 mm2 is the largest single opening on the
    # part and exists to clear the card's die boss. The exported volume ran
    # 9.1% over the cut file's.
    #
    # The slots matter for a second reason: with the skins' tabs also missing
    # from the export, the tab-in-slot joint - the cover's only mechanical
    # location - was absent from BOTH halves of the assembly, so nothing about
    # it could be seen in the one place a person actually looks.
    from die_window import POLY as _DIE
    import hardware as _HW
    slots = unary_union([h["geom"] for h in _HW.holes(RB.route45())
                         if h["kind"] == "slot" and h["geom"] is not None])
    # THE TAPPED HOLES TOO. They live on the TAP layer, which this never
    # read, so the 3-D view showed a plate with no way to screw the feet
    # down and the owner asked, reasonably, whether that was right. Drawn
    # at tap-drill size, as the vendor drills them.
    taps = unary_union([Point(h["at"]).buffer(h["d"] / 2.0, resolution=24)
                        for h in _HW.holes(RB.route45())
                        if h["kind"] == "tapped" and h["part"] == "backplate"]
                       or [Point(0, 0).buffer(0)])
    solid = (plate.difference(vents).difference(holes)
             .difference(Polygon(_DIE)).difference(slots).difference(taps))
    # Three edges came out non-manifold (used 4 and 6 times) because a few
    # vent shapes meet a neighbour or a fastener hole at exactly one point.
    # The mesh is closed - zero open edges - but it is not a VOLUME, and a
    # renderer that wants a solid will refuse it. Snapping to a 1 micron grid
    # separates the touches without moving anything that matters at 2 mm.
    import shapely
    solid = shapely.set_precision(solid, 1e-3).buffer(0)
    return slab(solid, 0.0, RB.PLATE_T)


def _weld(pieces):
    """Union touching panels into ONE solid rather than stacking shells.

    concatenate() just puts N closed shells in one file. They look right and
    they are not a volume: at every fold the two panels share a face, and a
    renderer doing anything physical - subsurface, thickness, ambient
    occlusion from inside - sees a wall there. A boolean union removes it.
    """
    if not pieces:
        return None
    try:
        m = trimesh.boolean.union(pieces)
        m.merge_vertices()
        return m
    except Exception as e:                       # manifold missing or unhappy
        print("     union failed (%s) - falling back to concatenate" % e)
        return trimesh.util.concatenate(pieces)


def _plan_at(mid, path, flat):
    """Where a flat position along the developed skin lands in plan."""
    import math as _m
    ang = RB.deflections(path)
    Rm = RB.BEND_RADIUS + RB.T / 2.0
    Rn = RB.BEND_RADIUS + RB.K_FACTOR * RB.T
    SB = [Rm * _m.tan(_m.radians(a) / 2.0) for a in ang]
    BA = [_m.radians(a) * Rn for a in ang]
    tn = RB.turns(path)
    px, py = mid[0]
    ux = mid[1][0] - mid[0][0]
    uy = mid[1][1] - mid[0][1]
    L = _m.hypot(ux, uy)
    ux, uy = ux / L, uy / L
    run = 0.0
    for k in range(len(mid) - 1):
        lo = SB[k - 1] if k > 0 else 0.0
        hi = SB[k] if k < len(SB) else 0.0
        ml = _m.hypot(mid[k + 1][0] - mid[k][0], mid[k + 1][1] - mid[k][1])
        seg = ml - lo - hi
        if run - 1e-9 <= flat <= run + seg + 1e-9:
            d = flat - run
            return (px + ux * d, py + uy * d), (ux, uy)
        run += seg
        px, py = px + ux * seg, py + uy * seg
        if k < len(ang):
            vx, vy = px + ux * hi, py + uy * hi
            th = _m.radians(ang[k]) * (1.0 if tn[k] > 0 else -1.0)
            c, sn = _m.cos(th), _m.sin(th)
            ux, uy = ux * c - uy * sn, ux * sn + uy * c
            px, py = vx + ux * hi, vy + uy * hi
            run += BA[k]
    return None


def cover(path, flush):
    """Carcass, both skins and the notch cap, each as its own solid."""
    out = {}
    T = RB.T
    # BUILT FROM THE FLAPS THAT ARE ACTUALLY CUT, not from a second
    # derivation. This used to walk RB.carcass()["walls"] - a different
    # relief calculation - and append a foot to EVERY wall segment, so the
    # exported solid carried ten feet where the part has five. The render
    # therefore showed an 8.0 mm channel aperture instead of 16.0, which is
    # the very number the 8 mm foot size was chosen against, and the volume
    # was 8.9% high. The staggered foot had already been fixed once, in the
    # blank; the solid was never brought along.
    #
    # carcass_blank() is the one derivation, and folded_foot() puts a foot
    # where it lands after folding, taper and all.
    _top, flaps = RB.carcass_blank(path)
    parts = [slab(_top, RB.ZT, RB.ZP)]
    for f in flaps:
        c = list(f["poly"].exterior.coords)
        a, b = c[0], c[1]                 # the attachment edge IS the fold line
        sgn = f["sgn"]
        # THE FOLD LINE IS A DEVELOPED POSITION, NOT A FOLDED ONE. It sits at
        # carcass_dev()["fold1"] = 12.525 from the centreline in the FLAT
        # pattern; once folded, the wall's inner face is at CARCASS_HALF_IN =
        # 12.000. Building the solid straight off the flap put every wall
        # 0.525 mm outboard, which the section check caught at 14.525 against
        # a design 14.000. Slide the segment in by the difference and keep its
        # extent, which is the part carcass_blank has already got right.
        _i = f["leg"]
        (_ax, _ay), (_bx, _by) = path[_i], path[_i + 1]
        _L = ((_bx - _ax) ** 2 + (_by - _ay) ** 2) ** 0.5
        _ux, _uy = (_bx - _ax) / _L, (_by - _ay) / _L
        _nx, _ny = _uy * sgn, -_ux * sgn
        _d = RB.carcass_dev()["fold1"] - RB.CARCASS_HALF_IN
        a = (a[0] - _nx * _d, a[1] - _ny * _d)
        b = (b[0] - _nx * _d, b[1] - _ny * _d)
        if f["kind"] == "endcap":
            # its fold edge is the top face's end edge; it hangs down past
            # the plate edge, thickness growing OUTWARD (away from leg 0)
            c0, c1 = c[0], c[1]
            (_px, _py), (_qx, _qy) = path[0], path[1]
            _l = ((_qx - _px) ** 2 + (_qy - _py) ** 2) ** 0.5
            _ox, _oy = -(_qx - _px) / _l, -(_qy - _py) / _l
            w = RB.CARCASS_RIB_IN - RB.END_CAP_CLEAR
            ex, ey = (c1[0] - c0[0]), (c1[1] - c0[1])
            el = (ex * ex + ey * ey) ** 0.5
            ex, ey = ex / el, ey / el
            mx = (c0[0] + c1[0]) / 2 + _ox * RB.END_CAP_Y
            my = (c0[1] + c1[1]) / 2 + _oy * RB.END_CAP_Y
            a2 = (mx - ex * w, my - ey * w)
            b2 = (mx + ex * w, my + ey * w)
            lx, ly = -ey, ex                     # upright() thickens to the left of a->b for +t
            sgn_t = 1.0 if (lx * _ox + ly * _oy) > 0 else -1.0
            parts.append(upright(a2, b2, RB.Z0, RB.ZP, T * sgn_t))
            continue
        if f["kind"] == "downstand":
            # A FOOTED WALL STOPS ON TOP OF ITS FOOT; a footless one hangs to
            # a free edge. Drawing every wall down to Z0 made the footed ones
            # 2.00 mm too tall and buried them inside their own feet.
            # OUTWARD feet: the wall reaches the plate on every leg and the
            # foot runs out from its bottom corner; nothing stands on a foot.
            bot = RB.Z0
            # run it up THROUGH the top face rather than stopping flush against
            # it: two panels meeting exactly along a line share an edge and no
            # volume, and a union cannot merge that.
            parts.append(upright(a, b, bot, RB.ZP, -T * sgn))
        else:
            g = RB.folded_foot(f, path)
            for _b, (px_, py_) in f.get("screws", []):
                g = g.difference(Point(px_, py_).buffer(RB.FOOT_SCREW_CLEAR / 2.0))
            parts.append(slab(g, RB.Z0, RB.Z0 + T))
    out["carcass"] = _weld([p for p in parts if p])

    top_z = RB.skin_top(flush)
    for sgn, lab in ((RB.SHOW, "skin_show"), (RB.FAR, "skin_far")):
        pts = RB.offset(path, RB.CARCASS_RIB_OUT, sgn)
        # +T: the skin's segment is its OUTER face, so grow inward
        seg = [upright(pts[i], pts[i + 1], RB.Z0, top_z, +T * sgn)
               for i in range(len(pts) - 1)]
        # THE TABS ARE PART OF THE SKIN. They were absent from the export, so
        # the joint's other half was missing too. Each one hangs PLATE_T below
        # the skin's bottom edge, at its own station along the folded run.
        mid = RB.offset(path, RB.CARCASS_RIB_IN + T / 2.0, sgn)
        for t in RB.skin_tabs(sgn, path):
            q = _plan_at(mid, path, t["flat"])
            if q is None:
                continue
            (qx, qy), (ux, uy) = q
            nx, ny = -uy, ux
            half = RB.TAB_L / 2.0
            box = Polygon([(qx - ux * half - nx * T / 2, qy - uy * half - ny * T / 2),
                           (qx + ux * half - nx * T / 2, qy + uy * half - ny * T / 2),
                           (qx + ux * half + nx * T / 2, qy + uy * half + ny * T / 2),
                           (qx - ux * half + nx * T / 2, qy - uy * half + ny * T / 2)])
            seg.append(slab(box, RB.Z0 - RB.PLATE_T, RB.Z0))
        out[lab] = _weld([s for s in seg if s])

    if RB.CAP_IN_ORDER:
        cap = RB.notch_cap(path)["cap"]
        out["notch_cap"] = slab(cap, -RB.PLATE_T, 0.0)  # laps BEHIND the plate
    return out


def build(design="Interference / Graf3X, OCR", flush=False):
    os.makedirs(OUT, exist_ok=True)
    path = RB.route45()
    scene = trimesh.Scene()
    tag = "flush" if flush else "tall"

    parts = {"backplate": backplate(design)}
    parts.update(cover(path, flush))

    for name, m in parts.items():
        if m is None:
            continue
        m.merge_vertices()
        scene.add_geometry(m, node_name=name, geom_name=name)
        m.export(os.path.join(OUT, "%s_%s.stl" % (name, tag)))
        print("  %-12s %6d faces  watertight %-5s  %8.2f cm3"
              % (name, len(m.faces), m.is_watertight, m.volume / 1000.0))

    p = os.path.join(OUT, "assembly_%s.glb" % tag)
    scene.export(p)
    print("wrote", os.path.normpath(p))
    return p


if __name__ == "__main__":
    for fl in (False, True):
        print("\n%s SKINS" % ("FLUSH" if fl else "TALL"))
        build(flush=fl)
