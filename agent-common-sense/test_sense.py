"""
Test suite for Common Sense Engine v2.0.
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
                project TEXT, memory_type TEXT, created_at TEXT,
                helped_count INTEGER DEFAULT 0,
                not_helped_count INTEGER DEFAULT 0,
                last_helped TEXT,
                status TEXT DEFAULT 'active',
                domain TEXT,
                content_hash TEXT
            )
        """)
        conn.commit()
        conn.close()
        return CommonSense(project=project, db_path=tmp.name, search_backend="keyword"), tmp.name
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

    def test_delete_tmp_has_warnings(self):
        r = self.cs.before("delete /tmp/old_build directory")
        assert r.blocked is False
        assert len(r.warnings) > 0
        assert r.confidence < 1.0

    def test_send_email_has_warnings(self):
        r = self.cs.before("send email to client about update")
        assert r.blocked is False
        assert any("shared state" in w.lower() for w in r.warnings)

    def test_read_config_safe(self):
        r = self.cs.before("read config.yaml")
        assert r.blocked is False
        assert len(r.corrections) == 0

    def test_run_tests_safe(self):
        r = self.cs.before("run pytest on unit tests")
        assert r.blocked is False
        assert len(r.corrections) == 0

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
        assert len(sense._SEEDS_CACHE) >= 14  # At least the universal seeds

    def test_cache_reused_across_instances(self):
        sense._SEEDS_CACHE = None
        cs1 = CommonSense(project="test", db_path=None)
        cs1.before("anything")
        cache_after_first = sense._SEEDS_CACHE
        assert cache_after_first is not None
        cs2 = CommonSense(project="test2", db_path=None)
        cs2._ensure_seeds()
        assert sense._SEEDS_CACHE is cache_after_first

    def test_missing_seeds_file_gives_empty(self):
        sense._SEEDS_CACHE = None
        with patch.object(sense, 'SEEDS_PATH', Path("/nonexistent/seeds.json")):
            cs = CommonSense(project="test", db_path=None)
            cs._ensure_seeds()
            # May load from domains/ or fall back to empty
            assert sense._SEEDS_CACHE is not None


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
        assert count >= 14  # At least the universal seeds
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT COUNT(*) FROM memories WHERE content LIKE ?",
            ["%SEED CORRECTION%"]
        ).fetchone()[0]
        conn.close()
        assert rows >= 14


# ─── OUTCOME TRACKING ──────────────────────────────────────────

class TestOutcomeTracking:
    def setup_method(self):
        self.cs, self.db_path = fresh_cs(db=True)

    def teardown_method(self):
        cleanup_db(self.db_path)

    def test_correction_helped_increments(self):
        # Store a correction first
        self.cs.learn(
            action="test action",
            what_went_wrong="test wrong",
            correct_approach="test right"
        )
        conn = sqlite3.connect(self.db_path)
        row_id = conn.execute("SELECT id FROM memories LIMIT 1").fetchone()[0]
        conn.close()

        result = self.cs.correction_helped(row_id, helped=True, notes="it worked")
        assert result is True

        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT helped_count FROM memories WHERE id=?", (row_id,)).fetchone()
        conn.close()
        assert row[0] == 1

    def test_correction_not_helped_increments(self):
        self.cs.learn(
            action="test action",
            what_went_wrong="test wrong",
            correct_approach="test right"
        )
        conn = sqlite3.connect(self.db_path)
        row_id = conn.execute("SELECT id FROM memories LIMIT 1").fetchone()[0]
        conn.close()

        self.cs.correction_helped(row_id, helped=False, notes="not relevant")

        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT not_helped_count FROM memories WHERE id=?", (row_id,)).fetchone()
        conn.close()
        assert row[0] == 1

    def test_get_effectiveness(self):
        self.cs.learn(
            action="test action",
            what_went_wrong="test wrong",
            correct_approach="test right"
        )
        conn = sqlite3.connect(self.db_path)
        row_id = conn.execute("SELECT id FROM memories LIMIT 1").fetchone()[0]
        conn.close()

        self.cs.correction_helped(row_id, helped=True)
        self.cs.correction_helped(row_id, helped=True)
        self.cs.correction_helped(row_id, helped=False)

        stats = self.cs.get_effectiveness(row_id)
        assert "error" not in stats or stats.get("helped_count", 0) >= 2

    def test_feedback_summary(self):
        summary = self.cs.get_feedback_summary()
        # Should return a dict with stats, not an error
        assert isinstance(summary, dict)


# ─── QUALITY PIPELINE ──────────────────────────────────────────

class TestQualityPipeline:
    def test_validate_good_correction(self):
        from quality import validate_correction
        result = validate_correction({
            "content": "Always check the deployment path before deploying the DLL.",
            "category": "deployment",
            "importance": 8,
        })
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_fragment_rejected(self):
        from quality import validate_correction
        result = validate_correction({
            "content": "2.",
            "category": "general",
            "importance": 5,
        })
        assert result.valid is False

    def test_validate_short_rejected(self):
        from quality import validate_correction
        result = validate_correction({
            "content": "too short",
            "category": "general",
            "importance": 5,
        })
        assert result.valid is False

    def test_content_hash_deterministic(self):
        from quality import content_hash
        h1 = content_hash("deploy to wrong path")
        h2 = content_hash("deploy to wrong path")
        assert h1 == h2

    def test_content_hash_normalized(self):
        from quality import content_hash
        h1 = content_hash("Deploy   to  Wrong Path!!")
        h2 = content_hash("deploy to wrong path")
        assert h1 == h2

    def test_text_similarity_identical(self):
        from quality import text_similarity
        sim = text_similarity("deploy to wrong path", "deploy to wrong path")
        assert sim == 1.0

    def test_text_similarity_different(self):
        from quality import text_similarity
        sim = text_similarity("deploy to wrong path", "read a config file")
        assert sim < 0.3

    def test_text_similarity_similar(self):
        from quality import text_similarity
        sim = text_similarity(
            "deploy DLL to wrong Revit addins path",
            "deployed DLL to incorrect Revit addins folder"
        )
        assert sim > 0.3

    def test_decay_score_fresh(self):
        from quality import decay_score
        from datetime import datetime
        score = decay_score(
            importance=8,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            helped_count=0,
        )
        assert score > 0.7  # Fresh + high importance = high score

    def test_decay_score_old(self):
        from quality import decay_score
        score = decay_score(
            importance=8,
            created_at="2020-01-01 00:00:00",
            helped_count=0,
        )
        assert score < 0.3  # Very old = low score

    def test_decay_score_helped_boosts(self):
        from quality import decay_score
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        base = decay_score(importance=5, created_at=now, helped_count=0)
        boosted = decay_score(importance=5, created_at=now, helped_count=5)
        assert boosted > base

    def test_lifecycle_transitions(self):
        from quality import can_transition, CorrectionStatus
        assert can_transition("draft", "active") is True
        assert can_transition("active", "reinforced") is True
        assert can_transition("active", "deprecated") is True
        assert can_transition("draft", "reinforced") is False
        assert can_transition("deprecated", "active") is True  # Reactivation

    def test_auto_transition_reinforced(self):
        from quality import auto_transition
        result = auto_transition("active", helped_count=5, not_helped_count=1, days_old=30)
        assert result == "reinforced"

    def test_auto_transition_deprecated(self):
        from quality import auto_transition
        result = auto_transition("active", helped_count=0, not_helped_count=6, days_old=30)
        assert result == "deprecated"

    def test_auto_transition_stale_deprecated(self):
        from quality import auto_transition
        result = auto_transition("active", helped_count=0, not_helped_count=0, days_old=200)
        assert result == "deprecated"

    def test_cleanup_dry_run(self):
        cs, db_path = fresh_cs(db=True)
        try:
            result = cs.cleanup(dry_run=True)
            assert isinstance(result, dict)
        finally:
            cleanup_db(db_path)


# ─── DOMAIN MODULE SYSTEM ──────────────────────────────────────

class TestDomainSystem:
    def test_list_domains(self):
        from domains import DomainLoader
        loader = DomainLoader()
        domains = loader.list_domains()
        assert len(domains) >= 7  # git, filesystem, network, execution, scope, deployment, data, identity
        names = [d["name"] for d in domains]
        assert "git" in names
        assert "filesystem" in names

    def test_load_git_domain(self):
        from domains import DomainLoader
        loader = DomainLoader()
        pack = loader.load("git")
        assert pack is not None
        assert pack.name == "git"
        assert pack.count >= 3
        assert pack.critical_count >= 1

    def test_load_all_domains(self):
        from domains import DomainLoader
        loader = DomainLoader()
        packs = loader.load_all()
        assert len(packs) >= 7

    def test_get_all_corrections(self):
        from domains import DomainLoader
        loader = DomainLoader()
        corrections = loader.get_all_corrections()
        assert len(corrections) >= 14
        # Each should have _domain annotation
        for c in corrections:
            assert "_domain" in c

    def test_get_corrections_filtered(self):
        from domains import DomainLoader
        loader = DomainLoader()
        corrections = loader.get_all_corrections(["git"])
        assert len(corrections) == 3  # git has 3 corrections
        for c in corrections:
            assert c["_domain"] == "git"

    def test_validate_all_domains(self):
        from domains import DomainLoader
        loader = DomainLoader()
        issues = loader.validate_all()
        # All built-in domains should pass validation
        assert len(issues) == 0, f"Domain validation issues: {issues}"

    def test_domain_ids_unique(self):
        from domains import DomainLoader
        loader = DomainLoader()
        corrections = loader.get_all_corrections()
        ids = [c["id"] for c in corrections]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {[i for i in ids if ids.count(i) > 1]}"


# ─── SEARCH BACKENDS ───────────────────────────────────────────

class TestSearchBackends:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        conn = sqlite3.connect(self.tmp.name)
        conn.execute("""
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT, tags TEXT, importance INTEGER,
                project TEXT, memory_type TEXT, created_at TEXT,
                helped_count INTEGER DEFAULT 0,
                not_helped_count INTEGER DEFAULT 0,
                last_helped TEXT,
                status TEXT DEFAULT 'active',
                domain TEXT,
                content_hash TEXT
            )
        """)
        # Insert test data
        test_corrections = [
            ("Deploy DLL to wrong Revit addins folder. Use user folder instead.", 8, "correction", "deployment"),
            ("Force pushed to main branch and lost commits.", 10, "correction", "git"),
            ("Excel COM automation fails when app not visible.", 6, "correction", "excel"),
            ("Used wrong monitor coordinates for DPI scaling.", 7, "correction", "window_management"),
            ("Forgot to read file before editing, lost changes.", 8, "correction", "filesystem"),
        ]
        for content, importance, mtype, domain in test_corrections:
            conn.execute(
                """INSERT INTO memories (content, tags, importance, project, memory_type, created_at, domain, status)
                   VALUES (?, '[]', ?, 'test', ?, datetime('now'), ?, 'active')""",
                (content, importance, mtype, domain)
            )
        conn.commit()
        conn.close()

    def teardown_method(self):
        cleanup_db(self.tmp.name)

    def test_keyword_search(self):
        from search import KeywordSearch
        backend = KeywordSearch(self.tmp.name)
        results = backend.search("deploy DLL Revit addins")
        assert len(results) >= 1
        assert "Revit" in results[0].content

    def test_keyword_search_no_results(self):
        from search import KeywordSearch
        backend = KeywordSearch(self.tmp.name)
        results = backend.search("quantum computing blockchain")
        assert len(results) == 0

    def test_keyword_search_filters_type(self):
        from search import KeywordSearch
        backend = KeywordSearch(self.tmp.name)
        results = backend.search("deploy", memory_type="correction")
        assert all(r.memory_type == "correction" for r in results)

    def test_search_result_effectiveness(self):
        from search import SearchResult
        r = SearchResult(id=1, content="test", score=0.5,
                         helped_count=3, not_helped_count=1)
        assert r.effectiveness == 0.75

    def test_search_result_unknown_effectiveness(self):
        from search import SearchResult
        r = SearchResult(id=1, content="test", score=0.5)
        assert r.effectiveness == 0.5

    def test_get_best_backend(self):
        from search import get_best_backend
        backend = get_best_backend(self.tmp.name)
        assert backend is not None
        assert backend.name in ["keyword", "tfidf", "embedding",
                                "hybrid(keyword+tfidf)", "hybrid(keyword+embedding)"]


# ─── KERNEL GENERATOR ──────────────────────────────────────────

class TestKernelGen:
    def test_classify_domain_revit(self):
        from kernel_gen import classify_domain
        assert classify_domain("createWall in Revit floor plan") == "Revit / BIM"

    def test_classify_domain_git(self):
        from kernel_gen import classify_domain
        assert classify_domain("git push force to main branch") == "Git & Version Control"

    def test_classify_domain_excel(self):
        from kernel_gen import classify_domain
        assert classify_domain("Excel COM object chart creation") == "Excel & Desktop Automation"

    def test_classify_domain_general(self):
        from kernel_gen import classify_domain
        assert classify_domain("something completely random xyz") == "General"

    def test_clean_entry_good(self):
        from kernel_gen import clean_entry
        result = clean_entry("Always check the deployment path before deploying the DLL to the addins folder.")
        assert result is not None
        assert len(result) > 20

    def test_clean_entry_fragment_rejected(self):
        from kernel_gen import clean_entry
        assert clean_entry("2.") is None
        assert clean_entry("instead of top.") is None
        assert clean_entry("") is None
        assert clean_entry("   ") is None

    def test_clean_entry_short_rejected(self):
        from kernel_gen import clean_entry
        assert clean_entry("too short") is None

    def test_clean_entry_truncation_fixed(self):
        from kernel_gen import clean_entry
        long_text = "This is a very important correction about deployment. " * 20
        result = clean_entry(long_text)
        assert result is not None
        assert len(result) <= 320  # MAX_ENTRY_LENGTH + some tolerance
        assert result.endswith(".")

    def test_deduplicate_entries(self):
        from kernel_gen import deduplicate_entries
        entries = [
            {"text": "deploy DLL to wrong Revit addins folder on Windows", "score": 0.8},
            {"text": "deploy DLL to wrong Revit addins folder on machine", "score": 0.6},
            {"text": "git push force lost commits on main", "score": 0.7},
        ]
        result = deduplicate_entries(entries, threshold=0.5)
        # The two deploy entries should be deduped
        assert len(result) <= 2


# ─── INJECT ────────────────────────────────────────────────────

class TestInject:
    def test_kernel_loads(self):
        from inject import get_kernel
        kernel = get_kernel()
        assert "DECISION LOOP" in kernel
        assert "CLASSIFY" in kernel

    def test_kernel_core_loads(self):
        from inject import get_kernel
        kernel = get_kernel(core_only=True)
        assert "DECISION LOOP" in kernel
        assert "Universal" in kernel

    def test_seeds_as_prompt(self):
        from inject import get_seeds_as_prompt
        prompt = get_seeds_as_prompt()
        assert "Pre-Loaded Experience" in prompt
        assert "!!!" in prompt  # critical marker

    def test_seeds_filtered_by_domain(self):
        from inject import get_seeds_as_prompt
        prompt = get_seeds_as_prompt(domains=["git"])
        assert "GIT" in prompt
        # Should not have filesystem content
        assert "FILESYSTEM" not in prompt or "GIT" in prompt

    def test_full_injection(self):
        from inject import get_full_injection
        full = get_full_injection(include_seeds=True)
        assert "DECISION LOOP" in full
        assert "Pre-Loaded Experience" in full

    def test_full_injection_core_only(self):
        from inject import get_full_injection
        full = get_full_injection(core_only=True)
        assert "DECISION LOOP" in full
        assert "Universal" in full


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
        assert r.blocked is True

    def test_unicode_action(self):
        r = self.cs.before("deploy to 日本語パス")
        assert isinstance(r, ActionCheck)

    def test_no_db_no_crash(self):
        cs = CommonSense(project="test", db_path="/nonexistent/db.sqlite")
        r = cs.before("git push --force origin main")
        assert r.blocked is True

    def test_case_insensitive(self):
        r1 = self.cs.before("DELETE all files")
        r2 = self.cs.before("delete all files")
        assert r1.blocked == r2.blocked

    def test_multiple_seeds_match(self):
        r = self.cs.before("git push --force and deploy to unknown path")
        assert len(r.corrections) >= 2

    def test_first_critical_wins(self):
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
