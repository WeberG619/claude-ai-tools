"""Tests for the v3 critical thinking / reasoning engine."""

import pytest
import sys
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/pipelines")

from floor_plan_engine.models import (
    FloorPlan, RoomRect, WallSegment, DoorPlacement, WindowPlacement,
    RoomType, Zone, FloorPlanAnalysis,
)
from floor_plan_engine.reasoning import (
    build_connectivity_graph, analyze_circulation, analyze_zoning,
    analyze_doors, analyze_windows, narrate_walkthrough, critique,
    think_through,
)
from floor_plan_engine.builder import FloorPlanBuilder


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_3room():
    """Entry → Living → Kitchen, all connected."""
    return (FloorPlanBuilder("Simple 3")
        .add_room("Entry", RoomType.ENTRY, 0, 0, 5, 5)
        .add_room("Living", RoomType.LIVING, 5, 0, 15, 12)
        .add_room("Kitchen", RoomType.KITCHEN, 20, 0, 10, 12)
        .auto_interior_walls()
        .add_entry_door("south", 2.5)
        .add_door(5, 5, "Entry", "Living")
        .add_door(20, 6, "Living", "Kitchen")
        .add_window(12, 0, "Living")
        .add_window(25, 0, "Kitchen")
        .build())


@pytest.fixture
def disconnected():
    """One room has no door — should be detected as unreachable."""
    return (FloorPlanBuilder("Disconnected")
        .add_room("Entry", RoomType.ENTRY, 0, 0, 5, 5)
        .add_room("Living", RoomType.LIVING, 5, 0, 12, 12)
        .add_room("Isolated", RoomType.BEDROOM, 17, 0, 10, 12)
        .auto_interior_walls()
        .add_entry_door("south", 2.5)
        .add_door(5, 3, "Entry", "Living")
        .build())


@pytest.fixture
def open_plan():
    """Living + Kitchen are open-plan connected."""
    return (FloorPlanBuilder("Open Plan")
        .add_room("Entry", RoomType.ENTRY, 0, 0, 5, 5)
        .add_room("Living", RoomType.LIVING, 5, 0, 12, 12)
        .add_room("Kitchen", RoomType.KITCHEN, 17, 0, 10, 12)
        .connect_open_plan("Living", "Kitchen")
        .auto_interior_walls()
        .add_entry_door("south", 2.5)
        .add_door(5, 3, "Entry", "Living")
        .build())


@pytest.fixture
def edrawmax():
    """Approximate EdrawMax 1200sf plan with L-shape footprint."""
    L_SHAPE = [
        (19, 0), (44, 0), (44, 30), (0, 30),
        (0, 6), (19, 6),
    ]
    return (FloorPlanBuilder("EdrawMax")
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
        .add_entry_door(at=(14, 6))
        .add_door(19, 15, "Master Bedroom", "Great Room")
        .add_door(8, 18, "Bath 2", "Master Bedroom")
        .add_door(8, 10, "Wardrobe", "Master Bedroom")
        .add_door(8, 24, "Bath 1", "Bedroom 2")
        .add_door(14, 20, "Bedroom 2", "Dining")
        .add_door(34, 13, "Bedroom 1", "Great Room")
        .add_door(34, 4, "Bath 3", "Great Room")
        .add_door(34, 24, "Kitchen", "Dining")
        .build())


# ---------------------------------------------------------------------------
# Connectivity Graph
# ---------------------------------------------------------------------------

class TestConnectivityGraph:

    def test_door_connections(self, simple_3room):
        graph = build_connectivity_graph(simple_3room)
        assert "Living" in graph["Entry"]
        assert "Kitchen" in graph["Living"]
        assert "Entry" not in graph["Kitchen"]

    def test_open_plan_connections(self, open_plan):
        graph = build_connectivity_graph(open_plan)
        assert "Kitchen" in graph["Living"]
        assert "Living" in graph["Kitchen"]

    def test_all_rooms_present(self, edrawmax):
        graph = build_connectivity_graph(edrawmax)
        assert len(graph) == 10
        for room in edrawmax.rooms:
            assert room.name in graph

    def test_empty_plan(self):
        plan = FloorPlan()
        graph = build_connectivity_graph(plan)
        assert graph == {}

    def test_bidirectional(self, simple_3room):
        graph = build_connectivity_graph(simple_3room)
        for room, neighbors in graph.items():
            for nb in neighbors:
                assert room in graph[nb], f"{room} → {nb} but not {nb} → {room}"


# ---------------------------------------------------------------------------
# Circulation
# ---------------------------------------------------------------------------

class TestCirculation:

    def test_all_reachable(self, simple_3room):
        graph = build_connectivity_graph(simple_3room)
        circ = analyze_circulation(simple_3room, graph)
        assert len(circ["unreachable"]) == 0
        assert len(circ["reachable"]) == 3

    def test_unreachable_detected(self, disconnected):
        graph = build_connectivity_graph(disconnected)
        circ = analyze_circulation(disconnected, graph)
        assert "Isolated" in circ["unreachable"]

    def test_depth_ordering(self, simple_3room):
        graph = build_connectivity_graph(simple_3room)
        circ = analyze_circulation(simple_3room, graph)
        assert circ["room_depth"]["Entry"] == 0
        assert circ["room_depth"]["Living"] == 1
        assert circ["room_depth"]["Kitchen"] == 2

    def test_dead_ends(self, simple_3room):
        graph = build_connectivity_graph(simple_3room)
        circ = analyze_circulation(simple_3room, graph)
        assert "Entry" in circ["dead_ends"]
        assert "Kitchen" in circ["dead_ends"]

    def test_entry_detected(self, edrawmax):
        graph = build_connectivity_graph(edrawmax)
        circ = analyze_circulation(edrawmax, graph)
        # Entry door at (14,6) on L-notch south wall;
        # nearest room is Master Bedroom (center 13.5, 13.5)
        assert circ["entry_room"] == "Master Bedroom"


# ---------------------------------------------------------------------------
# Zoning
# ---------------------------------------------------------------------------

class TestZoning:

    def test_good_separation(self, simple_3room):
        graph = build_connectivity_graph(simple_3room)
        circ = analyze_circulation(simple_3room, graph)
        zoning = analyze_zoning(simple_3room, graph, circ["room_depth"])
        assert zoning["zone_separation_score"] >= 80

    def test_privacy_gradient_order(self, simple_3room):
        graph = build_connectivity_graph(simple_3room)
        circ = analyze_circulation(simple_3room, graph)
        zoning = analyze_zoning(simple_3room, graph, circ["room_depth"])
        gradient = zoning["privacy_gradient"]
        assert gradient[0] == "Entry"  # closest to entry


# ---------------------------------------------------------------------------
# Doors
# ---------------------------------------------------------------------------

class TestDoors:

    def test_no_issues_when_all_connected(self, simple_3room):
        result = analyze_doors(simple_3room)
        assert len(result["rooms_without_doors"]) == 0

    def test_detects_doorless_room(self, disconnected):
        result = analyze_doors(disconnected)
        assert "Isolated" in result["rooms_without_doors"]

    def test_open_plan_rooms_ok_without_doors(self, open_plan):
        result = analyze_doors(open_plan)
        # Kitchen connected via open plan, no door needed
        assert "Kitchen" not in result["rooms_without_doors"]

    def test_bathroom_facing_living(self):
        plan = (FloorPlanBuilder("Bad Bath")
            .add_room("Living", RoomType.LIVING, 0, 0, 15, 12)
            .add_room("Bathroom", RoomType.BATHROOM, 15, 0, 7, 7)
            .auto_interior_walls()
            .add_door(15, 3, "Bathroom", "Living")
            .build())
        result = analyze_doors(plan)
        assert any("bathroom" in i.lower() and "living" in i.lower()
                    for i in result["door_issues"])


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------

class TestWindows:

    def test_egress_detected(self):
        plan = (FloorPlanBuilder("No Egress")
            .add_room("Bedroom", RoomType.BEDROOM, 0, 0, 12, 10)
            .auto_interior_walls()
            .build())
        result = analyze_windows(plan)
        assert any("egress" in i.lower() for i in result["window_issues"])

    def test_no_issues_with_windows(self, simple_3room):
        result = analyze_windows(simple_3room)
        egress_issues = [i for i in result["window_issues"]
                         if "egress" in i.lower()]
        assert len(egress_issues) == 0  # no bedrooms in simple_3room


# ---------------------------------------------------------------------------
# Narrative
# ---------------------------------------------------------------------------

class TestNarrative:

    def test_walkthrough_starts_with_entry(self, simple_3room):
        graph = build_connectivity_graph(simple_3room)
        circ = analyze_circulation(simple_3room, graph)
        text = narrate_walkthrough(simple_3room, graph, circ["room_depth"])
        assert text.startswith("You enter through")

    def test_walkthrough_mentions_all_rooms(self, simple_3room):
        graph = build_connectivity_graph(simple_3room)
        circ = analyze_circulation(simple_3room, graph)
        text = narrate_walkthrough(simple_3room, graph, circ["room_depth"])
        for room in simple_3room.rooms:
            assert room.name in text

    def test_critique_mentions_issues(self, disconnected):
        text = critique(disconnected)
        assert "cannot be reached" in text.lower() or "unreachable" in text.lower()

    def test_empty_plan(self):
        plan = FloorPlan()
        graph = build_connectivity_graph(plan)
        text = narrate_walkthrough(plan, graph, {})
        assert "empty" in text.lower()


# ---------------------------------------------------------------------------
# think_through (full analysis)
# ---------------------------------------------------------------------------

class TestThinkThrough:

    def test_returns_analysis(self, simple_3room):
        analysis = think_through(simple_3room)
        assert isinstance(analysis, FloorPlanAnalysis)

    def test_score_range(self, simple_3room):
        analysis = think_through(simple_3room)
        assert 0 <= analysis.score <= 100

    def test_verdict_values(self, simple_3room):
        analysis = think_through(simple_3room)
        assert analysis.verdict in ("GOOD", "NEEDS WORK", "FUNDAMENTALLY FLAWED")

    def test_good_plan_scores_high(self, simple_3room):
        analysis = think_through(simple_3room)
        assert analysis.score >= 70

    def test_broken_plan_scores_lower(self, disconnected):
        analysis = think_through(disconnected)
        good_analysis = think_through(
            FloorPlanBuilder("Good")
            .add_room("Entry", RoomType.ENTRY, 0, 0, 5, 5)
            .add_room("Living", RoomType.LIVING, 5, 0, 12, 12)
            .add_room("Bedroom", RoomType.BEDROOM, 17, 0, 10, 12)
            .auto_interior_walls()
            .add_entry_door("south", 2.5)
            .add_door(5, 3, "Entry", "Living")
            .add_door(17, 6, "Living", "Bedroom")
            .add_window(22, 0, "Bedroom")
            .build()
        )
        assert analysis.score < good_analysis.score

    def test_floorplan_analyze_method(self, edrawmax):
        analysis = edrawmax.analyze()
        assert isinstance(analysis, FloorPlanAnalysis)
        assert analysis.score > 0

    def test_floorplan_narrate_method(self, edrawmax):
        text = edrawmax.narrate()
        assert len(text) > 50
        assert "enter" in text.lower()

    def test_floorplan_critique_method(self, edrawmax):
        text = edrawmax.critique()
        assert len(text) > 50
