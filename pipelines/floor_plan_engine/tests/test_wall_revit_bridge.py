"""
Tests for wall_revit_bridge.py — WallPlan → Revit execution.

Tests:
- Wall registry building from batch results
- Coordinate-based wall lookup (exact, near, no match)
- EdrawMax WallPlan → mock Revit execution
"""

import pytest
from floor_plan_engine.wall_revit_bridge import (
    _find_wall_id_at, build_wall_registry,
)
from floor_plan_engine.wall_model import Wall, Opening, RoomLabel, WallPlan


# ── Helper: EdrawMax walls for testing ──

def make_edrawmax_registry():
    """Build a mock wall registry matching the EdrawMax plan."""
    return [
        # Exterior walls
        {"wallId": 101, "x1": 19, "y1": 0, "x2": 44, "y2": 0, "is_exterior": True},
        {"wallId": 102, "x1": 44, "y1": 0, "x2": 44, "y2": 30, "is_exterior": True},
        {"wallId": 103, "x1": 44, "y1": 30, "x2": 0, "y2": 30, "is_exterior": True},
        {"wallId": 104, "x1": 0, "y1": 30, "x2": 0, "y2": 6, "is_exterior": True},
        {"wallId": 105, "x1": 0, "y1": 6, "x2": 19, "y2": 6, "is_exterior": True},
        {"wallId": 106, "x1": 19, "y1": 6, "x2": 19, "y2": 0, "is_exterior": True},
        # Interior walls
        {"wallId": 201, "x1": 19, "y1": 6, "x2": 19, "y2": 30, "is_exterior": False},
        {"wallId": 202, "x1": 19, "y1": 19, "x2": 44, "y2": 19, "is_exterior": False},
        {"wallId": 203, "x1": 34, "y1": 0, "x2": 34, "y2": 30, "is_exterior": False},
        {"wallId": 204, "x1": 34, "y1": 7, "x2": 44, "y2": 7, "is_exterior": False},
        {"wallId": 205, "x1": 8, "y1": 6, "x2": 8, "y2": 30, "is_exterior": False},
        {"wallId": 206, "x1": 0, "y1": 23, "x2": 8, "y2": 23, "is_exterior": False},
        {"wallId": 207, "x1": 8, "y1": 20, "x2": 19, "y2": 20, "is_exterior": False},
        {"wallId": 208, "x1": 0, "y1": 13, "x2": 8, "y2": 13, "is_exterior": False},
        {"wallId": 209, "x1": 8, "y1": 7, "x2": 19, "y2": 7, "is_exterior": False},
    ]


# ── _find_wall_id_at Tests ──

class TestFindWallIdAt:
    def test_exact_point_on_wall(self):
        """Point exactly on a wall segment returns that wall."""
        registry = make_edrawmax_registry()
        # Point (30, 0) is on wall 101 (south wall: 19,0→44,0)
        wid = _find_wall_id_at(registry, 30, 0)
        assert wid == 101

    def test_near_point(self):
        """Point near a wall (within tolerance) returns that wall."""
        registry = make_edrawmax_registry()
        # Point (30, 0.5) is 0.5 from south wall — within default tol=2.0
        wid = _find_wall_id_at(registry, 30, 0.5)
        assert wid == 101

    def test_no_wall_found(self):
        """Point far from any wall returns None."""
        registry = make_edrawmax_registry()
        # Point (22, 10) is in the middle of the Great Room — far from walls
        wid = _find_wall_id_at(registry, 26, 10, tol=0.5)
        assert wid is None

    def test_closest_wall_selected(self):
        """When point is near multiple walls, closest wins."""
        registry = make_edrawmax_registry()
        # Point (34, 15) is on vertical wall 203 (x=34, y=0→30)
        wid = _find_wall_id_at(registry, 34, 15)
        assert wid == 203

    def test_wall_endpoint(self):
        """Point at wall endpoint still matches."""
        registry = make_edrawmax_registry()
        # (44, 0) is the endpoint of wall 101 and start of wall 102
        wid = _find_wall_id_at(registry, 44, 0)
        # Should match one of these
        assert wid in (101, 102)

    def test_entry_door_position(self):
        """Entry door at (14, 6) finds south wall of left wing."""
        registry = make_edrawmax_registry()
        wid = _find_wall_id_at(registry, 14, 6)
        assert wid == 105  # Wall: (0,6)→(19,6)

    def test_custom_tolerance(self):
        """Tighter tolerance rejects farther points."""
        registry = make_edrawmax_registry()
        # Point 1.5 from wall, but tol=1.0 should reject
        wid = _find_wall_id_at(registry, 30, 1.5, tol=1.0)
        assert wid is None

    def test_empty_registry(self):
        """Empty registry returns None."""
        assert _find_wall_id_at([], 10, 10) is None

    def test_degenerate_wall(self):
        """Zero-length wall segment handles gracefully."""
        registry = [{"wallId": 1, "x1": 5, "y1": 5, "x2": 5, "y2": 5, "is_exterior": False}]
        wid = _find_wall_id_at(registry, 5, 5)
        assert wid == 1


# ── build_wall_registry Tests ──

class TestBuildWallRegistry:
    def test_basic_registry(self):
        """Build registry from walls and batch result."""
        walls = [
            Wall("W1", (0, 0), (10, 0), "exterior"),
            Wall("W2", (10, 0), (10, 10), "exterior"),
        ]
        batch_result = {
            "createdWalls": [
                {"wallId": 100, "elementId": 100},
                {"wallId": 200, "elementId": 200},
            ]
        }
        registry = build_wall_registry(walls, batch_result, True)
        assert len(registry) == 2
        assert registry[0]["wallId"] == 100
        assert registry[0]["x1"] == 0
        assert registry[0]["y2"] == 0
        assert registry[0]["is_exterior"] is True
        assert registry[1]["wallId"] == 200
        assert registry[1]["x1"] == 10

    def test_partial_result(self):
        """Handles case where Revit creates fewer walls than requested."""
        walls = [
            Wall("W1", (0, 0), (10, 0), "exterior"),
            Wall("W2", (10, 0), (10, 10), "exterior"),
            Wall("W3", (10, 10), (0, 10), "exterior"),
        ]
        batch_result = {
            "createdWalls": [
                {"wallId": 100},
                {"wallId": 200},
                # W3 failed — only 2 results
            ]
        }
        registry = build_wall_registry(walls, batch_result, True)
        assert len(registry) == 2

    def test_empty_result(self):
        """Handles empty batch result."""
        walls = [Wall("W1", (0, 0), (10, 0), "exterior")]
        registry = build_wall_registry(walls, {}, True)
        assert len(registry) == 0

    def test_interior_walls(self):
        """Interior walls flagged correctly."""
        walls = [Wall("W7", (5, 0), (5, 10), "interior")]
        batch_result = {
            "createdWalls": [{"wallId": 300}]
        }
        registry = build_wall_registry(walls, batch_result, False)
        assert len(registry) == 1
        assert registry[0]["is_exterior"] is False


# ── Integration: EdrawMax WallPlan ──

class TestEdrawMaxExecution:
    """Test that EdrawMax WallPlan resolves all doors and windows to correct walls."""

    def test_all_doors_resolve(self):
        """Every door in the EdrawMax plan resolves to a wall in the registry."""
        from floor_plan_engine.tests.test_wall_model import make_edrawmax_wallplan
        plan = make_edrawmax_wallplan()
        registry = make_edrawmax_registry()

        resolved = 0
        for door in plan.doors:
            wall = plan.wall_by_id(door.wall_id)
            assert wall is not None, f"Door {door.id} references missing wall {door.wall_id}"
            x, y = door.resolve_position(wall)
            wid = _find_wall_id_at(registry, x, y)
            if wid is not None:
                resolved += 1

        # All 11 doors should find walls
        assert resolved == len(plan.doors), \
            f"Only {resolved}/{len(plan.doors)} doors resolved to walls"

    def test_all_windows_resolve(self):
        """Every window in the EdrawMax plan resolves to a wall."""
        from floor_plan_engine.tests.test_wall_model import make_edrawmax_wallplan
        plan = make_edrawmax_wallplan()
        registry = make_edrawmax_registry()

        resolved = 0
        for win in plan.windows:
            wall = plan.wall_by_id(win.wall_id)
            assert wall is not None, f"Window {win.id} references missing wall {win.wall_id}"
            x, y = win.resolve_position(wall)
            wid = _find_wall_id_at(registry, x, y, tol=1.0)
            if wid is not None:
                resolved += 1

        assert resolved == len(plan.windows), \
            f"Only {resolved}/{len(plan.windows)} windows resolved to walls"

    def test_entry_door_on_exterior_wall(self):
        """Entry door resolves to an exterior wall."""
        from floor_plan_engine.tests.test_wall_model import make_edrawmax_wallplan
        plan = make_edrawmax_wallplan()
        registry = make_edrawmax_registry()

        entry_door = plan.doors[0]
        assert entry_door.is_entry
        wall = plan.wall_by_id(entry_door.wall_id)
        x, y = entry_door.resolve_position(wall)
        wid = _find_wall_id_at(registry, x, y)

        # Should be on wall 105 (south wall of left wing: 0,6→19,6)
        assert wid == 105
        # Verify that wall is exterior
        wall_entry = next(w for w in registry if w["wallId"] == wid)
        assert wall_entry["is_exterior"] is True
