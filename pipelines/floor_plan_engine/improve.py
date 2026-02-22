"""
Auto-improvement engine for floor plans.

Reads a FloorPlanAnalysis and applies fixes to the FloorPlan:
- Add doors to unreachable rooms
- Add egress windows to bedrooms missing them
- Fix bathroom doors facing living spaces

The reasoning engine identifies problems; this module fixes them.
"""

from typing import List, Optional, Tuple

from .models import (
    FloorPlan, RoomRect, WallSegment, DoorPlacement, WindowPlacement, RoomType,
)
from .knowledge import get_door_spec, WINDOW_RULES


def improve(plan: FloorPlan, max_iterations: int = 3,
            verbose: bool = False) -> Tuple[FloorPlan, List[str]]:
    """Run analysis → fix loop until score stabilizes or max iterations reached.

    Returns:
        (improved_plan, list_of_fixes_applied)
    """
    from .reasoning import think_through

    all_fixes = []

    for i in range(max_iterations):
        analysis = think_through(plan)

        if verbose:
            print(f"\nIteration {i + 1}: {analysis.score:.0f}/100 "
                  f"({analysis.verdict})")

        fixes = []

        # Fix 1: Add doors to unreachable rooms
        if analysis.unreachable_rooms:
            new_fixes = _fix_unreachable_rooms(plan, analysis.unreachable_rooms)
            fixes.extend(new_fixes)

        # Fix 2: Add doors to rooms that have no doors at all
        if analysis.rooms_without_doors:
            new_fixes = _fix_rooms_without_doors(
                plan, analysis.rooms_without_doors)
            fixes.extend(new_fixes)

        # Fix 3: Add egress windows to bedrooms missing them
        egress_missing = [
            issue for issue in analysis.window_issues
            if "egress" in issue.lower()
        ]
        if egress_missing:
            new_fixes = _fix_missing_egress_windows(plan)
            fixes.extend(new_fixes)

        # Fix 4: Add windows to rooms with exterior walls but no windows
        no_window_issues = [
            issue for issue in analysis.window_issues
            if "exterior wall access" in issue and "no window" in issue
        ]
        if no_window_issues:
            new_fixes = _fix_missing_windows(plan)
            fixes.extend(new_fixes)

        if not fixes:
            if verbose:
                print("  No more fixes to apply.")
            break

        all_fixes.extend(fixes)
        if verbose:
            for f in fixes:
                print(f"  FIX: {f}")

    if verbose:
        final = think_through(plan)
        print(f"\nFinal score: {final.score:.0f}/100 ({final.verdict})")
        print(f"Total fixes applied: {len(all_fixes)}")

    return plan, all_fixes


# ---------------------------------------------------------------------------
# Fix functions (mutate plan in place)
# ---------------------------------------------------------------------------

def _fix_unreachable_rooms(plan: FloorPlan,
                           unreachable: List[str]) -> List[str]:
    """Add doors to make unreachable rooms accessible."""
    fixes = []
    room_map = {r.name: r for r in plan.rooms}

    for room_name in unreachable:
        room = room_map.get(room_name)
        if not room:
            continue

        # Find a reachable neighbor that shares a wall
        best_neighbor = _find_best_neighbor_for_door(plan, room)
        if best_neighbor:
            fix = _add_door_between(plan, room, best_neighbor)
            if fix:
                fixes.append(fix)

    return fixes


def _fix_rooms_without_doors(plan: FloorPlan,
                             doorless: List[str]) -> List[str]:
    """Add doors to rooms that have no door connections."""
    fixes = []
    room_map = {r.name: r for r in plan.rooms}

    # Which rooms already have doors?
    rooms_with_doors = set()
    for d in plan.doors:
        if d.room_a and d.room_a != "exterior":
            rooms_with_doors.add(d.room_a)
        if d.room_b and d.room_b != "exterior":
            rooms_with_doors.add(d.room_b)

    for room_name in doorless:
        if room_name in rooms_with_doors:
            continue  # fixed by a previous iteration
        room = room_map.get(room_name)
        if not room:
            continue

        best_neighbor = _find_best_neighbor_for_door(plan, room)
        if best_neighbor:
            fix = _add_door_between(plan, room, best_neighbor)
            if fix:
                fixes.append(fix)
                rooms_with_doors.add(room_name)

    return fixes


def _fix_missing_egress_windows(plan: FloorPlan) -> List[str]:
    """Add egress windows to bedrooms that need them."""
    fixes = []

    rooms_with_windows = {w.room_name for w in plan.windows if w.room_name}
    egress_types = {RoomType.BEDROOM, RoomType.MASTER_BEDROOM}

    for room in plan.rooms:
        if room.room_type not in egress_types:
            continue
        if room.name in rooms_with_windows:
            continue

        fix = _add_window_to_room(plan, room)
        if fix:
            fixes.append(fix)
            rooms_with_windows.add(room.name)

    return fixes


def _fix_missing_windows(plan: FloorPlan) -> List[str]:
    """Add windows to rooms that have exterior wall access but no windows."""
    fixes = []

    rooms_with_windows = {w.room_name for w in plan.windows if w.room_name}
    # Room types that don't need windows
    skip_types = {RoomType.CLOSET, RoomType.WALK_IN_CLOSET, RoomType.PANTRY,
                  RoomType.LAUNDRY, RoomType.HALLWAY, RoomType.GARAGE}

    for room in plan.rooms:
        if room.room_type in skip_types:
            continue
        if room.name in rooms_with_windows:
            continue
        if not WINDOW_RULES.get(room.room_type):
            continue

        fix = _add_window_to_room(plan, room)
        if fix:
            fixes.append(fix)
            rooms_with_windows.add(room.name)

    return fixes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_best_neighbor_for_door(
    plan: FloorPlan, room: RoomRect
) -> Optional[RoomRect]:
    """Find the best adjacent room to connect with a door.

    Prefers: hallways > entry > connected rooms > any adjacent room.
    """
    # Find rooms that share an edge
    neighbors = []
    for other in plan.rooms:
        if other.name == room.name:
            continue
        edge = room.shares_edge_with(other)
        if edge:
            neighbors.append(other)

    if not neighbors:
        return None

    # Score neighbors by preference
    def neighbor_score(n: RoomRect) -> int:
        if n.room_type == RoomType.HALLWAY:
            return 100
        if n.room_type == RoomType.ENTRY:
            return 90
        # Prefer rooms that already have doors (they're reachable)
        has_door = any(
            d.room_a == n.name or d.room_b == n.name
            for d in plan.doors
        )
        if has_door:
            return 50
        return 10

    return max(neighbors, key=neighbor_score)


def _add_door_between(plan: FloorPlan, room_a: RoomRect,
                      room_b: RoomRect) -> Optional[str]:
    """Add a door at the midpoint of the shared edge between two rooms."""
    seg = room_a.shared_edge_segment(room_b)
    if seg is None:
        return None

    (x1, y1), (x2, y2) = seg
    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2

    # Find the wall segment at this location
    wall = _find_wall_at(plan, mid_x, mid_y)
    if wall is None:
        wall = WallSegment(x1, y1, x2, y2, is_exterior=False)

    w_in, h_in = get_door_spec(room_a.room_type)

    plan.doors.append(DoorPlacement(
        location=(mid_x, mid_y),
        wall_segment=wall,
        width_inches=w_in,
        height_inches=h_in,
        room_a=room_a.name,
        room_b=room_b.name,
    ))

    return (f"Added door between {room_a.name} and {room_b.name} "
            f"at ({mid_x:.1f}, {mid_y:.1f})")


def _add_window_to_room(plan: FloorPlan,
                        room: RoomRect) -> Optional[str]:
    """Add a window on the best exterior wall of a room."""
    tol = 0.5
    fp_w = plan.footprint_width
    fp_h = plan.footprint_height

    # Find which sides are exterior
    candidates = []
    polygon = plan.footprint_polygon if plan.footprint_polygon else None
    if polygon:
        from .wall_utils import is_on_polygon_edge
        if is_on_polygon_edge(room.x, room.y, room.right, room.y, polygon, tol):
            candidates.append(("south", room.cx, room.y, room.w))
        if is_on_polygon_edge(room.x, room.top, room.right, room.top, polygon, tol):
            candidates.append(("north", room.cx, room.top, room.w))
        if is_on_polygon_edge(room.x, room.y, room.x, room.top, polygon, tol):
            candidates.append(("west", room.x, room.cy, room.h))
        if is_on_polygon_edge(room.right, room.y, room.right, room.top, polygon, tol):
            candidates.append(("east", room.right, room.cy, room.h))
    else:
        if room.y <= tol:  # south
            candidates.append(("south", room.cx, 0.0, room.w))
        if abs(room.top - fp_h) <= tol:  # north
            candidates.append(("north", room.cx, fp_h, room.w))
        if room.x <= tol:  # west
            candidates.append(("west", 0.0, room.cy, room.h))
        if abs(room.right - fp_w) <= tol:  # east
            candidates.append(("east", fp_w, room.cy, room.h))

    if not candidates:
        return None

    # Pick the longest exterior wall for the window
    side, wx, wy, length = max(candidates, key=lambda c: c[3])

    # Find the wall segment
    wall = _find_wall_at(plan, wx, wy)
    if wall is None:
        if side in ("south", "north"):
            wall = WallSegment(room.x, wy, room.right, wy, is_exterior=True)
        else:
            wall = WallSegment(wx, room.y, wx, room.top, is_exterior=True)

    # Window specs from rules
    rule = WINDOW_RULES.get(room.room_type, {})
    sill = rule.get("sill_height", 36)
    needs_egress = rule.get("needs_egress", False)
    win_width = 36 if not needs_egress else 24  # egress: 24" min clear
    win_height = 48 if not needs_egress else 44  # egress: 24" min height

    plan.windows.append(WindowPlacement(
        location=(wx, wy),
        wall_segment=wall,
        width_inches=win_width,
        height_inches=win_height,
        sill_height_inches=sill,
        room_name=room.name,
    ))

    return f"Added {side} window to {room.name} at ({wx:.1f}, {wy:.1f})"


def _find_wall_at(plan: FloorPlan, x: float, y: float,
                  max_dist: float = 1.0) -> Optional[WallSegment]:
    """Find nearest wall to a point."""
    best = None
    best_dist = max_dist

    for wall in plan.walls:
        dx, dy = wall.x2 - wall.x1, wall.y2 - wall.y1
        length_sq = dx * dx + dy * dy

        if length_sq < 0.001:
            dist = ((x - wall.x1) ** 2 + (y - wall.y1) ** 2) ** 0.5
        else:
            t = max(0, min(1, ((x - wall.x1) * dx + (y - wall.y1) * dy)
                          / length_sq))
            px = wall.x1 + t * dx
            py = wall.y1 + t * dy
            dist = ((x - px) ** 2 + (y - py) ** 2) ** 0.5

        if dist < best_dist:
            best_dist = dist
            best = wall

    return best
