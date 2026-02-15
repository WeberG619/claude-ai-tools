#!/usr/bin/env python3
"""
Precisely detect door arc positions from the floor plan image.
For each known wall gap, crop that region, find the arc contour,
and fit a circle to determine exact hinge point, radius, and angles.
"""
import cv2
import numpy as np
import math

IMG = '/mnt/d/_CLAUDE-TOOLS/fp_example4.png'
gray = cv2.imread(IMG, cv2.IMREAD_GRAYSCALE)
h, w = gray.shape

# Binary threshold
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# Create thick mask (walls only) to subtract
binary_clean = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((3,3), np.uint8))
ek = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
eroded = cv2.erode(binary_clean, ek, iterations=2)
thick = cv2.dilate(eroded, ek, iterations=2)

# Thin mask = features only (doors, windows, fixtures, text)
thin = cv2.subtract(binary_clean, thick)

# Known wall gaps (from careful analysis)
# Each: (name, gap_region_x1, gap_region_y1, gap_region_x2, gap_region_y2,
#         wall_orientation, wall_side)
# We search a region around each gap for arc-shaped contours
gaps = [
    ("Entry",   280, 350, 400, 395, "H", "bottom"),  # bottom wall entry
    ("Kitchen", 220, 270, 270, 330, "V", "left"),     # V-wall-1 kitchen gap
    ("Terrace", 220, 155, 270, 255, "V", "left"),     # V-wall-1 terrace gap
    ("LR",      360, 260, 400, 310, "V", "right"),    # V-wall-2 LR gap
    ("BR1",     180, 120, 260, 170, "H", "top"),      # H-wall-BR BR1 gap
    ("BR2",     360, 110, 400, 165, "V", "right"),    # V-wall-2 BR2 gap
    ("Bath",    330, 120, 380, 170, "H", "top"),      # H-wall-BR bath gap
]

debug = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

print("=" * 70)
print("PRECISE DOOR ARC DETECTION")
print("=" * 70)

for name, x1, y1, x2, y2, orient, side in gaps:
    # Expand search region by door radius (~35px)
    pad = 40
    rx1 = max(0, x1 - pad)
    ry1 = max(0, y1 - pad)
    rx2 = min(w, x2 + pad)
    ry2 = min(h, y2 + pad)

    # Extract the region from thin mask (no walls, just features)
    region_thin = thin[ry1:ry2, rx1:rx2].copy()
    region_bin = binary_clean[ry1:ry2, rx1:rx2].copy()

    # Also look at original binary (door arcs might be same thickness as walls)
    # Use the original binary but mask out the thick wall areas
    # Actually, let's look at both

    # Find contours in the thin region
    contours_thin, _ = cv2.findContours(region_thin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    # Also find in full binary region
    contours_bin, _ = cv2.findContours(region_bin, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

    print(f"\n--- {name} door (region {rx1},{ry1} to {rx2},{ry2}) ---")
    print(f"  Thin contours: {len(contours_thin)}, Binary contours: {len(contours_bin)}")

    best_arc = None
    best_score = 0

    # Try both contour sets
    for label, contours in [("thin", contours_thin), ("binary", contours_bin)]:
        for cnt in contours:
            area = cv2.contourArea(cnt)
            peri = cv2.arcLength(cnt, False)  # open arc

            if area < 30 or peri < 20:
                continue

            # Circularity check (arcs have moderate circularity)
            if peri > 0:
                circ = 4 * math.pi * area / (peri * peri)
            else:
                continue

            # Fit minimum enclosing circle
            if len(cnt) >= 5:
                (cx, cy), radius = cv2.minEnclosingCircle(cnt)
                cx_abs = cx + rx1
                cy_abs = cy + ry1

                # Door arcs should have radius 15-40px
                if radius < 12 or radius > 50:
                    continue

                # Check if this looks like an arc (not a full circle or blob)
                # Arc: perimeter should be roughly pi*r/2 to pi*r (quarter to half circle)
                expected_quarter = math.pi * radius / 2
                expected_half = math.pi * radius

                # Calculate how much of the circle the contour covers
                coverage = peri / (2 * math.pi * radius)

                # We want quarter-circle arcs (coverage ~0.25 +/- 0.15)
                if coverage < 0.10 or coverage > 0.60:
                    continue

                # Score: prefer arcs with coverage near 0.25 (quarter circle)
                # and with radius in the expected range
                score = 1.0 - abs(coverage - 0.28) * 3
                if 18 <= radius <= 35:
                    score += 0.5

                print(f"  [{label}] area={area:.0f} peri={peri:.0f} circ={circ:.3f} "
                      f"center=({cx_abs:.0f},{cy_abs:.0f}) r={radius:.1f} "
                      f"coverage={coverage:.2f} score={score:.2f}")

                if score > best_score:
                    best_score = score
                    best_arc = (cx_abs, cy_abs, radius, coverage, label)

    if best_arc:
        cx, cy, radius, coverage, src = best_arc
        print(f"  BEST: center=({cx:.0f},{cy:.0f}) r={radius:.1f} coverage={coverage:.2f} [{src}]")

        # Now determine hinge point and angles based on wall gap position
        # The hinge is where the door meets the wall at one end of the gap
        # The arc center (from minEnclosingCircle) approximates the hinge

        # Draw on debug image
        cv2.circle(debug, (int(cx), int(cy)), int(radius), (0, 255, 0), 1)
        cv2.circle(debug, (int(cx), int(cy)), 3, (0, 0, 255), -1)
        cv2.putText(debug, f"{name} r={radius:.0f}", (int(cx)-20, int(cy)-int(radius)-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 0), 1)
    else:
        print(f"  NO ARC FOUND")
        # Let's try a different approach - look for curved pixels
        # Use HoughCircles on the region
        region_gray = gray[ry1:ry2, rx1:rx2]
        circles = cv2.HoughCircles(region_gray, cv2.HOUGH_GRADIENT, 1, 20,
                                    param1=50, param2=15,
                                    minRadius=12, maxRadius=45)
        if circles is not None:
            for c in circles[0]:
                cx, cy, r = c
                cx_abs = cx + rx1
                cy_abs = cy + ry1
                print(f"  HoughCircle: center=({cx_abs:.0f},{cy_abs:.0f}) r={r:.0f}")
                cv2.circle(debug, (int(cx_abs), int(cy_abs)), int(r), (255, 0, 255), 1)

# Also do a global search for all arc-like contours
print("\n" + "=" * 70)
print("GLOBAL ARC SEARCH (thin mask)")
print("=" * 70)

all_contours, _ = cv2.findContours(thin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
arc_candidates = []

for cnt in all_contours:
    area = cv2.contourArea(cnt)
    peri = cv2.arcLength(cnt, False)

    if area < 50 or peri < 30:
        continue

    if len(cnt) < 5:
        continue

    (cx, cy), radius = cv2.minEnclosingCircle(cnt)

    if radius < 12 or radius > 45:
        continue

    coverage = peri / (2 * math.pi * radius)
    circ = 4 * math.pi * area / (peri * peri) if peri > 0 else 0

    # Quarter circle arcs
    if 0.15 <= coverage <= 0.45 and circ < 0.5:
        arc_candidates.append((cx, cy, radius, coverage, area, peri, circ))
        print(f"  ARC at ({cx:.0f},{cy:.0f}) r={radius:.1f} coverage={coverage:.2f} "
              f"area={area:.0f} circ={circ:.3f}")

        cv2.circle(debug, (int(cx), int(cy)), int(radius), (255, 255, 0), 1)
        cv2.circle(debug, (int(cx), int(cy)), 2, (0, 0, 255), -1)

print(f"\nTotal arc candidates: {len(arc_candidates)}")

# Try another approach: use the ORIGINAL image (not thin mask)
# Door arcs in floor plans are drawn as thin lines, similar to wall thickness
print("\n" + "=" * 70)
print("ORIGINAL BINARY ARC SEARCH")
print("=" * 70)

# Use edge detection on the original grayscale
edges = cv2.Canny(gray, 50, 150)

# Look for circles using Hough on edges
circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1.2, 25,
                            param1=80, param2=20,
                            minRadius=15, maxRadius=40)

if circles is not None:
    print(f"Found {len(circles[0])} circles via HoughCircles")
    for c in circles[0]:
        cx, cy, r = c
        # Filter to regions near wall gaps
        near_gap = False
        for gname, gx1, gy1, gx2, gy2, _, _ in gaps:
            if gx1-45 <= cx <= gx2+45 and gy1-45 <= cy <= gy2+45:
                near_gap = True
                print(f"  Circle at ({cx:.0f},{cy:.0f}) r={r:.0f} near {gname}")
                cv2.circle(debug, (int(cx), int(cy)), int(r), (0, 128, 255), 1)
                break
        if not near_gap and False:  # set to True to see all
            print(f"  Circle at ({cx:.0f},{cy:.0f}) r={r:.0f} (not near any gap)")
else:
    print("No circles found via HoughCircles")

cv2.imwrite('/mnt/d/_CLAUDE-TOOLS/fp_door_detection.png', debug)
print("\nSaved: fp_door_detection.png")
