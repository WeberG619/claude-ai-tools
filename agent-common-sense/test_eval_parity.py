"""
Tests for Eval Parity v1.0
============================
AST-level audit ensuring production and test code paths are identical.
Detects test-specific branches, threshold gaming, and eval shortcuts.

These tests scan ALL production modules for patterns that would make
test results diverge from production behavior.
"""

import ast
import os
import re
import pytest
from pathlib import Path


# ─── CONFIG ───────────────────────────────────────────────────

PROD_DIR = Path(__file__).parent
PROD_MODULES = [
    "alignment.py",
    "coherence.py",
    "aggregator.py",
    "coordinator.py",
    "goals.py",
    "planner.py",
    "permissions.py",
    "selfcheck.py",
    "sense.py",
]

# Only test modules that exist
EXISTING_MODULES = [m for m in PROD_MODULES if (PROD_DIR / m).exists()]


def _read_source(module_name: str) -> str:
    path = PROD_DIR / module_name
    return path.read_text() if path.exists() else ""


def _parse_ast(module_name: str) -> ast.Module:
    source = _read_source(module_name)
    return ast.parse(source) if source else ast.parse("")


# ─── NO TEST DETECTION ────────────────────────────────────────

class TestNoTestDetection:
    """Production code must not detect or branch on test environment."""

    def test_no_pytest_detection(self):
        """No production module should import or reference pytest."""
        for mod in EXISTING_MODULES:
            source = _read_source(mod)
            # Allow 'pytest' in comments/docstrings but not in actual imports or code
            lines = source.split("\n")
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Skip comments and docstrings
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                # Check for pytest imports or references in code
                if "import pytest" in stripped:
                    pytest.fail(f"{mod}:{i+1} imports pytest in production code")
                if "pytest.mark" in stripped or "pytest.fixture" in stripped:
                    pytest.fail(f"{mod}:{i+1} references pytest in production code")

    def test_no_test_mode_flags(self):
        """No test_mode, testing, or is_test flags in production code."""
        flag_patterns = [
            re.compile(r'\btest_mode\s*[=:]', re.IGNORECASE),
            re.compile(r'\bis_test\s*[=:]', re.IGNORECASE),
            re.compile(r'\btesting\s*=\s*True', re.IGNORECASE),
            re.compile(r'if\s+.*\btest_mode\b', re.IGNORECASE),
            re.compile(r'if\s+.*\bis_test\b', re.IGNORECASE),
        ]
        for mod in EXISTING_MODULES:
            source = _read_source(mod)
            for pattern in flag_patterns:
                match = pattern.search(source)
                if match:
                    pytest.fail(f"{mod} contains test detection flag: '{match.group()}'")

    def test_thresholds_are_constants(self):
        """Thresholds must be class constants or module-level, not env-driven."""
        env_patterns = [
            re.compile(r'os\.environ.*threshold', re.IGNORECASE),
            re.compile(r'os\.getenv.*threshold', re.IGNORECASE),
            re.compile(r'THRESHOLD.*os\.environ', re.IGNORECASE),
            re.compile(r'THRESHOLD.*os\.getenv', re.IGNORECASE),
        ]
        for mod in EXISTING_MODULES:
            source = _read_source(mod)
            for pattern in env_patterns:
                match = pattern.search(source)
                if match:
                    pytest.fail(f"{mod} has env-driven threshold: '{match.group()}'")


# ─── THRESHOLD PARITY ────────────────────────────────────────

class TestThresholdParity:
    """Thresholds must be identical across instances."""

    def test_coherence_thresholds_constant(self):
        """CoherenceMonitor thresholds are class constants, not instance variables."""
        from coherence import CoherenceMonitor
        m1 = CoherenceMonitor(db_path="/nonexistent/path1.db")
        m2 = CoherenceMonitor(db_path="/nonexistent/path2.db")
        assert m1.THRESHOLD_WARN == m2.THRESHOLD_WARN
        assert m1.THRESHOLD_HALT == m2.THRESHOLD_HALT
        assert m1.THRESHOLD_WARN == CoherenceMonitor.THRESHOLD_WARN

    def test_selfcheck_thresholds_constant(self):
        """SelfChecker thresholds are class constants."""
        from selfcheck import SelfChecker
        s1 = SelfChecker(db_path="/nonexistent/path1.db")
        s2 = SelfChecker(db_path="/nonexistent/path2.db")
        assert s1.PASS_THRESHOLD == s2.PASS_THRESHOLD
        assert s1.RETRY_THRESHOLD == s2.RETRY_THRESHOLD
        assert s1.PASS_THRESHOLD == SelfChecker.PASS_THRESHOLD

    def test_injection_quality_threshold_constant(self):
        """InjectionResult.meets_minimum uses a fixed threshold."""
        from alignment import InjectionResult
        r1 = InjectionResult(success=True, char_count=200, quality_score=0.3)
        r2 = InjectionResult(success=True, char_count=200, quality_score=0.3)
        assert r1.meets_minimum == r2.meets_minimum


# ─── CODE PATH PARITY ────────────────────────────────────────

class TestCodePathParity:
    """Methods must not be monkey-patched or conditional on test environment."""

    def test_no_conditional_imports_on_test_env(self):
        """No 'if testing/test_env' guards around imports."""
        test_import_patterns = [
            re.compile(r'if\s+.*test.*:\s*\n\s*import', re.IGNORECASE),
            re.compile(r'if\s+.*test.*:\s*\n\s*from\s+', re.IGNORECASE),
        ]
        for mod in EXISTING_MODULES:
            source = _read_source(mod)
            for pattern in test_import_patterns:
                match = pattern.search(source)
                if match:
                    pytest.fail(f"{mod} has conditional import based on test env: '{match.group()}'")

    def test_coherence_methods_not_patched(self):
        """CoherenceMonitor core methods are actual methods, not replaced at runtime."""
        from coherence import CoherenceMonitor
        m = CoherenceMonitor(db_path="/nonexistent/path.db")
        # Verify key methods exist and are callable
        assert callable(m.check_step_coherence)
        assert callable(m.detect_drift_signals)
        assert callable(m.check_trajectory_coherence)
        # Verify they're bound methods from the class
        assert m.check_step_coherence.__func__ is CoherenceMonitor.check_step_coherence

    def test_selfcheck_methods_not_patched(self):
        """SelfChecker core methods are actual methods, not replaced."""
        from selfcheck import SelfChecker
        s = SelfChecker(db_path="/nonexistent/path.db")
        assert callable(s.check)
        assert callable(s.build_retry_feedback)
        assert s.check.__func__ is SelfChecker.check


# ─── NO EVAL GAMING ──────────────────────────────────────────

class TestNoEvalGaming:
    """Scan all modules for suspicious patterns that might game eval."""

    def test_no_if_branches_referencing_test(self):
        """AST walk: no 'if' branches whose condition references 'test' or 'eval'."""
        suspicious = []
        for mod in EXISTING_MODULES:
            tree = _parse_ast(mod)
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    # Get the condition source
                    try:
                        cond_names = [n.id for n in ast.walk(node.test)
                                      if isinstance(n, ast.Name)]
                        for name in cond_names:
                            name_lower = name.lower()
                            if any(kw in name_lower for kw in ["test", "eval", "mock"]):
                                suspicious.append(
                                    f"{mod}:line {node.lineno}: if branch references '{name}'"
                                )
                    except Exception:
                        pass

        if suspicious:
            pytest.fail("Suspicious test/eval branches found:\n" + "\n".join(suspicious))

    def test_no_hardcoded_test_returns(self):
        """No functions that return hardcoded values when 'test' appears in args."""
        patterns = [
            re.compile(r'if\s+["\']test["\']\s+in\s+', re.IGNORECASE),
            re.compile(r'return\s+True.*#.*test', re.IGNORECASE),
        ]
        for mod in EXISTING_MODULES:
            source = _read_source(mod)
            for pattern in patterns:
                match = pattern.search(source)
                if match:
                    pytest.fail(f"{mod} may have hardcoded test return: '{match.group()}'")

    def test_no_noop_methods_in_test_path(self):
        """No pass-only methods that exist just for tests."""
        for mod in EXISTING_MODULES:
            tree = _parse_ast(mod)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Skip __init__ and single-line helpers
                    if node.name.startswith("__"):
                        continue
                    body = node.body
                    # Check for pass-only functions (excluding those with docstrings)
                    if len(body) == 1 and isinstance(body[0], ast.Pass):
                        if "test" in node.name.lower() or "mock" in node.name.lower():
                            pytest.fail(
                                f"{mod}: noop method '{node.name}' at line {node.lineno} "
                                f"may exist only for testing"
                            )

    def test_no_sleep_in_production(self):
        """Production code should not use time.sleep (test timing hack)."""
        for mod in EXISTING_MODULES:
            source = _read_source(mod)
            if "time.sleep(" in source:
                # Allow in CLI/main blocks only
                lines = source.split("\n")
                in_main = False
                for i, line in enumerate(lines):
                    if 'if __name__' in line:
                        in_main = True
                    if "time.sleep(" in line and not in_main:
                        pytest.fail(f"{mod}:{i+1} uses time.sleep in production code")

    def test_no_random_in_scoring(self):
        """Scoring/threshold logic must not use random values."""
        for mod in EXISTING_MODULES:
            source = _read_source(mod)
            if "random." in source and any(kw in source.lower()
                                            for kw in ["score", "threshold", "weight"]):
                # Find the specific line
                for i, line in enumerate(source.split("\n")):
                    if "random." in line:
                        pytest.fail(f"{mod}:{i+1} uses random in scoring context")

    def test_consistent_weight_sums(self):
        """SelfChecker weights must sum to 1.0."""
        from selfcheck import SelfChecker
        total = sum(SelfChecker.WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"SelfChecker weights sum to {total}, expected 1.0"
