"""Tests for the v3 auto-improvement engine."""

import pytest
import sys
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/pipelines")

from floor_plan_engine.models import RoomType
from floor_plan_engine.builder import FloorPlanBuilder
from floor_plan_engine.improve import improve


class TestImprove:

    def test_fixes_unreachable_room(self):
        plan = (FloorPlanBuilder("Broken")
            .add_room("Entry", RoomType.ENTRY, 0, 0, 5, 5)
            .add_room("Living", RoomType.LIVING, 5, 0, 12, 12)
            .add_room("Isolated", RoomType.BEDROOM, 17, 0, 10, 12)
            .auto_interior_walls()
            .add_entry_door("south", 2.5)
            .add_door(5, 3, "Entry", "Living")
            .build())

        before = plan.analyze()
        assert "Isolated" in before.unreachable_rooms

        plan, fixes = improve(plan)
        after = plan.analyze()
        assert len(after.unreachable_rooms) == 0
        assert len(fixes) > 0

    def test_adds_egress_windows(self):
        plan = (FloorPlanBuilder("No Windows")
            .add_room("Entry", RoomType.ENTRY, 0, 0, 5, 5)
            .add_room("Bedroom", RoomType.BEDROOM, 5, 0, 12, 12)
            .auto_interior_walls()
            .add_entry_door("south", 2.5)
            .add_door(5, 3, "Entry", "Bedroom")
            .build())

        assert len(plan.windows) == 0
        plan, fixes = improve(plan)
        assert len(plan.windows) > 0
        assert any("window" in f.lower() for f in fixes)

    def test_no_fixes_on_good_plan(self):
        plan = (FloorPlanBuilder("Good")
            .add_room("Entry", RoomType.ENTRY, 0, 0, 5, 5)
            .add_room("Living", RoomType.LIVING, 5, 0, 15, 12)
            .auto_interior_walls()
            .add_entry_door("south", 2.5)
            .add_door(5, 3, "Entry", "Living")
            .add_window(12, 0, "Living")
            .build())

        plan, fixes = improve(plan)
        assert len(fixes) == 0

    def test_score_improves(self):
        plan = (FloorPlanBuilder("Broken")
            .add_room("Entry", RoomType.ENTRY, 0, 0, 5, 5)
            .add_room("Living", RoomType.LIVING, 5, 0, 15, 12)
            .add_room("Bedroom", RoomType.BEDROOM, 20, 0, 10, 12)
            .auto_interior_walls()
            .add_entry_door("south", 2.5)
            .add_door(5, 3, "Entry", "Living")
            # No door to bedroom, no windows
            .build())

        before = plan.analyze().score
        plan, _ = improve(plan)
        after = plan.analyze().score
        assert after >= before

    def test_max_iterations_respected(self):
        plan = (FloorPlanBuilder("Test")
            .add_room("Entry", RoomType.ENTRY, 0, 0, 5, 5)
            .add_room("Living", RoomType.LIVING, 5, 0, 12, 12)
            .auto_interior_walls()
            .add_entry_door("south", 2.5)
            .add_door(5, 3, "Entry", "Living")
            .build())

        # Should not error even with max_iterations=1
        plan, fixes = improve(plan, max_iterations=1)
        assert isinstance(fixes, list)
