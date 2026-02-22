#!/usr/bin/env python3
"""Analyze fp_example4.png to extract wall positions, doors, windows, fixtures."""
import cv2
import numpy as np
import json

img = cv2.imread('/mnt/d/_CLAUDE-TOOLS/fp_example4.png', cv2.IMREAD_GRAYSCALE)
h, w = img.shape
print(f"Image: {w}x{h}")

# Binary: walls/lines = white on black
_, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)

# Find building bounding box (exclude text at bottom and watermark)
# Use morphological close to connect wall segments
kernel = np.ones((5,5), np.uint8)
closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

# Find largest connected component = building outline
contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
largest = max(contours, key=cv2.contourArea)
bx, by, bw, bh = cv2.boundingRect(largest)
print(f"Building bbox: x={bx}, y={by}, w={bw}, h={bh}")
print(f"Building pixel range: x=[{bx}..{bx+bw}], y=[{by}..{by+bh}]")

# Crop to building area
crop = binary[by:by+bh, bx:bx+bw]

# Vertical projection (sum each column) - peaks = vertical walls
v_proj = np.sum(crop > 0, axis=0).astype(float)
# Horizontal projection (sum each row) - peaks = horizontal walls
h_proj = np.sum(crop > 0, axis=1).astype(float)

# Find wall positions: columns/rows with high density
# Walls are thick black lines -> high white count in inverted image
v_threshold = bh * 0.3  # vertical wall must span at least 30% of height
h_threshold = bw * 0.3  # horizontal wall must span at least 30% of width

print(f"\n--- Vertical wall candidates (columns with density > {v_threshold:.0f}) ---")
v_wall_cols = []
in_wall = False
wall_start = 0
for c in range(len(v_proj)):
    if v_proj[c] > v_threshold:
        if not in_wall:
            wall_start = c
            in_wall = True
    else:
        if in_wall:
            v_wall_cols.append((wall_start, c-1, c - wall_start))
            in_wall = False
if in_wall:
    v_wall_cols.append((wall_start, len(v_proj)-1, len(v_proj) - wall_start))

for start, end, thickness in v_wall_cols:
    center = (start + end) / 2
    print(f"  col {start}-{end} (center={center:.0f}, thick={thickness}px) -> img_x={bx+start}-{bx+end}")

print(f"\n--- Horizontal wall candidates (rows with density > {h_threshold:.0f}) ---")
h_wall_rows = []
in_wall = False
for r in range(len(h_proj)):
    if h_proj[r] > h_threshold:
        if not in_wall:
            wall_start = r
            in_wall = True
    else:
        if in_wall:
            h_wall_rows.append((wall_start, r-1, r - wall_start))
            in_wall = False
if in_wall:
    h_wall_rows.append((wall_start, len(h_proj)-1, len(h_proj) - wall_start))

for start, end, thickness in h_wall_rows:
    center = (start + end) / 2
    print(f"  row {start}-{end} (center={center:.0f}, thick={thickness}px) -> img_y={by+start}-{by+end}")

# Now analyze with lower threshold for shorter walls
print(f"\n--- All vertical features (lower threshold > {bh*0.10:.0f}) ---")
v_features = []
in_wall = False
for c in range(len(v_proj)):
    if v_proj[c] > bh * 0.10:
        if not in_wall:
            wall_start = c
            in_wall = True
    else:
        if in_wall:
            if c - wall_start >= 3:  # at least 3px wide
                v_features.append((wall_start, c-1, c - wall_start, np.max(v_proj[wall_start:c])))
            in_wall = False

for start, end, thickness, peak in v_features:
    center = (start + end) / 2
    print(f"  col {start}-{end} (center={center:.0f}, thick={thickness}px, peak={peak:.0f}) -> img_x={bx+start}-{bx+end}")

print(f"\n--- All horizontal features (lower threshold > {bw*0.10:.0f}) ---")
h_features = []
in_wall = False
for r in range(len(h_proj)):
    if h_proj[r] > bw * 0.10:
        if not in_wall:
            wall_start = r
            in_wall = True
    else:
        if in_wall:
            if r - wall_start >= 3:
                h_features.append((wall_start, r-1, r - wall_start, np.max(h_proj[wall_start:r])))
            in_wall = False

for start, end, thickness, peak in h_features:
    center = (start + end) / 2
    print(f"  row {start}-{end} (center={center:.0f}, thick={thickness}px, peak={peak:.0f}) -> img_y={by+start}-{by+end}")

# Detect thick vs thin by erosion
thick_kernel = np.ones((3,3), np.uint8)
eroded = cv2.erode(binary, thick_kernel, iterations=2)
thick_mask = cv2.dilate(eroded, thick_kernel, iterations=2)
thin_mask = cv2.subtract(binary, thick_mask)

# Count features in thin mask
thin_contours, _ = cv2.findContours(thin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f"\nThin mask contours: {len(thin_contours)}")

# Filter significant thin contours
significant = []
for cnt in thin_contours:
    area = cv2.contourArea(cnt)
    if area > 15:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = max(w,h) / max(min(w,h), 1)
        perim = cv2.arcLength(cnt, True)
        circ = 4 * 3.14159 * area / (perim * perim) if perim > 0 else 0
        significant.append({
            'area': area, 'bbox': (x, y, w, h), 'aspect': aspect,
            'circularity': circ, 'center': (x + w//2, y + h//2)
        })

print(f"Significant thin contours (area>15): {len(significant)}")
for s in sorted(significant, key=lambda x: -x['area'])[:20]:
    print(f"  area={s['area']:.0f} bbox={s['bbox']} aspect={s['aspect']:.1f} circ={s['circularity']:.2f} center={s['center']}")

# Save analysis image
debug = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
# Draw building bbox
cv2.rectangle(debug, (bx, by), (bx+bw, by+bh), (0, 255, 0), 1)
# Mark detected walls
for start, end, _, _ in v_features:
    cv2.line(debug, (bx+start, by), (bx+start, by+bh), (0, 0, 255), 1)
    cv2.line(debug, (bx+end, by), (bx+end, by+bh), (0, 0, 255), 1)
for start, end, _, _ in h_features:
    cv2.line(debug, (bx, by+start), (bx+bw, by+start), (255, 0, 0), 1)
    cv2.line(debug, (bx, by+end), (bx+bw, by+end), (255, 0, 0), 1)

cv2.imwrite('/mnt/d/_CLAUDE-TOOLS/fp_analysis_debug.png', debug)
print("\nDebug image saved to fp_analysis_debug.png")
