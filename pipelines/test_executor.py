#!/usr/bin/env python3
"""
Test Suite for Pipeline Executor

Tests:
1. Pipeline loading
2. Dry-run mode
3. State persistence
4. Checkpoint handling
5. Variable resolution

Usage:
    python test_executor.py
    python test_executor.py -v  # Verbose
"""

import json
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from executor import (
    PipelineExecutor,
    ExecutionState,
    Output,
    PIPELINES_DIR,
    STATE_DIR
)


class TestResult:
    """Simple test result tracking."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name: str):
        self.passed += 1
        print(f"  ✓ {name}")

    def fail(self, name: str, error: str = ""):
        self.failed += 1
        self.errors.append((name, error))
        print(f"  ✗ {name}: {error}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*40}")
        print(f"Tests: {total} | Passed: {self.passed} | Failed: {self.failed}")
        if self.errors:
            print("\nFailures:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        return self.failed == 0


def test_pipeline_loading(results: TestResult):
    """Test that pipelines can be loaded."""
    print("\n[Test: Pipeline Loading]")

    # Test cd-set pipeline
    cd_set_path = PIPELINES_DIR / "cd-set.pipeline.json"
    if cd_set_path.exists():
        try:
            executor = PipelineExecutor(cd_set_path, dry_run=True)
            assert executor.pipeline_id == "cd-set"
            assert len(executor.pipeline.get("phases", [])) > 0
            results.ok("Load cd-set.pipeline.json")
        except Exception as e:
            results.fail("Load cd-set.pipeline.json", str(e))
    else:
        results.fail("Load cd-set.pipeline.json", "File not found")

    # Test markup-to-model pipeline
    markup_path = PIPELINES_DIR / "markup-to-model.pipeline.json"
    if markup_path.exists():
        try:
            executor = PipelineExecutor(markup_path, dry_run=True)
            assert executor.pipeline_id == "markup-to-model"
            results.ok("Load markup-to-model.pipeline.json")
        except Exception as e:
            results.fail("Load markup-to-model.pipeline.json", str(e))
    else:
        results.fail("Load markup-to-model.pipeline.json", "File not found")


def test_dry_run_mode(results: TestResult):
    """Test dry-run execution."""
    print("\n[Test: Dry-Run Mode]")

    cd_set_path = PIPELINES_DIR / "cd-set.pipeline.json"
    if not cd_set_path.exists():
        results.fail("Dry-run execution", "Pipeline not found")
        return

    try:
        executor = PipelineExecutor(cd_set_path, dry_run=True, auto_approve=True)

        # Capture output
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            success = executor.run()

        output = f.getvalue()

        # Verify dry-run indicators
        if "[DRY-RUN]" in output:
            results.ok("Dry-run markers present")
        else:
            results.fail("Dry-run markers present", "No [DRY-RUN] markers in output")

        if success:
            results.ok("Dry-run completes successfully")
        else:
            results.fail("Dry-run completes successfully", "Run returned False")

    except Exception as e:
        results.fail("Dry-run execution", str(e))


def test_state_persistence(results: TestResult):
    """Test that state is saved and can be resumed."""
    print("\n[Test: State Persistence]")

    # Create a test state
    test_state = ExecutionState(
        pipeline_id="test-pipeline",
        pipeline_name="Test Pipeline",
        started_at="2026-01-11T12:00:00",
        current_phase="P2",
        current_step="P2.1"
    )

    # Save it
    test_state_path = STATE_DIR / "test-pipeline.state.json"
    try:
        test_state.save(test_state_path)
        results.ok("State save")
    except Exception as e:
        results.fail("State save", str(e))
        return

    # Load it back
    try:
        loaded_state = ExecutionState.load(test_state_path)
        assert loaded_state.pipeline_id == "test-pipeline"
        assert loaded_state.current_phase == "P2"
        results.ok("State load")
    except Exception as e:
        results.fail("State load", str(e))

    # Cleanup
    try:
        test_state_path.unlink()
    except:
        pass


def test_variable_resolution(results: TestResult):
    """Test that variables are resolved correctly."""
    print("\n[Test: Variable Resolution]")

    cd_set_path = PIPELINES_DIR / "cd-set.pipeline.json"
    if not cd_set_path.exists():
        results.fail("Variable resolution", "Pipeline not found")
        return

    try:
        executor = PipelineExecutor(cd_set_path, dry_run=True)

        # Set some test variables
        executor.variables["levels"] = [{"id": 1}, {"id": 2}, {"id": 3}]
        executor.variables["project_info"] = {"name": "Test Project"}

        # Test resolution
        resolved = executor._resolve_variables("$levels")
        assert len(resolved) == 3
        results.ok("Simple variable resolution")

        # Test nested resolution
        nested = executor._resolve_variables({"project": "$project_info"})
        assert nested["project"]["name"] == "Test Project"
        results.ok("Nested variable resolution")

        # Test format prompt
        prompt = executor._format_prompt("Found {level_count} levels")
        assert "3" in prompt
        results.ok("Prompt formatting")

    except Exception as e:
        results.fail("Variable resolution", str(e))


def test_checkpoint_structure(results: TestResult):
    """Test checkpoint configuration in pipelines."""
    print("\n[Test: Checkpoint Structure]")

    cd_set_path = PIPELINES_DIR / "cd-set.pipeline.json"
    if not cd_set_path.exists():
        results.fail("Checkpoint structure", "Pipeline not found")
        return

    try:
        with open(cd_set_path) as f:
            pipeline = json.load(f)

        phases = pipeline.get("phases", [])
        checkpoints_found = 0

        for phase in phases:
            checkpoint = phase.get("checkpoint")
            if checkpoint:
                checkpoints_found += 1

                # Verify checkpoint has required fields
                assert "name" in checkpoint, f"Checkpoint in {phase['id']} missing 'name'"

                # Check for approval flag
                has_approval = checkpoint.get("requires_approval") or checkpoint.get("auto_pass")
                assert has_approval is not None, f"Checkpoint in {phase['id']} missing approval config"

        results.ok(f"Found {checkpoints_found} checkpoints with valid structure")

    except AssertionError as e:
        results.fail("Checkpoint structure", str(e))
    except Exception as e:
        results.fail("Checkpoint structure", str(e))


def test_corrections_loading(results: TestResult):
    """Test corrections_to_apply section."""
    print("\n[Test: Corrections Loading]")

    cd_set_path = PIPELINES_DIR / "cd-set.pipeline.json"
    if not cd_set_path.exists():
        results.fail("Corrections loading", "Pipeline not found")
        return

    try:
        with open(cd_set_path) as f:
            pipeline = json.load(f)

        corrections = pipeline.get("corrections_to_apply", [])

        if corrections:
            # Verify structure
            for corr in corrections:
                assert "id" in corr or "rule" in corr, "Correction missing id or rule"

            results.ok(f"Loaded {len(corrections)} corrections")
        else:
            results.ok("No corrections defined (optional)")

    except AssertionError as e:
        results.fail("Corrections loading", str(e))
    except Exception as e:
        results.fail("Corrections loading", str(e))


def test_cli_list(results: TestResult):
    """Test --list command."""
    print("\n[Test: CLI List Command]")

    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(PIPELINES_DIR / "executor.py"), "--list"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if "cd-set" in result.stdout or "Available" in result.stdout:
            results.ok("--list shows pipelines")
        else:
            results.fail("--list shows pipelines", f"Output: {result.stdout[:100]}")

    except Exception as e:
        results.fail("CLI list command", str(e))


def test_state_directory(results: TestResult):
    """Test that state directory exists."""
    print("\n[Test: State Directory]")

    if STATE_DIR.exists():
        results.ok("State directory exists")
    else:
        results.fail("State directory exists", f"Missing: {STATE_DIR}")


def main():
    """Run all tests."""
    print("=" * 50)
    print("Pipeline Executor Test Suite")
    print("=" * 50)

    results = TestResult()

    # Run tests
    test_pipeline_loading(results)
    test_dry_run_mode(results)
    test_state_persistence(results)
    test_variable_resolution(results)
    test_checkpoint_structure(results)
    test_corrections_loading(results)
    test_cli_list(results)
    test_state_directory(results)

    # Summary
    success = results.summary()

    print("\n" + "=" * 50)
    if success:
        print("All tests passed!")
    else:
        print("Some tests failed.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
