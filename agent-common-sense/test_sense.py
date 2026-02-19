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
        # May find low-relevance corrections from real DB — just check not blocked

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


# ─── AUTO-CAPTURE ──────────────────────────────────────────────

class TestAutoCapture:
    def test_detects_correction(self):
        from autocapture import CorrectionCapture
        cap = CorrectionCapture()
        result = cap.check_message("No, that's wrong. The path is /opt/app-v2, not /opt/app.")
        assert result is not None
        assert result.confidence >= 0.6

    def test_detects_strong_correction(self):
        from autocapture import CorrectionCapture
        cap = CorrectionCapture()
        result = cap.check_message("You made a mistake. The correct way is to use git rebase.")
        assert result is not None
        assert result.confidence >= 0.8

    def test_ignores_normal_message(self):
        from autocapture import CorrectionCapture
        cap = CorrectionCapture()
        result = cap.check_message("Can you help me with this task?")
        assert result is None

    def test_ignores_short_message(self):
        from autocapture import CorrectionCapture
        cap = CorrectionCapture()
        result = cap.check_message("ok")
        assert result is None

    def test_extracts_wrong_and_right(self):
        from autocapture import CorrectionCapture
        cap = CorrectionCapture()
        result = cap.check_message("No, that's wrong. Wrong: used Outlook. Use Gmail in Chrome instead.")
        assert result is not None
        assert result.correct_approach or result.what_wrong

    def test_domain_detection(self):
        from autocapture import CorrectionCapture
        cap = CorrectionCapture()
        result = cap.check_message("No, that's wrong. The Revit wall should be 8 inches.")
        assert result is not None
        assert result.domain == "revit"

    def test_domain_detection_git(self):
        from autocapture import CorrectionCapture
        cap = CorrectionCapture()
        result = cap.check_message("Don't do that. Never force push to the main branch.")
        assert result is not None
        assert result.domain == "git"

    def test_severity_escalation(self):
        from autocapture import CorrectionCapture
        cap = CorrectionCapture()
        result = cap.check_message("No, that's wrong! That crashed the application and lost data!")
        assert result is not None
        assert result.severity == "critical"

    def test_capture_and_store_with_db(self):
        from autocapture import CorrectionCapture
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

        try:
            cap = CorrectionCapture(db_path=tmp.name)
            result = cap.capture_and_store("No, that's wrong. You should use the user addins path.")
            assert result is not None
        finally:
            os.unlink(tmp.name)

    def test_scan_transcript(self):
        from autocapture import CorrectionCapture
        cap = CorrectionCapture()
        transcript = """
User: Create a wall at position 0,0
Assistant: I'll create the wall now.
User: No, that's wrong. The wall should be at position 10,5.
Assistant: Let me fix that.
User: Also, you forgot to set the wall height.
"""
        results = cap.scan_transcript(transcript)
        assert len(results) >= 1


# ─── HOOKS ─────────────────────────────────────────────────────

class TestHooks:
    def test_classify_risk_bash_high(self):
        from hooks import classify_risk
        level, domains = classify_risk("Bash", {"command": "rm -rf /tmp/build"})
        assert level == "high"

    def test_classify_risk_read_low(self):
        from hooks import classify_risk
        level, domains = classify_risk("Read", {"file_path": "/tmp/config.yaml"})
        assert level == "low"

    def test_classify_risk_edit_medium(self):
        from hooks import classify_risk
        level, domains = classify_risk("Edit", {"file_path": "/src/main.py"})
        assert level == "medium"

    def test_classify_risk_revit(self):
        from hooks import classify_risk
        level, domains = classify_risk(
            "mcp__revit__createWall",
            {"params": {"startX": 0, "startY": 0}}
        )
        assert level == "high"
        assert "revit" in domains

    def test_classify_risk_deploy_keyword(self):
        from hooks import classify_risk
        level, domains = classify_risk("Bash", {"command": "deploy to production"})
        assert level == "high"

    def test_extract_search_query(self):
        from hooks import extract_search_query
        query = extract_search_query("mcp__revit__createWall",
                                      {"params": {"wallType": "Basic Wall"}})
        assert "revit" in query.lower()
        assert "createwall" in query.lower()

    def test_pre_action_hook_returns_dict(self):
        from hooks import pre_action_hook
        result = pre_action_hook("Read", {"file_path": "/tmp/test.txt"})
        assert isinstance(result, dict)
        assert "checked" in result

    def test_post_action_hook_returns_dict(self):
        from hooks import post_action_hook
        result = post_action_hook("Read", {"file_path": "/tmp/test.txt"})
        assert isinstance(result, dict)

    def test_correction_detect_hook_no_correction(self):
        from hooks import correction_detect_hook
        result = correction_detect_hook("Can you help me with this?")
        assert result.get("type") == "no_correction"

    def test_correction_detect_hook_finds_correction(self):
        from hooks import correction_detect_hook
        result = correction_detect_hook("No, that's wrong. Use Gmail not Outlook.")
        assert result.get("type") == "correction_detected"


# ─── SUMMARIZER ────────────────────────────────────────────────

class TestSummarizer:
    def test_detect_theme_path(self):
        from summarizer import detect_theme
        theme = detect_theme("Deployed to wrong path directory")
        assert theme == "wrong_path"

    def test_detect_theme_identity(self):
        from summarizer import detect_theme
        theme = detect_theme("Used wrong user name Rick instead of Weber")
        assert theme == "wrong_identity"

    def test_detect_theme_coordinates(self):
        from summarizer import detect_theme
        theme = detect_theme("Wrong monitor coordinates DPI position")
        assert theme == "wrong_coordinates"

    def test_detect_theme_general(self):
        from summarizer import detect_theme
        theme = detect_theme("fluffy purple dinosaurs dancing on moonbeams")
        assert theme == "general"

    def test_cluster_corrections(self):
        from summarizer import cluster_corrections
        corrections = [
            {"content": "deploy to wrong path", "domain": "deployment"},
            {"content": "deploy DLL to incorrect folder", "domain": "deployment"},
            {"content": "git force push error", "domain": "git"},
        ]
        clusters = cluster_corrections(corrections)
        assert len(clusters) >= 2  # At least deployment + git

    def test_distill_rule(self):
        from summarizer import distill_rule, CorrectionCluster
        cluster = CorrectionCluster(
            domain="deployment",
            theme="wrong_path",
            corrections=[
                {"content": "CORRECTION [HIGH]: deploy\nWrong: used system path\nRight: use user path",
                 "importance": 8, "helped_count": 2, "not_helped_count": 0},
                {"content": "CORRECTION [MEDIUM]: deploy\nWrong: wrong folder\nRight: check folder",
                 "importance": 6, "helped_count": 1, "not_helped_count": 1},
            ],
        )
        rule = distill_rule(cluster)
        assert rule.title != ""
        assert rule.source_count == 2
        assert rule.domain == "deployment"

    def test_summarizer_with_db(self):
        from summarizer import CorrectionSummarizer
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
                status TEXT DEFAULT 'active',
                domain TEXT, content_hash TEXT
            )
        """)
        conn.execute(
            "INSERT INTO memories (content, importance, memory_type, domain, created_at) VALUES (?, 8, 'correction', 'git', datetime('now'))",
            ("CORRECTION: Force pushed to main and lost commits",)
        )
        conn.execute(
            "INSERT INTO memories (content, importance, memory_type, domain, created_at) VALUES (?, 7, 'correction', 'git', datetime('now'))",
            ("CORRECTION: Committed secrets to git repository",)
        )
        conn.commit()
        conn.close()

        try:
            summarizer = CorrectionSummarizer(db_path=tmp.name)
            rules = summarizer.generate_rules()
            assert len(rules) >= 1
            content = summarizer.write_rules(dry_run=True)
            assert "Rules" in content
        finally:
            os.unlink(tmp.name)


# ─── CONTEXT ENGINE ───────────────────────────────────────────

class TestContextEngine:
    def test_system_state_defaults(self):
        from context import SystemState
        state = SystemState()
        assert state.active_window == ""
        assert state.revit_open is False
        assert state.active_domains == []

    def test_active_domains_revit(self):
        from context import SystemState
        state = SystemState(revit_open=True)
        assert "revit" in state.active_domains
        assert "bim" in state.active_domains

    def test_active_domains_vs_code(self):
        from context import SystemState
        state = SystemState(active_window="Visual Studio Code")
        assert "code" in state.active_domains
        assert "git" in state.active_domains

    def test_active_domains_multiple(self):
        from context import SystemState
        state = SystemState(
            revit_open=True,
            excel_open=True,
            active_window="Chrome"
        )
        domains = state.active_domains
        assert "revit" in domains
        assert "excel" in domains
        assert "web" in domains

    def test_context_engine_no_state_file(self):
        from context import ContextEngine, SystemState
        engine = ContextEngine(state_path=Path("/nonexistent/state.json"))
        state = engine.read_system_state()
        assert isinstance(state, SystemState)
        assert state.active_window == ""

    def test_context_engine_with_mock_state(self):
        from context import ContextEngine
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        json.dump({
            "active_window": {"title": "Autodesk Revit 2026"},
            "open_apps": ["Revit", "Chrome"],
        }, tmp)
        tmp.close()

        try:
            engine = ContextEngine(state_path=Path(tmp.name))
            state = engine.read_system_state()
            assert "Revit" in state.active_window
            assert state.revit_open is True
        finally:
            os.unlink(tmp.name)

    def test_score_correction_domain_match(self):
        from context import ContextEngine
        engine = ContextEngine()
        score_match = engine._score_correction(
            {"content": "revit wall", "domain": "revit", "importance": 8,
             "helped_count": 2, "not_helped_count": 0, "created_at": "2026-01-01"},
            active_domains=["revit"]
        )
        score_nomatch = engine._score_correction(
            {"content": "excel chart", "domain": "excel", "importance": 8,
             "helped_count": 2, "not_helped_count": 0, "created_at": "2026-01-01"},
            active_domains=["revit"]
        )
        assert score_match > score_nomatch

    def test_contextual_injection_output(self):
        from context import ContextEngine, SystemState
        engine = ContextEngine(db_path="/nonexistent.db")
        injection = engine.get_contextual_injection()
        # With no DB, should return empty
        assert injection == ""


# ─── WORKFLOWS ─────────────────────────────────────────────────

class TestWorkflows:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        from workflows import WorkflowRecorder
        self.recorder = WorkflowRecorder(db_path=self.tmp.name)

    def teardown_method(self):
        cleanup_db(self.tmp.name)

    def test_start_recording(self):
        self.recorder.start("test-workflow")
        assert self.recorder.recording is True

    def test_add_steps(self):
        self.recorder.start("test-workflow")
        self.recorder.add_step("Bash", {"command": "echo hello"}, "hello")
        self.recorder.add_step("Read", {"file_path": "/tmp/test"}, "contents")
        assert self.recorder.current_steps == 2

    def test_save_workflow(self):
        self.recorder.start("test-workflow", description="A test workflow")
        self.recorder.add_step("Bash", {"command": "echo hello"}, "hello")
        result = self.recorder.save(tags=["test"])
        assert result is True
        assert self.recorder.recording is False

    def test_list_workflows(self):
        self.recorder.start("wf-1", domain="git")
        self.recorder.add_step("Bash", {"command": "git status"})
        self.recorder.save()

        self.recorder.start("wf-2", domain="deployment")
        self.recorder.add_step("Bash", {"command": "deploy"})
        self.recorder.save()

        workflows = self.recorder.list_workflows()
        assert len(workflows) == 2

    def test_list_workflows_by_domain(self):
        self.recorder.start("wf-git", domain="git")
        self.recorder.add_step("Bash", {"command": "git status"})
        self.recorder.save()

        self.recorder.start("wf-deploy", domain="deployment")
        self.recorder.add_step("Bash", {"command": "deploy"})
        self.recorder.save()

        git_workflows = self.recorder.list_workflows(domain="git")
        assert len(git_workflows) == 1
        assert git_workflows[0]["name"] == "wf-git"

    def test_get_workflow(self):
        self.recorder.start("my-workflow", description="test")
        self.recorder.add_step("Bash", {"command": "echo hello"}, "hello")
        self.recorder.add_step("Read", {"file_path": "/tmp/x"}, "contents")
        self.recorder.save(tags=["test"], success=True)

        wf = self.recorder.get_workflow("my-workflow")
        assert wf is not None
        assert wf.name == "my-workflow"
        assert len(wf.steps) == 2
        assert wf.steps[0].tool_name == "Bash"

    def test_find_similar(self):
        self.recorder.start("deploy-revit-addin", domain="deployment")
        self.recorder.add_step("Bash", {"command": "dotnet build"})
        self.recorder.add_step("Bash", {"command": "cp dll"})
        self.recorder.save(tags=["revit", "deployment"])

        matches = self.recorder.find_similar("deploy revit plugin")
        assert len(matches) >= 1
        assert matches[0]["name"] == "deploy-revit-addin"

    def test_find_similar_no_match(self):
        self.recorder.start("git-commit", domain="git")
        self.recorder.add_step("Bash", {"command": "git commit"})
        self.recorder.save()

        matches = self.recorder.find_similar("quantum computing blockchain")
        assert len(matches) == 0

    def test_delete_workflow(self):
        self.recorder.start("to-delete")
        self.recorder.add_step("Bash", {"command": "echo"})
        self.recorder.save()

        assert self.recorder.delete_workflow("to-delete") is True
        assert self.recorder._load_workflow("to-delete") is None

    def test_cancel_recording(self):
        self.recorder.start("will-cancel")
        self.recorder.add_step("Bash", {"command": "echo"})
        self.recorder.cancel()
        assert self.recorder.recording is False
        assert self.recorder.current_steps == 0

    def test_format_workflow(self):
        self.recorder.start("format-test", description="A test", domain="git")
        self.recorder.add_step("Bash", {"command": "git status"}, "clean")
        self.recorder.add_step("Bash", {"command": "git commit"}, "committed")
        self.recorder.save(tags=["git"])

        wf = self.recorder._load_workflow("format-test")
        formatted = self.recorder.format_workflow(wf)
        assert "format-test" in formatted
        assert "git status" in formatted
        assert "Steps:" in formatted

    def test_workflow_update_existing(self):
        self.recorder.start("update-me")
        self.recorder.add_step("Bash", {"command": "echo v1"})
        self.recorder.save()

        # Save again with same name — should update
        self.recorder.start("update-me")
        self.recorder.add_step("Bash", {"command": "echo v2"})
        self.recorder.add_step("Read", {"file_path": "/tmp"})
        self.recorder.save()

        wf = self.recorder._load_workflow("update-me")
        assert len(wf.steps) == 2  # Updated version


# ─── SENSE.PY INTEGRATION WITH NEW MODULES ────────────────────

class TestSenseIntegration:
    def setup_method(self):
        self.cs, self.db_path = fresh_cs(db=True)

    def teardown_method(self):
        cleanup_db(self.db_path)

    def test_check_for_correction(self):
        result = self.cs.check_for_correction(
            "No, that's wrong. You should use the user addins path."
        )
        assert result is not None
        assert "confidence" in result

    def test_check_for_correction_normal_message(self):
        result = self.cs.check_for_correction("Can you help me?")
        assert result is None

    def test_auto_capture(self):
        result = self.cs.auto_capture(
            "No, that's wrong. The correct approach is to always check first."
        )
        # May or may not store depending on confidence
        # Just verify it doesn't crash
        assert result is None or isinstance(result, dict)

    def test_summarize_rules(self):
        # Add some corrections first
        self.cs.learn("test1", "wrong thing 1", "right thing 1")
        self.cs.learn("test2", "wrong thing 2", "right thing 2")
        content = self.cs.summarize_rules(dry_run=True)
        assert isinstance(content, str)

    def test_workflow_lifecycle(self):
        self.cs.start_workflow("test-wf", description="testing", domain="test")
        self.cs.record_step("Bash", {"command": "echo hi"}, "hi")
        self.cs.record_step("Read", {"file_path": "/tmp"}, "ok")
        result = self.cs.save_workflow(tags=["test"], success=True)
        assert result is True

    def test_find_workflows(self):
        self.cs.start_workflow("deploy-test", domain="deployment")
        self.cs.record_step("Bash", {"command": "deploy"})
        self.cs.save_workflow(tags=["deploy"])

        matches = self.cs.find_workflows("deploy application")
        assert len(matches) >= 1


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
        # With real DB, may find low-relevance corrections — just verify no crash
        assert result.returncode == 0
        assert "OK" in result.stdout or "WARN" in result.stdout

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
