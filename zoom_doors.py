#!/usr/bin/env python3
"""
Extract and magnify each door region from the floor plan image.
Creates a single composite image with all door regions side by side,
each magnified 4x with grid lines for precise coordinate reading.
"""
import cv2
import numpy as np

IMG = '/mnt/d/_CLAUDE-TOOLS/fp_example4.png'
gray = cv2.imread(IMG, cv2.IMREAD_GRAYSCALE)

# Door regions to extract (name, center_x, center_y, half_size)
# Centered on the wall gap where each door is
doors = [
    ("1.Entry",   330, 380, 50),
    ("2.Kitchen", 255, 300, 45),
    ("3.Terrace", 255, 200, 55),
    ("4.LR",      378, 280, 45),
    ("5.BR1",     220, 155, 50),
    ("6.BR2",     378, 135, 50),
    ("7.Bath",    350, 155, 45),
]

SCALE = 4  # magnification factor
cols = 4
rows = 2
regions = []

for name, cx, cy, half in doors:
    x1 = max(0, cx - half)
    y1 = max(0, cy - half)
    x2 = min(gray.shape[1], cx + half)
    y2 = min(gray.shape[0], cy + half)

    crop = gray[y1:y2, x1:x2]
    # Magnify
    big = cv2.resize(crop, (crop.shape[1]*SCALE, crop.shape[0]*SCALE),
                     interpolation=cv2.INTER_NEAREST)
    big_color = cv2.cvtColor(big, cv2.COLOR_GRAY2BGR)

    # Draw grid every 10 original pixels
    for gx in range(0, crop.shape[1], 10):
        px = gx * SCALE
        cv2.line(big_color, (px, 0), (px, big_color.shape[0]), (0, 80, 0), 1)
    for gy in range(0, crop.shape[0], 10):
        py = gy * SCALE
        cv2.line(big_color, (0, py), (big_color.shape[1], py), (0, 80, 0), 1)

    # Label with coordinates at edges
    for gx in range(0, crop.shape[1], 20):
        cv2.putText(big_color, str(x1+gx), (gx*SCALE, 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)
    for gy in range(0, crop.shape[0], 20):
        cv2.putText(big_color, str(y1+gy), (2, gy*SCALE+12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)

    # Title
    cv2.putText(big_color, name, (5, big_color.shape[0]-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

    # Draw crosshair at center
    ccx = (cx - x1) * SCALE
    ccy = (cy - y1) * SCALE
    cv2.line(big_color, (ccx-10, ccy), (ccx+10, ccy), (0, 0, 255), 1)
    cv2.line(big_color, (ccx, ccy-10), (ccx, ccy+10), (0, 0, 255), 1)

    regions.append(big_color)

# Find max dimensions
max_h = max(r.shape[0] for r in regions)
max_w = max(r.shape[1] for r in regions)

# Pad all regions to same size
padded = []
for r in regions:
    p = np.ones((max_h, max_w, 3), dtype=np.uint8) * 40  # dark gray background
    p[:r.shape[0], :r.shape[1]] = r
    padded.append(p)

# Arrange in grid
row1 = np.hstack(padded[:4])
row2_items = padded[4:] + [np.ones((max_h, max_w, 3), dtype=np.uint8) * 40]
row2 = np.hstack(row2_items)

# Pad row2 to match row1 width
if row2.shape[1] < row1.shape[1]:
    pad_w = row1.shape[1] - row2.shape[1]
    row2 = np.hstack([row2, np.ones((max_h, pad_w, 3), dtype=np.uint8) * 40])

composite = np.vstack([row1, row2])

cv2.imwrite('/mnt/d/_CLAUDE-TOOLS/fp_door_zoom.png', composite)
print(f"Saved: fp_door_zoom.png ({composite.shape[1]}x{composite.shape[0]})")
