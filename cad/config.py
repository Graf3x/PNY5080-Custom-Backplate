"""
Shared parameters for the PNY RTX 5080 custom backplate and cable cover.

The v94 parts are built from values MEASURED ON ONE CARD: a PNY RTX 5080 OC
Triple Fan (VCG508016TFXPB1-O, board PG147 SKU 45), from 300 dpi flatbed
scans of the stock backplate plus calipers. Those live in the SCANNED class
and in hole_pattern.py. The MEASURED class holds the early estimates the
project started from and is kept for reference.

If your card is not this exact board, measure it yourself and print the 1:1
paper templates (tools/print_templates.py) before you order any metal.

  plate stock ........... 2.0 mm 5052-H32, RAL 9003 white powder coat
  card fasteners ........ M2, 13 holes, 3.2 mm clearance + nylon washers
"""

import os

# --------------------------------------------------------------------------
# Manufacturing constraints
# --------------------------------------------------------------------------


class MFG:
    """SendCutSend design rules for 2 mm (0.080") 5052 aluminium."""

    THICKNESS = 2.0
    # SCS: minimum hole diameter >= material thickness
    MIN_HOLE_DIA = 2.0
    # SCS: minimum feature width / web between features >= material thickness
    MIN_FEATURE = 2.0
    # Powder coat adds ~0.06-0.12 mm per surface -> oversize fastener holes
    COAT_ALLOWANCE = 0.15
    # Bend relief if we add a lip later
    MIN_BEND_RADIUS = 2.0


class HARDWARE:
    SCREW = "M2 x 0.5"
    # CONFIRMED 2026-08-25 against the owner's full M2 set (4/6/8/10/12/16 mm
    # with nuts and washers). The first read rested on a single M2x5 pulled out
    # of a mixed box, which was suggestive rather than conclusive.
    # OPENED 2026-08-20, from 2.55 to 3.2, deliberately.
    #
    # The scan-derived fastener pattern agrees pass-to-pass to 0.30 mm mean
    # and 0.66 mm worst (see photos/EXTRACTION_LOG.md; the cause was never
    # established). A 2.55 mm hole on a 2 mm screw leaves 0.28 mm of radial
    # play, which that scatter would eat. 3.2 mm leaves 0.6 mm per side and
    # absorbs it with margin.
    #
    # This is not a workaround for sloppy data - the tight hole was never a
    # requirement of the part. The STOCK plate needs precision because its
    # drawn bosses locate the screws; a flat plate on separate standoffs does
    # not. Overall pattern SCALE still has to be right, and that comes from
    # the scanner calibration at 0.06%, not from per-hole position.
    # CONFIRMED M2 2026-08-22 by threading an M2x5 into the card's standoff -
    # it engaged cleanly and did not slip. An M3 would not start, though it
    # passes through the plate's hole freely, which is the giveaway that the
    # hole is far larger than the thread.
    #
    # The STOCK plate's hole measures 3.39 mm (user fitted a circle to the bore
    # on a 4x scan crop). On a 2 mm screw that is 0.70 mm of radial play - PNY
    # themselves are looser than the 3.2 mm chosen here, which settles the
    # earlier worry that 3.2 was excessive. Matching stock at 3.4 would be
    # equally defensible and gives more room for any residual pattern error.
    SCREW_CLEAR_DIA = 3.2
    STOCK_HOLE_DIA = 3.39

    # REQUIRED CONSEQUENCE: with a 3.2 mm hole and a 3.8 mm button head, only
    # 0.3 mm of head annulus bears on the plate. That will deform the hole
    # edge and can pull through. WASHERS ARE NOT OPTIONAL at this clearance.
    # An M2 flat washer (OD 5.0, ID 2.2) restores 0.9 mm of bearing.
    WASHER_OD = 5.0
    WASHER_ID = 2.2
    WASHER_T = 0.3
    WASHER_REQUIRED = True
    # LOW-PROFILE BUTTON HEAD, not countersunk. SendCutSend cannot countersink
    # below 0.125" (3.2 mm) on any material, so 2 mm stock rules it out
    # entirely. The 5070 Ti sibling mod used M2 x 0.5 x 8 mm button heads on
    # 2.4 mm spacers for exactly this reason.
    SCREW_HEAD_DIA = 3.8

    # STANDOFF ARCHITECTURE  -  settled 2026-08-24, kits ordered.
    #
    # M2 MALE-FEMALE nylon hex standoffs, from an assortment. The male end
    # threads into the card's boss; the plate lands on the standoff's shoulder;
    # the screw passes through the plate into the standoff's FEMALE end.
    #
    # Two things this buys, and the second is the important one:
    #   * each standoff is captive on the card, so the plate can be dropped on
    #     rather than juggling loose spacers against gravity;
    #   * SCREW LENGTH NO LONGER DEPENDS ON STANDOFF HEIGHT. The screw only
    #     spans washer + plate + engagement:
    #         0.5 washer + 2.0 plate + ~3.2 engagement = 5.7 mm under-head
    #     which is what the STOCK screws already are. The earlier
    #     SCREW_LEN_FOR(h) = 6.3 + h formula assumed a through-spacer and is
    #     SUPERSEDED - it does not apply to male-female.
    #
    # ONE HOLE IS NOW A CLEARANCE CONSTRAINT, NOT JUST A FLATNESS ONE.
    # Added 2026-08-28. The connector's top edge sits 14.29 mm above the PCB
    # face the plate lands on (rule, zero at the PCB top edge, read generously).
    # The channel has to clear the CONNECTOR at the entry, not the cable, so:
    #
    #     standoff >= H - plate - channel = 14.29 - 2.0 - 10.5 = 1.79 mm
    #
    # at the hole nearest the connector. Nominal 2.4 leaves 0.61 mm. Shim that
    # hole DOWN below 1.79 and the plug fouls the top of the channel - which is
    # a failure the flatness reasoning below would never catch, because it is
    # perfectly happy to shim a hole short. See cad/entry_height.py.
    #
    # HEIGHTS VARY PER HOLE. The stock plate's screw holes are dimpled to
    # different depths, because the card's bosses sit at different heights
    # (PCB, cooler frame, brackets) while the plate's face stays flat. That is
    # also why every stock screw is the same length: each dimple brings the
    # plate down to its own boss. So this needs one standoff height per hole,
    # not one for the part - fit from the assortment, shim with nylon washers
    # where a required height falls between kit steps.
    #
    # Shimming is structural, not cosmetic: torque a hole that is short and you
    # pull 2 mm aluminium down to meet the boss. Thirteen screws each pulling
    # to a different height is how a flat plate ends up bowed.
    #
    # The thermal pads are NOT affected - the PCB back is a plane and the
    # plate's face is flat, so that gap is uniform. Only the bosses vary.
    #
    # CAN WE DIMPLE THE PLATE INSTEAD, like stock?  No - checked 2026-08-24.
    # SendCutSend do offer dimple forming, and 5052-H32 at 0.080" is on their
    # supported list, but it is the wrong operation and our pattern fails it
    # twice over:
    #   * a dimple die makes a FLARED hole for stiffness, not a flat-bottomed
    #     boss that can seat on a mounting pad;
    #   * smallest dimple is 0.500" = 12.70 mm across; we would want 6-8 mm
    #     around a 3.2 mm bore;
    #   * min centre-to-edge 15.24 mm - 10 of our 13 holes are inside that,
    #     the tightest at 3.07 mm;
    #   * min centre-to-centre 30.48 mm - our tightest pair is 29.43 mm.
    # Standoffs are the answer and they do the job better here anyway, because
    # the depths vary and dimpling would need a different die per depth.
    WASHER_MATERIAL = "white nylon"     # not steel: it will not mark the
                                        # RAL 9003 gloss at 13 holes, and it
                                        # matches. OD/thickness TBC off the part.
    STANDOFF_H = 2.4
    # user-owned magnets (1 mm thick). Pockets are parametric - set to real
    # measured sizes before printing.
    MAGNET_ROUND_DIA = 6.0
    MAGNET_ROUND_H = 1.0
    MAGNET_RECT_L = 10.0
    MAGNET_RECT_W = 5.0
    MAGNET_RECT_H = 1.0
    # glue-in pocket clearance (per side) for FDM/SLS
    MAGNET_POCKET_CLEAR = 0.15
    # sink pockets slightly below flush so the mating face seats on plastic,
    # not on magnet-to-magnet steel (prevents chipping + scratching paint)
    MAGNET_RECESS = 0.20



# --------------------------------------------------------------------------
# SCAN-DERIVED  --  measured 2026-08-20 from 300 dpi flatbed scans
# --------------------------------------------------------------------------
# Pipeline: scan_calibration.py -> find_holes.py / trace_outline.py /
#           extract_features.py.  Provenance, and the things that did NOT
#           work, in photos/EXTRACTION_LOG.md.
#
# Scanner scale came from a rules-only scan and lands within 0.06% of nominal
# on both axes, fit residuals 0.34-0.39 px. Scan poses were confirmed against
# the user's own record of how each pass was laid down: all six outside-face
# passes matched to within 0.35 degrees, both handednesses.


class SCANNED:
    """Values taken off the scans, each with its spread and sample count.

    Anything not here is still an estimate in MEASURED below.
    """

    # ---- solid -----------------------------------------------------------
    # CORRECTED 2026-08-22:  121.78 -> 122.40
    #
    # The old figure is the distance from the free long edge to the plate/RULE
    # seam. All six outside scans have the steel rule along one long edge and
    # paper along the other, so all six share that systematic and agreed with
    # one another (121.25-122.49) while all reading slightly short. Agreement
    # across scans was mistaken for accuracy.
    #
    # The true width comes from cross-scan hole matching. 9128 (rot 0) and
    # 9122 (rot 90) rest against the jig on OPPOSITE long edges - the plate is
    # not square, so turning it 90 deg into the same corner presents a
    # different edge. For a hole seen in both scans,
    #     across_9128 + across_9122 = width
    # Of the 15 possible pair sums, seven fall in a 0.62 mm band centred on
    # 122.35 and the rest scatter well clear of it. A least-squares fit over
    # the same data returns 122.43. No fitting is needed to see the cluster.
    #
    # So the rule overlaps the plate edge by only ~0.5 mm - it is essentially
    # butted, and part of that 0.5 mm is edge-threshold bias rather than
    # overlap. The correction is real but small.
    #
    # Sanity: at 122.40 the nearest hole sits 3.07 mm from the seam-side edge
    # and 4.64 mm from the free edge, so no bore breaks an edge.
    #
    # DO NOT re-derive this from a 3-inlier (W, L) fit alone. An earlier pass
    # did exactly that, on a mis-mapped hole numbering, and produced 123.40 -
    # a full millimetre out. With 55 candidate pairs and a +-1.0 x +-1.5 mm
    # acceptance box, three inliers arise by chance in roughly 5% of boxes and
    # the search tries ~128,000 of them. Three inliers prove nothing. What
    # makes this value trustworthy is the pair-sum CLUSTER plus the column
    # scatter check below.
    PLATE_H = 122.40            # +-0.20   cross-scan hole registration
    PLATE_H_SEAM = 121.78       # superseded: free edge to plate/rule seam
    # Was estimated 120.0. Every vent and screw position references this.

    # Die window over the GPU. OUTSIDE face is the true through-dimension;
    # the inside reads ~1.0 mm larger, which is the draw chamfer seen from
    # its two sides, not a disagreement between scans.
    DIE_WIN_W = 74.54           # +-0.50, n=3
    DIE_WIN_H = 51.52           # +-0.43, n=3
    DIE_WIN_AREA = 2547.8       # mm2, +-17.2

    # Shape is NOT a rounded rectangle, and not a dogbone either - it was
    # called that early on from thumbnails and the profile says otherwise.
    # Measured across the long axis: 23.4 mm at the ends, 41.9 mm in the
    # middle. Narrow-ended and waisted-wide, filling 66% of its bounding box.
    # Ratio held at 1.74-1.82 over 10 scans in four orientations.
    DIE_WIN_END_W = 23.4
    DIE_WIN_MID_W = 41.9

    # Connector cut-out in the plate's top edge - PNY's own clearance around
    # the 12V-2x6, which beats connector width plus a guessed allowance.
    CONN_CUT_W = 24.24          # +-0.07, n=4    along the plate's length
    CONN_CUT_D = 9.83           # +-0.18, n=4    into the plate

    # ---- EZDIYFAB "180 degree" 12V-2x6 adapter -------------------------
    # MEASURED 2026-08-27 by the owner, calipers, photos in the transcript.
    # "180 degree" is the vendor's naming, not the cable's behaviour: it dumps
    # the cable straight into the channel, same as the 90 we designed around,
    # so the ROUTE is unaffected.
    #
    # RAW, as read off the display:
    ADAPTER_A = 30.18       # one PCB axis
    ADAPTER_B = 25.10       # the other PCB axis
    ADAPTER_T = 12.63       # thickness of the assembled adapter
    ADAPTER_D = 18.54       # 0.730 in - the display was switched to inches for
                            # this one. What it spans is not yet established.
    #
    # WHICH SIDE FOULS: THE BRACKET SIDE. Owner, 2026-08-27, with the part in
    # hand on the stock card - "the part that blocks the adapter on the stock
    # card is the backplate on the bracket side."
    #
    # That is the side NOTCH_EXTRA_BRACKET already opens, so the correction we
    # made months ago is right in direction, and it is enough on the numbers:
    #
    #   stock notch bracket edge   x 139.22
    #   ours                       x 135.22        4.0 mm further out
    #   worst case (30.18 is the along-card axis AND every bit of the 2.48 mm
    #   of excess sits bracket-side)               clears by 1.52 mm
    #   other case (25.10 along the card)          clears by 4.00 mm
    #
    # It also corrects a wrong call made before this observation. Assuming the
    # adapter was CENTRED on the connector, 30.18 would foul our notch by
    # 1.24 mm on the NON-bracket side, and that was flagged as a problem. The
    # fouling being bracket-side only means the adapter is NOT centred - it
    # sits offset toward the bracket - so the non-bracket edge was never in
    # contact and does not need to move. Nothing to change.
    #
    # STILL WORTH ONE READING before cutting: with the adapter plugged in, how
    # far does it reach past the STOCK notch's bracket edge? That number has to
    # be under 4.0 mm. Everything above says it is; it has not been measured.
    ADAPTER_FOULS_SIDE = "bracket"
    # 2026-09-02, from the owner: the 12.63 was measured PLUGGED IN, from the
    # PCB UP. The plate's outer face is 2.4 (standoff) + 2.0 (plate) = 4.4
    # above the PCB, so the adapter's top stands 8.23 above the plate face,
    # against a cover roof at 11.05: clears by 2.82. ESTIMATED from that
    # reading, not callipered against the plate.
    ADAPTER_TOP_ABOVE_PCB = 12.63
    ADAPTER_TOP_ABOVE_PLATE = 12.63 - 4.4          # 8.23
    # WHICH SIDE RUNS ALONG THE CARD - an estimate that two observations pin
    # down. The connector sits at 148.32 (against the stock notch's bracket
    # end, photo). An adapter centred on it with 30.18 along the card would
    # span 133.23..163.41 and could NOT have "just fit" the 135.22 edge on
    # the printed template; with 25.10 along it spans 135.77..160.87 and
    # clears that edge by 0.55 - "just fits" - and fouls the STOCK edge at
    # 139.22 by 3.45, which is the bracket-side foul the owner saw. Both
    # observations agree on 25.10 along. That is also how these adapters are
    # built: the socket is 18.2 along the card and the 180-degree turn wants
    # its length ACROSS it.
    # MEASURED 2026-09-02 by the owner, callipers, plugged in: 25.03 along
    # the card. The estimate above was right; this is the reading.
    ADAPTER_ALONG_CARD = 25.03

    # ---- thermal pads ----------------------------------------------------
    # THREE pads, confirmed by the user marking them up: two flanking the die
    # window and one strip beyond it. There is NO pad on the near side - an
    # earlier "four pads in a frame" reading was wrong.
    #
    # Positions are given in the DIE WINDOW's own frame, which sidesteps the
    # mirror question entirely: the window's long axis (74.5 mm) runs ACROSS
    # the plate, its short axis (51.5 mm) ALONG it, and both were fixed from
    # the outside-face scans. So no inside/outside mapping is needed.
    #
    #   along   +ve is toward the CHEVRON, i.e. the flow-through end
    #   across  +/- are the two long edges
    #
    #   (name, w, h, along, across, n_scans)
    # SIZES RE-MEASURED 2026-08-25 from IMG_9130 - a flatbed scan of the BARE
    # PCB back, pads peeled, imprints visible. That is a better source than
    # what the first figures came from: an imprint on bare board has a hard
    # edge, whereas a pad photographed on the plate merges into neighbouring
    # dark regions, which is exactly the failure the note below describes.
    #
    #   superseded          measured        under by
    #   strip  55.0 x 16.5  58.8 x 19.0     3.8 / 2.5
    #   side_a 15.0 x 25.0  18.0 x 31.0     3.0 / 6.0
    #   side_b 11.2 x 21.0  16.1 x 30.3     1.1 / 5.3
    #
    # Every pad is LARGER than modelled, mostly along the plate. Calibrated on
    # ACROSS (the well-determined axis, the two side pads 67.3 mm apart) and
    # cross-checked two ways: the strip lands at along +29.4 against a stored
    # +29.4, and the die centre falls where the geometry puts it.
    #
    # BOTH side pads take the LARGER of the two imprints. The scan cannot say
    # which imprint is side_a and which is side_b - the sign of ACROSS is not
    # fixed by it - and they differ by under 2 mm. A keep-out slightly too big
    # costs a little vent area; one too small cuts into a pad.
    #
    # POSITIONS ARE UNCHANGED. Only the sizes were re-derived. Read off a
    # gridded crop, so +-1.3 mm; PAD_KEEPOUT_EXTRA absorbs that.
    PADS_VS_DIE = [
        ("strip",  58.8, 19.0, +29.4, -1.0, 4),
        ("side_a", 18.0, 31.0,  -1.5, -33.3, 5),
        ("side_b", 18.0, 31.0,  -0.7, +34.0, 3),
    ]
    # ACROSS is the well-determined axis: +-0.4 mm across scans. ALONG is
    # looser (+-1.2 on the strip, +-2.6 on side_a). SIZES are the weak part -
    # side_a's height read anywhere from 24 to 42 mm because the pad merges
    # with neighbouring dark regions at this threshold. Treat the sizes as
    # approximate and pad the keep-out accordingly; the positions are sound.
    PAD_KEEPOUT_EXTRA = 4.0     # mm added around each pad, over MEASURED.PAD_MARGIN

    # A fourth blob shows up at along +25.9, across +37.5 in four scans
    # (~18.5 x 24.5). It sits in the corner between the strip and side_b. The
    # user marked only three pads, so this is treated as NOT a pad - most
    # likely a shadow or a step in the plate. Flagged rather than silently
    # dropped, because if it IS a pad, venting there would be a real error.
    PAD_UNKNOWN_BLOB = (18.5, 24.5, +25.9, +37.5)

    # ---- caliper, at the bench ------------------------------------------
    CARD_D = 59.80              # card width at the top edge, stock plate on
    PLATE_T_STOCK = 1.56
    SCREW_LEN_OVERALL = 6.9     # 6.81-6.99 across all backplate screws

    # ---- 12V-2x6 recess --------------------------------------------------
    # Depth from the card's TOP EDGE down to the connector's face.
    CONN_WELL_DEPTH = 26.61     # caliper depth rod, IMG_9096

    # Cut-out in the backplate's long edge around that well, from the scans.
    CONN_NOTCH_L = 27.7         # +-0.5, n=4   along the plate
    CONN_NOTCH_D = 26.5         # +-0.6, n=4   into the plate

    # Those two are INDEPENDENT measurements - one off a 300 dpi scan of the
    # bare plate, one off a depth rod on the reassembled card - and they agree
    # to 0.1 mm. So the backplate is relieved to exactly the full depth of the
    # connector recess, not merely notched around it.
    #
    # DECIDES THE WIREVIEW: the standard (non-wired) WireView Pro II's plug
    # protrudes only ~13 mm below its body (ref/wireview_pro2_NONwired_
    # drawing.pdf). At 26.6 mm of well it bottoms out with 13 mm still to go,
    # so it cannot seat regardless of side clearance. The WIRED edition is
    # required. Its GPU end is a straight plug, which is what puts the 35 mm
    # straight-run rule back in play - see the notes on the bent flange.

    # ---- measured but NOT yet trustworthy --------------------------------
    # Fastener pattern detects reliably per scan (7-13 holes, NCC 0.87-1.00,
    # visually verified, no false positives) but pass-to-pass agreement is
    # ~0.30 mm mean and 0.66 mm worst. The cause is not established: three
    # hypotheses were tested and all three rejected. The mitigation is to
    # open the clearance holes rather than chase precision this part does
    # not actually require.
    FASTENER_SPAN = (114.9, 307.4)
    FASTENER_SCATTER = 0.30

    # PLATE_L: the 312.0 estimate in MEASURED is WRONG, by roughly 13 mm.
    #
    # Two independent routes agree:
    #
    #   ~323 mm   rule laid along the installed plate, read off a photo
    #             (low-res, perspective - treat as corroboration, not proof)
    #
    #   326.3 mm  pattern span 307.4 + the two END insets, measured directly
    #             off the 90/270 degree scans where both short edges fall
    #             inside the frame: nearest hole is 12.29 mm from one end and
    #             6.62 mm from the other.
    #
    # The second route is the stronger one - it never reads a photo. And it
    # rules 312 OUT rather than merely disagreeing: 312 would require the two
    # insets to total 4.6 mm, and they measure 18.9 mm.
    #
    # RESOLVED 2026-08-21: no rule long enough is available (12 in = 305 mm
    # against a ~325 mm plate), so the scan-derived figure stands.
    #
    # Of the two routes, the inset one is the better and should not be blended
    # with the photo: 307.4 + 12.29 + 6.62 = 326.3, from the same sub-pixel
    # edge detection that put the die window at +-1.8 mm2. Its error is the
    # pattern-span registration, ~1 mm, not the +-3 I first assigned by
    # averaging in a hand-held photo reading. Photo agreement at ~323 is
    # corroboration; it is not evidence of equal weight.
    PLATE_L_MEASURED = 326.3
    PLATE_L_TOL = 1.5

    # ...but CUT IT SHORTER THAN MEASURED, deliberately.
    #
    # The two errors are not symmetric. Too long and the plate fouls the
    # shroud at the far end, which is unrecoverable without re-cutting. Too
    # short leaves a hairline gap at one end, which nobody will see because
    # the shroud overhangs there anyway. So bias into the safe direction
    # rather than centring on the estimate.
    PLATE_L = 324.0
    # CORROBORATED 2026-08-22. The cross-scan hole fit that corrected PLATE_H
    # solved LENGTH as a free parameter at the same time and returned 326.30,
    # against the 326.3 +-1.5 rule reading this value was derived from. That
    # is an independent route to the same number, so the 326.3 measurement
    # stands and the 2.3 mm short bias below is a deliberate choice, not an
    # accommodation of a doubtful figure. Keeping 324.0.
    PLATE_END_INSET = (12.29, 6.62)   # nearest hole to each end

    # VERIFY BEFORE ORDERING METAL, at zero cost: print the finished outline
    # at 1:1 on paper, lay it on the card, check the ends and every hole.
    # This catches PLATE_L, the fastener pattern's 0.3 mm scatter and any
    # datum mistake in one go, for the price of a sheet of paper. Do not skip
    # it - it is the only check that tests the whole chain against the part.

# --------------------------------------------------------------------------
# MEASURED — replace every value here after opening the card
#
# 2026-08-20: entries superseded by SCANNED above are marked OVERRIDDEN.
# They stay because other modules still import them.
# --------------------------------------------------------------------------


class MEASURED:
    """ESTIMATES. Verify against the physical card. Origin = bottom-left of the
    backplate, +X toward the far (flow-through) end, +Y toward the top edge."""

    VERIFIED = False  # flip to True once traced; scripts warn while False

    PLATE_L = 312.0      # STILL AN ESTIMATE - one rule reading settles it
    PLATE_H = 120.0      # OVERRIDDEN by SCANNED.PLATE_H = 122.40
    CORNER_R = 3.0

    # PCB occupies the bracket end; cooler fin stack runs past it. The
    # flow-through window lives beyond PCB_END_X.
    # ~178 mm measured off a scale-calibrated bare-board photo, corroborated by
    # Alphacool's block and backplate both being exactly 180.00 mm long. The
    # PCB is far shorter than the card - flow-through is ~44% of its length.
    PCB_END_X = 180.0

    # GPU die centre. Core mounting pattern measured at 41.5 x 64.5 mm
    # (a rectangle, not a square) centred ~79 mm along the PCB.
    GPU_CX = 80.0
    GPU_CY = 56.0

    # Backplate fastener pattern (x, y). Placeholder perimeter pattern.
    SCREWS = [
        (10.0, 12.0), (10.0, 108.0),
        (68.0, 8.0), (68.0, 112.0),
        (140.0, 8.0), (140.0, 112.0),
        (206.0, 8.0), (206.0, 112.0),
        (262.0, 10.0), (262.0, 110.0),
        (302.0, 24.0), (302.0, 96.0),
    ]

    # Backside thermal-pad keep-outs: (centre_x, centre_y, width, height)
    # from Alphacool's backplate pad kit for this PCB.
    # OVERRIDDEN IN PRINCIPLE. This map came from ALPHACOOL'S WATERBLOCK
    # BACKPLATE - a solid cooling plate, a different part. The stock PNY
    # plate is OPEN at the die and carries four pads in a frame around
    # that window, over memory and VRM. Sizes are measured now (see
    # SCANNED.PAD_SIZES); positions still need the mirror axis.
    # Do not lay out vents against this list.
    PAD_ZONES = [
        (GPU_CX, GPU_CY, 45.0, 45.0),          # K: behind the die
        (GPU_CX - 34.0, GPU_CY, 8.0, 55.0),    # I: strip left of GPU
        (GPU_CX, GPU_CY + 30.0, 26.0, 8.0),    # J1: above GPU
        (GPU_CX, GPU_CY - 30.0, 26.0, 8.0),    # J2: below GPU
        (40.0, 96.0, 20.0, 8.0),               # L: top-left VRM
    ]
    # breathing room around pads so a vent edge never undercuts a pad
    PAD_MARGIN = 3.0

    # Flow-through vent window (over bare fin stack, no PCB behind).
    # Split into a slot field (lower) and a logo panel (upper) so the two
    # never share a web - that is what keeps every feature >= 2 mm.
    VENT_X0 = 214.0
    VENT_X1 = 304.0
    VENT_Y0 = 10.0
    VENT_Y1 = 72.0

    LOGO_X0 = 216.0
    LOGO_X1 = 294.0
    LOGO_CY = 88.0

    # clear radius kept around every fastener: head + washer + margin
    SCREW_KEEPOUT_R = 5.5

    # Secondary vent band over the fin area between PCB end and window
    BAND_X0 = 148.0
    BAND_X1 = 202.0

    # 12V-2x6 connector (silkscreen J6), flush to the card's top edge.
    # Body spans ~145-163 mm along the PCB; 18.2 mm wide, which matches
    # 6 x 3.0 mm pitch plus walls - a good check that the photo scale is right.
    CONNECTOR_CX = 156.0   # still estimated
    CONNECTOR_W = 18.2     # bare connector body; for the opening PNY
                           # actually cut, see SCANNED.CONN_CUT_W

    # ---- cable channel --------------------------------------------------
    # Route of the 12V-2x6 across the BACKPLATE face, in plate coordinates
    # (x from the I/O end, y from the bottom edge):
    #   1. leaves the connector already turned 90 deg by the WireView pigtail
    #   2. runs STRAIGHT DOWN for 46 mm - no second bend anywhere near the
    #      connector, which is the whole point (>= 35 mm of straight cable out
    #      of a 12V-2x6 before anything bends it)
    #   3. CHAMFERED corner: two 45 deg turns rather than one 90. Gentler on
    #      the cable than a single hard turn, and it echoes the faceted
    #      language on the shroud
    #   4. horizontal toward the far end
    #   5. SECOND chamfered corner, then drops through the bottom edge and
    #      dumps out under the card
    #
    # The horizontal run sits at mid height, clear of BOTH the DIMM latches at
    # the card's bottom edge and the mirror cover's lip at the top. The drop is
    # at x=284, which is past the end of the motherboard (the card overhangs it
    # by ~50 mm+), so nothing is in the way down there - and it still keeps the
    # cover's full width on the plate rather than hanging off the end.
    # MEASURED BUNDLE, owner with calipers, 2026-08-28: 22.0 wide x 6.0 high,
    # called a rough estimate. This is the FIRST time the cable itself has been
    # measured in this project - CABLE_W and CABLE_D below have always been the
    # CHANNEL, and every note warning that they were not a measured cable can
    # now be retired.
    BUNDLE_W = 22.0
    BUNDLE_H = 6.0
    CABLE_W = 24.0           # internal channel width
    CABLE_D = 10.5           # internal channel depth
    CABLE_WALL = 2.5         # channel wall thickness
    CABLE_FLANGE = 9.0       # contact flange each side, BEYOND the wall
    CABLE_CHAMFER = 30.0     # cut-back along each leg -> two 45 deg turns
    CABLE_RUN_Y = 46.0       # height of the horizontal leg
    CABLE_TIE_X = [188.0, 240.0]   # zip-tie stations on the straight run
    # Vents through the cover's flanges, cut from the SAME arc field as the
    # plate so the pattern reads continuously across both parts and air still
    # moves through the strip the cover occupies.
    CABLE_VENT = True
    # Keep-out the plate's vent field must respect. Only the CHANNEL needs to
    # stay solid - the flanges sit over pattern deliberately, and the cover
    # carries matching vents so air still gets through.
    CABLE_CLEAR = 4.0
    # Centreline waypoints. MEASURED is used as a bare class elsewhere, so
    # these stay plain values rather than properties.
    CABLE_PATH = [(156.0, 124.0), (156.0, 46.0), (284.0, 46.0), (284.0, -14.0)]

    # ---- shroud (front face) -------------------------------------------
    # Shroud footprint 324 mm; the visible face is only ~120 mm tall, NOT the
    # 137.6 mm card height (that figure includes the bracket tabs).
    SHROUD_L = 324.0
    SHROUD_FACE_H = 120.0
    SHROUD_DEPTH = 24.0

    # Six stock shroud screws, exact coordinates lifted from the community
    # deshroud STL (every circle had zero radial spread, so these are modelled
    # values, not measurements off a photo). X from the I/O end of the plate.
    # Given here in FACE coordinates: x from the I/O end, y from the bottom of
    # a SHROUD_FACE_H-tall face. The STL gives the x values and the vertical
    # SPANS (104.5 mm for the first two pairs, 80 mm at the far end) exactly;
    # how those spans sit relative to the face centreline is the part still
    # worth checking against the real card.
    SHROUD_SCREWS = [
        (6.0, 8.0), (6.0, 112.0),
        (137.0, 112.0), (154.0, 8.0),
        (318.0, 20.0), (318.0, 100.0),
    ]
    SHROUD_SCREW_CLEAR = 1.8

    # 2 x 140 mm is the only geometrically viable swap: 3 x 120 needs 360 mm on
    # a 324 mm face and cannot fit. Centres are the equal-margin solution,
    # which is also exactly what the community bracket used.
    FAN140_CENTRES = [87.4, 241.4]
    FAN140_MOUNT_PITCH = 125.0
    FAN140_APERTURE = 133.0
    # Reusing the three stock 100 mm-frame fans keeps the face inside the
    # card's height and needs no adapter.
    FAN100_CENTRES = [67.0, 168.0, 269.0]
    FAN100_APERTURE = 96.0


# --------------------------------------------------------------------------
# Branding
# --------------------------------------------------------------------------


def find_font(filename):
    """Full path to an installed font file, or the bare name if none is found.

    Fonts are NOT shipped with this repo: Bahnschrift and Arial are Microsoft
    fonts and may not be redistributed. Set PNY5080_FONT to an explicit .ttf
    path to override the search, or put the file next to this script.
    """
    import glob
    import os
    explicit = os.environ.get("PNY5080_FONT")
    if explicit and os.path.basename(explicit).lower() == filename.lower():
        return explicit
    roots = [os.path.dirname(os.path.abspath(__file__)),
             os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"),
             "/Library/Fonts", "/System/Library/Fonts", os.path.expanduser("~/Library/Fonts"),
             os.path.expanduser("~/.fonts"), os.path.expanduser("~/.local/share/fonts"),
             "/usr/share/fonts", "/usr/local/share/fonts"]
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for hit in glob.glob(os.path.join(root, "**", "*"), recursive=True):
            if os.path.basename(hit).lower() == filename.lower():
                return hit
    return filename


class BRAND:
    # The wordmark cut through the vent field. Change it, then run
    # cad/vent_ocr.py and cad/gate_v94.py - see the README's "Customizing".
    TEXT = "Graf3X"
    # Bahnschrift is the face the v94 parts were cut in. The sweep below is
    # why: it is the one face and size that cuts clean in 2 mm aluminium AND
    # reads back correctly through the OCR check.
    FONT = os.environ.get("PNY5080_FONT") or find_font("bahnschrift.ttf")
    FONT_ALT = find_font("arialbd.ttf")
    CAP_HEIGHT = 24.0     # mm, on the backplate
    MAX_WIDTH = 72.0      # shrink to fit the logo panel if the font runs wide
    BRIDGE_W = 2.6        # material bridge holding letter islands (>= MIN_FEATURE)
    TRACKING = 3.2        # mm gap between glyphs (>= MIN_FEATURE, hand-set)
    STROKE_ADJUST = 0.0   # Bahnschrift needs none; use -0.6 if switching to Impact
    # FONT SWITCHED BACK TO BAHNSCHRIFT 2026-08-30. Arial Bold cannot be cut at
    # this size in 2 mm stock: it necks to 1.547 mm in the CUT and traps metal
    # islands on a 1.337 mm web, and the two pull opposite ways - thickening
    # the strokes opens the cut and closes the metal. Swept both fonts against
    # both minima plus the OCR margin:
    #
    #   arialbd   82   cut 1.750  metal 2.007  reads
    #   arialbd   90   cut 1.876  metal 2.203  reads
    #   arialbd   96   cut 1.892  metal 2.218  reads '3raf3X'
    #   bahnschr  82   cut 2.050  metal 2.170  weak X
    #   bahnschr  90   cut 2.094  metal 2.400  reads          <- all three
    #   bahnschr  96   cut 2.078  metal 2.400  reads '3raf3X'
    #
    # Something had once switched FONT to Arial Bold and nothing measured the
    # consequence. Measure before you trust a font change.


OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
