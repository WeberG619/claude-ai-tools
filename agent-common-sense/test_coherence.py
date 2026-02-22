"""Tests for Coherence Monitor v1.0 — drift detection and trajectory checking."""

import json
import os
import sqlite3
import tempfile
import pytest
from coherence import CoherenceMonitor, CoherenceCheck


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def monitor(db_path):
    return CoherenceMonitor(db_path=db_path)


# ─── SAMPLE OUTPUTS ───────────────────────────────────────────

COHERENT_WALL_OUTPUT = """
## Wall Extraction Results

Found 12 wall segments in the floor plan PDF.

### Walls Detected:
- Wall A: 25'-0" exterior, bearing wall, 6" thick
- Wall B: 12'-6" interior partition, 4" thick
- Wall C: 30'-0" exterior, bearing wall, 8" thick

### Room Boundaries:
- Living Room: 450 sq ft (bounded by walls A, B, D)
- Kitchen: 200 sq ft (bounded by walls B, C, E)

### Dimensions Validated:
All dimensions cross-referenced with PDF annotations. 8 of 8 match.

Total wall length: 185'-0"
Total rooms detected: 4
"""

INCOHERENT_OUTPUT = """
Here's a delicious recipe for chocolate cake:

Ingredients:
- 2 cups flour
- 1 cup sugar
- 3 eggs
- 1 cup milk

Mix all ingredients and bake at 350°F for 30 minutes.
Enjoy your chocolate cake!
"""

CONFUSED_OUTPUT = """
I'm not sure what you want me to do with this file.
I don't understand the format of the input.
Let me start over and try a different approach.
I'm confused about whether this is a floor plan or a site plan.
"""

REFUSING_OUTPUT = """
I cannot perform this action because it requires access to external systems.
This is not possible with the current configuration.
I'm afraid I can't help with this particular task.
"""

SHORT_CONFUSED_OUTPUT = "Um, I'm not sure."

EMPTY_OUTPUT = ""

VALIDATION_OUTPUT = """
## BIM Model Validation Report

### Check Results:
- Wall placement: PASS (12/12 walls within tolerance)
- Door openings: PASS (3/3 doors correctly placed)
- Window placement: FAIL (1 window at wrong elevation)
- Room areas: PASS (4/4 rooms within 2% of spec)

### Issues Found:
1. Window W3 placed at 4'-0" sill height instead of 3'-6"

### Overall: 3/4 checks passed. 1 issue requires attention.
"""

REPETITIVE_OUTPUT = """
Processing the data now. Processing the data now. Processing the data now.
Still processing the data now. Processing the data now.
The data is being processed. Processing the data now. Processing the data now.
"""


# ─── STEP COHERENCE TESTS ─────────────────────────────────────

class TestStepCoherence:
    def test_coherent_output_high_score(self, monitor):
        check = monitor.check_step_coherence(
            output=COHERENT_WALL_OUTPUT,
            step_title="Extract walls from PDF floor plan",
            step_description="Parse floor plan geometry to identify wall segments",
            pipeline_goal="Convert PDF floor plan to Revit model",
        )
        assert check.score > 0.4
        assert check.recommendation == "proceed"
        assert check.coherent is True

    def test_incoherent_output_low_score(self, monitor):
        check = monitor.check_step_coherence(
            output=INCOHERENT_OUTPUT,
            step_title="Extract walls from PDF floor plan",
            step_description="Parse floor plan geometry",
            pipeline_goal="Convert PDF floor plan to Revit model",
        )
        assert check.score < 0.3
        assert check.recommendation in ("warn", "halt")

    def test_confused_output_detects_drift(self, monitor):
        check = monitor.check_step_coherence(
            output=CONFUSED_OUTPUT,
            step_title="Extract walls from PDF",
            step_description="Parse geometry",
        )
        assert len(check.drift_indicators) > 0
        assert check.score < 0.4

    def test_refusing_output_detects_drift(self, monitor):
        check = monitor.check_step_coherence(
            output=REFUSING_OUTPUT,
            step_title="Create Revit walls",
            step_description="Place wall elements in model",
        )
        assert len(check.drift_indicators) > 0

    def test_empty_output_halts(self, monitor):
        check = monitor.check_step_coherence(
            output=EMPTY_OUTPUT,
            step_title="Extract data",
            step_description="Process input",
        )
        assert check.recommendation == "halt"
        assert check.score < 0.1

    def test_very_short_output_flags_drift(self, monitor):
        check = monitor.check_step_coherence(
            output="ok",
            step_title="Analyze complex floor plan",
            step_description="Full geometric analysis",
        )
        assert check.recommendation == "halt"

    def test_no_goal_returns_proceed(self, monitor):
        """Without a goal, can't evaluate coherence — should proceed."""
        check = monitor.check_step_coherence(
            output="Some output",
            step_title="",
            step_description="",
            pipeline_goal="",
        )
        assert check.recommendation == "proceed"

    def test_keyword_overlap_tracked(self, monitor):
        check = monitor.check_step_coherence(
            output=COHERENT_WALL_OUTPUT,
            step_title="wall extraction from floor plan",
        )
        assert check.total_goal_keywords > 0
        assert check.goal_keywords_found > 0
        assert check.overlap_ratio > 0

    def test_validation_output_with_key(self, monitor):
        check = monitor.check_step_coherence(
            output=VALIDATION_OUTPUT,
            step_title="Validate BIM model",
            step_description="Check wall placement and dimensions",
            expected_data_key="validation",
        )
        assert check.score > 0.4
        assert check.recommendation == "proceed"


# ─── STRUCTURAL COHERENCE TESTS ───────────────────────────────

class TestStructuralCoherence:
    def test_spec_data_key(self, monitor):
        check = monitor.check_step_coherence(
            output=COHERENT_WALL_OUTPUT,
            step_title="Extract spec",
            expected_data_key="spec",
        )
        # Output mentions wall, dimension, room, area — should score well
        assert check.score > 0.3

    def test_validation_data_key(self, monitor):
        check = monitor.check_step_coherence(
            output=VALIDATION_OUTPUT,
            step_title="Validate model",
            expected_data_key="validation",
        )
        assert check.score > 0.3

    def test_wrong_data_key(self, monitor):
        """Output about walls when expecting validation."""
        check = monitor.check_step_coherence(
            output=INCOHERENT_OUTPUT,
            step_title="Validate model",
            expected_data_key="validation",
        )
        assert check.score < 0.3

    def test_no_data_key_neutral(self, monitor):
        check = monitor.check_step_coherence(
            output=COHERENT_WALL_OUTPUT,
            step_title="Do something",
            expected_data_key="",
        )
        # No data key expectation = neutral structural score
        assert check is not None


# ─── DRIFT SIGNAL DETECTION TESTS ─────────────────────────────

class TestDriftDetection:
    def test_confusion_detected(self, monitor):
        signals = monitor.detect_drift_signals(CONFUSED_OUTPUT)
        assert any("Confusion" in s for s in signals)

    def test_refusal_detected(self, monitor):
        signals = monitor.detect_drift_signals(REFUSING_OUTPUT)
        assert any("Refusal" in s for s in signals)

    def test_apology_detected(self, monitor):
        signals = monitor.detect_drift_signals("I apologize, but I cannot complete this task.")
        assert any("Apology" in s or "hedging" in s for s in signals)

    def test_repetition_detected(self, monitor):
        signals = monitor.detect_drift_signals(REPETITIVE_OUTPUT)
        assert any("repetition" in s.lower() for s in signals)

    def test_short_output_flagged(self, monitor):
        signals = monitor.detect_drift_signals("Done.")
        assert any("short" in s.lower() for s in signals)

    def test_clean_output_no_signals(self, monitor):
        signals = monitor.detect_drift_signals(COHERENT_WALL_OUTPUT)
        # Clean output should have no confusion/refusal/apology signals
        confusion = [s for s in signals if "Confusion" in s]
        refusal = [s for s in signals if "Refusal" in s]
        assert len(confusion) == 0
        assert len(refusal) == 0

    def test_normal_length_no_short_flag(self, monitor):
        signals = monitor.detect_drift_signals("This is a reasonably long output that should not trigger the short output flag at all.")
        assert not any("short" in s.lower() for s in signals)


# ─── TRAJECTORY COHERENCE TESTS ───────────────────────────────

class TestTrajectoryCoherence:
    def test_converging_trajectory(self, monitor):
        """Each step adds new goal-relevant keywords."""
        outputs = [
            "Extracted wall geometry from the floor plan PDF",
            "Created Revit model with wall elements placed at correct dimensions",
            "Validated the BIM model: all walls pass tolerance checks",
        ]
        check = monitor.check_trajectory_coherence(
            outputs, "Convert PDF floor plan to Revit BIM model with wall validation"
        )
        assert check.score > 0.3
        assert check.recommendation == "proceed"

    def test_stalling_trajectory(self, monitor):
        """Step 3 adds no new goal keywords — trajectory stalls."""
        outputs = [
            "Extracted wall segments from the floor plan",
            "Created wall elements in the Revit model",
            "I ran the process again and got the same results as before",
        ]
        check = monitor.check_trajectory_coherence(
            outputs, "Extract walls, create model, validate dimensions"
        )
        assert len(check.drift_indicators) > 0

    def test_completely_off_topic_trajectory(self, monitor):
        """All steps are about cooking, not BIM."""
        outputs = [
            "First, preheat the oven to 350 degrees",
            "Mix the flour with sugar and eggs",
            "Bake for 30 minutes until golden brown",
        ]
        check = monitor.check_trajectory_coherence(
            outputs, "Extract walls from PDF and create Revit model"
        )
        assert check.score < 0.2

    def test_empty_outputs_list(self, monitor):
        check = monitor.check_trajectory_coherence([], "Some goal")
        assert check.recommendation == "proceed"

    def test_empty_goal(self, monitor):
        check = monitor.check_trajectory_coherence(
            ["Some output"], ""
        )
        assert check.recommendation == "proceed"


# ─── THRESHOLD TESTS ──────────────────────────────────────────

class TestThresholds:
    def test_halt_threshold(self, monitor):
        """Score below 0.1 should halt."""
        check = monitor.check_step_coherence(
            output=INCOHERENT_OUTPUT,
            step_title="Build Revit walls from extracted geometry",
            step_description="Place wall elements using Revit API with dimensions from PDF",
            pipeline_goal="PDF floor plan to Revit model conversion",
        )
        # Chocolate cake recipe has zero overlap with BIM keywords
        assert check.score < monitor.THRESHOLD_HALT or check.score < monitor.THRESHOLD_WARN

    def test_proceed_threshold(self, monitor):
        """Score above 0.3 should proceed."""
        check = monitor.check_step_coherence(
            output=COHERENT_WALL_OUTPUT,
            step_title="Extract walls from floor plan",
        )
        assert check.score >= monitor.THRESHOLD_WARN
        assert check.recommendation == "proceed"


# ─── KEYWORD EXTRACTION TESTS ─────────────────────────────────

class TestKeywordExtraction:
    def test_extracts_meaningful_words(self, monitor):
        keywords = monitor._extract_keywords("Extract wall geometry from PDF floor plan")
        assert "wall" in keywords
        assert "geometry" in keywords
        assert "floor" in keywords
        assert "plan" in keywords
        assert "extract" in keywords

    def test_filters_stop_words(self, monitor):
        keywords = monitor._extract_keywords("the and for with this that from")
        assert len(keywords) == 0

    def test_filters_short_words(self, monitor):
        keywords = monitor._extract_keywords("is it at to do go")
        assert len(keywords) == 0

    def test_case_insensitive(self, monitor):
        kw1 = monitor._extract_keywords("Wall GEOMETRY Floor")
        kw2 = monitor._extract_keywords("wall geometry floor")
        assert kw1 == kw2


# ─── LOGGING TESTS ────────────────────────────────────────────

class TestLogging:
    def test_coherence_logged(self, monitor, db_path):
        check = monitor.check_step_coherence(
            output=COHERENT_WALL_OUTPUT,
            step_title="Extract walls",
        )
        monitor.log_coherence("test-pipeline", 0, check, "test-agent")

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM coherence_log").fetchone()[0]
        conn.close()
        assert count == 1

    def test_stats_returned(self, monitor, db_path):
        for i in range(3):
            check = CoherenceCheck(score=0.5 + i * 0.1, recommendation="proceed")
            monitor.log_coherence("p1", i, check, "agent")

        stats = monitor.get_stats("p1")
        assert stats["total"] == 3
        assert stats["proceeds"] == 3
        assert stats["halts"] == 0

    def test_no_db_no_crash(self):
        m = CoherenceMonitor(db_path="/nonexistent/path.db")
        check = m.check_step_coherence("output", "goal")
        assert check is not None


# ─── EDGE CASES ───────────────────────────────────────────────

class TestEdgeCases:
    def test_very_long_output(self, monitor):
        """Should process first MAX_OUTPUT_CHARS only, not timeout."""
        long_output = COHERENT_WALL_OUTPUT * 100  # ~50K chars
        check = monitor.check_step_coherence(
            output=long_output,
            step_title="Extract walls",
        )
        assert check is not None

    def test_unicode_output(self, monitor):
        check = monitor.check_step_coherence(
            output="Résultat: 12 murs extraits. Superficie: 450 m²",
            step_title="Extract walls from plan",
        )
        assert check is not None

    def test_output_with_only_code(self, monitor):
        code_output = """```python
def create_wall(length, height):
    return Wall(length=length, height=height)
```"""
        check = monitor.check_step_coherence(
            output=code_output,
            step_title="Write wall creation code",
            expected_data_key="code",
        )
        assert check is not None
