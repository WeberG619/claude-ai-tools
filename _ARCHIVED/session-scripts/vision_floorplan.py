#!/usr/bin/env python3
"""
Vision-based floor plan to DXF reconstruction.
Based on visual analysis of fp_example4.png (2BR/1BA condo).
All dimensions in inches, derived from room labels.
"""
import ezdxf
import math
import sys


def create_floor_plan_dxf(output_path):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    # Layers
    doc.layers.new('WALLS', dxfattribs={'color': 7})
    doc.layers.new('DOORS', dxfattribs={'color': 5})
    doc.layers.new('WINDOWS', dxfattribs={'color': 4})
    doc.layers.new('CASEWORK', dxfattribs={'color': 6})
    doc.layers.new('FIXTURES', dxfattribs={'color': 30})
    doc.layers.new('TEXT', dxfattribs={'color': 2})

    # === COORDINATE GRID (inches) ===
    # Walls: exterior=6", interior=5"
    # X: left to right
    x0, x1 = 0, 6          # left ext wall
    x2, x3 = 127, 132      # V-wall-1 (Kitchen|Foyer, Terrace|Hall, BR1|Bath)
    x4, x5 = 236, 241      # V-wall-2 (Foyer|LR, Hall|BR2)
    x6, x7 = 380, 386      # right ext wall
    # Y: bottom to top
    y0, y1 = 0, 6          # bottom ext wall
    y2, y3 = 134, 139      # H-wall-1 (Kitchen top)
    y4, y5 = 193, 198      # H-wall-R (LR top / BR2 bottom)
    y6, y7 = 222, 227      # H-wall-2 (Terrace top / BR1 bottom)
    y8, y9 = 360, 366      # top ext wall

    # --- Helper: draw wall segments with gaps ---
    def wall_seg(p1, p2):
        msp.add_line(p1, p2, dxfattribs={'layer': 'WALLS'})

    def split(start, end, gaps):
        """Return solid segments after removing gaps."""
        gaps = sorted(gaps, key=lambda g: g[0])
        segs = []
        cur = start
        for gs, ge in gaps:
            if gs > cur:
                segs.append((cur, gs))
            cur = max(cur, ge)
        if cur < end:
            segs.append((cur, end))
        return segs

    def hwall(x_from, x_to, y_bot, y_top, gaps=None):
        """Horizontal wall rect with gaps along X axis."""
        for sx, ex in split(x_from, x_to, gaps or []):
            wall_seg((sx, y_bot), (ex, y_bot))
            wall_seg((sx, y_top), (ex, y_top))
            wall_seg((sx, y_bot), (sx, y_top))
            wall_seg((ex, y_bot), (ex, y_top))

    def vwall(x_left, x_right, y_from, y_to, gaps=None):
        """Vertical wall rect with gaps along Y axis."""
        for sy, ey in split(y_from, y_to, gaps or []):
            wall_seg((x_left, sy), (x_left, ey))
            wall_seg((x_right, sy), (x_right, ey))
            wall_seg((x_left, sy), (x_right, sy))
            wall_seg((x_left, ey), (x_right, ey))

    # =====================================================
    # EXTERIOR WALLS
    # =====================================================
    # Bottom wall - entry door gap at x=168..204 (36" door)
    hwall(x0, x7, y0, y1, gaps=[(168, 204)])
    # Top wall
    hwall(x0, x7, y8, y9)
    # Left wall - windows for kitchen, terrace, BR1
    vwall(x0, x1, y0, y9, gaps=[(50, 86), (160, 196), (275, 323)])
    # Right wall - windows for LR, BR2
    vwall(x6, x7, y0, y9, gaps=[(70, 130), (255, 315)])

    # =====================================================
    # INTERIOR WALLS
    # =====================================================
    # H-wall-1: Kitchen north wall (x1 to x3)
    hwall(x1, x3, y2, y3)

    # V-wall-1 bottom: Kitchen|Foyer (y1 to y2) - kitchen door gap y=88..118
    vwall(x2, x3, y1, y2, gaps=[(88, 118)])
    # V-wall-1 middle: Terrace|Hallway (y3 to y6) - terrace door gap y=158..194
    vwall(x2, x3, y3, y6, gaps=[(158, 194)])
    # V-wall-1 top: BR1|Bathroom (y7 to y8) - no gaps
    vwall(x2, x3, y7, y8)

    # H-wall-R: LR top / BR2 bottom (x5 to x6) - no gaps
    hwall(x5, x6, y4, y5)

    # V-wall-2 bottom: Foyer|LR (y1 to y4) - LR door gap y=55..91
    vwall(x4, x5, y1, y4, gaps=[(55, 91)])
    # V-wall-2 top: Hall+Bath|BR2 (y5 to y8) - BR2 door gap y=250..280
    vwall(x4, x5, y5, y8, gaps=[(250, 280)])

    # H-wall-2 left: Terrace top / BR1 bottom (x1 to x3)
    # BR1 door gap x=50..80
    hwall(x1, x3, y6, y7, gaps=[(50, 80)])
    # H-wall-2 right: Hall top / Bath bottom (x3 to x4)
    # Bath door gap x=165..195
    hwall(x3, x4, y6, y7, gaps=[(165, 195)])

    # =====================================================
    # DOORS (arc + leaf line)
    # =====================================================
    def door(hx, hy, r, sa, ea):
        """Quarter-circle arc + leaf line at start angle."""
        msp.add_arc(center=(hx, hy), radius=r,
                     start_angle=sa, end_angle=ea,
                     dxfattribs={'layer': 'DOORS'})
        a = math.radians(sa)
        msp.add_line((hx, hy), (hx + r*math.cos(a), hy + r*math.sin(a)),
                     dxfattribs={'layer': 'DOORS'})

    # Entry door: hinge at left of gap on bottom wall, swings north into foyer
    door(168, y1, 36, 0, 90)
    # Kitchen door: hinge top of gap on V-wall-1 west face, swings west into kitchen
    door(x2, 118, 30, 180, 270)
    # Terrace door: hinge top of gap on V-wall-1 west face, swings west
    door(x2, 194, 36, 180, 270)
    # LR door: hinge top of gap on V-wall-2 east face, swings east into LR
    door(x5, 91, 36, 270, 360)
    # BR1 door: hinge right of gap on H-wall-2, swings north into BR1
    door(80, y7, 30, 90, 180)
    # BR2 door: hinge bottom of gap on V-wall-2 east face, swings east into BR2
    door(x5, 250, 30, 0, 90)
    # Bathroom door: hinge right of gap on H-wall-2, swings north into bath
    door(195, y7, 30, 90, 180)

    # =====================================================
    # WINDOWS (3 parallel lines within wall gap)
    # =====================================================
    def window_v(x_out, x_in, y_from, y_to):
        """Window in a vertical wall (lines run N-S)."""
        for t in [0.15, 0.5, 0.85]:
            xx = x_out + (x_in - x_out) * t
            msp.add_line((xx, y_from), (xx, y_to),
                         dxfattribs={'layer': 'WINDOWS'})

    def window_h(y_out, y_in, x_from, x_to):
        """Window in a horizontal wall (lines run E-W)."""
        for t in [0.15, 0.5, 0.85]:
            yy = y_out + (y_in - y_out) * t
            msp.add_line((x_from, yy), (x_to, yy),
                         dxfattribs={'layer': 'WINDOWS'})

    # Left wall windows (x0=0 outside, x1=6 inside)
    window_v(x0, x1, 50, 86)    # Kitchen
    window_v(x0, x1, 160, 196)  # Terrace
    window_v(x0, x1, 275, 323)  # BR1
    # Right wall windows (x6=380 inside, x7=386 outside)
    window_v(x6, x7, 70, 130)   # LR
    window_v(x6, x7, 255, 315)  # BR2

    # =====================================================
    # KITCHEN CASEWORK (L-counter, fridge)
    # =====================================================
    cd = 24  # counter depth
    # L-counter: along left wall and bottom wall of kitchen
    msp.add_lwpolyline([
        (x1, y2 - 10),         # top of left counter run (leave gap for fridge)
        (x1, y1),              # bottom-left corner
        (x1 + 60, y1),         # along bottom wall
        (x1 + 60, y1 + cd),   # inner corner (bottom run)
        (x1 + cd, y1 + cd),   # inner L corner
        (x1 + cd, y2 - 10),   # inner top of left run
    ], close=True, dxfattribs={'layer': 'CASEWORK'})

    # Fridge: top-left corner of kitchen
    msp.add_lwpolyline([
        (x1, y2 - 6), (x1 + 30, y2 - 6),
        (x1 + 30, y2 - 36), (x1, y2 - 36),
    ], close=True, dxfattribs={'layer': 'FIXTURES'})

    # Sink symbol on bottom counter
    sx, sy = x1 + 32, y1 + 4
    msp.add_lwpolyline([
        (sx, sy), (sx + 18, sy), (sx + 18, sy + 14), (sx, sy + 14)
    ], close=True, dxfattribs={'layer': 'FIXTURES'})
    # Inner basin
    msp.add_lwpolyline([
        (sx+2, sy+2), (sx+16, sy+2), (sx+16, sy+12), (sx+2, sy+12)
    ], close=True, dxfattribs={'layer': 'FIXTURES'})

    # =====================================================
    # BATHROOM FIXTURES
    # =====================================================
    # Bath bounds: x3=132 to x4=236, y7=227 to y8=360
    # Bathtub along top wall
    tub_x, tub_y = x3 + 8, y8 - 34
    msp.add_lwpolyline([
        (tub_x, tub_y), (tub_x + 60, tub_y),
        (tub_x + 60, tub_y + 28), (tub_x, tub_y + 28)
    ], close=True, dxfattribs={'layer': 'FIXTURES'})
    # Inner tub
    msp.add_lwpolyline([
        (tub_x+3, tub_y+3), (tub_x+57, tub_y+3),
        (tub_x+57, tub_y+25), (tub_x+3, tub_y+25)
    ], close=True, dxfattribs={'layer': 'FIXTURES'})

    # Toilet near right wall
    tx, ty = x4 - 28, y7 + 15
    # Tank
    msp.add_lwpolyline([
        (tx, ty), (tx + 18, ty), (tx + 18, ty + 8), (tx, ty + 8)
    ], close=True, dxfattribs={'layer': 'FIXTURES'})
    # Bowl (oval approximation)
    msp.add_lwpolyline([
        (tx + 2, ty + 8), (tx + 16, ty + 8),
        (tx + 18, ty + 16), (tx + 16, ty + 24),
        (tx + 2, ty + 24), (tx, ty + 16),
    ], close=True, dxfattribs={'layer': 'FIXTURES'})

    # Vanity/sink along bottom wall of bathroom
    vx, vy = x3 + 10, y7 + 6
    msp.add_lwpolyline([
        (vx, vy), (vx + 42, vy), (vx + 42, vy + 20), (vx, vy + 20)
    ], close=True, dxfattribs={'layer': 'FIXTURES'})
    # Sink basin
    msp.add_circle(center=(vx + 21, vy + 12), radius=7,
                   dxfattribs={'layer': 'FIXTURES'})

    # =====================================================
    # TEXT LABELS
    # =====================================================
    def label(text, x, y, h=5.0):
        msp.add_text(text, dxfattribs={
            'layer': 'TEXT', 'height': h, 'insert': (x, y)
        })

    # Room labels (centered in each room)
    kx, ky = (x1+x2)/2, (y1+y2)/2
    label("KITCHEN", kx - 22, ky + 8)
    label("10'1\" x 10'8\"", kx - 28, ky - 8, 4)

    fx, fy = (x3+x4)/2, (y1+y2)/2
    label("FOYER", fx - 15, fy + 8)
    label("8'8\" x 18'1\"", fx - 25, fy - 8, 4)

    lx, ly = (x5+x6)/2, (y1+y4)/2
    label("LIVING ROOM", lx - 30, ly + 8)
    label("11'7\" x 15'7\"", lx - 28, ly - 8, 4)

    label("TERRACE", (x1+x2)/2 - 20, (y3+y6)/2)

    b1x, b1y = (x1+x2)/2, (y7+y8)/2
    label("BEDROOM", b1x - 24, b1y + 8)
    label("10'1\" x 11'1\"", b1x - 28, b1y - 8, 4)

    b2x, b2y = (x5+x6)/2, (y5+y8)/2
    label("BEDROOM", b2x - 24, b2y + 8)
    label("11'1\" x 13'6\"", b2x - 28, b2y - 8, 4)

    label("BATH", (x3+x4)/2 - 12, (y7+y8)/2)

    # =====================================================
    # SAVE
    # =====================================================
    doc.saveas(output_path)
    print(f"Saved: {output_path}")
    print(f"Building: {x7}\" x {y9}\" = {x7/12:.1f}' x {y9/12:.1f}'")
    print(f"Rooms: Kitchen, Foyer, Living Room, Terrace, 2 Bedrooms, Bath")


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '/mnt/d/_CLAUDE-TOOLS/fp_example4_v6_vision.dxf'
    create_floor_plan_dxf(out)
