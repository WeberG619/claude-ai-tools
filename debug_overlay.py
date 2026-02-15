#!/usr/bin/env python3
"""Debug overlay: draw doors, windows, fixtures on the original image."""
import cv2
import numpy as np
import math

IMG = '/mnt/d/_CLAUDE-TOOLS/fp_example4.png'
gray = cv2.imread(IMG, cv2.IMREAD_GRAYSCALE)
debug = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

# Door positions (from trace_floorplan.py visual_doors)
# (img_x, img_y, radius_px, start_angle_dxf, end_angle_dxf)
doors = [
    (310, 387, 32, 0, 90, "Entry"),
    (259, 285, 30, 180, 270, "Kitchen"),
    (259, 178, 32, 180, 270, "Terrace"),
    (375, 288, 32, 270, 360, "LR"),
    (240, 158, 28, 90, 180, "BR1"),
    (375, 121, 30, 0, 90, "BR2"),
    (362, 158, 25, 90, 180, "Bath"),
]

for dx, dy, r, sa_dxf, ea_dxf, name in doors:
    # Convert DXF angles to image angles (Y is flipped)
    # DXF: 0=east, 90=north (up), CCW
    # Image: 0=east, 90=south (down in cv2), CW
    # In image coords: angle_img = -angle_dxf (flip sign for Y)
    # cv2.ellipse uses: startAngle, endAngle in CW from east
    sa_img = -ea_dxf  # flip start/end and negate for Y-flip
    ea_img = -sa_dxf

    # Draw arc
    cv2.ellipse(debug, (dx, dy), (r, r), 0, sa_img, ea_img, (0, 0, 255), 2)

    # Leaf line at start angle (in DXF convention, converted to image)
    a_rad = math.radians(sa_dxf)
    lx = int(dx + r * math.cos(a_rad))
    ly = int(dy - r * math.sin(a_rad))  # flip Y
    cv2.line(debug, (dx, dy), (lx, ly), (0, 0, 255), 2)

    # Label
    cv2.putText(debug, name, (dx - 20, dy - r - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

# Windows (from trace_floorplan.py visual_windows)
windows = [
    ('V', 130, 300, 340, "Kit Win"),
    ('V', 130, 175, 215, "Terr Win"),
    ('V', 130, 55, 105, "BR1 Win"),
    ('V', 520, 245, 315, "LR Win"),
    ('V', 520, 55, 125, "BR2 Win"),
]

for orient, cx, y1, y2, name in windows:
    half = 3
    for t in [-0.8, 0, 0.8]:
        xx = int(cx + half * t)
        cv2.line(debug, (xx, y1), (xx, y2), (0, 255, 255), 1)
    cv2.putText(debug, name, (cx - 25, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 255), 1)

# Wall positions for reference
walls = [
    ("Left", 127, 133), ("V1", 259, 264), ("V2", 372, 378), ("Right", 517, 523),
]
hwall = [
    ("Top", 12, 18), ("HBR", 155, 161), ("HLR", 186, 192), ("HKit", 247, 253), ("Bot", 386, 393),
]

for name, x1, x2 in walls:
    cv2.line(debug, (x1, 12), (x1, 393), (0, 128, 0), 1)
    cv2.line(debug, (x2, 12), (x2, 393), (0, 128, 0), 1)
for name, y1, y2 in hwall:
    cv2.line(debug, (127, y1), (523, y1), (128, 0, 0), 1)
    cv2.line(debug, (127, y2), (523, y2), (128, 0, 0), 1)

cv2.imwrite('/mnt/d/_CLAUDE-TOOLS/fp_v8_debug_overlay.png', debug)
print("Saved: fp_v8_debug_overlay.png")
