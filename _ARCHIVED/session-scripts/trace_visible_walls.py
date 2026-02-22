#!/usr/bin/env python3
"""
TRACE VISIBLE WALLS
===================
Only traces walls from layers YOU specify. No hidden layers.

Usage:
    python trace_visible_walls.py <dxf_file> --layers "A-WALL-EXIST,A-WALL" --output walls.json

Then place with PowerShell:
    .\place_walls.ps1 -WallsJson walls.json

This respects YOUR layer choices. Hidden = not traced.
"""

import ezdxf
import json
import argparse
import sys

# Default wall layers to trace (you can override with --layers)
DEFAULT_WALL_LAYERS = [
    'A-WALL-EXIST',
    'A-WALL',
]

# Wall thickness detection: parallel lines this far apart
MIN_THICKNESS_FT = 0.25  # 3 inches
MAX_THICKNESS_FT = 1.17  # 14 inches

# Unit conversion: DXF is in inches, Revit in feet
DXF_TO_REVIT = 1.0 / 12.0


def extract_lines_from_layers(dxf_path: str, layer_names: list) -> list:
    """Extract LINE entities from specified layers only."""
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # Normalize layer names for comparison
    layer_set = set(name.upper() for name in layer_names)

    lines = []
    for entity in msp:
        if entity.dxftype() != 'LINE':
            continue

        entity_layer = entity.dxf.layer.upper()
        if entity_layer not in layer_set:
            continue

        start = entity.dxf.start
        end = entity.dxf.end
        length = ((end.x - start.x)**2 + (end.y - start.y)**2)**0.5

        # Skip tiny lines
        if length < 6:  # 6 inches minimum
            continue

        lines.append({
            'layer': entity.dxf.layer,
            'startX': start.x,
            'startY': start.y,
            'endX': end.x,
            'endY': end.y,
            'length': length
        })

    return lines


def find_wall_centerlines(lines: list) -> list:
    """Find parallel line pairs and calculate centerlines."""

    def is_horizontal(line, tol=0.1):
        return abs(line['startY'] - line['endY']) < tol

    def is_vertical(line, tol=0.1):
        return abs(line['startX'] - line['endX']) < tol

    horizontal = [l for l in lines if is_horizontal(l)]
    vertical = [l for l in lines if is_vertical(l)]

    walls = []

    # Find vertical walls (from horizontal line pairs)
    horiz_sorted = sorted(horizontal, key=lambda l: l['startY'])
    paired_h = set()

    for i, l1 in enumerate(horiz_sorted):
        if i in paired_h:
            continue
        for j in range(i+1, min(i+50, len(horiz_sorted))):
            if j in paired_h:
                continue
            l2 = horiz_sorted[j]

            dist = abs(l2['startY'] - l1['startY'])
            if dist < MIN_THICKNESS_FT * 12 or dist > MAX_THICKNESS_FT * 12:
                if dist > MAX_THICKNESS_FT * 12:
                    break
                continue

            # Calculate X overlap
            x1_min, x1_max = min(l1['startX'], l1['endX']), max(l1['startX'], l1['endX'])
            x2_min, x2_max = min(l2['startX'], l2['endX']), max(l2['startX'], l2['endX'])
            overlap_start = max(x1_min, x2_min)
            overlap_end = min(x1_max, x2_max)

            if overlap_end - overlap_start < 24:  # At least 2 ft overlap
                continue

            center_y = (l1['startY'] + l2['startY']) / 2
            thickness_in = round(dist)

            walls.append({
                'type': 'VERTICAL',
                'start': [overlap_start * DXF_TO_REVIT, center_y * DXF_TO_REVIT, 0],
                'end': [overlap_end * DXF_TO_REVIT, center_y * DXF_TO_REVIT, 0],
                'thickness_in': thickness_in,
                'length_ft': round((overlap_end - overlap_start) * DXF_TO_REVIT, 2)
            })
            paired_h.add(i)
            paired_h.add(j)
            break

    # Find horizontal walls (from vertical line pairs)
    vert_sorted = sorted(vertical, key=lambda l: l['startX'])
    paired_v = set()

    for i, l1 in enumerate(vert_sorted):
        if i in paired_v:
            continue
        for j in range(i+1, min(i+50, len(vert_sorted))):
            if j in paired_v:
                continue
            l2 = vert_sorted[j]

            dist = abs(l2['startX'] - l1['startX'])
            if dist < MIN_THICKNESS_FT * 12 or dist > MAX_THICKNESS_FT * 12:
                if dist > MAX_THICKNESS_FT * 12:
                    break
                continue

            # Calculate Y overlap
            y1_min, y1_max = min(l1['startY'], l1['endY']), max(l1['startY'], l1['endY'])
            y2_min, y2_max = min(l2['startY'], l2['endY']), max(l2['startY'], l2['endY'])
            overlap_start = max(y1_min, y2_min)
            overlap_end = min(y1_max, y2_max)

            if overlap_end - overlap_start < 24:
                continue

            center_x = (l1['startX'] + l2['startX']) / 2
            thickness_in = round(dist)

            walls.append({
                'type': 'HORIZONTAL',
                'start': [center_x * DXF_TO_REVIT, overlap_start * DXF_TO_REVIT, 0],
                'end': [center_x * DXF_TO_REVIT, overlap_end * DXF_TO_REVIT, 0],
                'thickness_in': thickness_in,
                'length_ft': round((overlap_end - overlap_start) * DXF_TO_REVIT, 2)
            })
            paired_v.add(i)
            paired_v.add(j)
            break

    return walls


def main():
    parser = argparse.ArgumentParser(description='Extract walls from specified DXF layers only')
    parser.add_argument('dxf_file', help='Path to DXF file')
    parser.add_argument('--layers', '-l', default=','.join(DEFAULT_WALL_LAYERS),
                        help='Comma-separated list of layer names to trace')
    parser.add_argument('--output', '-o', default='walls.json', help='Output JSON file')
    parser.add_argument('--list-layers', action='store_true', help='List all layers and exit')

    args = parser.parse_args()

    if args.list_layers:
        doc = ezdxf.readfile(args.dxf_file)
        print("All layers in DXF:")
        for layer in sorted(doc.layers, key=lambda l: l.dxf.name):
            status = "ON" if layer.is_on() and not layer.is_frozen() else "OFF"
            print(f"  [{status}] {layer.dxf.name}")
        return

    # Parse layer names
    layer_names = [l.strip() for l in args.layers.split(',')]

    print(f"Extracting from layers: {layer_names}")
    print(f"DXF file: {args.dxf_file}")
    print()

    # Extract lines
    lines = extract_lines_from_layers(args.dxf_file, layer_names)
    print(f"Lines extracted: {len(lines)}")

    # Find wall centerlines
    walls = find_wall_centerlines(lines)
    print(f"Walls detected: {len(walls)}")

    # Save
    with open(args.output, 'w') as f:
        json.dump(walls, f, indent=2)
    print(f"Saved to: {args.output}")

    # Summary
    from collections import Counter
    thickness_dist = Counter(w['thickness_in'] for w in walls)
    print("\nThickness distribution:")
    for t, c in sorted(thickness_dist.items()):
        print(f"  {t}\": {c} walls")


if __name__ == '__main__':
    main()
