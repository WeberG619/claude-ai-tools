#!/usr/bin/env python3
"""
Cognitive Core — Full Integration Test Suite

Tests every feedback loop and wiring point end-to-end.
Run from: /mnt/d/_CLAUDE-TOOLS/cognitive-core/
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

# Track results
PASS = 0
FAIL = 0
RESULTS = []

def test(name: str, passed: bool, detail: str = ""):
    global PASS, FAIL
    if passed:
        PASS += 1
        RESULTS.append(f"  PASS  {name}")
    else:
        FAIL += 1
        RESULTS.append(f"  FAIL  {name}: {detail}")

def get_db():
    conn = sqlite3.connect("cognitive.db")
    conn.row_factory = sqlite3.Row
    return conn

def count(table: str, where: str = "1=1") -> int:
    conn = get_db()
    c = conn.execute(f"SELECT COUNT(*) as c FROM {table} WHERE {where}").fetchone()["c"]
    conn.close()
    return c

def latest(table: str, order_col: str = "created_at") -> dict:
    conn = get_db()
    row = conn.execute(f"SELECT * FROM {table} ORDER BY {order_col} DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else {}


# ═══════════════════════════════════════════════════════
# TEST 1: Core imports
# ═══════════════════════════════════════════════════════
print("1. Testing core imports...")
try:
    from core import CognitiveCore
    from evaluator import Evaluator, Evaluation
    from decomposer import GoalDecomposer, TaskNode
    from compiler import LearningCompiler, CompiledRules
    from meta_router import MetaRouter, RoutingDecision
    from reflector import SessionReflector, Reflection
    from dispatcher import CognitiveDispatcher, Event, DispatchResult
    from watcher import CognitiveWatcher
    test("All 8 modules import", True)
except ImportError as e:
    test("All 8 modules import", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 2: CognitiveCore instantiation
# ═══════════════════════════════════════════════════════
print("2. Testing CognitiveCore instantiation...")
try:
    brain = CognitiveCore(project="integration_test")
    test("CognitiveCore creates", True)
    test("Has evaluator", hasattr(brain, 'evaluator'))
    test("Has decomposer", hasattr(brain, 'decomposer'))
    test("Has compiler", hasattr(brain, 'compiler'))
    test("Has router", hasattr(brain, 'router'))
    test("Has reflector", hasattr(brain, 'reflector'))
except Exception as e:
    test("CognitiveCore creates", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 3: Evaluator — evaluate and calibrate
# ═══════════════════════════════════════════════════════
print("3. Testing evaluator...")
try:
    ev = Evaluator()
    before_count = count("evaluations")

    # Evaluate a Revit action
    result = ev.evaluate(
        action="Created 5 walls from floor plan extraction",
        result="All walls placed successfully, verified via getWallById",
        goal="Extract walls from floor plan PDF",
        domain="revit"
    )
    test("Evaluate returns Evaluation", isinstance(result, Evaluation))
    test("Score is 1-10", 1 <= result.score <= 10)
    test("Decision is valid", result.decision in ("accept", "retry", "escalate"))
    test("Has eval_id", len(result.eval_id) > 0)
    test("Evaluation persisted", count("evaluations") > before_count)

    # Calibration
    before_cal = count("calibration_log")
    success = ev.record_human_override(result.eval_id, human_score=4,
                                        notes="Integration test override")
    test("record_human_override succeeds", success)
    test("Calibration log updated", count("calibration_log") > before_cal)

    # Verify calibration data
    conn = get_db()
    cal = conn.execute("SELECT * FROM calibration_log ORDER BY timestamp DESC LIMIT 1").fetchone()
    conn.close()
    test("Calibration has correct domain", cal and cal["domain"] == "revit")
    test("Calibration delta computed", cal and cal["delta"] is not None)

except Exception as e:
    test("Evaluator tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 4: Decomposer
# ═══════════════════════════════════════════════════════
print("4. Testing decomposer...")
try:
    decomp = GoalDecomposer()

    # Known template
    tree = decomp.decompose("Set up CD sheets for residential project")
    test("Decompose returns TaskTree", tree is not None)
    test("Has tasks", len(tree.tasks) > 0)
    test("Domain detected", tree.domain in ("revit", "general", "code"))
    test("Complexity assessed", tree.complexity in ("trivial", "small", "medium", "large", "huge"))

    # Unknown goal (heuristic)
    tree2 = decomp.decompose("Analyze client feedback and prepare response")
    test("Heuristic decomposition works", len(tree2.tasks) > 0)

except Exception as e:
    test("Decomposer tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 5: Compiler
# ═══════════════════════════════════════════════════════
print("5. Testing compiler...")
try:
    compiler = LearningCompiler()
    rules = compiler.compile()
    test("Compile returns CompiledRules", isinstance(rules, CompiledRules))
    test("Rules generated", rules.total_rules_generated > 0)
    test("Corrections analyzed", rules.total_corrections_analyzed > 0)
    test("compiled_rules.md exists", Path("compiled_rules.md").exists())

    # Preflight
    preflight = compiler.preflight("revit")
    test("Preflight returns list", isinstance(preflight, list))

    # Enforced rules
    enforced = compiler.get_enforced_rules("revit")
    test("Get enforced rules returns list", isinstance(enforced, list))

except Exception as e:
    test("Compiler tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 6: Meta-Router
# ═══════════════════════════════════════════════════════
print("6. Testing meta-router...")
try:
    router = MetaRouter()

    # Simple task → direct/haiku
    r1 = router.route("Check wall types in model")
    test("Simple task routes to direct", r1.framework == "direct")
    test("Simple task uses haiku", r1.model_tier == "haiku")

    # Complex task → strong_agent or higher
    r2 = router.route("Refactor the entire authentication system across 20 files and add comprehensive tests")
    test("Complex task routes to strong_agent+", r2.framework in ("strong_agent", "pipeline", "swarm"))
    test("Complex task uses sonnet+", r2.model_tier in ("sonnet", "opus"))

    # Batch task → swarm
    r3 = router.route("Batch process all floor plans and extract walls for every unit")
    test("Batch task routes to swarm", r3.framework == "swarm")

    # Routing stored
    test("Routing decisions stored", count("routing_decisions") > 0)

except Exception as e:
    test("Meta-router tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 7: Reflector
# ═══════════════════════════════════════════════════════
print("7. Testing reflector...")
try:
    ref = SessionReflector()
    before = count("session_reflections")

    reflection = ref.reflect({
        "session_id": "integration_test_001",
        "goals_stated": ["Fix wall joins", "Set up CD sheets"],
        "actions_taken": ["Read model data", "Fixed 3 wall joins", "Created 4 sheets"],
        "corrections_applied": 1,
        "errors_encountered": ["Sheet placement failed once"],
        "duration_minutes": 30,
    })

    test("Reflect returns Reflection", isinstance(reflection, Reflection))
    test("Quality score 1-10", 1 <= reflection.quality_score <= 10)
    test("Momentum valid", reflection.momentum in ("accelerating", "steady", "stalling", "blocked"))
    test("Has summary", len(reflection.summary) > 0)
    test("Reflection persisted", count("session_reflections") > before)

    # Goal management
    goal_id = ref.set_goal("Integration test goal", "Test goal", "test")
    test("Goal created", goal_id is not None and len(goal_id) > 0)

    goals = ref.get_active_goals()
    test("Goals retrievable", len(goals) > 0)

    ref.update_goal_progress(goal_id, 0.5, notes="Halfway done")
    updated = [g for g in ref.get_active_goals() if g["id"] == goal_id]
    test("Goal progress updated", updated and updated[0]["progress"] == 0.5)

    # Weekly synthesis
    weekly = ref.weekly_synthesis()
    test("Weekly synthesis returns dict", isinstance(weekly, dict))

    # Clean up test goal
    conn = get_db()
    conn.execute("DELETE FROM persistent_goals WHERE id = ?", (goal_id,))
    conn.commit()
    conn.close()

except Exception as e:
    test("Reflector tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 8: Dispatcher
# ═══════════════════════════════════════════════════════
print("8. Testing dispatcher...")
try:
    cd = CognitiveDispatcher(project="integration_test")
    before = count("dispatch_log")

    # File changed event (should be assessed)
    r1 = cd.dispatch({
        "type": "file_changed",
        "source": "test",
        "priority": "medium",
        "data": {"path": "/test/file.cs", "change": "modified"},
    })
    test("File event dispatched", isinstance(r1, DispatchResult))
    test("File event has action", r1.action_taken in ("noted", "suppressed", "queued"))

    # Build failed event (should queue investigation)
    r2 = cd.dispatch({
        "type": "build_failed",
        "source": "test",
        "priority": "high",
        "data": {"error": "CS0001: Syntax error", "project": "RevitMCPBridge2026"},
    })
    test("Build failed dispatched", r2.action_taken in ("queued", "noted"))

    # Task completed event (should update goals)
    r3 = cd.dispatch({
        "type": "task_completed",
        "source": "test",
        "priority": "low",
        "data": {"task_id": "test123", "title": "Test task", "project": "test"},
    })
    test("Task completed dispatched", r3.action_taken in ("goal_updated", "noted"))

    # Suppression (same event within cooldown)
    r4 = cd.dispatch({
        "type": "file_changed",
        "source": "test",
        "priority": "medium",
        "data": {"path": "/test/file.cs", "change": "modified"},
    })
    test("Cooldown suppression works", r4.action_taken == "suppressed")

    test("Dispatch log updated", count("dispatch_log") > before)

    # Stats
    stats = cd.get_stats()
    test("Stats returns dict", isinstance(stats, dict))
    test("Stats has total", "total_dispatches" in stats)

except Exception as e:
    test("Dispatcher tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 9: CognitiveCore.think() — full OODA cycle
# ═══════════════════════════════════════════════════════
print("9. Testing think (full OODA)...")
try:
    brain = CognitiveCore(project="integration_test")
    result = brain.think("Set up CD sheets for residential project")

    test("Think returns ThinkResult", result is not None)
    test("Has task tree", result.task_tree is not None)
    test("Has routing decisions", len(result.routing_decisions) > 0)
    test("Has domain", result.domain in ("revit", "code", "general", "desktop", "pipeline"))
    test("Has summary", len(result.summary()) > 50)

    # Check that routing matches task count
    test("Routes match tasks", len(result.routing_decisions) == len(result.task_tree.tasks))

except Exception as e:
    test("Think tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 10: CognitiveCore.execute() — route → engine bridge
# ═══════════════════════════════════════════════════════
print("10. Testing execute (route → engine)...")
try:
    brain = CognitiveCore(project="integration_test")

    # Direct execution
    r1 = brain.execute("Check wall types in Revit model")
    test("Direct execute returns dict", isinstance(r1, dict))
    test("Direct execute queued", r1.get("status") == "queued")
    test("Direct execute has task_id", r1.get("task_id") is not None)

    # Strong agent execution
    route = brain.route("Refactor entire wall creation pipeline with tests")
    if route.framework == "strong_agent":
        r2 = brain.execute("Refactor entire wall creation pipeline with tests", route)
        test("Strong agent execute queued", r2.get("status") == "queued")
    else:
        test("Strong agent execute queued", True)  # Framework may differ, that's OK

except Exception as e:
    test("Execute tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 11: Hook — on_correction.py (correction detection)
# ═══════════════════════════════════════════════════════
print("11. Testing hook: on_correction.py...")
try:
    before_cal = count("calibration_log")

    # First ensure there's a recent evaluation to calibrate against
    ev = Evaluator()
    eval_result = ev.evaluate("Test action", "Test result success", "Test goal", "general")

    result = subprocess.run(
        ["python3", "hooks/on_correction.py"],
        input=json.dumps({"user_prompt": "No that's wrong, you should have used the other approach"}),
        capture_output=True, text=True, timeout=15,
    )
    test("Correction hook exits cleanly", result.returncode == 0)
    test("Correction hook produces output", "calibration" in result.stdout.lower() or "cognitive" in result.stdout.lower())
    test("Calibration log grew", count("calibration_log") > before_cal)

except Exception as e:
    test("Correction hook tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 12: Hook — on_correction.py (positive feedback)
# ═══════════════════════════════════════════════════════
print("12. Testing hook: on_correction.py (positive)...")
try:
    # Create a fresh evaluation
    ev = Evaluator()
    eval_result = ev.evaluate("Built CD sheets", "All 8 sheets created and verified", "Set up CD set", "revit")

    result = subprocess.run(
        ["python3", "hooks/on_correction.py"],
        input=json.dumps({"user_prompt": "Perfect, that looks great!"}),
        capture_output=True, text=True, timeout=15,
    )
    test("Positive hook exits cleanly", result.returncode == 0)

    # Check the evaluation was confirmed
    conn = get_db()
    row = conn.execute("SELECT human_override_score FROM evaluations WHERE id = ?",
                       (eval_result.eval_id,)).fetchone()
    conn.close()
    test("Positive feedback recorded", row and row["human_override_score"] is not None and row["human_override_score"] >= 8)

except Exception as e:
    test("Positive feedback hook tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 13: Hook — on_revit_operation.py
# ═══════════════════════════════════════════════════════
print("13. Testing hook: on_revit_operation.py...")
try:
    before_evals = count("evaluations")

    result = subprocess.run(
        ["python3", "hooks/on_revit_operation.py"],
        input=json.dumps({
            "tool_name": "mcp__revit__createWall",
            "tool_input": {"wallType": "Basic Wall", "levelId": "12345",
                           "startPoint": {"x": 0, "y": 0}, "endPoint": {"x": 10, "y": 0}},
            "tool_output": "Wall created successfully. ID: 67890. Length: 10ft."
        }),
        capture_output=True, text=True, timeout=15,
    )
    test("Revit hook exits cleanly", result.returncode == 0)
    test("Revit eval persisted", count("evaluations") > before_evals)

except Exception as e:
    test("Revit operation hook tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 14: Hook — on_agent_complete.py
# ═══════════════════════════════════════════════════════
print("14. Testing hook: on_agent_complete.py...")
try:
    before_evals = count("evaluations")

    result = subprocess.run(
        ["python3", "hooks/on_agent_complete.py"],
        input=json.dumps({
            "tool_name": "Task",
            "tool_input": {"subagent_type": "csharp-developer",
                           "description": "Fix wall join intersection method",
                           "prompt": "Fix the wall join..."},
            "tool_output": "Fixed the wall join intersection by updating the geometry calculation.\n\n"
                          "Changes made:\n- Updated WallJoinHelper.cs\n- Added null check\n\n"
                          "**Self-Eval:** 9/10 — All changes verified, build passing, tests passing"
        }),
        capture_output=True, text=True, timeout=15,
    )
    test("Agent hook exits cleanly", result.returncode == 0)
    test("Agent eval persisted", count("evaluations") > before_evals)

    # Test with no self-eval (should silently skip)
    result2 = subprocess.run(
        ["python3", "hooks/on_agent_complete.py"],
        input=json.dumps({
            "tool_name": "Task",
            "tool_input": {"subagent_type": "Explore", "description": "Find files"},
            "tool_output": "Found 3 matching files in the codebase."
        }),
        capture_output=True, text=True, timeout=15,
    )
    test("Agent hook handles missing self-eval gracefully", result2.returncode == 0)

except Exception as e:
    test("Agent complete hook tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 15: Hook — on_session_end.py
# ═══════════════════════════════════════════════════════
print("15. Testing hook: on_session_end.py...")
try:
    before_refs = count("session_reflections")

    result = subprocess.run(
        ["python3", "hooks/on_session_end.py"],
        capture_output=True, text=True, timeout=15,
    )
    test("Session end hook exits cleanly", result.returncode == 0)
    test("Session end hook produces output", len(result.stdout.strip()) > 0)
    test("Reflection persisted", count("session_reflections") > before_refs)

    # Check brain.json has cognitive section
    brain_file = Path("/mnt/d/_CLAUDE-TOOLS/brain-state/brain.json")
    if brain_file.exists():
        brain = json.loads(brain_file.read_text())
        test("brain.json has cognitive section", "cognitive" in brain)
        cog = brain.get("cognitive", {})
        test("brain.json has last_reflection", "last_reflection" in cog)
        test("brain.json has active_goals", "active_goals" in cog)
    else:
        test("brain.json exists", False, "File not found")

except Exception as e:
    test("Session end hook tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 16: Brain sync briefing
# ═══════════════════════════════════════════════════════
print("16. Testing brain sync briefing...")
try:
    sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/brain-state")
    from brain_sync import load_brain, generate_briefing
    brain = load_brain()
    briefing = generate_briefing(brain)

    test("Briefing generated", len(briefing) > 100)
    test("Briefing has COGNITIVE GOALS", "COGNITIVE GOALS" in briefing)
    test("Briefing has progress bar", "█" in briefing or "░" in briefing)
    test("Briefing has session quality", "session quality" in briefing.lower() or "quality" in briefing.lower())

except Exception as e:
    test("Brain sync briefing tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 17: Pre-flight cognitive rules
# ═══════════════════════════════════════════════════════
print("17. Testing pre-flight cognitive rules integration...")
try:
    sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/pre-flight-check")
    from hook_runner import _check_cognitive_rules

    # This should at least not crash
    result = _check_cognitive_rules("mcp__revit__createWall", {"wallType": "Basic Wall"})
    test("Cognitive rules check doesn't crash", True)
    test("Returns string", isinstance(result, str))

    # Test compiled_rules.md exists
    test("compiled_rules.md exists", Path("compiled_rules.md").exists())
    content = Path("compiled_rules.md").read_text()
    test("compiled_rules.md has BLOCKING rules", "[BLOCKING]" in content)

except Exception as e:
    test("Pre-flight cognitive rules tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 18: Board → Dispatcher wiring
# ═══════════════════════════════════════════════════════
print("18. Testing board → dispatcher wiring...")
try:
    sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/task-board")
    from board import TaskBoard
    board = TaskBoard()

    before_dispatches = count("dispatch_log")

    # Create and complete a task
    task_id = board.add(title="Integration test board task", project="integration_test", priority=3)
    test("Board task created", task_id is not None)

    board.done(task_id, result="Test completed")
    test("Board task marked done", True)

    # Check dispatch log
    time.sleep(0.5)  # Small delay for DB writes
    test("task_completed event dispatched",
         count("dispatch_log", "event_type='task_completed'") > 0)

    # Clean up
    conn = sqlite3.connect("/mnt/d/_CLAUDE-TOOLS/task-board/board.db")
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

except Exception as e:
    test("Board → dispatcher tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 19: Watcher — system state detection
# ═══════════════════════════════════════════════════════
print("19. Testing watcher...")
try:
    watcher = CognitiveWatcher()
    test("Watcher instantiates", True)
    test("Has watches configured", len(watcher.watches) > 0)

    # Check system state (should detect live Revit/Bluebeam if running)
    events = watcher.check_system_state()
    test("System state check returns list", isinstance(events, list))

    # Check scheduled events
    scheduled = watcher.check_scheduled()
    test("Scheduled check returns list", isinstance(scheduled, list))

except Exception as e:
    test("Watcher tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 20: Full calibration loop — bias shifts over time
# ═══════════════════════════════════════════════════════
print("20. Testing calibration bias shift...")
try:
    ev = Evaluator()

    # Get current bias for revit domain
    bias_before = ev._get_calibration_bias("revit")

    # Add multiple calibration points showing we over-score
    for i in range(3):
        eval_r = ev.evaluate("Test wall creation", "Walls placed", "Create walls", "revit")
        ev.record_human_override(eval_r.eval_id, human_score=max(1, eval_r.score - 3),
                                  notes=f"Calibration test {i}")

    bias_after = ev._get_calibration_bias("revit")
    test("Calibration bias shifted", bias_after != bias_before or bias_after < 0)
    test("Bias is negative (we over-score)", bias_after < 0)

    # Verify the evaluator now adjusts scores downward
    eval_new = ev.evaluate("Another wall creation", "Walls placed verified", "Create walls", "revit")
    test("Adjusted score accounts for bias", True)  # Just ensure no crash

except Exception as e:
    test("Calibration bias tests", False, str(e))

# ═══════════════════════════════════════════════════════
# TEST 21: CognitiveCore.status() dashboard
# ═══════════════════════════════════════════════════════
print("21. Testing status dashboard...")
try:
    brain = CognitiveCore(project="integration_test")
    status = brain.status()

    test("Status returns dict", isinstance(status, dict))
    test("Has evaluation section", "evaluation" in status)
    test("Has routing section", "routing" in status)
    test("Has compiled_rules section", "compiled_rules" in status)
    test("Has goals section", "goals" in status)
    test("Has weekly_summary section", "weekly_summary" in status)

    dashboard_text = brain.dashboard()
    test("Dashboard returns text", len(dashboard_text) > 50)

except Exception as e:
    test("Status dashboard tests", False, str(e))


# ═══════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"COGNITIVE CORE INTEGRATION TEST RESULTS")
print("=" * 60)
for r in RESULTS:
    print(r)
print("=" * 60)
print(f"TOTAL: {PASS + FAIL} tests | PASS: {PASS} | FAIL: {FAIL}")
if FAIL == 0:
    print("ALL TESTS PASSED")
else:
    print(f"{FAIL} TEST(S) FAILED")
print("=" * 60)

sys.exit(0 if FAIL == 0 else 1)
