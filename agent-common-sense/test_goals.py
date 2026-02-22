"""Tests for GoalEngine v1.0"""

import json
import os
import sqlite3
import tempfile
import pytest
from goals import GoalEngine, Goal, GoalEvent


@pytest.fixture
def db_path():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def engine(db_path):
    """Create a GoalEngine with a temp database."""
    return GoalEngine(db_path=db_path)


# ─── CRUD ──────────────────────────────────────────────────────

class TestGoalCRUD:
    def test_create_goal(self, engine):
        gid = engine.create_goal("Test Goal", description="A test", priority="high")
        assert gid > 0
        goal = engine.get_goal(gid)
        assert goal.title == "Test Goal"
        assert goal.description == "A test"
        assert goal.priority == "high"
        assert goal.status == "draft"
        assert goal.progress_pct == 0.0

    def test_create_goal_invalid_status(self, engine):
        with pytest.raises(ValueError, match="Invalid status"):
            engine.create_goal("Bad", status="invalid")

    def test_create_goal_invalid_priority(self, engine):
        with pytest.raises(ValueError, match="Invalid priority"):
            engine.create_goal("Bad", priority="super")

    def test_get_nonexistent(self, engine):
        assert engine.get_goal(9999) is None

    def test_update_goal(self, engine):
        gid = engine.create_goal("Original")
        engine.update_goal(gid, title="Updated", status="active", priority="high")
        goal = engine.get_goal(gid)
        assert goal.title == "Updated"
        assert goal.status == "active"
        assert goal.priority == "high"

    def test_update_nonexistent(self, engine):
        assert engine.update_goal(9999, title="X") is False

    def test_update_invalid_status(self, engine):
        gid = engine.create_goal("Test")
        with pytest.raises(ValueError):
            engine.update_goal(gid, status="bad")

    def test_delete_goal(self, engine):
        gid = engine.create_goal("To Delete")
        assert engine.delete_goal(gid)
        assert engine.get_goal(gid) is None

    def test_delete_nonexistent(self, engine):
        assert engine.delete_goal(9999) is False

    def test_delete_cascade(self, engine):
        parent = engine.create_goal("Parent")
        child = engine.create_goal("Child", parent_goal_id=parent)
        grandchild = engine.create_goal("Grandchild", parent_goal_id=child)
        engine.delete_goal(parent, cascade=True)
        assert engine.get_goal(parent) is None
        assert engine.get_goal(child) is None
        assert engine.get_goal(grandchild) is None

    def test_goal_to_dict(self, engine):
        gid = engine.create_goal("Dict Test", project="proj", domain="bim")
        goal = engine.get_goal(gid)
        d = goal.to_dict()
        assert d["title"] == "Dict Test"
        assert d["project"] == "proj"
        assert d["domain"] == "bim"
        assert "children" not in d  # children not in dict output

    def test_goal_properties(self, engine):
        gid = engine.create_goal("Props Test")
        goal = engine.get_goal(gid)
        assert goal.is_leaf is True
        assert goal.is_complete is False
        assert goal.is_active is False
        assert goal.priority_rank == 2  # medium


# ─── HIERARCHY ─────────────────────────────────────────────────

class TestGoalHierarchy:
    def test_parent_child(self, engine):
        parent = engine.create_goal("Parent")
        child1 = engine.create_goal("Child 1", parent_goal_id=parent)
        child2 = engine.create_goal("Child 2", parent_goal_id=parent)

        children = engine.get_children(parent)
        assert len(children) == 2
        assert {c.title for c in children} == {"Child 1", "Child 2"}

    def test_get_roots(self, engine):
        r1 = engine.create_goal("Root 1")
        r2 = engine.create_goal("Root 2")
        engine.create_goal("Child", parent_goal_id=r1)

        roots = engine.get_roots()
        root_ids = {r.id for r in roots}
        assert r1 in root_ids
        assert r2 in root_ids

    def test_get_tree(self, engine):
        parent = engine.create_goal("Parent")
        child = engine.create_goal("Child", parent_goal_id=parent)
        engine.create_goal("Grandchild", parent_goal_id=child)

        tree = engine.get_tree(parent)
        assert len(tree) == 1
        assert tree[0].title == "Parent"
        assert len(tree[0].children) == 1
        assert tree[0].children[0].title == "Child"
        assert len(tree[0].children[0].children) == 1

    def test_get_tree_all(self, engine):
        engine.create_goal("Root1")
        engine.create_goal("Root2")
        tree = engine.get_tree(None)
        assert len(tree) >= 2

    def test_cycle_detection(self, engine):
        p = engine.create_goal("Parent")
        c = engine.create_goal("Child", parent_goal_id=p)
        with pytest.raises(ValueError, match="cycle"):
            engine.move_goal(p, c)

    def test_self_cycle_detection(self, engine):
        g = engine.create_goal("Self")
        with pytest.raises(ValueError, match="cycle"):
            engine.move_goal(g, g)

    def test_move_goal(self, engine):
        r1 = engine.create_goal("Root1")
        r2 = engine.create_goal("Root2")
        child = engine.create_goal("Child", parent_goal_id=r1)

        engine.move_goal(child, r2)
        assert len(engine.get_children(r1)) == 0
        assert len(engine.get_children(r2)) == 1

    def test_move_to_root(self, engine):
        parent = engine.create_goal("Parent")
        child = engine.create_goal("Child", parent_goal_id=parent)
        engine.move_goal(child, None)
        goal = engine.get_goal(child)
        assert goal.parent_goal_id is None

    def test_invalid_parent(self, engine):
        with pytest.raises(ValueError, match="not found"):
            engine.create_goal("Test", parent_goal_id=9999)

    def test_is_leaf(self, engine):
        parent = engine.create_goal("Parent")
        child = engine.create_goal("Child", parent_goal_id=parent)
        # Parent has children loaded by get_children; but Goal.is_leaf checks goal.children
        parent_goal = engine.get_goal(parent)
        assert parent_goal.is_leaf is True  # children not populated yet
        engine._populate_children(parent_goal)
        assert parent_goal.is_leaf is False


# ─── DEPENDENCIES ──────────────────────────────────────────────

class TestGoalDependencies:
    def test_add_dependency(self, engine):
        g1 = engine.create_goal("Goal 1")
        g2 = engine.create_goal("Goal 2")
        assert engine.add_dependency(g2, g1)

    def test_self_dependency(self, engine):
        g = engine.create_goal("Self")
        with pytest.raises(ValueError, match="itself"):
            engine.add_dependency(g, g)

    def test_invalid_dep_type(self, engine):
        g1 = engine.create_goal("G1")
        g2 = engine.create_goal("G2")
        with pytest.raises(ValueError, match="Invalid dependency"):
            engine.add_dependency(g2, g1, "invalid")

    def test_circular_dependency(self, engine):
        g1 = engine.create_goal("G1")
        g2 = engine.create_goal("G2")
        g3 = engine.create_goal("G3")
        engine.add_dependency(g2, g1)
        engine.add_dependency(g3, g2)
        with pytest.raises(ValueError, match="circular"):
            engine.add_dependency(g1, g3)

    def test_is_ready(self, engine):
        g1 = engine.create_goal("Blocker", status="active")
        g2 = engine.create_goal("Blocked", status="active")
        engine.add_dependency(g2, g1)
        assert engine.is_ready(g2) is False

        engine.complete_goal(g1)
        assert engine.is_ready(g2) is True

    def test_get_blocked_by(self, engine):
        g1 = engine.create_goal("Blocker", status="active")
        g2 = engine.create_goal("Blocked", status="active")
        engine.add_dependency(g2, g1)

        blockers = engine.get_blocked_by(g2)
        assert len(blockers) == 1
        assert blockers[0].id == g1

    def test_get_dependents(self, engine):
        g1 = engine.create_goal("Base")
        g2 = engine.create_goal("Dependent1")
        g3 = engine.create_goal("Dependent2")
        engine.add_dependency(g2, g1)
        engine.add_dependency(g3, g1)

        deps = engine.get_dependents(g1)
        assert len(deps) == 2

    def test_remove_dependency(self, engine):
        g1 = engine.create_goal("G1")
        g2 = engine.create_goal("G2")
        engine.add_dependency(g2, g1)
        assert engine.is_ready(g2) is False
        engine.remove_dependency(g2, g1)
        assert engine.is_ready(g2) is True

    def test_soft_dependency_doesnt_block(self, engine):
        g1 = engine.create_goal("Soft Dep", status="active")
        g2 = engine.create_goal("Goal", status="active")
        engine.add_dependency(g2, g1, dependency_type="soft")
        assert engine.is_ready(g2) is True  # soft deps don't block


# ─── PROGRESS ──────────────────────────────────────────────────

class TestGoalProgress:
    def test_update_progress(self, engine):
        gid = engine.create_goal("Test")
        engine.update_progress(gid, 50.0)
        goal = engine.get_goal(gid)
        assert goal.progress_pct == 50.0

    def test_progress_clamped(self, engine):
        gid = engine.create_goal("Test")
        engine.update_progress(gid, 150.0)
        goal = engine.get_goal(gid)
        assert goal.progress_pct == 100.0

        engine.update_progress(gid, -10.0)
        goal = engine.get_goal(gid)
        assert goal.progress_pct == 0.0

    def test_rollup_progress(self, engine):
        parent = engine.create_goal("Parent", status="active")
        c1 = engine.create_goal("Child1", parent_goal_id=parent, priority="medium")
        c2 = engine.create_goal("Child2", parent_goal_id=parent, priority="medium")

        engine.update_progress(c1, 100.0)
        engine.update_progress(c2, 50.0)

        result = engine.rollup_progress(parent)
        assert result == 75.0  # equal weight: (100+50)/2

    def test_rollup_weighted(self, engine):
        parent = engine.create_goal("Parent")
        c1 = engine.create_goal("High", parent_goal_id=parent, priority="high")
        c2 = engine.create_goal("Low", parent_goal_id=parent, priority="low")

        engine.update_progress(c1, 100.0)
        engine.update_progress(c2, 0.0)

        result = engine.rollup_progress(parent)
        # high=3, low=1: (100*3 + 0*1) / (3+1) = 75.0
        assert result == 75.0

    def test_rollup_recursive(self, engine):
        root = engine.create_goal("Root")
        mid = engine.create_goal("Mid", parent_goal_id=root, priority="medium")
        leaf1 = engine.create_goal("Leaf1", parent_goal_id=mid, priority="medium")
        leaf2 = engine.create_goal("Leaf2", parent_goal_id=mid, priority="medium")

        engine.update_progress(leaf1, 100.0)
        engine.update_progress(leaf2, 50.0)

        result = engine.rollup_progress(root)
        # mid should be 75%, root gets 75% from mid
        assert result == 75.0

    def test_complete_goal_rollup(self, engine):
        parent = engine.create_goal("Parent", status="active")
        c1 = engine.create_goal("C1", parent_goal_id=parent, priority="medium")
        c2 = engine.create_goal("C2", parent_goal_id=parent, priority="medium")

        engine.complete_goal(c1)
        parent_goal = engine.get_goal(parent)
        assert parent_goal.progress_pct == 50.0  # one of two done


# ─── QUERIES ──────────────────────────────────────────────────

class TestGoalQueries:
    def test_list_all(self, engine):
        engine.create_goal("A")
        engine.create_goal("B")
        goals = engine.list_goals()
        assert len(goals) >= 2

    def test_list_by_project(self, engine):
        engine.create_goal("A", project="alpha")
        engine.create_goal("B", project="beta")
        goals = engine.list_goals(project="alpha")
        assert len(goals) == 1
        assert goals[0].title == "A"

    def test_list_by_status(self, engine):
        engine.create_goal("Draft", status="draft")
        engine.create_goal("Active", status="active")
        goals = engine.list_goals(status="active")
        assert all(g.status == "active" for g in goals)

    def test_search_goals(self, engine):
        engine.create_goal("Build Revit Bridge", description="C# MCP bridge")
        engine.create_goal("Cook dinner")
        results = engine.search_goals("Revit")
        assert len(results) == 1
        assert "Revit" in results[0].title

    def test_get_actionable(self, engine):
        g1 = engine.create_goal("Leaf Active", status="active")
        engine.create_goal("Leaf Draft", status="draft")
        parent = engine.create_goal("Parent Active", status="active")
        engine.create_goal("Child", parent_goal_id=parent, status="active")

        actionable = engine.get_actionable()
        ids = {g.id for g in actionable}
        assert g1 in ids
        # parent should NOT be in actionable (has children)
        assert parent not in ids

    def test_get_actionable_respects_deps(self, engine):
        blocker = engine.create_goal("Blocker", status="active")
        blocked = engine.create_goal("Blocked", status="active")
        engine.add_dependency(blocked, blocker)

        actionable = engine.get_actionable()
        ids = {g.id for g in actionable}
        assert blocker in ids
        assert blocked not in ids

    def test_get_stale(self, engine):
        gid = engine.create_goal("Stale", status="active")
        # Manually backdate
        conn = sqlite3.connect(engine.db_path)
        conn.execute(
            "UPDATE goals SET updated_at = '2020-01-01 00:00:00' WHERE id = ?",
            (gid,)
        )
        conn.commit()
        conn.close()

        stale = engine.get_stale(days=1)
        assert any(g.id == gid for g in stale)


# ─── INTEGRATION ──────────────────────────────────────────────

class TestGoalIntegration:
    def test_link_task(self, engine):
        gid = engine.create_goal("Test")
        assert engine.link_task_to_goal(gid, "Write unit tests")
        events = engine.get_events(gid)
        assert any(e.event_type == "linked_task" for e in events)

    def test_on_task_completed(self, engine):
        gid = engine.create_goal("Test", status="active")
        engine.on_task_completed(gid, "Tests pass", progress_increment=25.0)
        goal = engine.get_goal(gid)
        assert goal.progress_pct == 25.0
        events = engine.get_events(gid)
        assert any(e.event_type == "completed_task" for e in events)

    def test_sync_to_brain(self, engine):
        fd, brain_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            engine.create_goal("Active Goal", status="active", priority="high")
            engine.create_goal("Draft Goal", status="draft")

            assert engine.sync_to_brain(brain_path)

            with open(brain_path) as f:
                brain = json.load(f)
            assert "goals" in brain
            assert len(brain["goals"]["active"]) == 1
            assert brain["goals"]["active"][0]["title"] == "Active Goal"
        finally:
            os.unlink(brain_path)

    def test_to_memory_summary(self, engine):
        engine.create_goal("Goal A", status="active", priority="high")
        engine.create_goal("Goal B", status="active", priority="medium")
        summary = engine.to_memory_summary()
        assert "Active goals (2)" in summary
        assert "Goal A" in summary

    def test_events_audit_trail(self, engine):
        gid = engine.create_goal("Audited")
        engine.update_goal(gid, status="active")
        engine.update_progress(gid, 50.0)
        engine.complete_goal(gid)

        events = engine.get_events(gid)
        types = [e.event_type for e in events]
        assert "created" in types
        assert "status_change" in types
        assert "progress_update" in types

    def test_format_tree(self, engine):
        parent = engine.create_goal("Root", status="active")
        engine.create_goal("Child", parent_goal_id=parent, status="draft")
        tree = engine.get_tree(parent)
        output = engine.format_tree(tree)
        assert "Root" in output
        assert "Child" in output


# ─── EDGE CASES ───────────────────────────────────────────────

class TestGoalEdgeCases:
    def test_create_with_all_fields(self, engine):
        gid = engine.create_goal(
            "Full Goal", description="Full desc",
            project="proj", status="active", priority="critical",
            deadline="2026-12-31", tags=["tag1", "tag2"],
            domain="bim", source="auto", notes="Some notes"
        )
        goal = engine.get_goal(gid)
        assert goal.priority == "critical"
        assert goal.domain == "bim"
        assert goal.source == "auto"
        assert goal.notes == "Some notes"
        assert goal.deadline == "2026-12-31"
        assert "tag1" in goal.tags

    def test_delete_without_cascade_orphans_children(self, engine):
        parent = engine.create_goal("Parent")
        child = engine.create_goal("Child", parent_goal_id=parent)
        engine.delete_goal(parent, cascade=False)
        # Child should still exist but with NULL parent
        orphan = engine.get_goal(child)
        assert orphan is not None
        assert orphan.parent_goal_id is None

    def test_complete_nonexistent_goal(self, engine):
        result = engine.complete_goal(9999)
        assert result is False

    def test_rollup_no_children(self, engine):
        gid = engine.create_goal("Leaf", status="active")
        engine.update_progress(gid, 42.0)
        result = engine.rollup_progress(gid)
        assert result == 42.0

    def test_update_with_tags_list(self, engine):
        gid = engine.create_goal("Tags Test")
        engine.update_goal(gid, tags=["a", "b", "c"])
        goal = engine.get_goal(gid)
        tags = json.loads(goal.tags)
        assert tags == ["a", "b", "c"]

    def test_multiple_status_transitions(self, engine):
        gid = engine.create_goal("Lifecycle")
        engine.update_goal(gid, status="active")
        engine.update_goal(gid, status="blocked")
        engine.update_goal(gid, status="active")
        engine.complete_goal(gid)
        goal = engine.get_goal(gid)
        assert goal.status == "completed"
        events = engine.get_events(gid)
        status_changes = [e for e in events if e.event_type == "status_change"]
        assert len(status_changes) == 4  # draft->active, active->blocked, blocked->active, active->completed

    def test_on_task_completed_nonexistent(self, engine):
        assert engine.on_task_completed(9999, "test") is False

    def test_on_task_completed_no_increment(self, engine):
        gid = engine.create_goal("Test", status="active")
        engine.update_progress(gid, 50.0)
        engine.on_task_completed(gid, "task done", progress_increment=0)
        goal = engine.get_goal(gid)
        assert goal.progress_pct == 50.0  # unchanged

    def test_search_by_description(self, engine):
        engine.create_goal("Generic Title", description="MCP bridge for Revit")
        results = engine.search_goals("bridge")
        assert len(results) == 1

    def test_search_by_notes(self, engine):
        engine.create_goal("Goal", notes="needs refactoring")
        results = engine.search_goals("refactoring")
        assert len(results) == 1

    def test_search_no_results(self, engine):
        engine.create_goal("Alpha")
        results = engine.search_goals("zzznonexistent")
        assert len(results) == 0

    def test_list_by_priority(self, engine):
        engine.create_goal("H", priority="high")
        engine.create_goal("L", priority="low")
        goals = engine.list_goals(priority="high")
        assert all(g.priority == "high" for g in goals)

    def test_list_by_domain(self, engine):
        engine.create_goal("BIM goal", domain="bim")
        engine.create_goal("Dev goal", domain="dev")
        goals = engine.list_goals(domain="bim")
        assert len(goals) == 1

    def test_get_stale_no_results(self, engine):
        engine.create_goal("Fresh", status="active")
        stale = engine.get_stale(days=1)
        assert len(stale) == 0

    def test_sync_to_brain_creates_new_file(self, engine, db_path):
        import tempfile
        brain_path = os.path.join(tempfile.gettempdir(), "brain_new_test.json")
        try:
            engine.create_goal("Goal A", status="active")
            engine.complete_goal(engine.create_goal("Done", status="active"))
            assert engine.sync_to_brain(brain_path)
            with open(brain_path) as f:
                brain = json.load(f)
            assert "summary" in brain["goals"]
            assert "last_sync" in brain["goals"]
        finally:
            if os.path.exists(brain_path):
                os.unlink(brain_path)

    def test_to_memory_summary_no_goals(self, engine):
        summary = engine.to_memory_summary()
        assert summary == "No active goals."

    def test_priority_rank_critical(self, engine):
        gid = engine.create_goal("Critical", priority="critical")
        goal = engine.get_goal(gid)
        assert goal.priority_rank == 0

    def test_deep_hierarchy_rollup(self, engine):
        """Test rollup through 4 levels of hierarchy."""
        root = engine.create_goal("Root")
        level1 = engine.create_goal("L1", parent_goal_id=root, priority="medium")
        level2 = engine.create_goal("L2", parent_goal_id=level1, priority="medium")
        leaf = engine.create_goal("Leaf", parent_goal_id=level2, priority="medium")
        engine.update_progress(leaf, 80.0)
        result = engine.rollup_progress(root)
        assert result == 80.0  # Single path, should cascade up

    def test_update_invalid_priority(self, engine):
        gid = engine.create_goal("Test")
        with pytest.raises(ValueError, match="Invalid priority"):
            engine.update_goal(gid, priority="super")

    def test_update_with_unknown_fields(self, engine):
        """update_goal with non-allowed fields should return False (no updates)."""
        gid = engine.create_goal("Test")
        result = engine.update_goal(gid, nonexistent_field="value")
        assert result is False

    def test_sync_to_brain_corrupted_json(self, engine):
        """sync_to_brain should handle a corrupted existing brain.json."""
        fd, brain_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(brain_path, 'w') as f:
                f.write("{{{invalid json!!!")
            engine.create_goal("Active", status="active")
            assert engine.sync_to_brain(brain_path)
            with open(brain_path) as f:
                brain = json.load(f)
            assert "goals" in brain
        finally:
            os.unlink(brain_path)

    def test_dependency_chain_readiness(self, engine):
        """A -> B -> C: C should not be ready until both A and B are completed."""
        a = engine.create_goal("A", status="active")
        b = engine.create_goal("B", status="active")
        c = engine.create_goal("C", status="active")
        engine.add_dependency(b, a)
        engine.add_dependency(c, b)
        assert engine.is_ready(c) is False
        engine.complete_goal(a)
        assert engine.is_ready(c) is False  # B still not done
        engine.complete_goal(b)
        assert engine.is_ready(c) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
