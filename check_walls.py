#!/usr/bin/env python3
"""Quick check: find exact bottom wall and V-wall-2 at foyer level."""
import cv2
import numpy as np

gray = cv2.imread('/mnt/d/_CLAUDE-TOOLS/fp_example4.png', cv2.IMREAD_GRAYSCALE)
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# Bottom wall scan: binary presence across full width at y=384-393
print("=== BOTTOM WALL full width scan ===")
for y in range(384, 394):
    segs = []
    in_seg, ss = False, 0
    row = binary[y, 127:523]
    for c in range(len(row)):
        if row[c] > 0:
            if not in_seg: ss = c; in_seg = True
        else:
            if in_seg:
                segs.append((127+ss, 127+c-1))
                in_seg = False
    if in_seg:
        segs.append((127+ss, 127+len(row)-1))
    total = sum(e-s+1 for s, e in segs)
    seg_str = " | ".join(f"{s}-{e}({e-s+1})" for s, e in segs)
    print(f"  y={y}: {total}px [{seg_str}]")

# V-wall-2 scan: check x=365-385 column by column at foyer level (y=250-390)
print(f"\n=== V-WALL-2 column density at foyer level (y=250-390) ===")
for x in range(365, 386):
    col = binary[250:390, x]
    nz = np.sum(col > 0)
    if nz > 20:
        print(f"  x={x}: {nz} pixels")

# Kitchen top wall scan: check y=240-260
print(f"\n=== KITCHEN TOP WALL scan (y=240-260, x=127-265) ===")
for y in range(240, 262):
    row = binary[y, 127:265]
    nz = np.sum(row > 0)
    if nz > 20:
        segs = []
        in_seg, ss = False, 0
        for c in range(len(row)):
            if row[c] > 0:
                if not in_seg: ss = c; in_seg = True
            else:
                if in_seg:
                    segs.append((127+ss, 127+c-1))
                    in_seg = False
        if in_seg:
            segs.append((127+ss, 127+len(row)-1))
        seg_str = " | ".join(f"{s}-{e}" for s, e in segs)
        print(f"  y={y}: {nz}px [{seg_str}]")

# Check for foyer-to-LR wall more precisely
print(f"\n=== V-WALL-2 FOYER/LR (x=370-380) binary density per row ===")
for y_range_name, y1, y2 in [("foyer", 300, 390), ("mid", 250, 300)]:
    dens = np.sum(binary[y1:y2, 370:380] > 0, axis=1)
    solid_rows = np.sum(dens > 5)
    total = y2 - y1
    print(f"  {y_range_name} (y={y1}-{y2}): {solid_rows}/{total} rows have >5px density")
    # Find wall rows
    in_w, ws = False, 0
    for r in range(len(dens)):
        if dens[r] > 5:
            if not in_w: ws = r; in_w = True
        else:
            if in_w:
                print(f"    wall: y={y1+ws}-{y1+r-1} ({r-ws}px)")
            in_w = False
    if in_w:
        print(f"    wall: y={y1+ws}-{y1+len(dens)-1}")

# Find the entry door arc precisely
print(f"\n=== ENTRY DOOR ARC (binary minus thick_gentle) ===")
ek = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
eroded = cv2.erode(binary, ek, iterations=1)
thick = cv2.dilate(eroded, ek, iterations=1)
thin = cv2.subtract(binary, thick)

# Search entry region
roi = thin[340:395, 260:400]
cnts, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
for cnt in cnts:
    area = cv2.contourArea(cnt)
    if area > 10:
        x, y, cw, ch = cv2.boundingRect(cnt)
        print(f"  area={area:.0f} bbox=({260+x},{340+y},{cw},{ch})")
