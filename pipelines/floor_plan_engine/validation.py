"""
Validation checks for generated floor plans.

Checks for:
- Overlapping rooms
- Rooms outside footprint
- Aspect ratio violations
- Adjacency quality
- Minimum dimension violations
"""

from typing import List, Dict, Any

from .models import RoomRect, FloorPlan
from .knowledge import (
    ASPECT_RATIOS, MIN_DIMENSIONS, adjacency_weight,
)


def check_overlaps(rooms: List[RoomRect], tol: float = 0.1) -> List[Dict[str, Any]]:
    """Check for overlapping rooms. Returns list of violations."""
    violations = []
    for i, a in enumerate(rooms):
        for j, b in enumerate(rooms):
            if j <= i:
                continue
            # Check AABB overlap
            overlap_x = min(a.right, b.right) - max(a.x, b.x)
            overlap_y = min(a.top, b.top) - max(a.y, b.y)
            if overlap_x > tol and overlap_y > tol:
                violations.append({
                    "type": "overlap",
                    "severity": "error",
                    "rooms": [a.name, b.name],
                    "overlap_area": round(overlap_x * overlap_y, 1),
                    "message": f"'{a.name}' and '{b.name}' overlap by {overlap_x:.1f}' x {overlap_y:.1f}'",
                })
    return violations


def check_bounds(rooms: List[RoomRect], width: float, height: float, tol: float = 0.5) -> List[Dict[str, Any]]:
    """Check rooms are within footprint bounds."""
    violations = []
    for room in rooms:
        issues = []
        if room.x < -tol:
            issues.append(f"left edge at {room.x:.1f}' (min 0)")
        if room.y < -tol:
            issues.append(f"bottom edge at {room.y:.1f}' (min 0)")
        if room.right > width + tol:
            issues.append(f"right edge at {room.right:.1f}' (max {width})")
        if room.top > height + tol:
            issues.append(f"top edge at {room.top:.1f}' (max {height})")
        if issues:
            violations.append({
                "type": "out_of_bounds",
                "severity": "error",
                "room": room.name,
                "message": f"'{room.name}' out of bounds: {'; '.join(issues)}",
            })
    return violations


def check_aspect_ratios(rooms: List[RoomRect]) -> List[Dict[str, Any]]:
    """Check aspect ratios against knowledge constraints."""
    from .models import RoomType, Zone
    violations = []
    for room in rooms:
        # Skip hallways — they are naturally elongated
        if room.room_type == RoomType.HALLWAY or room.zone == Zone.CIRCULATION:
            continue
        limits = ASPECT_RATIOS.get(room.room_type)
        if limits is None:
            continue
        _, max_aspect = limits
        actual = room.aspect_ratio
        if actual > max_aspect + 0.3:  # small tolerance
            violations.append({
                "type": "aspect_ratio",
                "severity": "warning",
                "room": room.name,
                "actual": round(actual, 2),
                "max": max_aspect,
                "message": f"'{room.name}' aspect ratio {actual:.1f} exceeds max {max_aspect}",
            })
    return violations


def check_min_dimensions(rooms: List[RoomRect]) -> List[Dict[str, Any]]:
    """Check rooms meet minimum dimension requirements."""
    violations = []
    for room in rooms:
        mins = MIN_DIMENSIONS.get(room.room_type)
        if mins is None:
            continue
        min_w, min_h = mins
        short_side = min(room.w, room.h)
        if short_side < min_w - 0.5:  # 6" tolerance
            violations.append({
                "type": "min_dimension",
                "severity": "warning",
                "room": room.name,
                "actual": round(short_side, 1),
                "required": min_w,
                "message": f"'{room.name}' short side {short_side:.1f}' below minimum {min_w}'",
            })
    return violations


def check_adjacency_quality(rooms: List[RoomRect]) -> Dict[str, Any]:
    """Score the adjacency quality of the layout.

    Returns score (0-100) and list of adjacency issues.
    """
    issues = []
    total_weight = 0
    achieved_weight = 0

    for i, a in enumerate(rooms):
        for j, b in enumerate(rooms):
            if j <= i:
                continue
            weight = adjacency_weight(a.room_type, b.room_type)
            if weight == 0:
                continue

            are_adjacent = a.shares_edge_with(b) is not None
            abs_weight = abs(weight)
            total_weight += abs_weight

            if weight > 0:
                # Should be adjacent
                if are_adjacent:
                    achieved_weight += abs_weight
                elif weight >= 2:
                    issues.append({
                        "type": "adjacency_missing",
                        "severity": "warning",
                        "rooms": [a.name, b.name],
                        "weight": weight,
                        "message": f"'{a.name}' and '{b.name}' should be adjacent (weight={weight})",
                    })
            else:
                # Should not be adjacent
                if not are_adjacent:
                    achieved_weight += abs_weight
                elif weight <= -2:
                    issues.append({
                        "type": "adjacency_conflict",
                        "severity": "warning",
                        "rooms": [a.name, b.name],
                        "weight": weight,
                        "message": f"'{a.name}' and '{b.name}' should NOT be adjacent (weight={weight})",
                    })

    score = (achieved_weight / total_weight * 100) if total_weight > 0 else 100

    return {
        "score": round(score, 1),
        "total_weight": total_weight,
        "achieved_weight": achieved_weight,
        "issues": issues,
    }


def check_coverage(rooms: List[RoomRect], width: float, height: float) -> Dict[str, Any]:
    """Check how much of the footprint is covered by rooms."""
    total_footprint = width * height
    total_rooms = sum(r.area for r in rooms)
    coverage = total_rooms / total_footprint if total_footprint > 0 else 0

    return {
        "footprint_area": round(total_footprint, 1),
        "rooms_area": round(total_rooms, 1),
        "coverage_pct": round(coverage * 100, 1),
        "gap_area": round(total_footprint - total_rooms, 1),
    }


def validate_floor_plan(plan: FloorPlan) -> Dict[str, Any]:
    """Run all validation checks on a floor plan.

    Returns:
        {
            "valid": bool,
            "errors": [...],
            "warnings": [...],
            "adjacency_score": float,
            "coverage": {...},
            "summary": str,
        }
    """
    errors = []
    warnings = []

    # Overlap check
    overlap_violations = check_overlaps(plan.rooms)
    errors.extend(overlap_violations)

    # Bounds check
    bounds_violations = check_bounds(plan.rooms, plan.footprint_width, plan.footprint_height)
    errors.extend(bounds_violations)

    # Aspect ratio check
    aspect_violations = check_aspect_ratios(plan.rooms)
    warnings.extend(aspect_violations)

    # Min dimension check
    dim_violations = check_min_dimensions(plan.rooms)
    warnings.extend(dim_violations)

    # Adjacency quality
    adj_result = check_adjacency_quality(plan.rooms)
    warnings.extend(adj_result["issues"])

    # Coverage
    coverage = check_coverage(plan.rooms, plan.footprint_width, plan.footprint_height)

    valid = len(errors) == 0

    # Build summary
    parts = []
    if valid:
        parts.append("VALID")
    else:
        parts.append(f"INVALID ({len(errors)} errors)")
    parts.append(f"adj={adj_result['score']:.0f}%")
    parts.append(f"coverage={coverage['coverage_pct']:.0f}%")
    if warnings:
        parts.append(f"{len(warnings)} warnings")

    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "adjacency_score": adj_result["score"],
        "coverage": coverage,
        "summary": " | ".join(parts),
    }
