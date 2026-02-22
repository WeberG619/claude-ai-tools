"""Tests for wall_utils: merging and polygon edge detection."""

import pytest
import sys
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/pipelines")

from floor_plan_engine.models import WallSegment
from floor_plan_engine.wall_utils import merge_collinear_walls, is_on_polygon_edge


# ---------------------------------------------------------------------------
# is_on_polygon_edge
# ---------------------------------------------------------------------------

class TestIsOnPolygonEdge:

    def test_segment_on_rect_south(self):
        polygon = [(0, 0), (20, 0), (20, 15), (0, 15)]
        assert is_on_polygon_edge(5, 0, 15, 0, polygon) is True

    def test_segment_on_rect_north(self):
        polygon = [(0, 0), (20, 0), (20, 15), (0, 15)]
        assert is_on_polygon_edge(0, 15, 20, 15, polygon) is True

    def test_segment_on_rect_west(self):
        polygon = [(0, 0), (20, 0), (20, 15), (0, 15)]
        assert is_on_polygon_edge(0, 0, 0, 15, polygon) is True

    def test_segment_not_on_boundary(self):
        polygon = [(0, 0), (20, 0), (20, 15), (0, 15)]
        # Interior segment at x=10
        assert is_on_polygon_edge(10, 0, 10, 15, polygon) is False

    def test_L_shape_notch_edge(self):
        # L-shape: right wing (19,0)→(44,0)→(44,30)→(0,30)→(0,6)→(19,6)
        polygon = [(19, 0), (44, 0), (44, 30), (0, 30), (0, 6), (19, 6)]
        # The L-notch south wall: (0,6)→(19,6)
        assert is_on_polygon_edge(0, 6, 19, 6, polygon) is True
        # Partial segment on the notch wall
        assert is_on_polygon_edge(8, 6, 19, 6, polygon) is True

    def test_L_shape_inner_vertical(self):
        polygon = [(19, 0), (44, 0), (44, 30), (0, 30), (0, 6), (19, 6)]
        # Inner corner step-down: (19,6)→(19,0)
        assert is_on_polygon_edge(19, 0, 19, 6, polygon) is True

    def test_L_shape_interior_not_on_boundary(self):
        polygon = [(19, 0), (44, 0), (44, 30), (0, 30), (0, 6), (19, 6)]
        # Interior wall at x=19, y=6→30 is NOT on boundary
        # (polygon edge at x=19 only covers y=0→6)
        assert is_on_polygon_edge(19, 6, 19, 30, polygon) is False

    def test_empty_polygon(self):
        assert is_on_polygon_edge(0, 0, 10, 0, []) is False

    def test_segment_exceeds_edge(self):
        polygon = [(0, 0), (10, 0), (10, 10), (0, 10)]
        # Segment is longer than the polygon edge
        assert is_on_polygon_edge(-5, 0, 15, 0, polygon) is False


# ---------------------------------------------------------------------------
# merge_collinear_walls
# ---------------------------------------------------------------------------

class TestMergeCollinearWalls:

    def test_two_horizontal_merge(self):
        walls = [
            WallSegment(0, 0, 10, 0),
            WallSegment(10, 0, 20, 0),
        ]
        merged = merge_collinear_walls(walls)
        assert len(merged) == 1
        assert merged[0].x1 == 0
        assert merged[0].x2 == 20
        assert merged[0].y1 == 0

    def test_three_vertical_merge(self):
        walls = [
            WallSegment(5, 0, 5, 7),
            WallSegment(5, 7, 5, 19),
            WallSegment(5, 19, 5, 30),
        ]
        merged = merge_collinear_walls(walls)
        assert len(merged) == 1
        assert merged[0].y1 == 0
        assert merged[0].y2 == 30

    def test_gap_prevents_merge(self):
        walls = [
            WallSegment(0, 0, 10, 0),
            WallSegment(12, 0, 20, 0),  # 2-ft gap
        ]
        merged = merge_collinear_walls(walls)
        assert len(merged) == 2

    def test_different_y_no_merge(self):
        walls = [
            WallSegment(0, 0, 10, 0),
            WallSegment(0, 5, 10, 5),
        ]
        merged = merge_collinear_walls(walls)
        assert len(merged) == 2

    def test_exterior_wins_on_merge(self):
        walls = [
            WallSegment(0, 0, 10, 0, is_exterior=True),
            WallSegment(10, 0, 20, 0, is_exterior=False),
        ]
        merged = merge_collinear_walls(walls)
        assert len(merged) == 1
        assert merged[0].is_exterior is True

    def test_empty_input(self):
        assert merge_collinear_walls([]) == []

    def test_overlapping_segments(self):
        walls = [
            WallSegment(0, 0, 15, 0),
            WallSegment(10, 0, 25, 0),
        ]
        merged = merge_collinear_walls(walls)
        assert len(merged) == 1
        assert merged[0].x1 == 0
        assert merged[0].x2 == 25

    def test_non_axis_aligned_pass_through(self):
        walls = [
            WallSegment(0, 0, 10, 5),  # diagonal
        ]
        merged = merge_collinear_walls(walls)
        assert len(merged) == 1
        assert merged[0].x1 == 0
        assert merged[0].y2 == 5


# ---------------------------------------------------------------------------
# Integration: auto_interior_walls produces merged walls
# ---------------------------------------------------------------------------

class TestAutoInteriorWallsMerging:

    def test_edrawmax_produces_continuous_walls(self):
        """The EdrawMax plan should produce merged continuous walls, not fragments."""
        from floor_plan_engine.builder import FloorPlanBuilder
        from floor_plan_engine.models import RoomType

        L_SHAPE = [
            (19, 0), (44, 0), (44, 30), (0, 30),
            (0, 6), (19, 6),
        ]
        plan = (FloorPlanBuilder("EdrawMax")
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
            .add_exterior_walls_L(L_SHAPE)
            .auto_interior_walls()
            .build())

        interior = [w for w in plan.walls if not w.is_exterior]
        # With merging, should have 9 or fewer interior walls, not 15+
        assert len(interior) <= 10, (
            f"Expected ≤10 merged interior walls, got {len(interior)}: "
            + str([(w.x1, w.y1, w.x2, w.y2) for w in interior])
        )
