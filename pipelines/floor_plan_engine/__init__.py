"""
FloorPlanEngine — Architecturally Intelligent Layout Generation

3-stage pipeline:
  Natural Language → [Program] → [Layout] → [Revit] → Complete Model

Usage:
    from floor_plan_engine import generate_floor_plan
    plan = generate_floor_plan(total_area=1200, bedrooms=2)
    print(plan.ascii_preview())

    # Execute in Revit:
    from floor_plan_engine import execute_in_revit
    result = execute_in_revit(plan)
"""

from .models import (
    FloorPlan, RoomRect, WallSegment, DoorPlacement, WindowPlacement,
    RoomType, Zone, FloorPlanAnalysis,
)
from .program import extract_program
from .layout import generate_layout
from .validation import validate_floor_plan
from .revit_bridge import execute_in_revit
from .reasoning import think_through, critique, narrate_walkthrough, build_connectivity_graph
from .builder import FloorPlanBuilder

from typing import Optional, List, Dict, Any


def generate_floor_plan(
    total_area: float = 1200,
    bedrooms: int = 2,
    bathrooms: Optional[int] = None,
    extra_rooms: Optional[List[Dict[str, Any]]] = None,
    validate: bool = True,
    verbose: bool = False,
) -> FloorPlan:
    """Generate a complete floor plan from high-level parameters.

    Args:
        total_area: Total house area in sq ft (800-3000)
        bedrooms: Number of bedrooms (1-4)
        bathrooms: Number of bathrooms (auto if None)
        extra_rooms: Additional rooms [{"type": "office", "name": "Home Office"}]
        validate: Run validation checks
        verbose: Print progress

    Returns:
        FloorPlan with rooms, walls, doors, windows ready for Revit execution
    """
    # Stage 1: Program extraction
    program = extract_program(
        total_area=total_area,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        extra_rooms=extra_rooms,
    )

    if verbose:
        print(f"Stage 1: {len(program['rooms'])} rooms, tier={program['tier']}")
        print(f"  Footprint: {program['footprint'][0]}' x {program['footprint'][1]}'")
        for r in program['rooms']:
            print(f"  - {r.name}: {r.target_area} SF ({r.zone.value})")

    # Stage 2: Layout generation
    plan = generate_layout(
        rooms=program["rooms"],
        footprint_w=program["footprint"][0],
        footprint_h=program["footprint"][1],
    )

    if verbose:
        print(f"\nStage 2: Layout complete")
        print(f"  {len(plan.rooms)} rooms, {len(plan.walls)} walls")
        print(f"  {len(plan.doors)} doors, {len(plan.windows)} windows")

    # Validation
    if validate:
        report = validate_floor_plan(plan)
        if verbose:
            print(f"\nValidation: {report['summary']}")
            for err in report["errors"]:
                print(f"  ERROR: {err['message']}")
            for warn in report["warnings"][:5]:
                print(f"  WARN: {warn['message']}")

    return plan


__all__ = [
    "generate_floor_plan",
    "execute_in_revit",
    "validate_floor_plan",
    # Models
    "FloorPlan",
    "FloorPlanAnalysis",
    "RoomRect",
    "WallSegment",
    "DoorPlacement",
    "WindowPlacement",
    "RoomType",
    "Zone",
    # v3: Reasoning
    "think_through",
    "critique",
    "narrate_walkthrough",
    "build_connectivity_graph",
    # v3: Builder
    "FloorPlanBuilder",
]
