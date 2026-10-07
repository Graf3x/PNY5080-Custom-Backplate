"""Which of the 150 files in out/ belong to this design, and which do not.

WHY. out/ has accumulated 150 files across the life of this project - three
superseded architectures, abandoned vent studies, one-off previews, two
backplate templates from before the die window was traced. Eight of them come
from the current build. Everything else is exploration that happens to still
be sitting there with a plausible name: backplate_v3_TEMPLATE_1to1_INK-UP.pdf
and backplate_TEST_TEMPLATE_MIRRORED.pdf both read like the thing you would
print, and neither is.

A builder printing "the template" has a one-in-nine chance of printing the
right one by name alone. So the build writes down what it made.

The ribbon_90_* pair is deliberately kept and deliberately listed as
SUPERSEDED: it documents the 90-degree cleated variant this design replaced,
and the reasoning in it is still worth having. It is not what gets built.
"""

from __future__ import annotations

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")

# what the current build makes, and what each is for
CURRENT = [
    ("production/upload/", "THE ORDER. Seven DXFs, the order sheet, and the "
                           "stop notice while it stands. This folder is what "
                           "goes to the vendor."),
    ("production/", "The same seven parts as annotated drawings, for reading. "
                    "Their notes sit outside the part, so they are not the "
                    "files to upload."),
    ("templates_channel.pdf", "1:1, 3 sheets: the two skins with their folds "
                              "and tabs, the plan, and the carcass blank. "
                              "Print at 100% and check the scale bar."),
    ("templates_backplate.pdf", "1:1, tiled: the backplate with every opening, "
                                "read from the cut file."),
    ("harness_flush.pdf", "1:1 card mock-up of the FLUSH facade - the one "
                          "ordered - carcass, both skins, and the plan to lay "
                          "the folded result on."),
    ("harness_tall.pdf", "the same for the TALL facade, which is NOT in the "
                         "order. Kept so the choice can be revisited."),
    ("ribbon_45_views.png", "plan, both elevations and the section of the "
                            "design as built."),
    ("ribbon_45_fasteners.png", "the same, with the hardware called out."),
    ("render/", "exported solids and the assembled GLB, for looking at."),
]

SUPERSEDED_NOTE = [
    ("ribbon_90_views.png", "the 90-degree CLEATED variant this design "
                            "replaced. Kept for its reasoning; not built."),
    ("ribbon_90_fasteners.png", "ditto."),
]


def report():
    L = []
    L.append("WHAT IN out/ BELONGS TO THIS DESIGN")
    L.append("")
    L.append("Written by cad/make_manifest.py at build time. Everything in")
    L.append("out/ that is NOT listed below is superseded exploration - three")
    L.append("earlier architectures, abandoned vent studies, one-off previews.")
    L.append("Several of them have names that read like the real thing.")
    L.append("")
    L.append("CURRENT")
    for name, why in CURRENT:
        p = os.path.join(OUT, name.rstrip("/"))
        stamp = (time.strftime("%Y-%m-%d %H:%M",
                               time.localtime(os.path.getmtime(p)))
                 if os.path.exists(p) else "MISSING")
        L.append("  %-28s %s" % (name, stamp))
        L.append("      %s" % why)
    L.append("")
    L.append("KEPT BUT SUPERSEDED")
    for name, why in SUPERSEDED_NOTE:
        L.append("  %-28s %s" % (name, why))
    L.append("")
    known = {n.rstrip("/") for n, _ in CURRENT + SUPERSEDED_NOTE}
    others = sorted(f for f in os.listdir(OUT)
                    if f not in known and not f.startswith("."))
    L.append("EVERYTHING ELSE IN out/ (%d entries) IS SUPERSEDED." % len(others))
    L.append("  Do not print, cut or measure from any of it. The ones most")
    L.append("  likely to be mistaken for current work:")
    for f in others:
        if "TEMPLATE" in f.upper() or "1to1" in f:
            L.append("     %s" % f)
    return "\n".join(L)


if __name__ == "__main__":
    txt = report()
    p = os.path.join(OUT, "WHAT_IS_CURRENT.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(txt + "\n")
    print(txt)
    print("\nwrote %s" % p)
