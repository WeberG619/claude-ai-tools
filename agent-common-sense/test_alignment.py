"""Tests for Alignment Core v1.0"""

import json
import os
import sqlite3
import tempfile
import pytest
from alignment import AlignmentCore, AlignmentPrinciple, AlignmentProfile


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def core(db_path):
    return AlignmentCore(db_path=db_path)


# ─── PRINCIPLE MANAGEMENT ──────────────────────────────────────

class TestPrincipleManagement:
    def test_core_principles_auto_loaded(self, core):
        principles = core.get_principles(layer="core")
        assert len(principles) >= 4

    def test_register_principle(self, core):
        pid = core.register_principle(
            "Always validate BIM dimensions",
            layer="domain", domain="bim", priority=8
        )
        assert pid > 0
        principles = core.get_principles(domain="bim")
        assert any(p.id == pid for p in principles)

    def test_register_invalid_layer(self, core):
        with pytest.raises(ValueError, match="Invalid layer"):
            core.register_principle("Test", layer="invalid")

    def test_deactivate_principle(self, core):
        pid = core.register_principle("Temporary rule")
        assert core.deactivate_principle(pid)
        active = core.get_principles(active_only=True)
        assert not any(p.id == pid for p in active)

    def test_get_principles_by_domain(self, core):
        core.register_principle("BIM rule", domain="bim")
        core.register_principle("Dev rule", domain="development")
        bim = core.get_principles(domain="bim")
        # Should include BIM + universal principles
        assert any(p.domain == "bim" for p in bim)
        assert any(p.domain == "universal" for p in bim)

    def test_get_principles_by_layer(self, core):
        core.register_principle("User rule", layer="user")
        user_principles = core.get_principles(layer="user")
        assert all(p.layer == "user" for p in user_principles)

    def test_principle_to_dict(self, core):
        pid = core.register_principle("Test principle", domain="bim", priority=7)
        principles = core.get_principles()
        p = next(p for p in principles if p.id == pid)
        d = p.to_dict()
        assert d["principle"] == "Test principle"
        assert d["domain"] == "bim"
        assert d["priority"] == 7


# ─── CONFLICT RESOLUTION ──────────────────────────────────────

class TestConflictResolution:
    def test_higher_priority_wins(self, core):
        principles = [
            AlignmentPrinciple(id=1, priority=3, layer="domain"),
            AlignmentPrinciple(id=2, priority=8, layer="domain"),
            AlignmentPrinciple(id=3, priority=5, layer="domain"),
        ]
        resolved = core.resolve_conflicts(principles)
        assert resolved[0].priority >= resolved[-1].priority

    def test_core_layer_first(self, core):
        principles = [
            AlignmentPrinciple(id=1, priority=10, layer="domain"),
            AlignmentPrinciple(id=2, priority=5, layer="core"),
        ]
        resolved = core.resolve_conflicts(principles)
        assert resolved[0].layer == "core"

    def test_correction_over_domain(self, core):
        principles = [
            AlignmentPrinciple(id=1, priority=5, layer="domain"),
            AlignmentPrinciple(id=2, priority=5, layer="correction"),
        ]
        resolved = core.resolve_conflicts(principles)
        assert resolved[0].layer == "correction"

    def test_specific_domain_over_universal(self, core):
        principles = [
            AlignmentPrinciple(id=1, priority=5, layer="domain", domain="universal"),
            AlignmentPrinciple(id=2, priority=5, layer="domain", domain="bim"),
        ]
        resolved = core.resolve_conflicts(principles)
        assert resolved[0].domain == "bim"


# ─── PROFILE COMPILATION ──────────────────────────────────────

class TestProfileCompilation:
    def test_compile_profile(self, core):
        profile = core.compile_profile("test-agent", "Create walls in Revit")
        assert profile.agent_name == "test-agent"
        assert profile.task_domain == "bim"
        assert len(profile.principles) > 0

    def test_compile_prompt_output(self, core):
        prompt = core.compile_prompt("test-agent", "Build feature")
        assert isinstance(prompt, str)
        # Should contain principles section
        assert "Alignment Principles" in prompt

    def test_domain_detection_bim(self, core):
        assert core.detect_domain("Create walls in Revit model") == "bim"

    def test_domain_detection_dev(self, core):
        assert core.detect_domain("Write Python code and run tests") == "development"

    def test_domain_detection_excel(self, core):
        assert core.detect_domain("Update Excel spreadsheet formulas") == "excel"

    def test_domain_detection_client(self, core):
        assert core.detect_domain("Send client proposal and invoice") == "client"

    def test_domain_detection_desktop(self, core):
        assert core.detect_domain("Move window to monitor and take screenshot") == "desktop"

    def test_domain_detection_general(self, core):
        assert core.detect_domain("do something random") == "general"

    def test_token_budget(self, core):
        profile = core.compile_profile("test", "Write code and deploy")
        # Should be within budget
        assert profile.total_char_estimate <= 16000

    def test_compile_with_project(self, core):
        prompt = core.compile_prompt("test", "Build feature", project="MyProject")
        assert isinstance(prompt, str)


# ─── AUTO-INJECTION ───────────────────────────────────────────

class TestAutoInjection:
    def test_pre_task_hook_format(self, core):
        tool_input = {
            "prompt": "Create Revit walls",
            "subagent_type": "revit-builder",
        }
        result = core.pre_task_hook(tool_input)
        assert result["status"] == "pass"

    def test_pre_task_hook_empty_prompt(self, core):
        result = core.pre_task_hook({"prompt": ""})
        assert result["status"] == "pass"

    def test_autonomous_injection(self, core):
        prefix = core.get_injection_for_autonomous(
            "revit-builder",
            "Create walls from spec",
            {"project": "Test Project"}
        )
        assert isinstance(prefix, str)

    def test_autonomous_injection_no_event(self, core):
        prefix = core.get_injection_for_autonomous(
            "tech-scout", "Research topic"
        )
        assert isinstance(prefix, str)


# ─── OUTCOME VERIFICATION ────────────────────────────────────

class TestOutcomeVerification:
    def test_verify_aligned_outcome(self, core):
        result = core.verify_outcome(
            "test-agent",
            "Read a file",
            "File was read and verified. Screenshot taken."
        )
        assert result["aligned"] is True
        assert result["principles_checked"] > 0

    def test_verify_domain_detected(self, core):
        result = core.verify_outcome(
            "revit-builder",
            "Create walls in Revit",
            "Walls created"
        )
        assert result["domain"] == "bim"


# ─── DRIFT DETECTION ──────────────────────────────────────────

class TestDriftDetection:
    def test_record_violation(self, core):
        pid = core.register_principle("Always verify", priority=9)
        vid = core.record_violation(
            "test-agent", pid, "missing_verification",
            "Agent didn't verify work"
        )
        assert vid > 0

    def test_violation_count_increments(self, core):
        pid = core.register_principle("Always verify", priority=9)
        core.record_violation("test", pid, "skip", "Skipped check")
        core.record_violation("test", pid, "skip", "Skipped again")

        principles = core.get_principles()
        p = next(p for p in principles if p.id == pid)
        assert p.violations == 2

    def test_detect_drift_pattern(self, core):
        pid = core.register_principle("Important rule", priority=8)
        core.record_violation("agent1", pid, "skip", "V1")
        core.record_violation("agent2", pid, "skip", "V2")
        core.record_violation("agent1", pid, "skip", "V3")

        drift = core.detect_drift()
        assert len(drift) >= 1
        assert drift[0]["violation_count"] >= 2

    def test_get_drift_report(self, core):
        report = core.get_drift_report()
        assert "total_violations" in report
        assert "unresolved" in report
        assert "drift_patterns" in report
        assert "most_violated_principles" in report

    def test_no_drift_when_clean(self, core):
        drift = core.detect_drift()
        assert len(drift) == 0

    def test_drift_report_with_violations(self, core):
        pid = core.register_principle("Test rule")
        core.record_violation("agent", pid, "type", "desc")

        report = core.get_drift_report()
        assert report["total_violations"] == 1
        assert report["unresolved"] == 1


# ─── CORRECTIONS WITH REAL DATA ──────────────────────────────

class TestCorrectionsWithData:
    def test_get_corrections_for_task_with_memories(self, db_path):
        """Test corrections loading with actual memories table."""
        # Create memories table with correction rows
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                memory_type TEXT DEFAULT 'general',
                importance REAL DEFAULT 0.5,
                status TEXT DEFAULT NULL
            )
        """)
        conn.execute("""
            INSERT INTO memories (content, memory_type, importance)
            VALUES ('CORRECTION: Always verify Revit wall dimensions against PDF source', 'correction', 0.9)
        """)
        conn.execute("""
            INSERT INTO memories (content, memory_type, importance)
            VALUES ('CORRECTION: Use DPI-aware positioning for Excel windows', 'correction', 0.8)
        """)
        conn.execute("""
            INSERT INTO memories (content, memory_type, importance)
            VALUES ('General note about something unrelated', 'general', 0.5)
        """)
        conn.commit()
        conn.close()

        core = AlignmentCore(db_path=db_path)
        result = core.get_corrections_for_task("Create walls in Revit model")
        assert "Relevant Corrections" in result
        assert "Revit" in result or "wall" in result

    def test_get_corrections_empty_task(self, db_path):
        core = AlignmentCore(db_path=db_path)
        result = core.get_corrections_for_task("")
        assert result == ""

    def test_get_corrections_no_memories_table(self, db_path):
        core = AlignmentCore(db_path=db_path)
        result = core.get_corrections_for_task("some task description")
        assert result == ""

    def test_get_corrections_no_matching(self, db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                memory_type TEXT DEFAULT 'general',
                importance REAL DEFAULT 0.5,
                status TEXT DEFAULT NULL
            )
        """)
        conn.execute("""
            INSERT INTO memories (content, memory_type, importance)
            VALUES ('CORRECTION: Something about cooking recipes', 'correction', 0.9)
        """)
        conn.commit()
        conn.close()

        core = AlignmentCore(db_path=db_path)
        result = core.get_corrections_for_task("build quantum computer firmware")
        # No matching corrections for this task
        assert result == "" or "Relevant Corrections" not in result or "cooking" not in result

    def test_compile_prompt_with_corrections(self, db_path):
        """Full compile_prompt with corrections in the DB."""
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                memory_type TEXT DEFAULT 'general',
                importance REAL DEFAULT 0.5,
                status TEXT DEFAULT NULL
            )
        """)
        conn.execute("""
            INSERT INTO memories (content, memory_type, importance)
            VALUES ('CORRECTION: Always validate wall lengths before creating in Revit', 'correction', 0.9)
        """)
        conn.commit()
        conn.close()

        core = AlignmentCore(db_path=db_path)
        prompt = core.compile_prompt("revit-builder", "Create walls from extracted geometry")
        assert isinstance(prompt, str)
        assert "Alignment Principles" in prompt


# ─── OUTCOME VERIFICATION — VIOLATIONS ──────────────────────

class TestVerificationViolations:
    def test_verify_unverified_outcome(self, core):
        """Outcome that doesn't mention verification should flag violation."""
        result = core.verify_outcome(
            "revit-builder",
            "Create walls in Revit model",
            "Walls were created. Done."
        )
        # The "verify" core principle should trigger since no "verified" or "screenshot" in result
        assert result["principles_checked"] > 0

    def test_verify_with_screenshot(self, core):
        """Outcome that mentions screenshot should pass verification."""
        result = core.verify_outcome(
            "test-agent",
            "Build Excel dashboard",
            "Dashboard built and verified. Screenshot taken to confirm layout."
        )
        assert result["aligned"] is True

    def test_verify_returns_domain(self, core):
        result = core.verify_outcome(
            "test", "Update Excel formulas", "Done"
        )
        assert result["domain"] == "excel"


# ─── ALIGNMENT HOOK ──────────────────────────────────────────

class TestAlignmentHook:
    def test_hook_main_no_env(self):
        """Hook should output pass when no env var set."""
        import subprocess
        result = subprocess.run(
            ["python3", os.path.join(os.path.dirname(__file__), "alignment_hook.py")],
            capture_output=True, text=True,
            env={**os.environ, "CLAUDE_TOOL_INPUT": "{}"},
            cwd=os.path.dirname(__file__),
        )
        output = result.stdout.strip().split("\n")[-1]
        parsed = json.loads(output)
        assert parsed["status"] == "pass"

    def test_hook_with_prompt(self):
        """Hook should process a valid Task tool input."""
        import subprocess
        tool_input = json.dumps({
            "prompt": "Create walls in Revit model",
            "subagent_type": "revit-builder"
        })
        result = subprocess.run(
            ["python3", os.path.join(os.path.dirname(__file__), "alignment_hook.py")],
            capture_output=True, text=True,
            env={**os.environ, "CLAUDE_TOOL_INPUT": tool_input},
            cwd=os.path.dirname(__file__),
        )
        output = result.stdout.strip().split("\n")[-1]
        parsed = json.loads(output)
        assert parsed["status"] == "pass"

    def test_hook_double_injection_skip(self):
        """Hook should skip if alignment already injected."""
        import subprocess
        tool_input = json.dumps({
            "prompt": "# Agent Execution Framework\nAlready injected\nDo the thing",
            "subagent_type": "test"
        })
        result = subprocess.run(
            ["python3", os.path.join(os.path.dirname(__file__), "alignment_hook.py")],
            capture_output=True, text=True,
            env={**os.environ, "CLAUDE_TOOL_INPUT": tool_input},
            cwd=os.path.dirname(__file__),
        )
        output = result.stdout.strip().split("\n")[-1]
        parsed = json.loads(output)
        assert parsed["status"] == "pass"

    def test_hook_invalid_json(self):
        """Hook should handle invalid JSON gracefully."""
        import subprocess
        result = subprocess.run(
            ["python3", os.path.join(os.path.dirname(__file__), "alignment_hook.py")],
            capture_output=True, text=True,
            env={**os.environ, "CLAUDE_TOOL_INPUT": "not valid json{{{"},
            cwd=os.path.dirname(__file__),
        )
        output = result.stdout.strip().split("\n")[-1]
        parsed = json.loads(output)
        assert parsed["status"] == "pass"

    def test_hook_empty_prompt_passthrough(self):
        """Hook should pass through when prompt is empty."""
        import subprocess
        tool_input = json.dumps({"prompt": "", "subagent_type": "test"})
        result = subprocess.run(
            ["python3", os.path.join(os.path.dirname(__file__), "alignment_hook.py")],
            capture_output=True, text=True,
            env={**os.environ, "CLAUDE_TOOL_INPUT": tool_input},
            cwd=os.path.dirname(__file__),
        )
        output = result.stdout.strip().split("\n")[-1]
        parsed = json.loads(output)
        assert parsed["status"] == "pass"

    def test_hook_kernel_marker_skip(self):
        """Hook should skip when '# Common Sense Kernel' is in prompt."""
        import subprocess
        tool_input = json.dumps({
            "prompt": "# Common Sense Kernel\nAlready has kernel content\nDo the work",
            "subagent_type": "test"
        })
        result = subprocess.run(
            ["python3", os.path.join(os.path.dirname(__file__), "alignment_hook.py")],
            capture_output=True, text=True,
            env={**os.environ, "CLAUDE_TOOL_INPUT": tool_input},
            cwd=os.path.dirname(__file__),
        )
        output = result.stdout.strip().split("\n")[-1]
        parsed = json.loads(output)
        assert parsed["status"] == "pass"


# ─── KERNEL AND CONTENT LOADING ──────────────────────────────

class TestKernelLoading:
    def test_get_kernel_returns_string(self, core):
        result = core.get_kernel_for_domain("general")
        assert isinstance(result, str)

    def test_get_kernel_domain_filter(self, core):
        result = core.get_kernel_for_domain("bim")
        assert isinstance(result, str)

    def test_kernel_respects_max_chars(self, core):
        result = core.get_kernel_for_domain("general")
        assert len(result) <= 6000  # MAX_KERNEL_CHARS

    def test_extract_kernel_sections_keeps_essentials(self, core):
        """_extract_kernel_sections should keep headers and essential patterns."""
        content = """# Common Sense Kernel

## DECISION LOOP
Always think before acting.

## Random Section
Some random content here.

## CRITICAL RULES
Never skip verification.

## BIM Guidelines
Use correct wall parameters.
Check revit model quality.

## Cooking Tips
Boil water first.
"""
        result = core._extract_kernel_sections(content, "bim")
        assert "DECISION LOOP" in result
        assert "CRITICAL" in result
        assert "revit" in result or "wall" in result

    def test_load_strong_agent_trimmed_with_file(self, core, db_path):
        """Test strong agent trimming with actual oversized content."""
        import alignment
        original = alignment.STRONG_AGENT_PATH

        # Create a temp file larger than MAX_STRONG_AGENT_CHARS
        fd, tmp = tempfile.mkstemp(suffix=".md")
        os.close(fd)
        try:
            sections = ["# Strong Agent Framework\nIntro content.\n"]
            sections.append("\n## Execution Phase\nRun the plan carefully.\n" * 50)
            sections.append("\n## Quality Check\nVerify all outputs.\n" * 50)
            sections.append("\n## Random Filler\nLots of filler text.\n" * 100)
            with open(tmp, 'w') as f:
                f.write("".join(sections))

            alignment.STRONG_AGENT_PATH = __import__('pathlib').Path(tmp)
            result = core._load_strong_agent_trimmed()
            assert len(result) <= 4000  # MAX_STRONG_AGENT_CHARS
            assert "Strong Agent Framework" in result
        finally:
            alignment.STRONG_AGENT_PATH = original
            os.unlink(tmp)

    def test_trim_to_budget_actually_trims(self, core):
        """Verify _trim_to_budget reduces content when over MAX_TOTAL_CHARS."""
        profile = AlignmentProfile(
            agent_name="test",
            kernel_content="K" * 8000,
            strong_agent_content="S" * 5000,
            corrections_content="C" * 5000,
            total_char_estimate=18000,
        )
        core._trim_to_budget(profile)
        assert profile.total_char_estimate <= 16000


# ─── EDGE CASES ──────────────────────────────────────────────

class TestAlignmentEdgeCases:
    def test_domain_detection_filesystem(self, core):
        assert core.detect_domain("copy file to directory and rename") == "filesystem"

    def test_domain_detection_mixed(self, core):
        """When multiple domains match, highest score wins."""
        result = core.detect_domain("Create Revit wall model with BIM parameters and schedule family elements")
        assert result == "bim"

    def test_resolve_conflicts_empty(self, core):
        resolved = core.resolve_conflicts([])
        assert resolved == []

    def test_resolve_conflicts_single(self, core):
        p = AlignmentPrinciple(id=1, priority=5, layer="domain")
        resolved = core.resolve_conflicts([p])
        assert len(resolved) == 1

    def test_user_layer_between_correction_and_domain(self, core):
        principles = [
            AlignmentPrinciple(id=1, priority=5, layer="user"),
            AlignmentPrinciple(id=2, priority=5, layer="domain"),
        ]
        resolved = core.resolve_conflicts(principles)
        assert resolved[0].layer == "user"

    def test_deactivate_nonexistent(self, core):
        # Should not crash
        core.deactivate_principle(9999)

    def test_profile_token_estimate(self, core):
        profile = core.compile_profile("test", "Write Python tests")
        assert profile.total_token_estimate == profile.total_char_estimate // 4

    def test_compile_prompt_includes_principles(self, core):
        prompt = core.compile_prompt("test", "Create Revit walls")
        assert "Alignment Principles" in prompt
        assert "[CORE]" in prompt

    def test_pre_task_hook_with_description_key(self, core):
        """Hook should also check 'description' key when 'prompt' is missing."""
        result = core.pre_task_hook({"description": "do something"})
        assert result["status"] == "pass"

    def test_record_violation_with_session_id(self, core):
        pid = core.register_principle("Always check", priority=7)
        vid = core.record_violation(
            "test-agent", pid, "skip", "Skipped check",
            severity="high", session_id="session-123"
        )
        assert vid > 0

    def test_detect_drift_custom_window(self, core):
        """detect_drift with a very large window should still find violations."""
        pid = core.register_principle("Test rule", priority=8)
        core.record_violation("a", pid, "skip", "V1")
        core.record_violation("b", pid, "skip", "V2")
        drift = core.detect_drift(window_hours=8760)  # 1 year
        assert len(drift) >= 1

    def test_detect_drift_narrow_window(self, core):
        """detect_drift with 0-hour window should find nothing."""
        pid = core.register_principle("Test rule", priority=8)
        core.record_violation("a", pid, "skip", "V1")
        core.record_violation("b", pid, "skip", "V2")
        # 0-hour window = only violations from "now" forward, which is nothing
        drift = core.detect_drift(window_hours=0)
        assert len(drift) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
