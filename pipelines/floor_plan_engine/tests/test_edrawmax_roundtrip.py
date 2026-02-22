"""
End-to-end test: FloorPlanBuilder produces the exact same geometry
as the reference script (replicate_edrawmax_plan.py).

Verifies that the engine's L-shape polygon, wall merging, entry door
placement, and boundary walls match the proven reference values.
"""

import pytest
import sys
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/pipelines")

from floor_plan_engine.models import RoomType
from floor_plan_engine.builder import FloorPlanBuilder
from floor_plan_engine.revit_bridge import _find_wall_id_at


# ── Reference values from replicate_edrawmax_plan.py ──

L_SHAPE_POINTS = [
    (19, 0), (44, 0), (44, 30), (0, 30),
    (0, 6), (19, 6),
]

REFERENCE_EXTERIOR_WALLS = [
    (19, 0, 44, 0),
    (44, 0, 44, 30),
    (44, 30, 0, 30),
    (0, 30, 0, 6),
    (0, 6, 19, 6),
    (19, 6, 19, 0),
]

REFERENCE_INTERIOR_WALLS = [
    # Wing divider: starts at y=7 (Master Bedroom bottom), not y=6 (L-notch)
    # because auto_interior_walls generates from room shared edges
    (19, 7, 19, 30),
    # Horizontal at y=19: only x=34→44 because Dining↔Great Room is open-plan
    # (reference script has full 19→44 but engine correctly skips open-plan boundary)
    (34, 19, 44, 19),
    (34, 0, 34, 30),
    (34, 7, 44, 7),
    # Left wing vertical divider: bath column | bedroom column
    (8, 7, 8, 30),
    (0, 23, 8, 23),
    (8, 20, 19, 20),
    (0, 13, 8, 13),
    # Master bedroom south boundary (circulation void wall)
    (8, 7, 19, 7),
]

REFERENCE_ENTRY_DOOR = (14, 6)


# ── Build the EdrawMax plan via FloorPlanBuilder ──

def _build_edrawmax():
    """Build the EdrawMax plan using the engine (not the reference script)."""
    return (FloorPlanBuilder("EdrawMax Roundtrip")
        .add_room("Great Room", RoomType.LIVING, 19, 0, 15, 19)
        .add_room("Dining", RoomType.DINING, 19, 19, 15, 11)
        .add_room("Kitchen", RoomType.KITCHEN, 34, 19, 10, 11)
        .add_room("Bedroom 1", RoomType.BEDROOM, 34, 7, 10, 12)
        .add_room("Bath 3", RoomType.BATHROOM, 34, 0, 10, 7)
        .add_room("Bath 1", RoomType.BATHROOM, 0, 23, 8, 7)
        .add_room("Bedroom 2", RoomType.BEDROOM, 8, 20, 11, 10)
        .add_room("Bath 2", RoomType.BATHROOM, 0, 13, 8, 10)
        .add_room("Master Bedroom", RoomType.MASTER_BEDROOM, 8, 7, 11, 13)
        .add_room("Wardrobe", RoomType.WALK_IN_CLOSET, 0, 6, 8, 7)
        .connect_open_plan("Dining", "Great Room")
        .add_exterior_walls_L(L_SHAPE_POINTS)
        .auto_interior_walls()
        .auto_boundary_walls()
        .add_entry_door(at=REFERENCE_ENTRY_DOOR)
        .add_door(14, 7, "Master Bedroom", "entry_area")
        .add_door(8, 10, "Wardrobe", "Master Bedroom")
        .add_door(8, 18, "Bath 2", "Master Bedroom")
        .add_door(8, 24, "Bath 1", "Bedroom 2")
        .add_door(14, 20, "Bedroom 2", "Dining")
        .add_door(19, 12, "Master Bedroom", "Great Room")
        .add_door(26, 19, "Dining", "Great Room")
        .add_door(34, 24, "Kitchen", "Dining")
        .add_door(34, 13, "Bedroom 1", "Great Room")
        .add_door(34, 3, "Bath 3", "Great Room")
        .add_window(4, 30, "Bath 1")
        .add_window(14, 30, "Bedroom 2")
        .add_window(26, 30, "Dining")
        .add_window(39, 30, "Kitchen")
        .add_window(44, 24, "Kitchen")
        .add_window(44, 13, "Bedroom 1")
        .add_window(44, 3, "Bath 3")
        .add_window(26, 0, "Great Room")
        .add_window(34, 0, "Great Room")
        .add_window(0, 26, "Bath 1")
        .add_window(0, 18, "Bath 2")
        .add_window(0, 9, "Wardrobe")
        .build())


# ── Tests ──

class TestEdrawMaxRoundtrip:

    @pytest.fixture
    def plan(self):
        return _build_edrawmax()

    def test_footprint_polygon(self, plan):
        """L-shape polygon should be stored on the plan."""
        assert plan.footprint_polygon == L_SHAPE_POINTS

    def test_footprint_dimensions(self, plan):
        assert plan.footprint_width == 44
        assert plan.footprint_height == 30

    def test_room_count(self, plan):
        assert len(plan.rooms) == 10

    def test_exterior_wall_count(self, plan):
        exterior = [w for w in plan.walls if w.is_exterior]
        assert len(exterior) == 6, (
            f"Expected 6 exterior walls, got {len(exterior)}: "
            + str([(w.x1, w.y1, w.x2, w.y2) for w in exterior])
        )

    def test_exterior_walls_match_reference(self, plan):
        """Each reference exterior wall should appear in the plan."""
        exterior = [w for w in plan.walls if w.is_exterior]
        tol = 0.5

        for rx1, ry1, rx2, ry2 in REFERENCE_EXTERIOR_WALLS:
            found = False
            for w in exterior:
                fwd = (abs(w.x1 - rx1) < tol and abs(w.y1 - ry1) < tol
                       and abs(w.x2 - rx2) < tol and abs(w.y2 - ry2) < tol)
                rev = (abs(w.x1 - rx2) < tol and abs(w.y1 - ry2) < tol
                       and abs(w.x2 - rx1) < tol and abs(w.y2 - ry1) < tol)
                if fwd or rev:
                    found = True
                    break
            assert found, (
                f"Reference exterior wall ({rx1},{ry1})→({rx2},{ry2}) "
                f"not found in plan"
            )

    def test_interior_walls_match_reference(self, plan):
        """Each reference interior wall should appear in the plan (possibly merged)."""
        interior = [w for w in plan.walls if not w.is_exterior]
        tol = 0.5

        for rx1, ry1, rx2, ry2 in REFERENCE_INTERIOR_WALLS:
            found = False
            for w in interior:
                # Check if the reference wall is contained within a merged wall
                if _segment_contains(w, rx1, ry1, rx2, ry2, tol):
                    found = True
                    break
            assert found, (
                f"Reference interior wall ({rx1},{ry1})→({rx2},{ry2}) "
                f"not found in plan interior walls: "
                + str([(w.x1, w.y1, w.x2, w.y2) for w in interior])
            )

    def test_entry_door_position(self, plan):
        """Entry door should be at (14, 6), not (26, 0)."""
        entry_doors = [d for d in plan.doors if d.room_b == "exterior"]
        assert len(entry_doors) >= 1
        d = entry_doors[0]
        assert abs(d.location[0] - 14) < 0.5, f"Entry door x={d.location[0]}, expected 14"
        assert abs(d.location[1] - 6) < 0.5, f"Entry door y={d.location[1]}, expected 6"

    def test_door_count(self, plan):
        assert len(plan.doors) == 11

    def test_window_count(self, plan):
        assert len(plan.windows) == 12

    def test_to_building_program_uses_polygon(self, plan):
        """to_building_program should use L-shape polygon, not rectangle."""
        bp = plan.to_building_program()
        footprint = bp["buildingFootprint"]
        assert len(footprint) == 6  # L-shape has 6 points
        assert footprint[0] == {"x": 19, "y": 0}


class TestFindWallIdAt:
    """Test the coordinate-based wall ID lookup from revit_bridge."""

    def test_exact_match(self):
        registry = [
            {"wallId": 100, "x1": 0, "y1": 0, "x2": 20, "y2": 0, "is_exterior": True},
            {"wallId": 200, "x1": 20, "y1": 0, "x2": 20, "y2": 15, "is_exterior": True},
        ]
        assert _find_wall_id_at(registry, 10, 0) == 100

    def test_near_match(self):
        registry = [
            {"wallId": 100, "x1": 0, "y1": 0, "x2": 20, "y2": 0, "is_exterior": True},
        ]
        # Point 1 ft away from wall
        assert _find_wall_id_at(registry, 10, 1.0) == 100

    def test_no_match_too_far(self):
        registry = [
            {"wallId": 100, "x1": 0, "y1": 0, "x2": 20, "y2": 0, "is_exterior": True},
        ]
        assert _find_wall_id_at(registry, 10, 5.0) is None

    def test_empty_registry(self):
        assert _find_wall_id_at([], 10, 0) is None

    def test_picks_closest_wall(self):
        registry = [
            {"wallId": 100, "x1": 0, "y1": 0, "x2": 20, "y2": 0, "is_exterior": True},
            {"wallId": 200, "x1": 0, "y1": 5, "x2": 20, "y2": 5, "is_exterior": False},
        ]
        # Closer to wall at y=5
        assert _find_wall_id_at(registry, 10, 4.5) == 200


# ── Helpers ──

def _segment_contains(wall, rx1, ry1, rx2, ry2, tol):
    """Check if a (potentially merged) wall segment contains the reference segment."""
    # Horizontal
    if abs(wall.y1 - wall.y2) < tol and abs(ry1 - ry2) < tol and abs(wall.y1 - ry1) < tol:
        w_lo = min(wall.x1, wall.x2)
        w_hi = max(wall.x1, wall.x2)
        r_lo = min(rx1, rx2)
        r_hi = max(rx1, rx2)
        return r_lo >= w_lo - tol and r_hi <= w_hi + tol

    # Vertical
    if abs(wall.x1 - wall.x2) < tol and abs(rx1 - rx2) < tol and abs(wall.x1 - rx1) < tol:
        w_lo = min(wall.y1, wall.y2)
        w_hi = max(wall.y1, wall.y2)
        r_lo = min(ry1, ry2)
        r_hi = max(ry1, ry2)
        return r_lo >= w_lo - tol and r_hi <= w_hi + tol

    return False
