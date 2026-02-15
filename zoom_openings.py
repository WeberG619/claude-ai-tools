#!/usr/bin/env python3
"""
Zoom into each opening to identify door TYPE (single, double, sliding)
and window TYPE. Creates individual large zoomed images for each.
"""
import cv2
import numpy as np

IMG = '/mnt/d/_CLAUDE-TOOLS/fp_example4.png'
gray = cv2.imread(IMG, cv2.IMREAD_GRAYSCALE)

SCALE = 6  # bigger magnification for detail

# Each opening: (name, center_x, center_y, half_w, half_h)
openings = [
    ("1_Entry_door",    340, 378, 55, 30),   # bottom wall, wide view
    ("2_Kitchen_door",  252, 300, 30, 30),   # V-wall-1 kitchen gap
    ("3_Terrace_door",  252, 200, 35, 55),   # V-wall-1 terrace (large gap!)
    ("4_LR_door",       382, 280, 30, 40),   # V-wall-2 LR gap
    ("5_BR1_door",      215, 155, 45, 30),   # H-wall-BR BR1 gap (wide!)
    ("6_BR2_door",      380, 135, 30, 30),   # V-wall-2 BR2 gap
    ("7_Bath_door",     355, 155, 25, 25),   # H-wall-BR bath gap
    ("8_Win_Kit_L",     130, 318, 18, 30),   # left wall kitchen window
    ("9_Win_Terr_L",    130, 196, 18, 30),   # left wall terrace window
    ("10_Win_BR1_L",    130, 76, 18, 30),    # left wall BR1 window
    ("11_Win_LR_R",     520, 280, 18, 40),   # right wall LR window
    ("12_Win_BR2_R",    520, 88, 18, 40),    # right wall BR2 window
]

results = []
for name, cx, cy, hw, hh in openings:
    x1 = max(0, cx - hw)
    y1 = max(0, cy - hh)
    x2 = min(gray.shape[1], cx + hw)
    y2 = min(gray.shape[0], cy + hh)

    crop = gray[y1:y2, x1:x2]
    big = cv2.resize(crop, (crop.shape[1]*SCALE, crop.shape[0]*SCALE),
                     interpolation=cv2.INTER_NEAREST)
    big_color = cv2.cvtColor(big, cv2.COLOR_GRAY2BGR)

    # Grid every 5 original pixels
    for gx in range(0, crop.shape[1], 5):
        px = gx * SCALE
        cv2.line(big_color, (px, 0), (px, big_color.shape[0]), (0, 50, 0), 1)
    for gy in range(0, crop.shape[0], 5):
        py = gy * SCALE
        cv2.line(big_color, (0, py), (big_color.shape[1], py), (0, 50, 0), 1)

    # Coordinate labels every 10px
    for gx in range(0, crop.shape[1], 10):
        cv2.putText(big_color, str(x1+gx), (gx*SCALE+1, 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
    for gy in range(0, crop.shape[0], 10):
        cv2.putText(big_color, str(y1+gy), (2, gy*SCALE+12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

    # Title
    cv2.putText(big_color, name, (5, big_color.shape[0]-8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    results.append(big_color)

# Create composite - 4 columns
cols = 4
rows = (len(results) + cols - 1) // cols
max_h = max(r.shape[0] for r in results)
max_w = max(r.shape[1] for r in results)

# Pad all to same size
padded = []
for r in results:
    p = np.ones((max_h, max_w, 3), dtype=np.uint8) * 30
    p[:r.shape[0], :r.shape[1]] = r
    padded.append(p)

# Fill remaining slots
while len(padded) % cols != 0:
    padded.append(np.ones((max_h, max_w, 3), dtype=np.uint8) * 30)

row_images = []
for r in range(rows):
    row_images.append(np.hstack(padded[r*cols:(r+1)*cols]))

composite = np.vstack(row_images)
cv2.imwrite('/mnt/d/_CLAUDE-TOOLS/fp_openings_zoom.png', composite)
print(f"Saved: fp_openings_zoom.png ({composite.shape[1]}x{composite.shape[0]})")

# Also save individual images for the most critical ones
for i, (name, cx, cy, hw, hh) in enumerate(openings[:7]):
    cv2.imwrite(f'/mnt/d/_CLAUDE-TOOLS/fp_zoom_{name}.png', results[i])
    print(f"Saved: fp_zoom_{name}.png")
