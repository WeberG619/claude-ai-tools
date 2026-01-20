#!/usr/bin/env python3
"""
DXF to Revit Wall Converter
===========================
Extracts walls from DXF files and places them in Revit via MCP Bridge.

KEY CONCEPT: A wall is TWO parallel lines (wall faces) with thickness between them.
Single lines are NOT walls. We detect PAIRS of parallel lines.

Usage:
    python dxf_to_revit_walls.py <dxf_file> [--level LEVEL_ID] [--preview]

Author: Bruce Davis / BD Architect + Claude
Version: 1.0
"""

import ezdxf
import json
import argparse
import sys
from collections import Counter
from typing import List, Dict, Tuple, Optional


# ============================================================================
# CONFIGURATION - Wall Type Mapping for Revit
# ============================================================================

WALL_TYPE_MAP = {
    # thickness_inches: (wall_type_id, wall_type_name)
    4: (26564, "Generic - 4\""),
    5: (533588, "Generic - 5\""),
    6: (1693, "Generic - 6\""),
    8: (1698, "Generic - 8\""),
    9: (790343, "Generic - 9\""),
    10: (1214289, "Generic - 10\""),
    12: (1219224, "Generic - 12\""),
}

# Wall layers to search (in priority order)
WALL_LAYER_KEYWORDS = [
    'A-WALL-EXIST',
    'A-WALL',
    'I-WALL',
    'WALL-EXIST',
    'WALL',
    'PARTITION',
    '1HRWALL', '2HRWALL', '3HRWALL',
]

# Tolerances
MIN_WALL_LENGTH_FT = 2.0          # Minimum wall length to consider
MIN_THICKNESS_FT = 0.25           # 3 inches minimum
MAX_THICKNESS_FT = 1.17           # 14 inches maximum
LINE_PARALLEL_TOLERANCE = 0.1     # How close to perfectly horizontal/vertical
MIN_OVERLAP_FT = 2.0              # Minimum overlap between parallel lines


# ============================================================================
# STEP 1: Load DXF and Analyze Layers
# ============================================================================

def load_dxf(filepath: str) -> Tuple:
    """Load DXF file and return document and modelspace."""
    print(f"\n[STEP 1] Loading DXF: {filepath}")
    doc = ezdxf.readfile(filepath)
    msp = doc.modelspace()
    return doc, msp


def analyze_layers(doc, msp) -> Dict[str, int]:
    """Analyze layers and return entity counts per layer."""
    entities_by_layer = Counter(e.dxf.layer for e in msp)
    return dict(entities_by_layer.most_common())


def find_wall_layers(doc, msp) -> List[str]:
    """Find layers that likely contain walls based on keywords."""
    all_layers = [layer.dxf.name for layer in doc.layers]
    entities_by_layer = Counter(e.dxf.layer for e in msp)

    wall_layers = []

    # Check each keyword against all layers
    for keyword in WALL_LAYER_KEYWORDS:
        for layer in all_layers:
            if keyword.upper() in layer.upper():
                count = entities_by_layer.get(layer, 0)
                if count > 0 and layer not in wall_layers:
                    wall_layers.append(layer)

    return wall_layers


# ============================================================================
# STEP 2: Extract Line Entities from Wall Layers
# ============================================================================

def extract_wall_lines(msp, wall_layers: List[str]) -> List[Dict]:
    """Extract LINE entities from specified wall layers."""
    print(f"\n[STEP 2] Extracting lines from {len(wall_layers)} wall layers")

    lines = []
    for entity in msp:
        if entity.dxf.layer in wall_layers and entity.dxftype() == 'LINE':
            start = entity.dxf.start
            end = entity.dxf.end

            length = ((end.x - start.x)**2 + (end.y - start.y)**2)**0.5

            # Skip very short lines
            if length >= 0.5:
                lines.append({
                    'layer': entity.dxf.layer,
                    'startX': round(start.x, 4),
                    'startY': round(start.y, 4),
                    'endX': round(end.x, 4),
                    'endY': round(end.y, 4),
                    'length': round(length, 4)
                })

    print(f"    Extracted {len(lines)} lines")
    return lines


# ============================================================================
# STEP 3: Classify Lines as Horizontal or Vertical
# ============================================================================

def is_horizontal(line: Dict, tolerance: float = LINE_PARALLEL_TOLERANCE) -> bool:
    """Check if line is horizontal (Y values nearly equal)."""
    return abs(line['startY'] - line['endY']) < tolerance


def is_vertical(line: Dict, tolerance: float = LINE_PARALLEL_TOLERANCE) -> bool:
    """Check if line is vertical (X values nearly equal)."""
    return abs(line['startX'] - line['endX']) < tolerance


def classify_lines(lines: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Separate lines into horizontal and vertical."""
    print(f"\n[STEP 3] Classifying lines")

    horizontal = [l for l in lines if is_horizontal(l)]
    vertical = [l for l in lines if is_vertical(l)]

    print(f"    Horizontal: {len(horizontal)}")
    print(f"    Vertical: {len(vertical)}")

    return horizontal, vertical


# ============================================================================
# STEP 4: Find Parallel Line Pairs (THE KEY ALGORITHM)
# ============================================================================

def find_wall_pairs(lines: List[Dict], is_horiz: bool = True) -> List[Dict]:
    """
    Find parallel line pairs that form walls.

    KEY CONCEPT:
    - A wall is represented by TWO parallel lines (the two faces of the wall)
    - The DISTANCE between them is the wall THICKNESS
    - The OVERLAP region is the actual wall extent

    For horizontal lines (Y is constant):
        - Sort by Y
        - Find pairs with Y distance = wall thickness
        - Calculate X overlap = wall length
        - Result: VERTICAL wall (runs in Y direction)

    For vertical lines (X is constant):
        - Sort by X
        - Find pairs with X distance = wall thickness
        - Calculate Y overlap = wall length
        - Result: HORIZONTAL wall (runs in X direction)
    """
    walls = []
    paired = set()

    if is_horiz:
        # Horizontal lines -> Vertical walls
        sorted_lines = sorted(lines, key=lambda l: l['startY'])
        coord_key = 'startY'
    else:
        # Vertical lines -> Horizontal walls
        sorted_lines = sorted(lines, key=lambda l: l['startX'])
        coord_key = 'startX'

    for i, l1 in enumerate(sorted_lines):
        if i in paired:
            continue

        # Check nearby lines for potential pair
        for j in range(i + 1, min(i + 100, len(sorted_lines))):
            if j in paired:
                continue

            l2 = sorted_lines[j]

            # Calculate distance between parallel lines (= wall thickness)
            if is_horiz:
                distance = abs(l2['startY'] - l1['startY'])
            else:
                distance = abs(l2['startX'] - l1['startX'])

            # Check if distance is valid wall thickness (3-14 inches)
            if distance < MIN_THICKNESS_FT or distance > MAX_THICKNESS_FT:
                if distance > MAX_THICKNESS_FT:
                    break  # Sorted, so no more valid pairs
                continue

            # Calculate overlap (= wall length)
            if is_horiz:
                # For horizontal lines, check X overlap
                x1_min = min(l1['startX'], l1['endX'])
                x1_max = max(l1['startX'], l1['endX'])
                x2_min = min(l2['startX'], l2['endX'])
                x2_max = max(l2['startX'], l2['endX'])

                overlap_start = max(x1_min, x2_min)
                overlap_end = min(x1_max, x2_max)
            else:
                # For vertical lines, check Y overlap
                y1_min = min(l1['startY'], l1['endY'])
                y1_max = max(l1['startY'], l1['endY'])
                y2_min = min(l2['startY'], l2['endY'])
                y2_max = max(l2['startY'], l2['endY'])

                overlap_start = max(y1_min, y2_min)
                overlap_end = min(y1_max, y2_max)

            overlap = overlap_end - overlap_start

            # Check if overlap is sufficient
            if overlap < MIN_OVERLAP_FT:
                continue

            # FOUND A WALL PAIR!
            thickness_inches = round(distance * 12)

            if is_horiz:
                # Horizontal line pair = Vertical wall
                centerline = (l1['startY'] + l2['startY']) / 2
                wall = {
                    'type': 'VERTICAL',
                    'centerline': round(centerline, 4),
                    'start': round(overlap_start, 4),
                    'end': round(overlap_end, 4),
                    'length': round(overlap, 4),
                    'thickness_ft': round(distance, 4),
                    'thickness_in': thickness_inches,
                    'start_point': [round(overlap_start, 4), round(centerline, 4), 0],
                    'end_point': [round(overlap_end, 4), round(centerline, 4), 0]
                }
            else:
                # Vertical line pair = Horizontal wall
                centerline = (l1['startX'] + l2['startX']) / 2
                wall = {
                    'type': 'HORIZONTAL',
                    'centerline': round(centerline, 4),
                    'start': round(overlap_start, 4),
                    'end': round(overlap_end, 4),
                    'length': round(overlap, 4),
                    'thickness_ft': round(distance, 4),
                    'thickness_in': thickness_inches,
                    'start_point': [round(centerline, 4), round(overlap_start, 4), 0],
                    'end_point': [round(centerline, 4), round(overlap_end, 4), 0]
                }

            walls.append(wall)
            paired.add(i)
            paired.add(j)
            break

    return walls


def detect_all_walls(horizontal_lines: List[Dict], vertical_lines: List[Dict]) -> List[Dict]:
    """Detect all walls from classified lines."""
    print(f"\n[STEP 4] Finding parallel line pairs (walls)")

    # Horizontal lines form vertical walls
    vertical_walls = find_wall_pairs(horizontal_lines, is_horiz=True)
    print(f"    Vertical walls found: {len(vertical_walls)}")

    # Vertical lines form horizontal walls
    horizontal_walls = find_wall_pairs(vertical_lines, is_horiz=False)
    print(f"    Horizontal walls found: {len(horizontal_walls)}")

    all_walls = vertical_walls + horizontal_walls

    # Show thickness distribution
    thickness_dist = Counter(w['thickness_in'] for w in all_walls)
    print(f"\n    Thickness distribution:")
    for thickness, count in sorted(thickness_dist.items()):
        print(f"        {thickness}\": {count} walls")

    return all_walls


# ============================================================================
# STEP 5: Map Thickness to Revit Wall Types
# ============================================================================

def get_wall_type_id(thickness_inches: int) -> Tuple[int, str]:
    """Get Revit wall type ID for given thickness."""
    if thickness_inches in WALL_TYPE_MAP:
        return WALL_TYPE_MAP[thickness_inches]

    # Find closest match
    available = sorted(WALL_TYPE_MAP.keys())
    closest = min(available, key=lambda x: abs(x - thickness_inches))
    return WALL_TYPE_MAP[closest]


# ============================================================================
# STEP 6: Generate Revit Commands
# ============================================================================

def generate_revit_commands(walls: List[Dict], level_id: int) -> List[Dict]:
    """Generate Revit createWall commands for each wall."""
    print(f"\n[STEP 5] Generating Revit commands")

    commands = []
    for wall in walls:
        wall_type_id, wall_type_name = get_wall_type_id(wall['thickness_in'])

        command = {
            "method": "createWall",
            "params": {
                "startPoint": wall['start_point'],
                "endPoint": wall['end_point'],
                "levelId": level_id,
                "wallTypeId": wall_type_id,
                "height": 10
            },
            "_meta": {
                "wall_type": wall_type_name,
                "thickness": wall['thickness_in'],
                "length": wall['length']
            }
        }
        commands.append(command)

    print(f"    Generated {len(commands)} wall commands")
    return commands


# ============================================================================
# STEP 7: Send to Revit (or Preview)
# ============================================================================

def send_to_revit(commands: List[Dict], pipe_name: str = "RevitMCPBridge2025"):
    """Send wall commands to Revit via named pipe."""
    import socket

    print(f"\n[STEP 6] Sending to Revit via {pipe_name}")

    try:
        import sys
        if sys.platform == 'win32':
            # Windows named pipe
            pipe_path = f"\\\\.\\pipe\\{pipe_name}"
            # Would need win32pipe for proper Windows implementation
            print("    NOTE: Run this from PowerShell for Windows pipe support")
            return
        else:
            # WSL - access Windows named pipe through /mnt
            print("    NOTE: Use PowerShell script for wall placement")
            return
    except Exception as e:
        print(f"    Error: {e}")


def preview_walls(walls: List[Dict], output_file: Optional[str] = None):
    """Preview detected walls and optionally save to JSON."""
    print(f"\n[PREVIEW] Detected {len(walls)} walls:")
    print("-" * 80)

    for i, wall in enumerate(walls[:20]):  # Show first 20
        wall_type_id, wall_type_name = get_wall_type_id(wall['thickness_in'])
        print(f"  {i+1}. {wall['type']:10} {wall_type_name:15} "
              f"from ({wall['start_point'][0]:.1f}, {wall['start_point'][1]:.1f}) "
              f"to ({wall['end_point'][0]:.1f}, {wall['end_point'][1]:.1f}) "
              f"len={wall['length']:.1f}ft")

    if len(walls) > 20:
        print(f"  ... and {len(walls) - 20} more walls")

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(walls, f, indent=2)
        print(f"\n    Saved to {output_file}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def process_dxf(filepath: str, level_id: int = 368, preview: bool = False,
                output_file: Optional[str] = None) -> List[Dict]:
    """
    Complete pipeline: DXF -> Wall Detection -> Revit Commands

    Args:
        filepath: Path to DXF file
        level_id: Revit level ID for wall placement
        preview: If True, only preview (don't send to Revit)
        output_file: Optional JSON file to save detected walls

    Returns:
        List of detected walls
    """
    # Step 1: Load DXF
    doc, msp = load_dxf(filepath)

    # Step 2: Find wall layers
    wall_layers = find_wall_layers(doc, msp)
    print(f"    Found wall layers: {wall_layers}")

    if not wall_layers:
        print("ERROR: No wall layers found!")
        return []

    # Step 3: Extract lines
    lines = extract_wall_lines(msp, wall_layers)

    # Step 4: Classify lines
    horizontal, vertical = classify_lines(lines)

    # Step 5: Detect walls (find parallel pairs)
    walls = detect_all_walls(horizontal, vertical)

    if preview or output_file:
        preview_walls(walls, output_file)

    if not preview:
        # Step 6: Generate commands
        commands = generate_revit_commands(walls, level_id)

        # Step 7: Send to Revit
        # Note: For actual placement, use PowerShell script
        print("\n[INFO] To place walls, run the PowerShell script with the JSON output")

    return walls


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert DXF floor plan to Revit walls")
    parser.add_argument("dxf_file", help="Path to DXF file")
    parser.add_argument("--level", type=int, default=368, help="Revit level ID")
    parser.add_argument("--preview", action="store_true", help="Preview only, don't place")
    parser.add_argument("--output", "-o", help="Output JSON file for detected walls")

    args = parser.parse_args()

    walls = process_dxf(
        args.dxf_file,
        level_id=args.level,
        preview=args.preview,
        output_file=args.output
    )

    print(f"\n{'='*80}")
    print(f"COMPLETE: Detected {len(walls)} walls")
    print(f"{'='*80}")
