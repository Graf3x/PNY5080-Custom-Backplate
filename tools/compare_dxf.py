"""Compare the geometry of two sets of DXF cut files, ignoring the bytes.

ezdxf stamps fresh handles and timestamps on every save, so two builds of the
same part never match byte for byte. This compares what the laser and the
press brake actually see: every CUT, BEND and TAP entity, its layer and its
coordinates to a micron.

    python tools/compare_dxf.py out/production_v94/upload  path/to/other/upload
"""
import glob
import os
import sys

import ezdxf

ROUND = 6   # decimal places in mm: 1e-6 mm


def _r(v):
    return tuple(round(float(c), ROUND) + 0.0 for c in v)


def signature(path):
    """Sorted list of (layer, type, geometry) for every non-text entity."""
    out = []
    for e in ezdxf.readfile(path).modelspace():
        t = e.dxftype()
        if t in ("TEXT", "MTEXT"):
            continue
        layer = e.dxf.layer
        if t == "LWPOLYLINE":
            pts = [_r(p[:2]) for p in e.get_points("xy")]
            geo = (bool(e.closed), tuple(pts))
        elif t == "CIRCLE":
            geo = (_r(e.dxf.center)[:2], round(e.dxf.radius, ROUND))
        elif t == "LINE":
            geo = (_r(e.dxf.start)[:2], _r(e.dxf.end)[:2])
        elif t == "ARC":
            geo = (_r(e.dxf.center)[:2], round(e.dxf.radius, ROUND),
                   round(e.dxf.start_angle, ROUND), round(e.dxf.end_angle, ROUND))
        else:
            geo = ("unhandled", t)
        out.append((layer, t, geo))
    return sorted(out, key=repr)


def main(a_dir, b_dir):
    a_files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(a_dir, "*.dxf")))
    b_files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(b_dir, "*.dxf")))
    bad = 0
    if a_files != b_files:
        print("DIFFERENT FILE SETS\n  %s\n  %s" % (a_files, b_files))
        bad += 1
    for name in sorted(set(a_files) & set(b_files)):
        sa = signature(os.path.join(a_dir, name))
        sb = signature(os.path.join(b_dir, name))
        if sa == sb:
            print("  SAME       %-34s %d entities" % (name, len(sa)))
        else:
            bad += 1
            only_a = len(set(map(repr, sa)) - set(map(repr, sb)))
            only_b = len(set(map(repr, sb)) - set(map(repr, sa)))
            print("  DIFFERENT  %-34s %d vs %d entities, %d / %d unmatched"
                  % (name, len(sa), len(sb), only_a, only_b))
    print("\nALL GEOMETRY IDENTICAL" if not bad else "\n%d DIFFERENCE(S)" % bad)
    return bad


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1], sys.argv[2]) else 0)
