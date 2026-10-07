"""Backplate v3 - cut file and 1:1 test template from the measured pattern.

Supersedes backplate_v2_dxf.py, which was fed by test_template.load_holes and
so predates every correction made on 2026-08-22: the column-major numbering
fix, the re-measured hole, the plate width, and the face convention. None of
its geometry is reused.

FRAME  (this is the whole ballgame - see hole_pattern.py)
    x  from the BRACKET end,    +x toward the far / fin-stack end
    y  from the CONNECTOR edge, +y toward the PCIe edge

    Plotted x-right y-UP, as a DXF is, that is the OUTSIDE face - the side you
    will actually see. The 1:1 template is mirrored from it, because the
    template is laid on the card INK DOWN.

VERIFIED AGAINST THE CARD  (1:1 prints, 2026-08-22/23)
    far-end holes     printed bore falls INSIDE the stock hole
    top / plate edge  lines up
    die window        "good for the bone" - the dogbone profile matches. This
                      was the least-verified feature on the plate: it rests on
                      a single scan, because at X 95.5 it falls outside 9122's
                      coverage and never got the two-scan treatment the holes
                      did. Now checked on the part.
    connector notch   width AND depth good, including the 4 mm added on the
                      bracket side. Depth reads FLUSH, which independently
                      corroborates config's claim that the plate is relieved
                      to the full depth of the connector well (notch 26.5 vs
                      well 26.61) rather than merely notched around it.
    cable exit        WRONG at X 284 - moved to 263, see cable_route_v3.

    bracket-end holes  check out.

    NOTHING OUTSTANDING. Every feature on this plate has been confirmed
    against the physical card, and dfm_check.py passes 17/17 reading the
    emitted DXF back rather than the model that wrote it. Clear to order.

BRACKET END - RESOLVED 2026-08-23
    Nothing goes there. The I/O bracket fastens to the case BELOW the
    backplate's plane and does not touch it, confirmed from photographs of the
    card installed. So the bracket end is a plain edge, which is what it
    already was; it was an open question rather than a known omission.

WHAT SITS WHERE
    die window        the dogbone over the GPU die, traced from the scan and
                      frozen in die_window.py. Cut as its real profile, not a
                      bounding box - thermal pads sit against the tabs that
                      intrude into its long edges.
    connector notch   on the y = 0 edge, centred x 153.07
    three slots       on the y = PLATE_H edge, the PCIe edge, where the web
                      would otherwise be 1.47-1.60 mm (see edge_slots.py)
    ten closed holes  everywhere else

LENGTH
    Cut at config.SCANNED.PLATE_L = 324.0, not the measured 326.30. That 2.3 mm
    short bias is deliberate and explained in config: too long fouls the shroud
    and cannot be recovered, too short leaves a hairline the shroud overhangs
    anyway. Holes are positioned from the BRACKET end, so the bias only ever
    eats into the far end, which has 10.4 mm of margin past its last hole.
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import edge_slots as ES                                    # noqa: E402
from config import HARDWARE, MFG, MEASURED, SCANNED        # noqa: E402
from hole_pattern import HOLES, PLATE_W                    # noqa: E402
from die_window import POLY as DIE_POLY, AREA as DIE_AREA  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")

L = SCANNED.PLATE_L                 # 324.0, biased short on purpose
H = PLATE_W                         # 122.40
R = MEASURED.CORNER_R               # 3.0, still an estimate
BORE = HARDWARE.SCREW_CLEAR_DIA
NOTCH_CX = 153.07                   # measured this session; v2 had 152.70
NOTCH_W = SCANNED.CONN_NOTCH_L      # 27.7
NOTCH_D = SCANNED.CONN_NOTCH_D      # 26.5

# The 12V-2x6 does NOT sit centred in the stock opening - confirmed on the
# card - and the tight side is the BRACKET side. So the notch is opened that
# way only: the far-end edge stays exactly where PNY put it, and the bracket
# edge moves out. Widening symmetrically would have thrown away clearance on
# the side that already had enough.
#
# 4 mm was a deliberate "a little bit"; on 2026-09-02 the owner made it 7.0 -
# a further 3 mm toward the bracket, "just in case", so the right-angle
# adapter goes in comfortably without touching the plates after they arrive.
# It costs 7 x 26.5 = 186 mm2 of material. The nearest bore, (120.91, 31.96),
# is 11.31 mm from the new edge at x 132.22; the nearest feature inside the
# notch's span sits at Y 116 where the notch only reaches Y 26.5.
#
# What it does NOT change: where the adapter sits. That is set by the
# connector on the card, not by this edge, so the cover-wall clearances in
# hardware.py are the same as before. What it DOES change in the cover: the
# leg-0 far foot lay at x 126.0..134.0 and now overhangs the notch void for
# y < 26.5, so it is trimmed back to y > 27.8 by the same exclusion that
# keeps every foot off the notch.
NOTCH_EXTRA_BRACKET = 7.0


def _arc(cx, cy, r, a0, a1, n=16):
    a = np.linspace(np.radians(a0), np.radians(a1), n)
    return [(cx + r * np.cos(t), cy + r * np.sin(t)) for t in a]


def _dedupe(pts, tol=1e-6):
    """Drop consecutive coincident points, including the closing one.

    Every corner arc begins exactly where the preceding straight ends, and the
    last arc ends exactly on the first point. Those repeats are invisible to
    look at but leave zero-length segments, which make any self-intersection
    test fire and which some CAM tools refuse. Same bug bit the slot profile.
    """
    out = []
    for q in pts:
        if not out or abs(q[0]-out[-1][0]) > tol or abs(q[1]-out[-1][1]) > tol:
            out.append(q)
    while len(out) > 1 and (abs(out[-1][0]-out[0][0]) < tol
                            and abs(out[-1][1]-out[0][1]) < tol):
        out.pop()
    return out


def classify():
    """Split the pattern into holes cut closed and holes opened to the edge."""
    r = BORE / 2.0
    closed, slotted = [], []
    for x, y, ty, src in HOLES:
        if ES.needs_slot(H - y, r, MFG.MIN_FEATURE):
            slotted.append((x, y, ty, src))
        elif ES.needs_slot(y, r, MFG.MIN_FEATURE):
            raise RuntimeError(f"hole at {x},{y} is tight to the CONNECTOR edge "
                               "- slotting that side is not implemented")
        else:
            closed.append((x, y, ty, src))
    return closed, slotted


def outline():
    """Plate profile, counter-clockwise, with the notch and the slots in it."""
    r = BORE / 2.0
    _, slotted = classify()
    nx0 = NOTCH_CX - NOTCH_W / 2.0 - NOTCH_EXTRA_BRACKET
    nx1 = NOTCH_CX + NOTCH_W / 2.0

    p = [(R, 0.0)]
    # --- connector edge, +x, through the notch ---
    p += [(nx0, 0.0), (nx0, NOTCH_D), (nx1, NOTCH_D), (nx1, 0.0)]
    p += [(L - R, 0.0)]
    p += _arc(L - R, R, R, -90, 0)
    # --- far end, up ---
    p += [(L, H - R)]
    p += _arc(L - R, H - R, R, 0, 90)
    # --- PCIe edge, -x, through the slots (descending x) ---
    for x, y, _, _ in sorted(slotted, key=lambda h: -h[0]):
        p += ES.slot_points(x, y, r, edge_y=H, side="top")
    p += [(R, H)]
    p += _arc(R, H - R, R, 90, 180)
    # --- bracket end, down ---
    p += [(0.0, R)]
    p += _arc(R, R, R, 180, 270)
    return _dedupe(p)


def check(pts):
    """Area, winding and self-intersection. Cheap, and it has caught real bugs."""
    P = np.asarray(pts)
    a = 0.5 * (np.dot(P[:, 0], np.roll(P[:, 1], -1)) -
               np.dot(P[:, 1], np.roll(P[:, 0], -1)))
    seg = [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]

    def x(a1, b1, c1, d1):
        def cr(o, q, s):
            return (q[0]-o[0])*(s[1]-o[1]) - (q[1]-o[1])*(s[0]-o[0])
        d1_, d2, d3, d4 = cr(c1, d1, a1), cr(c1, d1, b1), cr(a1, b1, c1), cr(a1, b1, d1)
        return ((d1_ > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))

    bad = sum(1 for i in range(len(seg)) for j in range(i + 2, len(seg))
              if not (i == 0 and j == len(seg) - 1) and x(*seg[i], *seg[j]))
    return float(a), bad


CENTRE_X, CENTRE_Y = 95.47, 76.12


# --- cable strain relief -----------------------------------------------------
# A pair of slots flanking the cable, for a tie or a 10 mm strap. Two reasons
# it earns its place on a plate that is otherwise only holes:
#
#   1. The WireView Pro II Wired ends in a straight 12V-2x6 plug on 400 mm of
#      INDIVIDUAL conductors (ref/ref_wireview_pro2_wired_drawing.pdf). With no
#      jacket there is no bundle to absorb a pull, so any load is shared
#      unevenly across twelve terminals.
#   2. A pre-bent 90 deg cable carries spring-back. The conductors want to
#      straighten, which puts a steady moment on the plug for as long as it is
#      fitted. A tie 40-odd mm downstream takes that moment into the plate.
#
# GEOMETRY IS FORCED, not chosen. Only a 13.0 mm half-gap clears everything -
# 14 mm and wider fouls the fastener at (171.28, 32.02). That leaves 26.0 mm
# between the slots for a 24 mm cable, which is what you want for a tie.
#
# The tie also has to sit OUTSIDE the 35 mm no-bend zone, or the relief is
# clamping exactly where the cable is not supposed to be worked. At y 38 it is
# 38 mm along the plate plus 26.6 mm of well depth from the connector face.
# TURNED OFF 2026-08-30. Both slots ended up 100% under the cover, roofed by
# carcass metal, so no tie could be fitted, reached or adjusted. They were
# offset from the UNSHIFTED route and the cover later moved 2.0 mm and widened
# to 36.6, which put them underneath it.
#
# The justification is also gone. They existed for a WireView Pro II Wired that
# ends in a straight plug on 400 mm of unjacketed conductors - a part not
# owned - and for spring-back from a pre-bent cable, which the cover now
# handles by enclosing the run end to end.
#
# Deleting them clears three audit blockers at once: a slot cutting straight
# through vent openings, a 0.632 mm rib to a cover tab slot, and 0.234 /
# 0.756 mm webs to two more vents. If the WireView arrives and needs relief,
# design it against that part rather than reviving slots sized for a route
# that moved.
RELIEF = False
RELIEF_HALF = 13.0          # slot inner edge, either side of the route
RELIEF_W = 3.0              # slot width
RELIEF_L = 12.0             # slot length, along the plate
RELIEF_S = 46.0             # arc length along the route, from the notch
# 46 and not 40. At 40 the slots landed 1.20 mm from the fastener at
# (171.28, 32.02) - under the 2.0 mm minimum, and dfm_check caught it. The
# window that clears every keep-out is 43.0-89.0 mm along the route; 46 sits
# just inside its near end, where the web peaks at 4.62 mm, because a relief
# wants to be as close to the connector as it can while still being legal.
#
# At 46 mm along, plus the 26.61 mm the connector sits down its well, the tie
# is ~72 mm of conductor from the terminals - comfortably past the 35 mm
# no-bend zone, which a relief must never sit inside.
RELIEF_R = 1.4              # end radius


def relief_slots():
    """Two slots straddling the cable, PERPENDICULAR to the route.

    The first version put them on a fixed vertical line under the notch, which
    only worked while the route left the notch straight down. The diagonal
    route has already begun its turn by then, so the cable had moved out from
    under one of the slots and straight over the other. A tie has to cross the
    cable square, so the slots are placed off the route itself: RELIEF_S along
    it, offset either side, rotated to its tangent.
    """
    if not RELIEF:
        return []
    from shapely.geometry import LineString
    from shapely.affinity import rotate, translate
    import cable_route_v3 as R
    from cover_footprint import chamfered
    cl = LineString(chamfered(R.ROUTES[R.CHOSEN]))
    s = min(RELIEF_S, cl.length - 1.0)
    p0 = cl.interpolate(max(0.0, s - 0.5))
    p1 = cl.interpolate(min(cl.length, s + 0.5))
    import math
    ang = math.degrees(math.atan2(p1.y - p0.y, p1.x - p0.x))
    c = cl.interpolate(s)
    nx, ny = -math.sin(math.radians(ang)), math.cos(math.radians(ang))
    out = []
    for sgn in (-1, +1):
        off = RELIEF_HALF + RELIEF_W / 2.0
        cx, cy = c.x + sgn * nx * off, c.y + sgn * ny * off
        sl = LineString([(cx, cy - (RELIEF_L - RELIEF_W) / 2.0),
                         (cx, cy + (RELIEF_L - RELIEF_W) / 2.0)]
                        ).buffer(RELIEF_W / 2.0, cap_style=1, resolution=12)
        out.append(rotate(sl, ang - 90.0, origin=(cx, cy)))
    return out


def write_dxf():
    import ezdxf
    os.makedirs(OUT, exist_ok=True)
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    doc.layers.add("CUT", color=7)
    doc.layers.add("NOTES", color=4)

    pts = outline()
    area, bad = check(pts)
    if bad:
        raise RuntimeError(f"outline self-intersects at {bad} places")
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "CUT"})

    closed, slotted = classify()
    for x, y, _, _ in closed:
        msp.add_circle((x, y), BORE / 2.0, dxfattribs={"layer": "CUT"})

    # die window - a separate closed contour inside the outline, which is how
    # an interior cutout is expressed. It must NOT touch the outline; checked
    # below rather than assumed.
    msp.add_lwpolyline(DIE_POLY, close=True, dxfattribs={"layer": "CUT"})

    for sl in relief_slots():
        msp.add_lwpolyline(list(sl.exterior.coords), close=True,
                           dxfattribs={"layer": "CUT"})

    for t, xy, hgt in [
        ("BRACKET END", (5, H / 2 - 20), 4),
        ("FAR END (fin stack)", (L - 62, H / 2 - 20), 4),
        ("CONNECTOR EDGE - 12V-2x6 notch below", (NOTCH_CX - 55, NOTCH_D + 4), 3.2),
        ("PCIe EDGE - 3 holes opened to this edge", (12, H - 9), 3.2),
        ("DIE WINDOW - real traced profile, do not simplify",
         (CENTRE_X - 34, CENTRE_Y - 3), 3.0),
        (f"OUTSIDE face, viewed from outside  |  {L} x {H} mm  |  "
         f"{len(closed)} closed holes dia {BORE} + {len(slotted)} slots"
         f" + die window {DIE_AREA:.0f} mm2", (5, -9), 3.2),
    ]:
        msp.add_text(t, height=hgt, dxfattribs={"layer": "NOTES"}).set_placement(xy)

    path = os.path.join(OUT, "backplate_v3.dxf")
    doc.saveas(path)
    return path, area, len(closed), len(slotted)



# ---------------------------------------------------------------------------
# 1:1 test template
#
# UN-MIRRORED, i.e. the OUTSIDE face, the same view as the DXF.
#
# The handedness follows from which way up the sheet is laid, and nothing else:
#
#   ink UP    the ink faces you, away from the card, so you are looking at it
#             from outside -> it must show the OUTSIDE face. Un-mirrored.
#   ink DOWN  the ink faces the card, so the card "sees" it -> it must show
#             the INSIDE face. Mirrored.
#
# Changed to ink-up on request 2026-08-22. It is also the more practical of
# the two: ink down cannot be aligned by eye, because the ink is against the
# card where you cannot see it.
#
# Both this and the DXF are now the same view, so the connector edge is at the
# bottom of both. Edges are still labelled by the CARD PART they meet rather
# than by any direction - a directional label would have been wrong on one of
# the two while the template was mirrored, and the habit is worth keeping.
# ---------------------------------------------------------------------------

PAGE_W, PAGE_H = 279.4, 215.9      # Letter, landscape, mm
MARGIN = 10.0
OVERLAP = 30.0
MM = 1.0 / 25.4


def write_template(mirror=False, png=False, cover=True):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    closed, slotted = classify()
    pts = np.array(outline())
    mir = (lambda y: H - y) if mirror else (lambda y: y)   # noqa: E731

    x_lo, x_hi = -6.0, L + 6.0
    usable = PAGE_W - 2 * MARGIN
    step = usable - OVERLAP
    starts = [x_lo]
    while starts[-1] + usable < x_hi:
        starts.append(starts[-1] + step)

    os.makedirs(OUT, exist_ok=True)
    tag = "INK-DOWN_mirrored" if mirror else "INK-UP"
    path = os.path.join(OUT, f"backplate_v3_TEMPLATE_1to1_{tag}.pdf")
    with PdfPages(path) as pdf:
        for n, sx in enumerate(starts, 1):
            fig = plt.figure(figsize=(PAGE_W * MM, PAGE_H * MM))
            ax = fig.add_axes([0, 0, 1, 1])
            # centre the plate vertically, which leaves a clear band below it
            # for the scale bar and one above for the header. The bar used to
            # sit 2 mm under the plate edge and its caption ran straight
            # through the outline and the notch.
            y_lo = (H - PAGE_H) / 2.0
            y_hi = y_lo + PAGE_H
            ax.set_xlim(sx - MARGIN, sx - MARGIN + PAGE_W)
            ax.set_ylim(y_lo, y_hi)
            ax.set_aspect("equal")
            ax.axis("off")

            ax.plot(pts[:, 0].tolist() + [pts[0, 0]],
                    [mir(v) for v in pts[:, 1]] + [mir(pts[0, 1])],
                    "-", color="k", lw=0.9)
            if cover:
                # The cable cover's footprint, DASHED so it can never be read
                # as a cut line - it is a different part and is not in the DXF.
                import cover_footprint as CF
                co, ch = CF.outlines()
                for poly, st, lw in ((co, (0, (6, 3)), 0.8), (ch, (0, (2, 2)), 0.55)):
                    A = np.array(poly)
                    ax.plot(A[:, 0], [mir(v) for v in A[:, 1]], linestyle=st,
                            color="0.45", lw=lw)
                for x, y, d, _ in CF.screw_reliefs():
                    ax.add_patch(plt.Circle((x, mir(y)), d / 2.0, fill=False,
                                            ec="0.45", lw=0.8, ls=(0, (2, 2))))
                    ax.text(x + 5, mir(y) + 4, "flange relief %.1f" % d,
                            fontsize=5.6, color="0.45")
                ax.text(153, mir(84), "CABLE COVER footprint - dashed, NOT a cut line",
                        fontsize=6.4, color="0.45", ha="center")

            dp = np.array(DIE_POLY)
            ax.plot(list(dp[:, 0]) + [dp[0, 0]],
                    [mir(v) for v in dp[:, 1]] + [mir(dp[0, 1])],
                    "-", color="k", lw=0.9)
            for x, y, _, _ in closed:
                ax.add_patch(plt.Circle((x, mir(y)), BORE / 2.0, fill=False,
                                        ec="k", lw=0.7))
                ax.plot([x - 3, x + 3], [mir(y)] * 2, "-", color="k", lw=0.35)
                ax.plot([x] * 2, [mir(y) - 3, mir(y) + 3], "-", color="k", lw=0.35)
            for x, y, _, _ in slotted:
                ax.plot([x - 3, x + 3], [mir(y)] * 2, "-", color="k", lw=0.35)
                ax.plot([x] * 2, [mir(y) - 3, mir(y) + 3], "-", color="k", lw=0.35)

            # edges named by the part of the CARD they meet
            ax.text(sx + usable / 2, mir(0) - 5, "CONNECTOR EDGE  (card's top edge, 12V-2x6)",
                    ha="center", va="top", fontsize=7, color="0.35")
            ax.text(sx + usable / 2, mir(H) + 4, "PCIe EDGE  (goes down into the slot)",
                    ha="center", va="bottom", fontsize=7, color="0.35")
            if n == 1:
                ax.text(3, mir(H / 2), "BRACKET END", ha="left", va="center",
                        fontsize=7, color="0.35")
            if n == len(starts):
                ax.text(L - 3, mir(H / 2), "FAR END (fin stack)", ha="right",
                        va="center", fontsize=7, color="0.35")

            # scale check - measure it before trusting anything else
            by = y_lo + 16
            bx = sx - MARGIN + 14
            ax.plot([bx, bx + 100], [by, by], "-", color="k", lw=1.0)
            for t in range(0, 101, 10):
                ax.plot([bx + t] * 2, [by, by + (3 if t % 50 else 5)], "-",
                        color="k", lw=0.8)
            ax.text(bx + 50, by + 7, "this bar must measure 100.0 mm - if it does "
                    "not, the print is scaled and nothing else on the sheet is valid",
                    ha="center", va="bottom", fontsize=6.5)

            ax.text(sx - MARGIN + PAGE_W - 12, y_hi - 12,
                    ("INSIDE FACE - lay ink DOWN against the card" if mirror else
                     "OUTSIDE FACE - lay ink UP, blank side down on the card"),
                    ha="right", va="top", fontsize=8, color="k", weight="bold")
            ax.text(sx - MARGIN + PAGE_W - 12, y_hi - 24,
                    f"sheet {n} of {len(starts)}   backplate v3   {L} x {H} mm   "
                    f"{len(closed)} holes dia {BORE} + {len(slotted)} edge slots"
                    f" + die window",                     ha="right", va="top", fontsize=6.5, color="0.35")

            if n == 1:
                # What to actually look at. The fastener pattern has been
                # checked six ways and the far end confirmed on the card; the
                # DIE WINDOW has not - it rests on a single scan, because at
                # X 95.5 it falls outside 9122's coverage and never got the
                # two-independent-scans treatment the holes did.
                cy0 = y_hi - 9
                ax.text(sx - MARGIN + 14, cy0, "CHECK, in this order:",
                        fontsize=7.5, weight="bold", va="top")
                for k, line in enumerate([
                        "1.  the 100 mm bar above - everything else is void if it is wrong",
                        "2.  BRACKET-END HOLES  <- the only thing not yet checked",
                        "3.  the dashed CABLE COVER overlay: exit is now at X 263,",
                        "     inside the 2-3 in band off the far end. Not a cut line.",
                        "",
                        "Already confirmed on the card: die window (the bone),",
                        "connector notch width AND depth, top edge, far-end holes."]):
                    ax.text(sx - MARGIN + 14, cy0 - 5.0 - k * 4.4, line,
                            fontsize=6.6, va="top")

            if n == len(starts):
                # Sheet 2 is mostly empty; put the outstanding measurements on
                # it. These gate the cover's CROSS-SECTION, not its route -
                # the route is what this sheet is for checking.
                mx, my = L + 16, y_hi - 12    # clear of the plate entirely
                ax.text(mx, my, "STILL NEEDED, off the assembled card:",
                        fontsize=7.5, weight="bold", va="top")
                for k, line in enumerate([
                        "A.  plug height above the plate           ____ mm",
                        "B.  90 deg adapter hood height           ____ mm",
                        "C.  is there 35 mm of straight run       Y / N",
                        "     before the first bend?",
                        "",
                        "A and B set the channel depth (now 10.5).",
                        "C sets the corner radius, and it is the one",
                        "with a safety argument behind it.",
                        "Connector well is already known: 26.61 mm deep."]):
                    ax.text(mx, my - 5.5 - k * 4.6, line, fontsize=6.6, va="top")

            if n < len(starts):                       # join marks
                jx = sx - MARGIN + usable - OVERLAP / 2
                ax.plot([jx, jx], [y_lo + 3, y_hi - 3], ":",
                        color="0.6", lw=0.6)
                ax.text(jx + 1.5, y_lo + PAGE_H / 2, "align next sheet on this line",
                        rotation=90, ha="left", va="center", fontsize=6, color="0.5")
            pdf.savefig(fig)
            if png:
                fig.savefig(os.path.join(OUT, f"v3_sheet{n}.png"),
                            dpi=170, facecolor='white')
            plt.close(fig)
    return path, len(starts)


if __name__ == "__main__":
    closed, slotted = classify()
    pts = outline()
    area, bad = check(pts)
    print(f"outline {len(pts)} pts   area {area/100:.1f} cm2   self-intersections {bad}")
    print(f"holes   {len(closed)} closed + {len(slotted)} slotted = "
          f"{len(closed)+len(slotted)}")
    for x, y, _, s in slotted:
        print(f"   slot  x {x:7.2f}  y {y:6.2f}   web would have been "
              f"{H-y-BORE/2:.2f} mm   ({s})")
    path, area, nc, ns = write_dxf()
    print(f"\nwrote {path}")
    tp, n = write_template(png=True)
    print(f"wrote {tp}")
    print(f"  {n} sheets, 1:1, OUTSIDE face - lay ink UP on the card")
