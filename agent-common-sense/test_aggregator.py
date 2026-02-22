"""Tests for Aggregator v1.0 — active context compression."""

import json
import os
import sqlite3
import tempfile
import pytest
from aggregator import Aggregator, AggregatedContext


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def agg(db_path):
    return Aggregator(strategy="auto", db_path=db_path)


@pytest.fixture
def heuristic_agg(db_path):
    return Aggregator(strategy="heuristic", db_path=db_path)


@pytest.fixture
def structured_agg(db_path):
    return Aggregator(strategy="structured", db_path=db_path)


# ─── SAMPLE OUTPUTS ───────────────────────────────────────────

VERBOSE_OUTPUT = """
Let me search for the relevant files first.
Reading the configuration...
Checking the project structure...
Loading dependencies...

## Analysis Results

Result: Found 12 walls in the floor plan
Result: Total area is 2450 sq ft
Found: 3 doors and 8 windows

### Wall Dimensions
- Wall A: 25'-0" x 8'-0"
- Wall B: 12'-6" x 8'-0"
- Wall C: 30'-0" x 10'-0"

I decided to use the standard wall family for all exterior walls.
Using approach: trace-and-extract for the floor plan parsing.

Warning: Wall B has an unusual thickness of 2"
Note: The PDF resolution is lower than recommended (150 DPI)

```json
{"walls": [{"id": "A", "length": 25.0}, {"id": "B", "length": 12.5}]}
```

Now let me proceed with the next step...
Processing complete.
"""

SHORT_OUTPUT = "Created 5 walls successfully. Total length: 85'-0\"."

JSON_OUTPUT = """Here are the results:

```json
{
    "rooms": [
        {"name": "Living Room", "area": 450},
        {"name": "Kitchen", "area": 200},
        {"name": "Bedroom", "area": 250}
    ],
    "total_area": 900
}
```

All rooms extracted successfully.
"""

MARKDOWN_OUTPUT = """# Floor Plan Analysis

## Room Detection
Found 4 rooms using computer vision analysis. Each room boundary was traced.

## Wall Extraction
Extracted 12 wall segments from the floor plan. Used Hough transform for line detection.

## Dimension Parsing
OCR detected 8 dimension annotations. Units are in feet-inches format.

## Issues Found
Warning: 2 walls have ambiguous endpoints that may need manual review.
"""

EMPTY_OUTPUT = ""

VERY_LONG_OUTPUT = "x" * 60000


# ─── STRATEGY SELECTION TESTS ─────────────────────────────────

class TestStrategySelection:
    def test_short_output_passthrough(self, agg):
        assert agg._select_strategy("short text") == "passthrough"

    def test_short_output_threshold(self, agg):
        text = "x" * 999
        assert agg._select_strategy(text) == "passthrough"

    def test_at_threshold_is_heuristic(self, agg):
        text = "x" * 1000
        assert agg._select_strategy(text) == "heuristic"

    def test_json_output_structured(self, agg):
        text = 'Some text\n```json\n{"key": "value"}\n```\nMore text' + "x" * 1000
        assert agg._select_strategy(text) == "structured"

    def test_nested_braces_structured(self, agg):
        text = 'Result: {"a": {"b": 1}, "c": {"d": 2}}' + "x" * 1000
        assert agg._select_strategy(text) == "structured"

    def test_plain_text_heuristic(self, agg):
        text = "This is a plain text result without JSON. " * 50
        assert agg._select_strategy(text) == "heuristic"


# ─── HEURISTIC STRATEGY TESTS ─────────────────────────────────

class TestHeuristicStrategy:
    def test_extracts_result_lines(self, heuristic_agg):
        ctx = heuristic_agg.aggregate(VERBOSE_OUTPUT, {"agent": "test", "data_key": "spec"})
        facts = " ".join(ctx.key_facts)
        assert "12 walls" in facts or "Found" in facts

    def test_extracts_json_blocks(self, heuristic_agg):
        ctx = heuristic_agg.aggregate(VERBOSE_OUTPUT, {"agent": "test"})
        assert "data" in ctx.artifacts or "file_paths" in ctx.artifacts or ctx.artifacts

    def test_extracts_warnings(self, heuristic_agg):
        ctx = heuristic_agg.aggregate(VERBOSE_OUTPUT, {"agent": "test"})
        assert len(ctx.warnings) > 0

    def test_drops_noise_lines(self, heuristic_agg):
        ctx = heuristic_agg.aggregate(VERBOSE_OUTPUT, {"agent": "test"})
        prompt = heuristic_agg.to_prompt_section(ctx)
        assert "Let me search" not in prompt
        assert "Loading dependencies" not in prompt

    def test_extracts_decisions(self, heuristic_agg):
        ctx = heuristic_agg.aggregate(VERBOSE_OUTPUT, {"agent": "test"})
        assert len(ctx.decisions) > 0

    def test_respects_max_key_facts(self, heuristic_agg):
        big_output = "\n".join([f"Result: item {i} processed" for i in range(50)])
        ctx = heuristic_agg.aggregate(big_output, {"agent": "test"})
        assert len(ctx.key_facts) <= heuristic_agg.MAX_KEY_FACTS

    def test_extracts_file_paths(self, heuristic_agg):
        output = "Saved output to /mnt/d/projects/output.json\nResult: done" + "x" * 1000
        ctx = heuristic_agg.aggregate(output, {"agent": "test"})
        if "file_paths" in ctx.artifacts:
            assert any("/mnt/d" in p for p in ctx.artifacts["file_paths"])


# ─── STRUCTURED STRATEGY TESTS ────────────────────────────────

class TestStructuredStrategy:
    def test_extracts_json(self, structured_agg):
        ctx = structured_agg.aggregate(JSON_OUTPUT, {"agent": "test"})
        assert "data" in ctx.artifacts

    def test_json_data_preserved(self, structured_agg):
        ctx = structured_agg.aggregate(JSON_OUTPUT, {"agent": "test"})
        data = ctx.artifacts.get("data")
        if isinstance(data, dict):
            assert "rooms" in data or "total_area" in data

    def test_extracts_markdown_sections(self, structured_agg):
        ctx = structured_agg.aggregate(MARKDOWN_OUTPUT, {"agent": "test"})
        assert len(ctx.key_facts) >= 3  # At least 3 sections

    def test_extracts_warnings_from_sections(self, structured_agg):
        ctx = structured_agg.aggregate(MARKDOWN_OUTPUT, {"agent": "test"})
        assert len(ctx.warnings) > 0 or any("issue" in f.lower() or "warning" in f.lower() for f in ctx.key_facts)

    def test_summary_mentions_sections(self, structured_agg):
        ctx = structured_agg.aggregate(MARKDOWN_OUTPUT, {"agent": "test"})
        assert "section" in ctx.raw_summary.lower() or len(ctx.key_facts) > 0


# ─── PASSTHROUGH TESTS ────────────────────────────────────────

class TestPassthrough:
    def test_short_output_passthrough(self, agg):
        ctx = agg.aggregate(SHORT_OUTPUT, {"agent": "test"})
        # Passthrough keeps the content as raw_summary
        assert SHORT_OUTPUT in ctx.raw_summary
        # Original and compressed char counts tracked (compressed includes formatting)
        assert ctx.char_count_original == len(SHORT_OUTPUT)

    def test_short_output_in_prompt(self, agg):
        result = agg.aggregate_for_prompt(SHORT_OUTPUT, {"agent": "test"})
        assert SHORT_OUTPUT in result


# ─── COMPRESSION TESTS ────────────────────────────────────────

class TestCompression:
    def test_enforces_max_compressed_chars(self, agg):
        big_output = "\n".join([f"Result: finding number {i} is very important" for i in range(200)])
        result = agg.aggregate_for_prompt(big_output, {"agent": "test"})
        assert len(result) <= agg.MAX_COMPRESSED_CHARS + 100  # Small margin for formatting

    def test_compression_ratio_tracked(self, agg):
        # Must be above PASSTHROUGH_THRESHOLD (1000) to trigger compression
        long_verbose = VERBOSE_OUTPUT + "\n" + VERBOSE_OUTPUT + "\nExtra padding " * 50
        ctx = agg.aggregate(long_verbose, {"agent": "test"})
        assert ctx.compression_ratio < 1.0
        assert ctx.char_count_original > ctx.char_count_compressed

    def test_very_long_input_truncated(self, agg):
        ctx = agg.aggregate(VERY_LONG_OUTPUT, {"agent": "test"})
        # Should not process all 60K chars
        assert ctx.char_count_original <= agg.MAX_INPUT_CHARS


# ─── EDGE CASES ───────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_output(self, agg):
        ctx = agg.aggregate("", {"agent": "test"})
        assert "No output" in ctx.raw_summary
        assert ctx.char_count_original == 0

    def test_none_step_config(self, agg):
        ctx = agg.aggregate("Result: success", None)
        assert ctx.source_agent == "unknown"

    def test_whitespace_only_output(self, agg):
        ctx = agg.aggregate("   \n\n  \n  ", {"agent": "test"})
        # Should handle gracefully
        assert ctx is not None

    def test_special_characters(self, agg):
        output = "Result: café résumé naïve 日本語 🎉" + "x" * 1000
        ctx = agg.aggregate(output, {"agent": "test"})
        assert ctx is not None

    def test_binary_like_content(self, agg):
        output = bytes(range(256)).decode("latin-1") * 10
        ctx = agg.aggregate(output, {"agent": "test"})
        assert ctx is not None


# ─── PROMPT FORMATTING TESTS ──────────────────────────────────

class TestPromptFormatting:
    def test_prompt_section_has_header(self, agg):
        ctx = AggregatedContext(source_agent="test-agent", step_index=2,
                                raw_summary="Test summary")
        section = agg.to_prompt_section(ctx)
        assert "test-agent" in section
        assert "step 2" in section

    def test_prompt_section_has_summary(self, agg):
        ctx = AggregatedContext(raw_summary="Found 5 walls")
        section = agg.to_prompt_section(ctx)
        assert "Found 5 walls" in section

    def test_prompt_section_has_facts(self, agg):
        ctx = AggregatedContext(key_facts=["Fact 1", "Fact 2"])
        section = agg.to_prompt_section(ctx)
        assert "Fact 1" in section
        assert "Fact 2" in section

    def test_prompt_section_has_warnings(self, agg):
        ctx = AggregatedContext(warnings=["Check dimensions"])
        section = agg.to_prompt_section(ctx)
        assert "Check dimensions" in section


# ─── LOGGING TESTS ────────────────────────────────────────────

class TestLogging:
    def test_aggregation_logged(self, agg, db_path):
        agg.aggregate(VERBOSE_OUTPUT, {"agent": "test"},
                      {"pipeline_name": "test-pipeline", "step": 1})
        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM aggregation_log").fetchone()[0]
        conn.close()
        assert count == 1

    def test_stats_returned(self, agg, db_path):
        agg.aggregate(VERBOSE_OUTPUT, {"agent": "test"},
                      {"pipeline_name": "p1", "step": 0})
        agg.aggregate(VERBOSE_OUTPUT, {"agent": "test"},
                      {"pipeline_name": "p1", "step": 1})
        stats = agg.get_stats("p1")
        assert stats["total"] == 2
        assert "avg_compression_ratio" in stats

    def test_no_db_no_crash(self):
        agg = Aggregator(db_path="/nonexistent/path.db")
        # Should not crash even with no DB
        ctx = agg.aggregate("Result: test", {"agent": "test"})
        assert ctx is not None


# ─── INTEGRATION TESTS ────────────────────────────────────────

class TestIntegration:
    def test_pipeline_context_reduces_size(self, agg):
        """Simulate a 3-step pipeline and verify context stays bounded."""
        step_outputs = [VERBOSE_OUTPUT, MARKDOWN_OUTPUT, JSON_OUTPUT]
        compressed_sizes = []

        for i, output in enumerate(step_outputs):
            compressed = agg.aggregate_for_prompt(
                output, {"agent": f"step-{i}", "data_key": "data"},
                {"pipeline_name": "test", "step": i}
            )
            compressed_sizes.append(len(compressed))

        # All compressed outputs should be under MAX_COMPRESSED_CHARS
        for size in compressed_sizes:
            assert size <= agg.MAX_COMPRESSED_CHARS + 100

    def test_aggregate_for_prompt_returns_string(self, agg):
        result = agg.aggregate_for_prompt(VERBOSE_OUTPUT, {"agent": "test"})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_extract_key_lines_public(self, agg):
        """The coordinator uses _extract_key_lines directly."""
        lines = agg._extract_key_lines(VERBOSE_OUTPUT)
        assert isinstance(lines, list)
        assert len(lines) > 0
