r"""
Custom GPU backplate for the PNY RTX 5080 OC Triple Fan.

Output: 2 mm 5052-H32, laser cut (SendCutSend), RAL 9003 gloss white powder coat.

Emits:
  out/backplate_CUT.dxf    <- upload THIS to SendCutSend (cut geometry only)
  out/backplate_REF.dxf    <- same + pad keep-outs/annotation, for your own use
  out/backplate_preview.png

Design intent
-------------
* The stock backplate is a functional heatsink: it couples to the PCB backside
  through thermal pads over the die, VRAM and VRM. Those zones are hard
  keep-outs; we never vent through them.
* Venting is concentrated over the flow-through fin stack (no PCB behind it),
  with a lighter secondary band over bare PCB areas.
* "Graf3X" is cut through as part of the vent pattern so it flows air and reads
  as branding. Letter islands are held by material bridges >= min feature width.

Run:  python backplate.py
"""

from __future__ import annotations

import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.textpath import TextPath

import ezdxf
from shapely.affinity import scale as shp_scale
from shapely.affinity import translate as shp_translate
from shapely.geometry import LineString, MultiPolygon, Polygon, box
from shapely.ops import nearest_points, unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import BRAND, HARDWARE, MEASURED, MFG, OUT_DIR  # noqa: E402

ARC_SEGS = 24


# ---------------------------------------------------------------- helpers


def as_polys(geom):
    """Normalise any shapely geometry to a list of Polygons."""
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)]


def rounded_rect(cx, cy, w, h, r):
    """Rectangle centred on (cx, cy) with radius-r corners."""
    r = min(r, w / 2 - 1e-6, h / 2 - 1e-6)
    base = box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    if r <= 0:
        return base
    return base.buffer(-r, quad_segs=ARC_SEGS).buffer(r, quad_segs=ARC_SEGS)


def circle(cx, cy, d):
    from shapely.geometry import Point

    return Point(cx, cy).buffer(d / 2, quad_segs=ARC_SEGS)


def _signed_area(ring):
    x = ring[:, 0]
    y = ring[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))


def _glyph(ch, font_path):
    """One character as a shapely geometry, baseline at y=0.

    TrueType fills by NON-ZERO winding, not even-odd. Glyphs like 'X' are drawn
    as two overlapping strokes; treating them as even-odd punches a false hole
    where the strokes cross. Contour orientation tells us which rings are
    outlines and which are true counters: union the outlines, subtract the
    counters.
    """
    fp = FontProperties(fname=font_path)
    tp = TextPath((0, 0), ch, size=100, prop=fp)

    rings = [np.asarray(r) for r in tp.to_polygons() if len(r) >= 4]
    if not rings:
        return Polygon()

    areas = [_signed_area(r) for r in rings]
    outer_sign = 1.0 if areas[int(np.argmax(np.abs(areas)))] > 0 else -1.0

    outlines, counters = [], []
    for ring, a in zip(rings, areas):
        if abs(a) < 1e-9:
            continue
        p = Polygon(ring)
        if not p.is_valid:
            p = p.buffer(0)
        (outlines if (a > 0) == (outer_sign > 0) else counters).extend(as_polys(p))

    geom = unary_union(outlines) if outlines else Polygon()
    if counters:
        geom = geom.difference(unary_union(counters))
    return geom.buffer(0)


def text_polygons(
    s, font_path, target_cap_h, max_width=None, tracking=3.0, stroke_adjust=0.0
):
    """Lay `s` out glyph-by-glyph with an explicit `tracking` gap in mm.

    Display faces like Impact set letters almost touching; at cut scale that
    leaves webs of material under the minimum feature width. Spacing each glyph
    by hand guarantees the gap. `stroke_adjust` (negative) thins the strokes,
    which fattens both the letter counters and the webs between glyphs.
    """
    glyphs = [g for g in (_glyph(ch, font_path) for ch in s) if not g.is_empty]
    if not glyphs:
        return Polygon()

    tops = [g.bounds[3] for g in glyphs]
    bottoms = [g.bounds[1] for g in glyphs]
    h100 = max(tops) - min(bottoms)
    widths = [g.bounds[2] - g.bounds[0] for g in glyphs]

    factor = target_cap_h / h100
    if max_width is not None:
        gaps = tracking * (len(glyphs) - 1)
        fit = (max_width - gaps) / sum(widths)
        factor = min(factor, fit)

    placed = []
    cursor = 0.0
    base_y = min(bottoms) * factor
    for g, w in zip(glyphs, widths):
        g = shp_scale(g, xfact=factor, yfact=factor, origin=(0, 0))
        gminx, _, _, _ = g.bounds
        placed.append(shp_translate(g, cursor - gminx, -base_y))
        cursor += w * factor + tracking

    result = unary_union(placed)
    if stroke_adjust:
        result = result.buffer(stroke_adjust, quad_segs=ARC_SEGS).buffer(0)
    minx, miny, _, _ = result.bounds
    return shp_translate(result, -minx, -miny)


def bridge_islands(text_geom, bridge_w):
    """Legacy helper kept for cad/font_sweep.py: bridge glyph counters using
    the text's own interior rings."""
    bridges = []
    for poly in as_polys(text_geom):
        _, _, _, poly_top = poly.bounds
        for interior in poly.interiors:
            ring = Polygon(interior)
            pt = ring.representative_point()
            _, r_min_y, _, r_max_y = ring.bounds
            bridges.append(
                box(
                    pt.x - bridge_w / 2.0,
                    (r_min_y + r_max_y) / 2.0,
                    pt.x + bridge_w / 2.0,
                    poly_top + 2.0,
                )
            )
    if not bridges:
        return text_geom, None
    bridge_geom = unary_union(bridges)
    return text_geom.difference(bridge_geom), bridge_geom


def weld_islands(plate, cuts, bridge_w, max_passes=8):
    """Reconnect every piece of material that the cut pattern would set adrift.

    Works on the finished material topology rather than on glyph interiors, so
    it catches counters, slot-field leftovers and anything else, whatever font
    or pattern produced them. Returns (cuts, n_bridges).
    """
    n = 0
    for _ in range(max_passes):
        material = plate.difference(cuts)
        pieces = sorted(as_polys(material), key=lambda p: -p.area)
        if len(pieces) <= 1:
            break
        body, islands = pieces[0], pieces[1:]
        bridges = []
        for isl in islands:
            a, b = nearest_points(isl, body)
            seg = LineString([(a.x, a.y), (b.x, b.y)])
            # zero-length when pieces already touch at a point: nudge outward
            if seg.length < 1e-9:
                seg = LineString(
                    [(a.x, a.y), (b.x + bridge_w, b.y)]
                )
            bridges.append(seg.buffer(bridge_w / 2.0, cap_style=2, quad_segs=ARC_SEGS))
            n += 1
        cuts = cuts.difference(unary_union(bridges))
    return cuts, n


def slot_field(x0, x1, y0, y1, slot_w, gap, r, y_inset=0.0):
    """Vertical rounded slots filling a window."""
    slots = []
    pitch = slot_w + gap
    n = max(1, int((x1 - x0 + gap) // pitch))
    span = n * pitch - gap
    start = x0 + ((x1 - x0) - span) / 2.0 + slot_w / 2.0
    for i in range(n):
        cx = start + i * pitch
        cy = (y0 + y1) / 2.0
        h = (y1 - y0) - 2 * y_inset
        slots.append(rounded_rect(cx, cy, slot_w, h, r))
    return unary_union(slots)


def drop_slivers(geom, min_width, min_area):
    """Remove fragments narrower than min_width or smaller than min_area."""
    keep = []
    for p in as_polys(geom):
        if p.area < min_area:
            continue
        if p.buffer(-min_width / 2.0, quad_segs=8).is_empty:
            continue
        keep.append(p)
    return unary_union(keep) if keep else Polygon()


# ---------------------------------------------------------------- checks


def design_rule_check(material, cuts, plate):
    problems = []

    # Erosion flags every sharp interior corner, which lasers cut fine. Only a
    # patch that is both sizeable AND elongated is a genuine thin web.
    thin = material.difference(
        material.buffer(-MFG.MIN_FEATURE / 2.0, quad_segs=8).buffer(
            MFG.MIN_FEATURE / 2.0, quad_segs=8
        )
    )
    real, corners = [], 0
    for p in as_polys(thin):
        x0, y0, x1, y1 = p.bounds
        span = max(x1 - x0, y1 - y0)
        if p.area >= 2.0 and span >= 4.0:
            real.append((p, span))
        elif p.area > 1e-6:
            corners += 1
    if real:
        real.sort(key=lambda t: -t[0].area)
        detail = ", ".join(
            f"({p.centroid.x:.0f},{p.centroid.y:.0f}) {p.area:.1f}mm^2/{s:.1f}mm long"
            for p, s in real[:5]
        )
        problems.append(
            f"{len(real)} genuine web(s) under {MFG.MIN_FEATURE} mm: {detail}"
        )
    if corners:
        print(f"  note: {corners} sharp-corner erosion artifact(s) ignored "
              "(not manufacturing defects)")

    narrow = [
        c
        for c in as_polys(cuts)
        if c.buffer(-MFG.MIN_HOLE_DIA / 2.0, quad_segs=8).is_empty
    ]
    if narrow:
        where = ", ".join(
            f"({c.centroid.x:.0f},{c.centroid.y:.0f}) {c.area:.1f}mm^2"
            for c in sorted(narrow, key=lambda c: -c.area)[:5]
        )
        problems.append(
            f"{len(narrow)} cut opening(s) narrower than {MFG.MIN_HOLE_DIA} mm "
            f"(min hole dia = material thickness): {where}"
        )

    for zx, zy, zw, zh in MEASURED.PAD_ZONES:
        zone = box(zx - zw / 2, zy - zh / 2, zx + zw / 2, zy + zh / 2)
        hit = cuts.intersection(zone)
        if not hit.is_empty and hit.area > 0.5:
            problems.append(
                f"VENT INTRUDES THERMAL PAD ZONE at ({zx:.0f},{zy:.0f}) "
                f"{zw:.0f}x{zh:.0f} - {hit.area:.1f} mm^2"
            )

    outside = cuts.difference(plate.buffer(-1.0))
    if not outside.is_empty and outside.area > 0.5:
        problems.append("cut geometry runs off/too close to the plate edge")

    return problems


# ---------------------------------------------------------------- export


def write_dxf(path, cut_geom, ref_layers=None, true_circles=None):
    """Write cut geometry as closed LWPOLYLINEs.

    `true_circles` is a list of (x, y, dia). Rings matching one of these are
    emitted as real CIRCLE entities instead of polygon approximations. Shapely
    tessellates every arc, and SendCutSend's parser reported our fastener holes
    as 96-line polygons with `"circular": false`. Lasers cut that fine, but a
    vendor cannot apply a hole operation (tapping, hardware, countersink) to a
    shape it does not recognise as a circle - so emit them properly.
    """
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4  # millimetres
    doc.header["$MEASUREMENT"] = 1
    msp = doc.modelspace()

    if "CUT" not in doc.layers:
        doc.layers.add("CUT", color=7)

    def add_ring(coords, layer):
        pts = [(float(x), float(y)) for x, y in coords]
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})

    circles = list(true_circles or [])

    def as_true_circle(ring):
        """Return (x, y, dia) if this ring is one of the declared circles."""
        p = Polygon(ring)
        c = p.centroid
        for (cx, cy, dia) in circles:
            if math.hypot(c.x - cx, c.y - cy) < 0.15:
                expect = math.pi * (dia / 2.0) ** 2
                if abs(p.area - expect) / expect < 0.05:
                    return (cx, cy, dia)
        return None

    n_circles = 0
    for poly in as_polys(cut_geom):
        add_ring(poly.exterior.coords, "CUT")
        for interior in poly.interiors:
            hit = as_true_circle(interior.coords)
            if hit:
                cx, cy, dia = hit
                msp.add_circle((cx, cy), dia / 2.0, dxfattribs={"layer": "CUT"})
                n_circles += 1
            else:
                add_ring(interior.coords, "CUT")

    if ref_layers:
        for name, color, geoms in ref_layers:
            if name not in doc.layers:
                doc.layers.add(name, color=color)
            for g in geoms:
                for poly in as_polys(g):
                    add_ring(poly.exterior.coords, name)
                    for interior in poly.interiors:
                        add_ring(interior.coords, name)

    doc.saveas(path)


def preview_png(path, material, cuts, pad_zones, screws):
    fig, ax = plt.subplots(figsize=(16, 6.6), dpi=150)
    fig.patch.set_facecolor("#16181c")
    ax.set_facecolor("#16181c")

    for p in as_polys(material):
        ax.add_patch(
            MplPolygon(
                np.asarray(p.exterior.coords),
                closed=True,
                facecolor="#f2f4f7",
                edgecolor="#9aa0a8",
                lw=0.8,
                zorder=2,
            )
        )
        for interior in p.interiors:
            ax.add_patch(
                MplPolygon(
                    np.asarray(interior.coords),
                    closed=True,
                    facecolor="#16181c",
                    edgecolor="#9aa0a8",
                    lw=0.6,
                    zorder=3,
                )
            )

    for zx, zy, zw, zh in pad_zones:
        ax.add_patch(
            MplPolygon(
                np.asarray(
                    box(zx - zw / 2, zy - zh / 2, zx + zw / 2, zy + zh / 2)
                    .exterior.coords
                ),
                closed=True,
                facecolor="#ff5c5c",
                alpha=0.30,
                edgecolor="#ff5c5c",
                ls="--",
                lw=1.2,
                zorder=4,
            )
        )

    if screws:
        sx = [s[0] for s in screws]
        sy = [s[1] for s in screws]
        ax.scatter(sx, sy, s=26, c="#6ba4ff", zorder=6, marker="o")

    ax.set_xlim(-8, MEASURED.PLATE_L + 8)
    ax.set_ylim(-8, MEASURED.PLATE_H + 8)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        f"Backplate mock-up  {MEASURED.PLATE_L:.0f} x {MEASURED.PLATE_H:.0f} x "
        f"{MFG.THICKNESS:.0f} mm  5052-H32 / RAL 9003\n"
        "red = thermal pad keep-out   blue = M2 fastener",
        color="#e6e6e6",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


# ---------------------------------------------------------------- build


def build():
    m = MEASURED
    plate = rounded_rect(
        m.PLATE_L / 2, m.PLATE_H / 2, m.PLATE_L, m.PLATE_H, m.CORNER_R
    )

    pad_keepout = unary_union(
        [
            box(
                zx - zw / 2 - m.PAD_MARGIN,
                zy - zh / 2 - m.PAD_MARGIN,
                zx + zw / 2 + m.PAD_MARGIN,
                zy + zh / 2 + m.PAD_MARGIN,
            )
            for (zx, zy, zw, zh) in m.PAD_ZONES
        ]
    )

    # --- branding, in its own panel above the slot field ----------------
    txt = text_polygons(
        BRAND.TEXT,
        BRAND.FONT,
        BRAND.CAP_HEIGHT,
        max_width=BRAND.MAX_WIDTH,
        tracking=BRAND.TRACKING,
        stroke_adjust=BRAND.STROKE_ADJUST,
    )
    tminx, tminy, tmaxx, tmaxy = txt.bounds
    logo_cx = (m.LOGO_X0 + m.LOGO_X1) / 2.0
    txt = shp_translate(
        txt,
        logo_cx - (tminx + tmaxx) / 2.0,
        m.LOGO_CY - (tminy + tmaxy) / 2.0,
    )
    text_cut = txt  # islands are welded after the full pattern is assembled

    # --- primary vent field over the flow-through fin stack -------------
    # Drop whole slots that come near the logo or a fastener boss rather than
    # clipping them; clipped slots leave sub-minimum webs.
    screw_keepout = unary_union(
        [circle(x, y, 2 * m.SCREW_KEEPOUT_R) for (x, y) in m.SCREWS]
    )
    keep_clear = unary_union([txt.buffer(6.0, quad_segs=ARC_SEGS), screw_keepout])
    field = unary_union(
        [
            s
            for s in as_polys(
                slot_field(
                    m.VENT_X0, m.VENT_X1, m.VENT_Y0, m.VENT_Y1,
                    slot_w=5.0, gap=3.2, r=2.4,
                )
            )
            if not s.intersects(keep_clear)
        ]
    )
    field = drop_slivers(field, MFG.MIN_HOLE_DIA, min_area=14.0)

    # --- secondary band over bare PCB, clear of every pad zone ----------
    band = unary_union(
        [
            s
            for s in as_polys(
                slot_field(
                    m.BAND_X0, m.BAND_X1, 16.0, 104.0,
                    slot_w=4.0, gap=4.5, r=1.9,
                )
            )
            if not s.intersects(screw_keepout)
        ]
    )
    band = band.difference(pad_keepout)
    band = drop_slivers(band, MFG.MIN_HOLE_DIA, min_area=18.0)

    # --- fasteners ------------------------------------------------------
    holes = unary_union(
        [circle(x, y, HARDWARE.SCREW_CLEAR_DIA) for (x, y) in m.SCREWS]
    )

    cuts = unary_union([field, band, text_cut, holes])
    cuts = cuts.intersection(plate.buffer(-2.5))  # keep a solid rim
    cuts, n_bridges = weld_islands(plate, cuts, BRAND.BRIDGE_W)
    # Welding can leave crescent-thin cut fragments beside a bridge. A laser
    # cannot resolve them; let them fill in as material (visually negligible).
    cuts = unary_union(
        [
            c
            for c in as_polys(cuts)
            if not c.buffer(-MFG.MIN_HOLE_DIA / 2.0, quad_segs=8).is_empty
        ]
    )
    material = plate.difference(cuts)

    problems = design_rule_check(material, cuts, plate)

    hit = [
        (x, y) for (x, y) in m.SCREWS
        if txt.buffer(m.SCREW_KEEPOUT_R).intersects(circle(x, y, 0.1))
    ]
    if hit:
        problems.append(
            "logo overlaps fastener boss at "
            + ", ".join(f"({x:.0f},{y:.0f})" for x, y in hit)
            + " - move LOGO_* or shrink BRAND.MAX_WIDTH"
        )

    os.makedirs(OUT_DIR, exist_ok=True)
    cut_dxf = os.path.join(OUT_DIR, "backplate_CUT.dxf")
    ref_dxf = os.path.join(OUT_DIR, "backplate_REF.dxf")
    png = os.path.join(OUT_DIR, "backplate_preview.png")

    screw_circles = [
        (x, y, HARDWARE.SCREW_CLEAR_DIA) for (x, y) in m.SCREWS
    ]
    # CUT file: outline + all openings, nothing else
    write_dxf(cut_dxf, material, true_circles=screw_circles)
    write_dxf(
        ref_dxf,
        material,
        true_circles=screw_circles,
        ref_layers=[
            (
                "REF_PAD_KEEPOUT",
                1,
                [
                    box(zx - zw / 2, zy - zh / 2, zx + zw / 2, zy + zh / 2)
                    for (zx, zy, zw, zh) in m.PAD_ZONES
                ],
            ),
        ],
    )
    preview_png(png, material, cuts, m.PAD_ZONES, m.SCREWS)

    open_area = sum(p.area for p in as_polys(cuts))
    plate_area = plate.area
    print(f"plate            {m.PLATE_L:.0f} x {m.PLATE_H:.0f} x {MFG.THICKNESS} mm")
    print(f"material area    {material.area:.0f} mm^2")
    print(f"open area        {open_area:.0f} mm^2  ({100*open_area/plate_area:.1f}% of plate)")
    print(f"fasteners        {len(m.SCREWS)} x {HARDWARE.SCREW} "
          f"(clearance dia {HARDWARE.SCREW_CLEAR_DIA:.2f} mm incl. coat allowance)")
    n_pieces = len(as_polys(material))
    print(f"islands welded   {n_bridges} bridge(s) @ {BRAND.BRIDGE_W} mm")
    print(f"cut entities     {n_pieces} outline(s) + "
          f"{sum(len(p.interiors) for p in as_polys(material))} openings")
    if n_pieces != 1:
        print(f"  ! {n_pieces - 1} loose piece(s) would fall out of the sheet")
    print()
    if problems:
        print("DESIGN RULE ISSUES:")
        for p in problems:
            print("  ! " + p)
    else:
        print("design rule check: PASS "
              f"(min feature {MFG.MIN_FEATURE} mm, min hole {MFG.MIN_HOLE_DIA} mm)")
    if not m.VERIFIED:
        print()
        print("*** MEASURED.VERIFIED is False - hole pattern and pad zones are")
        print("*** ESTIMATES. Trace the stock plate before ordering metal.")
    print()
    print("wrote:", cut_dxf)
    print("wrote:", ref_dxf)
    print("wrote:", png)


if __name__ == "__main__":
    build()
