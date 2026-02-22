"""
Wall geometry utilities for FloorPlanEngine.

Functions:
- merge_collinear_walls: Merge fragmented wall segments into continuous walls
- is_on_polygon_edge: Check if a segment lies on a polygon edge
"""

from typing import List, Tuple

from .models import WallSegment


def is_on_polygon_edge(x1: float, y1: float, x2: float, y2: float,
                       polygon: List[Tuple[float, float]],
                       tol: float = 0.25) -> bool:
    """Check if segment (x1,y1)→(x2,y2) lies on any edge of the polygon.

    The segment must be collinear with a polygon edge AND its span must
    overlap with that edge's span. Checks both endpoints of the segment
    against each polygon edge.
    """
    if not polygon:
        return False

    n = len(polygon)
    for i in range(n):
        px1, py1 = polygon[i]
        px2, py2 = polygon[(i + 1) % n]

        # Both segments must be on the same line (collinear)
        # Check if the test segment is collinear with this polygon edge

        # Horizontal edge check
        if abs(py1 - py2) < tol and abs(y1 - y2) < tol and abs(y1 - py1) < tol:
            # Both horizontal at same y — check span overlap
            edge_lo = min(px1, px2)
            edge_hi = max(px1, px2)
            seg_lo = min(x1, x2)
            seg_hi = max(x1, x2)
            if seg_lo >= edge_lo - tol and seg_hi <= edge_hi + tol:
                return True

        # Vertical edge check
        if abs(px1 - px2) < tol and abs(x1 - x2) < tol and abs(x1 - px1) < tol:
            # Both vertical at same x — check span overlap
            edge_lo = min(py1, py2)
            edge_hi = max(py1, py2)
            seg_lo = min(y1, y2)
            seg_hi = max(y1, y2)
            if seg_lo >= edge_lo - tol and seg_hi <= edge_hi + tol:
                return True

    return False


def merge_collinear_walls(walls: List[WallSegment],
                          tol: float = 0.5) -> List[WallSegment]:
    """Merge collinear, overlapping/adjacent wall segments.

    Groups walls by orientation (horizontal/vertical) and coordinate line,
    then merges overlapping or adjacent segments within each group.

    Args:
        walls: List of WallSegments to merge
        tol: Tolerance for coordinate matching and gap detection

    Returns:
        New list of merged WallSegments
    """
    if not walls:
        return []

    horizontal = []  # (y, x_lo, x_hi, is_exterior, height)
    vertical = []    # (x, y_lo, y_hi, is_exterior, height)
    other = []       # non-axis-aligned walls pass through unchanged

    for w in walls:
        if w.is_horizontal:
            x_lo = min(w.x1, w.x2)
            x_hi = max(w.x1, w.x2)
            horizontal.append((round(w.y1, 1), x_lo, x_hi,
                               w.is_exterior, w.height))
        elif w.is_vertical:
            y_lo = min(w.y1, w.y2)
            y_hi = max(w.y1, w.y2)
            vertical.append((round(w.x1, 1), y_lo, y_hi,
                             w.is_exterior, w.height))
        else:
            other.append(w)

    result = list(other)

    # Merge horizontal groups (grouped by y coordinate)
    result.extend(_merge_group_horizontal(horizontal, tol))

    # Merge vertical groups (grouped by x coordinate)
    result.extend(_merge_group_vertical(vertical, tol))

    return result


def _merge_group_horizontal(
    segments: List[tuple], tol: float
) -> List[WallSegment]:
    """Merge horizontal segments grouped by y-coordinate."""
    if not segments:
        return []

    # Group by rounded y
    groups = {}
    for y, x_lo, x_hi, is_ext, height in segments:
        key = round(y / tol) * tol
        groups.setdefault(key, []).append((x_lo, x_hi, is_ext, height))

    result = []
    for y_key, segs in groups.items():
        # Sort by start position
        segs.sort(key=lambda s: s[0])
        merged = _merge_spans(segs, tol)
        for x_lo, x_hi, is_ext, height in merged:
            result.append(WallSegment(
                x_lo, y_key, x_hi, y_key,
                is_exterior=is_ext, height=height,
            ))

    return result


def _merge_group_vertical(
    segments: List[tuple], tol: float
) -> List[WallSegment]:
    """Merge vertical segments grouped by x-coordinate."""
    if not segments:
        return []

    # Group by rounded x
    groups = {}
    for x, y_lo, y_hi, is_ext, height in segments:
        key = round(x / tol) * tol
        groups.setdefault(key, []).append((y_lo, y_hi, is_ext, height))

    result = []
    for x_key, segs in groups.items():
        segs.sort(key=lambda s: s[0])
        merged = _merge_spans(segs, tol)
        for y_lo, y_hi, is_ext, height in merged:
            result.append(WallSegment(
                x_key, y_lo, x_key, y_hi,
                is_exterior=is_ext, height=height,
            ))

    return result


def _merge_spans(
    spans: List[tuple], tol: float
) -> List[tuple]:
    """Merge sorted (lo, hi, is_ext, height) spans where gap < tol.

    is_exterior: exterior wins if mixed.
    height: max height wins.
    """
    if not spans:
        return []

    merged = []
    cur_lo, cur_hi, cur_ext, cur_h = spans[0]

    for lo, hi, is_ext, height in spans[1:]:
        if lo <= cur_hi + tol:
            # Overlapping or adjacent — merge
            cur_hi = max(cur_hi, hi)
            cur_ext = cur_ext or is_ext  # exterior wins
            cur_h = max(cur_h, height)
        else:
            # Gap too big — emit current, start new
            merged.append((cur_lo, cur_hi, cur_ext, cur_h))
            cur_lo, cur_hi, cur_ext, cur_h = lo, hi, is_ext, height

    merged.append((cur_lo, cur_hi, cur_ext, cur_h))
    return merged
