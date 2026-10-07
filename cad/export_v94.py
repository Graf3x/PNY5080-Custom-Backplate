"""v94 solids: out/render_v94/assembly_v94.glb, per-part STLs, and the viewer
data (render_data_v94.json) the three.js page inlines.

Every part sits at its true position in plate coordinates, z up from the
plate's OUTER face. Bend radii are not modelled (sharp corners), same as the
v93 export.
"""

from __future__ import annotations

import base64
import json
import os
import sys

import numpy as np
import trimesh
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backplate_v3 as B                                     # noqa: E402
import cover_ribbon as RB                                    # noqa: E402
import export_solids as ES                                   # noqa: E402
import v94 as V                                              # noqa: E402
from hole_pattern import HOLES                               # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "render_v94")


def backplate(design_name):
    import shapely
    from config import HARDWARE
    from die_window import POLY as DIE
    plate = Polygon(B.outline())
    vents, _ = V.plate_vents(design_name)
    d = HARDWARE.SCREW_CLEAR_DIA
    bores = unary_union([Point(x, y).buffer(d / 2.0, resolution=24) for x, y, _t, _s in HOLES])
    clear = unary_union([Point(p).buffer(V.CLEAR_HOLE / 2.0, resolution=24) for p in V.plate_holes()])
    solid = plate.difference(vents).difference(bores).difference(Polygon(DIE)).difference(clear)
    solid = shapely.set_precision(solid, 1e-3).buffer(0)
    return ES.slab(solid, 0.0, V.PLATE_T)


def cover(pth):
    out = {}
    T = V.T
    top, flaps = V.carcass_blank(pth)
    parts = [ES.slab(top, V.Z_ROOF_UNDER, V.Z_ROOF_TOP)]
    d = RB.carcass_dev()
    shift = d["fold1"] - RB.CARCASS_HALF_IN
    for f in flaps:
        c = list(f["poly"].exterior.coords)
        a, b = c[0], c[1]
        sgn = f["sgn"]
        if f["kind"] == "endcap":
            (px, py), (qx, qy) = pth[0], pth[1]
            L = ((qx - px) ** 2 + (qy - py) ** 2) ** 0.5
            ox, oy = -(qx - px) / L, -(qy - py) / L
            w = RB.CARCASS_RIB_IN - RB.END_CAP_CLEAR
            ex, ey = (c[1][0] - c[0][0]), (c[1][1] - c[0][1])
            el = (ex * ex + ey * ey) ** 0.5
            ex, ey = ex / el, ey / el
            mx = (c[0][0] + c[1][0]) / 2 + ox * RB.END_CAP_Y
            my = (c[0][1] + c[1][1]) / 2 + oy * RB.END_CAP_Y
            a2 = (mx - ex * w, my - ey * w)
            b2 = (mx + ex * w, my + ey * w)
            lx, ly = -ey, ex
            sgn_t = 1.0 if (lx * ox + ly * oy) > 0 else -1.0
            parts.append(ES.upright(a2, b2, V.Z_ROOF_TOP - V.CAP_OML, V.Z_ROOF_TOP, T * sgn_t))
            continue
        i = f["leg"]
        (ax, ay), (bx, by), L, (ux, uy) = V._leg(pth, i)
        nx, ny = V._normal((ux, uy), sgn)
        a = (a[0] - nx * shift, a[1] - ny * shift)
        b = (b[0] - nx * shift, b[1] - ny * shift)
        parts.append(ES.upright(a, b, V.Z_CARC, V.Z_ROOF_TOP, -T * sgn))
    out["carcass"] = ES._weld([p for p in parts if p])

    for sgn, lab in ((RB.SHOW, "skin_show"), (RB.FAR, "skin_far")):
        pts = RB.offset(pth, V.SKIN_OUT, sgn)
        seg = [ES.upright(pts[i], pts[i + 1], V.Z_PLATE + 0.30, V.Z_ROOF_TOP, +T * sgn)
               for i in range(len(pts) - 1)]
        holes = [p for _x, p, _pi in V.foot_screws(sgn, pth)]
        for _pi, g in V.folded_feet(sgn, pth):
            for p in holes:
                if g.contains(Point(p)):
                    g = g.difference(Point(p).buffer(V.TAP_DRILL / 2.0, resolution=16))
            seg.append(ES.slab(g, V.Z_PLATE, V.Z_PLATE + T))
        out[lab] = ES._weld([s for s in seg if s])
    return out


def viewer_data(scene_parts):
    parts = {}
    lo = np.array([1e9, 1e9, 1e9]); hi = -lo
    for name, m in scene_parts.items():
        if m is None:
            continue
        v = m.vertices[m.faces].reshape(-1, 3).astype(np.float32)
        n = np.repeat(m.face_normals, 3, axis=0).astype(np.float32)
        parts[name] = dict(pos=base64.b64encode(v.tobytes()).decode("ascii"),
                           nrm=base64.b64encode(n.tobytes()).decode("ascii"),
                           tris=int(len(m.faces)))
        lo = np.minimum(lo, m.bounds[0]); hi = np.maximum(hi, m.bounds[1])
    c = (lo + hi) / 2.0; s = hi - lo
    return dict(meta=dict(center=[float(q) for q in c], size=[float(q) for q in s]), parts=parts)


def build(design="Interference / Graf3X, OCR"):
    os.makedirs(OUT, exist_ok=True)
    pth = V.path()
    scene = trimesh.Scene()
    parts = {"backplate": backplate(design)}
    parts.update(cover(pth))
    for name, m in parts.items():
        if m is None:
            continue
        m.merge_vertices()
        scene.add_geometry(m, node_name=name, geom_name=name)
        m.export(os.path.join(OUT, "%s_%s.stl" % (name, V.VERSION)))
        print("  %-12s %6d faces  watertight %-5s  %8.2f cm3"
              % (name, len(m.faces), m.is_watertight, m.volume / 1000.0))
    p = os.path.join(OUT, "assembly_%s.glb" % V.VERSION)
    scene.export(p)
    with open(os.path.join(OUT, "render_data_%s.json" % V.VERSION), "w") as fh:
        json.dump(viewer_data(parts), fh, separators=(",", ":"))
    print("wrote", os.path.normpath(p))
    return p


if __name__ == "__main__":
    build()
