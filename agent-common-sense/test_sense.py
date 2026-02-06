"""
Test suite for Common Sense Engine.
Run: python3 -m pytest test_sense.py -v
  or: python3 test_sense.py
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import sense
from sense import CommonSense, ActionCheck, _SEEDS_CACHE, SEEDS_PATH


# ─── HELPERS ────────────────────────────────────────────────────

def fresh_cs(db=False, project="test"):
    """Create a CommonSense instance with clean state."""
    sense._SEEDS_CACHE = None  # Reset global cache between tests
    if db:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        conn = sqlite3.connect(tmp.name)
        conn.execute("""
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT, tags TEXT, importance INTEGER,
                project TEXT, memory_type TEXT, created_at TEXT
            )
        """)
        conn.commit()
        conn.close()
        return CommonSense(project=project, db_path=tmp.name), tmp.name
    return CommonSense(project=project, db_path=None), None


def cleanup_db(path):
    if path and os.path.exists(path):
        os.unlink(path)


# ─── ACTION CHECK DATACLASS ────────────────────────────────────

class TestActionCheck:
    def test_defaults(self):
        r = ActionCheck()
        assert r.blocked is False
        assert r.reason == ""
        assert r.warnings == []
        assert r.corrections == []
        assert r.confidence == 1.0
        assert r.safe is True

    def test_safe_with_warnings(self):
        r = ActionCheck(warnings=["something"])
        assert r.safe is False

    def test_safe_when_blocked(self):
        r = ActionCheck(blocked=True)
        assert r.safe is False

    def test_blocked_and_warnings(self):
        r = ActionCheck(blocked=True, warnings=["x"])
        assert r.safe is False


# ─── CLASSIFICATION ─────────────────────────────────────────────

class TestClassification:
    def setup_method(self):
        self.cs, _ = fresh_cs()

    def test_destructive_delete(self):
        c = self.cs._classify("delete all files")
        assert c["destructive"] is True
        assert c["reversible"] is False

    def test_destructive_rm(self):
        c = self.cs._classify("rm -rf /opt/app")
        assert c["destructive"] is True

    def test_destructive_drop(self):
        c = self.cs._classify("drop table users")
        assert c["destructive"] is True

    def test_destructive_force(self):
        c = self.cs._classify("git push --force origin main")
        assert c["destructive"] is True

    def test_destructive_reset_hard(self):
        c = self.cs._classify("git reset --hard HEAD~3")
        assert c["destructive"] is True

    def test_shared_push(self):
        c = self.cs._classify("git push origin feature")
        assert c["shared_state"] is True

    def test_shared_deploy(self):
        c = self.cs._classify("deploy to production")
        assert c["shared_state"] is True

    def test_shared_send_email(self):
        c = self.cs._classify("send email to client")
        assert c["shared_state"] is True

    def test_safe_read(self):
        c = self.cs._classify("read config file")
        assert c["destructive"] is False
        assert c["shared_state"] is False
        assert c["reversible"] is True

    def test_safe_edit(self):
        c = self.cs._classify("edit line 42 of utils.py")
        assert c["destructive"] is False
        assert c["shared_state"] is False

    def test_safe_run_tests(self):
        c = self.cs._classify("run the test suite")
        assert c["destructive"] is False
        assert c["shared_state"] is False


# ─── SEED MATCHING ──────────────────────────────────────────────

class TestSeedMatching:
    def setup_method(self):
        self.cs, _ = fresh_cs()

    def test_git_force_push_matches_git001(self):
        matches = self.cs._match_seeds("git push --force origin main")
        ids = [m["id"] for m in matches]
        assert "git-001" in ids

    def test_git_force_push_is_critical(self):
        matches = self.cs._match_seeds("git push --force origin main")
        git001 = next(m for m in matches if m["id"] == "git-001")
        assert git001["severity"] == "critical"

    def test_drop_table_matches_data001(self):
        matches = self.cs._match_seeds("DROP TABLE users")
        ids = [m["id"] for m in matches]
        assert "data-001" in ids

    def test_commit_env_matches_git002(self):
        matches = self.cs._match_seeds("git commit .env file")
        ids = [m["id"] for m in matches]
        assert "git-002" in ids

    def test_deploy_matches_deploy001(self):
        matches = self.cs._match_seeds("deploy DLL to unknown path")
        ids = [m["id"] for m in matches]
        assert "deploy-001" in ids

    def test_delete_matches_fs001(self):
        matches = self.cs._match_seeds("delete important project files")
        ids = [m["id"] for m in matches]
        assert "fs-001" in ids

    def test_git_reset_hard_matches_git003(self):
        matches = self.cs._match_seeds("git reset --hard HEAD")
        ids = [m["id"] for m in matches]
        assert "git-003" in ids

    def test_edit_matches_fs003(self):
        matches = self.cs._match_seeds("edit or write operation on config")
        ids = [m["id"] for m in matches]
        assert "fs-003" in ids

    def test_api_loop_matches_net002(self):
        matches = self.cs._match_seeds("API calls in a loop without rate limiting")
        ids = [m["id"] for m in matches]
        assert "net-002" in ids

    def test_safe_action_no_matches(self):
        matches = self.cs._match_seeds("read a log file")
        assert len(matches) == 0

    def test_benign_action_no_matches(self):
        matches = self.cs._match_seeds("check current git branch")
        assert len(matches) == 0


# ─── BEFORE() DECISIONS ────────────────────────────────────────

class TestBeforeDecisions:
    """Integration tests: action → correct decision."""

    def setup_method(self):
        self.cs, _ = fresh_cs()

    # BLOCKED scenarios
    def test_force_push_blocked(self):
        r = self.cs.before("git push --force origin main")
        assert r.blocked is True
        assert "git-001" in r.reason
        assert r.confidence == 0.0

    def test_drop_table_blocked(self):
        r = self.cs.before("DROP TABLE users")
        assert r.blocked is True
        assert "data-001" in r.reason

    def test_commit_env_blocked(self):
        r = self.cs.before("git add and commit .env file")
        assert r.blocked is True
        assert "git-002" in r.reason

    def test_deploy_unknown_path_blocked(self):
        r = self.cs.before("deploy DLL to unknown addins path")
        assert r.blocked is True
        assert "deploy-001" in r.reason

    # CAUTION scenarios (warnings, not blocked)
    def test_delete_tmp_has_warnings(self):
        r = self.cs.before("delete /tmp/old_build directory")
        assert r.blocked is False
        assert len(r.warnings) > 0
        assert r.confidence < 1.0

    def test_send_email_has_warnings(self):
        r = self.cs.before("send email to client about update")
        assert r.blocked is False
        assert any("shared state" in w.lower() for w in r.warnings)

    # SAFE scenarios
    def test_read_config_safe(self):
        r = self.cs.before("read config.yaml")
        assert r.blocked is False
        # May have unfamiliar warning but no seed matches
        assert len(r.corrections) == 0

    def test_run_tests_safe(self):
        r = self.cs.before("run pytest on unit tests")
        assert r.blocked is False
        assert len(r.corrections) == 0

    # Confidence levels
    def test_critical_zero_confidence(self):
        r = self.cs.before("git push --force origin main")
        assert r.confidence == 0.0

    def test_high_severity_low_confidence(self):
        r = self.cs.before("delete important tracked files from project")
        assert r.confidence <= 0.3

    def test_shared_state_caps_confidence(self):
        r = self.cs.before("publish package to npm")
        assert r.confidence <= 0.7


# ─── SEVERITY MAPPING ──────────────────────────────────────────

class TestSeverity:
    def test_critical_maps_to_10(self):
        assert CommonSense._severity_to_importance("critical") == 10

    def test_high_maps_to_8(self):
        assert CommonSense._severity_to_importance("high") == 8

    def test_medium_maps_to_6(self):
        assert CommonSense._severity_to_importance("medium") == 6

    def test_low_maps_to_4(self):
        assert CommonSense._severity_to_importance("low") == 4

    def test_unknown_maps_to_5(self):
        assert CommonSense._severity_to_importance("banana") == 5


# ─── SEED CACHE ─────────────────────────────────────────────────

class TestSeedCache:
    def test_cache_loads_on_first_check(self):
        sense._SEEDS_CACHE = None
        cs, _ = fresh_cs()
        cs.before("anything")
        assert sense._SEEDS_CACHE is not None
        assert len(sense._SEEDS_CACHE) == 15

    def test_cache_reused_across_instances(self):
        sense._SEEDS_CACHE = None
        cs1 = CommonSense(project="test", db_path=None)
        cs1.before("anything")
        cache_after_first = sense._SEEDS_CACHE
        assert cache_after_first is not None
        # Second instance should reuse the same cache object (not reload)
        cs2 = CommonSense(project="test2", db_path=None)
        cs2._ensure_seeds()
        assert sense._SEEDS_CACHE is cache_after_first

    def test_missing_seeds_file_gives_empty(self):
        sense._SEEDS_CACHE = None
        with patch.object(sense, 'SEEDS_PATH', Path("/nonexistent/seeds.json")):
            cs = CommonSense(project="test", db_path=None)
            cs._ensure_seeds()
            assert sense._SEEDS_CACHE == []


# ─── SQLITE INTEGRATION ────────────────────────────────────────

class TestSQLiteIntegration:
    def setup_method(self):
        self.cs, self.db_path = fresh_cs(db=True)

    def teardown_method(self):
        cleanup_db(self.db_path)

    def test_learn_stores_to_db(self):
        self.cs.learn(
            action="deployed to wrong folder",
            what_went_wrong="used system addins instead of user addins",
            correct_approach="always use user addins path"
        )
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        conn.close()
        assert rows >= 1

    def test_learn_content_searchable(self):
        self.cs.learn(
            action="wrote to locked file",
            what_went_wrong="file was open in another process",
            correct_approach="check file lock before writing"
        )
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT * FROM memories WHERE content LIKE ?",
            ["%locked file%"]
        ).fetchall()
        conn.close()
        assert len(rows) >= 1

    def test_avoided_stores_to_db(self):
        self.cs.avoided("almost force-pushed to main, used feature branch instead")
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT * FROM memories WHERE content LIKE ?",
            ["%AVOIDED MISTAKE%"]
        ).fetchall()
        conn.close()
        assert len(rows) == 1

    def test_succeeded_stores_to_db(self):
        self.cs.succeeded("deployed to correct user addins path", context="revit project")
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT * FROM memories WHERE content LIKE ?",
            ["%KNOWN GOOD%"]
        ).fetchall()
        conn.close()
        assert len(rows) == 1

    def test_keyword_search_finds_by_partial(self):
        self.cs.learn(
            action="deployed DLL to wrong Revit addins folder",
            what_went_wrong="system folder vs user folder",
            correct_approach="use AppData Roaming path"
        )
        results = self.cs._keyword_search("Revit addins deploy")
        assert len(results) >= 1

    def test_seed_to_db(self):
        count = self.cs.seed()
        assert count == 15
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT COUNT(*) FROM memories WHERE content LIKE ?",
            ["%SEED CORRECTION%"]
        ).fetchone()[0]
        conn.close()
        assert rows == 15


# ─── SEEDS.JSON INTEGRITY ──────────────────────────────────────

class TestSeedsFile:
    def setup_method(self):
        with open(SEEDS_PATH) as f:
            self.data = json.load(f)
        self.corrections = self.data["corrections"]

    def test_has_15_corrections(self):
        assert len(self.corrections) == 15

    def test_all_have_required_fields(self):
        required = {"id", "domain", "what_went_wrong", "correct_approach", "detection", "severity", "tags"}
        for c in self.corrections:
            missing = required - set(c.keys())
            assert not missing, f"{c['id']} missing fields: {missing}"

    def test_ids_are_unique(self):
        ids = [c["id"] for c in self.corrections]
        assert len(ids) == len(set(ids))

    def test_severities_valid(self):
        valid = {"critical", "high", "medium", "low"}
        for c in self.corrections:
            assert c["severity"] in valid, f"{c['id']} has invalid severity: {c['severity']}"

    def test_critical_count(self):
        criticals = [c for c in self.corrections if c["severity"] == "critical"]
        assert len(criticals) == 4

    def test_high_count(self):
        highs = [c for c in self.corrections if c["severity"] == "high"]
        assert len(highs) == 5

    def test_all_have_tags(self):
        for c in self.corrections:
            assert len(c["tags"]) >= 2, f"{c['id']} needs at least 2 tags"

    def test_all_have_detection(self):
        for c in self.corrections:
            assert len(c["detection"]) > 10, f"{c['id']} detection too short"


# ─── INJECT.PY ──────────────────────────────────────────────────

class TestInject:
    def test_kernel_loads(self):
        from inject import get_kernel
        kernel = get_kernel()
        assert "DECISION LOOP" in kernel
        assert "CLASSIFY" in kernel
        assert "SIMULATE" in kernel

    def test_seeds_as_prompt(self):
        from inject import get_seeds_as_prompt
        prompt = get_seeds_as_prompt()
        assert "Pre-Loaded Experience" in prompt
        assert "!!!" in prompt  # critical marker
        assert "FILESYSTEM" in prompt or "GIT" in prompt

    def test_full_injection(self):
        from inject import get_full_injection
        full = get_full_injection(include_seeds=True)
        assert "DECISION LOOP" in full
        assert "Pre-Loaded Experience" in full

    def test_kernel_only(self):
        from inject import get_full_injection
        kernel_only = get_full_injection(include_seeds=False)
        assert "DECISION LOOP" in kernel_only
        assert "Pre-Loaded Experience" not in kernel_only


# ─── EDGE CASES ─────────────────────────────────────────────────

class TestEdgeCases:
    def setup_method(self):
        self.cs, _ = fresh_cs()

    def test_empty_action(self):
        r = self.cs.before("")
        assert r.blocked is False

    def test_very_long_action(self):
        r = self.cs.before("x " * 1000)
        assert isinstance(r, ActionCheck)

    def test_special_characters(self):
        r = self.cs.before("rm -rf /; DROP TABLE --; <script>")
        assert isinstance(r, ActionCheck)
        assert r.blocked is True  # should catch destructive signals

    def test_unicode_action(self):
        r = self.cs.before("deploy to 日本語パス")
        assert isinstance(r, ActionCheck)

    def test_no_db_no_crash(self):
        cs = CommonSense(project="test", db_path="/nonexistent/db.sqlite")
        r = cs.before("git push --force origin main")
        # Should still work via seed matching alone
        assert r.blocked is True

    def test_case_insensitive(self):
        r1 = self.cs.before("DELETE all files")
        r2 = self.cs.before("delete all files")
        assert r1.blocked == r2.blocked

    def test_multiple_seeds_match(self):
        """An action that triggers multiple seeds should collect all of them."""
        r = self.cs.before("git push --force and deploy to unknown path")
        assert len(r.corrections) >= 2

    def test_first_critical_wins(self):
        """When multiple criticals match, the first one sets the block reason."""
        r = self.cs.before("git push --force and deploy to unknown path")
        assert r.blocked is True
        assert r.confidence == 0.0


# ─── CLI ────────────────────────────────────────────────────────

class TestCLI:
    def test_check_blocked(self):
        import subprocess
        result = subprocess.run(
            ["python3", "sense.py", "check", "--action", "git push --force origin main"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent)
        )
        assert "BLOCKED" in result.stdout

    def test_check_ok(self):
        import subprocess
        result = subprocess.run(
            ["python3", "sense.py", "check", "--action", "read a config file"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent)
        )
        assert "OK" in result.stdout

    def test_check_warnings(self):
        import subprocess
        result = subprocess.run(
            ["python3", "sense.py", "check", "--action", "send email to someone"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent)
        )
        assert "WARN" in result.stdout or "shared state" in result.stdout.lower()


# ─── RUN DIRECTLY ──────────────────────────────────────────────

if __name__ == "__main__":
    try:
        import pytest
        pytest.main([__file__, "-v", "--tb=short"])
    except ImportError:
        # Fallback: run without pytest
        import traceback
        passed = 0
        failed = 0
        errors = []

        for cls_name, cls in sorted(globals().items()):
            if not isinstance(cls, type) or not cls_name.startswith("Test"):
                continue
            for method_name in sorted(dir(cls)):
                if not method_name.startswith("test_"):
                    continue
                instance = cls()
                if hasattr(instance, "setup_method"):
                    instance.setup_method()
                try:
                    getattr(instance, method_name)()
                    passed += 1
                    print(f"  PASS  {cls_name}.{method_name}")
                except Exception as e:
                    failed += 1
                    errors.append((f"{cls_name}.{method_name}", e))
                    print(f"  FAIL  {cls_name}.{method_name}: {e}")
                finally:
                    if hasattr(instance, "teardown_method"):
                        instance.teardown_method()

        print(f"\n{'='*50}")
        print(f"Results: {passed} passed, {failed} failed")
        if errors:
            print(f"\nFailures:")
            for name, e in errors:
                print(f"  {name}: {e}")
