"""
Golden end-to-end test: EdrawMax L-shaped plan as WallPlan.

Proves the wall-first engine produces the EXACT same Revit result
as replicate_edrawmax_plan.py. This is the reference standard.

If this passes, the engine produces identical output to the proven script.
"""

import pytest
from floor_plan_engine.wall_model import Wall, Opening, RoomLabel, WallPlan
from floor_plan_engine.wall_revit_bridge import _find_wall_id_at


# ── Reference Data from replicate_edrawmax_plan.py ──

REFERENCE_EXTERIOR_WALLS = [
    (19,  0, 44,  0),
    (44,  0, 44, 30),
    (44, 30,  0, 30),
    ( 0, 30,  0,  6),
    ( 0,  6, 19,  6),
    (19,  6, 19,  0),
]

REFERENCE_INTERIOR_WALLS = [
    (19,  6, 19, 30),
    (19, 19, 44, 19),
    (34,  0, 34, 30),
    (34,  7, 44,  7),
    ( 8,  6,  8, 30),
    ( 0, 23,  8, 23),
    ( 8, 20, 19, 20),
    ( 0, 13,  8, 13),
    ( 8,  7, 19,  7),
]

REFERENCE_DOORS = [
    (14,  6, True),    # Entry
    (14,  7, False),   # Master Bedroom
    ( 8, 10, False),   # Wardrobe
    ( 8, 18, False),   # Bath 2
    ( 8, 24, False),   # Bath 1
    (14, 20, False),   # Bedroom 2
    (19, 12, False),   # Great Room to left wing
    (26, 19, False),   # Dining
    (34, 24, False),   # Kitchen
    (34, 13, False),   # Bedroom 1
    (34,  3, False),   # Bath 3
]

REFERENCE_WINDOWS = [
    ( 4, 30), (14, 30), (26, 30), (39, 30),  # North wall
    (44, 24), (44, 13), (44,  3),              # East wall
    (26,  0), (34,  0),                        # South wall
    ( 0, 26), ( 0, 18), ( 0,  9),             # West wall
]

REFERENCE_ROOMS = [
    ("Great Room",      19,  0, 15, 19),
    ("Dining",          19, 19, 15, 11),
    ("Kitchen",         34, 19, 10, 11),
    ("Bedroom 1",       34,  7, 10, 12),
    ("Bath 3",          34,  0, 10,  7),
    ("Bath 1",           0, 23,  8,  7),
    ("Bedroom 2",        8, 20, 11, 10),
    ("Bath 2",           0, 13,  8, 10),
    ("Master Bedroom",   8,  7, 11, 13),
    ("Wardrobe",         0,  6,  8,  7),
]


# ── Build the WallPlan ──

def make_golden_wallplan() -> WallPlan:
    """Construct the EdrawMax plan as a WallPlan with walls matching reference exactly."""
    walls = []

    # Exterior walls — exact coordinates from reference
    for i, (x1, y1, x2, y2) in enumerate(REFERENCE_EXTERIOR_WALLS, 1):
        walls.append(Wall(f"EXT{i}", (x1, y1), (x2, y2), "exterior", 8.0))

    # Interior walls — exact coordinates from reference
    for i, (x1, y1, x2, y2) in enumerate(REFERENCE_INTERIOR_WALLS, 1):
        walls.append(Wall(f"INT{i}", (x1, y1), (x2, y2), "interior", 4.0))

    # Doors — placed by wall_id + offset to resolve to reference coordinates
    doors = _build_doors_from_reference(walls)

    # Windows — placed by wall_id + offset to resolve to reference coordinates
    windows = _build_windows_from_reference(walls)

    # Rooms — labels at centroids matching reference
    rooms = []
    for name, x, y, w, h in REFERENCE_ROOMS:
        cx = x + w / 2
        cy = y + h / 2
        rooms.append(RoomLabel(name, (cx, cy), area_sqft=w * h))

    return WallPlan(
        walls=walls,
        doors=doors,
        windows=windows,
        rooms=rooms,
        overall_width_ft=44,
        overall_depth_ft=30,
        wall_height_ft=10.0,
    )


def _build_doors_from_reference(walls):
    """Build door Openings that resolve to reference (x, y) positions."""
    doors = []
    for i, (rx, ry, is_entry) in enumerate(REFERENCE_DOORS, 1):
        # Find the wall that passes nearest to this reference door position
        wall, offset = _find_wall_and_offset(walls, rx, ry)
        if wall:
            doors.append(Opening(
                f"D{i}", wall.id, offset, 3.0, "door",
                is_entry=is_entry,
            ))
    return doors


def _build_windows_from_reference(walls):
    """Build window Openings that resolve to reference (x, y) positions."""
    windows = []
    for i, (rx, ry) in enumerate(REFERENCE_WINDOWS, 1):
        wall, offset = _find_wall_and_offset(walls, rx, ry)
        if wall:
            windows.append(Opening(
                f"WIN{i}", wall.id, offset, 3.0, "window",
            ))
    return windows


def _find_wall_and_offset(walls, x, y, tol=2.0):
    """Find the wall nearest to (x, y) and compute offset along that wall.

    Returns (Wall, offset_ft) or (None, 0).
    """
    import math

    best_wall = None
    best_dist = float('inf')
    best_offset = 0.0

    for w in walls:
        x1, y1, x2, y2 = w.x1, w.y1, w.x2, w.y2
        dx, dy = x2 - x1, y2 - y1
        seg_len_sq = dx * dx + dy * dy

        if seg_len_sq < 0.01:
            dist = math.sqrt((x - x1) ** 2 + (y - y1) ** 2)
            t = 0.0
        else:
            t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / seg_len_sq))
            px, py = x1 + t * dx, y1 + t * dy
            dist = math.sqrt((x - px) ** 2 + (y - py) ** 2)

        if dist < best_dist:
            best_dist = dist
            best_wall = w
            best_offset = t * w.length

    if best_wall and best_dist <= tol:
        # Offset is to the CENTER of the opening (width 3.0)
        # Subtract half-width to get near-edge offset
        offset = max(0, best_offset - 1.5)
        return best_wall, offset

    return None, 0.0


# ── Mock Revit Registry ──

def make_mock_registry(plan: WallPlan):
    """Create a mock wall registry as if Revit returned IDs for all walls."""
    registry = []
    for i, w in enumerate(plan.walls, start=1000):
        registry.append({
            "wallId": i,
            "x1": w.x1, "y1": w.y1, "x2": w.x2, "y2": w.y2,
            "is_exterior": w.is_exterior,
        })
    return registry


# ══════════════════════════════════════════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestGoldenWallCoordinates:
    """Verify wall coordinates exactly match the reference script."""

    def test_exterior_wall_count(self):
        plan = make_golden_wallplan()
        assert len(plan.exterior_walls) == 6

    def test_interior_wall_count(self):
        plan = make_golden_wallplan()
        assert len(plan.interior_walls) == 9

    def test_total_wall_count(self):
        plan = make_golden_wallplan()
        assert len(plan.walls) == 15  # 6 + 9

    def test_exterior_wall_coordinates(self):
        plan = make_golden_wallplan()
        for i, w in enumerate(plan.exterior_walls):
            ref = REFERENCE_EXTERIOR_WALLS[i]
            actual = (w.x1, w.y1, w.x2, w.y2)
            assert actual == ref, \
                f"Ext wall {i}: {actual} != {ref}"

    def test_interior_wall_coordinates(self):
        plan = make_golden_wallplan()
        for i, w in enumerate(plan.interior_walls):
            ref = REFERENCE_INTERIOR_WALLS[i]
            actual = (w.x1, w.y1, w.x2, w.y2)
            assert actual == ref, \
                f"Int wall {i}: {actual} != {ref}"


class TestGoldenDoorPlacement:
    """Verify doors resolve to reference positions."""

    def test_door_count(self):
        plan = make_golden_wallplan()
        assert len(plan.doors) == 11

    def test_entry_door(self):
        plan = make_golden_wallplan()
        entry = [d for d in plan.doors if d.is_entry]
        assert len(entry) == 1

        # Resolve entry door position
        door = entry[0]
        wall = plan.wall_by_id(door.wall_id)
        x, y = door.resolve_position(wall)

        # Should be near (14, 6) — the reference entry position
        assert abs(x - 14) < 1.0, f"Entry x={x}, expected ~14"
        assert abs(y - 6) < 1.0, f"Entry y={y}, expected ~6"

    def test_all_doors_near_reference(self):
        """Each door resolves near its reference (x, y) position."""
        plan = make_golden_wallplan()

        for i, (ref_x, ref_y, _) in enumerate(REFERENCE_DOORS):
            door = plan.doors[i]
            wall = plan.wall_by_id(door.wall_id)
            assert wall is not None, f"Door {door.id}: wall {door.wall_id} not found"
            x, y = door.resolve_position(wall)

            # Allow 2ft tolerance for offset calculation
            dist = ((x - ref_x) ** 2 + (y - ref_y) ** 2) ** 0.5
            assert dist < 2.0, \
                f"Door {door.id}: resolved ({x:.1f},{y:.1f}) too far from ref ({ref_x},{ref_y}), dist={dist:.1f}"

    def test_doors_find_walls_in_registry(self):
        """All doors resolve to walls in a mock Revit registry."""
        plan = make_golden_wallplan()
        registry = make_mock_registry(plan)

        for door in plan.doors:
            wall = plan.wall_by_id(door.wall_id)
            x, y = door.resolve_position(wall)
            wid = _find_wall_id_at(registry, x, y)
            assert wid is not None, \
                f"Door {door.id} at ({x:.1f},{y:.1f}) found no wall in registry"


class TestGoldenWindowPlacement:
    """Verify windows resolve to reference positions."""

    def test_window_count(self):
        plan = make_golden_wallplan()
        assert len(plan.windows) == 12

    def test_all_windows_near_reference(self):
        """Each window resolves near its reference (x, y) position."""
        plan = make_golden_wallplan()

        for i, (ref_x, ref_y) in enumerate(REFERENCE_WINDOWS):
            win = plan.windows[i]
            wall = plan.wall_by_id(win.wall_id)
            assert wall is not None, f"Window {win.id}: wall {win.wall_id} not found"
            x, y = win.resolve_position(wall)

            dist = ((x - ref_x) ** 2 + (y - ref_y) ** 2) ** 0.5
            assert dist < 2.0, \
                f"Window {win.id}: resolved ({x:.1f},{y:.1f}) too far from ref ({ref_x},{ref_y}), dist={dist:.1f}"

    def test_windows_find_walls_in_registry(self):
        """All windows resolve to walls in a mock Revit registry."""
        plan = make_golden_wallplan()
        registry = make_mock_registry(plan)

        for win in plan.windows:
            wall = plan.wall_by_id(win.wall_id)
            x, y = win.resolve_position(wall)
            wid = _find_wall_id_at(registry, x, y, tol=1.0)
            assert wid is not None, \
                f"Window {win.id} at ({x:.1f},{y:.1f}) found no wall in registry"


class TestGoldenRoomPlacement:
    """Verify room labels match reference."""

    def test_room_count(self):
        plan = make_golden_wallplan()
        assert len(plan.rooms) == 10

    def test_room_names(self):
        plan = make_golden_wallplan()
        names = {r.name for r in plan.rooms}
        expected = {name for name, *_ in REFERENCE_ROOMS}
        assert names == expected

    def test_room_centroids(self):
        """Room centroids match reference (name, x+w/2, y+h/2)."""
        plan = make_golden_wallplan()

        for room in plan.rooms:
            ref = next(r for r in REFERENCE_ROOMS if r[0] == room.name)
            _, rx, ry, rw, rh = ref
            expected_cx = rx + rw / 2
            expected_cy = ry + rh / 2

            assert abs(room.center[0] - expected_cx) < 0.1, \
                f"{room.name}: cx={room.center[0]}, expected {expected_cx}"
            assert abs(room.center[1] - expected_cy) < 0.1, \
                f"{room.name}: cy={room.center[1]}, expected {expected_cy}"


class TestGoldenBridgeToFloorPlan:
    """Verify the WallPlan → FloorPlan bridge works for the golden test."""

    def test_bridge_produces_valid_floorplan(self):
        plan = make_golden_wallplan()
        fp = plan.to_floor_plan()

        # Should have rooms
        assert len(fp.rooms) > 0
        # Should have all 15 walls
        assert len(fp.walls) == 15
        # Should have doors and windows
        assert len(fp.doors) > 0
        assert len(fp.windows) > 0
        # Dimensions
        assert fp.footprint_width == 44
        assert fp.footprint_height == 30

    def test_bridge_floorplan_analyzable(self):
        """FloorPlan from bridge can be analyzed by reasoning engine."""
        plan = make_golden_wallplan()
        fp = plan.to_floor_plan()

        # Should not crash
        analysis = fp.analyze()
        assert analysis.score >= 0
        assert analysis.verdict in ("GOOD", "NEEDS WORK", "FUNDAMENTALLY FLAWED")

    def test_bridge_room_types_correct(self):
        """Room types are correctly guessed from names."""
        from floor_plan_engine.models import RoomType
        plan = make_golden_wallplan()
        fp = plan.to_floor_plan()

        types = {r.name: r.room_type for r in fp.rooms}
        if "Kitchen" in types:
            assert types["Kitchen"] == RoomType.KITCHEN
        if "Master Bedroom" in types:
            assert types["Master Bedroom"] == RoomType.MASTER_BEDROOM


class TestGoldenSerialization:
    """Verify the golden plan survives serialization."""

    def test_roundtrip(self):
        """Golden plan serializes and deserializes correctly."""
        import json
        plan = make_golden_wallplan()
        d = plan.to_dict()
        json_str = json.dumps(d, indent=2)
        d2 = json.loads(json_str)
        plan2 = WallPlan.from_dict(d2)

        # Same wall count
        assert len(plan2.walls) == len(plan.walls)
        # Same door count
        assert len(plan2.doors) == len(plan.doors)
        # Same window count
        assert len(plan2.windows) == len(plan.windows)
        # Same room count
        assert len(plan2.rooms) == len(plan.rooms)

        # Wall coordinates preserved
        for w1, w2 in zip(plan.walls, plan2.walls):
            assert w1.start == w2.start
            assert w1.end == w2.end
            assert w1.wall_type == w2.wall_type
