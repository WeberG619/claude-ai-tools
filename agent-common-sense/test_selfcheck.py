"""Tests for Self-Check Hooks v1.0 — post-execution output validation."""

import json
import os
import sqlite3
import tempfile
import pytest
from selfcheck import SelfChecker, SelfCheckResult
from permissions import PermissionScope


# ─── FIXTURES ─────────────────────────────────────────────────

@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def checker(db_path):
    return SelfChecker(db_path=db_path)


@pytest.fixture
def checker_no_db():
    return SelfChecker(db_path="/nonexistent/path.db")


# ─── SAMPLE OUTPUTS ──────────────────────────────────────────

GOOD_WALL_OUTPUT = """
## Wall Extraction Results

Found 10 wall segments in the floor plan.

### Walls Detected:
- Wall A: 25'-0" exterior, bearing wall
- Wall B: 12'-6" interior partition
- Wall C: 30'-0" exterior wall

### Rooms:
- Living Room: 450 sq ft
- Kitchen: 200 sq ft
- Bedroom: 180 sq ft

Total walls: 10
Total rooms: 3
"""

SHORT_OUTPUT = "Done."

EMPTY_OUTPUT = ""

CONFUSED_OUTPUT = """
I'm not sure what you want me to do with this file.
I don't understand the format of the input.
Let me start over.
"""

REFUSING_OUTPUT = """
I cannot perform this action because the system is not configured.
I'm afraid I can't help with this task.
"""

APOLOGETIC_OUTPUT = """
I apologize, but I was unable to complete the extraction.
Unfortunately, I could not parse the floor plan correctly.
"""

OFF_TOPIC_OUTPUT = """
Here's a recipe for chocolate brownies:

Ingredients:
- 2 cups sugar
- 1 cup butter
- 4 eggs

Preheat oven to 350F and mix ingredients.
"""


# ─── SELF CHECK RESULT TESTS ─────────────────────────────────

class TestSelfCheckResult:
    def test_default_values(self):
        r = SelfCheckResult()
        assert r.passed is False
        assert r.score == 0.0
        assert r.retriable is False
        assert r.retry_feedback == ""

    def test_to_dict(self):
        r = SelfCheckResult(passed=True, score=0.85, failures=["test"])
        d = r.to_dict()
        assert d["passed"] is True
        assert d["score"] == 0.85
        assert d["failures"] == ["test"]

    def test_serialization(self):
        r = SelfCheckResult(passed=True, score=0.75, checks_run={"a": 0.8, "b": 0.7})
        d = r.to_dict()
        j = json.dumps(d)
        assert json.loads(j)["score"] == 0.75

    def test_retriable_range(self):
        """Score between RETRY_THRESHOLD and PASS_THRESHOLD should be retriable."""
        checker = SelfChecker(db_path="/nonexistent/path.db")
        result = checker.check(
            agent_output=SHORT_OUTPUT,
            task_description="Extract walls and rooms from PDF floor plan",
            agent_name="test",
        )
        # Short output typically scores in retriable or fail range
        assert result.score < checker.PASS_THRESHOLD

    def test_passed_result_not_retriable(self):
        checker = SelfChecker(db_path="/nonexistent/path.db")
        result = checker.check(
            agent_output=GOOD_WALL_OUTPUT,
            task_description="Extract walls and rooms from floor plan",
            agent_name="test",
        )
        if result.passed:
            assert result.retriable is False


# ─── TASK ADDRESSAL TESTS ────────────────────────────────────

class TestTaskAddressal:
    def test_on_topic_high_score(self, checker):
        score = checker._check_task_addressal(
            GOOD_WALL_OUTPUT, "Extract walls and rooms from floor plan"
        )
        assert score > 0.5

    def test_off_topic_low_score(self, checker):
        score = checker._check_task_addressal(
            OFF_TOPIC_OUTPUT, "Extract walls and rooms from floor plan"
        )
        assert score < 0.5

    def test_partial_overlap_medium(self, checker):
        score = checker._check_task_addressal(
            "Found some walls in the document. Processing continues.",
            "Extract walls, rooms, doors, and windows from floor plan"
        )
        # Some overlap (walls) but not full
        assert 0.0 < score < 1.0

    def test_empty_task_neutral(self, checker):
        score = checker._check_task_addressal(GOOD_WALL_OUTPUT, "")
        assert score == 0.7  # Neutral

    def test_empty_output_zero(self, checker):
        score = checker._check_task_addressal("", "Extract walls")
        assert score == 0.0

    def test_identical_text_high(self, checker):
        text = "Extract wall geometry from floor plan PDF"
        score = checker._check_task_addressal(text, text)
        assert score > 0.7


# ─── COMPLETENESS TESTS ─────────────────────────────────────

class TestCompleteness:
    def test_empty_fails(self, checker):
        score = checker._check_completeness("")
        assert score == 0.0

    def test_very_short_fails(self, checker):
        score = checker._check_completeness("ok")
        assert score < 0.2

    def test_short_low_score(self, checker):
        score = checker._check_completeness("Done. Task completed successfully.")
        assert score < 0.5

    def test_structured_high(self, checker):
        score = checker._check_completeness(GOOD_WALL_OUTPUT)
        assert score > 0.6  # Has headings, lists, multiple lines

    def test_adequate_passes(self, checker):
        text = "The analysis found 10 wall segments. " * 5
        score = checker._check_completeness(text)
        assert score >= 0.4


# ─── DRIFT SIGNAL TESTS ─────────────────────────────────────

class TestDriftSignals:
    def test_confusion_detected(self, checker):
        score = checker._check_drift_free(CONFUSED_OUTPUT)
        assert score < 0.7

    def test_refusal_detected(self, checker):
        score = checker._check_drift_free(REFUSING_OUTPUT)
        assert score < 0.7

    def test_apology_detected(self, checker):
        score = checker._check_drift_free(APOLOGETIC_OUTPUT)
        assert score < 0.7

    def test_clean_passes(self, checker):
        score = checker._check_drift_free(GOOD_WALL_OUTPUT)
        assert score == 1.0

    def test_uses_same_patterns_as_coherence(self):
        """Verify we're importing from coherence, not duplicating."""
        from coherence import CONFUSION_SIGNALS as coherence_signals
        from selfcheck import CONFUSION_SIGNALS as selfcheck_signals
        assert coherence_signals is selfcheck_signals


# ─── ARTIFACT PRESENCE TESTS ─────────────────────────────────

class TestArtifactPresence:
    def test_all_found(self, checker):
        score = checker._check_artifacts(
            GOOD_WALL_OUTPUT, ["wall", "room"]
        )
        assert score == 1.0

    def test_missing_flagged(self, checker):
        score = checker._check_artifacts(
            GOOD_WALL_OUTPUT, ["wall", "room", "elevator", "staircase"]
        )
        assert score < 1.0

    def test_none_expected_neutral(self, checker):
        score = checker._check_artifacts(GOOD_WALL_OUTPUT, None)
        assert score == 0.7

    def test_empty_list_neutral(self, checker):
        score = checker._check_artifacts(GOOD_WALL_OUTPUT, [])
        assert score == 0.7


# ─── FULL CHECK TESTS ────────────────────────────────────────

class TestFullCheck:
    def test_good_agent_passes(self, checker):
        result = checker.check(
            agent_output=GOOD_WALL_OUTPUT,
            task_description="Extract walls and rooms from floor plan",
            agent_name="floor-plan-processor",
            expected_artifacts=["wall", "room"],
        )
        assert result.passed is True
        assert result.score >= checker.PASS_THRESHOLD

    def test_bad_agent_retriable(self, checker):
        result = checker.check(
            agent_output="I found some walls but couldn't complete the analysis.",
            task_description="Extract walls and rooms from floor plan",
            agent_name="floor-plan-processor",
        )
        # Short-ish output with partial relevance — might be retriable or fail
        assert result.score < 1.0

    def test_terrible_agent_low_addressal(self, checker):
        result = checker.check(
            agent_output=OFF_TOPIC_OUTPUT,
            task_description="Build Revit walls from extracted geometry specification",
            agent_name="revit-builder",
        )
        # Task addressal should be 0 for off-topic output
        assert result.checks_run["task_addressal"] < 0.1
        assert "Output does not address the assigned task" in result.failures

    def test_works_without_db(self, checker_no_db):
        result = checker_no_db.check(
            agent_output=GOOD_WALL_OUTPUT,
            task_description="Extract walls",
        )
        assert result is not None
        assert isinstance(result.score, float)

    def test_scope_compliance_integrated(self, checker):
        scope = PermissionScope(
            write_access=False,
            execute_access=False,
        )
        result = checker.check(
            agent_output="I created the file and ran the bash command to process it.",
            task_description="Read the floor plan data",
            agent_name="tech-scout",
            permission_scope=scope,
        )
        # Should detect scope violations
        assert result.checks_run["scope_compliance"] < 0.5


# ─── RETRY FEEDBACK TESTS ────────────────────────────────────

class TestRetryFeedback:
    def test_feedback_contains_task(self, checker):
        result = SelfCheckResult(
            score=0.3,
            failures=["Output does not address the task"],
        )
        feedback = checker.build_retry_feedback(result, "Extract walls from PDF")
        assert "Extract walls from PDF" in feedback

    def test_feedback_contains_failures(self, checker):
        result = SelfCheckResult(
            score=0.3,
            failures=["Missing artifacts: wall, room"],
        )
        feedback = checker.build_retry_feedback(result, "Extract walls")
        assert "Missing artifacts" in feedback

    def test_feedback_contains_score(self, checker):
        result = SelfCheckResult(score=0.25, failures=["Too short"])
        feedback = checker.build_retry_feedback(result, "Do task")
        assert "0.25" in feedback


# ─── LOGGING TESTS ────────────────────────────────────────────

class TestLogging:
    def test_check_logged(self, checker, db_path):
        checker.check(
            agent_output=GOOD_WALL_OUTPUT,
            task_description="Extract walls",
            agent_name="test-agent",
        )
        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM selfcheck_log").fetchone()[0]
        conn.close()
        assert count == 1

    def test_stats_returned(self, checker, db_path):
        for i in range(3):
            checker.check(
                agent_output=GOOD_WALL_OUTPUT,
                task_description="Extract walls",
                agent_name="test-agent",
            )
        stats = checker.get_stats("test-agent")
        assert stats["total"] == 3

    def test_no_db_no_crash(self, checker_no_db):
        stats = checker_no_db.get_stats()
        assert stats == {"total": 0}


# ─── EDGE CASES ──────────────────────────────────────────────

class TestEdgeCases:
    def test_none_output(self, checker):
        result = checker.check(
            agent_output=None,
            task_description="Some task",
        )
        assert result.passed is False
        assert result.score < 0.3

    def test_none_task(self, checker):
        result = checker.check(
            agent_output=GOOD_WALL_OUTPUT,
            task_description=None,
        )
        # No task = can't fully evaluate, but output itself is good
        assert result is not None

    def test_very_long_output(self, checker):
        long_output = GOOD_WALL_OUTPUT * 100
        result = checker.check(
            agent_output=long_output,
            task_description="Extract walls",
        )
        assert result is not None
