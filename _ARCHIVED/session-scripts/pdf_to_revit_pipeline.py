#!/usr/bin/env python3
"""
PDF/DXF/Image-to-Revit Pipeline
=================================
End-to-end pipeline: PDF/Image/DXF → Convert to DXF → Import into Revit →
Analyze with Revit geometry engine → Create walls, doors, windows automatically.

Accepts PDF, PNG, JPG, TIFF, or DXF as input. PDFs and images are automatically
converted to DXF using pdf_to_dxf.py before importing into Revit.

Uses RevitMCPBridge2026's built-in CAD analysis (C# side) instead of Python-side
line detection. This leverages Revit's own geometry engine for much better accuracy.

Pipeline Steps:
  0. (if needed) Convert PDF/image → DXF using pdf_to_dxf.py
  1. importCAD        — Import DXF into Revit's active view
  2. analyzeCADFloorPlan — Detect walls, doors, windows from imported geometry
  3. batchCreateWalls  — Create all walls in a single transaction
  4. placeDoor/Window  — Place doors and windows on host walls
  5. zoomToFit         — Zoom to see results

Usage:
    python pdf_to_revit_pipeline.py "D:\\path\\to\\floorplan.pdf"
    python pdf_to_revit_pipeline.py "D:\\path\\to\\floorplan.pdf" --scale "1/8" --dry-run
    python pdf_to_revit_pipeline.py "D:\\path\\to\\file.DXF" --unit inch
    python pdf_to_revit_pipeline.py "D:\\path\\to\\photo.png" --scale "1/4"

Author: Weber Gouin / BD Architect + Claude
"""

import json
import math
import os
import subprocess
import argparse
import sys
import time
from collections import defaultdict
from typing import Optional, Dict, Any, List

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False


def _run_ps(cmd, timeout=30):
    if _HAS_BRIDGE:
        return _ps_bridge(cmd, timeout)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, timeout=timeout)
    class _R:
        stdout = r.stdout; stderr = r.stderr; returncode = r.returncode; success = r.returncode == 0
    return _R()


# ============================================================================
# CONFIGURATION
# ============================================================================

PIPE_NAME = "RevitMCPBridge2026"
POWERSHELL_TIMEOUT = 60  # seconds

# Default wall type IDs (query your model to get actual IDs)
DEFAULT_WALL_TYPES = {
    "exterior_8": {"id": 441456, "name": "Generic - 8\" Masonry"},
    "exterior_6": {"id": 1693, "name": "Generic - 6\""},
    "interior_4.5": {"id": 441519, "name": "Interior - 4 1/2\" Partition"},
    "interior_5": {"id": 533588, "name": "Generic - 5\""},
}

# Thickness-to-type mapping (inches → wall type key)
THICKNESS_MAP = {
    (3.0, 5.0): "interior_4.5",
    (5.0, 7.0): "exterior_6",
    (7.0, 10.0): "exterior_8",
}

# Supported input formats
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
DXF_EXTENSIONS = {".dxf", ".dwg"}


# ============================================================================
# PDF/IMAGE → DXF CONVERSION
# ============================================================================

def convert_to_dxf(input_path: str, scale: Optional[str] = None,
                   page: int = 1, building_width_ft: float = 55.0) -> str:
    """
    Convert PDF or image to DXF using pdf_to_dxf.py.

    Args:
        input_path: Path to PDF or image file
        scale: Scale string (e.g., "1/8") or None for auto-detect
        page: PDF page number (1-indexed)
        building_width_ft: Expected building width for auto-scale

    Returns:
        Path to generated DXF file
    """
    # Import the converter (it's in the same directory)
    converter_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, converter_dir)
    from pdf_to_dxf import convert as pdf_to_dxf_convert

    # Generate output path next to input file
    base = os.path.splitext(input_path)[0]
    output_dxf = base + "_converted.dxf"

    print(f"\n[STEP 0] Converting to DXF: {os.path.basename(input_path)}")

    result = pdf_to_dxf_convert(
        input_path=input_path,
        output_path=output_dxf,
        scale=scale,
        page=page,
        building_width_ft=building_width_ft,
    )

    if result["total_entities"] == 0:
        raise RuntimeError("PDF/image conversion produced no geometry")

    ob = result.get("output_bounds", {})
    print(f"    DXF created: {result['total_entities']} entities, "
          f"{ob.get('width_feet', 0):.1f}ft x {ob.get('height_feet', 0):.1f}ft")
    print(f"    Scale: {result['scale']} (factor: {result['scale_factor']})")
    print(f"    Output: {output_dxf}")

    return output_dxf


def needs_conversion(file_path: str) -> bool:
    """Check if the input file needs PDF/image-to-DXF conversion."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in PDF_EXTENSIONS or ext in IMAGE_EXTENSIONS


def to_windows_path(path: str) -> str:
    """Convert WSL path to Windows path for Revit."""
    if path.startswith("/mnt/"):
        # /mnt/d/foo → D:\foo
        drive = path[5].upper()
        rest = path[7:].replace("/", "\\")
        return f"{drive}:\\{rest}"
    return path


# ============================================================================
# NAMED PIPE COMMUNICATION
# ============================================================================

def send_mcp_command(method: str, params: Optional[Dict] = None,
                     pipe_name: str = PIPE_NAME,
                     timeout: int = POWERSHELL_TIMEOUT) -> Dict[str, Any]:
    """
    Send a command to Revit via named pipe using PowerShell.

    The MCP bridge uses newline-delimited JSON over a named pipe.
    From WSL, we use PowerShell to access the Windows named pipe.

    Args:
        method: MCP method name (e.g., "importCAD", "analyzeCADFloorPlan")
        params: Method parameters as dict
        pipe_name: Named pipe name
        timeout: Timeout in seconds

    Returns:
        Parsed JSON response from Revit
    """
    request = {"method": method}
    if params:
        request["params"] = params

    request_json = json.dumps(request)

    # Escape single quotes for PowerShell embedding
    escaped_json = request_json.replace("'", "''")

    ps_script = f"""
$pipeName = "{pipe_name}"
$pipe = $null
try {{
    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream('.', $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    $pipe.Connect({timeout * 1000})

    $writer = New-Object System.IO.StreamWriter($pipe)
    $writer.AutoFlush = $true
    $reader = New-Object System.IO.StreamReader($pipe)

    $writer.WriteLine('{escaped_json}')
    $response = $reader.ReadLine()
    Write-Output $response
}} catch {{
    Write-Output ('{{"success": false, "error": "' + $_.Exception.Message.Replace('"', '\\"') + '"}}')
}} finally {{
    if ($pipe) {{ $pipe.Dispose() }}
}}
"""

    try:
        result = _run_ps(ps_script, timeout=timeout + 10)

        stdout = result.stdout.strip()
        if not stdout:
            return {"success": False, "error": f"No response from Revit (returncode={result.returncode}, stderr={result.stderr.strip()})"}

        return json.loads(stdout)

    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timeout after {timeout}s waiting for Revit"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON response: {e}", "raw": stdout[:500]}
    except FileNotFoundError:
        return {"success": False, "error": "powershell.exe not found. Run from WSL with PowerShell accessible."}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# WALL TYPE RESOLUTION
# ============================================================================

def resolve_wall_type(thickness_inches: float, wall_type: str,
                      wall_type_overrides: Optional[Dict] = None) -> Dict:
    """
    Map wall thickness and type to a Revit wall type.

    Args:
        thickness_inches: Detected wall thickness
        wall_type: "exterior" or "interior"
        wall_type_overrides: Optional dict of {exterior_id, interior_id} to override defaults

    Returns:
        Dict with wallTypeId and wallTypeName
    """
    if wall_type_overrides:
        if wall_type == "exterior" and "exterior_id" in wall_type_overrides:
            return {"wallTypeId": wall_type_overrides["exterior_id"]}
        if wall_type == "interior" and "interior_id" in wall_type_overrides:
            return {"wallTypeId": wall_type_overrides["interior_id"]}

    # Use thickness-based mapping
    for (low, high), type_key in THICKNESS_MAP.items():
        if low <= thickness_inches < high:
            wt = DEFAULT_WALL_TYPES[type_key]
            return {"wallTypeId": wt["id"]}

    # Fallback by type
    if wall_type == "exterior":
        wt = DEFAULT_WALL_TYPES["exterior_8"]
    else:
        wt = DEFAULT_WALL_TYPES["interior_4.5"]

    return {"wallTypeId": wt["id"]}


# ============================================================================
# PYTHON-SIDE WALL DETECTION (for PDF-converted DXFs)
# ============================================================================
# When Revit's analyzeCADFloorPlan is overwhelmed by noise in PDF-converted
# DXFs (text, dimensions, annotations all become vector lines), this module
# detects walls directly from PDF vector geometry using parallel line pairs.
#
# Algorithm:
#   1. Extract vectors from PDF (pymupdf)
#   2. Convert to real-world inches using scale factor
#   3. Classify lines as H/V, filter short ones (< 12")
#   4. Find parallel line pairs with wall-thickness gaps (2.5-12")
#   5. Deduplicate: group by position, snap to known thicknesses, merge extents
#   6. Convert to feet, classify exterior/interior, return analysis dict

# Known architectural wall thicknesses (inches)
# Common residential: 3.5" (2x4 stud), 4.5" (2x4+drywall), 5.5" (2x6),
# 6.0" (6" CMU), 7.0-7.2" (8" CMU actual), 8.0" (8" CMU + finish)
# Note: 9"+ walls exist in commercial but are rare in residential and
# cause false positives from annotation geometry in PDF-converted DXFs
KNOWN_THICKNESSES = [3.5, 4.5, 5.5, 6.0, 7.0, 7.2, 8.0]


def _classify_line(x1: float, y1: float, x2: float, y2: float,
                   angle_tol: float = 5.0):
    """Classify line as H, V, or D. Returns (orientation, length)."""
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length < 0.01:
        return "D", 0.0
    angle = math.degrees(math.atan2(abs(dy), abs(dx)))
    if angle <= angle_tol:
        return "H", length
    elif angle >= 90 - angle_tol:
        return "V", length
    return "D", length


def _find_pairs(lines: List[Dict], min_gap: float, max_gap: float,
                min_overlap: float) -> List[Dict]:
    """
    Find parallel line pairs with wall-thickness gaps.

    Lines must be pre-sorted dicts with {pos, start, end} where:
      - pos: constant coordinate (Y for H lines, X for V lines)
      - start/end: extent along the line

    Returns wall candidates: {center, gap, start, end, length}
    """
    sorted_lines = sorted(lines, key=lambda l: l['pos'])
    n = len(sorted_lines)
    walls = []

    for i in range(n):
        l1 = sorted_lines[i]
        for j in range(i + 1, n):
            l2 = sorted_lines[j]
            gap = l2['pos'] - l1['pos']

            if gap < min_gap:
                continue
            if gap > max_gap:
                break  # sorted — all further lines are farther away

            # Calculate overlap extent
            ov_start = max(l1['start'], l2['start'])
            ov_end = min(l1['end'], l2['end'])
            overlap = ov_end - ov_start

            if overlap >= min_overlap:
                walls.append({
                    'center': (l1['pos'] + l2['pos']) / 2.0,
                    'gap': gap,
                    'start': ov_start,
                    'end': ov_end,
                    'length': overlap,
                })

    return walls


def _snap_to_thickness(gap: float, tolerance: float = 1.5):
    """
    Snap gap to nearest known wall thickness if within tolerance.
    Returns (snapped_value, matched) where matched=True if a known thickness was found.
    """
    best = None
    best_dist = tolerance
    for t in KNOWN_THICKNESSES:
        d = abs(gap - t)
        if d < best_dist:
            best_dist = d
            best = t
    if best is not None:
        return best, True
    return gap, False


def _merge_extents(extents: List, merge_gap: float = 24.0) -> List:
    """Merge overlapping or near-adjacent extents. Returns list of (start, end)."""
    if not extents:
        return []
    sorted_ext = sorted(extents)
    merged = [list(sorted_ext[0])]
    for s, e in sorted_ext[1:]:
        if s <= merged[-1][1] + merge_gap:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [tuple(m) for m in merged]


def _deduplicate_walls(raw_walls: List[Dict], orientation: str,
                       pos_tol: float = 6.0,
                       min_length: float = 36.0) -> List[Dict]:
    """
    Deduplicate wall candidates at similar positions.

    Groups by center position (within pos_tol inches), sub-groups by gap
    thickness, snaps to known wall thickness, rejects non-matching gaps,
    merges extents into continuous segments.
    """
    if not raw_walls:
        return []

    raw_walls.sort(key=lambda w: w['center'])

    # Group by position (within pos_tol inches)
    groups = []
    current = [raw_walls[0]]
    for w in raw_walls[1:]:
        if w['center'] - current[-1]['center'] <= pos_tol:
            current.append(w)
        else:
            groups.append(current)
            current = [w]
    groups.append(current)

    result = []
    for group in groups:
        # Sub-group by gap thickness (within 2" of each other)
        # This separates e.g., 3.5" interior wall from 7.2" exterior at same position
        gap_sorted = sorted(group, key=lambda w: w['gap'])
        sub_groups = []
        sub = [gap_sorted[0]]
        for w in gap_sorted[1:]:
            if w['gap'] - sub[0]['gap'] <= 2.0:
                sub.append(w)
            else:
                sub_groups.append(sub)
                sub = [w]
        sub_groups.append(sub)

        for sub_group in sub_groups:
            # Find best gap — snap to known thickness
            gaps = sorted(w['gap'] for w in sub_group)
            median_gap = gaps[len(gaps) // 2]
            snapped, matched = _snap_to_thickness(median_gap, tolerance=1.5)

            # Reject if gap doesn't match any known wall thickness
            if not matched:
                continue

            # Average center position
            avg_center = sum(w['center'] for w in sub_group) / len(sub_group)

            # Merge extents (allow 36" gap for doorways)
            extents = [(w['start'], w['end']) for w in sub_group]
            merged = _merge_extents(extents, merge_gap=36.0)

            for seg_start, seg_end in merged:
                seg_len = seg_end - seg_start
                if seg_len >= min_length:
                    result.append({
                        'orientation': orientation,
                        'center': avg_center,
                        'gap': snapped,
                        'start': seg_start,
                        'end': seg_end,
                        'length': seg_len,
                        'support': len(sub_group),
                    })

    return result


def _filter_false_positives(walls: List[Dict],
                            connectivity_threshold: float = 24.0,
                            t_intersection_threshold: float = 6.0,
                            min_isolated_length: float = 60.0,
                            cluster_radius: float = 120.0,
                            cluster_min_count: int = 3,
                            cluster_max_length: float = 60.0) -> List[Dict]:
    """
    Remove likely false-positive walls (furniture, fixture rectangles, closet rods).

    Three filters applied in sequence:
      1. Connectivity: Real walls connect to other walls at endpoints.
         Walls with no connections that are shorter than min_isolated_length are removed.
      2. Short-wall clustering: 3+ short walls clustered in a small area
         are likely furniture, not walls.
      3. Boundary consistency: Walls completely isolated from the main
         network (no path to any long wall) are suspect.

    Args:
        walls: List of wall dicts with orientation, center, start, end, length, gap
        connectivity_threshold: Max distance (inches) for endpoint-to-endpoint connection
        t_intersection_threshold: Max distance (inches) for T-intersection (endpoint to wall body)
        min_isolated_length: Walls shorter than this (inches) with 0 connections are removed
        cluster_radius: Radius (inches) to check for short-wall clusters
        cluster_min_count: Min number of short walls in cluster to trigger removal
        cluster_max_length: Max wall length (inches) to be considered "short" for clustering

    Returns:
        Filtered list of walls (false positives removed)
    """
    if len(walls) <= 1:
        return walls

    # --- Step 1: Score connectivity ---
    # For each wall, count how many other walls have endpoints near its endpoints
    # or have their body near its endpoints (T-intersection)
    scores = []
    for i, w in enumerate(walls):
        # Get this wall's endpoints
        if w['orientation'] == 'H':
            ep1 = (w['start'], w['center'])
            ep2 = (w['end'], w['center'])
        else:
            ep1 = (w['center'], w['start'])
            ep2 = (w['center'], w['end'])

        connections = 0
        for j, other in enumerate(walls):
            if i == j:
                continue

            if other['orientation'] == 'H':
                oep1 = (other['start'], other['center'])
                oep2 = (other['end'], other['center'])
            else:
                oep1 = (other['center'], other['start'])
                oep2 = (other['center'], other['end'])

            # Check endpoint-to-endpoint proximity
            for ep in (ep1, ep2):
                for oep in (oep1, oep2):
                    if math.hypot(ep[0] - oep[0], ep[1] - oep[1]) <= connectivity_threshold:
                        connections += 1
                        break
                else:
                    continue
                break

            # Check T-intersection: our endpoint near other wall's body
            if w['orientation'] != other['orientation']:
                for ep in (ep1, ep2):
                    if other['orientation'] == 'H':
                        # Other is horizontal: check if our endpoint is near its Y and within its X span
                        if (abs(ep[1] - other['center']) <= t_intersection_threshold and
                                other['start'] - t_intersection_threshold <= ep[0] <= other['end'] + t_intersection_threshold):
                            connections += 1
                    else:
                        # Other is vertical: check if our endpoint is near its X and within its Y span
                        if (abs(ep[0] - other['center']) <= t_intersection_threshold and
                                other['start'] - t_intersection_threshold <= ep[1] <= other['end'] + t_intersection_threshold):
                            connections += 1

        scores.append(connections)

    # Remove isolated short walls (score=0, length < min_isolated_length)
    keep = set(range(len(walls)))
    removed_isolated = 0
    for i, (w, score) in enumerate(zip(walls, scores)):
        if score == 0 and w['length'] < min_isolated_length:
            keep.discard(i)
            removed_isolated += 1

    # --- Step 2: Short-wall clustering ---
    # Find clusters of short walls in small areas — likely furniture
    short_indices = [i for i in keep if walls[i]['length'] < cluster_max_length]
    cluster_removed = set()

    for i in short_indices:
        if i in cluster_removed:
            continue
        w = walls[i]
        # Midpoint of this wall
        if w['orientation'] == 'H':
            mx, my = (w['start'] + w['end']) / 2, w['center']
        else:
            mx, my = w['center'], (w['start'] + w['end']) / 2

        # Count nearby short walls
        nearby = []
        for j in short_indices:
            if j == i:
                continue
            ow = walls[j]
            if ow['orientation'] == 'H':
                omx, omy = (ow['start'] + ow['end']) / 2, ow['center']
            else:
                omx, omy = ow['center'], (ow['start'] + ow['end']) / 2

            if math.hypot(mx - omx, my - omy) <= cluster_radius:
                nearby.append(j)

        if len(nearby) + 1 >= cluster_min_count:
            # This cluster is likely furniture — remove all
            cluster_removed.add(i)
            cluster_removed.update(nearby)

    keep -= cluster_removed

    removed_cluster = len(cluster_removed)
    total_removed = removed_isolated + removed_cluster

    if total_removed > 0:
        print(f"  False-positive filter: removed {removed_isolated} isolated + "
              f"{removed_cluster} clustered = {total_removed} walls")

    return [walls[i] for i in sorted(keep)]


def _match_doors_to_walls(doors, walls, max_perp_dist=5.0, end_tolerance=3.0):
    """Match each door to its nearest host wall by perpendicular distance.

    Args:
        doors: List of door dicts with centerX/centerY or position.x/y
        walls: Combined list of exterior + interior walls (with startX/Y, endX/Y, orientation)
        max_perp_dist: Max perpendicular distance from wall centerline (ft)
        end_tolerance: How far past wall endpoints a door can be (ft)

    Returns:
        List of (door_index, wall_index, perpendicular_distance) tuples.
        Unmatched doors are not included.
    """
    matches = []
    for di, door in enumerate(doors):
        dx = door.get("centerX", door.get("position", {}).get("x", 0))
        dy = door.get("centerY", door.get("position", {}).get("y", 0))
        best = None

        for wi, wall in enumerate(walls):
            sx, sy = wall["startX"], wall["startY"]
            ex, ey = wall["endX"], wall["endY"]

            if wall["orientation"] == "H":
                wall_y = (sy + ey) / 2
                perp = abs(dy - wall_y)
                lo = min(sx, ex) - end_tolerance
                hi = max(sx, ex) + end_tolerance
                if lo <= dx <= hi and perp < max_perp_dist:
                    if best is None or perp < best[2]:
                        best = (di, wi, perp)
            elif wall["orientation"] == "V":
                wall_x = (sx + ex) / 2
                perp = abs(dx - wall_x)
                lo = min(sy, ey) - end_tolerance
                hi = max(sy, ey) + end_tolerance
                if lo <= dy <= hi and perp < max_perp_dist:
                    if best is None or perp < best[2]:
                        best = (di, wi, perp)

        if best:
            matches.append(best)

    return matches


def _match_windows_to_walls(windows, walls, max_perp_dist=6.0, end_tolerance=3.0):
    """Match windows to host walls. Uses larger max_perp_dist since window labels
    are often placed inside the room, further from the exterior wall face."""
    normalized = []
    for w in windows:
        pos = w.get("position", {})
        normalized.append({**w, "centerX": pos.get("x", 0), "centerY": pos.get("y", 0)})
    return _match_doors_to_walls(normalized, walls, max_perp_dist, end_tolerance)


def _final_overlap_dedup(walls: List[Dict], pos_tol: float = 12.0,
                         overlap_pct: float = 0.5) -> List[Dict]:
    """
    Final deduplication pass: remove walls that are near-duplicates of longer walls.

    Two walls are near-duplicates if:
      - Same orientation
      - Centers within pos_tol inches
      - Overlapping by >= overlap_pct of the shorter wall's length

    When duplicates are found, keep the longer wall (more likely real).
    If lengths are similar, prefer thickness closer to a known standard.
    """
    if not walls:
        return []

    # Process each orientation separately
    result = []
    for orient in ['H', 'V']:
        orient_walls = [w for w in walls if w['orientation'] == orient]
        if not orient_walls:
            continue

        # Sort by center position
        orient_walls.sort(key=lambda w: w['center'])

        # Mark walls to remove
        remove = set()

        for i in range(len(orient_walls)):
            if i in remove:
                continue
            w1 = orient_walls[i]

            for j in range(i + 1, len(orient_walls)):
                if j in remove:
                    continue
                w2 = orient_walls[j]

                # Check center proximity
                if w2['center'] - w1['center'] > pos_tol:
                    break  # sorted — no more candidates

                # Check overlap
                ov_start = max(w1['start'], w2['start'])
                ov_end = min(w1['end'], w2['end'])
                overlap = max(0, ov_end - ov_start)

                shorter_len = min(w1['length'], w2['length'])
                if shorter_len > 0 and overlap / shorter_len >= overlap_pct:
                    # These are near-duplicates — remove the shorter one
                    if w1['length'] >= w2['length']:
                        remove.add(j)
                    else:
                        remove.add(i)
                        break  # w1 is removed, skip remaining comparisons

        for i, w in enumerate(orient_walls):
            if i not in remove:
                result.append(w)

    return result


def _extract_lines_from_dxf(dxf_path: str, layer_filter: Optional[List[str]] = None,
                            scale_factor: float = 1.0) -> Dict:
    """
    Extract line geometry from a DXF file, optionally filtering by layer.

    This is used for re-analyzing PDF-converted DXFs where layer separation
    helps filter noise (e.g., only use WALLS layer, skip CURVES and WALLS-RECT).

    Args:
        dxf_path: Path to DXF file
        layer_filter: List of layer names to include (None = all layers)
        scale_factor: Scale factor from DXF units to inches

    Returns:
        Dict with lines[], bounds, and layer statistics
    """
    try:
        import ezdxf
    except ImportError:
        raise ImportError("ezdxf required for DXF layer filtering. Install: pip install ezdxf")

    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    lines = []
    layer_counts = defaultdict(int)

    for entity in msp.query('LINE'):
        layer = entity.dxf.layer
        layer_counts[layer] += 1

        if layer_filter and layer not in layer_filter:
            continue

        start = entity.dxf.start
        end = entity.dxf.end

        lines.append({
            'x1': start.x * scale_factor,
            'y1': start.y * scale_factor,
            'x2': end.x * scale_factor,
            'y2': end.y * scale_factor,
            'layer': layer,
        })

    # Compute bounds from included lines
    if lines:
        all_x = [l['x1'] for l in lines] + [l['x2'] for l in lines]
        all_y = [l['y1'] for l in lines] + [l['y2'] for l in lines]
        bounds = {
            'min_x': min(all_x), 'max_x': max(all_x),
            'min_y': min(all_y), 'max_y': max(all_y),
            'width': max(all_x) - min(all_x),
            'height': max(all_y) - min(all_y),
        }
    else:
        bounds = {'min_x': 0, 'max_x': 0, 'min_y': 0, 'max_y': 0, 'width': 0, 'height': 0}

    return {
        'lines': lines,
        'bounds': bounds,
        'layer_counts': dict(layer_counts),
        'total_lines': sum(layer_counts.values()),
        'filtered_lines': len(lines),
    }


def detect_walls_from_pdf(pdf_path: str, page: int = 1,
                          scale: Optional[str] = None,
                          building_width_ft: float = 55.0,
                          min_line_inches: float = 18.0,
                          min_wall_gap: float = 2.5,
                          max_wall_gap: float = 10.0,
                          min_overlap_inches: float = 18.0,
                          min_wall_ft: float = 3.0,
                          layer_filter: Optional[List[str]] = None,
                          dxf_reanalyze: Optional[str] = None,
                          filter_false_positives: bool = True) -> Dict:
    """
    Detect walls from a PDF floor plan using Python-side parallel line analysis.

    Returns analysis dict compatible with analyzeCADFloorPlan output format,
    so it can be passed directly to step_create_walls().

    Args:
        pdf_path: Path to PDF file
        page: Page number (1-indexed)
        scale: Scale string (e.g., "1/8") or None for auto-detect
        building_width_ft: Expected building width for auto-scale
        min_line_inches: Minimum line length to consider (filters noise)
        min_wall_gap: Minimum parallel gap to consider as wall (inches)
        max_wall_gap: Maximum parallel gap to consider as wall (inches)
        min_overlap_inches: Minimum overlap between paired lines
        min_wall_ft: Minimum wall length in feet
        layer_filter: For DXF re-analysis, list of layers to include
                      (e.g., ["WALLS"] to skip CURVES and WALLS-RECT noise)
        dxf_reanalyze: Path to a DXF file to re-analyze with layer filtering
                       (instead of extracting from PDF). Units must be in inches.
        filter_false_positives: Apply connectivity-based false positive filter (default True)

    Returns:
        Analysis dict with exteriorWalls, interiorWalls, bounds, summary
    """
    print(f"\n{'=' * 60}")
    print(f"Python-Side Wall Detection")
    print(f"{'=' * 60}")

    h_lines = []  # {pos: y_center, start: x_min, end: x_max}
    v_lines = []  # {pos: x_center, start: y_min, end: y_max}
    total_lines = 0

    # --- Mode 1: Re-analyze a DXF with layer filtering ---
    if dxf_reanalyze:
        print(f"  Input: {os.path.basename(dxf_reanalyze)} (DXF re-analysis)")
        if layer_filter:
            print(f"  Layer filter: {layer_filter}")

        dxf_data = _extract_lines_from_dxf(dxf_reanalyze, layer_filter)
        total_lines = dxf_data['total_lines']

        print(f"  Total lines in DXF: {dxf_data['total_lines']}")
        for layer, count in sorted(dxf_data['layer_counts'].items()):
            marker = " *" if (not layer_filter or layer in layer_filter) else ""
            print(f"    {layer}: {count} lines{marker}")
        print(f"  Using {dxf_data['filtered_lines']} lines after layer filter")

        # Lines from DXF are already in inches (DXF units), no scale conversion needed
        for line in dxf_data['lines']:
            x1, y1 = line['x1'], line['y1']
            x2, y2 = line['x2'], line['y2']

            orient, length = _classify_line(x1, y1, x2, y2)
            if length < min_line_inches:
                continue

            if orient == "H":
                h_lines.append({
                    'pos': (y1 + y2) / 2.0,
                    'start': min(x1, x2),
                    'end': max(x1, x2),
                })
            elif orient == "V":
                v_lines.append({
                    'pos': (x1 + x2) / 2.0,
                    'start': min(y1, y2),
                    'end': max(y1, y2),
                })

    # --- Mode 2: Extract from PDF/image (original path) ---
    else:
        print(f"  Input: {os.path.basename(pdf_path)}")

        # Import from pdf_to_dxf (same directory)
        converter_dir = os.path.dirname(os.path.abspath(__file__))
        if converter_dir not in sys.path:
            sys.path.insert(0, converter_dir)
        from pdf_to_dxf import (extract_vectors_from_pdf, extract_lines_from_image,
                                 auto_detect_scale, parse_scale, ARCH_SCALES)

        # Determine extraction mode based on file type
        ext = os.path.splitext(pdf_path)[1].lower()
        is_image = ext in ('.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp')

        if is_image:
            geometry = extract_lines_from_image(pdf_path, dpi=300,
                                                min_line_length=30, hough_threshold=50)
            print(f"  Image mode: {len(geometry['lines'])} lines detected")
        else:
            geometry = extract_vectors_from_pdf(pdf_path, page_num=page - 1)
            print(f"  Vector mode: {len(geometry['lines'])} lines, "
                  f"{len(geometry['rectangles'])} rects")

        total_lines = len(geometry['lines'])

        # Determine scale
        if scale:
            scale_factor = parse_scale(scale)
            print(f"  Scale: {scale} (factor: {scale_factor})")
        else:
            bounds = geometry["bounds"]
            scale_name = auto_detect_scale(
                bounds["width"], bounds["height"],
                expected_width_ft=building_width_ft
            )
            scale_factor = ARCH_SCALES[scale_name]["factor"]
            print(f"  Scale: {ARCH_SCALES[scale_name]['label']} (auto, factor: {scale_factor})")

        # Convert all geometry to real-world inches
        if is_image:
            dpi = geometry.get("dpi", 300)
            to_inches = scale_factor / dpi
        else:
            to_inches = scale_factor / 72.0
        page_height = geometry["page_height"]

        # Process line segments
        for line in geometry["lines"]:
            x1 = line["x1"] * to_inches
            y1 = (page_height - line["y1"]) * to_inches
            x2 = line["x2"] * to_inches
            y2 = (page_height - line["y2"]) * to_inches

            orient, length = _classify_line(x1, y1, x2, y2)
            if length < min_line_inches:
                continue

            if orient == "H":
                h_lines.append({
                    'pos': (y1 + y2) / 2.0,
                    'start': min(x1, x2),
                    'end': max(x1, x2),
                })
            elif orient == "V":
                v_lines.append({
                    'pos': (x1 + x2) / 2.0,
                    'start': min(y1, y2),
                    'end': max(y1, y2),
                })

        # Process thin rectangles (filled wall segments in PDF)
        for rect in geometry.get("rectangles", []):
            x0 = rect["x0"] * to_inches
            y0_r = (page_height - rect["y0"]) * to_inches
            x1 = rect["x1"] * to_inches
            y1_r = (page_height - rect["y1"]) * to_inches

            w = abs(x1 - x0)
            h = abs(y1_r - y0_r)
            x_lo, x_hi = min(x0, x1), max(x0, x1)
            y_lo, y_hi = min(y0_r, y1_r), max(y0_r, y1_r)

            if w > h and w >= min_line_inches:
                # Horizontal rectangle → two parallel H lines
                h_lines.append({'pos': y_lo, 'start': x_lo, 'end': x_hi})
                h_lines.append({'pos': y_hi, 'start': x_lo, 'end': x_hi})
            elif h > w and h >= min_line_inches:
                # Vertical rectangle → two parallel V lines
                v_lines.append({'pos': x_lo, 'start': y_lo, 'end': y_hi})
                v_lines.append({'pos': x_hi, 'start': y_lo, 'end': y_hi})

    print(f"  Filtered lines (>= {min_line_inches}\"): {len(h_lines)} H, {len(v_lines)} V")

    # Find parallel pairs
    h_pairs = _find_pairs(h_lines, min_wall_gap, max_wall_gap, min_overlap_inches)
    v_pairs = _find_pairs(v_lines, min_wall_gap, max_wall_gap, min_overlap_inches)
    print(f"  Raw pairs: {len(h_pairs)} H-wall, {len(v_pairs)} V-wall")

    # Deduplicate: group by position, snap thickness, merge extents
    min_len_in = min_wall_ft * 12.0
    h_walls = _deduplicate_walls(h_pairs, "H", pos_tol=6.0, min_length=min_len_in)
    v_walls = _deduplicate_walls(v_pairs, "V", pos_tol=6.0, min_length=min_len_in)
    all_walls = h_walls + v_walls
    print(f"  After position dedup: {len(h_walls)} H + {len(v_walls)} V = {len(all_walls)} walls")

    # Final overlap-based deduplication: remove near-duplicates where a shorter
    # wall overlaps significantly with a longer wall at a similar position
    all_walls = _final_overlap_dedup(all_walls, pos_tol=12.0, overlap_pct=0.5)
    h_count = sum(1 for w in all_walls if w['orientation'] == 'H')
    v_count = sum(1 for w in all_walls if w['orientation'] == 'V')
    print(f"  After overlap dedup: {h_count} H + {v_count} V = {len(all_walls)} walls")

    # Apply false-positive filter
    if filter_false_positives:
        all_walls = _filter_false_positives(all_walls)
        h_count = sum(1 for w in all_walls if w['orientation'] == 'H')
        v_count = sum(1 for w in all_walls if w['orientation'] == 'V')
        print(f"  After false-positive filter: {h_count} H + {v_count} V = {len(all_walls)} walls")

    # Classify exterior (>= 6") vs interior (< 6") and convert to feet
    exterior = []
    interior = []

    for w in all_walls:
        thickness = w['gap']
        length_ft = w['length'] / 12.0

        if w['orientation'] == 'H':
            wall_dict = {
                'startX': round(w['start'] / 12.0, 2),
                'startY': round(w['center'] / 12.0, 2),
                'endX': round(w['end'] / 12.0, 2),
                'endY': round(w['center'] / 12.0, 2),
                'length': round(length_ft, 2),
                'orientation': 'H',
                'thicknessInches': round(thickness, 1),
                'openings': [],
            }
        else:
            wall_dict = {
                'startX': round(w['center'] / 12.0, 2),
                'startY': round(w['start'] / 12.0, 2),
                'endX': round(w['center'] / 12.0, 2),
                'endY': round(w['end'] / 12.0, 2),
                'length': round(length_ft, 2),
                'orientation': 'V',
                'thicknessInches': round(thickness, 1),
                'openings': [],
            }

        if thickness >= 6.0:
            exterior.append(wall_dict)
        else:
            interior.append(wall_dict)

    # Compute bounds
    all_x = []
    all_y = []
    for w in exterior + interior:
        all_x.extend([w['startX'], w['endX']])
        all_y.extend([w['startY'], w['endY']])

    result_bounds = {}
    if all_x:
        result_bounds = {
            'minX': round(min(all_x), 2),
            'minY': round(min(all_y), 2),
            'maxX': round(max(all_x), 2),
            'maxY': round(max(all_y), 2),
            'width': round(max(all_x) - min(all_x), 2),
            'height': round(max(all_y) - min(all_y), 2),
        }

    print(f"\n  Results:")
    print(f"    Exterior walls: {len(exterior)}")
    print(f"    Interior walls: {len(interior)}")
    if result_bounds:
        print(f"    Bounds: {result_bounds.get('width', 0):.1f}' x "
              f"{result_bounds.get('height', 0):.1f}'")
    print(f"{'=' * 60}")

    return {
        'success': True,
        'method': 'python_wall_detection',
        'bounds': result_bounds,
        'summary': {
            'totalLines': total_lines,
            'totalArcs': 0,
            'exteriorWallCount': len(exterior),
            'interiorWallCount': len(interior),
            'doorCount': 0,
            'windowCount': 0,
        },
        'exteriorWalls': exterior,
        'interiorWalls': interior,
        'doors': [],
        'windows': [],
    }


# ============================================================================
# DOOR/WINDOW DETECTION FROM ORIGINAL CAD DXF
# ============================================================================
# When the original CAD DXF is available (not a PDF-converted DXF), it contains
# rich door/window information that the PDF conversion strips out:
#   - Arc entities = door swings (radius = door width)
#   - Text tags = door/window sizes in WWWH format (e.g., "3068" = 30"x68")
#   - Block inserts = fixtures/furniture (toilets, tubs, sinks)
#
# This function extracts door/window data from the original CAD DXF.

def _parse_door_window_tag(text: str):
    """
    Parse a 4-digit WWWH door/window tag.

    Format: WWWH where WW=width in inches, WH=height in inches.
    Examples:
      "3068" → 30" wide, 68" tall (standard door)
      "2868" → 28" wide, 68" tall (bathroom door)
      "3153" → 31" wide, 53" tall (window)
      "6068" → 60" wide, 68" tall (sliding door)

    Returns (width_inches, height_inches) or None if not a valid tag.
    """
    text = text.strip()
    if len(text) != 4 or not text.isdigit():
        return None

    width = int(text[:2])
    height = int(text[2:])

    # Sanity check: doors/windows are typically 12-72" wide, 24-96" tall
    if not (12 <= width <= 72 and 24 <= height <= 96):
        return None

    return (width, height)


def detect_doors_from_cad(dxf_path: str, scale_factor: float = 1.0) -> Dict:
    """
    Detect doors and windows from an original CAD DXF file.

    Uses arc entities (door swings), text tags (WWWH format), and their
    spatial relationships to identify doors and windows.

    Also computes wall-line bounds (from long lines >= 10ft) to enable
    coordinate alignment with PDF-derived wall positions.

    Args:
        dxf_path: Path to original CAD DXF file (not PDF-converted)
        scale_factor: Scale factor to convert DXF units to inches
                      (1.0 if DXF is already in inches)

    Returns:
        Dict with doors[], windows[], cad_wall_bounds, and metadata.
        Coordinates are in CAD's native system (inches, converted to feet).
        Use _align_cad_to_pdf_coords() to map to PDF coordinate system.
    """
    try:
        import ezdxf
    except ImportError:
        return {
            'success': False,
            'error': 'ezdxf not installed. Install with: pip install ezdxf',
            'doors': [],
            'windows': [],
        }

    print(f"\n{'=' * 60}")
    print(f"CAD Door/Window Detection")
    print(f"{'=' * 60}")
    print(f"  Input: {os.path.basename(dxf_path)}")

    try:
        doc = ezdxf.readfile(dxf_path)
    except Exception as e:
        print(f"  ERROR: Cannot read DXF: {e}")
        return {'success': False, 'error': str(e), 'doors': [], 'windows': []}

    msp = doc.modelspace()

    # --- Compute wall bounds from long lines (>= 10ft = 120") ---
    # These represent the building perimeter for coordinate alignment
    wall_x, wall_y = [], []
    for entity in msp.query('LINE'):
        sx = entity.dxf.start.x * scale_factor
        sy = entity.dxf.start.y * scale_factor
        ex = entity.dxf.end.x * scale_factor
        ey = entity.dxf.end.y * scale_factor
        length = math.hypot(ex - sx, ey - sy)
        if length >= 120:  # >= 10ft
            wall_x.extend([sx, ex])
            wall_y.extend([sy, ey])

    cad_wall_bounds = None
    if wall_x:
        cad_wall_bounds = {
            'minX': min(wall_x) / 12.0,
            'maxX': max(wall_x) / 12.0,
            'minY': min(wall_y) / 12.0,
            'maxY': max(wall_y) / 12.0,
        }
        print(f"  CAD wall bounds (ft): X=[{cad_wall_bounds['minX']:.1f}, {cad_wall_bounds['maxX']:.1f}] "
              f"Y=[{cad_wall_bounds['minY']:.1f}, {cad_wall_bounds['maxY']:.1f}]")

    # --- Extract arcs (door swings) ---
    # Door swings in CAD can be partial arcs (15-90+ degrees) with R = 24-42"
    arcs = []
    for entity in msp.query('ARC'):
        center = entity.dxf.center
        radius = entity.dxf.radius * scale_factor
        start_angle = entity.dxf.start_angle
        end_angle = entity.dxf.end_angle

        angle_span = (end_angle - start_angle) % 360
        # Accept any arc with door-sized radius (2ft-3.5ft = 24-42")
        # Some CAD files draw partial door swings (15-38 degrees) instead of full 90
        if 10 <= angle_span <= 100 and 20 <= radius <= 44:
            arcs.append({
                'center_x': center.x * scale_factor,
                'center_y': center.y * scale_factor,
                'radius': radius,
                'start_angle': start_angle,
                'end_angle': end_angle,
                'angle_span': angle_span,
            })

    print(f"  Arcs found: {len(arcs)} door swings")

    # --- Extract text tags ---
    tags = []
    room_labels = []
    for entity in msp.query('TEXT MTEXT'):
        if hasattr(entity.dxf, 'insert'):
            pos = entity.dxf.insert
        elif hasattr(entity.dxf, 'text_direction'):
            pos = entity.dxf.insert
        else:
            continue

        text = entity.dxf.text if hasattr(entity.dxf, 'text') else str(entity.text)
        text = text.strip()

        parsed = _parse_door_window_tag(text)
        if parsed:
            width, height = parsed
            tags.append({
                'text': text,
                'x': pos.x * scale_factor,
                'y': pos.y * scale_factor,
                'width_inches': width,
                'height_inches': height,
            })
        elif len(text) > 1 and not text.isdigit():
            # Likely a room label
            room_labels.append({
                'text': text,
                'x': pos.x * scale_factor,
                'y': pos.y * scale_factor,
            })

    print(f"  Text tags found: {len(tags)} door/window tags, {len(room_labels)} room labels")

    # --- Match arcs to tags ---
    # A door is an arc with a nearby matching text tag
    # Windows are tags with no nearby arc and height < 60" (typical window height)
    doors = []
    windows = []
    used_tags = set()
    used_arcs = set()

    # First pass: match arcs to nearest text tags
    for i, arc in enumerate(arcs):
        best_tag_idx = None
        best_dist = 72.0  # Max 6ft search radius for matching tag to arc

        for j, tag in enumerate(tags):
            if j in used_tags:
                continue
            dist = math.hypot(arc['center_x'] - tag['x'], arc['center_y'] - tag['y'])
            if dist < best_dist:
                best_dist = dist
                best_tag_idx = j

        width_inches = arc['radius']  # Arc radius ≈ door width
        width_ft = width_inches / 12.0
        height_inches = 80  # Default 6'8" door

        if best_tag_idx is not None:
            tag = tags[best_tag_idx]
            width_inches = tag['width_inches']
            height_inches = tag['height_inches']
            width_ft = width_inches / 12.0
            used_tags.add(best_tag_idx)

        used_arcs.add(i)

        doors.append({
            'centerX': round(arc['center_x'] / 12.0, 2),
            'centerY': round(arc['center_y'] / 12.0, 2),
            'widthInches': width_inches,
            'widthFeet': round(width_ft, 2),
            'heightInches': height_inches,
            'source': 'arc' + ('+tag' if best_tag_idx is not None else ''),
            'wallOrientation': '?',
        })

    # Second pass: remaining tags without arcs
    for j, tag in enumerate(tags):
        if j in used_tags:
            continue

        width = tag['width_inches']
        height = tag['height_inches']

        # Classify: doors are tall (>= 60"), windows are shorter
        if height >= 60:
            doors.append({
                'centerX': round(tag['x'] / 12.0, 2),
                'centerY': round(tag['y'] / 12.0, 2),
                'widthInches': width,
                'widthFeet': round(width / 12.0, 2),
                'heightInches': height,
                'source': 'tag_only',
                'wallOrientation': '?',
            })
        else:
            windows.append({
                'position': {
                    'x': round(tag['x'] / 12.0, 2),
                    'y': round(tag['y'] / 12.0, 2),
                },
                'widthInches': width,
                'widthFeet': round(width / 12.0, 2),
                'heightInches': height,
                'sillHeight': 3.0,  # Default 3ft sill
                'source': 'tag',
                'wallOrientation': '?',
            })

    print(f"\n  Results:")
    print(f"    Doors:   {len(doors)}")
    print(f"    Windows: {len(windows)}")
    print(f"    Rooms:   {len(room_labels)}")
    print(f"{'=' * 60}")

    return {
        'success': True,
        'method': 'cad_door_detection',
        'doors': doors,
        'windows': windows,
        'rooms': room_labels,
        'cad_wall_bounds': cad_wall_bounds,
        'metadata': {
            'total_arcs': len(arcs),
            'total_tags': len(tags),
            'total_room_labels': len(room_labels),
            'matched_arc_tag': sum(1 for d in doors if '+tag' in d.get('source', '')),
        }
    }


def _get_perimeter_bounds(exterior_walls: List[Dict],
                          min_perimeter_length: float = 10.0) -> Optional[Dict]:
    """
    Compute perimeter bounds from exterior walls, using only substantial walls
    (>= min_perimeter_length ft) to define the building outline.

    Short exterior walls (garage stubs, setbacks) can shift bounds and
    produce incorrect coordinate alignment. By requiring minimum length,
    we get the true building perimeter.

    Returns {minX, maxX, minY, maxY} from the primary perimeter walls,
    or None if insufficient exterior walls.
    """
    if len(exterior_walls) < 4:
        return None

    # Filter to substantial walls only
    long_h = [w for w in exterior_walls
              if w.get('orientation') == 'H' and w.get('length', 0) >= min_perimeter_length]
    long_v = [w for w in exterior_walls
              if w.get('orientation') == 'V' and w.get('length', 0) >= min_perimeter_length]

    # Fallback: if too few long walls, lower the threshold
    if len(long_h) < 2 or len(long_v) < 2:
        long_h = [w for w in exterior_walls if w.get('orientation') == 'H']
        long_v = [w for w in exterior_walls if w.get('orientation') == 'V']

    if len(long_h) < 2 or len(long_v) < 2:
        return None

    # For V walls: find the leftmost (min X) and rightmost (max X)
    long_v.sort(key=lambda w: w['startX'])
    left_x = long_v[0]['startX']
    right_x = long_v[-1]['startX']

    # For H walls: find topmost (min Y) and bottommost (max Y)
    long_h.sort(key=lambda w: w['startY'])
    top_y = long_h[0]['startY']
    bottom_y = long_h[-1]['startY']

    if top_y > bottom_y:
        top_y, bottom_y = bottom_y, top_y

    return {
        'minX': left_x,
        'maxX': right_x,
        'minY': top_y,
        'maxY': bottom_y,
    }


def _align_cad_to_pdf_coords(cad_result: Dict, pdf_analysis: Dict) -> Dict:
    """
    Transform door/window coordinates from CAD space to PDF wall-detection space.

    The CAD DXF and PDF extraction use different coordinate systems:
    - Different origins (CAD centered near 0, PDF offset by page position + scale)
    - Different scales (PDF ~0.73x the CAD due to rendering)
    - Y axis is flipped (CAD Y-up, PDF Y increases downward on plan)

    Computes an affine transform using the building perimeter (outermost exterior
    walls in both systems) as correspondence anchors.

    Args:
        cad_result: Output from detect_doors_from_cad() (includes cad_wall_bounds)
        pdf_analysis: Full analysis dict from wall detection (with exteriorWalls)

    Returns:
        Modified cad_result with doors/windows in PDF coordinates
    """
    cad_bounds = cad_result.get('cad_wall_bounds')
    if not cad_bounds:
        print("  WARNING: Cannot align coordinates — missing CAD wall bounds")
        return cad_result

    # Use exterior wall perimeter for alignment (more precise than all-wall bounds)
    exterior_walls = pdf_analysis.get('exteriorWalls', [])
    pdf_perim = _get_perimeter_bounds(exterior_walls)

    if not pdf_perim:
        # Fallback to full analysis bounds
        pdf_perim = pdf_analysis.get('bounds')
        if not pdf_perim:
            print("  WARNING: Cannot align coordinates — missing PDF bounds")
            return cad_result
        print("  Note: Using full bounds for alignment (few exterior walls)")

    cad_dx = cad_bounds['maxX'] - cad_bounds['minX']
    cad_dy = cad_bounds['maxY'] - cad_bounds['minY']
    pdf_dx = pdf_perim['maxX'] - pdf_perim['minX']
    pdf_dy = pdf_perim['maxY'] - pdf_perim['minY']

    if cad_dx == 0 or cad_dy == 0:
        print("  WARNING: Cannot align — zero-span CAD bounds")
        return cad_result

    # X: direct mapping (CAD minX → PDF minX, CAD maxX → PDF maxX)
    scale_x = pdf_dx / cad_dx
    offset_x = pdf_perim['minX'] - scale_x * cad_bounds['minX']

    # Y: flipped mapping (CAD maxY=top → PDF minY=top, CAD minY=bottom → PDF maxY=bottom)
    # Solve: pdf_minY = scale_y * cad_maxY + offset_y
    #        pdf_maxY = scale_y * cad_minY + offset_y
    scale_y = (pdf_perim['maxY'] - pdf_perim['minY']) / (cad_bounds['minY'] - cad_bounds['maxY'])
    offset_y = pdf_perim['minY'] - scale_y * cad_bounds['maxY']

    # Verify the mapping
    check_top = scale_y * cad_bounds['maxY'] + offset_y
    check_bot = scale_y * cad_bounds['minY'] + offset_y
    err_top = abs(check_top - pdf_perim['minY'])
    err_bot = abs(check_bot - pdf_perim['maxY'])

    if err_top > 1.0 or err_bot > 1.0:
        # Y flip didn't work — try direct mapping
        scale_y = pdf_dy / cad_dy
        offset_y = pdf_perim['minY'] - scale_y * cad_bounds['minY']
        print(f"  Note: Using direct Y mapping (no flip)")

    print(f"  Coordinate alignment (perimeter-based):")
    print(f"    X: pdf = {scale_x:.4f} * cad + {offset_x:.2f}")
    print(f"    Y: pdf = {scale_y:.4f} * cad + {offset_y:.2f}")
    print(f"    CAD perimeter: X=[{cad_bounds['minX']:.1f}, {cad_bounds['maxX']:.1f}] "
          f"Y=[{cad_bounds['minY']:.1f}, {cad_bounds['maxY']:.1f}]")
    print(f"    PDF perimeter: X=[{pdf_perim['minX']:.1f}, {pdf_perim['maxX']:.1f}] "
          f"Y=[{pdf_perim['minY']:.1f}, {pdf_perim['maxY']:.1f}]")

    # Transform all door positions
    for door in cad_result['doors']:
        old_x, old_y = door['centerX'], door['centerY']
        door['centerX'] = round(scale_x * old_x + offset_x, 2)
        door['centerY'] = round(scale_y * old_y + offset_y, 2)

    # Transform all window positions
    for window in cad_result['windows']:
        pos = window['position']
        old_x, old_y = pos['x'], pos['y']
        pos['x'] = round(scale_x * old_x + offset_x, 2)
        pos['y'] = round(scale_y * old_y + offset_y, 2)

    return cad_result


# ============================================================================
# PIPELINE STEPS
# ============================================================================

def step_test_connection() -> bool:
    """Step 0: Test MCP bridge connectivity."""
    print("\n[STEP 0] Testing RevitMCPBridge connection...")

    result = send_mcp_command("ping")
    if result.get("success"):
        print("    Connected to Revit MCP Bridge")
        return True
    else:
        print(f"    FAILED: {result.get('error', 'Unknown error')}")
        print("    Make sure Revit is open and the MCP bridge is running.")
        return False


def step_import_cad(dxf_path: str, unit: str = "inch",
                    view_id: Optional[int] = None) -> Optional[int]:
    """
    Step 1: Import DXF file into Revit.

    Args:
        dxf_path: Windows path to DXF file (e.g., "D:\\path\\file.DXF")
        unit: Import unit ("inch", "foot", "millimeter", etc.)
        view_id: Target view ID (uses active view if None)

    Returns:
        importedId (ElementId) or None on failure
    """
    print(f"\n[STEP 1] Importing DXF: {dxf_path}")
    print(f"    Unit: {unit}")

    params = {"filePath": dxf_path, "unit": unit}
    if view_id:
        params["viewId"] = view_id

    result = send_mcp_command("importCAD", params)

    if result.get("success"):
        imported_id = result["importedId"]
        print(f"    Imported successfully. Element ID: {imported_id}")
        return imported_id
    else:
        print(f"    FAILED: {result.get('error', 'Unknown error')}")
        return None


def step_analyze_floor_plan(import_id: int,
                            exterior_thickness: float = 8.0,
                            interior_thickness: float = 4.5,
                            tolerance: float = 2.0) -> Optional[Dict]:
    """
    Step 2: Analyze imported CAD geometry to detect walls, doors, windows.

    Uses Revit's C# geometry engine for parallel line detection, arc detection, etc.

    Args:
        import_id: ElementId of the imported CAD
        exterior_thickness: Expected exterior wall thickness (inches)
        interior_thickness: Expected interior wall thickness (inches)
        tolerance: Matching tolerance (inches)

    Returns:
        Analysis result dict or None on failure
    """
    print(f"\n[STEP 2] Analyzing floor plan (import ID: {import_id})...")
    print(f"    Exterior thickness: {exterior_thickness}\"")
    print(f"    Interior thickness: {interior_thickness}\"")
    print(f"    Tolerance: {tolerance}\"")

    result = send_mcp_command("analyzeCADFloorPlan", {
        "importId": import_id,
        "exteriorWallThickness": exterior_thickness,
        "interiorWallThickness": interior_thickness,
        "tolerance": tolerance
    })

    if result.get("success"):
        summary = result.get("summary", {})
        bounds = result.get("bounds", {})
        print(f"    Analysis complete!")
        print(f"    Bounds: {bounds.get('width', 0):.1f}' x {bounds.get('height', 0):.1f}'")
        print(f"    Exterior walls: {summary.get('exteriorWallCount', 0)}")
        print(f"    Interior walls: {summary.get('interiorWallCount', 0)}")
        print(f"    Doors detected: {summary.get('doorCount', 0)}")
        print(f"    Windows detected: {summary.get('windowCount', 0)}")
        print(f"    Total CAD lines: {summary.get('totalLines', 0)}")
        print(f"    Total CAD arcs: {summary.get('totalArcs', 0)}")
        return result
    else:
        print(f"    FAILED: {result.get('error', 'Unknown error')}")
        return None


def step_create_walls(analysis: Dict, level_id: int, height: float = 10.0,
                      wall_type_overrides: Optional[Dict] = None) -> Optional[Dict]:
    """
    Step 3: Create walls from analysis results using batchCreateWalls.

    Coordinates from analyzeCADFloorPlan are already in feet (Revit internal units).
    No unit conversion needed.

    Args:
        analysis: Result from step_analyze_floor_plan
        level_id: Revit Level ElementId
        height: Wall height in feet
        wall_type_overrides: Optional {exterior_id: int, interior_id: int}

    Returns:
        batchCreateWalls result or None on failure
    """
    exterior_walls = analysis.get("exteriorWalls", [])
    interior_walls = analysis.get("interiorWalls", [])
    all_walls = []

    print(f"\n[STEP 3] Creating {len(exterior_walls)} exterior + {len(interior_walls)} interior walls...")

    # Build wall commands for exterior walls
    for i, wall in enumerate(exterior_walls):
        wall_type_info = resolve_wall_type(
            wall.get("thicknessInches", 8.0), "exterior", wall_type_overrides
        )
        all_walls.append({
            "startPoint": [wall["startX"], wall["startY"], 0],
            "endPoint": [wall["endX"], wall["endY"], 0],
            "levelId": level_id,
            "wallTypeId": wall_type_info["wallTypeId"],
            "height": height,
        })

    # Build wall commands for interior walls
    for i, wall in enumerate(interior_walls):
        wall_type_info = resolve_wall_type(
            wall.get("thicknessInches", 4.5), "interior", wall_type_overrides
        )
        all_walls.append({
            "startPoint": [wall["startX"], wall["startY"], 0],
            "endPoint": [wall["endX"], wall["endY"], 0],
            "levelId": level_id,
            "wallTypeId": wall_type_info["wallTypeId"],
            "height": height,
        })

    if not all_walls:
        print("    No walls to create!")
        return None

    # Send batch command
    result = send_mcp_command("batchCreateWalls", {"walls": all_walls})

    if result.get("success"):
        created = result.get("createdCount", 0)
        failed = result.get("failedCount", 0)
        print(f"    Created: {created} walls")
        if failed:
            print(f"    Failed: {failed} walls")
            for fw in result.get("failedWalls", []):
                print(f"      - {fw.get('error', 'unknown')}")
        return result
    else:
        print(f"    FAILED: {result.get('error', 'Unknown error')}")
        return None


def step_place_doors(analysis: Dict, wall_result: Optional[Dict],
                     level_id: int) -> int:
    """
    Step 4a: Place doors at detected locations.

    Args:
        analysis: Result from step_analyze_floor_plan
        wall_result: Result from step_create_walls (with wall IDs)
        level_id: Revit Level ElementId

    Returns:
        Number of doors placed
    """
    doors = analysis.get("doors", [])
    if not doors:
        print("\n[STEP 4a] No doors detected — skipping door placement")
        return 0

    print(f"\n[STEP 4a] Placing {len(doors)} doors...")

    placed = 0
    matched = sum(1 for d in doors if d.get("hostWallId"))
    for door in doors:
        cx = door.get("centerX", 0)
        cy = door.get("centerY", 0)
        width_ft = door.get("widthFeet", 3.0)
        host_wall_id = door.get("hostWallId")

        params = {
            "location": [cx, cy, 0],
            "levelId": level_id,
            "width": width_ft,
        }
        if host_wall_id:
            params["wallId"] = host_wall_id

        result = send_mcp_command("placeDoor", params)

        if result.get("success"):
            placed += 1

    print(f"    Placed: {placed}/{len(doors)} doors")
    if placed < len(doors):
        print(f"    Note: {len(doors) - placed} doors need manual placement")
    return placed


def step_place_windows(analysis: Dict, wall_result: Optional[Dict],
                       level_id: int) -> int:
    """
    Step 4b: Place windows at detected locations.

    Args:
        analysis: Result from step_analyze_floor_plan
        wall_result: Result from step_create_walls (with wall IDs)
        level_id: Revit Level ElementId

    Returns:
        Number of windows placed
    """
    windows = analysis.get("windows", [])
    if not windows:
        print("\n[STEP 4b] No windows detected — skipping window placement")
        return 0

    print(f"\n[STEP 4b] Placing {len(windows)} windows...")

    placed = 0
    matched = sum(1 for w in windows if w.get("hostWallId"))
    for window in windows:
        pos = window.get("position", {})
        width_ft = window.get("widthFeet", 3.0)
        host_wall_id = window.get("hostWallId")

        params = {
            "location": [pos.get("x", 0), pos.get("y", 0), 0],
            "levelId": level_id,
            "width": width_ft,
            "sillHeight": 3.0,  # Default 3' sill
        }
        if host_wall_id:
            params["wallId"] = host_wall_id

        result = send_mcp_command("placeWindow", params)

        if result.get("success"):
            placed += 1

    print(f"    Placed: {placed}/{len(windows)} windows")
    if placed < len(windows):
        print(f"    Note: {len(windows) - placed} windows need manual placement")
    return placed


def step_zoom_to_fit() -> bool:
    """Step 5: Zoom to fit to see results."""
    print("\n[STEP 5] Zooming to fit...")

    result = send_mcp_command("zoomToFit")
    if result.get("success"):
        print("    View zoomed to fit")
        return True
    else:
        print(f"    Note: zoomToFit returned: {result.get('error', 'unknown')}")
        return False


# ============================================================================
# DRY RUN / PREVIEW
# ============================================================================

def dry_run_report(analysis: Dict, level_id: int, height: float,
                   wall_type_overrides: Optional[Dict] = None):
    """Print a detailed dry-run report of what would be created."""
    print("\n" + "=" * 70)
    print("DRY RUN — No changes will be made to Revit")
    print("=" * 70)

    bounds = analysis.get("bounds", {})
    summary = analysis.get("summary", {})

    print(f"\nFloor Plan Bounds:")
    print(f"  Width:  {bounds.get('width', 0):.1f} ft")
    print(f"  Height: {bounds.get('height', 0):.1f} ft")
    print(f"  Origin: ({bounds.get('minX', 0):.1f}, {bounds.get('minY', 0):.1f})")

    print(f"\nDetected Elements:")
    print(f"  Exterior walls: {summary.get('exteriorWallCount', 0)}")
    print(f"  Interior walls: {summary.get('interiorWallCount', 0)}")
    print(f"  Doors:          {summary.get('doorCount', 0)}")
    print(f"  Windows:        {summary.get('windowCount', 0)}")

    # List exterior walls
    ext_walls = analysis.get("exteriorWalls", [])
    if ext_walls:
        print(f"\nExterior Walls ({len(ext_walls)}):")
        for i, w in enumerate(ext_walls):
            orient = w.get("orientation", "?")
            length = w.get("length", 0)
            thick = w.get("thicknessInches", 0)
            openings = w.get("openings", [])
            opening_str = f"  [{len(openings)} opening(s)]" if openings else ""
            print(f"  {i+1:2d}. {orient} {length:6.1f}ft  {thick:.0f}\"  "
                  f"({w.get('startX',0):.1f},{w.get('startY',0):.1f}) → "
                  f"({w.get('endX',0):.1f},{w.get('endY',0):.1f}){opening_str}")

    # List interior walls
    int_walls = analysis.get("interiorWalls", [])
    if int_walls:
        print(f"\nInterior Walls ({len(int_walls)}):")
        for i, w in enumerate(int_walls):
            orient = w.get("orientation", "?")
            length = w.get("length", 0)
            thick = w.get("thicknessInches", 0)
            openings = w.get("openings", [])
            opening_str = f"  [{len(openings)} opening(s)]" if openings else ""
            print(f"  {i+1:2d}. {orient} {length:6.1f}ft  {thick:.0f}\"  "
                  f"({w.get('startX',0):.1f},{w.get('startY',0):.1f}) → "
                  f"({w.get('endX',0):.1f},{w.get('endY',0):.1f}){opening_str}")

    # List doors
    doors = analysis.get("doors", [])
    if doors:
        print(f"\nDoors ({len(doors)}):")
        for i, d in enumerate(doors):
            print(f"  {i+1:2d}. {d.get('widthInches', 0):.0f}\" wide at "
                  f"({d.get('centerX', 0):.1f}, {d.get('centerY', 0):.1f})"
                  f"  wall: {d.get('wallOrientation', '?')}")

    # List windows
    windows = analysis.get("windows", [])
    if windows:
        print(f"\nWindows ({len(windows)}):")
        for i, w in enumerate(windows):
            pos = w.get("position", {})
            print(f"  {i+1:2d}. {w.get('widthInches', 0):.0f}\" wide at "
                  f"({pos.get('x', 0):.1f}, {pos.get('y', 0):.1f})"
                  f"  wall: {w.get('wallOrientation', '?')}")

    # Door/window → wall matching preview
    all_walls = ext_walls + int_walls
    if doors and all_walls:
        door_matches = _match_doors_to_walls(doors, all_walls)
        print(f"\nDoor → Wall Matching:")
        print(f"  Matched: {len(door_matches)}/{len(doors)} "
              f"({100 * len(door_matches) / len(doors):.0f}%)")
        for di, wi, dist in door_matches:
            d = doors[di]
            w = all_walls[wi]
            print(f"    Door {di+1} → Wall {wi+1} ({w.get('orientation','?')}, "
                  f"{w.get('length',0):.1f}ft) dist={dist:.2f}ft")

    if windows and all_walls:
        window_matches = _match_windows_to_walls(windows, all_walls)
        print(f"\nWindow → Wall Matching:")
        print(f"  Matched: {len(window_matches)}/{len(windows)} "
              f"({100 * len(window_matches) / len(windows):.0f}%)")
        for wi_idx, wall_idx, dist in window_matches:
            w_elem = windows[wi_idx]
            wall = all_walls[wall_idx]
            print(f"    Window {wi_idx+1} → Wall {wall_idx+1} ({wall.get('orientation','?')}, "
                  f"{wall.get('length',0):.1f}ft) dist={dist:.2f}ft")

    print(f"\nWall Creation Parameters:")
    print(f"  Level ID: {level_id}")
    print(f"  Wall height: {height} ft")

    # Show wall type assignments
    print(f"\nWall Type Assignments:")
    for w in ext_walls:
        wt = resolve_wall_type(w.get("thicknessInches", 8), "exterior", wall_type_overrides)
        print(f"  Ext {w.get('thicknessInches', 0):.0f}\" → wallTypeId {wt['wallTypeId']}")
        break
    for w in int_walls:
        wt = resolve_wall_type(w.get("thicknessInches", 4.5), "interior", wall_type_overrides)
        print(f"  Int {w.get('thicknessInches', 0):.0f}\" → wallTypeId {wt['wallTypeId']}")
        break

    print("\n" + "=" * 70)
    total = len(ext_walls) + len(int_walls) + len(doors) + len(windows)
    print(f"TOTAL: {total} elements would be created")
    print("=" * 70)


# ============================================================================
# SAVE/LOAD ANALYSIS
# ============================================================================

def save_analysis(analysis: Dict, output_path: str):
    """Save analysis results to JSON for inspection or reuse."""
    with open(output_path, 'w') as f:
        json.dump(analysis, f, indent=2)
    print(f"\n    Analysis saved to: {output_path}")


def _convert_simple_wall_format(data: Dict) -> Dict:
    """Convert simple wall JSON (start/end arrays) to pipeline format.

    Detects the simpler format by checking for 'exterior_walls' key (snake_case
    with start/end coordinate arrays) vs pipeline's 'exteriorWalls' (camelCase
    with startX/startY/endX/endY).
    """
    def convert_walls(walls_in, default_thickness):
        out = []
        for w in walls_in:
            sx, sy = w["start"]
            ex, ey = w["end"]
            dx, dy = ex - sx, ey - sy
            length = math.hypot(dx, dy)
            orient = "H" if abs(dx) >= abs(dy) else "V"
            out.append({
                "startX": sx, "startY": sy,
                "endX": ex, "endY": ey,
                "orientation": orient,
                "length": round(length, 2),
                "thicknessInches": w.get("thicknessInches", default_thickness),
                "desc": w.get("desc", ""),
            })
        return out

    ext = convert_walls(data.get("exterior_walls", []), 8.0)
    int_ = convert_walls(data.get("interior_walls", []), 4.5)

    # Compute bounds from wall endpoints
    all_pts_x = [w["startX"] for w in ext + int_] + [w["endX"] for w in ext + int_]
    all_pts_y = [w["startY"] for w in ext + int_] + [w["endY"] for w in ext + int_]
    min_x = min(all_pts_x) if all_pts_x else 0
    max_x = max(all_pts_x) if all_pts_x else 0
    min_y = min(all_pts_y) if all_pts_y else 0
    max_y = max(all_pts_y) if all_pts_y else 0

    print(f"    Converted simple format: {len(ext)} exterior + {len(int_)} interior walls")

    return {
        "success": True,
        "exteriorWalls": ext,
        "interiorWalls": int_,
        "doors": [],
        "windows": [],
        "bounds": {
            "minX": min_x, "minY": min_y,
            "maxX": max_x, "maxY": max_y,
            "width": max_x - min_x, "height": max_y - min_y,
        },
        "summary": {
            "exteriorWallCount": len(ext),
            "interiorWallCount": len(int_),
            "doorCount": 0,
            "windowCount": 0,
        },
    }


def load_analysis(input_path: str) -> Optional[Dict]:
    """Load analysis results. Auto-converts simple wall format if detected."""
    try:
        with open(input_path, 'r') as f:
            data = json.load(f)

        # Auto-detect simple format (snake_case keys with start/end arrays)
        if "exterior_walls" in data or "interior_walls" in data:
            return _convert_simple_wall_format(data)

        return data
    except Exception as e:
        print(f"    Failed to load analysis: {e}")
        return None


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run_pipeline(input_path: str,
                 unit: str = "inch",
                 level_id: int = 30,
                 height: float = 10.0,
                 exterior_thickness: float = 8.0,
                 interior_thickness: float = 4.5,
                 tolerance: float = 2.0,
                 dry_run: bool = False,
                 skip_doors: bool = False,
                 skip_windows: bool = False,
                 save_json: Optional[str] = None,
                 load_json: Optional[str] = None,
                 exterior_type_id: Optional[int] = None,
                 interior_type_id: Optional[int] = None,
                 import_id: Optional[int] = None,
                 pdf_scale: Optional[str] = None,
                 pdf_page: int = 1,
                 building_width_ft: float = 55.0,
                 python_detect: bool = False,
                 cad_file: Optional[str] = None,
                 layer_filter: Optional[List[str]] = None,
                 dxf_reanalyze: Optional[str] = None,
                 filter_false_positives: bool = True) -> Dict:
    """
    Run the complete PDF/DXF/Image-to-Revit pipeline.

    Accepts PDF, PNG, JPG, TIFF, or DXF. Non-DXF files are automatically
    converted to DXF first using pdf_to_dxf.py.

    Args:
        input_path: Path to PDF, image, or DXF file
        unit: DXF units for Revit import ("inch", "foot", "millimeter")
        level_id: Revit level ElementId
        height: Wall height in feet
        exterior_thickness: Expected exterior wall thickness (inches)
        interior_thickness: Expected interior wall thickness (inches)
        tolerance: Line-pair matching tolerance (inches)
        dry_run: If True, analyze only — don't create elements
        skip_doors: Skip door placement
        skip_windows: Skip window placement
        save_json: Save analysis results to this path
        load_json: Load analysis from this path (skip import+analyze)
        exterior_type_id: Override exterior wall type ID
        interior_type_id: Override interior wall type ID
        import_id: Use existing import instead of importing again
        pdf_scale: Drawing scale for PDF/image conversion (e.g., "1/8")
        pdf_page: PDF page number (1-indexed)
        building_width_ft: Expected building width for auto-scale detection
        python_detect: Use Python-side wall detection instead of Revit analysis
                       (recommended for PDF inputs where Revit gets overwhelmed by noise)
        cad_file: Path to original CAD DXF for door/window detection
        layer_filter: Layer names to include when re-analyzing a DXF (e.g., ["WALLS"])
        dxf_reanalyze: Path to DXF to re-analyze with layer filtering
        filter_false_positives: Apply connectivity-based false positive filter (default True)

    Returns:
        Summary dict with results from each step
    """
    print("=" * 70)
    print("PDF/DXF/Image-to-Revit Pipeline")
    print("=" * 70)

    # Determine if we should use Python-side wall detection
    is_pdf_input = needs_conversion(input_path)
    use_python = python_detect or (is_pdf_input and not load_json)

    print(f"  Input:  {input_path}")
    print(f"  Level:  {level_id}")
    print(f"  Height: {height} ft")
    print(f"  Detect: {'Python-side' if use_python else 'Revit analyzeCADFloorPlan'}")
    print(f"  Dry run: {dry_run}")

    wall_type_overrides = {}
    if exterior_type_id:
        wall_type_overrides["exterior_id"] = exterior_type_id
    if interior_type_id:
        wall_type_overrides["interior_id"] = interior_type_id

    results = {
        "input_path": input_path,
        "steps": {},
        "success": False
    }

    analysis = None

    if load_json:
        # Load saved analysis
        print(f"\n[LOAD] Loading saved analysis from: {load_json}")
        analysis = load_analysis(load_json)
        if analysis:
            print(f"    Loaded: {len(analysis.get('exteriorWalls', []))} ext + "
                  f"{len(analysis.get('interiorWalls', []))} int walls")
        else:
            return results

    elif dxf_reanalyze:
        # DXF re-analysis mode: use layer filtering on an existing DXF
        try:
            analysis = detect_walls_from_pdf(
                input_path, page=pdf_page, scale=pdf_scale,
                building_width_ft=building_width_ft,
                dxf_reanalyze=dxf_reanalyze,
                layer_filter=layer_filter,
                filter_false_positives=filter_false_positives,
            )
        except Exception as e:
            print(f"\n  DXF re-analysis FAILED: {e}")
            results["error"] = f"DXF re-analysis failed: {e}"
            return results

        if not analysis.get("success"):
            results["error"] = "DXF re-analysis returned no results"
            return results

        results["steps"]["detect"] = {
            "method": "dxf_reanalysis",
            "layers": layer_filter,
            "exteriorWalls": len(analysis.get("exteriorWalls", [])),
            "interiorWalls": len(analysis.get("interiorWalls", [])),
        }

    elif use_python and is_pdf_input:
        # Python-side detection: PDF → walls directly (no Revit import needed for analysis)
        try:
            analysis = detect_walls_from_pdf(
                input_path, page=pdf_page, scale=pdf_scale,
                building_width_ft=building_width_ft,
                filter_false_positives=filter_false_positives,
            )
        except Exception as e:
            print(f"\n  Python detection FAILED: {e}")
            results["error"] = f"Python wall detection failed: {e}"
            return results

        if not analysis.get("success"):
            results["error"] = "Python wall detection returned no results"
            return results

        results["steps"]["detect"] = {
            "method": "python",
            "exteriorWalls": len(analysis.get("exteriorWalls", [])),
            "interiorWalls": len(analysis.get("interiorWalls", [])),
        }

        # Still convert PDF→DXF and import as underlay (for visual reference in Revit)
        if not dry_run:
            try:
                dxf_path = convert_to_dxf(
                    input_path, scale=pdf_scale,
                    page=pdf_page, building_width_ft=building_width_ft
                )
                results["dxf_path"] = dxf_path
                revit_dxf_path = to_windows_path(dxf_path)
                if step_test_connection():
                    import_id = step_import_cad(revit_dxf_path, unit)
                    if import_id:
                        results["steps"]["import"] = {"importedId": import_id}
            except Exception:
                print("    Note: DXF underlay import skipped (non-critical)")

    else:
        # Original flow: DXF → Revit import → Revit analysis
        dxf_path = input_path
        if is_pdf_input:
            ext = os.path.splitext(input_path)[1].lower()
            print(f"  Scale:  {pdf_scale or 'auto-detect'}")
            try:
                dxf_path = convert_to_dxf(
                    input_path, scale=pdf_scale,
                    page=pdf_page, building_width_ft=building_width_ft
                )
            except Exception as e:
                print(f"\n  FAILED to convert: {e}")
                results["error"] = f"PDF/image conversion failed: {e}"
                return results

        results["dxf_path"] = dxf_path
        revit_dxf_path = to_windows_path(dxf_path)
        print(f"  DXF:    {revit_dxf_path}")
        print(f"  Walls:  ext={exterior_thickness}\" / int={interior_thickness}\"")

        if not dry_run:
            if not step_test_connection():
                results["error"] = "Cannot connect to Revit MCP Bridge"
                return results

        if import_id is None:
            import_id = step_import_cad(revit_dxf_path, unit)
            if import_id is None:
                results["error"] = "DXF import failed"
                return results
        else:
            print(f"\n[STEP 1] Using existing import ID: {import_id}")

        results["steps"]["import"] = {"importedId": import_id}
        time.sleep(1)

        analysis = step_analyze_floor_plan(
            import_id, exterior_thickness, interior_thickness, tolerance
        )
        if analysis is None:
            results["error"] = "Floor plan analysis failed"
            return results

    results["steps"]["analyze"] = {
        "exteriorWalls": len(analysis.get("exteriorWalls", [])),
        "interiorWalls": len(analysis.get("interiorWalls", [])),
        "doors": len(analysis.get("doors", [])),
        "windows": len(analysis.get("windows", [])),
    }

    # Detect doors/windows from original CAD DXF if provided
    if cad_file:
        cad_result = detect_doors_from_cad(cad_file)
        if cad_result.get('success'):
            # Align CAD coordinates to PDF coordinate system
            if cad_result.get('cad_wall_bounds') and analysis.get('exteriorWalls'):
                cad_result = _align_cad_to_pdf_coords(cad_result, analysis)

            # Merge CAD doors/windows into analysis
            analysis['doors'] = cad_result['doors']
            analysis['windows'] = cad_result['windows']
            analysis['summary']['doorCount'] = len(cad_result['doors'])
            analysis['summary']['windowCount'] = len(cad_result['windows'])
            results["steps"]["cad_doors"] = {
                "doors": len(cad_result['doors']),
                "windows": len(cad_result['windows']),
                "source": cad_file,
            }

    # Save analysis if requested
    if save_json:
        save_analysis(analysis, save_json)

    # Dry run — print report and exit
    if dry_run:
        dry_run_report(analysis, level_id, height, wall_type_overrides or None)
        results["success"] = True
        results["dry_run"] = True
        return results

    # Step 3: Create walls
    wall_result = step_create_walls(
        analysis, level_id, height, wall_type_overrides or None
    )
    results["steps"]["walls"] = {
        "created": wall_result.get("createdCount", 0) if wall_result else 0,
        "failed": wall_result.get("failedCount", 0) if wall_result else 0,
    }

    # Step 3b: Match doors/windows to host walls
    wall_id_map = {}  # our_index -> revit_wallId
    if wall_result and wall_result.get("createdWalls"):
        for i, cw in enumerate(wall_result["createdWalls"]):
            wall_id_map[i] = cw["wallId"]

    all_walls = analysis.get("exteriorWalls", []) + analysis.get("interiorWalls", [])
    doors = analysis.get("doors", [])
    windows = analysis.get("windows", [])

    if doors and all_walls:
        door_matches = _match_doors_to_walls(doors, all_walls)
        for di, wi, dist in door_matches:
            if wi in wall_id_map:
                analysis["doors"][di]["hostWallId"] = wall_id_map[wi]
                analysis["doors"][di]["hostWallIndex"] = wi
        print(f"\n[STEP 3b] Matched {len(door_matches)}/{len(doors)} doors to host walls "
              f"({100 * len(door_matches) / len(doors):.0f}%)")

    if windows and all_walls:
        window_matches = _match_windows_to_walls(windows, all_walls)
        for wi_idx, wall_idx, dist in window_matches:
            if wall_idx in wall_id_map:
                analysis["windows"][wi_idx]["hostWallId"] = wall_id_map[wall_idx]
        print(f"[STEP 3b] Matched {len(window_matches)}/{len(windows)} windows to host walls "
              f"({100 * len(window_matches) / len(windows):.0f}%)")

    # Step 4a: Place doors
    if not skip_doors:
        doors_placed = step_place_doors(analysis, wall_result, level_id)
        results["steps"]["doors"] = {"placed": doors_placed}
    else:
        print("\n[STEP 4a] Skipping doors (--skip-doors)")

    # Step 4b: Place windows
    if not skip_windows:
        windows_placed = step_place_windows(analysis, wall_result, level_id)
        results["steps"]["windows"] = {"placed": windows_placed}
    else:
        print("\n[STEP 4b] Skipping windows (--skip-windows)")

    # Step 5: Zoom to fit
    step_zoom_to_fit()

    results["success"] = True

    # Final summary
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    walls_created = results["steps"].get("walls", {}).get("created", 0)
    walls_failed = results["steps"].get("walls", {}).get("failed", 0)
    doors_placed = results["steps"].get("doors", {}).get("placed", 0)
    windows_placed = results["steps"].get("windows", {}).get("placed", 0)
    print(f"  Walls created:   {walls_created} ({walls_failed} failed)")
    print(f"  Doors placed:    {doors_placed}")
    print(f"  Windows placed:  {windows_placed}")
    print("=" * 70)

    return results


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="PDF/DXF/Image-to-Revit Pipeline — Convert, import, analyze, and build floor plans",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From PDF (auto-detect scale)
  python pdf_to_revit_pipeline.py floorplan.pdf

  # From PDF with known scale
  python pdf_to_revit_pipeline.py floorplan.pdf --scale "1/8"

  # From image
  python pdf_to_revit_pipeline.py floorplan.png --scale "1/4"

  # Dry run — convert + analyze only, don't create in Revit
  python pdf_to_revit_pipeline.py floorplan.pdf --dry-run

  # From DXF directly (no conversion)
  python pdf_to_revit_pipeline.py "D:\\path\\to\\file.DXF"

  # Save analysis for later reuse
  python pdf_to_revit_pipeline.py floorplan.pdf --dry-run --save analysis.json

  # Run from saved analysis
  python pdf_to_revit_pipeline.py floorplan.pdf --load analysis.json

  # Custom wall types and level
  python pdf_to_revit_pipeline.py floorplan.pdf --level-id 30 --exterior-type 441456

  # Specify expected building size for better auto-scale
  python pdf_to_revit_pipeline.py floorplan.pdf --building-width 80

  # Use original CAD DXF for door/window detection
  python pdf_to_revit_pipeline.py floorplan.pdf --cad-file original.DXF

  # Re-analyze a PDF-converted DXF with layer filtering
  python pdf_to_revit_pipeline.py floorplan.pdf --dxf-reanalyze converted.dxf --layer-filter WALLS

  # Disable false-positive filtering
  python pdf_to_revit_pipeline.py floorplan.pdf --no-filter-fp
        """
    )

    parser.add_argument("input_file",
                        help="Input file: PDF, PNG, JPG, TIFF, or DXF")
    parser.add_argument("--scale",
                        help='Drawing scale for PDF/image (e.g., "1/8" for 1/8"=1\'-0", or direct factor like "96")')
    parser.add_argument("--page", type=int, default=1,
                        help="PDF page number, 1-indexed (default: 1)")
    parser.add_argument("--building-width", type=float, default=55.0,
                        help="Expected building width in feet for auto-scale (default: 55)")
    parser.add_argument("--unit", default="inch",
                        choices=["inch", "foot", "millimeter", "centimeter", "meter"],
                        help="DXF import units for Revit (default: inch)")
    parser.add_argument("--level-id", type=int, default=30,
                        help="Revit Level ElementId (default: 30)")
    parser.add_argument("--height", type=float, default=10.0,
                        help="Wall height in feet (default: 10)")
    parser.add_argument("--exterior-thickness", type=float, default=8.0,
                        help="Expected exterior wall thickness in inches (default: 8)")
    parser.add_argument("--interior-thickness", type=float, default=4.5,
                        help="Expected interior wall thickness in inches (default: 4.5)")
    parser.add_argument("--tolerance", type=float, default=2.0,
                        help="Line matching tolerance in inches (default: 2)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyze only, don't create elements in Revit")
    parser.add_argument("--skip-doors", action="store_true",
                        help="Skip door placement")
    parser.add_argument("--skip-windows", action="store_true",
                        help="Skip window placement")
    parser.add_argument("--save", metavar="FILE",
                        help="Save analysis results to JSON file")
    parser.add_argument("--load", metavar="FILE",
                        help="Load analysis from JSON file (skip import+analyze)")
    parser.add_argument("--exterior-type", type=int, metavar="ID",
                        help="Override exterior wall type ID")
    parser.add_argument("--interior-type", type=int, metavar="ID",
                        help="Override interior wall type ID")
    parser.add_argument("--import-id", type=int, metavar="ID",
                        help="Use existing import ElementId (skip DXF import)")
    parser.add_argument("--python-detect", action="store_true",
                        help="Use Python-side wall detection instead of Revit analysis "
                             "(recommended for PDF inputs)")
    parser.add_argument("--no-python-detect", action="store_true",
                        help="Force Revit-side analysis even for PDF inputs")
    parser.add_argument("--cad-file", metavar="FILE",
                        help="Original CAD DXF for door/window detection "
                             "(arcs=doors, text tags=sizes)")
    parser.add_argument("--layer-filter", metavar="LAYERS",
                        help="Comma-separated layer names to include when re-analyzing "
                             "a DXF (e.g., 'WALLS' to skip CURVES and WALLS-RECT)")
    parser.add_argument("--dxf-reanalyze", metavar="FILE",
                        help="Re-analyze an existing DXF with layer filtering "
                             "(instead of extracting from PDF)")
    parser.add_argument("--no-filter-fp", action="store_true",
                        help="Disable false-positive filtering "
                             "(connectivity check, cluster removal)")

    args = parser.parse_args()

    # Python detection is default for PDF inputs unless --no-python-detect
    python_detect = args.python_detect
    if args.no_python_detect:
        python_detect = False

    # Parse layer filter
    layer_filter = None
    if args.layer_filter:
        layer_filter = [l.strip() for l in args.layer_filter.split(',')]

    results = run_pipeline(
        input_path=args.input_file,
        unit=args.unit,
        level_id=args.level_id,
        height=args.height,
        exterior_thickness=args.exterior_thickness,
        interior_thickness=args.interior_thickness,
        tolerance=args.tolerance,
        dry_run=args.dry_run,
        skip_doors=args.skip_doors,
        skip_windows=args.skip_windows,
        save_json=args.save,
        load_json=args.load,
        exterior_type_id=args.exterior_type,
        interior_type_id=args.interior_type,
        import_id=args.import_id,
        pdf_scale=args.scale,
        pdf_page=args.page,
        building_width_ft=args.building_width,
        python_detect=python_detect,
        cad_file=args.cad_file,
        layer_filter=layer_filter,
        dxf_reanalyze=args.dxf_reanalyze,
        filter_false_positives=not args.no_filter_fp,
    )

    if not results["success"]:
        print(f"\nPipeline failed: {results.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
