"""
Tests for wall_model.py — Wall-first data model.

Tests:
- Wall properties and point_at_offset
- Opening resolution from wall_id + offset
- RoomLabel serialization
- WallPlan serialization round-trip (to_dict → from_dict)
- to_floor_plan bridge produces valid FloorPlan for reasoning
- EdrawMax plan as WallPlan matches reference geometry
"""

import pytest
import json
from floor_plan_engine.wall_model import Wall, Opening, RoomLabel, WallPlan


# ── Helper: EdrawMax L-shaped plan as WallPlan ──

def make_edrawmax_wallplan() -> WallPlan:
    """Create the EdrawMax 1200 SF L-shaped plan as a WallPlan."""
    walls = [
        # Exterior walls (6) — L-shaped perimeter
        Wall("W1", (19, 0), (44, 0), "exterior", 8.0),
        Wall("W2", (44, 0), (44, 30), "exterior", 8.0),
        Wall("W3", (44, 30), (0, 30), "exterior", 8.0),
        Wall("W4", (0, 30), (0, 6), "exterior", 8.0),
        Wall("W5", (0, 6), (19, 6), "exterior", 8.0),
        Wall("W6", (19, 6), (19, 0), "exterior", 8.0),
        # Interior walls (9)
        Wall("W7", (19, 6), (19, 30), "interior", 4.0),   # wing divider
        Wall("W8", (19, 19), (44, 19), "interior", 4.0),   # horizontal mid
        Wall("W9", (34, 0), (34, 30), "interior", 4.0),    # vertical right col
        Wall("W10", (34, 7), (44, 7), "interior", 4.0),    # bath3 divider
        Wall("W11", (8, 6), (8, 30), "interior", 4.0),     # bath column
        Wall("W12", (0, 23), (8, 23), "interior", 4.0),    # bath1/bath2
        Wall("W13", (8, 20), (19, 20), "interior", 4.0),   # bed2/master
        Wall("W14", (0, 13), (8, 13), "interior", 4.0),    # bath2/wardrobe
        Wall("W15", (8, 7), (19, 7), "interior", 4.0),     # master bottom
    ]

    doors = [
        Opening("D1", "W5", 14 - 0 - 1.5, 3.0, "door", is_entry=True),  # Entry at x≈14
        Opening("D2", "W15", 14 - 8 - 1.5, 3.0, "door"),    # Master bed
        Opening("D3", "W11", 10 - 6 - 1.5, 3.0, "door"),    # Wardrobe
        Opening("D4", "W11", 18 - 6 - 1.5, 3.0, "door"),    # Bath 2
        Opening("D5", "W11", 24 - 6 - 1.5, 3.0, "door"),    # Bath 1
        Opening("D6", "W13", 14 - 8 - 1.5, 3.0, "door"),    # Bedroom 2
        Opening("D7", "W7", 12 - 6 - 1.5, 3.0, "door"),     # Great room to left
        Opening("D8", "W8", 26 - 19 - 1.5, 3.0, "door"),    # Dining
        Opening("D9", "W9", 24 - 0 - 1.5, 3.0, "door"),     # Kitchen
        Opening("D10", "W9", 13 - 0 - 1.5, 3.0, "door"),    # Bedroom 1
        Opening("D11", "W9", 3 - 0 - 1.5, 3.0, "door"),     # Bath 3
    ]

    windows = [
        # North wall
        Opening("WIN1", "W3", 44 - 4 - 1.5, 3.0, "window"),
        Opening("WIN2", "W3", 44 - 14 - 1.5, 3.0, "window"),
        Opening("WIN3", "W3", 44 - 26 - 1.5, 3.0, "window"),
        Opening("WIN4", "W3", 44 - 39 - 1.5, 3.0, "window"),
        # East wall
        Opening("WIN5", "W2", 24 - 0 - 1.5, 3.0, "window"),
        Opening("WIN6", "W2", 13 - 0 - 1.5, 3.0, "window"),
        Opening("WIN7", "W2", 3 - 0 - 1.5, 3.0, "window"),
        # South wall
        Opening("WIN8", "W1", 26 - 19 - 1.5, 3.0, "window"),
        Opening("WIN9", "W1", 34 - 19 - 1.5, 3.0, "window"),
        # West wall
        Opening("WIN10", "W4", 30 - 26 - 1.5, 3.0, "window"),
        Opening("WIN11", "W4", 30 - 18 - 1.5, 3.0, "window"),
        Opening("WIN12", "W4", 30 - 9 - 1.5, 3.0, "window"),
    ]

    rooms = [
        RoomLabel("Great Room", (26.5, 9.5), "living_room", area_sqft=285),
        RoomLabel("Dining", (26.5, 24.5), "dining_room", area_sqft=165),
        RoomLabel("Kitchen", (39, 24.5), "kitchen", area_sqft=110),
        RoomLabel("Bedroom 1", (39, 13), "bedroom", area_sqft=120),
        RoomLabel("Bath 3", (39, 3.5), "bathroom", area_sqft=70),
        RoomLabel("Bath 1", (4, 26.5), "bathroom", area_sqft=56),
        RoomLabel("Bedroom 2", (13.5, 25), "bedroom", area_sqft=110),
        RoomLabel("Bath 2", (4, 18), "bathroom", area_sqft=80),
        RoomLabel("Master Bedroom", (13.5, 13.5), "master_bedroom", area_sqft=143),
        RoomLabel("Wardrobe", (4, 9.5), "walk_in_closet", area_sqft=56),
    ]

    return WallPlan(
        walls=walls,
        doors=doors,
        windows=windows,
        rooms=rooms,
        overall_width_ft=44,
        overall_depth_ft=30,
        wall_height_ft=10.0,
    )


# ── Wall Tests ──

class TestWall:
    def test_wall_properties(self):
        w = Wall("W1", (0, 0), (10, 0), "exterior", 8.0)
        assert w.length == 10.0
        assert w.is_horizontal
        assert not w.is_vertical
        assert w.is_exterior
        assert w.midpoint == (5.0, 0.0)

    def test_wall_vertical(self):
        w = Wall("W2", (5, 0), (5, 20), "interior")
        assert w.length == 20.0
        assert w.is_vertical
        assert not w.is_horizontal
        assert not w.is_exterior

    def test_point_at_offset_horizontal(self):
        w = Wall("W1", (10, 5), (30, 5), "exterior")
        # Offset 0 = start
        assert w.point_at_offset(0) == (10, 5)
        # Offset 10 = midpoint
        x, y = w.point_at_offset(10)
        assert abs(x - 20) < 0.01
        assert abs(y - 5) < 0.01
        # Offset = length = end
        x, y = w.point_at_offset(20)
        assert abs(x - 30) < 0.01

    def test_point_at_offset_vertical(self):
        w = Wall("W2", (0, 10), (0, 30), "exterior")
        x, y = w.point_at_offset(10)
        assert abs(x - 0) < 0.01
        assert abs(y - 20) < 0.01

    def test_wall_serialization(self):
        w = Wall("W1", (0, 0), (10, 0), "exterior", 8.0, height_ft=10.0)
        d = w.to_dict()
        assert d["id"] == "W1"
        assert d["start"] == {"x": 0, "y": 0}
        assert d["end"] == {"x": 10, "y": 0}
        assert d["type"] == "exterior"
        assert d["thickness_in"] == 8.0
        assert d["height_ft"] == 10.0

        w2 = Wall.from_dict(d)
        assert w2.id == w.id
        assert w2.start == w.start
        assert w2.end == w.end
        assert w2.wall_type == w.wall_type


# ── Opening Tests ──

class TestOpening:
    def test_resolve_position_horizontal_wall(self):
        w = Wall("W1", (0, 0), (20, 0), "exterior")
        door = Opening("D1", "W1", 5.0, 3.0, "door")
        # Center of door = offset + width/2 = 5 + 1.5 = 6.5 along wall
        x, y = door.resolve_position(w)
        assert abs(x - 6.5) < 0.01
        assert abs(y - 0) < 0.01

    def test_resolve_position_vertical_wall(self):
        w = Wall("W2", (10, 0), (10, 30), "exterior")
        win = Opening("WIN1", "W2", 10.0, 3.0, "window")
        x, y = win.resolve_position(w)
        assert abs(x - 10) < 0.01
        assert abs(y - 11.5) < 0.01

    def test_door_serialization(self):
        d = Opening("D1", "W5", 5.0, 3.0, "door", swing="left",
                     swing_side="positive", is_entry=True)
        dd = d.to_dict()
        assert dd["id"] == "D1"
        assert dd["wall_id"] == "W5"
        assert dd["offset_ft"] == 5.0
        assert dd["is_entry"] is True
        assert "sill_height_ft" not in dd  # door, not window

        d2 = Opening.from_dict(dd, "door")
        assert d2.id == "D1"
        assert d2.is_entry is True

    def test_window_serialization(self):
        w = Opening("WIN1", "W3", 8.0, 3.0, "window",
                     sill_height_ft=3.0, head_height_ft=7.0)
        wd = w.to_dict()
        assert wd["sill_height_ft"] == 3.0
        assert "swing" not in wd  # window, not door

        w2 = Opening.from_dict(wd, "window")
        assert w2.sill_height_ft == 3.0


# ── RoomLabel Tests ──

class TestRoomLabel:
    def test_serialization(self):
        r = RoomLabel("Kitchen", (15, 20), "kitchen", "10' x 12'", 120)
        d = r.to_dict()
        assert d["name"] == "Kitchen"
        assert d["label_position"] == {"x": 15, "y": 20}
        assert d["room_type"] == "kitchen"
        assert d["area_sqft"] == 120

        r2 = RoomLabel.from_dict(d)
        assert r2.name == "Kitchen"
        assert r2.center == (15, 20)
        assert r2.area_sqft == 120


# ── WallPlan Tests ──

class TestWallPlan:
    def test_empty_plan(self):
        plan = WallPlan()
        assert len(plan.walls) == 0
        assert len(plan.doors) == 0
        d = plan.to_dict()
        assert "metadata" in d
        assert "walls" in d

    def test_serialization_roundtrip(self):
        """to_dict → from_dict produces identical WallPlan."""
        plan = make_edrawmax_wallplan()
        d = plan.to_dict()

        # Verify JSON-serializable
        json_str = json.dumps(d)
        d2 = json.loads(json_str)

        plan2 = WallPlan.from_dict(d2)
        assert len(plan2.walls) == len(plan.walls)
        assert len(plan2.doors) == len(plan.doors)
        assert len(plan2.windows) == len(plan.windows)
        assert len(plan2.rooms) == len(plan.rooms)

        # Verify wall coordinates match
        for w1, w2 in zip(plan.walls, plan2.walls):
            assert w1.id == w2.id
            assert w1.start == w2.start
            assert w1.end == w2.end
            assert w1.wall_type == w2.wall_type

    def test_wall_by_id(self):
        plan = make_edrawmax_wallplan()
        w = plan.wall_by_id("W1")
        assert w is not None
        assert w.start == (19, 0)
        assert plan.wall_by_id("W999") is None

    def test_exterior_interior_split(self):
        plan = make_edrawmax_wallplan()
        assert len(plan.exterior_walls) == 6
        assert len(plan.interior_walls) == 9

    def test_resolve_openings(self):
        plan = make_edrawmax_wallplan()
        resolved = plan.resolve_openings()
        assert len(resolved) == len(plan.doors) + len(plan.windows)

        # All should have x, y coordinates
        for r in resolved:
            assert "x" in r
            assert "y" in r
            assert "wall_id" in r

    def test_to_floor_plan_bridge(self):
        """Bridge produces a valid FloorPlan usable by reasoning engine."""
        plan = make_edrawmax_wallplan()
        fp = plan.to_floor_plan()

        # Should have rooms, walls, doors, windows
        assert len(fp.rooms) > 0
        assert len(fp.walls) == 15  # 6 ext + 9 int
        assert len(fp.doors) > 0
        assert len(fp.windows) > 0

        # Footprint dimensions
        assert fp.footprint_width == 44
        assert fp.footprint_height == 30

    def test_to_floor_plan_room_types(self):
        """Room type guessing from names works correctly."""
        plan = make_edrawmax_wallplan()
        fp = plan.to_floor_plan()

        from floor_plan_engine.models import RoomType
        room_types = {r.name: r.room_type for r in fp.rooms}

        # Verify key room type mappings
        if "Great Room" in room_types:
            assert room_types["Great Room"] == RoomType.LIVING
        if "Kitchen" in room_types:
            assert room_types["Kitchen"] == RoomType.KITCHEN
        if "Master Bedroom" in room_types:
            assert room_types["Master Bedroom"] == RoomType.MASTER_BEDROOM

    def test_edrawmax_wall_geometry(self):
        """EdrawMax WallPlan wall coordinates match the reference script."""
        plan = make_edrawmax_wallplan()

        # Reference exterior walls from replicate_edrawmax_plan.py
        expected_ext = [
            (19, 0, 44, 0),
            (44, 0, 44, 30),
            (44, 30, 0, 30),
            (0, 30, 0, 6),
            (0, 6, 19, 6),
            (19, 6, 19, 0),
        ]

        for i, w in enumerate(plan.exterior_walls):
            ex = expected_ext[i]
            assert (w.x1, w.y1, w.x2, w.y2) == ex, \
                f"Exterior wall {i}: {(w.x1, w.y1, w.x2, w.y2)} != {ex}"

    def test_compute_footprint(self):
        plan = make_edrawmax_wallplan()
        fp = plan._compute_footprint()
        # Should have 6 vertices for L-shape
        assert len(fp) == 6
        # First point should be (19, 0) — start of first exterior wall
        assert fp[0] == (19, 0)

    def test_guess_room_type(self):
        from floor_plan_engine.models import RoomType
        assert WallPlan._guess_room_type("Great Room") == RoomType.LIVING
        assert WallPlan._guess_room_type("Master Bedroom") == RoomType.MASTER_BEDROOM
        assert WallPlan._guess_room_type("Bath 3") == RoomType.BATHROOM
        assert WallPlan._guess_room_type("Wardrobe") == RoomType.WALK_IN_CLOSET
        assert WallPlan._guess_room_type("Kitchen") == RoomType.KITCHEN


# ── Schema.json Compatibility ──

class TestSchemaCompat:
    def test_schema_fields_present(self):
        """Verify output has required schema.json fields."""
        plan = make_edrawmax_wallplan()
        d = plan.to_dict()

        # Required top-level
        assert "metadata" in d
        assert "walls" in d
        assert d["metadata"]["units"] == "feet"

        # Each wall has required fields
        for w in d["walls"]:
            assert "id" in w
            assert "start" in w
            assert "end" in w
            assert "x" in w["start"]
            assert "y" in w["start"]

        # Each door has required fields
        for door in d.get("doors", []):
            assert "id" in door
            assert "wall_id" in door
            assert "offset_ft" in door
            assert "width_ft" in door

        # Each room has required fields
        for room in d.get("rooms", []):
            assert "name" in room
            assert "label_position" in room
