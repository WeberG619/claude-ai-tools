#!/usr/bin/env python3
"""Scan binary image around each wall gap to find door arcs precisely."""
import cv2
import numpy as np
import math

IMG = '/mnt/d/_CLAUDE-TOOLS/fp_example4.png'
gray = cv2.imread(IMG, cv2.IMREAD_GRAYSCALE)
h, w = gray.shape
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((3,3), np.uint8))

# Building bbox
closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((5,5), np.uint8))
contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
largest = max(contours, key=cv2.contourArea)
bx, by, bw, bh = cv2.boundingRect(largest)

# Thick mask
ek = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
eroded = cv2.erode(binary, ek, iterations=2)
thick = cv2.dilate(eroded, ek, iterations=2)

debug = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

# Wall positions (from analysis)
# Vertical walls: left ext=127-133, V1=259-264, V2=372-378, right ext=517-523
# Horizontal walls: top=12-18, h_bath=111-117, h_br=155-161, h_lr=186-192, bottom=387-393

print("=== DETAILED WALL GAP ANALYSIS ===")

def scan_vwall_gaps(name, wall_x1, wall_x2, y_start, y_end):
    """Scan a vertical wall for gaps and nearby door arcs."""
    print(f"\n--- {name} (x={wall_x1}-{wall_x2}, y={y_start}-{y_end}) ---")
    # Sum thick mask across wall width for each row
    col_sum = np.sum(thick[y_start:y_end, wall_x1:wall_x2+1] > 0, axis=1)

    gaps = []
    in_gap, gs = False, 0
    for r in range(len(col_sum)):
        if col_sum[r] < 2:
            if not in_gap: gs = r; in_gap = True
        else:
            if in_gap and r - gs > 5:
                gy1 = y_start + gs
                gy2 = y_start + r - 1
                gaps.append((gy1, gy2))
            in_gap = False
    if in_gap and len(col_sum) - gs > 5:
        gy1 = y_start + gs
        gy2 = y_start + len(col_sum) - 1
        gaps.append((gy1, gy2))

    for gy1, gy2 in gaps:
        span = gy2 - gy1
        print(f"  Gap: y={gy1}-{gy2} ({span}px)")

        # Search for door arc in binary on BOTH sides of the wall
        # West side (x < wall_x1)
        for side, label, x1, x2 in [
            ('W', 'west', max(0, wall_x1-50), wall_x1),
            ('E', 'east', wall_x2+1, min(w, wall_x2+51)),
        ]:
            roi = binary[max(0,gy1-10):min(h,gy2+10), x1:x2]
            # Remove thick wall pixels from search
            roi_thick = thick[max(0,gy1-10):min(h,gy2+10), x1:x2]
            roi_arcs = cv2.subtract(roi, roi_thick)

            # Find contours
            cnts, _ = cv2.findContours(roi_arcs, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in cnts:
                area = cv2.contourArea(cnt)
                if area < 10:
                    continue
                peri = cv2.arcLength(cnt, True)
                circ = 4*math.pi*area/(peri*peri) if peri > 0 else 0
                bx2, by2, cw, ch = cv2.boundingRect(cnt)
                # Translate back to image coords
                abs_x = x1 + bx2
                abs_y = max(0,gy1-10) + by2
                print(f"    {label}: area={area:.0f} circ={circ:.3f} bbox=({abs_x},{abs_y},{cw},{ch})")
                cv2.rectangle(debug, (abs_x, abs_y), (abs_x+cw, abs_y+ch), (0,255,0), 1)

def scan_hwall_gaps(name, wall_y1, wall_y2, x_start, x_end):
    """Scan a horizontal wall for gaps and nearby door arcs."""
    print(f"\n--- {name} (y={wall_y1}-{wall_y2}, x={x_start}-{x_end}) ---")
    row_sum = np.sum(thick[wall_y1:wall_y2+1, x_start:x_end] > 0, axis=0)

    gaps = []
    in_gap, gs = False, 0
    for c in range(len(row_sum)):
        if row_sum[c] < 2:
            if not in_gap: gs = c; in_gap = True
        else:
            if in_gap and c - gs > 5:
                gx1 = x_start + gs
                gx2 = x_start + c - 1
                gaps.append((gx1, gx2))
            in_gap = False
    if in_gap and len(row_sum) - gs > 5:
        gx1 = x_start + gs
        gx2 = x_start + len(row_sum) - 1
        gaps.append((gx1, gx2))

    for gx1, gx2 in gaps:
        span = gx2 - gx1
        print(f"  Gap: x={gx1}-{gx2} ({span}px)")

        # Search for door arc above and below the wall
        for side, label, y1, y2 in [
            ('N', 'above', max(0, wall_y1-50), wall_y1),
            ('S', 'below', wall_y2+1, min(h, wall_y2+51)),
        ]:
            roi = binary[y1:y2, max(0,gx1-10):min(w,gx2+10)]
            roi_thick = thick[y1:y2, max(0,gx1-10):min(w,gx2+10)]
            roi_arcs = cv2.subtract(roi, roi_thick)

            cnts, _ = cv2.findContours(roi_arcs, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in cnts:
                area = cv2.contourArea(cnt)
                if area < 10:
                    continue
                peri = cv2.arcLength(cnt, True)
                circ = 4*math.pi*area/(peri*peri) if peri > 0 else 0
                bx2, by2, cw, ch = cv2.boundingRect(cnt)
                abs_x = max(0,gx1-10) + bx2
                abs_y = y1 + by2
                print(f"    {label}: area={area:.0f} circ={circ:.3f} bbox=({abs_x},{abs_y},{cw},{ch})")
                cv2.rectangle(debug, (abs_x, abs_y), (abs_x+cw, abs_y+ch), (0,255,0), 1)

# === Bottom exterior wall - find it precisely ===
print("\n=== BOTTOM WALL LOCATION ===")
# The bottom wall should be near y=387-393 but might not show in projection
# Scan bottom 20 rows of building for wall presence
for r in range(bh-20, bh):
    row_sum = np.sum(thick[by+r, bx:bx+bw] > 0)
    if row_sum > 50:
        print(f"  row {by+r}: thick_sum={row_sum}")

# Also check binary
print("\nBottom binary presence:")
for r in range(bh-15, bh):
    row_sum = np.sum(binary[by+r, bx:bx+bw] > 0)
    if row_sum > 50:
        print(f"  row {by+r}: binary_sum={row_sum}")

# Find bottom wall gap (entry door)
print("\n=== BOTTOM WALL ENTRY DOOR ===")
# Check binary image at the very bottom of building
bot_y1, bot_y2 = by+bh-10, by+bh
bot_binary = binary[bot_y1:bot_y2, bx:bx+bw]
bot_thick = thick[bot_y1:bot_y2, bx:bx+bw]
bot_proj = np.sum(bot_binary > 0, axis=0)

# Find gaps in bottom wall
in_gap, gs = False, 0
for c in range(bw):
    if bot_proj[c] < 2:
        if not in_gap: gs = c; in_gap = True
    else:
        if in_gap and c - gs > 10:
            print(f"  Bottom wall gap: x={bx+gs}-{bx+c-1} ({c-gs}px)")
        in_gap = False

# Now search around each known gap for arcs
# Use the ORIGINAL BINARY (not thin mask) for better arc detection

# V-wall-1 runs from top to bottom, but has different segments
scan_vwall_gaps("V-wall-1 (full)", 259, 264, by, by+bh)
scan_vwall_gaps("V-wall-2 (full)", 372, 378, by, by+bh)

# Horizontal walls
scan_hwall_gaps("H-wall-bath (y=111-117)", 111, 117, bx, bx+bw)
scan_hwall_gaps("H-wall-BR (y=155-161)", 155, 161, bx, bx+bw)
scan_hwall_gaps("H-wall-LR (y=186-192)", 186, 192, bx, bx+bw)

# Bottom wall
scan_hwall_gaps("Bottom wall (y=386-393)", 386, 393, bx, bx+bw)

# === Check where door arcs are in the BINARY directly ===
print("\n=== DIRECT ARC SEARCH (binary minus thick, whole image) ===")
arcs_mask = cv2.subtract(binary, thick)
arcs_mask = cv2.morphologyEx(arcs_mask, cv2.MORPH_OPEN, np.ones((2,2), np.uint8))

# Find contours
arc_cnts, _ = cv2.findContours(arcs_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
arc_candidates = []
for cnt in arc_cnts:
    area = cv2.contourArea(cnt)
    if area < 15:
        continue
    peri = cv2.arcLength(cnt, True)
    if peri < 15:
        continue
    circ = 4*math.pi*area/(peri*peri)
    x, y, cw, ch = cv2.boundingRect(cnt)
    aspect = max(cw, ch) / max(min(cw, ch), 1)

    # Filter: must be in building area and have arc-like properties
    if x >= bx-5 and x+cw <= bx+bw+5 and y >= by-5 and y+ch <= by+bh+5:
        arc_candidates.append({
            'area': area, 'circ': circ, 'peri': peri,
            'bbox': (x, y, cw, ch), 'aspect': aspect,
            'center': (x+cw//2, y+ch//2)
        })

arc_candidates.sort(key=lambda a: -a['area'])
print(f"Total candidates: {len(arc_candidates)}")
for i, a in enumerate(arc_candidates[:40]):
    x, y, cw, ch = a['bbox']
    print(f"  #{i}: area={a['area']:.0f} circ={a['circ']:.3f} peri={a['peri']:.0f} "
          f"bbox=({x},{y},{cw},{ch}) asp={a['aspect']:.1f} center=({a['center'][0]},{a['center'][1]})")

cv2.imwrite('/mnt/d/_CLAUDE-TOOLS/fp_doors_v2_debug.png', debug)
print(f"\nDebug image saved")
