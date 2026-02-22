#!/usr/bin/env python3
"""Debug overlay for v10: draw all elements on the original image."""
import cv2
import numpy as np
import math

IMG = '/mnt/d/_CLAUDE-TOOLS/fp_example4.png'
gray = cv2.imread(IMG, cv2.IMREAD_GRAYSCALE)
debug = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

# v10 corrected door positions
doors = [
    (298, 387, 30, 0, 90, "Entry"),
    (259, 298, 26, 180, 270, "Kitchen"),
    (259, 185, 28, 180, 270, "Terrace"),
    (378, 285, 28, 270, 360, "LR"),
    (225, 157, 26, 90, 180, "BR1"),
    (375, 130, 28, 0, 90, "BR2"),
    (345, 157, 24, 90, 180, "Bath"),
]

for dx, dy, r, sa_dxf, ea_dxf, name in doors:
    sa_img = -ea_dxf
    ea_img = -sa_dxf
    cv2.ellipse(debug, (dx, dy), (r, r), 0, sa_img, ea_img, (0, 255, 0), 2)
    a_rad = math.radians(sa_dxf)
    lx = int(dx + r * math.cos(a_rad))
    ly = int(dy - r * math.sin(a_rad))
    cv2.line(debug, (dx, dy), (lx, ly), (0, 255, 0), 2)
    cv2.circle(debug, (dx, dy), 3, (0, 255, 0), -1)
    cv2.putText(debug, name, (dx - 20, dy - r - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)

# Windows
windows = [
    ('V', 130, 300, 338, "Kit Win"),
    ('V', 130, 176, 216, "Terr Win"),
    ('V', 130, 52, 100, "BR1 Win"),
    ('V', 520, 246, 312, "LR Win"),
    ('V', 520, 54, 120, "BR2 Win"),
]
for orient, cx, y1, y2, name in windows:
    for t in [-2, 0, 2]:
        cv2.line(debug, (cx+t, y1), (cx+t, y2), (0, 255, 255), 1)
    cv2.putText(debug, name, (cx - 25, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 255), 1)

# Kitchen fixtures (magenta for casework, orange for fixtures)
MAGENTA = (255, 0, 255)
ORANGE = (0, 140, 255)

# L-counter
counter = [(135,270),(135,384),(198,384),(198,368),(155,368),(155,270)]
cv2.polylines(debug, [np.array(counter)], True, MAGENTA, 2)

# Fridge
fridge = [(135,250),(160,250),(160,270),(135,270)]
cv2.polylines(debug, [np.array(fridge)], True, ORANGE, 1)
cv2.putText(debug, "Fridge", (136, 262), cv2.FONT_HERSHEY_SIMPLEX, 0.25, ORANGE, 1)

# Sink
sink = [(137,308),(153,308),(153,325),(137,325)]
cv2.polylines(debug, [np.array(sink)], True, ORANGE, 1)
cv2.putText(debug, "Sink", (138, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.25, ORANGE, 1)

# Stove
stove = [(166,370),(190,370),(190,382),(166,382)]
cv2.polylines(debug, [np.array(stove)], True, ORANGE, 1)
cv2.putText(debug, "Stove", (167, 378), cv2.FONT_HERSHEY_SIMPLEX, 0.25, ORANGE, 1)

# Bathroom fixtures
# Bathtub
tub = [(268,20),(348,20),(348,50),(268,50)]
cv2.polylines(debug, [np.array(tub)], True, ORANGE, 2)
cv2.putText(debug, "Tub", (290, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.3, ORANGE, 1)

# Toilet
tk_x, tk_y = 352, 78
tank = [(tk_x,tk_y),(tk_x+16,tk_y),(tk_x+16,tk_y+8),(tk_x,tk_y+8)]
bowl = [(tk_x+1,tk_y+8),(tk_x+15,tk_y+8),(tk_x+16,tk_y+16),(tk_x+13,tk_y+22),(tk_x+3,tk_y+22),(tk_x,tk_y+16)]
cv2.polylines(debug, [np.array(tank)], True, ORANGE, 1)
cv2.polylines(debug, [np.array(bowl)], True, ORANGE, 1)
cv2.putText(debug, "WC", (tk_x, tk_y-3), cv2.FONT_HERSHEY_SIMPLEX, 0.25, ORANGE, 1)

# Vanity
van = [(278,130),(335,130),(335,150),(278,150)]
cv2.polylines(debug, [np.array(van)], True, ORANGE, 1)
cv2.circle(debug, (306, 140), 6, ORANGE, 1)
cv2.putText(debug, "Vanity", (285, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.25, ORANGE, 1)

cv2.imwrite('/mnt/d/_CLAUDE-TOOLS/fp_v10_debug_overlay.png', debug)
print("Saved: fp_v10_debug_overlay.png")
