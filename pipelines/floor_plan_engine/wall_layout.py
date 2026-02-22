"""
Text-to-Plan Pipeline: Description → WallPlan generation.

v2: Room Templates + Purposeful Placement

Algorithm:
1. Classify rooms into architectural clusters
2. Select room dimensions from ROOM_TEMPLATES (standard architect sizes)
3. Place rooms in grid layout (private=north, public=south, hallway spine)
4. Place doors near corners (furniture wall rule) or with privacy positioning
5. Place windows opposite doors (light draws you in)
6. Validate and repair

Key differences from v1:
- Fixed room dimensions from templates (not proportional strip packing)
- Doors near corners (not midpoint)
- Windows opposite door wall (not evenly spaced on any exterior)
- Kitchen windows at 42" sill, bathroom windows 2ft wide at 48" sill
"""

import math
from typing import List, Optional, Dict, Any, Tuple

from .models import RoomType, Zone, RoomSpec
from .wall_model import Wall, Opening, RoomLabel, WallPlan
from .knowledge import (
    ZONE_MAP, OPEN_PLAN_GROUPS, WINDOW_RULES, DOOR_SPECS,
    ASPECT_RATIOS, MIN_DIMENSIONS, adjacency_weight, get_door_spec,
)
from .program import extract_program, determine_tier

# Type alias for room cells: (x, y, width, height, RoomSpec)
Cell = Tuple[float, float, float, float, RoomSpec]

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

HALLWAY_WIDTH = 4.0       # feet
BATH_COLUMN_WIDTH = 8.0   # feet (L-shape)
MIN_ZONE_DEPTH = 8.0      # minimum depth for any zone band
GRID = 0.5                # snap grid in feet


def _snap(v: float) -> float:
    """Snap value to half-foot grid."""
    return round(v / GRID) * GRID


class _IdGen:
    """Sequential ID generator for walls, doors, windows."""
    def __init__(self, prefix: str):
        self._prefix = prefix
        self._n = 0

    def __call__(self) -> str:
        self._n += 1
        return f"{self._prefix}{self._n}"


# ══════════════════════════════════════════════════════════════════════════════
# ROOM TEMPLATES — Standard architect dimensions (width x depth in feet)
# ══════════════════════════════════════════════════════════════════════════════
# width = hallway-facing side, depth = perpendicular to hallway

ROOM_TEMPLATES: Dict[Tuple[RoomType, str], Tuple[float, float]] = {
    (RoomType.MASTER_BEDROOM, "small"):  (12, 14),
    (RoomType.MASTER_BEDROOM, "medium"): (14, 16),
    (RoomType.MASTER_BEDROOM, "large"):  (16, 18),
    (RoomType.BEDROOM, "small"):         (10, 11),
    (RoomType.BEDROOM, "medium"):        (11, 12),
    (RoomType.BEDROOM, "large"):         (12, 14),
    (RoomType.MASTER_BATH, "small"):     (5, 8),
    (RoomType.MASTER_BATH, "medium"):    (8, 10),
    (RoomType.MASTER_BATH, "large"):     (10, 12),
    (RoomType.BATHROOM, "small"):        (5, 8),
    (RoomType.BATHROOM, "medium"):       (5, 9),
    (RoomType.BATHROOM, "large"):        (7, 9),
    (RoomType.HALF_BATH, "small"):       (3, 6),
    (RoomType.HALF_BATH, "medium"):      (4, 6),
    (RoomType.HALF_BATH, "large"):       (5, 7),
    (RoomType.WALK_IN_CLOSET, "small"):  (5, 6),
    (RoomType.WALK_IN_CLOSET, "medium"): (6, 8),
    (RoomType.WALK_IN_CLOSET, "large"):  (8, 8),
    (RoomType.LAUNDRY, "small"):         (5, 7),
    (RoomType.LAUNDRY, "medium"):        (6, 8),
    (RoomType.LAUNDRY, "large"):         (7, 9),
    (RoomType.PANTRY, "small"):          (3, 5),
    (RoomType.PANTRY, "medium"):         (4, 6),
    (RoomType.PANTRY, "large"):          (5, 8),
    (RoomType.ENTRY, "small"):           (5, 5),
    (RoomType.ENTRY, "medium"):          (6, 7),
    (RoomType.ENTRY, "large"):           (7, 8),
    (RoomType.OFFICE, "small"):          (9, 10),
    (RoomType.OFFICE, "medium"):         (10, 12),
    (RoomType.OFFICE, "large"):          (12, 14),
}

# ══════════════════════════════════════════════════════════════════════════════
# DOOR PLACEMENT RULES
# ══════════════════════════════════════════════════════════════════════════════
# "near_corner": door 1ft from corner, leaves furniture wall
# "center": door centered on wall
# "privacy": door 1ft from near corner, hides toilet behind swing

DOOR_RULES: Dict[RoomType, Dict[str, str]] = {
    RoomType.MASTER_BEDROOM: {"position": "near_corner"},
    RoomType.BEDROOM:        {"position": "near_corner"},
    RoomType.MASTER_BATH:    {"position": "privacy"},
    RoomType.BATHROOM:       {"position": "privacy"},
    RoomType.HALF_BATH:      {"position": "privacy"},
    RoomType.WALK_IN_CLOSET: {"position": "near_corner"},
    RoomType.LAUNDRY:        {"position": "center"},
    RoomType.PANTRY:         {"position": "center"},
    RoomType.OFFICE:         {"position": "near_corner"},
}

# ══════════════════════════════════════════════════════════════════════════════
# WINDOW PLACEMENT RULES
# ══════════════════════════════════════════════════════════════════════════════
# preferred_wall: which wall gets the window
# position: where on that wall
# count: base window count (scaled by glazing ratio)

WINDOW_PLACEMENT: Dict[RoomType, Dict[str, Any]] = {
    RoomType.LIVING:         {"preferred_wall": "exterior", "position": "centered", "count": 2},
    RoomType.KITCHEN:        {"preferred_wall": "exterior", "position": "above_counter", "count": 1},
    RoomType.DINING:         {"preferred_wall": "exterior", "position": "centered", "count": 1},
    RoomType.MASTER_BEDROOM: {"preferred_wall": "opposite_door", "position": "centered", "count": 2},
    RoomType.BEDROOM:        {"preferred_wall": "opposite_door", "position": "centered", "count": 1},
    RoomType.MASTER_BATH:    {"preferred_wall": "exterior", "position": "high_privacy", "count": 1},
    RoomType.BATHROOM:       {"preferred_wall": "exterior", "position": "high_privacy", "count": 1},
    RoomType.OFFICE:         {"preferred_wall": "exterior", "position": "centered", "count": 1},
    RoomType.FAMILY_ROOM:    {"preferred_wall": "exterior", "position": "centered", "count": 2},
}


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1: CLUSTER CLASSIFICATION (unchanged from v1)
# ══════════════════════════════════════════════════════════════════════════════

def _classify_into_clusters(
    rooms: List[RoomSpec], tier: str,
) -> Dict[str, List[RoomSpec]]:
    """Group rooms into architectural clusters."""
    clusters: Dict[str, List[RoomSpec]] = {
        "open_plan": [],
        "master_suite": [],
        "bedroom_wing": [],
        "service": [],
        "entry": [],
        "overflow": [],
    }

    for room in rooms:
        rt = room.room_type
        if rt in (RoomType.LIVING, RoomType.KITCHEN, RoomType.DINING):
            clusters["open_plan"].append(room)
        elif rt in (RoomType.MASTER_BEDROOM, RoomType.MASTER_BATH,
                    RoomType.WALK_IN_CLOSET):
            clusters["master_suite"].append(room)
        elif rt in (RoomType.BEDROOM, RoomType.BATHROOM):
            clusters["bedroom_wing"].append(room)
        elif rt in (RoomType.HALF_BATH, RoomType.LAUNDRY, RoomType.PANTRY):
            clusters["service"].append(room)
        elif rt == RoomType.ENTRY:
            clusters["entry"].append(room)
        elif rt == RoomType.HALLWAY:
            clusters["bedroom_wing"].append(room)
        else:  # OFFICE, FAMILY_ROOM, CLOSET, GARAGE
            clusters["overflow"].append(room)

    # If bedroom wing has no actual bedrooms, merge baths into master suite
    if clusters["bedroom_wing"] and not any(
        r.room_type == RoomType.BEDROOM for r in clusters["bedroom_wing"]
    ):
        clusters["master_suite"].extend(clusters["bedroom_wing"])
        clusters["bedroom_wing"] = []

    return clusters


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS (mostly unchanged)
# ══════════════════════════════════════════════════════════════════════════════

def _is_open_plan(room_a: RoomSpec, room_b: RoomSpec) -> bool:
    """Check if two rooms should be open-plan (no wall between)."""
    for group in OPEN_PLAN_GROUPS:
        if room_a.room_type in group and room_b.room_type in group:
            return True
    return False


def _cells_share_edge(a: Cell, b: Cell, tol: float = 0.5) -> bool:
    """Check if two cells share an edge."""
    ax, ay, aw, ah, _ = a
    bx, by, bw, bh, _ = b

    # Vertical shared edge
    if abs((ax + aw) - bx) < tol or abs((bx + bw) - ax) < tol:
        overlap_y = min(ay + ah, by + bh) - max(ay, by)
        if overlap_y > tol:
            return True

    # Horizontal shared edge
    if abs((ay + ah) - by) < tol or abs((by + bh) - ay) < tol:
        overlap_x = min(ax + aw, bx + bw) - max(ax, bx)
        if overlap_x > tol:
            return True

    return False


def _find_cell_at(cells: List[Cell], x: float, y: float) -> Optional[Cell]:
    """Find cell containing point (x, y)."""
    for cell in cells:
        cx, cy, cw, ch, _ = cell
        if cx - 0.1 <= x <= cx + cw + 0.1 and cy - 0.1 <= y <= cy + ch + 0.1:
            return cell
    return None


def _cell_touches_exterior(
    cell: Cell, W: float, H: float, tol: float = 0.5,
) -> bool:
    """Check if cell touches any exterior boundary."""
    x, y, w, h, _ = cell
    return (x < tol or y < tol or
            abs(x + w - W) < tol or abs(y + h - H) < tol)


def _get_room_dims(
    room_type: RoomType, tier: str,
    available_w: float, available_h: float,
) -> Tuple[float, float]:
    """Get room dimensions from ROOM_TEMPLATES, clamped to available space.

    Returns (width, depth) from templates, or falls back to MIN_DIMENSIONS.
    """
    key = (room_type, tier)
    if key in ROOM_TEMPLATES:
        tw, td = ROOM_TEMPLATES[key]
    else:
        # Fallback: try medium tier, then use MIN_DIMENSIONS
        key_med = (room_type, "medium")
        if key_med in ROOM_TEMPLATES:
            tw, td = ROOM_TEMPLATES[key_med]
        else:
            dims = MIN_DIMENSIONS.get(room_type, (8, 8))
            tw, td = float(dims[0]), float(dims[1])

    # Clamp to available space
    tw = min(tw, available_w)
    td = min(td, available_h)

    # Enforce minimum dimensions
    mins = MIN_DIMENSIONS.get(room_type, (4, 4))
    tw = max(tw, float(mins[0]))
    td = max(td, float(mins[1]))

    return (_snap(tw), _snap(td))


# ══════════════════════════════════════════════════════════════════════════════
# PACKING STRATEGIES
# ══════════════════════════════════════════════════════════════════════════════

def _pack_strip(
    rooms: List[RoomSpec],
    rx: float, ry: float, rw: float, rh: float,
    horizontal: bool = True,
) -> List[Cell]:
    """Pack rooms in a strip with aspect-ratio awareness.

    horizontal=True  → rooms placed left-to-right, each full height rh
    horizontal=False → rooms placed bottom-to-top, each full width rw
    """
    if not rooms:
        return []

    n = len(rooms)
    total_area = sum(r.target_area for r in rooms) or 1
    band = rh if horizontal else rw            # fixed dimension
    total_span = rw if horizontal else rh      # variable dimension

    # Step 1: proportional spans
    spans = [total_span * r.target_area / total_area for r in rooms]

    # Step 2: enforce aspect ratio + min dimension constraints
    for i, room in enumerate(rooms):
        rt = room.room_type
        _, max_a = ASPECT_RATIOS.get(rt, (1.0, 3.0))
        min_dim = MIN_DIMENSIONS.get(rt, (4, 4))
        min_span_dim = min_dim[0] if horizontal else min_dim[1]

        min_span_aspect = band / max_a if band > spans[i] else 0

        min_span = max(min_span_dim, min_span_aspect, 4.0)
        spans[i] = max(spans[i], min_span)

    # Step 3: fit within total_span
    for _ in range(5):
        excess = sum(spans) - total_span
        if excess <= 0.5:
            break
        adjustable = []
        for i, room in enumerate(rooms):
            rt = room.room_type
            _, max_a = ASPECT_RATIOS.get(rt, (1.0, 3.0))
            min_dim = MIN_DIMENSIONS.get(rt, (4, 4))
            floor = max(min_dim[0] if horizontal else min_dim[1],
                        band / max_a if band > 4 else 4, 4.0)
            headroom = spans[i] - floor
            if headroom > 0.5:
                adjustable.append((i, headroom))
        if not adjustable:
            break
        total_hr = sum(h for _, h in adjustable)
        for i, hr in adjustable:
            spans[i] -= min(hr, excess * hr / total_hr)

    # Distribute surplus if total < available
    shortfall = total_span - sum(spans)
    if shortfall > 0.5:
        for i in range(n):
            spans[i] += shortfall * (rooms[i].target_area / total_area)

    # Step 4: build cells
    cells: List[Cell] = []
    cursor = rx if horizontal else ry
    for i, room in enumerate(rooms):
        s = _snap(spans[i])
        if i == n - 1:
            s = (rx + rw if horizontal else ry + rh) - cursor
        s = max(s, 2.0)
        if horizontal:
            cells.append((cursor, ry, s, rh, room))
        else:
            cells.append((rx, cursor, rw, s, room))
        cursor += s

    return cells


def _pack_open_plan(
    rooms: List[RoomSpec],
    rx: float, ry: float, rw: float, rh: float,
) -> List[Cell]:
    """Pack open-plan rooms. Living faces entry, Kitchen on exterior."""
    if not rooms:
        return []
    priority = {
        RoomType.LIVING: 0, RoomType.DINING: 1,
        RoomType.KITCHEN: 2, RoomType.FAMILY_ROOM: 3,
    }
    rooms = sorted(rooms, key=lambda r: priority.get(r.room_type, 9))
    return _pack_strip(rooms, rx, ry, rw, rh, horizontal=(rw >= rh))


def _pack_master_suite_templates(
    rooms: List[RoomSpec],
    rx: float, ry: float, rw: float, rh: float,
    tier: str,
) -> List[Cell]:
    """Pack master suite using template dimensions.

    Layout: master bedroom on left (exterior), bath+WIC stacked on right.
    """
    if not rooms:
        return []

    beds = [r for r in rooms if r.room_type == RoomType.MASTER_BEDROOM]
    accessories = [r for r in rooms if r.room_type != RoomType.MASTER_BEDROOM]

    if not beds:
        return _pack_strip(rooms, rx, ry, rw, rh)

    if not accessories:
        return [(rx, ry, rw, rh, beds[0])]

    # Get template dimensions for master bedroom
    bed_tw, bed_td = _get_room_dims(RoomType.MASTER_BEDROOM, tier, rw, rh)

    # Bed takes left portion, accessories stack on right
    bed_w = min(bed_tw, rw * 0.7)  # never more than 70% of available
    acc_w = rw - bed_w

    # Enforce minimum accessory width
    min_acc_w = max(
        MIN_DIMENSIONS.get(r.room_type, (4, 4))[0] for r in accessories
    )
    if acc_w < min_acc_w:
        acc_w = _snap(min_acc_w)
        bed_w = rw - acc_w

    bed_w = _snap(bed_w)
    cells: List[Cell] = [(rx, ry, bed_w, rh, beds[0])]

    # Stack accessories vertically in remaining strip
    acc_cells = _pack_strip(
        accessories, rx + bed_w, ry, acc_w, rh, horizontal=False)
    cells.extend(acc_cells)

    return cells


def _pack_bedroom_wing_templates(
    rooms: List[RoomSpec],
    rx: float, ry: float, rw: float, rh: float,
    tier: str,
) -> List[Cell]:
    """Pack bedroom wing using template dimensions.

    Bedrooms placed left-to-right with template widths, bath at east end.
    """
    if not rooms:
        return []

    beds = [r for r in rooms if r.room_type == RoomType.BEDROOM]
    baths = [r for r in rooms if r.room_type == RoomType.BATHROOM]
    others = [r for r in rooms
              if r.room_type not in (
                  RoomType.BEDROOM, RoomType.BATHROOM, RoomType.HALLWAY)]

    ordered = beds + others + baths  # bath at end (near plumbing wall)
    if not ordered:
        return []

    # Get template widths for each room
    template_widths = []
    for room in ordered:
        tw, _ = _get_room_dims(room.room_type, tier, rw, rh)
        template_widths.append(tw)

    total_tw = sum(template_widths)

    # Scale if total exceeds available width
    if total_tw > rw + 0.5:
        scale = rw / total_tw
        template_widths = [w * scale for w in template_widths]
        # Enforce minimums after scaling
        for i, room in enumerate(ordered):
            mins = MIN_DIMENSIONS.get(room.room_type, (4, 4))
            template_widths[i] = max(template_widths[i], float(mins[0]))

        # If enforcing minimums made total exceed available again,
        # reduce the largest rooms (bedrooms) to compensate
        for _ in range(5):
            excess = sum(template_widths) - rw
            if excess <= 0.5:
                break
            # Find rooms with most headroom above their minimum
            adjustable = []
            for i, room in enumerate(ordered):
                mins = MIN_DIMENSIONS.get(room.room_type, (4, 4))
                headroom = template_widths[i] - float(mins[0])
                if headroom > 0.5:
                    adjustable.append((i, headroom))
            if not adjustable:
                break
            total_hr = sum(h for _, h in adjustable)
            for i, hr in adjustable:
                template_widths[i] -= min(hr, excess * hr / total_hr)

    # Build cells left to right, ensuring total fits in rw
    cells: List[Cell] = []
    cursor = rx
    remaining_min = sum(
        max(float(MIN_DIMENSIONS.get(ordered[j].room_type, (4, 4))[0]), 2.0)
        for j in range(len(ordered))
    )
    for i, room in enumerate(ordered):
        mins = MIN_DIMENSIONS.get(room.room_type, (4, 4))
        min_w = max(float(mins[0]), 2.0)
        remaining_min -= min_w

        if i == len(ordered) - 1:
            w = (rx + rw) - cursor  # last room absorbs remainder
        else:
            w = _snap(template_widths[i])
            # Clamp so remaining rooms can still meet their minimums
            max_allowed = (rx + rw) - cursor - remaining_min
            w = min(w, max_allowed)

        w = max(w, min_w)
        cells.append((cursor, ry, w, rh, room))
        cursor += w

    return cells


def _pack_service(
    rooms: List[RoomSpec],
    rx: float, ry: float, rw: float, rh: float,
) -> List[Cell]:
    """Pack service rooms: half-bath near entry, laundry near kitchen."""
    if not rooms:
        return []
    priority = {
        RoomType.HALF_BATH: 0, RoomType.LAUNDRY: 1, RoomType.PANTRY: 2,
    }
    rooms = sorted(rooms, key=lambda r: priority.get(r.room_type, 9))
    return _pack_strip(rooms, rx, ry, rw, rh, horizontal=(rw >= rh))


# ══════════════════════════════════════════════════════════════════════════════
# V3: COLUMN-BASED SPLIT PLAN HELPERS
# ══════════════════════════════════════════════════════════════════════════════

MIN_GREAT_ROOM_W = 12.0  # minimum great room width (feet)


def _stack_master_column(
    master_rooms: List[RoomSpec],
    overflow_rooms: List[RoomSpec],
    x: float, y: float, w: float, h: float,
    tier: str,
) -> List[Cell]:
    """Stack master suite rooms vertically in the west column.

    Layout (top to bottom):
      Master Bedroom (top, touches north + west exterior)
      Master Bath + WIC side-by-side
      Overflow rooms (laundry, office)
    """
    cells: List[Cell] = []
    if not master_rooms:
        return cells

    cursor = y + h  # start from top

    # Find master bedroom
    mb = next((r for r in master_rooms
               if r.room_type == RoomType.MASTER_BEDROOM), None)
    accessories = [r for r in master_rooms
                   if r.room_type != RoomType.MASTER_BEDROOM]

    if mb:
        # Master bed at top — limit to 55% of column height
        _, mb_template_h = _get_room_dims(mb.room_type, tier, w, h)
        mb_h = _snap(min(mb_template_h, h * 0.55))
        cursor -= mb_h
        cells.append((x, cursor, w, mb_h, mb))

        # Accessories row (MBath + WIC side by side)
        if accessories:
            acc_h_vals = [_get_room_dims(a.room_type, tier, w, h)[1]
                          for a in accessories]
            acc_h = _snap(max(acc_h_vals))
            # Leave at least 4ft for overflow/service below
            max_acc_h = cursor - y - 4.0 if overflow_rooms else cursor - y
            acc_h = _snap(min(acc_h, max(max_acc_h, 5.0)))
            cursor -= acc_h

            # Place side by side within the row
            acc_cursor_x = x
            total_template_w = sum(
                _get_room_dims(a.room_type, tier, w, h)[0]
                for a in accessories)
            for i, acc in enumerate(accessories):
                if i == len(accessories) - 1:
                    acc_w = (x + w) - acc_cursor_x
                else:
                    t_w = _get_room_dims(acc.room_type, tier, w, h)[0]
                    acc_w = _snap(w * t_w / max(total_template_w, 1))
                cells.append((acc_cursor_x, cursor, acc_w, acc_h, acc))
                acc_cursor_x += acc_w
    else:
        # No master bed — just stack all master rooms
        per_h = h / len(master_rooms)
        for room in master_rooms:
            room_h = _snap(per_h)
            cursor -= room_h
            cells.append((x, cursor, w, room_h, room))

    # Overflow rooms fill remaining space at bottom
    remaining = cursor - y
    if remaining > 4.0 and overflow_rooms:
        per_h = remaining / len(overflow_rooms)
        for room in overflow_rooms:
            room_h = _snap(min(per_h, remaining))
            if room_h < 4.0:
                break
            cursor -= room_h
            cells.append((x, cursor, w, room_h, room))
            remaining = cursor - y

    return cells


def _stack_bedroom_column(
    bed_rooms: List[RoomSpec],
    bath_rooms: List[RoomSpec],
    x: float, y: float, w: float, h: float,
    tier: str,
) -> List[Cell]:
    """Stack bedrooms + baths vertically in the east column.

    Layout (top to bottom):
      Bedroom 2
      Bedroom 3
      Bathroom(s)
      Half bath (if any)
    """
    cells: List[Cell] = []
    all_rooms = bed_rooms + bath_rooms
    if not all_rooms:
        return cells

    # Compute template heights for each room
    heights = [_get_room_dims(r.room_type, tier, w, h)[1] for r in all_rooms]
    total_h = sum(heights)

    # Compress proportionally if total exceeds available height
    if total_h > h + 0.5:
        scale = h / total_h
        compressed = []
        for h_i, r in zip(heights, all_rooms):
            mins = MIN_DIMENSIONS.get(r.room_type, (4, 4))
            min_h = float(mins[1]) - 1.0  # 1ft tolerance
            compressed.append(max(h_i * scale, min_h))
        # Last room absorbs remainder
        used = sum(compressed[:-1])
        compressed[-1] = h - used
        heights = compressed

    # Place top-to-bottom
    cursor = y + h
    for i, (room, room_h) in enumerate(zip(all_rooms, heights)):
        room_h = _snap(room_h)
        if i == len(all_rooms) - 1:
            room_h = cursor - y  # last room absorbs remainder
        cursor -= room_h
        cells.append((x, cursor, w, room_h, room))

    return cells


def _place_great_room(
    open_rooms: List[RoomSpec],
    x: float, y: float, w: float, h: float,
) -> List[Cell]:
    """Fill center column with open-plan rooms.

    Since open-plan rooms share one large space (no walls between them),
    each room gets the full column rectangle. The analysis layer's
    _subdivide_overlapping_rooms handles proportional subdivision.

    Rooms are ordered with distinct label centers for visual clarity:
    Kitchen at bottom, Living at top.
    """
    cells: List[Cell] = []
    if not open_rooms:
        return cells

    if len(open_rooms) == 1:
        cells.append((x, y, w, h, open_rooms[0]))
        return cells

    # All open-plan rooms share the same enclosure.
    # Use slicing along the WIDER dimension for better aspect ratios.
    # Sort: kitchen at bottom/left, living at top/right
    living = [r for r in open_rooms if r.room_type == RoomType.LIVING]
    kitchen = [r for r in open_rooms if r.room_type == RoomType.KITCHEN]
    dining = [r for r in open_rooms if r.room_type == RoomType.DINING]
    family = [r for r in open_rooms if r.room_type == RoomType.FAMILY_ROOM]
    others = [r for r in open_rooms
              if r not in living + kitchen + dining + family]

    ordered = kitchen + dining + family + living + others
    n = len(ordered)

    if w >= h:
        # Wide column: slice horizontally (left-to-right)
        slice_w = w / n
        cursor = x
        for i, room in enumerate(ordered):
            rw = _snap(slice_w) if i < n - 1 else (x + w) - cursor
            cells.append((cursor, y, rw, h, room))
            cursor += rw
    else:
        # Tall column: slice vertically (bottom-to-top)
        # Slices may be below individual min dimensions, but open-plan rooms
        # share one enclosure architecturally — analysis skips individual checks.
        slice_h = h / n
        cursor = y
        for i, room in enumerate(ordered):
            rh = _snap(slice_h) if i < n - 1 else (y + h) - cursor
            cells.append((x, cursor, w, rh, room))
            cursor += rh

    return cells


def _place_service_row(
    entry_rooms: List[RoomSpec],
    svc_rooms: List[RoomSpec],
    x: float, y: float, w: float, h: float,
    master_col_w: float,
    bedroom_col_w: float,
    tier: str,
) -> List[Cell]:
    """Place entry + hallway connector + service rooms in bottom strip.

    Layout (left to right):
      Entry (under master column)
      Hallway connector (4ft, links columns)
      Service rooms (pantry, etc.) fill remaining
    """
    cells: List[Cell] = []
    cursor_x = x

    # Layout: Entry (left) | Service rooms (right) | Hallway (center, fills gap)
    # This ensures the entire row is filled with cells (no gaps for ray-casting).

    # Compute service room widths first (capped to templates)
    svc_widths = []
    if svc_rooms:
        for room in svc_rooms:
            tw, _ = _get_room_dims(room.room_type, tier, w, h)
            svc_widths.append(_snap(tw))

    total_svc_w = sum(svc_widths)

    # Entry under master column
    if entry_rooms:
        entry = entry_rooms[0]
        entry_w = _snap(max(master_col_w, 4.0))
        cells.append((cursor_x, y, entry_w, h, entry))
        cursor_x += entry_w

    # Service rooms at the right end of the row
    svc_start_x = (x + w) - total_svc_w
    if svc_rooms:
        svc_cursor = svc_start_x
        for i, room in enumerate(svc_rooms):
            if i == len(svc_rooms) - 1:
                room_w = (x + w) - svc_cursor
            else:
                room_w = svc_widths[i]
            room_w = max(room_w, 3.0)
            cells.append((svc_cursor, y, room_w, h, room))
            svc_cursor += room_w

    # Hallway fills the gap between entry and service rooms
    hall_w = svc_start_x - cursor_x if svc_rooms else (x + w) - cursor_x
    if hall_w > 2.0:
        hall_spec = RoomSpec("Hallway", RoomType.HALLWAY,
                             hall_w * h, Zone.CIRCULATION)
        cells.append((cursor_x, y, hall_w, h, hall_spec))

    return cells


# ══════════════════════════════════════════════════════════════════════════════
# WALL PLACEMENT
# ══════════════════════════════════════════════════════════════════════════════

def _place_partition_walls(
    cells: List[Cell],
    walls: List[Wall],
    wid: _IdGen,
    wall_height: float,
    W: float, H: float,
) -> None:
    """Place interior partition walls between non-open-plan adjacent cells."""
    def _wall_covers_edge(is_vert, coord, lo, hi):
        for w in walls:
            if is_vert and w.is_vertical and abs(w.x1 - coord) < 0.5:
                wlo = min(w.y1, w.y2)
                whi = max(w.y1, w.y2)
                if wlo <= lo + 0.5 and whi >= hi - 0.5:
                    return True
            elif not is_vert and w.is_horizontal and abs(w.y1 - coord) < 0.5:
                wlo = min(w.x1, w.x2)
                whi = max(w.x1, w.x2)
                if wlo <= lo + 0.5 and whi >= hi - 0.5:
                    return True
        return False

    placed = set()

    for i, ca in enumerate(cells):
        ax, ay, aw, ah, ra = ca
        for cb in cells[i + 1:]:
            bx, by, bw, bh, rb = cb

            if _is_open_plan(ra, rb):
                continue
            if not _cells_share_edge(ca, cb):
                continue

            # Vertical shared edge
            if abs((ax + aw) - bx) < 0.5:
                edge_x = round(ax + aw, 1)
                y_lo = round(max(ay, by), 1)
                y_hi = round(min(ay + ah, by + bh), 1)
                key = ("v", edge_x, y_lo, y_hi)
                if key not in placed and not _wall_covers_edge(True, edge_x, y_lo, y_hi):
                    placed.add(key)
                    walls.append(Wall(wid(), (edge_x, y_lo), (edge_x, y_hi),
                                     "interior", 4.0, wall_height))
            elif abs((bx + bw) - ax) < 0.5:
                edge_x = round(bx + bw, 1)
                y_lo = round(max(ay, by), 1)
                y_hi = round(min(ay + ah, by + bh), 1)
                key = ("v", edge_x, y_lo, y_hi)
                if key not in placed and not _wall_covers_edge(True, edge_x, y_lo, y_hi):
                    placed.add(key)
                    walls.append(Wall(wid(), (edge_x, y_lo), (edge_x, y_hi),
                                     "interior", 4.0, wall_height))

            # Horizontal shared edge
            if abs((ay + ah) - by) < 0.5:
                edge_y = round(ay + ah, 1)
                x_lo = round(max(ax, bx), 1)
                x_hi = round(min(ax + aw, bx + bw), 1)
                key = ("h", edge_y, x_lo, x_hi)
                if key not in placed and not _wall_covers_edge(False, edge_y, x_lo, x_hi):
                    placed.add(key)
                    walls.append(Wall(wid(), (x_lo, edge_y), (x_hi, edge_y),
                                     "interior", 4.0, wall_height))
            elif abs((by + bh) - ay) < 0.5:
                edge_y = round(by + bh, 1)
                x_lo = round(max(ax, bx), 1)
                x_hi = round(min(ax + aw, bx + bw), 1)
                key = ("h", edge_y, x_lo, x_hi)
                if key not in placed and not _wall_covers_edge(False, edge_y, x_lo, x_hi):
                    placed.add(key)
                    walls.append(Wall(wid(), (x_lo, edge_y), (x_hi, edge_y),
                                     "interior", 4.0, wall_height))


# ══════════════════════════════════════════════════════════════════════════════
# PURPOSEFUL DOOR PLACEMENT (v2)
# ══════════════════════════════════════════════════════════════════════════════

def _compute_door_offset(
    wall_length: float, door_w: float, room_type: RoomType,
) -> float:
    """Compute door offset along wall using DOOR_RULES.

    Returns offset from wall start in feet.
    """
    rule = DOOR_RULES.get(room_type, {"position": "center"})
    position = rule["position"]

    if position == "near_corner":
        # Door 1ft from far corner — leaves long furniture wall
        offset = wall_length - door_w - 1.0
    elif position == "privacy":
        # Door 1ft from near corner — hides fixtures behind door swing
        offset = 1.0
    else:  # center
        offset = (wall_length - door_w) / 2.0

    # Clamp to valid range
    offset = max(0.5, min(offset, wall_length - door_w - 0.5))
    return offset


def _place_doors_v2(
    cells: List[Cell],
    walls: List[Wall],
    doors: List[Opening],
    did: _IdGen,
) -> Dict[str, str]:
    """Place interior doors with purpose-driven positioning.

    Returns dict mapping room name → wall_id of the wall containing its door.
    This is used by window placement to find the "opposite" wall.
    """
    room_door_walls: Dict[str, str] = {}
    placed_positions: set = set()  # (wall_id, rounded_offset) for dedup

    _HALLWAY_TYPES = {RoomType.HALLWAY}
    _OPEN_TYPES = {RoomType.LIVING, RoomType.KITCHEN, RoomType.DINING,
                   RoomType.FAMILY_ROOM}

    for i, ca in enumerate(cells):
        ax, ay, aw, ah, ra = ca
        for cb in cells[i + 1:]:
            bx, by, bw, bh, rb = cb

            if _is_open_plan(ra, rb):
                continue
            if not _cells_share_edge(ca, cb):
                continue

            # Skip hallway↔open-plan doors — zone transition door handles this
            if ((ra.room_type in _HALLWAY_TYPES and rb.room_type in _OPEN_TYPES) or
                    (rb.room_type in _HALLWAY_TYPES and ra.room_type in _OPEN_TYPES)):
                continue

            door = _make_door_v2(ca, cb, walls, did)
            if door:
                # Deduplicate: skip if a door already exists nearby on this wall
                pos_key = (door.wall_id, round(door.offset_ft, 0))
                if pos_key in placed_positions:
                    continue
                placed_positions.add(pos_key)

                doors.append(door)
                # Track which wall each room's door is on
                room_door_walls[ra.name] = door.wall_id
                room_door_walls[rb.name] = door.wall_id

    return room_door_walls


def _make_door_v2(
    cell_a: Cell, cell_b: Cell,
    walls: List[Wall], did: _IdGen,
) -> Optional[Opening]:
    """Create a door on the wall between two cells using DOOR_RULES."""
    ax, ay, aw, ah, ra = cell_a
    bx, by, bw, bh, rb = cell_b

    # Use the "receiving" room to determine door width and placement
    door_w_in_a, _ = get_door_spec(ra.room_type)
    door_w_in_b, _ = get_door_spec(rb.room_type)
    door_w_in = min(door_w_in_a, door_w_in_b)
    door_w_ft = door_w_in / 12.0

    # Determine which room's rules to use (the smaller/more specific room)
    # Prefer bathroom/closet rules over bedroom rules
    priority = {
        RoomType.HALF_BATH: 0, RoomType.BATHROOM: 1, RoomType.MASTER_BATH: 1,
        RoomType.WALK_IN_CLOSET: 2, RoomType.PANTRY: 2, RoomType.LAUNDRY: 3,
        RoomType.BEDROOM: 4, RoomType.MASTER_BEDROOM: 4, RoomType.OFFICE: 4,
    }
    pa = priority.get(ra.room_type, 5)
    pb = priority.get(rb.room_type, 5)
    rule_room = ra if pa <= pb else rb

    # Vertical shared edge
    for edge_x in [round(ax + aw, 1), round(bx + bw, 1)]:
        if abs(edge_x - bx) < 0.5 or abs(edge_x - ax) < 0.5:
            y_lo = max(ay, by)
            y_hi = min(ay + ah, by + bh)

            for w in walls:
                if w.is_vertical and abs(w.x1 - edge_x) < 0.5:
                    wlo = min(w.y1, w.y2)
                    whi = max(w.y1, w.y2)
                    if wlo <= y_lo + 0.5 and whi >= y_hi - 0.5:
                        # Convert segment bounds to wall-offset space
                        off_lo = _abs_to_wall_offset(w, y_lo)
                        off_hi = _abs_to_wall_offset(w, y_hi)
                        if off_lo > off_hi:
                            off_lo, off_hi = off_hi, off_lo
                        seg_len = off_hi - off_lo
                        seg_offset = _compute_door_offset(
                            seg_len, door_w_ft, rule_room.room_type)
                        wall_offset = off_lo + seg_offset
                        return Opening(did(), w.id, wall_offset, door_w_ft, "door")
            break

    # Horizontal shared edge
    for edge_y in [round(ay + ah, 1), round(by + bh, 1)]:
        if abs(edge_y - by) < 0.5 or abs(edge_y - ay) < 0.5:
            x_lo = max(ax, bx)
            x_hi = min(ax + aw, bx + bw)

            for w in walls:
                if w.is_horizontal and abs(w.y1 - edge_y) < 0.5:
                    wlo = min(w.x1, w.x2)
                    whi = max(w.x1, w.x2)
                    if wlo <= x_lo + 0.5 and whi >= x_hi - 0.5:
                        # Convert segment bounds to wall-offset space
                        off_lo = _abs_to_wall_offset(w, x_lo)
                        off_hi = _abs_to_wall_offset(w, x_hi)
                        if off_lo > off_hi:
                            off_lo, off_hi = off_hi, off_lo
                        seg_len = off_hi - off_lo
                        seg_offset = _compute_door_offset(
                            seg_len, door_w_ft, rule_room.room_type)
                        wall_offset = off_lo + seg_offset
                        return Opening(did(), w.id, wall_offset, door_w_ft, "door")
            break

    return None


# ══════════════════════════════════════════════════════════════════════════════
# PURPOSEFUL WINDOW PLACEMENT (v2)
# ══════════════════════════════════════════════════════════════════════════════

def _get_cell_exterior_walls(
    cell: Cell, walls: List[Wall], W: float, H: float,
) -> List[Tuple[Wall, str]]:
    """Get exterior walls that border this cell, with their direction.

    Returns list of (Wall, direction) where direction is "north", "south",
    "east", or "west".
    """
    x, y, w, h, _ = cell
    result = []

    for wall in walls:
        if not wall.is_exterior:
            continue

        # South wall (y≈0)
        if wall.is_horizontal and abs(wall.y1) < 0.5 and abs(y) < 0.5:
            span_lo = max(x, min(wall.x1, wall.x2))
            span_hi = min(x + w, max(wall.x1, wall.x2))
            if span_hi - span_lo > 2.0:
                result.append((wall, "south"))

        # North wall (y≈H)
        elif wall.is_horizontal and abs(wall.y1 - H) < 0.5 and abs(y + h - H) < 0.5:
            span_lo = max(x, min(wall.x1, wall.x2))
            span_hi = min(x + w, max(wall.x1, wall.x2))
            if span_hi - span_lo > 2.0:
                result.append((wall, "north"))

        # East wall (x≈W)
        elif wall.is_vertical and abs(wall.x1 - W) < 0.5 and abs(x + w - W) < 0.5:
            span_lo = max(y, min(wall.y1, wall.y2))
            span_hi = min(y + h, max(wall.y1, wall.y2))
            if span_hi - span_lo > 2.0:
                result.append((wall, "east"))

        # West wall (x≈0)
        elif wall.is_vertical and abs(wall.x1) < 0.5 and abs(x) < 0.5:
            span_lo = max(y, min(wall.y1, wall.y2))
            span_hi = min(y + h, max(wall.y1, wall.y2))
            if span_hi - span_lo > 2.0:
                result.append((wall, "west"))

        # L-shape extra exterior walls (non-boundary)
        elif wall.is_horizontal:
            wlo = min(wall.x1, wall.x2)
            whi = max(wall.x1, wall.x2)
            span_lo = max(x, wlo)
            span_hi = min(x + w, whi)
            if abs(wall.y1 - y) < 0.5 and span_hi - span_lo > 2.0:
                result.append((wall, "south"))
            elif abs(wall.y1 - (y + h)) < 0.5 and span_hi - span_lo > 2.0:
                result.append((wall, "north"))

        elif wall.is_vertical:
            wlo = min(wall.y1, wall.y2)
            whi = max(wall.y1, wall.y2)
            span_lo = max(y, wlo)
            span_hi = min(y + h, whi)
            if abs(wall.x1 - x) < 0.5 and span_hi - span_lo > 2.0:
                result.append((wall, "west"))
            elif abs(wall.x1 - (x + w)) < 0.5 and span_hi - span_lo > 2.0:
                result.append((wall, "east"))

    return result


def _get_door_wall_direction(
    cell: Cell, door_wall_id: str, walls: List[Wall],
) -> Optional[str]:
    """Determine which direction (N/S/E/W) the door wall is relative to the cell."""
    x, y, w, h, _ = cell
    for wall in walls:
        if wall.id != door_wall_id:
            continue
        if wall.is_horizontal:
            if abs(wall.y1 - y) < 0.5:
                return "south"
            elif abs(wall.y1 - (y + h)) < 0.5:
                return "north"
        elif wall.is_vertical:
            if abs(wall.x1 - x) < 0.5:
                return "west"
            elif abs(wall.x1 - (x + w)) < 0.5:
                return "east"
    return None


_OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}


def _place_windows_v2(
    cells: List[Cell],
    walls: List[Wall],
    windows: List[Opening],
    winid: _IdGen,
    W: float, H: float,
    room_door_walls: Dict[str, str],
) -> None:
    """Place windows with purpose-driven positioning.

    Bedrooms: windows on wall opposite door (light draws you in)
    Kitchens: sill at 42" (above counter)
    Bathrooms: small 2ft windows, sill at 48" (privacy)
    """
    for cell in cells:
        x, y, w, h, room = cell
        rules = WINDOW_RULES.get(room.room_type)
        if not rules:
            continue

        placement = WINDOW_PLACEMENT.get(room.room_type, {
            "preferred_wall": "exterior", "position": "centered"})

        ext_walls = _get_cell_exterior_walls(cell, walls, W, H)
        if not ext_walls:
            continue

        # Determine window size
        is_wet = room.room_type in (
            RoomType.BATHROOM, RoomType.MASTER_BATH, RoomType.HALF_BATH)
        win_w_ft = 2.0 if is_wet else 3.0
        sill_ht = rules.get("sill_height", 30) / 12.0

        # Determine window count from glazing ratio
        room_area = w * h
        glazing_area = room_area * rules["glazing_ratio"]
        win_area_each = win_w_ft * 4.0
        n_windows = max(1, math.ceil(glazing_area / win_area_each))

        # Choose target wall
        target_wall = None
        target_dir = None

        if placement["preferred_wall"] == "opposite_door":
            # Find wall opposite the door
            door_wid = room_door_walls.get(room.name)
            if door_wid:
                door_dir = _get_door_wall_direction(cell, door_wid, walls)
                if door_dir:
                    opp_dir = _OPPOSITE.get(door_dir)
                    if opp_dir:
                        # Find exterior wall in opposite direction
                        for ew, edir in ext_walls:
                            if edir == opp_dir:
                                target_wall = ew
                                target_dir = edir
                                break

        # Fallback: try each exterior wall until one has enough span
        if target_wall is None:
            for ew, edir in ext_walls:
                if ew.is_horizontal:
                    s_lo = max(x, min(ew.x1, ew.x2))
                    s_hi = min(x + w, max(ew.x1, ew.x2))
                else:
                    s_lo = max(y, min(ew.y1, ew.y2))
                    s_hi = min(y + h, max(ew.y1, ew.y2))
                if s_hi - s_lo >= win_w_ft + 4:
                    target_wall = ew
                    target_dir = edir
                    break

        if target_wall is None:
            continue

        # Compute span of wall that overlaps with this cell
        if target_wall.is_horizontal:
            span_lo = max(x, min(target_wall.x1, target_wall.x2))
            span_hi = min(x + w, max(target_wall.x1, target_wall.x2))
        else:
            span_lo = max(y, min(target_wall.y1, target_wall.y2))
            span_hi = min(y + h, max(target_wall.y1, target_wall.y2))

        if span_hi - span_lo < win_w_ft + 4:
            continue

        _add_windows_on_span(
            target_wall, span_lo, span_hi, n_windows,
            win_w_ft, sill_ht, windows, winid)


def _abs_to_wall_offset(wall: Wall, abs_coord: float) -> float:
    """Convert absolute X (horizontal) or Y (vertical) to wall offset.

    Handles walls going in either direction (L→R, R→L, B→T, T→B).
    Wall offset is distance from wall start along the wall.
    """
    if wall.is_horizontal:
        dx = wall.x2 - wall.x1
        if abs(dx) < 0.01:
            return 0.0
        t = (abs_coord - wall.x1) / dx
    else:
        dy = wall.y2 - wall.y1
        if abs(dy) < 0.01:
            return 0.0
        t = (abs_coord - wall.y1) / dy
    return t * wall.length


def _add_windows_on_span(
    wall: Wall,
    span_lo: float, span_hi: float,
    count: int,
    win_w_ft: float, sill_ht: float,
    windows: List[Opening],
    winid: _IdGen,
) -> None:
    """Place count windows evenly along a wall span.

    span_lo/span_hi are in absolute coordinates. Handles walls going
    in either direction (R→L, T→B) via wall-offset conversion.
    """
    avail = span_hi - span_lo
    margin = 2.0
    usable = avail - 2 * margin
    if usable < win_w_ft:
        return

    # Convert span boundaries to wall-offset space (handles reversed walls)
    off_lo = _abs_to_wall_offset(wall, span_lo)
    off_hi = _abs_to_wall_offset(wall, span_hi)
    if off_lo > off_hi:
        off_lo, off_hi = off_hi, off_lo

    if count == 1:
        center_off = (off_lo + off_hi) / 2
        offset = center_off - win_w_ft / 2
        if offset >= 0:
            windows.append(Opening(
                winid(), wall.id, offset, win_w_ft, "window",
                sill_height_ft=sill_ht))
    else:
        off_usable = (off_hi - off_lo) - 2 * margin
        if off_usable < win_w_ft:
            return
        spacing = off_usable / count
        for j in range(count):
            center_off = off_lo + margin + spacing * (j + 0.5)
            offset = center_off - win_w_ft / 2
            if offset >= 0:
                windows.append(Opening(
                    winid(), wall.id, offset, win_w_ft, "window",
                    sill_height_ft=sill_ht))


def _build_room_labels(cells: List[Cell]) -> List[RoomLabel]:
    """Create room labels from cell list."""
    labels = []
    for x, y, w, h, room in cells:
        labels.append(RoomLabel(
            room.name,
            (x + w / 2, y + h / 2),
            room_type=room.room_type.value,
            area_sqft=w * h,
        ))
    return labels


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def generate_wall_plan(
    rooms: Optional[List[RoomSpec]] = None,
    footprint_w: Optional[float] = None,
    footprint_h: Optional[float] = None,
    shape: str = "rectangle",
    total_area: float = 1200,
    bedrooms: int = 3,
    bathrooms: Optional[int] = None,
    wall_height: float = 10.0,
) -> WallPlan:
    """Generate a WallPlan from room program or high-level parameters.

    API signature identical to v1.
    """
    tier = "medium"
    if rooms is None:
        program = extract_program(total_area, bedrooms, bathrooms)
        rooms = program["rooms"]
        tier = program["tier"]
        if footprint_w is None:
            footprint_w = program["footprint"][0]
        if footprint_h is None:
            footprint_h = program["footprint"][1]
    else:
        tier = determine_tier(total_area)

    if footprint_w is None or footprint_h is None:
        aspect = 1.3
        footprint_w = math.sqrt(total_area * aspect)
        footprint_h = total_area / footprint_w
        footprint_w = _snap(footprint_w)
        footprint_h = _snap(footprint_h)

    clusters = _classify_into_clusters(rooms, tier)

    shape_upper = shape.upper()
    if shape_upper == "L":
        return _build_l_shape(clusters, footprint_w, footprint_h,
                              wall_height, tier)
    elif shape_upper == "T":
        return _build_t_shape(clusters, footprint_w, footprint_h,
                              wall_height, tier)
    elif shape_upper == "U":
        return _build_u_shape(clusters, footprint_w, footprint_h,
                              wall_height, tier)
    else:
        return _build_rectangle(clusters, footprint_w, footprint_h,
                                wall_height, tier)


# ══════════════════════════════════════════════════════════════════════════════
# RECTANGLE SHAPE (v3 — split plan columns)
# ══════════════════════════════════════════════════════════════════════════════

def _build_rectangle(
    clusters: Dict[str, List[RoomSpec]],
    W: float, H: float,
    wall_height: float, tier: str,
) -> WallPlan:
    """Build split-plan rectangular floor plan using vertical columns.

    v3: Master suite (west) + Great Room (center) + Bedrooms (east)
    with a service row at the bottom. Creates architecturally zoned homes
    instead of the v2 hotel-corridor pattern.
    """
    wid = _IdGen("W")
    did = _IdGen("D")
    winid = _IdGen("WIN")

    walls: List[Wall] = []
    doors: List[Opening] = []
    windows: List[Opening] = []
    cells: List[Cell] = []

    # ── Exterior walls (4) ──
    w_s = Wall(wid(), (0, 0), (W, 0), "exterior", 8.0, wall_height)
    w_e = Wall(wid(), (W, 0), (W, H), "exterior", 8.0, wall_height)
    w_n = Wall(wid(), (W, H), (0, H), "exterior", 8.0, wall_height)
    w_w = Wall(wid(), (0, H), (0, 0), "exterior", 8.0, wall_height)
    walls.extend([w_s, w_e, w_n, w_w])

    # ── Classify rooms ──
    public_overflow = [r for r in clusters["overflow"]
                       if r.room_type == RoomType.FAMILY_ROOM]
    private_overflow = [r for r in clusters["overflow"]
                        if r.room_type != RoomType.FAMILY_ROOM]

    master_rooms = clusters["master_suite"]
    bed_rooms = [r for r in clusters["bedroom_wing"]
                 if r.room_type == RoomType.BEDROOM]
    bath_rooms = [r for r in clusters["bedroom_wing"]
                  if r.room_type in (RoomType.BATHROOM, RoomType.HALF_BATH)]
    open_rooms = clusters["open_plan"] + public_overflow
    entry_rooms = clusters["entry"]
    service_rooms = clusters["service"]

    num_bedrooms = len(bed_rooms) + len(
        [r for r in master_rooms if r.room_type == RoomType.MASTER_BEDROOM])

    if not (master_rooms or bed_rooms or open_rooms):
        return WallPlan(walls=walls, wall_height_ft=wall_height,
                        overall_width_ft=W, overall_depth_ft=H)

    # ── Decide 2-column vs 3-column ──
    use_3col = (len(bed_rooms) >= 1 and W >= 30 and
                len(master_rooms) > 0)

    # ── Step 1: Compute column widths ──
    mb_w, mb_h = (0.0, 0.0)
    master_col_w = 0.0
    bedroom_col_w = 0.0
    great_room_w = W

    if master_rooms:
        mb = next((r for r in master_rooms
                   if r.room_type == RoomType.MASTER_BEDROOM), None)
        if mb:
            mb_w, mb_h = _get_room_dims(RoomType.MASTER_BEDROOM, tier, W, H)
        # Accessories side-by-side width
        accessories = [r for r in master_rooms
                       if r.room_type != RoomType.MASTER_BEDROOM]
        if accessories:
            acc_w = sum(_get_room_dims(a.room_type, tier, W, H)[0]
                        for a in accessories)
            master_col_w = _snap(max(mb_w, acc_w))
        else:
            master_col_w = _snap(mb_w) if mb_w > 0 else _snap(W * 0.35)

    if use_3col and bed_rooms:
        bed_depths = [_get_room_dims(r.room_type, tier, W, H)[0]
                      for r in bed_rooms]
        bedroom_col_w = _snap(max(bed_depths))

    great_room_w = W - master_col_w - bedroom_col_w

    # Ensure great room >= MIN_GREAT_ROOM_W
    if great_room_w < MIN_GREAT_ROOM_W and (master_col_w + bedroom_col_w) > 0:
        overshoot = MIN_GREAT_ROOM_W - great_room_w
        total_cols = master_col_w + bedroom_col_w
        if total_cols > 0:
            master_reduce = overshoot * master_col_w / total_cols
            bedroom_reduce = overshoot * bedroom_col_w / total_cols
            master_col_w = _snap(master_col_w - master_reduce)
            bedroom_col_w = _snap(bedroom_col_w - bedroom_reduce)
            great_room_w = W - master_col_w - bedroom_col_w

    # Enforce minimum column widths
    if master_col_w > 0:
        master_col_w = max(master_col_w, 10.0)
    if bedroom_col_w > 0:
        bedroom_col_w = max(bedroom_col_w, 9.0)
    # Recompute great room after enforcement
    great_room_w = W - master_col_w - bedroom_col_w
    if great_room_w < MIN_GREAT_ROOM_W and master_col_w > 0:
        master_col_w = _snap(W - bedroom_col_w - MIN_GREAT_ROOM_W)
        great_room_w = W - master_col_w - bedroom_col_w

    # ── Step 2: Compute service row height ──
    entry_h = 5.0
    if entry_rooms:
        _, entry_h = _get_room_dims(RoomType.ENTRY, tier, W, H)
    svc_row_h = _snap(max(5.0, min(entry_h, 8.0)))
    primary_h = H - svc_row_h

    # ── Step 3: Column divider walls ──
    if master_col_w > 0:
        master_div = Wall(wid(), (master_col_w, svc_row_h),
                          (master_col_w, H),
                          "interior", 4.0, wall_height)
        walls.append(master_div)

    if bedroom_col_w > 0:
        bed_div_x = W - bedroom_col_w
        bed_div = Wall(wid(), (bed_div_x, svc_row_h),
                       (bed_div_x, H),
                       "interior", 4.0, wall_height)
        walls.append(bed_div)

    # Service row divider wall
    svc_wall = Wall(wid(), (0, svc_row_h), (W, svc_row_h),
                    "interior", 4.0, wall_height)
    walls.append(svc_wall)

    # ── Step 4: Stack master column (west) ──
    if master_rooms:
        # Overflow rooms that go in master column: laundry, office
        master_overflow = [r for r in private_overflow
                           if r.room_type in (RoomType.OFFICE,
                                              RoomType.LAUNDRY)]
        # If no bedroom column, laundry from service goes to master column
        if not use_3col:
            laundry = [r for r in service_rooms
                       if r.room_type == RoomType.LAUNDRY]
            master_overflow.extend(laundry)
            service_rooms = [r for r in service_rooms
                             if r.room_type != RoomType.LAUNDRY]

        cells.extend(_stack_master_column(
            master_rooms, master_overflow,
            0, svc_row_h, master_col_w, primary_h, tier))

    # ── Step 5: Stack bedroom column (east) ──
    if use_3col and bed_rooms:
        wing_baths = bath_rooms[:]

        bed_div_x = W - bedroom_col_w
        cells.extend(_stack_bedroom_column(
            bed_rooms, wing_baths,
            bed_div_x, svc_row_h, bedroom_col_w, primary_h, tier))
    elif bed_rooms and not use_3col:
        # 2-column: bedrooms go in service row or below great room
        # Place bed rooms + baths below great room (east side of bottom)
        pass  # handled in service row

    # ── Step 6: Place great room (center column) ──
    if open_rooms:
        gr_x = master_col_w
        gr_w = great_room_w
        cells.extend(_place_great_room(
            open_rooms, gr_x, svc_row_h, gr_w, primary_h))

    # ── Step 7: Place service row (bottom) ──
    # For 2-column with bed_rooms but no bedroom column, put beds in service area
    if bed_rooms and not use_3col:
        # Bedrooms + baths go in the right portion of the bottom
        svc_left = entry_rooms + service_rooms
        left_w = master_col_w if master_col_w > 0 else _snap(W * 0.35)
        if svc_left:
            cells.extend(_pack_strip(
                svc_left, 0, 0, left_w, svc_row_h, horizontal=False))

        bed_x = left_w
        bed_w = W - left_w
        all_bed_bath = bed_rooms + bath_rooms
        cells.extend(_pack_strip(
            all_bed_bath, bed_x, 0, bed_w, svc_row_h, horizontal=True))
    else:
        cells.extend(_place_service_row(
            entry_rooms, service_rooms,
            0, 0, W, svc_row_h,
            master_col_w, bedroom_col_w, tier))

    # ── Step 8: Partition walls ──
    _place_partition_walls(cells, walls, wid, wall_height, W, H)

    # ── Step 9: Entry door on south wall ──
    entry_cell = next((c for c in cells
                       if c[4].room_type == RoomType.ENTRY), None)
    if entry_cell:
        entry_x = entry_cell[0] + entry_cell[2] / 2
    else:
        entry_x = W * 0.3

    entry_door_w = DOOR_SPECS["entry"][0] / 12.0
    doors.append(Opening(
        did(), w_s.id,
        max(0.5, entry_x - entry_door_w / 2), entry_door_w, "door",
        is_entry=True))

    # Zone transition door: hallway → great room (through svc_wall)
    # Place in the hallway section (center column), not at entry position
    hallway_cell = next((c for c in cells
                         if c[4].room_type == RoomType.HALLWAY), None)
    if hallway_cell:
        zone_door_x = hallway_cell[0] + hallway_cell[2] / 2
    else:
        zone_door_x = master_col_w + great_room_w / 2
    zone_door_offset = max(0.5, zone_door_x - 1.25)
    doors.append(Opening(did(), svc_wall.id, zone_door_offset, 2.5, "door"))

    # ── Step 10: Interior doors (v2: purpose-driven) ──
    room_door_walls = _place_doors_v2(cells, walls, doors, did)

    # ── Post-filter: remove kitchen↔private doors ──
    _PRIVATE_TYPES = {RoomType.MASTER_BATH, RoomType.BATHROOM,
                      RoomType.WALK_IN_CLOSET, RoomType.MASTER_BEDROOM,
                      RoomType.BEDROOM}
    doors = [d for d in doors
             if not _is_kitchen_to_private(d, cells, walls, _PRIVATE_TYPES)]

    # ── Step 11: Windows (v2: opposite-door placement) ──
    _place_windows_v2(cells, walls, windows, winid, W, H, room_door_walls)

    # ── Build plan ──
    room_labels = _build_room_labels(cells)

    return WallPlan(
        walls=walls,
        doors=doors,
        windows=windows,
        rooms=room_labels,
        overall_width_ft=W,
        overall_depth_ft=H,
        wall_height_ft=wall_height,
    )


def _is_kitchen_to_private(
    door: Opening, cells: List[Cell], walls: List[Wall],
    private_types: set,
) -> bool:
    """Check if a door connects kitchen directly to a private room."""
    if door.is_entry:
        return False
    wall = next((w for w in walls if w.id == door.wall_id), None)
    if wall is None:
        return False

    pos = door.resolve_position(wall)
    px, py = pos

    adjacent_types = set()
    for cx, cy, cw, ch, room in cells:
        if (cx - 1.0 <= px <= cx + cw + 1.0 and
                cy - 1.0 <= py <= cy + ch + 1.0):
            adjacent_types.add(room.room_type)

    has_kitchen = RoomType.KITCHEN in adjacent_types
    has_private = bool(adjacent_types & private_types)
    return has_kitchen and has_private


# ══════════════════════════════════════════════════════════════════════════════
# L-SHAPE (v3 — split plan with master wing)
# ══════════════════════════════════════════════════════════════════════════════

def _build_l_shape(
    clusters: Dict[str, List[RoomSpec]],
    W: float, H: float,
    wall_height: float, tier: str,
) -> WallPlan:
    """Build L-shaped floor plan with split plan zoning.

    v3: Left wing (above notch) = master suite column.
    Right wing = service row (bottom) + great room (middle) + bedrooms (top).
    Privacy gradient: entry→service→great room→bedrooms (top = most private).
    The notch creates natural acoustic separation.
    """
    wid = _IdGen("W")
    did = _IdGen("D")
    winid = _IdGen("WIN")

    walls: List[Wall] = []
    doors: List[Opening] = []
    windows: List[Opening] = []
    cells: List[Cell] = []

    # L-shape geometry
    split_x = _snap(W * 0.43)
    notch_h = _snap(H * 0.20)

    # ── 6 exterior walls ──
    w1 = Wall(wid(), (split_x, 0), (W, 0), "exterior", 8.0, wall_height)
    w2 = Wall(wid(), (W, 0), (W, H), "exterior", 8.0, wall_height)
    w3 = Wall(wid(), (W, H), (0, H), "exterior", 8.0, wall_height)
    w4 = Wall(wid(), (0, H), (0, notch_h), "exterior", 8.0, wall_height)
    w5 = Wall(wid(), (0, notch_h), (split_x, notch_h), "exterior", 8.0, wall_height)
    w6 = Wall(wid(), (split_x, notch_h), (split_x, 0), "exterior", 8.0, wall_height)
    walls.extend([w1, w2, w3, w4, w5, w6])

    # ── Classify rooms ──
    public_overflow = [r for r in clusters["overflow"]
                       if r.room_type == RoomType.FAMILY_ROOM]
    private_overflow = [r for r in clusters["overflow"]
                        if r.room_type != RoomType.FAMILY_ROOM]

    master_rooms = clusters["master_suite"]
    bed_rooms = [r for r in clusters["bedroom_wing"]
                 if r.room_type == RoomType.BEDROOM]
    bath_rooms = [r for r in clusters["bedroom_wing"]
                  if r.room_type in (RoomType.BATHROOM, RoomType.HALF_BATH)]
    open_rooms = clusters["open_plan"] + public_overflow
    entry_rooms = clusters["entry"]
    service_rooms = clusters["service"]

    # ── Left wing (master suite): x=0..split_x, y=notch_h..H ──
    left_w = split_x
    left_h = H - notch_h

    if master_rooms:
        master_overflow = [r for r in private_overflow
                           if r.room_type in (RoomType.OFFICE, RoomType.LAUNDRY)]
        cells.extend(_stack_master_column(
            master_rooms, master_overflow,
            0, notch_h, left_w, left_h, tier))
    elif clusters["bedroom_wing"] or private_overflow:
        # No master suite: put some bedrooms in left wing
        left_rooms = clusters["bedroom_wing"] + private_overflow
        cells.extend(_pack_strip(
            left_rooms, 0, notch_h, left_w, left_h, horizontal=False))

    # Wing divider: split_x from notch_h to H
    divider = Wall(wid(), (split_x, notch_h), (split_x, H),
                   "interior", 4.0, wall_height)
    walls.append(divider)

    # ── Right wing: service row (bottom) + great room (middle) + bedrooms (top) ──
    right_w = W - split_x

    # Compute service row and bedroom row heights
    svc_row_h = _snap(max(5.0, min(8.0, notch_h)))
    bed_area_h = 0.0
    if bed_rooms:
        bed_template_h = max(
            _get_room_dims(r.room_type, tier, right_w, H)[1]
            for r in bed_rooms)
        bed_area_h = _snap(max(bed_template_h, 10.0))

    # Great room fills middle of right wing (between service row and bedrooms)
    gr_h = H - svc_row_h - bed_area_h if bed_rooms else H - svc_row_h
    gr_h = max(gr_h, MIN_GREAT_ROOM_W)

    gr_y = svc_row_h  # great room directly above service row

    if open_rooms:
        cells.extend(_place_great_room(
            open_rooms, split_x, gr_y, right_w, gr_h))

    # Bedroom row at TOP of right wing (private rooms far from entry)
    if bed_rooms and bed_area_h > 0:
        bed_row_y = svc_row_h + gr_h  # bedrooms above great room

        # Horizontal divider between great room and bedrooms
        bed_row_wall = Wall(wid(),
                            (split_x, bed_row_y),
                            (W, bed_row_y),
                            "interior", 4.0, wall_height)
        walls.append(bed_row_wall)

        # Half baths from service go with bedrooms
        wing_baths = bath_rooms[:]
        half_baths = [r for r in service_rooms
                      if r.room_type == RoomType.HALF_BATH]
        wing_baths.extend(half_baths)
        service_rooms = [r for r in service_rooms
                         if r.room_type != RoomType.HALF_BATH]

        all_bed_bath = bed_rooms + wing_baths
        cells.extend(_pack_strip(
            all_bed_bath, split_x, bed_row_y,
            right_w, bed_area_h, horizontal=True))

    # Service row at bottom of right wing
    svc_all = entry_rooms + service_rooms
    if svc_all:
        cells.extend(_pack_strip(
            svc_all, split_x, 0, right_w, svc_row_h, horizontal=True))

    # ── Partition walls ──
    _place_partition_walls(cells, walls, wid, wall_height, W, H)

    # ── Entry door ──
    # Entry on south exterior wall of right wing (w1)
    entry_cell = next((c for c in cells
                       if c[4].room_type == RoomType.ENTRY), None)
    if entry_cell:
        entry_x_abs = entry_cell[0] + entry_cell[2] / 2
        # Convert to offset along w1 (which starts at split_x)
        entry_offset = entry_x_abs - split_x
    else:
        entry_offset = right_w * 0.3

    entry_door_w = DOOR_SPECS["entry"][0] / 12.0
    doors.append(Opening(
        did(), w1.id, max(0.5, entry_offset - entry_door_w / 2),
        entry_door_w, "door", is_entry=True))

    # Door through wing divider (master wing → great room)
    # Position door at great room level (above notch, in middle of great room)
    gr_mid_y = gr_y + gr_h * 0.4
    # Offset along divider wall (which starts at notch_h)
    div_offset = gr_mid_y - notch_h
    doors.append(Opening(did(), divider.id, max(0.5, div_offset), 2.5, "door"))

    # Zone transition door: service row → great room
    # Find the partition wall at y=svc_row_h between service row and great room
    svc_divider = None
    for wall in walls:
        if (wall.wall_type == "interior"
                and abs(wall.start[1] - svc_row_h) < 0.5
                and abs(wall.end[1] - svc_row_h) < 0.5
                and wall.start[0] >= split_x - 0.5):
            svc_divider = wall
            break
    if svc_divider:
        # Place door near center of service divider
        svc_div_len = abs(svc_divider.end[0] - svc_divider.start[0])
        doors.append(Opening(did(), svc_divider.id,
                             max(0.5, svc_div_len * 0.4), 2.5, "door"))

    # ── Interior doors (v2) ──
    room_door_walls = _place_doors_v2(cells, walls, doors, did)

    # ── Windows (v2) ──
    _place_windows_v2(cells, walls, windows, winid, W, H, room_door_walls)

    room_labels = _build_room_labels(cells)

    return WallPlan(
        walls=walls,
        doors=doors,
        windows=windows,
        rooms=room_labels,
        overall_width_ft=W,
        overall_depth_ft=H,
        wall_height_ft=wall_height,
    )


# ══════════════════════════════════════════════════════════════════════════════
# T-SHAPE and U-SHAPE
# ══════════════════════════════════════════════════════════════════════════════

def _build_t_shape(
    clusters: Dict[str, List[RoomSpec]],
    W: float, H: float,
    wall_height: float, tier: str,
) -> WallPlan:
    """T-shape: central body + side bump-outs. Uses rectangle for now."""
    return _build_rectangle(clusters, W, H, wall_height, tier)


def _build_u_shape(
    clusters: Dict[str, List[RoomSpec]],
    W: float, H: float,
    wall_height: float, tier: str,
) -> WallPlan:
    """U-shape: central courtyard. Uses rectangle for now."""
    return _build_rectangle(clusters, W, H, wall_height, tier)
