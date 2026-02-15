#!/usr/bin/env python3
"""Precisely locate door arcs and window patterns in fp_example4.png."""
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
print(f"Building bbox: ({bx},{by}) {bw}x{bh}")
print(f"  x range: {bx} to {bx+bw} ({bx+bw})")
print(f"  y range: {by} to {by+bh} ({by+bh})")

# Thick/thin masks
esz = 3
ek = cv2.getStructuringElement(cv2.MORPH_RECT, (esz, esz))
eroded = cv2.erode(binary, ek, iterations=2)
thick = cv2.dilate(eroded, ek, iterations=2)
thin = cv2.subtract(binary, thick)
thin = cv2.morphologyEx(thin, cv2.MORPH_OPEN, np.ones((2,2), np.uint8))

# Debug image
debug = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

# Find contours in thin mask
thin_contours, _ = cv2.findContours(thin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

print(f"\n=== DOOR ARC CANDIDATES (thin mask contours) ===")
arcs = []
for cnt in thin_contours:
    area = cv2.contourArea(cnt)
    if area < 20:
        continue
    peri = cv2.arcLength(cnt, True)
    if peri < 20:
        continue
    circ = 4 * math.pi * area / (peri * peri)
    x, y, cw, ch = cv2.boundingRect(cnt)
    aspect = max(cw, ch) / max(min(cw, ch), 1)

    # Door arcs: quarter-circle area, moderate size
    if 20 < area < 5000 and max(cw, ch) > 12:
        arcs.append({
            'area': area, 'circ': circ, 'bbox': (x, y, cw, ch),
            'aspect': aspect, 'peri': peri,
            'center': (x + cw//2, y + ch//2),
        })

# Sort by area descending
arcs.sort(key=lambda a: -a['area'])
for i, a in enumerate(arcs[:30]):
    x, y, cw, ch = a['bbox']
    print(f"  #{i}: area={a['area']:.0f} circ={a['circ']:.3f} "
          f"bbox=({x},{y},{cw},{ch}) aspect={a['aspect']:.1f} "
          f"center=({a['center'][0]},{a['center'][1]})")
    # Color code: red for high circularity (more arc-like), blue for low
    color = (0, 0, 255) if a['circ'] > 0.15 else (255, 128, 0)
    cv2.rectangle(debug, (x, y), (x+cw, y+ch), color, 1)
    cv2.putText(debug, f"#{i}", (x, y-2), cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)

# Now look for window patterns in exterior wall zones
print(f"\n=== WINDOW DETECTION IN EXTERIOR WALLS ===")

# Scan left wall (x ≈ bx to bx+14)
left_zone = binary[by:by+bh, bx:bx+14]
left_thick = thick[by:by+bh, bx:bx+14]
left_thin = cv2.subtract(left_zone, left_thick)
# Project along x-axis (sum each row)
left_proj = np.sum(left_thin > 0, axis=1)
print(f"\nLeft wall thin features (rows with > 1 thin pixel):")
in_win, ws = False, 0
for r in range(len(left_proj)):
    if left_proj[r] > 1:
        if not in_win: ws = r; in_win = True
    else:
        if in_win:
            span = r - ws
            if span > 5:
                print(f"  rows {ws}-{r-1} (img_y={by+ws}-{by+r-1}, span={span}px)")
                # Mark on debug
                cv2.rectangle(debug, (bx, by+ws), (bx+14, by+r), (0, 255, 255), 1)
            in_win = False

# Scan right wall (x ≈ bx+bw-14 to bx+bw)
right_zone = binary[by:by+bh, bx+bw-14:bx+bw]
right_thick = thick[by:by+bh, bx+bw-14:bx+bw]
right_thin = cv2.subtract(right_zone, right_thick)
right_proj = np.sum(right_thin > 0, axis=1)
print(f"\nRight wall thin features:")
in_win, ws = False, 0
for r in range(len(right_proj)):
    if right_proj[r] > 1:
        if not in_win: ws = r; in_win = True
    else:
        if in_win:
            span = r - ws
            if span > 5:
                print(f"  rows {ws}-{r-1} (img_y={by+ws}-{by+r-1}, span={span}px)")
                cv2.rectangle(debug, (bx+bw-14, by+ws), (bx+bw, by+r), (0, 255, 255), 1)
            in_win = False

# Scan top wall
top_zone = binary[by:by+14, bx:bx+bw]
top_thick = thick[by:by+14, bx:bx+bw]
top_thin = cv2.subtract(top_zone, top_thick)
top_proj = np.sum(top_thin > 0, axis=0)
print(f"\nTop wall thin features:")
in_win, ws = False, 0
for c in range(len(top_proj)):
    if top_proj[c] > 1:
        if not in_win: ws = c; in_win = True
    else:
        if in_win:
            span = c - ws
            if span > 5:
                print(f"  cols {ws}-{c-1} (img_x={bx+ws}-{bx+c-1}, span={span}px)")
            in_win = False

# Scan bottom wall
bot_zone = binary[by+bh-14:by+bh, bx:bx+bw]
bot_thick = thick[by+bh-14:by+bh, bx:bx+bw]
bot_thin = cv2.subtract(bot_zone, bot_thick)
bot_proj = np.sum(bot_thin > 0, axis=0)
print(f"\nBottom wall thin features:")
in_win, ws = False, 0
for c in range(len(bot_proj)):
    if bot_proj[c] > 1:
        if not in_win: ws = c; in_win = True
    else:
        if in_win:
            span = c - ws
            if span > 5:
                print(f"  cols {ws}-{c-1} (img_x={bx+ws}-{bx+c-1}, span={span}px)")
            in_win = False

# === Now look at the BINARY image (not thin mask) in wall gap zones ===
# Windows are often thin parallel lines that survive in the BINARY but NOT in thick mask
# Scan the original binary directly in exterior wall zones
print(f"\n=== WALL GAP ANALYSIS (binary in exterior wall zones) ===")

# For each exterior wall, find stretches where thick mask is 0 but binary is non-zero
# Left wall
print(f"\nLeft wall gaps (thick=0, binary>0):")
for r in range(bh):
    row_thick = thick[by+r, bx:bx+14]
    row_bin = binary[by+r, bx:bx+14]
    if np.sum(row_thick) == 0 and np.sum(row_bin) > 0:
        pass  # Individual rows aren't useful, need to group
# Group into spans
left_thick_col = np.sum(thick[by:by+bh, bx:bx+14] > 0, axis=1)
left_bin_col = np.sum(binary[by:by+bh, bx:bx+14] > 0, axis=1)
in_gap, gs = False, 0
for r in range(bh):
    if left_thick_col[r] < 3 and left_bin_col[r] > 1:
        if not in_gap: gs = r; in_gap = True
    else:
        if in_gap:
            span = r - gs
            if span > 8:
                avg_thin = np.mean(left_bin_col[gs:r])
                print(f"  rows {gs}-{r-1} (img_y={by+gs}-{by+r-1}, span={span}px, avg_density={avg_thin:.1f})")
            in_gap = False

print(f"\nRight wall gaps (thick=0, binary>0):")
right_thick_col = np.sum(thick[by:by+bh, bx+bw-14:bx+bw] > 0, axis=1)
right_bin_col = np.sum(binary[by:by+bh, bx+bw-14:bx+bw] > 0, axis=1)
in_gap, gs = False, 0
for r in range(bh):
    if right_thick_col[r] < 3 and right_bin_col[r] > 1:
        if not in_gap: gs = r; in_gap = True
    else:
        if in_gap:
            span = r - gs
            if span > 8:
                avg_thin = np.mean(right_bin_col[gs:r])
                print(f"  rows {gs}-{r-1} (img_y={by+gs}-{by+r-1}, span={span}px, avg_density={avg_thin:.1f})")
            in_gap = False

# === Precisely locate wall intersections ===
print(f"\n=== WALL CENTERLINE POSITIONS ===")
# Vertical projections on thick mask crop
thick_crop = thick[by:by+bh, bx:bx+bw]
v_proj = np.sum(thick_crop > 0, axis=0).astype(float)
h_proj = np.sum(thick_crop > 0, axis=1).astype(float)

# Find vertical walls (high column sums)
print(f"\nVertical wall bands (column density > {bh*0.2:.0f}):")
in_w, ws = False, 0
for c in range(bw):
    if v_proj[c] > bh * 0.2:
        if not in_w: ws = c; in_w = True
    else:
        if in_w:
            center = (ws + c - 1) / 2
            print(f"  cols {ws}-{c-1} → img_x={bx+ws}-{bx+c-1} (center={bx+center:.0f}, width={c-ws}px)")
            in_w = False

print(f"\nHorizontal wall bands (row density > {bw*0.2:.0f}):")
in_w, ws = False, 0
for r in range(bh):
    if h_proj[r] > bw * 0.2:
        if not in_w: ws = r; in_w = True
    else:
        if in_w:
            center = (ws + r - 1) / 2
            print(f"  rows {ws}-{r-1} → img_y={by+ws}-{by+r-1} (center={by+center:.0f}, width={r-ws}px)")
            in_w = False

# === Find wall gaps (door openings) ===
print(f"\n=== WALL GAPS (door openings) ===")
# For each vertical wall band, scan for gaps (rows where thick mask is thin)
for wall_name, wall_x_start, wall_x_end in [
    ("V-wall-1 (Kitch|Foyer)", 258-bx, 264-bx),
    ("V-wall-2 (Foyer|LR)", 371-bx, 378-bx),
]:
    print(f"\n{wall_name} (img_x={bx+wall_x_start}-{bx+wall_x_end}):")
    col_sum = np.sum(thick_crop[:, max(0,wall_x_start):min(bw,wall_x_end+1)] > 0, axis=1)
    in_gap, gs = False, 0
    for r in range(bh):
        if col_sum[r] < 2:  # gap
            if not in_gap: gs = r; in_gap = True
        else:
            if in_gap:
                span = r - gs
                if span > 5:
                    print(f"  gap rows {gs}-{r-1} → img_y={by+gs}-{by+r-1} (span={span}px)")
                in_gap = False

for wall_name, wall_y_start, wall_y_end in [
    ("H-wall-1 (Kitch top)", 252-by, 259-by),
    ("H-wall-BR (Terr|BR)", 155-by, 162-by),
    ("H-wall-LR (LR|BR2)", 191-by, 198-by),
]:
    print(f"\n{wall_name} (img_y={by+wall_y_start}-{by+wall_y_end}):")
    row_sum = np.sum(thick_crop[max(0,wall_y_start):min(bh,wall_y_end+1), :] > 0, axis=0)
    in_gap, gs = False, 0
    for c in range(bw):
        if row_sum[c] < 2:
            if not in_gap: gs = c; in_gap = True
        else:
            if in_gap:
                span = c - gs
                if span > 5:
                    print(f"  gap cols {gs}-{c-1} → img_x={bx+gs}-{bx+c-1} (span={span}px)")
                in_gap = False

cv2.imwrite('/mnt/d/_CLAUDE-TOOLS/fp_doors_windows_debug.png', debug)
print(f"\nDebug image saved: fp_doors_windows_debug.png")
