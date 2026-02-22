#!/usr/bin/env python3
"""Extract regions around expected door positions to find exact arc locations."""
import cv2
import numpy as np

IMG = '/mnt/d/_CLAUDE-TOOLS/fp_example4.png'
gray = cv2.imread(IMG, cv2.IMREAD_GRAYSCALE)
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# Building bbox
closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((5,5), np.uint8))
contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
largest = max(contours, key=cv2.contourArea)
bx, by, bw, bh = cv2.boundingRect(largest)
print(f"Building: ({bx},{by}) {bw}x{bh}")

# Use gentler erosion for thick mask to preserve more features
ek = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
eroded = cv2.erode(binary, ek, iterations=1)
thick_gentle = cv2.dilate(eroded, ek, iterations=1)

# Create output debug image with regions marked
debug = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

# Expected door regions (based on room layout analysis)
# Each: (name, x1, y1, x2, y2) in image coordinates
# I'll extract the binary and non-thick pixels in each region
regions = [
    # Entry door: bottom wall, foyer area (x=264 to x=372)
    ("ENTRY DOOR", 250, 350, 380, 395),
    # Kitchen door: V-wall-1 gap (x=259-264), lower portion
    ("KITCHEN DOOR", 210, 270, 270, 330),
    # Terrace door: V-wall-1 gap, middle section
    ("TERRACE DOOR", 210, 155, 270, 255),
    # LR door: V-wall-2 area (x=372-378), lower portion
    ("LR DOOR", 365, 270, 420, 340),
    # BR1 door: H-wall at y=155-161, left portion
    ("BR1 DOOR", 150, 105, 260, 170),
    # BR2 door: V-wall-2, upper portion
    ("BR2 DOOR", 365, 90, 420, 160),
    # Bath door: H-wall at y=155-161, center-right
    ("BATH DOOR", 280, 105, 375, 170),
]

for name, x1, y1, x2, y2 in regions:
    print(f"\n=== {name} (x={x1}-{x2}, y={y1}-{y2}) ===")

    # Extract binary region
    roi_bin = binary[y1:y2, x1:x2]
    roi_thick = thick_gentle[y1:y2, x1:x2]
    roi_thin = cv2.subtract(roi_bin, roi_thick)

    bin_count = np.sum(roi_bin > 0)
    thick_count = np.sum(roi_thick > 0)
    thin_count = np.sum(roi_thin > 0)

    print(f"  Binary pixels: {bin_count}, Thick: {thick_count}, Thin (arcs/etc): {thin_count}")

    # Find contours in thin region
    cnts, _ = cv2.findContours(roi_thin.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    thin_features = []
    for cnt in cnts:
        area = cv2.contourArea(cnt)
        if area < 5:
            continue
        peri = cv2.arcLength(cnt, True)
        circ = 4 * 3.14159 * area / (peri * peri) if peri > 0 else 0
        x, y, cw, ch = cv2.boundingRect(cnt)
        thin_features.append({
            'area': area, 'circ': circ, 'peri': peri,
            'bbox': (x1+x, y1+y, cw, ch),
            'local_bbox': (x, y, cw, ch),
        })

    thin_features.sort(key=lambda f: -f['area'])
    for f in thin_features[:5]:
        bx2, by2, fw, fh = f['bbox']
        print(f"  Feature: area={f['area']:.0f} circ={f['circ']:.3f} "
              f"bbox=({bx2},{by2},{fw},{fh})")

    # Also find contours in BINARY region (includes wall pieces)
    cnts2, _ = cv2.findContours(roi_bin.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in cnts2:
        area = cv2.contourArea(cnt)
        if area < 20:
            continue
        peri = cv2.arcLength(cnt, True)
        circ = 4 * 3.14159 * area / (peri * peri) if peri > 0 else 0
        x, y, cw, ch = cv2.boundingRect(cnt)
        aspect = max(cw, ch) / max(min(cw, ch), 1)
        # Look for arc-like shapes: moderate circularity, aspect near 1
        if circ > 0.05 and circ < 0.5 and aspect < 3:
            print(f"  ARC candidate: area={area:.0f} circ={circ:.3f} "
                  f"bbox=({x1+x},{y1+y},{cw},{ch}) aspect={aspect:.1f}")

    # Draw region on debug
    cv2.rectangle(debug, (x1, y1), (x2, y2), (0, 255, 0), 1)
    cv2.putText(debug, name, (x1, y1-3), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0,255,0), 1)

# Also examine the binary directly along the bottom wall for the entry door
print(f"\n=== BOTTOM WALL BINARY SCAN ===")
# Row-by-row binary pixel count at y=383-393
for y in range(383, 394):
    row = binary[y, 250:380]
    nonzero = np.where(row > 0)[0]
    if len(nonzero) > 0:
        segments = []
        in_seg, ss = False, 0
        for c in range(len(row)):
            if row[c] > 0:
                if not in_seg: ss = c; in_seg = True
            else:
                if in_seg:
                    segments.append((250+ss, 250+c-1))
                    in_seg = False
        if in_seg:
            segments.append((250+ss, 250+len(row)-1))
        seg_str = ", ".join(f"x={s}-{e}" for s, e in segments[:6])
        print(f"  y={y}: {len(nonzero)} pixels, segs: {seg_str}")

# Now do similar scan for V-wall-1 region
print(f"\n=== V-WALL-1 BINARY SCAN (x=255-268) ===")
for y in range(270, 395):
    col_strip = binary[y, 255:268]
    nz = np.sum(col_strip > 0)
    if nz > 0:
        pass  # too much output
    else:
        # This is a gap in the wall
        pass

# Check V-wall-1 gap precisely at the kitchen/foyer level
print(f"\n=== V-WALL-1 at Kitchen/Foyer level (y=270-390) ===")
vw1_density = np.sum(binary[270:390, 257:266] > 0, axis=1)
in_gap, gs = False, 0
for r in range(len(vw1_density)):
    if vw1_density[r] < 2:
        if not in_gap: gs = r; in_gap = True
    else:
        if in_gap and r - gs > 3:
            print(f"  Gap: rows {gs}-{r-1} → img_y={270+gs}-{270+r-1} ({r-gs}px)")
        in_gap = False
if in_gap:
    print(f"  Gap: rows {gs}-{len(vw1_density)-1} → img_y={270+gs}-{270+len(vw1_density)-1}")

# Check V-wall-2 for foyer/LR door
print(f"\n=== V-WALL-2 at Foyer/LR level (y=190-390) ===")
vw2_density = np.sum(binary[190:390, 370:380] > 0, axis=1)
in_gap, gs = False, 0
for r in range(len(vw2_density)):
    if vw2_density[r] < 2:
        if not in_gap: gs = r; in_gap = True
    else:
        if in_gap and r - gs > 3:
            print(f"  Gap: rows {gs}-{r-1} → img_y={190+gs}-{190+r-1} ({r-gs}px)")
        in_gap = False
if in_gap:
    print(f"  Gap: rows {gs}-{len(vw2_density)-1} → img_y={190+gs}-{190+len(vw2_density)-1}")

cv2.imwrite('/mnt/d/_CLAUDE-TOOLS/fp_door_regions_debug.png', debug)
print(f"\nDebug saved: fp_door_regions_debug.png")
