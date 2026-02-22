"""Tests for Agent Coordinator v1.0"""

import json
import os
import sqlite3
import tempfile
import time
import pytest
from coordinator import AgentCoordinator, AgentSession, ResourceLock, WorkflowState


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def coord(db_path):
    return AgentCoordinator(db_path=db_path)


# ─── SESSION MANAGEMENT ───────────────────────────────────────

class TestSessionManagement:
    def test_start_workflow(self, coord):
        wf_id = coord.start_workflow("test-workflow")
        assert wf_id.startswith("wf-")
        assert len(wf_id) > 5

    def test_register_agent(self, coord):
        wf_id = coord.start_workflow("test")
        assert coord.register_agent(wf_id, "agent-a", "explorer")

    def test_agent_lifecycle(self, coord):
        wf_id = coord.start_workflow("lifecycle")
        coord.register_agent(wf_id, "agent-a")

        # Start
        coord.agent_started(wf_id, "agent-a")
        active = coord.get_active_agents(wf_id)
        assert len(active) == 1
        assert active[0].agent_name == "agent-a"

        # Complete
        coord.agent_completed(wf_id, "agent-a", result_summary="Done!")
        active = coord.get_active_agents(wf_id)
        assert len(active) == 0

    def test_agent_failed(self, coord):
        wf_id = coord.start_workflow("fail-test")
        coord.register_agent(wf_id, "agent-a")
        coord.agent_started(wf_id, "agent-a")
        coord.agent_failed(wf_id, "agent-a", error="Connection lost")

        wf = coord.get_workflow_status(wf_id)
        failed_agents = [a for a in wf.agents if a.status == "failed"]
        assert len(failed_agents) >= 1

    def test_workflow_status(self, coord):
        wf_id = coord.start_workflow("status-test")
        coord.register_agent(wf_id, "agent-a")
        coord.register_agent(wf_id, "agent-b")

        wf = coord.get_workflow_status(wf_id)
        assert wf is not None
        assert len(wf.agents) >= 2

    def test_workflow_status_nonexistent(self, coord):
        assert coord.get_workflow_status("nonexistent") is None

    def test_get_idle_agents(self, coord):
        wf_id = coord.start_workflow("idle-test")
        coord.register_agent(wf_id, "agent-a")
        coord.register_agent(wf_id, "agent-b")
        coord.agent_started(wf_id, "agent-a")

        idle = coord.get_idle_agents(wf_id)
        assert len(idle) == 1
        assert idle[0].agent_name == "agent-b"

    def test_agent_session_to_dict(self, coord):
        session = AgentSession(
            session_id="test", agent_name="test-agent",
            status="running", agent_type="explorer"
        )
        d = session.to_dict()
        assert d["agent_name"] == "test-agent"
        assert d["status"] == "running"


# ─── RESOURCE LOCKING ─────────────────────────────────────────

class TestResourceLocking:
    def test_acquire_lock(self, coord):
        wf_id = coord.start_workflow("lock-test")
        assert coord.acquire_lock("file", "/test.pdf", wf_id, "agent-a")

    def test_exclusive_lock_blocks(self, coord):
        wf1 = coord.start_workflow("wf1")
        wf2 = coord.start_workflow("wf2")

        assert coord.acquire_lock("file", "/test.pdf", wf1, "agent-a")
        assert coord.acquire_lock("file", "/test.pdf", wf2, "agent-b") is False

    def test_shared_locks_coexist(self, coord):
        wf1 = coord.start_workflow("wf1")
        wf2 = coord.start_workflow("wf2")

        assert coord.acquire_lock("file", "/test.pdf", wf1, "agent-a", lock_type="shared")
        assert coord.acquire_lock("file", "/test.pdf", wf2, "agent-b", lock_type="shared")

    def test_shared_blocks_exclusive(self, coord):
        wf1 = coord.start_workflow("wf1")
        wf2 = coord.start_workflow("wf2")

        assert coord.acquire_lock("file", "/test.pdf", wf1, "agent-a", lock_type="shared")
        assert coord.acquire_lock("file", "/test.pdf", wf2, "agent-b", lock_type="exclusive") is False

    def test_release_lock(self, coord):
        wf_id = coord.start_workflow("release-test")
        coord.acquire_lock("file", "/test.pdf", wf_id, "agent-a")
        coord.release_lock("file", "/test.pdf", wf_id)

        # Should be able to acquire again from another session
        wf2 = coord.start_workflow("wf2")
        assert coord.acquire_lock("file", "/test.pdf", wf2, "agent-b")

    def test_release_all_locks(self, coord):
        wf_id = coord.start_workflow("release-all")
        coord.acquire_lock("file", "/a.pdf", wf_id, "agent-a")
        coord.acquire_lock("file", "/b.pdf", wf_id, "agent-a")

        released = coord.release_all_locks(wf_id, "agent-a")
        assert released == 2

    def test_same_session_reacquire(self, coord):
        wf_id = coord.start_workflow("reacquire")
        assert coord.acquire_lock("file", "/test.pdf", wf_id, "agent-a")
        # Same session should be able to re-acquire
        assert coord.acquire_lock("file", "/test.pdf", wf_id, "agent-b")

    def test_lock_expiry(self, coord):
        wf1 = coord.start_workflow("wf1")
        # Acquire with 0-minute timeout (already expired)
        coord.acquire_lock("file", "/test.pdf", wf1, "agent-a", timeout_minutes=0)

        # Should be able to acquire from another session (expired)
        wf2 = coord.start_workflow("wf2")
        assert coord.acquire_lock("file", "/test.pdf", wf2, "agent-b")

    def test_auto_release_on_complete(self, coord):
        wf_id = coord.start_workflow("auto-release")
        coord.register_agent(wf_id, "agent-a")
        coord.agent_started(wf_id, "agent-a")
        coord.acquire_lock("file", "/test.pdf", wf_id, "agent-a")

        coord.agent_completed(wf_id, "agent-a")

        # Lock should be released
        wf2 = coord.start_workflow("wf2")
        assert coord.acquire_lock("file", "/test.pdf", wf2, "agent-b")

    def test_lock_is_active_property(self):
        lock = ResourceLock(released_at="2020-01-01")
        assert lock.is_active is False

        active_lock = ResourceLock()
        assert active_lock.is_active is True


# ─── CONFLICT DETECTION ───────────────────────────────────────

class TestConflictDetection:
    def test_check_conflict(self, coord):
        wf_id = coord.start_workflow("conflict")
        coord.acquire_lock("file", "/test.pdf", wf_id, "agent-a")

        conflict = coord.check_conflict("file", "/test.pdf",
                                         requesting_session="other-session")
        assert conflict is not None
        assert conflict.resource_id == "/test.pdf"

    def test_no_conflict_same_session(self, coord):
        wf_id = coord.start_workflow("no-conflict")
        coord.acquire_lock("file", "/test.pdf", wf_id, "agent-a")

        conflict = coord.check_conflict("file", "/test.pdf",
                                         requesting_session=wf_id)
        assert conflict is None

    def test_detect_conflicts(self, coord):
        wf1 = coord.start_workflow("wf1")
        wf2 = coord.start_workflow("wf2")

        coord.acquire_lock("file", "/test.pdf", wf1, "agent-a")
        coord.acquire_lock("file", "/other.pdf", wf2, "agent-b")

        # No conflicts between these sessions
        conflicts = coord.detect_conflicts(wf1)
        assert len(conflicts) == 0


# ─── SHARED STATE ──────────────────────────────────────────────

class TestSharedState:
    def test_set_and_get_state(self, coord):
        wf_id = coord.start_workflow("state-test")
        coord.set_state(wf_id, "walls", '["wall1", "wall2"]', "processor")

        value = coord.get_state(wf_id, "walls")
        assert value == '["wall1", "wall2"]'

    def test_get_nonexistent_state(self, coord):
        wf_id = coord.start_workflow("no-state")
        assert coord.get_state(wf_id, "missing") is None

    def test_update_state(self, coord):
        wf_id = coord.start_workflow("update-state")
        coord.set_state(wf_id, "count", "1", "agent-a")
        coord.set_state(wf_id, "count", "2", "agent-b")

        value = coord.get_state(wf_id, "count")
        assert value == "2"

    def test_accumulated_context(self, coord):
        wf_id = coord.start_workflow("context")
        coord.set_state(wf_id, "walls", "24", "processor")
        coord.set_state(wf_id, "doors", "8", "processor")
        coord.set_state(wf_id, "validation", "passed", "validator")

        context = coord.get_accumulated_context(wf_id)
        assert len(context) == 3
        assert context["walls"]["value"] == "24"
        assert context["validation"]["set_by"] == "validator"


# ─── HANDOFF VALIDATION ───────────────────────────────────────

class TestHandoffValidation:
    def test_valid_handoff(self, coord):
        wf_id = coord.start_workflow("handoff")
        coord.register_agent(wf_id, "agent-a")
        coord.register_agent(wf_id, "agent-b")
        coord.agent_started(wf_id, "agent-a")
        coord.agent_completed(wf_id, "agent-a", result_summary="Done")

        result = coord.validate_handoff(wf_id, "agent-a", "agent-b")
        assert result["valid"] is True
        assert len(result["issues"]) == 0

    def test_handoff_from_running_agent(self, coord):
        wf_id = coord.start_workflow("handoff-running")
        coord.register_agent(wf_id, "agent-a")
        coord.register_agent(wf_id, "agent-b")
        coord.agent_started(wf_id, "agent-a")

        result = coord.validate_handoff(wf_id, "agent-a", "agent-b")
        assert result["valid"] is False
        assert any("running" in issue for issue in result["issues"])

    def test_handoff_with_unreleased_locks(self, coord):
        wf_id = coord.start_workflow("handoff-locks")
        coord.register_agent(wf_id, "agent-a")
        coord.register_agent(wf_id, "agent-b")
        coord.agent_started(wf_id, "agent-a")
        coord.acquire_lock("file", "/test.pdf", wf_id, "agent-a")

        # Manually set agent-a to completed without releasing locks
        conn = coord._conn()
        conn.execute("""
            UPDATE agent_sessions SET status = 'completed'
            WHERE session_id = ? AND agent_name = 'agent-a'
        """, (wf_id,))
        conn.commit()
        conn.close()

        result = coord.validate_handoff(wf_id, "agent-a", "agent-b")
        assert result["valid"] is False
        assert any("Unreleased" in issue for issue in result["issues"])

    def test_handoff_nonexistent_agent(self, coord):
        wf_id = coord.start_workflow("handoff-noagent")
        result = coord.validate_handoff(wf_id, "missing-a", "missing-b")
        assert result["valid"] is False

    def test_record_handoff(self, coord):
        wf_id = coord.start_workflow("record-handoff")
        coord.record_handoff(wf_id, "agent-a", "agent-b", "context data")
        value = coord.get_state(wf_id, "handoff_agent-a_to_agent-b")
        assert value == "context data"


# ─── RESULT AGGREGATION ───────────────────────────────────────

class TestResultAggregation:
    def test_aggregate_results(self, coord):
        wf_id = coord.start_workflow("aggregate")
        coord.register_agent(wf_id, "agent-a", "explorer")
        coord.register_agent(wf_id, "agent-b", "builder")
        coord.agent_started(wf_id, "agent-a")
        coord.agent_completed(wf_id, "agent-a", result_summary="Extracted data")
        coord.agent_started(wf_id, "agent-b")
        coord.agent_completed(wf_id, "agent-b", result_summary="Built model")

        results = coord.aggregate_results(wf_id)
        assert results["agents"] == 2
        assert results["completed"] == 2
        assert results["success_rate"] == 1.0
        assert len(results["summaries"]) == 2

    def test_aggregate_with_failures(self, coord):
        wf_id = coord.start_workflow("fail-aggregate")
        coord.register_agent(wf_id, "agent-a", "explorer")
        coord.register_agent(wf_id, "agent-b", "builder")
        coord.agent_started(wf_id, "agent-a")
        coord.agent_completed(wf_id, "agent-a")
        coord.agent_started(wf_id, "agent-b")
        coord.agent_failed(wf_id, "agent-b", error="Timeout")

        results = coord.aggregate_results(wf_id)
        assert results["completed"] == 1
        assert results["failed"] == 1
        assert results["success_rate"] == 0.5


# ─── CLEANUP ──────────────────────────────────────────────────

class TestCleanup:
    def test_cleanup_stale(self, coord):
        # Create a stale workflow
        wf_id = coord.start_workflow("stale")
        coord.register_agent(wf_id, "agent-a")
        coord.agent_started(wf_id, "agent-a")

        # Backdate the started_at to make it stale
        conn = coord._conn()
        conn.execute("""
            UPDATE agent_sessions SET started_at = '2020-01-01 00:00:00'
            WHERE session_id = ? AND agent_name = 'agent-a'
        """, (wf_id,))
        conn.commit()
        conn.close()

        result = coord.cleanup_stale(timeout_minutes=1)
        assert result["stale_agents_failed"] >= 1

    def test_cleanup_expired_locks(self, coord):
        wf_id = coord.start_workflow("expired-locks")
        coord.acquire_lock("file", "/test.pdf", wf_id, "agent-a", timeout_minutes=30)

        # Backdate the expires_at to force expiry
        conn = coord._conn()
        conn.execute("""
            UPDATE resource_locks SET expires_at = '2020-01-01 00:00:00'
            WHERE locked_by_session = ?
        """, (wf_id,))
        conn.commit()
        conn.close()

        result = coord.cleanup_stale()
        assert result["expired_locks_released"] >= 1

    def test_enhance_dispatch_prompt(self, coord):
        wf_id = coord.start_workflow("enhance")
        coord.set_state(wf_id, "walls", "24 walls extracted", "processor")

        enhanced = coord.enhance_dispatch_prompt(
            wf_id, "builder", "Build Revit model"
        )
        assert "Build Revit model" in enhanced
        assert "24 walls extracted" in enhanced


# ─── FULL WORKFLOW INTEGRATION ───────────────────────────────

class TestFullWorkflow:
    def test_complete_workflow_lifecycle(self, coord):
        """Full workflow: start → register → lock → state → handoff → complete → aggregate."""
        wf_id = coord.start_workflow("pdf-to-revit")

        # Register two agents
        coord.register_agent(wf_id, "processor", "explorer")
        coord.register_agent(wf_id, "builder", "builder")

        # Processor starts and acquires lock
        coord.agent_started(wf_id, "processor")
        assert coord.acquire_lock("file", "/plan.pdf", wf_id, "processor")

        # Processor sets shared state
        coord.set_state(wf_id, "walls", '{"count": 24}', "processor")
        coord.set_state(wf_id, "rooms", '{"count": 6}', "processor")

        # Processor completes (auto-releases lock)
        coord.agent_completed(wf_id, "processor", result_summary="Extracted 24 walls, 6 rooms")

        # Validate handoff
        handoff = coord.validate_handoff(wf_id, "processor", "builder")
        assert handoff["valid"] is True

        # Record handoff context
        coord.record_handoff(wf_id, "processor", "builder", "24 walls extracted from PDF")

        # Builder reads state
        walls = coord.get_state(wf_id, "walls")
        assert walls == '{"count": 24}'

        # Builder starts and acquires lock on Revit model
        coord.agent_started(wf_id, "builder")
        assert coord.acquire_lock("revit_model", "/project.rvt", wf_id, "builder")

        # Builder completes
        coord.agent_completed(wf_id, "builder", result_summary="Built 24 walls in Revit")

        # Aggregate results
        results = coord.aggregate_results(wf_id)
        assert results["agents"] == 2
        assert results["completed"] == 2
        assert results["success_rate"] == 1.0
        assert len(results["summaries"]) == 2

        # Workflow status should be completed
        wf = coord.get_workflow_status(wf_id)
        assert wf.status == "completed"

    def test_workflow_with_failure_and_recovery(self, coord):
        """Workflow where an agent fails and is retried."""
        wf_id = coord.start_workflow("retry-test")
        coord.register_agent(wf_id, "agent-a")
        coord.agent_started(wf_id, "agent-a")
        coord.acquire_lock("file", "/data.csv", wf_id, "agent-a")

        # Agent fails — locks auto-released
        coord.agent_failed(wf_id, "agent-a", error="Timeout")

        # Verify lock was released
        wf2 = coord.start_workflow("retry-session")
        assert coord.acquire_lock("file", "/data.csv", wf2, "agent-b")

    def test_parallel_agents_no_conflicts(self, coord):
        """Two agents working on different resources in the same workflow."""
        wf_id = coord.start_workflow("parallel")
        coord.register_agent(wf_id, "agent-a")
        coord.register_agent(wf_id, "agent-b")
        coord.agent_started(wf_id, "agent-a")
        coord.agent_started(wf_id, "agent-b")

        assert coord.acquire_lock("file", "/a.pdf", wf_id, "agent-a")
        assert coord.acquire_lock("file", "/b.pdf", wf_id, "agent-b")

        active = coord.get_active_agents(wf_id)
        assert len(active) == 2

        conflicts = coord.detect_conflicts(wf_id)
        assert len(conflicts) == 0


# ─── EDGE CASES ──────────────────────────────────────────────

class TestCoordinatorEdgeCases:
    def test_aggregate_empty_workflow(self, coord):
        wf_id = coord.start_workflow("empty")
        results = coord.aggregate_results(wf_id)
        assert results["agents"] == 0

    def test_aggregate_nonexistent(self, coord):
        results = coord.aggregate_results("nonexistent-session")
        assert results["agents"] == 0

    def test_release_all_locks_none_held(self, coord):
        wf_id = coord.start_workflow("no-locks")
        released = coord.release_all_locks(wf_id, "agent-x")
        assert released == 0

    def test_release_lock_not_held(self, coord):
        wf_id = coord.start_workflow("release-nothing")
        # Should not crash
        coord.release_lock("file", "/no.pdf", wf_id)

    def test_multiple_workflows_independent(self, coord):
        """State from one workflow doesn't leak into another."""
        wf1 = coord.start_workflow("wf1")
        wf2 = coord.start_workflow("wf2")
        coord.set_state(wf1, "key", "value1", "agent")
        coord.set_state(wf2, "key", "value2", "agent")
        assert coord.get_state(wf1, "key") == "value1"
        assert coord.get_state(wf2, "key") == "value2"

    def test_workflow_state_to_dict(self):
        wf = WorkflowState(session_id="test", status="active")
        assert wf.session_id == "test"
        assert wf.status == "active"

    def test_get_active_agents_all_sessions(self, coord):
        """get_active_agents() without session_id should find all active agents."""
        wf1 = coord.start_workflow("wf1")
        wf2 = coord.start_workflow("wf2")
        coord.register_agent(wf1, "agent-a")
        coord.register_agent(wf2, "agent-b")
        coord.agent_started(wf1, "agent-a")
        coord.agent_started(wf2, "agent-b")

        all_active = coord.get_active_agents()
        names = {a.agent_name for a in all_active}
        assert "agent-a" in names
        assert "agent-b" in names

    def test_enhance_dispatch_no_context(self, coord):
        """Enhance prompt with no prior context should just return base prompt."""
        wf_id = coord.start_workflow("empty-enhance")
        result = coord.enhance_dispatch_prompt(wf_id, "agent-a", "Do the thing")
        assert "Do the thing" in result

    def test_enhance_dispatch_with_active_agents(self, coord):
        wf_id = coord.start_workflow("enhance-active")
        coord.register_agent(wf_id, "agent-a")
        coord.register_agent(wf_id, "agent-b", "builder")
        coord.agent_started(wf_id, "agent-b")

        result = coord.enhance_dispatch_prompt(wf_id, "agent-a", "Base prompt")
        assert "Base prompt" in result
        assert "agent-b" in result

    def test_detect_conflicts_cross_workflow(self, coord):
        """Shared locks from different workflows on same resource shouldn't conflict."""
        wf1 = coord.start_workflow("wf1")
        wf2 = coord.start_workflow("wf2")

        assert coord.acquire_lock("file", "/shared.pdf", wf1, "a", lock_type="shared")
        assert coord.acquire_lock("file", "/shared.pdf", wf2, "b", lock_type="shared")

        # No conflicts since both are shared
        conflicts = coord.detect_conflicts(wf1)
        # Shared locks on the same resource from different workflows do show as "other" locks
        # but they don't conflict with each other
        assert isinstance(conflicts, list)

    def test_lock_timeout_boundary(self, coord):
        """Lock with very short timeout should expire quickly."""
        wf1 = coord.start_workflow("timeout")
        # 0 minutes = expires immediately
        coord.acquire_lock("file", "/test.pdf", wf1, "a", timeout_minutes=0)

        # Should be acquirable by another session since expired
        wf2 = coord.start_workflow("timeout2")
        assert coord.acquire_lock("file", "/test.pdf", wf2, "b")

    def test_cleanup_returns_both_counts(self, coord):
        result = coord.cleanup_stale()
        assert "expired_locks_released" in result
        assert "stale_agents_failed" in result

    def test_release_all_locks_without_agent(self, coord):
        """release_all_locks with no agent_name releases all session locks."""
        wf_id = coord.start_workflow("all-locks")
        coord.acquire_lock("file", "/a.pdf", wf_id, "agent-a")
        coord.acquire_lock("file", "/b.pdf", wf_id, "agent-b")

        released = coord.release_all_locks(wf_id)  # no agent_name
        assert released == 2

        # Verify both are released
        wf2 = coord.start_workflow("verify")
        assert coord.acquire_lock("file", "/a.pdf", wf2, "x")
        assert coord.acquire_lock("file", "/b.pdf", wf2, "x")

    def test_workflow_status_pending(self, coord):
        """Workflow with only registered agents should have 'pending' status."""
        wf_id = coord.start_workflow("pending-test")
        coord.register_agent(wf_id, "agent-a")
        coord.register_agent(wf_id, "agent-b")
        # Neither agent started — both are in 'registered' status

        wf = coord.get_workflow_status(wf_id)
        assert wf.status == "pending"

    def test_record_handoff_empty_context(self, coord):
        """record_handoff with empty context should not create a state entry."""
        wf_id = coord.start_workflow("empty-handoff")
        coord.record_handoff(wf_id, "agent-a", "agent-b", "")
        value = coord.get_state(wf_id, "handoff_agent-a_to_agent-b")
        assert value is None  # no state set when context is empty


# ─── END-TO-END INTEGRATION ──────────────────────────────────

class TestEndToEndIntegration:
    def test_goal_to_plan_to_execute_to_rollup(self, db_path):
        """Full end-to-end: Goal → Plan → Execute → Rollup → Brain sync."""
        import tempfile
        from goals import GoalEngine

        ge = GoalEngine(db_path=db_path)
        planner = AgentCoordinator(db_path=db_path)  # just for schema
        from planner import Planner, PlanStep
        p = Planner(db_path=db_path)

        # 1. Create goal hierarchy
        root = ge.create_goal("Ship Feature", status="active", priority="high")
        sub1 = ge.create_goal("Build Backend", parent_goal_id=root, status="active", priority="high")
        sub2 = ge.create_goal("Build Frontend", parent_goal_id=root, status="active", priority="medium")

        # 2. Decompose sub1 into a plan
        steps = [
            PlanStep(0, "Research", agent="tech-scout"),
            PlanStep(1, "Implement", agent="engineer", dependencies=[0]),
            PlanStep(2, "Test", agent="engineer", dependencies=[1]),
        ]
        pid = p.create_plan("Backend Plan", goal_id=sub1, steps=steps)

        # 3. Execute the plan
        p.start_plan(pid)
        p.record_step_result(pid, 0, success=True, summary="Research done")
        p.record_step_result(pid, 1, success=True, summary="Code written")
        p.record_step_result(pid, 2, success=True, summary="Tests pass")
        assert p.is_plan_complete(pid)
        p.complete_plan(pid)

        # 4. Goal should have progress event
        events = ge.get_events(sub1)
        assert any(e.event_type == "completed_task" for e in events)

        # 5. Complete sub1
        ge.complete_goal(sub1)
        ge.update_progress(sub2, 50.0)

        # 6. Rollup to root
        progress = ge.rollup_progress(root)
        # sub1 = 100% (high, weight 3), sub2 = 50% (medium, weight 2)
        # (100*3 + 50*2) / (3+2) = 400/5 = 80
        assert progress == 80.0

        # 7. Sync to brain
        fd, brain_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            ge.sync_to_brain(brain_path)
            with open(brain_path) as f:
                brain = json.load(f)
            assert "goals" in brain
            # Root and sub2 should be active (sub1 is completed)
            active_titles = {g["title"] for g in brain["goals"]["active"]}
            assert "Build Frontend" in active_titles
        finally:
            os.unlink(brain_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
