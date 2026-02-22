#!/usr/bin/env python3
"""
Trace floor plan from fp_example4.png — all coordinates in FEET for Revit import.

Building dimensions derived from room labels:
  Width:  6" + 10'1" + 5" + 8'8" + 5" + 11'7" + 6" = 386" = 32'-2"
  Height: 6" + 15'7" + 5" + 13'6" + 6" = 366" = 30'-6"

Image building bbox: (127,12) 396x381 pixels
Scale: ~0.0812 ft/px (x), ~0.0800 ft/px (y)
"""
import cv2
import numpy as np
import ezdxf
import math
import sys

IMG_PATH = '/mnt/d/_CLAUDE-TOOLS/fp_example4.png'
OUT_PATH = '/mnt/d/_CLAUDE-TOOLS/fp_example4_v10_traced.dxf'

# Building dimensions in FEET (Revit imports DXF as feet)
BUILDING_W_FT = 386.0 / 12.0   # 32.167'
BUILDING_H_FT = 366.0 / 12.0   # 30.5'


def _snap_polyline(pts, min_seg=0.2):
    """Force ALL segments to be perfectly H or V. min_seg in feet."""
    if len(pts) < 2:
        return pts
    result = [pts[0]]
    for i in range(1, len(pts)):
        x, y = pts[i]
        px, py = result[-1]
        dx, dy = abs(x - px), abs(y - py)
        if dx < min_seg and dy < min_seg:
            continue
        if dx >= dy:
            y = py
        else:
            x = px
        result.append((x, y))
    cleaned = [result[0]]
    for i in range(1, len(result)):
        x, y = result[i]
        px, py = cleaned[-1]
        if abs(x - px) > 0.01 or abs(y - py) > 0.01:
            cleaned.append((x, y))
    return cleaned


def main():
    output = sys.argv[1] if len(sys.argv) > 1 else OUT_PATH

    # === LOAD & PREPROCESS ===
    gray = cv2.imread(IMG_PATH, cv2.IMREAD_GRAYSCALE)
    h, w = gray.shape
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

    # Building bounding box
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest = max(contours, key=cv2.contourArea)
    bx, by, bw, bh = cv2.boundingRect(largest)
    print(f"Image: {w}x{h}, Building bbox: ({bx},{by}) {bw}x{bh}")

    # Scale: pixels to FEET
    sx = BUILDING_W_FT / bw
    sy = BUILDING_H_FT / bh
    print(f"Scale: {sx:.5f} x {sy:.5f} ft/px")
    print(f"Building: {BUILDING_W_FT:.2f}' x {BUILDING_H_FT:.2f}' ({BUILDING_W_FT*12:.0f}\" x {BUILDING_H_FT*12:.0f}\")")

    def to_dxf(px_x, px_y):
        """Convert image pixel coords to DXF coords (feet). Y is flipped."""
        return ((px_x - bx) * sx, (by + bh - px_y) * sy)

    # === THICK MASK (walls only) ===
    crop = binary[by:by + bh, bx:bx + bw]
    runs = []
    for r in range(0, crop.shape[0], crop.shape[0] // 20):
        row = crop[r, :]
        in_run, rs = False, 0
        for c in range(len(row)):
            if row[c] > 0:
                if not in_run:
                    rs = c
                    in_run = True
            else:
                if in_run:
                    rl = c - rs
                    if 3 <= rl <= 20:
                        runs.append(rl)
                    in_run = False
    for c in range(0, crop.shape[1], crop.shape[1] // 20):
        col = crop[:, c]
        in_run, rs = False, 0
        for r in range(len(col)):
            if col[r] > 0:
                if not in_run:
                    rs = r
                    in_run = True
            else:
                if in_run:
                    rl = r - rs
                    if 3 <= rl <= 20:
                        runs.append(rl)
                    in_run = False
    wall_thick = int(np.median(runs)) if runs else 7
    print(f"Wall thickness: {wall_thick}px")

    esz = max(2, wall_thick // 2)
    ek = cv2.getStructuringElement(cv2.MORPH_RECT, (esz, esz))
    eroded = cv2.erode(binary, ek, iterations=2)
    thick = cv2.dilate(eroded, ek, iterations=2)

    # === DXF SETUP ===
    doc = ezdxf.new('R2010')
    doc.header['$INSUNITS'] = 2  # feet
    msp = doc.modelspace()
    doc.layers.new('WALLS', dxfattribs={'color': 7})
    doc.layers.new('DOORS', dxfattribs={'color': 5})
    doc.layers.new('WINDOWS', dxfattribs={'color': 4})
    doc.layers.new('CASEWORK', dxfattribs={'color': 6})
    doc.layers.new('FIXTURES', dxfattribs={'color': 30})
    doc.layers.new('TEXT', dxfattribs={'color': 2})

    # === WALL OUTLINES FROM THICK MASK CONTOURS ===
    thick_contours, _ = cv2.findContours(thick, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    wall_count = 0
    for cnt in thick_contours:
        area = cv2.contourArea(cnt)
        if area < 80:
            continue
        epsilon = 2.0
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        if len(approx) < 3:
            continue
        dxf_pts = [to_dxf(float(pt[0][0]), float(pt[0][1])) for pt in approx]
        snapped = _snap_polyline(dxf_pts)
        if len(snapped) < 3:
            continue
        msp.add_lwpolyline(snapped, close=True, dxfattribs={'layer': 'WALLS'})
        wall_count += 1

    print(f"Wall contour polylines: {wall_count}")

    # =====================================================
    # DOORS — placed by image analysis of wall gaps
    # =====================================================
    # Wall gap positions (image coords):
    #   Bottom wall gaps: x=166-198 (kitchen), x=323-381 (entry door)
    #   V-wall-1 (x=259-264) gaps: y=285-318 (kitchen), y=162-246 (terrace)
    #   V-wall-2 (x=372-378) gaps: y=121-151 (BR2)
    #   H-wall-BR (y=155-161) gaps: x=184-249 (BR1), x=340-368 (bath)
    #
    # Format: (hinge_img_x, hinge_img_y, radius_px, start_angle, end_angle)
    # DXF angles: CCW from east. 0=E, 90=N, 180=W, 270=S
    # Leaf line drawn at start_angle

    visual_doors = [
        # 1. Entry: bottom wall, foyer. Hinge left of gap ~x=298, swings E+N
        (298, 387, 30, 0, 90),
        # 2. Kitchen: V-wall-1, gap y=285-318. Hinge at bottom of gap, swings W+S
        (259, 298, 26, 180, 270),
        # 3. Terrace: V-wall-1, gap y=162-246. Hinge near top, swings W+S
        (259, 185, 28, 180, 270),
        # 4. LR: V-wall-2 east face, foyer-to-LR. Hinge at top of gap, swings S+E
        (378, 285, 28, 270, 360),
        # 5. BR1: H-wall-BR, gap x=184-249. Hinge at right end ~x=225, swings N+W
        (225, 157, 26, 90, 180),
        # 6. BR2: V-wall-2 east face, gap y=121-151. Hinge at top ~y=130, swings E+N
        (375, 130, 28, 0, 90),
        # 7. Bath: H-wall-BR, gap x=340-368. Hinge at right end ~x=345, swings N+W
        (345, 157, 24, 90, 180),
    ]

    door_count = 0
    for dx, dy, rpx, sa, ea in visual_doors:
        hx, hy = to_dxf(dx, dy)
        r_ft = rpx * max(sx, sy)  # radius in feet
        msp.add_arc(center=(hx, hy), radius=r_ft,
                    start_angle=sa, end_angle=ea,
                    dxfattribs={'layer': 'DOORS'})
        a = math.radians(sa)
        msp.add_line((hx, hy),
                     (hx + r_ft * math.cos(a), hy + r_ft * math.sin(a)),
                     dxfattribs={'layer': 'DOORS'})
        door_count += 1
    print(f"Doors: {door_count}")

    # =====================================================
    # WINDOWS — triple lines in exterior wall gaps
    # =====================================================
    # Left ext wall center: img_x=130 (x=127-133)
    # Right ext wall center: img_x=520 (x=517-523)

    visual_windows = [
        # (orient, wall_center_px, start_px, end_px)
        ('V', 130, 300, 338),   # Left: Kitchen window
        ('V', 130, 176, 216),   # Left: Terrace window
        ('V', 130, 52, 100),    # Left: BR1 window
        ('V', 520, 246, 312),   # Right: LR window
        ('V', 520, 54, 120),    # Right: BR2 window
    ]

    win_count = 0
    for orient, center_px, start_px, end_px in visual_windows:
        half = 3  # half wall thickness pixels
        for t in [-0.8, 0, 0.8]:
            xx = center_px + half * t
            p1 = to_dxf(xx, start_px)
            p2 = to_dxf(xx, end_px)
            msp.add_line(p1, p2, dxfattribs={'layer': 'WINDOWS'})
        win_count += 1
    print(f"Windows: {win_count}")

    # =====================================================
    # KITCHEN CASEWORK & FIXTURES
    # =====================================================
    # Kitchen: img x=[133,259], y=[247,386]
    # L-counter along left wall (x=133) and bottom wall (y=386)

    # L-counter outline: runs along left wall (x~135) and bottom wall (y~384)
    counter_px = [
        (135, 270),          # top of left run (below fridge)
        (135, 384),          # bottom-left corner (at wall)
        (198, 384),          # along bottom wall (to right of stove)
        (198, 368),          # inner edge bottom run
        (155, 368),          # inner L corner
        (155, 270),          # inner top of left run
    ]
    counter_dxf = [to_dxf(px, py) for px, py in counter_px]
    msp.add_lwpolyline(counter_dxf, close=True, dxfattribs={'layer': 'CASEWORK'})

    # Fridge: upper-left of kitchen, against left wall just below kitchen top wall
    fridge_px = [(135, 250), (160, 250), (160, 270), (135, 270)]
    msp.add_lwpolyline([to_dxf(x, y) for x, y in fridge_px],
                       close=True, dxfattribs={'layer': 'FIXTURES'})

    # Kitchen sink on left counter run (against left wall, mid-height)
    ks_px = [(137, 308), (153, 308), (153, 325), (137, 325)]
    msp.add_lwpolyline([to_dxf(x, y) for x, y in ks_px],
                       close=True, dxfattribs={'layer': 'FIXTURES'})
    # Inner basin
    ksi_px = [(139, 310), (151, 310), (151, 323), (139, 323)]
    msp.add_lwpolyline([to_dxf(x, y) for x, y in ksi_px],
                       close=True, dxfattribs={'layer': 'FIXTURES'})

    # Stove/range on bottom counter run
    stove_px = [(166, 370), (190, 370), (190, 382), (166, 382)]
    msp.add_lwpolyline([to_dxf(x, y) for x, y in stove_px],
                       close=True, dxfattribs={'layer': 'FIXTURES'})

    # =====================================================
    # BATHROOM FIXTURES
    # =====================================================
    # Bathroom: img x=[264,372], y=[18,155]

    # Bathtub along top wall of bathroom
    tub_px = [(268, 20), (348, 20), (348, 50), (268, 50)]
    msp.add_lwpolyline([to_dxf(x, y) for x, y in tub_px],
                       close=True, dxfattribs={'layer': 'FIXTURES'})
    # Inner tub
    tubi_px = [(271, 23), (345, 23), (345, 47), (271, 47)]
    msp.add_lwpolyline([to_dxf(x, y) for x, y in tubi_px],
                       close=True, dxfattribs={'layer': 'FIXTURES'})

    # Toilet: right side of bathroom, against right wall
    # Tank (rectangular, against wall at x~370)
    tk_x, tk_y = 352, 78
    tank_px = [(tk_x, tk_y), (tk_x + 16, tk_y), (tk_x + 16, tk_y + 8), (tk_x, tk_y + 8)]
    msp.add_lwpolyline([to_dxf(x, y) for x, y in tank_px],
                       close=True, dxfattribs={'layer': 'FIXTURES'})
    # Bowl (oval shape)
    bowl_px = [
        (tk_x + 1, tk_y + 8), (tk_x + 15, tk_y + 8),
        (tk_x + 16, tk_y + 16), (tk_x + 13, tk_y + 22),
        (tk_x + 3, tk_y + 22), (tk_x, tk_y + 16),
    ]
    msp.add_lwpolyline([to_dxf(x, y) for x, y in bowl_px],
                       close=True, dxfattribs={'layer': 'FIXTURES'})

    # Vanity/sink counter along bottom wall of bathroom (near H-wall-BR y=155)
    van_px = [(278, 130), (335, 130), (335, 150), (278, 150)]
    msp.add_lwpolyline([to_dxf(x, y) for x, y in van_px],
                       close=True, dxfattribs={'layer': 'FIXTURES'})
    # Sink basin (circle centered in vanity)
    sink_c = to_dxf(306, 140)
    msp.add_circle(center=sink_c, radius=0.5,
                   dxfattribs={'layer': 'FIXTURES'})

    print("+ Kitchen: counter, fridge, sink, stove")
    print("+ Bath: tub, toilet, vanity+sink")

    # =====================================================
    # ROOM LABELS
    # =====================================================
    def label(text, px_x, px_y, ht=0.4):
        dx, dy = to_dxf(px_x, px_y)
        msp.add_text(text, dxfattribs={
            'layer': 'TEXT', 'height': ht, 'insert': (dx, dy)})

    label("KITCHEN", 170, 325)
    label("10'1\" x 10'8\"", 165, 340, 0.3)
    label("FOYER", 300, 330)
    label("8'8\" x 18'1\"", 290, 345, 0.3)
    label("LIVING ROOM", 415, 275)
    label("11'7\" x 15'7\"", 418, 295, 0.3)
    label("TERRACE", 175, 208)
    label("BEDROOM", 170, 75)
    label("10'1\" x 11'1\"", 165, 92, 0.3)
    label("BEDROOM", 430, 75)
    label("11'1\" x 13'6\"", 425, 92, 0.3)
    label("BATH", 305, 70)

    # === SAVE ===
    doc.saveas(output)
    print(f"\nSaved: {output}")
    print(f"Building: {BUILDING_W_FT:.2f}' x {BUILDING_H_FT:.2f}'")
    print(f"Total: {wall_count} walls, {door_count} doors, {win_count} windows")


if __name__ == '__main__':
    main()
