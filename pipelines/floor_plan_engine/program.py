"""
Stage 1: Program Extraction

Converts user input (total_area, bedrooms, bathrooms) into a structured
room list with target areas. No LLM call — pure rule-based.
"""

from typing import List, Optional, Dict, Any

from .models import RoomSpec, RoomType, Zone
from .knowledge import (
    ROOM_SIZING, ZONE_MAP, get_default_program,
)


def determine_tier(total_area: float) -> str:
    """Determine house tier from total area."""
    if total_area <= 1200:
        return "small"
    elif total_area <= 2200:
        return "medium"
    else:
        return "large"


def calculate_footprint(total_area: float, aspect_ratio: float = 1.3) -> tuple:
    """Calculate footprint width and height from area and aspect ratio.

    Returns (width, height) in feet. Width is the longer dimension.
    """
    # area = width * height, width = height * aspect_ratio
    height = (total_area / aspect_ratio) ** 0.5
    width = height * aspect_ratio
    # Snap to 0.5' grid
    width = round(width * 2) / 2
    height = round(height * 2) / 2
    # Verify area is close
    actual = width * height
    if abs(actual - total_area) / total_area > 0.05:
        # Adjust height to hit target area
        height = round((total_area / width) * 2) / 2
    return (width, height)


def allocate_areas(
    rooms: List[tuple],
    total_area: float,
    tier: str,
) -> List[RoomSpec]:
    """Allocate areas to rooms proportionally based on sizing tables.

    Args:
        rooms: List of (RoomType, name) tuples from default program
        total_area: Target total area in sq ft
        tier: "small", "medium", or "large"

    Returns:
        List of RoomSpec with target areas allocated
    """
    # Get target areas from knowledge tables
    raw_targets = []
    for room_type, name in rooms:
        sizing = ROOM_SIZING.get(room_type)
        if sizing and tier in sizing:
            _, target, _ = sizing[tier]
        else:
            target = 50  # fallback for unknown room types
        raw_targets.append((room_type, name, target))

    # Sum raw targets
    raw_total = sum(t for _, _, t in raw_targets)
    if raw_total == 0:
        raw_total = 1

    # Scale proportionally to fit total_area
    scale = total_area / raw_total

    specs = []
    for room_type, name, target in raw_targets:
        zone = ZONE_MAP.get(room_type, Zone.PRIVATE)
        scaled_area = target * scale

        # Clamp to min/max from knowledge
        sizing = ROOM_SIZING.get(room_type)
        if sizing and tier in sizing:
            min_a, _, max_a = sizing[tier]
            scaled_area = max(min_a, min(scaled_area, max_a))

        specs.append(RoomSpec(
            name=name,
            room_type=room_type,
            target_area=round(scaled_area, 1),
            zone=zone,
        ))

    # Final adjustment: distribute any remaining area proportionally
    allocated_total = sum(s.target_area for s in specs)
    remainder = total_area - allocated_total
    if abs(remainder) > 1.0 and len(specs) > 0:
        # Add remainder to largest rooms
        large_rooms = sorted(specs, key=lambda s: s.target_area, reverse=True)
        # Distribute to top 3 rooms
        distribute_to = large_rooms[:min(3, len(large_rooms))]
        per_room = remainder / len(distribute_to)
        for spec in distribute_to:
            spec.target_area = round(spec.target_area + per_room, 1)

    return specs


def extract_program(
    total_area: float = 1200,
    bedrooms: int = 2,
    bathrooms: Optional[int] = None,
    extra_rooms: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Stage 1: Extract building program from high-level parameters.

    Args:
        total_area: Total house area in sq ft (800-3000)
        bedrooms: Number of bedrooms (1-4)
        bathrooms: Number of bathrooms (auto-determined if None)
        extra_rooms: Optional list of additional rooms, each with
                     {"type": "office", "name": "Home Office"}

    Returns:
        Dict with:
        - rooms: List[RoomSpec] — room specifications
        - footprint: (width, height) in feet
        - tier: "small" | "medium" | "large"
        - total_area: actual target area
    """
    # Clamp inputs
    total_area = max(800, min(total_area, 3000))
    bedrooms = max(1, min(bedrooms, 4))

    tier = determine_tier(total_area)
    footprint = calculate_footprint(total_area)

    # Get default room program
    program = get_default_program(bedrooms, tier)

    # Adjust bathroom count if specified
    if bathrooms is not None:
        current_baths = sum(1 for rt, _ in program if rt in (
            RoomType.BATHROOM, RoomType.MASTER_BATH, RoomType.HALF_BATH
        ))
        if bathrooms > current_baths:
            # Add extra bathrooms
            for i in range(bathrooms - current_baths):
                program.append((RoomType.BATHROOM, f"Bathroom {current_baths + i + 1}"))
        elif bathrooms < current_baths and bathrooms >= 1:
            # Remove half baths first, then full baths
            removable = [(rt, n) for rt, n in program
                        if rt in (RoomType.HALF_BATH, RoomType.BATHROOM)]
            to_remove = current_baths - bathrooms
            for rt, n in reversed(removable):
                if to_remove <= 0:
                    break
                program.remove((rt, n))
                to_remove -= 1

    # Add extra rooms if specified
    if extra_rooms:
        for room_def in extra_rooms:
            rt_str = room_def.get("type", "office")
            name = room_def.get("name", rt_str.replace("_", " ").title())
            try:
                rt = RoomType(rt_str)
            except ValueError:
                rt = RoomType.OFFICE
            program.append((rt, name))

    # Allocate areas
    room_specs = allocate_areas(program, total_area, tier)

    return {
        "rooms": room_specs,
        "footprint": footprint,
        "tier": tier,
        "total_area": total_area,
        "bedrooms": bedrooms,
        "bathrooms": sum(1 for s in room_specs if s.room_type in (
            RoomType.BATHROOM, RoomType.MASTER_BATH, RoomType.HALF_BATH
        )),
    }
