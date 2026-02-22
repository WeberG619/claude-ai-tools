#!/usr/bin/env python3
"""
Scan each wall gap to find door arc hinge points by sampling pixel darkness
along radial patterns. For each candidate hinge point at a wall gap edge,
sweep a radius and count dark pixels. The correct hinge point + radius
combination will have the most dark pixels along a quarter-circle arc.
"""
import cv2
import numpy as np
import math

IMG = '/mnt/d/_CLAUDE-TOOLS/fp_example4.png'
gray = cv2.imread(IMG, cv2.IMREAD_GRAYSCALE)
h, w = gray.shape

# Threshold for "dark pixel" (wall/door lines)
DARK_THRESH = 160  # pixels below this are considered dark

debug = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

# For each door, define:
#   - wall gap endpoints (where the wall gap is)
#   - possible hinge sides (which end of the gap is the hinge)
#   - search range for hinge position refinement
#   - expected swing direction (which quadrant the arc is in)

doors = [
    {
        "name": "Entry",
        "gap_wall": "H",       # horizontal wall
        "gap_y": 388,          # y of wall centerline
        "gap_x1": 300, "gap_x2": 382,  # x range of gap
        "hinge_side": "left",  # hinge is on the left end of gap
        "sweep_quadrant": "NE",  # arc swings northeast (0 to 90 in DXF)
        "radius_range": (22, 38),
    },
    {
        "name": "Kitchen",
        "gap_wall": "V",
        "gap_x": 261,
        "gap_y1": 282, "gap_y2": 320,
        "hinge_side": "top",   # hinge at top of gap (lower y value)
        "sweep_quadrant": "SW",  # 180-270 in DXF → image: west+up
        "radius_range": (20, 34),
    },
    {
        "name": "Terrace",
        "gap_wall": "V",
        "gap_x": 261,
        "gap_y1": 160, "gap_y2": 248,
        "hinge_side": "top",
        "sweep_quadrant": "SW",
        "radius_range": (22, 38),
    },
    {
        "name": "LR",
        "gap_wall": "V",
        "gap_x": 375,
        "gap_y1": 255, "gap_y2": 310,
        "hinge_side": "top",
        "sweep_quadrant": "SE",  # 270-360 in DXF → image: east+up
        "radius_range": (22, 36),
    },
    {
        "name": "BR1",
        "gap_wall": "H",
        "gap_y": 158,
        "gap_x1": 182, "gap_x2": 250,
        "hinge_side": "right",
        "sweep_quadrant": "NW",  # 90-180 in DXF → image: west+down? No.
        # DXF 90-180 = north to west. In image (Y-flip): up to west = up-left
        "radius_range": (20, 32),
    },
    {
        "name": "BR2",
        "gap_wall": "V",
        "gap_x": 375,
        "gap_y1": 118, "gap_y2": 152,
        "hinge_side": "top",
        "sweep_quadrant": "NE",  # 0-90 in DXF
        "radius_range": (20, 34),
    },
    {
        "name": "Bath",
        "gap_wall": "H",
        "gap_y": 158,
        "gap_x1": 338, "gap_x2": 370,
        "hinge_side": "right",
        "sweep_quadrant": "NW",  # 90-180 in DXF
        "radius_range": (18, 30),
    },
]

def count_arc_pixels(img, hx, hy, radius, quadrant, n_samples=60):
    """Count dark pixels along a quarter-circle arc."""
    # Map quadrant to angle range (image coords, Y increases downward)
    angle_ranges = {
        "NE": (270, 360),  # right and up in image = DXF 0-90
        "NW": (180, 270),  # left and up in image = DXF 90-180
        "SW": (90, 180),   # left and down in image = DXF 180-270
        "SE": (0, 90),     # right and down in image = DXF 270-360
    }
    a1, a2 = angle_ranges[quadrant]

    count = 0
    total = 0
    for i in range(n_samples):
        angle_deg = a1 + (a2 - a1) * i / n_samples
        angle_rad = math.radians(angle_deg)
        px = int(hx + radius * math.cos(angle_rad))
        py = int(hy + radius * math.sin(angle_rad))

        if 0 <= px < img.shape[1] and 0 <= py < img.shape[0]:
            total += 1
            # Check a small neighborhood for dark pixels
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = px+dx, py+dy
                    if 0 <= nx < img.shape[1] and 0 <= ny < img.shape[0]:
                        if img[ny, nx] < DARK_THRESH:
                            count += 1
                            break
                else:
                    continue
                break

    return count, total

print("=" * 70)
print("DOOR ARC SCANNING")
print("=" * 70)

results = []

for door in doors:
    name = door["name"]
    rmin, rmax = door["radius_range"]
    quadrant = door["sweep_quadrant"]

    # Determine hinge search range
    if door["gap_wall"] == "H":
        gap_y = door["gap_y"]
        if door["hinge_side"] == "left":
            hinge_x_range = range(door["gap_x1"] - 5, door["gap_x1"] + 15)
            hinge_y_range = [gap_y - 1, gap_y, gap_y + 1]
        else:  # right
            hinge_x_range = range(door["gap_x2"] - 15, door["gap_x2"] + 5)
            hinge_y_range = [gap_y - 1, gap_y, gap_y + 1]
    else:  # V wall
        gap_x = door["gap_x"]
        if door["hinge_side"] == "top":
            hinge_x_range = [gap_x - 1, gap_x, gap_x + 1]
            hinge_y_range = range(door["gap_y1"] - 5, door["gap_y1"] + 15)
        else:  # bottom
            hinge_x_range = [gap_x - 1, gap_x, gap_x + 1]
            hinge_y_range = range(door["gap_y2"] - 15, door["gap_y2"] + 5)

    best_count = 0
    best_params = None

    for hx in hinge_x_range:
        for hy in hinge_y_range:
            for r in range(rmin, rmax + 1, 1):
                cnt, tot = count_arc_pixels(gray, hx, hy, r, quadrant)
                if cnt > best_count:
                    best_count = cnt
                    best_params = (hx, hy, r, cnt, tot)

    if best_params:
        hx, hy, r, cnt, tot = best_params
        pct = cnt / tot * 100 if tot > 0 else 0
        print(f"\n{name}: hinge=({hx},{hy}), radius={r}px, "
              f"arc_dark={cnt}/{tot} ({pct:.0f}%), quadrant={quadrant}")
        results.append((name, hx, hy, r, quadrant))

        # Draw the found arc on debug image
        angle_ranges = {
            "NE": (270, 360), "NW": (180, 270),
            "SW": (90, 180), "SE": (0, 90),
        }
        a1, a2 = angle_ranges[quadrant]
        cv2.ellipse(debug, (hx, hy), (r, r), 0, a1, a2, (0, 255, 0), 2)
        cv2.circle(debug, (hx, hy), 3, (0, 0, 255), -1)
        cv2.putText(debug, f"{name} r={r}", (hx-15, hy-r-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)

        # Also draw the door leaf line
        # Leaf is at the starting angle of the DXF arc
        dxf_angles = {
            "NE": 0, "NW": 90, "SW": 180, "SE": 270,
        }
        leaf_dxf = dxf_angles[quadrant]
        leaf_rad = math.radians(leaf_dxf)
        lx = int(hx + r * math.cos(leaf_rad))
        ly = int(hy - r * math.sin(leaf_rad))  # Y-flip for image
        cv2.line(debug, (hx, hy), (lx, ly), (0, 255, 0), 2)
    else:
        print(f"\n{name}: NO ARC FOUND")

# Print summary in the format needed for trace_floorplan.py
print("\n" + "=" * 70)
print("VISUAL_DOORS for trace_floorplan.py:")
print("=" * 70)

dxf_angle_map = {
    "NE": (0, 90),
    "NW": (90, 180),
    "SW": (180, 270),
    "SE": (270, 360),
}

for name, hx, hy, r, quad in results:
    sa, ea = dxf_angle_map[quad]
    print(f"    ({hx}, {hy}, {r}, {sa}, {ea}),  # {name}")

cv2.imwrite('/mnt/d/_CLAUDE-TOOLS/fp_arc_scan.png', debug)
print("\nSaved: fp_arc_scan.png")
