"""Tests for the v3 FloorPlanBuilder."""

import pytest
import sys
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/pipelines")

from floor_plan_engine.models import FloorPlan, RoomType, Zone
from floor_plan_engine.builder import FloorPlanBuilder


# ---------------------------------------------------------------------------
# Basic construction
# ---------------------------------------------------------------------------

class TestBasicBuilder:

    def test_empty_builder(self):
        plan = FloorPlanBuilder("Empty").build()
        assert isinstance(plan, FloorPlan)
        assert len(plan.rooms) == 0

    def test_single_room(self):
        plan = (FloorPlanBuilder("Single")
            .add_room("Living", RoomType.LIVING, 0, 0, 15, 12)
            .build())
        assert len(plan.rooms) == 1
        assert plan.rooms[0].name == "Living"
        assert plan.rooms[0].w == 15
        assert plan.rooms[0].h == 12

    def test_fluent_api_chaining(self):
        builder = FloorPlanBuilder("Chain")
        result = builder.add_room("A", RoomType.LIVING, 0, 0, 10, 10)
        assert result is builder  # returns self for chaining

    def test_zone_auto_assignment(self):
        plan = (FloorPlanBuilder()
            .add_room("Bed", RoomType.BEDROOM, 0, 0, 10, 10)
            .add_room("Kit", RoomType.KITCHEN, 10, 0, 10, 10)
            .build())
        bed = next(r for r in plan.rooms if r.name == "Bed")
        kit = next(r for r in plan.rooms if r.name == "Kit")
        assert bed.zone == Zone.PRIVATE
        assert kit.zone == Zone.PUBLIC


# ---------------------------------------------------------------------------
# Walls
# ---------------------------------------------------------------------------

class TestWalls:

    def test_exterior_walls_rect(self):
        plan = (FloorPlanBuilder()
            .add_room("R", RoomType.LIVING, 0, 0, 20, 15)
            .add_exterior_walls_rect(20, 15)
            .build())
        exterior = [w for w in plan.walls if w.is_exterior]
        assert len(exterior) == 4
        assert plan.footprint_width == 20
        assert plan.footprint_height == 15

    def test_auto_interior_walls(self):
        plan = (FloorPlanBuilder()
            .add_room("A", RoomType.LIVING, 0, 0, 10, 10)
            .add_room("B", RoomType.KITCHEN, 10, 0, 10, 10)
            .auto_interior_walls()
            .build())
        interior = [w for w in plan.walls if not w.is_exterior]
        assert len(interior) >= 1  # at least 1 shared wall

    def test_auto_walls_skips_open_plan(self):
        plan_with_wall = (FloorPlanBuilder()
            .add_room("A", RoomType.LIVING, 0, 0, 10, 10)
            .add_room("B", RoomType.KITCHEN, 10, 0, 10, 10)
            .auto_interior_walls()
            .build())
        plan_open = (FloorPlanBuilder()
            .add_room("A", RoomType.LIVING, 0, 0, 10, 10)
            .add_room("B", RoomType.KITCHEN, 10, 0, 10, 10)
            .connect_open_plan("A", "B")
            .auto_interior_walls()
            .build())
        interior_with = len([w for w in plan_with_wall.walls
                             if not w.is_exterior])
        interior_open = len([w for w in plan_open.walls
                             if not w.is_exterior])
        assert interior_open < interior_with

    def test_auto_walls_creates_exterior_if_none(self):
        plan = (FloorPlanBuilder()
            .add_room("A", RoomType.LIVING, 0, 0, 10, 10)
            .auto_interior_walls()
            .build())
        exterior = [w for w in plan.walls if w.is_exterior]
        assert len(exterior) == 4

    def test_l_shape_exterior(self):
        points = [(0, 0), (20, 0), (20, 15), (10, 15), (10, 10), (0, 10)]
        plan = (FloorPlanBuilder()
            .add_room("A", RoomType.LIVING, 0, 0, 10, 10)
            .add_room("B", RoomType.KITCHEN, 10, 0, 10, 15)
            .add_exterior_walls_L(points)
            .build())
        exterior = [w for w in plan.walls if w.is_exterior]
        assert len(exterior) == 6


# ---------------------------------------------------------------------------
# Doors
# ---------------------------------------------------------------------------

class TestDoors:

    def test_add_door(self):
        plan = (FloorPlanBuilder()
            .add_room("A", RoomType.LIVING, 0, 0, 10, 10)
            .add_room("B", RoomType.BEDROOM, 10, 0, 10, 10)
            .auto_interior_walls()
            .add_door(10, 5, "A", "B")
            .build())
        assert len(plan.doors) == 1
        assert plan.doors[0].room_a == "A"
        assert plan.doors[0].room_b == "B"

    def test_entry_door(self):
        plan = (FloorPlanBuilder()
            .add_room("Entry", RoomType.ENTRY, 0, 0, 5, 5)
            .auto_interior_walls()
            .add_entry_door("south", 2.5)
            .build())
        assert len(plan.doors) == 1
        d = plan.doors[0]
        assert d.room_b == "exterior"
        assert d.width_inches == 36  # entry door spec

    def test_door_auto_spec(self):
        plan = (FloorPlanBuilder()
            .add_room("A", RoomType.BATHROOM, 0, 0, 7, 7)
            .add_room("B", RoomType.HALLWAY, 7, 0, 4, 7)
            .auto_interior_walls()
            .add_door(7, 3, "A", "B")
            .build())
        assert plan.doors[0].width_inches == 28  # bathroom door spec


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------

class TestWindows:

    def test_add_window(self):
        plan = (FloorPlanBuilder()
            .add_room("Living", RoomType.LIVING, 0, 0, 15, 12)
            .auto_interior_walls()
            .add_window(7, 0, "Living")
            .build())
        assert len(plan.windows) == 1
        assert plan.windows[0].room_name == "Living"


# ---------------------------------------------------------------------------
# Build output
# ---------------------------------------------------------------------------

class TestBuild:

    def test_bedroom_count(self):
        plan = (FloorPlanBuilder()
            .add_room("Master", RoomType.MASTER_BEDROOM, 0, 0, 14, 12)
            .add_room("Bed2", RoomType.BEDROOM, 14, 0, 10, 12)
            .add_room("Bed3", RoomType.BEDROOM, 24, 0, 10, 12)
            .build())
        assert plan.bedrooms == 3

    def test_bathroom_count(self):
        plan = (FloorPlanBuilder()
            .add_room("MBath", RoomType.MASTER_BATH, 0, 0, 8, 7)
            .add_room("Bath", RoomType.BATHROOM, 8, 0, 7, 7)
            .add_room("Half", RoomType.HALF_BATH, 15, 0, 4, 5)
            .build())
        assert plan.bathrooms == 3

    def test_total_area(self):
        plan = (FloorPlanBuilder()
            .add_room("A", RoomType.LIVING, 0, 0, 10, 10)
            .add_room("B", RoomType.KITCHEN, 10, 0, 10, 10)
            .build())
        assert plan.total_area == 200.0

    def test_footprint_auto_computed(self):
        plan = (FloorPlanBuilder()
            .add_room("A", RoomType.LIVING, 0, 0, 15, 12)
            .add_room("B", RoomType.KITCHEN, 15, 0, 10, 12)
            .build())
        assert plan.footprint_width == 25
        assert plan.footprint_height == 12


# ---------------------------------------------------------------------------
# from_dict
# ---------------------------------------------------------------------------

class TestFromDict:

    def test_basic_from_dict(self):
        data = {
            "name": "Test",
            "rooms": [
                {"name": "Living", "type": "living_room",
                 "x": 0, "y": 0, "w": 15, "h": 12},
                {"name": "Kitchen", "type": "kitchen",
                 "x": 15, "y": 0, "w": 10, "h": 12},
            ],
            "doors": [
                {"x": 15, "y": 6, "room_a": "Living", "room_b": "Kitchen"},
            ],
            "windows": [
                {"x": 7, "y": 0, "room_name": "Living"},
            ],
            "open_connections": [],
        }
        builder = FloorPlanBuilder.from_dict(data)
        plan = builder.build()
        assert len(plan.rooms) == 2
        assert len(plan.doors) == 1
        assert len(plan.windows) == 1

    def test_open_connections_from_dict(self):
        data = {
            "rooms": [
                {"name": "A", "type": "living_room",
                 "x": 0, "y": 0, "w": 10, "h": 10},
                {"name": "B", "type": "kitchen",
                 "x": 10, "y": 0, "w": 10, "h": 10},
            ],
            "open_connections": [["A", "B"]],
        }
        builder = FloorPlanBuilder.from_dict(data)
        plan = builder.build()
        # Should have no interior wall between A and B
        from floor_plan_engine.reasoning import build_connectivity_graph
        graph = build_connectivity_graph(plan)
        assert "B" in graph["A"]

    def test_entry_door_from_dict(self):
        data = {
            "rooms": [
                {"name": "Entry", "type": "entry",
                 "x": 0, "y": 0, "w": 5, "h": 5},
            ],
            "doors": [
                {"x": 2.5, "y": 0, "room_a": "Entry",
                 "room_b": "exterior", "is_entry": True},
            ],
        }
        builder = FloorPlanBuilder.from_dict(data)
        plan = builder.build()
        assert len(plan.doors) == 1
        assert plan.doors[0].room_b == "exterior"


# ---------------------------------------------------------------------------
# Integration: Builder → Analysis
# ---------------------------------------------------------------------------

class TestBuilderAnalysis:

    def test_well_designed_scores_high(self):
        plan = (FloorPlanBuilder("Good House")
            .add_room("Entry", RoomType.ENTRY, 0, 0, 5, 5)
            .add_room("Living", RoomType.LIVING, 5, 0, 15, 14)
            .add_room("Kitchen", RoomType.KITCHEN, 20, 0, 10, 14)
            .add_room("Hallway", RoomType.HALLWAY, 0, 5, 5, 19)
            .add_room("Master", RoomType.MASTER_BEDROOM, 5, 14, 12, 10)
            .add_room("Bed2", RoomType.BEDROOM, 17, 14, 10, 10)
            .add_room("Bath", RoomType.BATHROOM, 27, 14, 6, 10)
            .connect_open_plan("Living", "Kitchen")
            .auto_interior_walls()
            .add_entry_door("south", 2.5)
            .add_door(5, 2, "Entry", "Living")
            .add_door(5, 10, "Hallway", "Living")
            .add_door(5, 18, "Hallway", "Master")
            .add_door(17, 18, "Hallway", "Bed2")
            .add_door(27, 18, "Hallway", "Bath")
            .add_window(10, 24, "Master")
            .add_window(22, 24, "Bed2")
            .add_window(12, 0, "Living")
            .add_window(25, 0, "Kitchen")
            .build())

        analysis = plan.analyze()
        assert analysis.score >= 80
        assert analysis.verdict == "GOOD"
        assert len(analysis.unreachable_rooms) == 0
