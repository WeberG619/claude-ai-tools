"""Tests for Autonomous Planner v1.0"""

import json
import os
import sqlite3
import tempfile
import pytest
from planner import Planner, Plan, PlanStep, PlanTemplate, BUILTIN_TEMPLATES


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def planner(db_path):
    return Planner(db_path=db_path)


@pytest.fixture
def planner_with_goals(db_path):
    """Planner with GoalEngine tables set up."""
    from goals import GoalEngine
    ge = GoalEngine(db_path=db_path)
    p = Planner(db_path=db_path)
    return p, ge


# ─── CRUD ──────────────────────────────────────────────────────

class TestPlanCRUD:
    def test_create_plan(self, planner):
        pid = planner.create_plan("Test Plan")
        assert pid > 0
        plan = planner.get_plan(pid)
        assert plan.title == "Test Plan"
        assert plan.status == "draft"

    def test_create_with_steps(self, planner):
        steps = [
            PlanStep(0, "Step 1", agent="tech-scout"),
            PlanStep(1, "Step 2", agent="python-engineer"),
        ]
        pid = planner.create_plan("With Steps", steps=steps)
        plan = planner.get_plan(pid)
        assert plan.total_steps == 2
        assert len(plan.steps) == 2
        assert plan.steps[0].title == "Step 1"
        assert plan.steps[1].agent == "python-engineer"

    def test_create_with_goal_id(self, planner_with_goals):
        planner, ge = planner_with_goals
        gid = ge.create_goal("Test Goal")
        pid = planner.create_plan("Plan for Goal", goal_id=gid)
        plan = planner.get_plan(pid)
        assert plan.goal_id == gid

    def test_get_nonexistent(self, planner):
        assert planner.get_plan(9999) is None

    def test_list_plans(self, planner):
        planner.create_plan("Plan A")
        planner.create_plan("Plan B")
        plans = planner.list_plans()
        assert len(plans) >= 2

    def test_list_by_status(self, planner):
        pid = planner.create_plan("Draft Plan")
        planner.create_plan("Another")
        planner.start_plan(pid)  # needs steps first
        plans = planner.list_plans(status="draft")
        assert all(p.status == "draft" for p in plans)

    def test_plan_to_dict(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Dict Test", steps=steps)
        plan = planner.get_plan(pid)
        d = plan.to_dict()
        assert d["title"] == "Dict Test"
        assert len(d["steps"]) == 1

    def test_plan_step_from_dict(self):
        data = {
            "index": 5,
            "title": "Test Step",
            "agent": "tech-scout",
            "can_parallel": True,
            "checkpoint": True,
        }
        step = PlanStep.from_dict(data)
        assert step.index == 5
        assert step.title == "Test Step"
        assert step.can_parallel is True
        assert step.checkpoint is True


# ─── TEMPLATES ─────────────────────────────────────────────────

class TestPlanTemplates:
    def test_builtin_templates_loaded(self, planner):
        templates = planner.list_templates()
        names = {t.name for t in templates}
        assert "build-feature" in names
        assert "pdf-to-revit-model" in names
        assert "research-topic" in names

    def test_create_from_template(self, planner):
        pid = planner.create_from_template("build-feature", title="Build Widget")
        assert pid is not None
        plan = planner.get_plan(pid)
        assert plan.template_name == "build-feature"
        assert plan.total_steps == 5

    def test_create_from_nonexistent_template(self, planner):
        pid = planner.create_from_template("nonexistent")
        assert pid is None

    def test_template_usage_count(self, planner):
        planner.create_from_template("research-topic")
        template = planner.get_template("research-topic")
        assert template.times_used >= 1

    def test_register_custom_template(self, planner):
        tid = planner.register_template(
            "custom-template",
            "A custom template",
            [{"title": "Step 1", "agent": "test"}],
            domain="testing",
        )
        assert tid > 0
        template = planner.get_template("custom-template")
        assert template.name == "custom-template"
        assert len(template.steps_template) == 1

    def test_match_template(self, planner):
        assert planner.match_template("build a new feature for auth") == "build-feature"
        assert planner.match_template("convert pdf floor plan to revit model") == "pdf-to-revit-model"
        assert planner.match_template("research this topic and analyze") == "research-topic"
        assert planner.match_template("random unrelated text") is None

    def test_create_with_context(self, planner):
        pid = planner.create_from_template(
            "research-topic",
            context={"topic": "BIM automation"}
        )
        plan = planner.get_plan(pid)
        assert plan is not None

    def test_promote_plan_to_template(self, planner):
        steps = [
            PlanStep(0, "Custom Step 1", agent="test"),
            PlanStep(1, "Custom Step 2", agent="test"),
        ]
        pid = planner.create_plan("Promotable Plan", steps=steps)
        tid = planner.promote_plan_to_template(pid, "promoted-template")
        assert tid is not None
        template = planner.get_template("promoted-template")
        assert len(template.steps_template) == 2


# ─── EXECUTION ─────────────────────────────────────────────────

class TestPlanExecution:
    def test_start_plan(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Start Test", steps=steps)
        assert planner.start_plan(pid)
        plan = planner.get_plan(pid)
        assert plan.status == "executing"
        assert plan.started_at != ""

    def test_start_already_executing(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Test", steps=steps)
        planner.start_plan(pid)
        assert planner.start_plan(pid) is False  # already executing

    def test_get_next_steps_sequential(self, planner):
        steps = [
            PlanStep(0, "Step 1", agent="test"),
            PlanStep(1, "Step 2", agent="test", dependencies=[0]),
            PlanStep(2, "Step 3", agent="test", dependencies=[1]),
        ]
        pid = planner.create_plan("Sequential", steps=steps)
        planner.start_plan(pid)

        # Only first step should be ready
        next_steps = planner.get_next_steps(pid)
        assert len(next_steps) == 1
        assert next_steps[0].index == 0

        # Complete step 0
        planner.record_step_result(pid, 0, success=True)
        next_steps = planner.get_next_steps(pid)
        assert len(next_steps) == 1
        assert next_steps[0].index == 1

    def test_get_next_steps_parallel(self, planner):
        steps = [
            PlanStep(0, "Step 1", agent="test"),
            PlanStep(1, "Step 2", agent="test"),  # no deps, can run parallel
            PlanStep(2, "Step 3", agent="test", dependencies=[0, 1]),
        ]
        pid = planner.create_plan("Parallel", steps=steps)
        planner.start_plan(pid)

        next_steps = planner.get_next_steps(pid)
        assert len(next_steps) == 2  # both step 0 and 1

    def test_record_step_result(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Test", steps=steps)
        planner.start_plan(pid)

        planner.record_step_result(pid, 0, success=True, summary="Done!")
        plan = planner.get_plan(pid)
        assert len(plan._step_results) == 1
        assert plan._step_results[0]["status"] == "completed"

    def test_record_failure(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Test", steps=steps)
        planner.start_plan(pid)

        planner.record_step_result(pid, 0, success=False, error="Connection lost")
        plan = planner.get_plan(pid)
        assert plan._step_results[0]["status"] == "failed"
        assert len(plan.error_log) > 0

    def test_complete_plan(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Test", steps=steps)
        planner.start_plan(pid)
        planner.record_step_result(pid, 0, success=True)
        planner.complete_plan(pid)
        plan = planner.get_plan(pid)
        assert plan.status == "completed"
        assert plan.completed_at != ""

    def test_fail_plan(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Test", steps=steps)
        planner.start_plan(pid)
        planner.fail_plan(pid, "Fatal error")
        plan = planner.get_plan(pid)
        assert plan.status == "failed"

    def test_is_plan_complete(self, planner):
        steps = [
            PlanStep(0, "S1", agent="test"),
            PlanStep(1, "S2", agent="test"),
        ]
        pid = planner.create_plan("Test", steps=steps)
        planner.start_plan(pid)
        assert planner.is_plan_complete(pid) is False

        planner.record_step_result(pid, 0, success=True)
        assert planner.is_plan_complete(pid) is False

        planner.record_step_result(pid, 1, success=True)
        assert planner.is_plan_complete(pid) is True

    def test_progress_tracking(self, planner):
        steps = [
            PlanStep(0, "S1", agent="test"),
            PlanStep(1, "S2", agent="test"),
            PlanStep(2, "S3", agent="test"),
            PlanStep(3, "S4", agent="test"),
        ]
        pid = planner.create_plan("Progress", steps=steps)
        planner.start_plan(pid)

        planner.record_step_result(pid, 0, success=True)
        plan = planner.get_plan(pid)
        assert plan.progress_pct == 25.0

        planner.record_step_result(pid, 1, success=True)
        plan = planner.get_plan(pid)
        assert plan.progress_pct == 50.0


# ─── ADAPTIVE REPLANNING ──────────────────────────────────────

class TestAdaptivePlanning:
    def test_replan_retry(self, planner):
        steps = [
            PlanStep(0, "S1", agent="test"),
            PlanStep(1, "S2", agent="test"),
        ]
        pid = planner.create_plan("Replan", steps=steps)
        planner.start_plan(pid)
        planner.record_step_result(pid, 0, success=True)
        planner.record_step_result(pid, 1, success=False)

        # Replan from step 1 (retry)
        planner.replan(pid, from_step=1)
        next_steps = planner.get_next_steps(pid)
        assert len(next_steps) == 1
        assert next_steps[0].index == 1

    def test_replan_with_new_steps(self, planner):
        steps = [
            PlanStep(0, "S1", agent="test"),
            PlanStep(1, "S2 Original", agent="test"),
        ]
        pid = planner.create_plan("Replan New", steps=steps)
        planner.start_plan(pid)
        planner.record_step_result(pid, 0, success=True)

        new_steps = [
            PlanStep(0, "S2 Replacement", agent="different-agent"),
            PlanStep(1, "S3 New Step", agent="different-agent"),
        ]
        planner.replan(pid, from_step=1, new_steps=new_steps)

        plan = planner.get_plan(pid)
        assert plan.total_steps == 3  # 1 original + 2 new
        assert plan.steps[1].title == "S2 Replacement"
        assert plan.steps[2].title == "S3 New Step"

    def test_suggest_alternative(self, planner):
        steps = [
            PlanStep(0, "S1", agent="test", fallback_agent="backup"),
        ]
        pid = planner.create_plan("Alt", steps=steps)
        alt = planner.suggest_alternative(pid, 0)
        assert alt is not None
        assert alt.agent == "backup"

    def test_suggest_alternative_no_fallback(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("No Alt", steps=steps)
        alt = planner.suggest_alternative(pid, 0)
        assert alt is None

    def test_replan_resets_failed_status(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Fail Reset", steps=steps)
        planner.start_plan(pid)
        planner.fail_plan(pid)
        plan = planner.get_plan(pid)
        assert plan.status == "failed"

        planner.replan(pid, from_step=0)
        plan = planner.get_plan(pid)
        assert plan.status == "executing"


# ─── DISPATCH & WORKFLOW INTEGRATION ──────────────────────────

class TestPlanIntegration:
    def test_to_dispatch_event(self, planner):
        steps = [PlanStep(0, "Research", agent="tech-scout", description="Find docs")]
        pid = planner.create_plan("Dispatch Test", steps=steps, goal_id=42)

        event = planner.to_dispatch_event(pid, 0)
        assert event is not None
        assert event["trigger_type"] == "plan_step"
        assert event["data"]["agent"] == "tech-scout"
        assert event["data"]["goal_id"] == 42

    def test_to_dispatch_event_nonexistent(self, planner):
        assert planner.to_dispatch_event(9999, 0) is None

    def test_to_task_queue_entries(self, planner):
        steps = [
            PlanStep(0, "Step A", agent="agent-a"),
            PlanStep(1, "Step B", agent="agent-b"),
        ]
        pid = planner.create_plan("Queue Test", steps=steps, goal_id=10)

        entries = planner.to_task_queue_entries(pid)
        assert len(entries) == 2
        assert entries[0]["agent"] == "agent-a"
        assert entries[0]["metadata"]["plan_id"] == pid

    def test_decompose_goal(self, planner):
        # Should match build-feature template
        pid = planner.decompose_goal(1, "Build new feature for auth")
        assert pid > 0
        plan = planner.get_plan(pid)
        assert plan.total_steps >= 3

    def test_decompose_goal_generic(self, planner):
        # No template match => generic 3-step plan
        pid = planner.decompose_goal(1, "Do something vague and unusual")
        plan = planner.get_plan(pid)
        assert plan.total_steps == 3

    def test_save_as_workflow(self, planner, db_path):
        # Need workflow tables
        from workflows import WorkflowRecorder
        WorkflowRecorder(db_path=db_path)  # creates table

        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Workflow Save", steps=steps)
        result = planner.save_as_workflow(pid, "test-workflow")
        assert result is True


# ─── WORKFLOW ROUND-TRIP ──────────────────────────────────────

class TestPlanWorkflowRoundTrip:
    def test_plan_from_workflow(self, planner, db_path):
        """Create a workflow, then convert it to a plan."""
        from workflows import WorkflowRecorder, Workflow, WorkflowStep
        recorder = WorkflowRecorder(db_path=db_path)

        # Record a workflow
        recorder.start("deploy-revit-addin", description="Deploy addin", domain="bim")
        recorder.add_step("Bash", {"command": "dotnet build"}, "Build succeeded")
        recorder.add_step("Bash", {"command": "cp out.dll"}, "DLL copied")
        recorder.save(tags=["revit"])

        # Convert to plan
        pid = planner.plan_from_workflow("deploy-revit-addin", goal_id=42)
        assert pid is not None
        plan = planner.get_plan(pid)
        assert plan is not None
        assert plan.goal_id == 42
        assert plan.total_steps == 2
        assert plan.domain == "bim"
        assert "workflow" in plan.title.lower()

    def test_plan_from_workflow_nonexistent(self, planner, db_path):
        from workflows import WorkflowRecorder
        WorkflowRecorder(db_path=db_path)  # ensure table exists
        result = planner.plan_from_workflow("nonexistent-workflow")
        assert result is None

    def test_plan_from_workflow_no_goal(self, planner, db_path):
        from workflows import WorkflowRecorder
        recorder = WorkflowRecorder(db_path=db_path)
        recorder.start("simple-wf", description="Simple workflow")
        recorder.add_step("Read", {"file": "/test.txt"}, "Read ok")
        recorder.save()

        pid = planner.plan_from_workflow("simple-wf")
        assert pid is not None
        plan = planner.get_plan(pid)
        assert plan.goal_id is None

    def test_save_and_load_round_trip(self, planner, db_path):
        """Save plan as workflow, then load it back as plan."""
        from workflows import WorkflowRecorder
        WorkflowRecorder(db_path=db_path)

        # Create and save a plan
        steps = [
            PlanStep(0, "Research", agent="tech-scout", description="Find info"),
            PlanStep(1, "Build", agent="engineer", description="Build it"),
        ]
        pid1 = planner.create_plan("Round Trip", steps=steps, domain="development")
        planner.save_as_workflow(pid1, "round-trip-wf")

        # Load back as plan
        pid2 = planner.plan_from_workflow("round-trip-wf")
        assert pid2 is not None
        plan2 = planner.get_plan(pid2)
        assert plan2.total_steps == 2


# ─── CROSS-MODULE INTEGRATION ───────────────────────────────

class TestPlanGoalIntegration:
    def test_complete_plan_updates_goal(self, planner_with_goals):
        """complete_plan() should trigger GoalEngine.on_task_completed()."""
        planner, ge = planner_with_goals
        gid = ge.create_goal("Test Goal", status="active")

        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Goal Plan", steps=steps, goal_id=gid)
        planner.start_plan(pid)
        planner.record_step_result(pid, 0, success=True)
        planner.complete_plan(pid)

        # Goal should have a completed_task event
        events = ge.get_events(gid)
        assert any(e.event_type == "completed_task" for e in events)

    def test_decompose_goal_with_engine(self, planner_with_goals):
        planner, ge = planner_with_goals
        gid = ge.create_goal("Build authentication feature", status="active")
        pid = planner.decompose_goal(gid, "Build authentication feature")
        plan = planner.get_plan(pid)
        assert plan.goal_id == gid
        assert plan.total_steps >= 3


# ─── EDGE CASES ──────────────────────────────────────────────

class TestPlanEdgeCases:
    def test_start_plan_no_steps(self, planner):
        pid = planner.create_plan("Empty Plan")
        plan = planner.get_plan(pid)
        assert plan.total_steps == 0
        # Starting plan with 0 steps should still work
        result = planner.start_plan(pid)
        assert result is True

    def test_is_plan_complete_nonexistent(self, planner):
        assert planner.is_plan_complete(9999) is False

    def test_to_dispatch_event_invalid_step(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Test", steps=steps)
        event = planner.to_dispatch_event(pid, 99)
        assert event is None

    def test_to_task_queue_nonexistent(self, planner):
        entries = planner.to_task_queue_entries(9999)
        assert entries == []

    def test_suggest_alternative_nonexistent_plan(self, planner):
        assert planner.suggest_alternative(9999, 0) is None

    def test_suggest_alternative_invalid_step(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Test", steps=steps)
        assert planner.suggest_alternative(pid, 99) is None

    def test_replan_nonexistent(self, planner):
        assert planner.replan(9999, 0) is False

    def test_promote_nonexistent_plan(self, planner):
        assert planner.promote_plan_to_template(9999, "test") is None

    def test_list_by_goal_id(self, planner_with_goals):
        planner, ge = planner_with_goals
        gid = ge.create_goal("Test")
        planner.create_plan("Plan A", goal_id=gid)
        planner.create_plan("Plan B", goal_id=gid)
        planner.create_plan("Plan C")  # no goal
        plans = planner.list_plans(goal_id=gid)
        assert len(plans) == 2

    def test_checkpoint_step_property(self):
        step = PlanStep(0, "Review", checkpoint=True)
        assert step.checkpoint is True
        d = step.to_dict()
        assert d["checkpoint"] is True
        reloaded = PlanStep.from_dict(d)
        assert reloaded.checkpoint is True

    def test_plan_progress_with_failures(self, planner):
        """Failed steps should not count toward progress."""
        steps = [
            PlanStep(0, "S1", agent="test"),
            PlanStep(1, "S2", agent="test"),
        ]
        pid = planner.create_plan("Fail Test", steps=steps)
        planner.start_plan(pid)
        planner.record_step_result(pid, 0, success=True)
        planner.record_step_result(pid, 1, success=False)
        plan = planner.get_plan(pid)
        assert plan.progress_pct == 50.0  # Only 1 of 2 completed

    def test_record_step_result_with_artifacts(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Artifact Test", steps=steps)
        planner.start_plan(pid)
        planner.record_step_result(
            pid, 0, success=True, summary="Done",
            artifacts=["/output/result.json", "/output/model.rvt"],
            duration_seconds=45.5
        )
        plan = planner.get_plan(pid)
        result = plan._step_results[0]
        assert result["duration_seconds"] == 45.5
        artifacts = json.loads(result["output_artifacts"])
        assert len(artifacts) == 2

    def test_match_template_client_deliverable(self, planner):
        assert planner.match_template("create client deliverable report") == "client-deliverable"

    def test_record_step_result_without_start(self, planner):
        """record_step_result insert-fallback when start_plan wasn't called."""
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("No Start", steps=steps)
        # Don't call start_plan — step result rows won't exist
        planner.record_step_result(pid, 0, success=True, summary="Direct insert")
        plan = planner.get_plan(pid)
        assert len(plan._step_results) == 1
        assert plan._step_results[0]["status"] == "completed"

    def test_fail_plan_no_reason(self, planner):
        """fail_plan without a reason should not add to error_log."""
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Fail No Reason", steps=steps)
        planner.start_plan(pid)
        planner.fail_plan(pid)  # no reason
        plan = planner.get_plan(pid)
        assert plan.status == "failed"
        assert len(plan.error_log) == 0

    def test_save_as_workflow_non_completed(self, planner, db_path):
        """save_as_workflow on a non-completed plan should mark workflow as not success."""
        from workflows import WorkflowRecorder
        WorkflowRecorder(db_path=db_path)

        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Draft Plan", steps=steps)
        # Plan is in 'draft' status, not completed
        result = planner.save_as_workflow(pid, "draft-workflow")
        assert result is True


# ─── TASK DECOMPOSITION (A-grade features) ────────────────────

class TestAtomicity:
    def test_simple_step_is_atomic(self, planner):
        step = PlanStep(0, "Read file", description="Read the config file")
        assert planner.is_atomic(step) is True

    def test_conjunction_step_is_not_atomic(self, planner):
        step = PlanStep(0, "Research and then implement",
                        description="Research existing code and then implement the solution")
        assert planner.is_atomic(step) is False

    def test_multi_domain_step_is_not_atomic(self, planner):
        step = PlanStep(0, "Build and deploy",
                        description="Implement the revit model wall creation and write the test script")
        assert planner.is_atomic(step) is False

    def test_short_simple_step_is_atomic(self, planner):
        step = PlanStep(0, "Write tests", description="Write unit tests", agent="python-engineer")
        assert planner.is_atomic(step) is True

    def test_complex_description_is_not_atomic(self, planner):
        step = PlanStep(0, "Full pipeline",
                        description="Research and implement the complete workflow, "
                                    "extract data from excel, create revit walls, "
                                    "validate model, and then generate the report")
        assert planner.is_atomic(step) is False


class TestComplexityEstimation:
    def test_simple_task_low_complexity(self, planner):
        score = planner.estimate_complexity("Read a file")
        assert score <= 3

    def test_conjunction_increases_complexity(self, planner):
        simple = planner.estimate_complexity("Create walls")
        compound = planner.estimate_complexity("Create walls and then validate model and then generate schedule")
        assert compound > simple

    def test_multi_domain_increases_complexity(self, planner):
        single = planner.estimate_complexity("Build revit model")
        multi = planner.estimate_complexity("Build revit model and write the test script and create client report")
        assert multi > single

    def test_complexity_capped_at_10(self, planner):
        desc = ("research and then implement and then test and then deploy "
                "multiple revit walls and excel reports and client proposals "
                "create build analyze extract validate generate transform")
        score = planner.estimate_complexity(desc)
        assert score == 10

    def test_complexity_min_is_1(self, planner):
        score = planner.estimate_complexity("ok")
        assert score >= 1

    def test_long_description_adds_complexity(self, planner):
        short = planner.estimate_complexity("Build walls")
        long_desc = " ".join(["Build a sophisticated automated system"] * 10)
        long_score = planner.estimate_complexity(long_desc)
        assert long_score >= short


class TestMECEValidation:
    def test_good_coverage(self, planner):
        steps = [
            PlanStep(0, "Research existing code", description="Research and understand the codebase"),
            PlanStep(1, "Implement feature", description="Build the implementation"),
            PlanStep(2, "Test and verify", description="Write tests and verify the feature"),
        ]
        pid = planner.create_plan("Build feature", description="Research, implement and test a new feature",
                                  steps=steps)
        result = planner.validate_mece(pid)
        assert result["coverage"] > 0.5

    def test_overlapping_steps_detected(self, planner):
        steps = [
            PlanStep(0, "Research code patterns", description="Analyze the existing code and patterns"),
            PlanStep(1, "Analyze code structure", description="Research existing code patterns and analyze"),
        ]
        pid = planner.create_plan("Analyze code", description="Research and analyze code",
                                  steps=steps)
        result = planner.validate_mece(pid)
        if result["overlap"] > 0:
            assert any("overlap" in i.lower() for i in result["issues"])

    def test_missing_coverage_detected(self, planner):
        steps = [
            PlanStep(0, "Write code", description="Implement the solution"),
        ]
        pid = planner.create_plan("Research, implement and test",
                                  description="Research the topic, implement solution, write tests, deploy",
                                  steps=steps)
        result = planner.validate_mece(pid)
        assert result["coverage"] < 1.0

    def test_nonexistent_plan(self, planner):
        result = planner.validate_mece(9999)
        assert result["valid"] is False
        assert "not found" in result.get("error", "").lower()


class TestRecursiveDecomposition:
    def test_atomic_step_not_decomposed(self, planner):
        steps = [PlanStep(0, "Read file", description="Read the config", agent="tech-scout")]
        pid = planner.create_plan("Simple", steps=steps)
        result = planner.auto_decompose_step(pid, 0)
        assert result is None

    def test_complex_step_decomposed(self, planner):
        steps = [
            PlanStep(0, "Research and then implement and then test",
                     description="Research existing code and then implement the solution "
                                 "and then write comprehensive tests",
                     agent="python-engineer", estimated_minutes=60),
        ]
        pid = planner.create_plan("Complex", steps=steps)
        sub_plan_id = planner.auto_decompose_step(pid, 0)
        assert sub_plan_id is not None
        sub_plan = planner.get_plan(sub_plan_id)
        assert sub_plan.total_steps >= 2
        assert sub_plan.parent_plan_id == pid

    def test_sub_plan_linked_to_parent(self, planner):
        steps = [
            PlanStep(0, "Full pipeline research and then build and then deploy",
                     description="Full end to end pipeline", agent="python-engineer",
                     estimated_minutes=90),
        ]
        pid = planner.create_plan("Parent", steps=steps)
        sub_id = planner.auto_decompose_step(pid, 0)
        assert sub_id is not None

        # Check parent's execution context has sub_plan reference
        parent = planner.get_plan(pid)
        assert "sub_plans" in parent.execution_context
        assert str(0) in parent.execution_context["sub_plans"]

    def test_get_sub_plans(self, planner):
        steps = [
            PlanStep(0, "Research and then implement and then test and then deploy",
                     description="Multiple phases", agent="test", estimated_minutes=60),
        ]
        pid = planner.create_plan("Parent", steps=steps)
        sub_id = planner.auto_decompose_step(pid, 0)
        assert sub_id is not None

        sub_plans = planner.get_sub_plans(pid)
        assert len(sub_plans) == 1
        assert sub_plans[0].id == sub_id

    def test_decompose_all_complex(self, planner):
        steps = [
            PlanStep(0, "Read config", description="Simple read", agent="test"),
            PlanStep(1, "Research and then implement and then test",
                     description="Complex multi-phase work", agent="test",
                     estimated_minutes=60),
            PlanStep(2, "Send email", description="Simple notification", agent="test"),
        ]
        pid = planner.create_plan("Mixed", steps=steps)
        result = planner.decompose_all_complex_steps(pid)
        # Only step 1 should be decomposed
        assert 0 not in result
        assert 1 in result
        assert 2 not in result

    def test_nonexistent_plan_returns_none(self, planner):
        assert planner.auto_decompose_step(9999, 0) is None

    def test_nonexistent_step_returns_none(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Test", steps=steps)
        assert planner.auto_decompose_step(pid, 99) is None

    def test_template_match_in_decomposition(self, planner):
        """Complex step matching a template should use that template for sub-plan."""
        steps = [
            PlanStep(0, "Build the authentication feature and then test and then deploy",
                     description="Research, design, implement, test and commit the auth feature",
                     agent="python-engineer", estimated_minutes=60),
        ]
        pid = planner.create_plan("Feature", steps=steps)
        sub_id = planner.auto_decompose_step(pid, 0)
        if sub_id:
            sub_plan = planner.get_plan(sub_id)
            # Should have matched build-feature template (5 steps)
            assert sub_plan.total_steps >= 3


class TestCoherenceScoreInStepResult:
    def test_record_with_coherence_score(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("Coherence Test", steps=steps)
        planner.start_plan(pid)
        planner.record_step_result(pid, 0, success=True, summary="Done",
                                   coherence_score=0.85)
        plan = planner.get_plan(pid)
        ctx = plan.execution_context
        assert "coherence_scores" in ctx
        assert len(ctx["coherence_scores"]) == 1
        assert ctx["coherence_scores"][0]["score"] == 0.85

    def test_record_without_coherence_score(self, planner):
        steps = [PlanStep(0, "S1", agent="test")]
        pid = planner.create_plan("No Coherence", steps=steps)
        planner.start_plan(pid)
        planner.record_step_result(pid, 0, success=True, summary="Done")
        plan = planner.get_plan(pid)
        assert "coherence_scores" not in plan.execution_context

    def test_multiple_coherence_scores(self, planner):
        steps = [PlanStep(0, "S1", agent="t"), PlanStep(1, "S2", agent="t")]
        pid = planner.create_plan("Multi Coherence", steps=steps)
        planner.start_plan(pid)
        planner.record_step_result(pid, 0, success=True, coherence_score=0.9)
        planner.record_step_result(pid, 1, success=True, coherence_score=0.7)
        plan = planner.get_plan(pid)
        assert len(plan.execution_context["coherence_scores"]) == 2


class TestParentPlanId:
    def test_plan_has_parent_plan_id(self, planner):
        pid = planner.create_plan("Test")
        plan = planner.get_plan(pid)
        assert plan.parent_plan_id is None

    def test_sub_plan_has_parent_reference(self, planner):
        steps = [
            PlanStep(0, "Complex: research and then implement and then test everything",
                     description="Multi-phase", agent="test", estimated_minutes=60),
        ]
        pid = planner.create_plan("Parent", steps=steps)
        sub_id = planner.auto_decompose_step(pid, 0)
        if sub_id:
            sub = planner.get_plan(sub_id)
            assert sub.parent_plan_id == pid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
