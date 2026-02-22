#!/usr/bin/env python3
"""Generate precise overlay comparing current placements vs image features."""
import cv2
import numpy as np
import math

gray = cv2.imread('/mnt/d/_CLAUDE-TOOLS/fp_example4.png', cv2.IMREAD_GRAYSCALE)
debug = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

# Current v9 door positions (RED)
v9_doors = [
    (303, 387, 30, 0, 90, "Entry-v9"),
    (259, 287, 28, 180, 270, "Kit-v9"),
    (259, 180, 30, 180, 270, "Terr-v9"),
    (375, 280, 30, 270, 360, "LR-v9"),
    (238, 157, 26, 90, 180, "BR1-v9"),
    (375, 148, 26, 0, 90, "BR2-v9"),
    (358, 157, 24, 90, 180, "Bath-v9"),
]

# Corrected positions based on careful image study (GREEN)
corrected_doors = [
    (298, 387, 30, 0, 90, "Entry"),
    (259, 298, 26, 180, 270, "Kit"),
    (259, 185, 28, 180, 270, "Terr"),
    (378, 285, 28, 270, 360, "LR"),
    (225, 157, 26, 90, 180, "BR1"),
    (375, 130, 28, 0, 90, "BR2"),
    (345, 157, 24, 90, 180, "Bath"),
]

def draw_door(img, dx, dy, r, sa_dxf, ea_dxf, name, color, thickness=1):
    sa_img = -ea_dxf
    ea_img = -sa_dxf
    cv2.ellipse(img, (dx, dy), (r, r), 0, sa_img, ea_img, color, thickness)
    a_rad = math.radians(sa_dxf)
    lx = int(dx + r * math.cos(a_rad))
    ly = int(dy - r * math.sin(a_rad))
    cv2.line(img, (dx, dy), (lx, ly), color, thickness)
    cv2.circle(img, (dx, dy), 3, color, -1)  # hinge dot
    cv2.putText(img, name, (dx - 25, dy - r - 3),
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)

# Draw v9 positions in RED
for dx, dy, r, sa, ea, name in v9_doors:
    draw_door(debug, dx, dy, r, sa, ea, name, (0, 0, 255), 1)

# Draw corrected positions in GREEN
for dx, dy, r, sa, ea, name in corrected_doors:
    draw_door(debug, dx, dy, r, sa, ea, name, (0, 255, 0), 2)

# Draw wall grid for reference (thin blue)
for x in [127, 133, 259, 264, 372, 378, 517, 523]:
    cv2.line(debug, (x, 12), (x, 393), (200, 128, 0), 1)
for y in [12, 18, 155, 161, 186, 192, 247, 253, 386, 393]:
    cv2.line(debug, (127, y), (523, y), (128, 0, 128), 1)

# Window positions
windows = [
    ('V', 130, 302, 340, "Kit"), ('V', 130, 178, 218, "Terr"),
    ('V', 130, 55, 95, "BR1"), ('V', 520, 250, 312, "LR"),
    ('V', 520, 58, 115, "BR2"),
]
for orient, cx, y1, y2, name in windows:
    for t in [-2, 0, 2]:
        cv2.line(debug, (cx+t, y1), (cx+t, y2), (0, 255, 255), 1)

cv2.imwrite('/mnt/d/_CLAUDE-TOOLS/fp_precise_overlay.png', debug)
print("Saved: fp_precise_overlay.png")
print("RED = v9 current, GREEN = corrected positions")
