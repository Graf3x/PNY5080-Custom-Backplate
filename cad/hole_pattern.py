"""The 13 backplate fastener holes, in plate coordinates.

This is the end of the chain that began with the flatbed scans. Every position
here traces back to a centre the user measured by hand on a 4x crop, not to a
detector output - the detector only supplies which candidate is which.

FRAME
    X   along the plate, 0 at the BRACKET end, +ve toward the far end
    Y   across the plate, 0 at the long edge that lay FREE (against paper)
        in scan 9128

    RESOLVED 2026-08-22. Y = 0 is the CONNECTOR edge - the card's top edge,
    where the 12V-2x6 plugs in. That edge carries a 28.6 x 27.4 mm indentation
    matching the 27.7 x 26.5 mm connector-well relief in config, itself
    confirmed with a depth rod from the card's top edge; its centre lands at
    X 153.07 against the 152.7 already in backplate_v2_dxf. Confirmed against
    the physical part by the user.

WHICH FACE - read this before plotting anything
-----------------------------------------------
The numbers below carry NO handedness. Each is a distance from a NAMED
physical feature (bracket end, connector edge), so no mirror can change which
edge a hole belongs to. Chirality enters only when you choose how to lay the
two axes on a page, and that is where it has gone wrong before.

    X right, Y UP    (standard CAD, and what a DXF does)  -> OUTSIDE face
    X right, Y DOWN  (SVG/screen coordinates)             -> INSIDE face

Verified, not assumed. Take three points - the bracket+connector corner, one
100 mm along the connector edge, one 100 mm along the bracket end - and compare
the sign of the cross product against scan 9128, which is a direct view of the
OUTSIDE face (a flatbed images the face pressed to its glass, un-mirrored).
Y-up preserves the sign, Y-down reverses it.

Consequences:
  * The DXF, drawn Y-up, depicts the OUTSIDE face. Its existing note already
    says so.
  * A 1:1 paper template drawn in screen coordinates shows the INSIDE face,
    so it must be laid on the card INK DOWN, printing against the card. Ink
    up puts the pattern on backwards.
  * The plate is flat, with only through features and no countersinks, so a
    mirrored part is still usable - you turn it over. Handedness stops being
    recoverable the moment a bend is added.

HOW IT WAS BUILT
    9128 (bracket end) contributes 11 holes, 9122 (far end) 5, and 3 are seen
    in both, giving 13 - the count the user verified by hand on the part.

    The two scans rest against the jig on OPPOSITE long edges: the plate is
    not square, so turning it 90 deg into the same corner presents a different
    edge. 9122 is therefore folded over as (L - x, W - y).

    Along-plate datums differ in quality. 9122's far end sits against paper
    and is a clean edge. 9128's bracket end sits against the rule, but the
    cross-scan fit returns L = 326.30 against a 326.3 +-1.5 rule reading, so
    that rule is butted flush and needs no offset.

CONFIDENCE
    Three holes appear in both scans and agree to 0.02 / 0.27 / 0.34 mm in X
    and 0.03 / 0.22 / 0.40 mm in Y.
    The across-plate columns are tight: 31.90-32.02 (n=4, 0.12 mm spread),
    119.20-119.33 (n=3, 0.13 mm) and 4.62-4.80 (n=3, 0.18 mm). The last of
    those only appeared after 9128 #2 was re-measured on 2026-08-22 - see
    hole_truth.py. The hole at X 313.63, Y 7.68 sits 3.0 mm off that line and
    is NOT part of it: it is past the end of the PCB and fastens to the cooler,
    which the user confirmed independently.
    Nearest hole to each end comes out (6.62, 12.67), against the (12.29,
    6.62) already in config.PLATE_END_INSET from separate measurements.

    That is four independent checks, none of which was used to build the
    pattern. See hole_truth.py for the numbering anchor, and note the warning
    there about 3-inlier fits.

PHYSICAL TEST FIT  2026-08-22
    First 1:1 print laid on the card. At the FAR end the printed bore falls
    inside the stock hole - the best fit achieved so far, after five earlier
    attempts drifted. That is the end the data predicted would be best: 9122's
    along-datum is the far-end edge against PAPER, the only clean end datum in
    the scan set, where 9128's bracket end is referenced to a rule seam.

    The BRACKET END needs no feature: the I/O bracket fastens to the case
    below the backplate's plane and never touches it (photos, 2026-08-23).

    So the seam was checked for an offset, using the three holes both scans
    see. Signed differences -0.27 / -0.02 / +0.34 mm, mean +0.02. Mixed signs,
    so the bracket-end rule is BUTTED, not overlapping - unlike the long-edge
    rule, which overlaps by ~0.5 mm and is why PLATE_H needed correcting. Both
    end datums are therefore sound and no along-plate offset is warranted.
"""

PLATE_W = 122.40      # config.SCANNED.PLATE_H
PLATE_L = 326.30      # true measured length; config.PLATE_L is biased short

#   X       Y      type   provenance
HOLES = [
    (  6.62,  31.90, 2, "9128#5"),
    ( 15.84, 119.20, 2, "9128#10"),
    ( 17.71,   4.64, 1, "9128#1"),
    ( 54.60, 119.25, 2, "9128#11"),
    ( 55.84,  31.97, 1, "9128#6"),
    ( 99.59,   4.80, 1, "9128#2"),
    (120.69, 119.33, 2, "9128#12"),
    (120.91,  31.96, 1, "9128#7"),
    (162.51, 116.12, 2, "9128#13 + 9122#8"),
    (171.28,  32.02, 1, "9122#7 + 9128#8"),
    (209.91,   4.62, 1, "9122#5 + 9128#3"),
    (313.54, 113.72, 1, "9122#3"),
    (313.63,   7.68, 1, "9122#1"),
]

# Hole style, as identified on the physical part. Type 1 is recessed, type 2
# has a collar. They bias the detector differently in X (see hole_truth.py);
# for the cut file both are simply clearance holes.
BORE_DIA = 3.39       # stock; we cut config.HARDWARE.SCREW_CLEAR_DIA

if __name__ == "__main__":
    xs = [h[0] for h in HOLES]; ys = [h[1] for h in HOLES]
    print(f"{len(HOLES)} holes")
    print(f"  X {min(xs):7.2f} - {max(xs):7.2f}   inset from ends "
          f"{min(xs):.2f} / {PLATE_L - max(xs):.2f}")
    print(f"  Y {min(ys):7.2f} - {max(ys):7.2f}   inset from edges "
          f"{min(ys):.2f} / {PLATE_W - max(ys):.2f}")
    for tol in (2.0,):
        cols = []
        for y in sorted(ys):
            if not cols or y - cols[-1][-1] > tol: cols.append([y])
            else: cols[-1].append(y)
        print(f"  {len(cols)} across-plate columns:")
        for c in cols:
            print(f"     {sum(c)/len(c):7.2f} mm   n={len(c)}   spread {max(c)-min(c):.2f}")
