"""
Stage 2: Layout Generation — Strip-Based Template Algorithm (v2)

Replaces the v1 squarified treemap with a two-band residential layout
that encodes real architectural patterns:
  - Front band (south): public zone — entry, living hub, service rooms
  - Back band (north): private zone — master suite, hallway, bedrooms

Algorithm:
1. Classify rooms into clusters (living hub, master suite, bedroom wing, service, entry)
2. Divide footprint into front/back bands
3. Lay out front band left-to-right: entry → living hub → service
4. Lay out back band left-to-right: master suite → hallway → bedrooms
5. Scale each band to fit footprint width
6. Generate walls, skipping open-plan connections
7. Place doors (skip open-plan pairs)
8. Place windows on exterior walls
"""

from typing import List, Dict, Set, Tuple, Optional
import math

from .models import RoomRect, RoomSpec, WallSegment, DoorPlacement, WindowPlacement, FloorPlan, Zone, RoomType
from .knowledge import (
    adjacency_weight, ASPECT_RATIOS, MIN_DIMENSIONS,
    get_door_spec, WINDOW_RULES, ZONE_MAP, OPEN_PLAN_GROUPS,
)


# =============================================================================
# GRID SNAPPING
# =============================================================================

def snap(value: float, grid: float = 0.5) -> float:
    """Snap a value to the nearest grid increment (default 6 inches)."""
    return round(value / grid) * grid


# =============================================================================
# ROOM CLASSIFICATION
# =============================================================================

def classify_rooms(rooms: List[RoomSpec]) -> Dict[str, List[RoomSpec]]:
    """Group room specs into architectural clusters.

    Returns dict with keys:
        entry, living_hub, service, master_suite, bedroom_wing, other
    """
    clusters = {
        "entry": [],
        "living_hub": [],
        "service": [],
        "master_suite": [],
        "bedroom_wing": [],
        "other": [],
    }

    for room in rooms:
        rt = room.room_type

        if rt == RoomType.ENTRY:
            clusters["entry"].append(room)

        elif rt in (RoomType.LIVING, RoomType.KITCHEN, RoomType.DINING, RoomType.FAMILY_ROOM):
            clusters["living_hub"].append(room)

        elif rt in (RoomType.HALF_BATH, RoomType.LAUNDRY, RoomType.PANTRY):
            clusters["service"].append(room)

        elif rt in (RoomType.MASTER_BEDROOM, RoomType.MASTER_BATH, RoomType.WALK_IN_CLOSET):
            clusters["master_suite"].append(room)

        elif rt in (RoomType.BEDROOM, RoomType.BATHROOM, RoomType.HALLWAY,
                    RoomType.CLOSET, RoomType.OFFICE):
            clusters["bedroom_wing"].append(room)

        else:
            clusters["other"].append(room)

    return clusters


# =============================================================================
# OPEN-PLAN CONNECTION LOGIC
# =============================================================================

def get_open_connections(rooms: List[RoomRect]) -> Set[Tuple[str, str]]:
    """Return set of (room_name_a, room_name_b) pairs that should be open-plan.

    Based on OPEN_PLAN_GROUPS from knowledge.py — any two rooms whose
    types both appear in the same group get an open connection.
    """
    connections = set()
    for i, a in enumerate(rooms):
        for j, b in enumerate(rooms):
            if j <= i:
                continue
            for group in OPEN_PLAN_GROUPS:
                if a.room_type in group and b.room_type in group:
                    pair = tuple(sorted([a.name, b.name]))
                    connections.add(pair)
    return connections


def is_open_pair(name_a: str, name_b: str, open_connections: Set[Tuple[str, str]]) -> bool:
    """Check if two rooms form an open-plan pair."""
    pair = tuple(sorted([name_a, name_b]))
    return pair in open_connections


# =============================================================================
# BAND SPLITTING
# =============================================================================

def calculate_band_split(
    footprint_h: float,
    clusters: Dict[str, List[RoomSpec]],
) -> Tuple[float, float]:
    """Determine front and back band heights.

    Front band (public): ~45% of depth (min 12')
    Back band (private): ~55% of depth (min 12')

    Returns (front_h, back_h).
    """
    front_rooms = clusters["entry"] + clusters["living_hub"] + clusters["service"]
    back_rooms = clusters["master_suite"] + clusters["bedroom_wing"]

    front_area = sum(r.target_area for r in front_rooms)
    back_area = sum(r.target_area for r in back_rooms)
    total_area = front_area + back_area
    if total_area == 0:
        total_area = 1

    # Proportional split biased toward private zone
    back_ratio = max(0.50, min(0.60, back_area / total_area))
    front_ratio = 1.0 - back_ratio

    front_h = snap(footprint_h * front_ratio)
    back_h = snap(footprint_h * back_ratio)

    # Enforce minimums
    min_band = 10.0
    if front_h < min_band and front_rooms:
        front_h = min_band
        back_h = snap(footprint_h - front_h)
    if back_h < min_band and back_rooms:
        back_h = min_band
        front_h = snap(footprint_h - back_h)

    # Final clamp — ensure they sum to footprint
    back_h = snap(footprint_h - front_h)

    return front_h, back_h


# =============================================================================
# GENERIC BAND LAYOUT
# =============================================================================

def layout_band(
    rooms: List[RoomSpec],
    band_x: float,
    band_y: float,
    band_w: float,
    band_h: float,
) -> List[RoomRect]:
    """Lay out rooms left-to-right within a horizontal band.

    Each room spans the full band height. Width = target_area / band_h.
    After initial sizing, widths are scaled to fill the band exactly.
    All coordinates snapped to 0.5' grid.
    """
    if not rooms:
        return []

    result = []
    raw_widths = []

    for room in rooms:
        # Width from target area, respecting min dimensions
        w = room.target_area / band_h if band_h > 0 else 3.0
        mins = MIN_DIMENSIONS.get(room.room_type, (3, 3))
        min_w = mins[0]
        min_h = mins[1]

        # If band_h is less than min_h for this room, we accept it
        # but ensure width meets minimum
        w = max(w, min_w)
        raw_widths.append(w)

    # Scale widths to fit band_w exactly
    total_raw = sum(raw_widths)
    if total_raw > 0:
        scale = band_w / total_raw
        scaled_widths = [w * scale for w in raw_widths]
    else:
        scaled_widths = [band_w / len(rooms)] * len(rooms)

    # Re-enforce minimum widths after scaling and re-normalize
    scaled_widths = _enforce_min_widths(scaled_widths, rooms, band_w)

    # Place rooms left-to-right
    cursor_x = band_x
    for i, room in enumerate(rooms):
        rw = snap(scaled_widths[i])
        rh = band_h
        rx = snap(cursor_x)
        ry = band_y

        # Ensure last room fills to the edge exactly
        if i == len(rooms) - 1:
            rw = snap(band_x + band_w - rx)

        result.append(RoomRect(
            name=room.name,
            room_type=room.room_type,
            zone=room.zone,
            x=rx, y=ry, w=rw, h=rh,
        ))
        cursor_x = rx + rw

    return result


def _enforce_min_widths(
    widths: List[float],
    rooms: List[RoomSpec],
    total_w: float,
    passes: int = 3,
) -> List[float]:
    """Enforce minimum widths. Steal from larger rooms if needed."""
    for _ in range(passes):
        deficit = 0.0
        for i, room in enumerate(rooms):
            mins = MIN_DIMENSIONS.get(room.room_type, (3, 3))
            min_w = mins[0]
            if widths[i] < min_w:
                deficit += min_w - widths[i]
                widths[i] = min_w

        if deficit <= 0:
            break

        # Distribute deficit by shrinking rooms that can afford it
        shrinkable = [(i, widths[i]) for i, room in enumerate(rooms)
                      if widths[i] > MIN_DIMENSIONS.get(room.room_type, (3, 3))[0] + 1.0]
        if not shrinkable:
            break
        total_shrinkable = sum(w for _, w in shrinkable)
        for idx, w in shrinkable:
            widths[idx] -= deficit * (w / total_shrinkable)

    # Final normalization to exactly fill total_w
    current_total = sum(widths)
    if current_total > 0 and abs(current_total - total_w) > 0.1:
        factor = total_w / current_total
        widths = [w * factor for w in widths]

    return widths


# =============================================================================
# FRONT BAND LAYOUT
# =============================================================================

def layout_front_band(
    clusters: Dict[str, List[RoomSpec]],
    band_x: float,
    band_y: float,
    band_w: float,
    band_h: float,
) -> List[RoomRect]:
    """Layout the front (public) band with entry as a sub-block.

    Layout strategy:
    - Entry occupies a sub-block at front-left (doesn't span full band height)
    - Living hub fills the center (kitchen + living + dining, open-plan)
    - Service rooms stacked at front-right if 2+, else inline

    Entry sub-block:
    +--------+-------------------------------------------+--------+
    |        |                                           | Svc 1  |
    | Entry  |     Kitchen | Living | Dining             |--------|
    | 6x8    |     (open plan, full band height)         | Svc 2  |
    +--------+-------------------------------------------+--------+
    """
    result = []

    # Sort living hub rooms
    hub = clusters["living_hub"]
    hub_order = {
        RoomType.KITCHEN: 0,
        RoomType.LIVING: 1,
        RoomType.DINING: 2,
        RoomType.FAMILY_ROOM: 3,
    }
    hub_sorted = sorted(hub, key=lambda r: hub_order.get(r.room_type, 5))

    # Sort service rooms
    service = clusters["service"]
    service_order = {
        RoomType.HALF_BATH: 0,
        RoomType.LAUNDRY: 1,
        RoomType.PANTRY: 2,
    }
    service_sorted = sorted(service, key=lambda r: service_order.get(r.room_type, 5))

    # Calculate service column width (if stacking)
    svc_col_w = 0.0
    if len(service_sorted) >= 2:
        svc_total_area = sum(r.target_area for r in service_sorted)
        svc_col_w = svc_total_area / band_h if band_h > 0 else 5.0
        svc_col_w = max(svc_col_w, 4.0)
        svc_col_w = min(svc_col_w, 8.0)
        svc_col_w = snap(svc_col_w)

    # Calculate entry sub-block dimensions
    entry_rooms = clusters["entry"]
    entry_w = 0.0
    if entry_rooms:
        entry_spec = entry_rooms[0]
        # Entry gets a reasonable proportion — aim for ~1.5:1 aspect
        entry_target_h = min(band_h, max(6.0, math.sqrt(entry_spec.target_area / 1.5)))
        entry_w = entry_spec.target_area / entry_target_h if entry_target_h > 0 else 6.0
        entry_w = max(entry_w, 5.0)  # at least 5' wide
        entry_w = min(entry_w, 8.0)  # at most 8' wide
        entry_w = snap(entry_w)
        entry_h = snap(entry_target_h)

        result.append(RoomRect(
            name=entry_spec.name,
            room_type=entry_spec.room_type,
            zone=entry_spec.zone,
            x=band_x, y=band_y, w=entry_w, h=entry_h,
        ))

    # Hub region: from entry right edge to service left edge
    hub_x = snap(band_x + entry_w)
    hub_w = snap(band_w - entry_w - svc_col_w)

    if len(service_sorted) == 1:
        # Single service room: add it inline with the hub
        hub_rooms_inline = hub_sorted + service_sorted
        hub_rects = layout_band(hub_rooms_inline, hub_x, band_y, hub_w + svc_col_w, band_h)
        result.extend(hub_rects)
    elif hub_sorted:
        # Layout hub rooms in main area
        hub_rects = layout_band(hub_sorted, hub_x, band_y, hub_w, band_h)
        result.extend(hub_rects)

        # Stack service rooms in right column
        if service_sorted and svc_col_w > 0:
            svc_x = snap(hub_x + hub_w)
            svc_rects = _stack_rooms_vertically(
                service_sorted, svc_x, band_y, svc_col_w, band_h,
            )
            result.extend(svc_rects)
    else:
        # No hub rooms (unlikely but handle)
        all_front = entry_rooms + service_sorted
        if all_front:
            result = layout_band(all_front, band_x, band_y, band_w, band_h)

    return result


def _stack_rooms_vertically(
    rooms: List[RoomSpec],
    col_x: float,
    col_y: float,
    col_w: float,
    col_h: float,
) -> List[RoomRect]:
    """Stack rooms top-to-bottom in a vertical column.

    Each room gets width=col_w, heights scaled to fill col_h.
    """
    if not rooms:
        return []

    result = []
    heights = []
    for room in rooms:
        h = room.target_area / col_w if col_w > 0 else 5.0
        mins = MIN_DIMENSIONS.get(room.room_type, (3, 3))
        h = max(h, mins[1])
        heights.append(h)

    # Scale heights to fill column
    total_h = sum(heights)
    if total_h > 0:
        scale = col_h / total_h
        heights = [h * scale for h in heights]

    cursor_y = col_y
    for i, room in enumerate(rooms):
        rh = snap(heights[i])
        ry = snap(cursor_y)

        if i == len(rooms) - 1:
            rh = snap(col_y + col_h - ry)

        result.append(RoomRect(
            name=room.name,
            room_type=room.room_type,
            zone=room.zone,
            x=col_x, y=ry, w=col_w, h=rh,
        ))
        cursor_y = ry + rh

    return result


# =============================================================================
# BACK BAND LAYOUT
# =============================================================================

def layout_back_band(
    clusters: Dict[str, List[RoomSpec]],
    band_x: float,
    band_y: float,
    band_w: float,
    band_h: float,
    hallway_width: float = 3.5,
) -> List[RoomRect]:
    """Layout the back (private) band: Master Suite | Hallway | Bedrooms.

    Master suite at back-left. Short hallway corridor (3.5' wide) connects
    to bedrooms. Bathrooms placed adjacent to bedrooms.
    All bedrooms touch the north (top) exterior wall for egress.
    """
    master_rooms = clusters["master_suite"]
    wing_rooms = clusters["bedroom_wing"]

    # If no private rooms, nothing to do
    if not master_rooms and not wing_rooms:
        return []

    # Order master suite: master bed, then master bath, then closet
    master_order = {
        RoomType.MASTER_BEDROOM: 0,
        RoomType.MASTER_BATH: 1,
        RoomType.WALK_IN_CLOSET: 2,
    }
    master_sorted = sorted(master_rooms, key=lambda r: master_order.get(r.room_type, 5))

    # Order bedroom wing: bedrooms interspersed with bathrooms
    bedrooms = [r for r in wing_rooms if r.room_type in (RoomType.BEDROOM, RoomType.OFFICE)]
    baths = [r for r in wing_rooms if r.room_type == RoomType.BATHROOM]
    other_wing = [r for r in wing_rooms
                  if r.room_type not in (RoomType.BEDROOM, RoomType.BATHROOM,
                                         RoomType.HALLWAY, RoomType.OFFICE)]

    # Determine if we need a hallway
    total_private = len(master_rooms) + len(bedrooms)
    need_hallway = total_private >= 3 and len(bedrooms) >= 1

    # Build ordered room list for the back band
    ordered = list(master_sorted)

    if need_hallway:
        # Create a hallway spec — area will be calculated from corridor dimensions
        hall_area = hallway_width * band_h
        hall_spec = RoomSpec(
            name="Hallway",
            room_type=RoomType.HALLWAY,
            target_area=hall_area,
            zone=Zone.CIRCULATION,
        )
        ordered.append(hall_spec)

    # Interleave bedrooms and bathrooms
    # Pattern: bedroom, bathroom, bedroom (or bedroom, bedroom, bathroom)
    wing_ordered = []
    bath_idx = 0
    for i, br in enumerate(bedrooms):
        wing_ordered.append(br)
        # Place a bathroom after every 1-2 bedrooms
        if bath_idx < len(baths) and (i % 2 == 0 or i == len(bedrooms) - 1):
            wing_ordered.append(baths[bath_idx])
            bath_idx += 1

    # Add remaining baths and other rooms
    while bath_idx < len(baths):
        wing_ordered.append(baths[bath_idx])
        bath_idx += 1
    wing_ordered.extend(other_wing)

    ordered.extend(wing_ordered)

    if not ordered:
        return []

    # Check if we should do a sub-layout for master suite (bath stacked under bed)
    if len(master_sorted) >= 2:
        return _layout_back_with_master_suite(
            master_sorted, need_hallway, hallway_width, wing_ordered,
            band_x, band_y, band_w, band_h,
        )

    return layout_band(ordered, band_x, band_y, band_w, band_h)


def _layout_back_with_master_suite(
    master_rooms: List[RoomSpec],
    need_hallway: bool,
    hallway_width: float,
    wing_rooms: List[RoomSpec],
    band_x: float,
    band_y: float,
    band_w: float,
    band_h: float,
) -> List[RoomRect]:
    """Layout back band with master suite as a sub-block.

    Master bedroom takes full band height on the left.
    Master bath + closet stack beside it.
    Then hallway corridor, then bedrooms.
    """
    result = []

    # Master bedroom — target width from area
    mbr = master_rooms[0]  # master bedroom
    mbr_w = mbr.target_area / band_h if band_h > 0 else 12.0
    mbr_w = max(mbr_w, MIN_DIMENSIONS.get(mbr.room_type, (12, 12))[0])
    mbr_w = snap(mbr_w)

    result.append(RoomRect(
        name=mbr.name,
        room_type=mbr.room_type,
        zone=mbr.zone,
        x=band_x, y=band_y, w=mbr_w, h=band_h,
    ))

    # Master bath + closet stacked vertically beside master bedroom
    secondary = master_rooms[1:]  # bath and/or closet
    if secondary:
        sec_total_area = sum(r.target_area for r in secondary)
        sec_col_w = sec_total_area / band_h if band_h > 0 else 6.0
        # Enforce minimums
        for sr in secondary:
            mins = MIN_DIMENSIONS.get(sr.room_type, (5, 5))
            sec_col_w = max(sec_col_w, mins[0])
        sec_col_w = snap(sec_col_w)

        sec_x = snap(band_x + mbr_w)
        sec_cursor_y = band_y
        sec_heights = []

        for room in secondary:
            h = room.target_area / sec_col_w if sec_col_w > 0 else 7.0
            mins = MIN_DIMENSIONS.get(room.room_type, (5, 5))
            h = max(h, mins[1])
            sec_heights.append(h)

        # Scale to fill band height
        total_sh = sum(sec_heights)
        if total_sh > 0:
            sh_scale = band_h / total_sh
            sec_heights = [h * sh_scale for h in sec_heights]

        for i, room in enumerate(secondary):
            rh = snap(sec_heights[i])
            ry = snap(sec_cursor_y)
            if i == len(secondary) - 1:
                rh = snap(band_y + band_h - ry)

            result.append(RoomRect(
                name=room.name,
                room_type=room.room_type,
                zone=room.zone,
                x=sec_x, y=ry, w=sec_col_w, h=rh,
            ))
            sec_cursor_y = ry + rh

        master_total_w = mbr_w + sec_col_w
    else:
        master_total_w = mbr_w

    # Hallway corridor
    remaining_x = snap(band_x + master_total_w)
    remaining_w = snap(band_w - master_total_w)

    if need_hallway and remaining_w > hallway_width + 6.0:
        hall_w = snap(hallway_width)
        result.append(RoomRect(
            name="Hallway",
            room_type=RoomType.HALLWAY,
            zone=Zone.CIRCULATION,
            x=remaining_x, y=band_y, w=hall_w, h=band_h,
        ))
        remaining_x = snap(remaining_x + hall_w)
        remaining_w = snap(band_x + band_w - remaining_x)

    # Wing rooms fill the rest
    if wing_rooms and remaining_w > 0:
        wing_rects = _layout_bedroom_wing(
            wing_rooms, remaining_x, band_y, remaining_w, band_h,
        )
        result.extend(wing_rects)

    return result


def _layout_bedroom_wing(
    wing_rooms: List[RoomSpec],
    wing_x: float,
    wing_y: float,
    wing_w: float,
    wing_h: float,
) -> List[RoomRect]:
    """Layout bedroom wing with paired columns: bedroom (top) + bath (bottom).

    When there are bathrooms, pair each with an adjacent bedroom vertically:
    - Bedrooms take the top portion (touching north wall for egress)
    - Bathrooms take the bottom portion

    When few rooms, use simple left-to-right layout.
    """
    bedrooms = [r for r in wing_rooms if r.room_type == RoomType.BEDROOM]
    baths = [r for r in wing_rooms if r.room_type == RoomType.BATHROOM]
    others = [r for r in wing_rooms
              if r.room_type not in (RoomType.BEDROOM, RoomType.BATHROOM, RoomType.HALLWAY)]

    # If very few rooms or no bathrooms, simple layout
    if len(wing_rooms) <= 2 or not baths:
        ordered = []
        bath_idx = 0
        for br in bedrooms:
            ordered.append(br)
            if bath_idx < len(baths):
                ordered.append(baths[bath_idx])
                bath_idx += 1
        while bath_idx < len(baths):
            ordered.append(baths[bath_idx])
            bath_idx += 1
        ordered.extend(others)
        return layout_band(ordered, wing_x, wing_y, wing_w, wing_h)

    # Paired column layout: each bedroom paired with a bath
    # Build pairs: [(bedroom, bath_or_None), ...]
    result = []
    pairs = []
    bath_queue = list(baths)

    for br in bedrooms:
        if bath_queue:
            pairs.append((br, bath_queue.pop(0)))
        else:
            pairs.append((br, None))

    # Collect unpaired bedrooms and remaining rooms
    unpaired_bedrooms = [br for br, bath in pairs if bath is None]
    paired = [(br, bath) for br, bath in pairs if bath is not None]
    remaining = list(bath_queue) + others

    # Try to pair unpaired bedrooms with remaining rooms (office, etc.)
    extra_pairs = []
    leftover = list(remaining)
    for br in unpaired_bedrooms:
        if leftover:
            extra_pairs.append((br, leftover.pop(0)))
        else:
            # Try to pair consecutive unpaired bedrooms together
            pass

    # Any truly unpaired bedrooms become standalone
    standalone_bedrooms = [br for br in unpaired_bedrooms
                           if not any(br is p[0] or br is p[1] for p in extra_pairs)]

    # Remaining leftover rooms pair among themselves
    while len(leftover) >= 2:
        extra_pairs.append((leftover.pop(0), leftover.pop(0)))

    standalone = standalone_bedrooms + leftover

    # Use paired list (bedroom+bath pairs) going forward
    pairs = paired

    # Calculate column widths — bedroom+bath pairs, extra pairs, standalone
    n_cols = len(pairs) + len(extra_pairs) + len(standalone)
    if n_cols == 0:
        return []

    col_widths = []
    all_specs = []  # track what's in each column for min-width

    for br, bath in pairs:
        combined_area = br.target_area + (bath.target_area if bath else 0)
        w = combined_area / wing_h if wing_h > 0 else 10.0
        min_w = MIN_DIMENSIONS.get(br.room_type, (9, 10))[0]
        if bath:
            min_w = max(min_w, MIN_DIMENSIONS.get(bath.room_type, (5, 7))[0])
        w = max(w, min_w)
        col_widths.append(w)
        all_specs.append(br)

    for top_room, bot_room in extra_pairs:
        combined_area = top_room.target_area + bot_room.target_area
        w = combined_area / wing_h if wing_h > 0 else 10.0
        min_w = max(
            MIN_DIMENSIONS.get(top_room.room_type, (3, 3))[0],
            MIN_DIMENSIONS.get(bot_room.room_type, (3, 3))[0],
        )
        w = max(w, min_w)
        col_widths.append(w)
        all_specs.append(top_room)

    for room in standalone:
        w = room.target_area / wing_h if wing_h > 0 else 5.0
        mins = MIN_DIMENSIONS.get(room.room_type, (3, 3))
        w = max(w, mins[0])
        col_widths.append(w)
        all_specs.append(room)

    # Scale to fit wing width
    total_w = sum(col_widths)
    if total_w > 0:
        scale = wing_w / total_w
        col_widths = [w * scale for w in col_widths]
    col_widths = _enforce_min_widths(col_widths, all_specs, wing_w)

    # Place columns
    cursor_x = wing_x
    col_idx = 0

    for br, bath in pairs:
        cw = snap(col_widths[col_idx])
        cx = snap(cursor_x)

        if bath:
            # Split vertically: bathroom at bottom, bedroom at top
            bath_h_target = bath.target_area / cw if cw > 0 else 7.0
            bath_h_target = max(bath_h_target, MIN_DIMENSIONS.get(bath.room_type, (5, 7))[1])
            bath_h_target = min(bath_h_target, wing_h * 0.45)  # bath max 45% of band
            bath_h = snap(bath_h_target)
            br_h = snap(wing_h - bath_h)

            # Bedroom on top (touches north wall)
            result.append(RoomRect(
                name=br.name,
                room_type=br.room_type,
                zone=br.zone,
                x=cx, y=snap(wing_y + bath_h), w=cw, h=br_h,
            ))
            # Bathroom on bottom
            result.append(RoomRect(
                name=bath.name,
                room_type=bath.room_type,
                zone=bath.zone,
                x=cx, y=wing_y, w=cw, h=bath_h,
            ))
        else:
            # Bedroom spans full height
            result.append(RoomRect(
                name=br.name,
                room_type=br.room_type,
                zone=br.zone,
                x=cx, y=wing_y, w=cw, h=wing_h,
            ))

        cursor_x = cx + cw
        col_idx += 1

    # Place extra paired columns (non-bedroom+bath pairs)
    for top_room, bot_room in extra_pairs:
        cw = snap(col_widths[col_idx])
        cx = snap(cursor_x)

        # Split vertically: larger room on top, smaller on bottom
        if top_room.target_area >= bot_room.target_area:
            big, small = top_room, bot_room
        else:
            big, small = bot_room, top_room

        small_h_target = small.target_area / cw if cw > 0 else 7.0
        small_h_target = max(small_h_target, MIN_DIMENSIONS.get(small.room_type, (3, 3))[1])
        small_h_target = min(small_h_target, wing_h * 0.45)
        small_h = snap(small_h_target)
        big_h = snap(wing_h - small_h)

        # Bigger room on top (touches north wall), smaller on bottom
        result.append(RoomRect(
            name=big.name,
            room_type=big.room_type,
            zone=big.zone,
            x=cx, y=snap(wing_y + small_h), w=cw, h=big_h,
        ))
        result.append(RoomRect(
            name=small.name,
            room_type=small.room_type,
            zone=small.zone,
            x=cx, y=wing_y, w=cw, h=small_h,
        ))

        cursor_x = cx + cw
        col_idx += 1

    # Place standalone rooms
    for room in standalone:
        cw = snap(col_widths[col_idx])
        cx = snap(cursor_x)

        # Last column fills to edge
        if col_idx == n_cols - 1:
            cw = snap(wing_x + wing_w - cx)

        result.append(RoomRect(
            name=room.name,
            room_type=room.room_type,
            zone=room.zone,
            x=cx, y=wing_y, w=cw, h=wing_h,
        ))
        cursor_x = cx + cw
        col_idx += 1

    return result


# =============================================================================
# WALL GENERATION (with open-plan support)
# =============================================================================

def generate_walls(
    rooms: List[RoomRect],
    footprint_w: float,
    footprint_h: float,
    open_connections: Set[Tuple[str, str]],
) -> List[WallSegment]:
    """Generate wall segments from room layout.

    1. Exterior walls (footprint boundary)
    2. Interior walls (shared room edges, deduplicated)
    3. SKIP walls between open-plan connected rooms
    """
    walls = []

    # Exterior walls
    walls.append(WallSegment(0, 0, footprint_w, 0, is_exterior=True))          # South
    walls.append(WallSegment(footprint_w, 0, footprint_w, footprint_h, is_exterior=True))  # East
    walls.append(WallSegment(footprint_w, footprint_h, 0, footprint_h, is_exterior=True))  # North
    walls.append(WallSegment(0, footprint_h, 0, 0, is_exterior=True))          # West

    # Interior walls: shared edges between rooms, deduplicated
    seen_edges = set()
    tol = 0.25

    for i, a in enumerate(rooms):
        for j, b in enumerate(rooms):
            if j <= i:
                continue

            # Skip walls between open-plan pairs
            if is_open_pair(a.name, b.name, open_connections):
                continue

            seg = a.shared_edge_segment(b, tol)
            if seg is None:
                continue

            (x1, y1), (x2, y2) = seg
            x1, y1, x2, y2 = snap(x1), snap(y1), snap(x2), snap(y2)

            # Normalize edge direction for dedup
            if (x1, y1) > (x2, y2):
                x1, y1, x2, y2 = x2, y2, x1, y1

            edge_key = (round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1))
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)

            # Skip edges that overlap with exterior walls
            is_on_exterior = False
            if abs(x1 - x2) < tol:  # Vertical
                if abs(x1) < tol or abs(x1 - footprint_w) < tol:
                    is_on_exterior = True
            if abs(y1 - y2) < tol:  # Horizontal
                if abs(y1) < tol or abs(y1 - footprint_h) < tol:
                    is_on_exterior = True

            if not is_on_exterior:
                walls.append(WallSegment(x1, y1, x2, y2, is_exterior=False))

    return walls


# =============================================================================
# DOOR PLACEMENT (with open-plan support)
# =============================================================================

def place_doors(
    rooms: List[RoomRect],
    walls: List[WallSegment],
    footprint_w: float,
    footprint_h: float,
    open_connections: Set[Tuple[str, str]],
) -> List[DoorPlacement]:
    """Place doors on interior walls between adjacent rooms and one entry door.

    Rules:
    - Every room gets at least one door
    - Door placed at midpoint of shared wall
    - Entry door on an exterior wall (south preferred)
    - Skip open-plan connections (no wall = no door needed)
    - Door specs from knowledge tables
    """
    doors = []
    rooms_with_doors = set()
    tol = 0.25

    # Find entry room and place entry door on south wall
    entry_room = None
    for room in rooms:
        if room.room_type == RoomType.ENTRY:
            entry_room = room
            break
    if entry_room is None:
        for room in rooms:
            if room.room_type in (RoomType.LIVING, RoomType.KITCHEN):
                entry_room = room
                break
    if entry_room is None and rooms:
        entry_room = rooms[0]

    if entry_room:
        # Place entry door on south exterior wall if room touches it
        if abs(entry_room.y) < tol:
            door_x = snap(entry_room.cx)
            door_y = 0
            ext_wall = None
            for w in walls:
                if w.is_exterior and w.is_horizontal and abs(w.y1) < tol:
                    if min(w.x1, w.x2) <= door_x <= max(w.x1, w.x2):
                        ext_wall = w
                        break
            if ext_wall:
                w_in, h_in = get_door_spec(entry_room.room_type, is_entry=True)
                doors.append(DoorPlacement(
                    location=(door_x, door_y),
                    wall_segment=ext_wall,
                    width_inches=w_in, height_inches=h_in,
                    room_a="Exterior", room_b=entry_room.name,
                ))
                rooms_with_doors.add(entry_room.name)
        elif abs(entry_room.x) < tol:
            door_x = 0
            door_y = snap(entry_room.cy)
            ext_wall = None
            for w in walls:
                if w.is_exterior and w.is_vertical and abs(w.x1) < tol:
                    ext_wall = w
                    break
            if ext_wall:
                w_in, h_in = get_door_spec(entry_room.room_type, is_entry=True)
                doors.append(DoorPlacement(
                    location=(door_x, door_y),
                    wall_segment=ext_wall,
                    width_inches=w_in, height_inches=h_in,
                    room_a="Exterior", room_b=entry_room.name,
                ))
                rooms_with_doors.add(entry_room.name)

    # Interior doors: for each pair of adjacent rooms, place a door on their shared wall
    for i, a in enumerate(rooms):
        for j, b in enumerate(rooms):
            if j <= i:
                continue

            # Skip open-plan pairs — they have no wall, so no door needed
            if is_open_pair(a.name, b.name, open_connections):
                continue

            seg = a.shared_edge_segment(b, tol)
            if seg is None:
                continue

            both_have = a.name in rooms_with_doors and b.name in rooms_with_doors
            weight = adjacency_weight(a.room_type, b.room_type)
            if both_have and weight <= 0:
                continue

            (x1, y1), (x2, y2) = seg
            mid_x = snap((x1 + x2) / 2)
            mid_y = snap((y1 + y2) / 2)

            # Find the interior wall for this edge
            matching_wall = None
            for w in walls:
                if w.is_exterior:
                    continue
                if w.is_horizontal and abs(w.y1 - mid_y) < tol:
                    if min(w.x1, w.x2) - tol <= mid_x <= max(w.x1, w.x2) + tol:
                        matching_wall = w
                        break
                elif w.is_vertical and abs(w.x1 - mid_x) < tol:
                    if min(w.y1, w.y2) - tol <= mid_y <= max(w.y1, w.y2) + tol:
                        matching_wall = w
                        break

            if matching_wall is None:
                continue

            smaller = a if a.area < b.area else b
            w_in, h_in = get_door_spec(smaller.room_type)

            doors.append(DoorPlacement(
                location=(mid_x, mid_y),
                wall_segment=matching_wall,
                width_inches=w_in, height_inches=h_in,
                room_a=a.name, room_b=b.name,
            ))
            rooms_with_doors.add(a.name)
            rooms_with_doors.add(b.name)

    return doors


# =============================================================================
# WINDOW PLACEMENT
# =============================================================================

def place_windows(
    rooms: List[RoomRect],
    walls: List[WallSegment],
    footprint_w: float,
    footprint_h: float,
) -> List[WindowPlacement]:
    """Place windows on exterior walls per glazing rules.

    Each habitable room with exterior wall exposure gets windows.
    Window count based on glazing ratio from WINDOW_RULES.
    """
    windows = []
    tol = 0.5

    for room in rooms:
        rules = WINDOW_RULES.get(room.room_type)
        if rules is None:
            continue

        glazing_ratio = rules["glazing_ratio"]
        sill_height = rules["sill_height"]

        # Find exterior wall segments this room touches
        exterior_edges = []

        if abs(room.y) < tol:
            exterior_edges.append(("south", room.x, 0, room.right, 0))
        if abs(room.top - footprint_h) < tol:
            exterior_edges.append(("north", room.x, footprint_h, room.right, footprint_h))
        if abs(room.x) < tol:
            exterior_edges.append(("west", 0, room.y, 0, room.top))
        if abs(room.right - footprint_w) < tol:
            exterior_edges.append(("east", footprint_w, room.y, footprint_w, room.top))

        if not exterior_edges:
            continue

        target_glazing = room.area * glazing_ratio
        window_w_ft = 3.0
        window_h_ft = 4.0
        window_area = window_w_ft * window_h_ft
        num_windows = max(1, round(target_glazing / window_area))

        windows_per_edge = max(1, num_windows // len(exterior_edges))

        for direction, ex1, ey1, ex2, ey2 in exterior_edges:
            ext_wall = None
            for w in walls:
                if not w.is_exterior:
                    continue
                if direction in ("south", "north") and w.is_horizontal:
                    if abs(w.y1 - ey1) < tol:
                        ext_wall = w
                        break
                elif direction in ("east", "west") and w.is_vertical:
                    if abs(w.x1 - ex1) < tol:
                        ext_wall = w
                        break

            if ext_wall is None:
                continue

            if direction in ("south", "north"):
                edge_len = ex2 - ex1
                spacing = edge_len / (windows_per_edge + 1)
                for n in range(windows_per_edge):
                    wx = snap(ex1 + spacing * (n + 1))
                    wy = ey1
                    windows.append(WindowPlacement(
                        location=(wx, wy),
                        wall_segment=ext_wall,
                        width_inches=36.0,
                        height_inches=48.0,
                        sill_height_inches=sill_height,
                        room_name=room.name,
                    ))
            else:
                edge_len = ey2 - ey1
                spacing = edge_len / (windows_per_edge + 1)
                for n in range(windows_per_edge):
                    wx = ex1
                    wy = snap(ey1 + spacing * (n + 1))
                    windows.append(WindowPlacement(
                        location=(wx, wy),
                        wall_segment=ext_wall,
                        width_inches=36.0,
                        height_inches=48.0,
                        sill_height_inches=sill_height,
                        room_name=room.name,
                    ))

    return windows


# =============================================================================
# MAIN LAYOUT FUNCTION
# =============================================================================

def generate_layout(
    rooms: List[RoomSpec],
    footprint_w: float,
    footprint_h: float,
    hallway_width: float = 3.5,
) -> FloorPlan:
    """Stage 2: Generate complete floor plan layout from room specs.

    Uses strip-based template algorithm:
    - Front band (south): entry + living hub + service
    - Back band (north): master suite + hallway + bedrooms

    Args:
        rooms: Room specifications from Stage 1
        footprint_w: Footprint width in feet
        footprint_h: Footprint height (depth) in feet
        hallway_width: Hallway width in feet (default 3.5')

    Returns:
        FloorPlan with rooms, walls, doors, windows
    """
    # 1. Classify rooms into clusters
    clusters = classify_rooms(rooms)

    # 2. Calculate band split
    front_h, back_h = calculate_band_split(footprint_h, clusters)

    # 3. Layout front band (public zone, bottom)
    front_rooms = layout_front_band(
        clusters,
        band_x=0, band_y=0,
        band_w=footprint_w, band_h=front_h,
    )

    # 4. Layout back band (private zone, top)
    back_rooms = layout_back_band(
        clusters,
        band_x=0, band_y=front_h,
        band_w=footprint_w, band_h=back_h,
        hallway_width=hallway_width,
    )

    all_rooms = front_rooms + back_rooms

    # 5. Determine open-plan connections
    open_connections = get_open_connections(all_rooms)

    # 6. Generate walls (skip open-plan connections)
    walls = generate_walls(all_rooms, footprint_w, footprint_h, open_connections)

    # 7. Place doors (skip open-plan pairs)
    doors = place_doors(all_rooms, walls, footprint_w, footprint_h, open_connections)

    # 8. Place windows
    windows = place_windows(all_rooms, walls, footprint_w, footprint_h)

    # Count bedrooms/bathrooms
    bed_count = sum(1 for r in all_rooms if r.room_type in (RoomType.MASTER_BEDROOM, RoomType.BEDROOM))
    bath_count = sum(1 for r in all_rooms if r.room_type in (RoomType.BATHROOM, RoomType.MASTER_BATH, RoomType.HALF_BATH))

    return FloorPlan(
        rooms=all_rooms,
        walls=walls,
        doors=doors,
        windows=windows,
        footprint_width=footprint_w,
        footprint_height=footprint_h,
        total_area=footprint_w * footprint_h,
        bedrooms=bed_count,
        bathrooms=bath_count,
    )
