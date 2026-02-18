"""
Common Sense Engine v2.0
========================
Gives any agent experiential judgment through accumulated corrections,
pluggable search, outcome tracking, and domain modules.

Changes from v1.0:
  - Pluggable search backends (keyword, TF-IDF, embeddings, hybrid)
  - Outcome tracking (correction_helped, effectiveness scoring)
  - Deduplication on store
  - Temporal decay scoring
  - Correction lifecycle (draft → active → reinforced → deprecated)
  - Domain module system
  - Quality validation on store
  - DB schema auto-migration

Usage:
    from sense import CommonSense

    cs = CommonSense(project="my-project")

    # Before doing something
    result = cs.before("deploy to /opt/app")
    if result.blocked:
        print(f"STOP: {result.reason}")
    elif result.warnings:
        print(f"CAUTION: {result.warnings}")

    # After something goes wrong
    cs.learn(
        action="deployed to /opt/app",
        what_went_wrong="wrong path, should be /opt/app-v2",
        correct_approach="always check the symlink target first"
    )

    # Record outcome
    cs.correction_helped(correction_id=42, helped=True, notes="caught the wrong path")

    # After catching yourself
    cs.avoided("almost deployed to /opt/app, caught it and used /opt/app-v2")
"""

import json
import sqlite3
import sys
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

SEEDS_PATH = Path(__file__).parent / "seeds.json"
_SEEDS_CACHE = None  # In-memory cache of parsed seeds


@dataclass
class ActionCheck:
    """Result of checking an action against experience."""
    blocked: bool = False
    reason: str = ""
    warnings: list = field(default_factory=list)
    corrections: list = field(default_factory=list)
    confidence: float = 1.0

    @property
    def safe(self) -> bool:
        return not self.blocked and not self.warnings


class CommonSense:
    """
    Experiential judgment engine for agents.

    Provides:
    - Pre-action checks against past mistakes (with pluggable search)
    - Post-action learning with dedup and validation
    - Outcome tracking (did corrections actually help?)
    - Seed knowledge from domain modules
    - Pattern synthesis across corrections
    - Correction lifecycle management
    """

    def __init__(self, project: str = "general", db_path: Optional[str] = None,
                 search_backend: str = "auto", domains: list[str] = None):
        """
        Args:
            project: Project context for scoping corrections
            db_path: Path to SQLite database (auto-detected if None)
            search_backend: "auto", "keyword", "tfidf", or "embedding"
            domains: List of domain names to load (all if None)
        """
        self.project = project
        self.db_path = db_path or self._find_db()
        self._seeds_loaded = False
        self._search = None
        self._search_backend_name = search_backend
        self._feedback = None
        self._domain_loader = None
        self._active_domains = domains

        # Initialize subsystems
        if self.db_path:
            self._init_search(search_backend)
            self._init_feedback()
            self._ensure_schema()

    def _find_db(self) -> Optional[str]:
        """Locate the claude-memory SQLite database."""
        candidates = [
            Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"),
            Path.home() / ".claude-memory" / "memories.db",
            Path("/mnt/d/_CLAUDE-TOOLS/claude-memory/memories.db"),
            Path.home() / ".claude" / "memory.db",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return None

    def _init_search(self, backend_name: str):
        """Initialize the search backend."""
        try:
            from search import get_best_backend, get_backend_by_name
            if backend_name == "auto":
                self._search = get_best_backend(self.db_path)
            else:
                self._search = get_backend_by_name(backend_name, self.db_path)
        except Exception:
            self._search = None

    def _init_feedback(self):
        """Initialize the feedback tracker."""
        try:
            from feedback import FeedbackTracker
            self._feedback = FeedbackTracker(self.db_path)
        except ImportError:
            self._feedback = None

    def _ensure_schema(self):
        """Run DB schema migrations for new columns."""
        if not self.db_path:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("PRAGMA table_info(memories)")
            existing_cols = {row[1] for row in cursor.fetchall()}

            migrations = {
                "helped_count": "ALTER TABLE memories ADD COLUMN helped_count INTEGER DEFAULT 0",
                "not_helped_count": "ALTER TABLE memories ADD COLUMN not_helped_count INTEGER DEFAULT 0",
                "last_helped": "ALTER TABLE memories ADD COLUMN last_helped TEXT",
                "status": "ALTER TABLE memories ADD COLUMN status TEXT DEFAULT 'active'",
                "domain": "ALTER TABLE memories ADD COLUMN domain TEXT",
                "content_hash": "ALTER TABLE memories ADD COLUMN content_hash TEXT",
            }

            for col, sql in migrations.items():
                if col not in existing_cols:
                    try:
                        conn.execute(sql)
                    except sqlite3.OperationalError:
                        pass

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Schema migration: {e}", file=sys.stderr)

    # ─── PRE-ACTION CHECK ───────────────────────────────────────

    def before(self, action: str, context: str = "") -> ActionCheck:
        """
        Check an action against accumulated experience.

        Call this BEFORE doing anything significant.
        Returns an ActionCheck with go/no-go and any warnings.

        Uses three search strategies:
        1. Direct seed matching (fast, no DB)
        2. Pluggable search backend (keyword/TF-IDF/embedding/hybrid)
        3. Classification heuristics
        """
        result = ActionCheck()

        # Load seeds on first check
        if not self._seeds_loaded:
            self._ensure_seeds()

        # Classify the action
        classification = self._classify(action)

        # Search for relevant corrections
        corrections = self._recall_corrections(action, context)

        if corrections:
            result.corrections = corrections
            for c in corrections:
                severity = c.get("severity", "medium")
                approach = c.get("correct_approach", c.get("content", ""))
                if severity == "critical":
                    result.blocked = True
                    result.reason = f"BLOCKED by [{c.get('id', 'correction')}]: {approach}"
                    result.confidence = 0.0
                    break
                elif severity == "high":
                    result.warnings.append(f"[HIGH] {approach}")
                    result.confidence = min(result.confidence, 0.3)
                else:
                    result.warnings.append(approach)

        # Apply classification heuristics
        if classification["destructive"] and not corrections:
            result.warnings.append("This looks destructive and has no prior experience. Confirm before proceeding.")
            result.confidence = 0.5

        if classification["shared_state"]:
            result.warnings.append("This affects shared state. Verify target.")
            result.confidence = min(result.confidence, 0.7)

        if classification["unfamiliar"]:
            result.confidence = min(result.confidence, 0.6)

        return result

    def _classify(self, action: str) -> dict:
        """Classify an action by risk profile."""
        action_lower = action.lower()

        destructive_signals = [
            "delete", "remove", "drop", "truncate", "rm ", "rm -",
            "overwrite", "force", "reset --hard", "clean -f",
            "wipe", "destroy", "purge"
        ]

        shared_signals = [
            "push", "deploy", "publish", "send", "email",
            "post", "merge", "release", "broadcast", "notify"
        ]

        return {
            "destructive": any(s in action_lower for s in destructive_signals),
            "shared_state": any(s in action_lower for s in shared_signals),
            "unfamiliar": not self._has_precedent(action),
            "reversible": not any(s in action_lower for s in destructive_signals + shared_signals),
        }

    def _has_precedent(self, action: str) -> bool:
        """Check if we've done something like this before successfully."""
        if self._search and self.db_path:
            try:
                results = self._search.search(action, memory_type="context", limit=1)
                return len(results) > 0
            except Exception:
                pass
        return False

    # ─── POST-ACTION LEARNING ──────────────────────────────────

    def learn(self, action: str, what_went_wrong: str, correct_approach: str,
              category: str = "execution", severity: str = "medium",
              tags: Optional[list] = None):
        """
        Store a correction from a mistake or user feedback.

        Includes deduplication and validation. Returns the stored correction
        or None if it was a duplicate/invalid.
        """
        content = (
            f"CORRECTION [{severity.upper()}]: {action}\n"
            f"Wrong: {what_went_wrong}\n"
            f"Right: {correct_approach}\n"
            f"Domain: {category}"
        )

        # Validate before storing
        try:
            from quality import validate_correction
            result = validate_correction({"content": content, "category": category,
                                          "importance": self._severity_to_importance(severity)})
            if not result.valid:
                print(f"Correction rejected: {result.errors}", file=sys.stderr)
                return None
        except ImportError:
            pass

        # Check for duplicates
        if self.db_path:
            try:
                from quality import find_duplicates
                dupes = find_duplicates(self.db_path, content, threshold=0.6,
                                        memory_type="correction")
                if dupes:
                    # Update existing instead of creating duplicate
                    from quality import merge_corrections
                    existing = dupes[0]
                    merged = merge_corrections(
                        existing,
                        {"content": content, "tags": json.dumps(tags or []),
                         "importance": self._severity_to_importance(severity)}
                    )
                    conn = sqlite3.connect(self.db_path)
                    conn.execute(
                        "UPDATE memories SET content=?, tags=?, importance=? WHERE id=?",
                        (merged["content"], merged["tags"], merged["importance"],
                         merged["id"])
                    )
                    conn.commit()
                    conn.close()
                    self._invalidate_search()
                    return merged
            except ImportError:
                pass

        # Store as new correction
        all_tags = ["correction", "common-sense", category, severity]
        if tags:
            all_tags.extend(tags)

        importance = self._severity_to_importance(severity)

        # Generate content hash for future dedup
        try:
            from quality import content_hash
            c_hash = content_hash(content)
        except ImportError:
            c_hash = None

        self._store_memory(content, tags=all_tags, importance=importance,
                           domain=category, content_hash=c_hash)
        self._invalidate_search()

        return {"content": content, "importance": importance, "domain": category}

    def avoided(self, description: str):
        """Log that a known mistake was successfully avoided."""
        content = f"AVOIDED MISTAKE: {description}"
        self._store_memory(
            content,
            tags=["avoided-mistake", "common-sense", "positive"],
            importance=5
        )

    def succeeded(self, action: str, context: str = ""):
        """Log a successful action as a known-good pattern."""
        content = f"KNOWN GOOD: {action}"
        if context:
            content += f"\nContext: {context}"
        self._store_memory(
            content,
            tags=["known-good", "common-sense", "positive"],
            importance=4
        )

    # ─── OUTCOME TRACKING ─────────────────────────────────────

    def correction_helped(self, correction_id: int, helped: bool,
                          notes: str = "") -> bool:
        """Record whether a surfaced correction actually helped.

        This closes the feedback loop. Corrections that help get reinforced,
        corrections that don't help get deprioritized.
        """
        if self._feedback:
            return self._feedback.correction_helped(correction_id, helped, notes)

        # Fallback: direct DB update
        if not self.db_path:
            return False
        try:
            conn = sqlite3.connect(self.db_path)
            if helped:
                conn.execute(
                    "UPDATE memories SET helped_count = COALESCE(helped_count, 0) + 1 WHERE id = ?",
                    (correction_id,)
                )
            else:
                conn.execute(
                    "UPDATE memories SET not_helped_count = COALESCE(not_helped_count, 0) + 1 WHERE id = ?",
                    (correction_id,)
                )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Feedback failed: {e}", file=sys.stderr)
            return False

    def get_effectiveness(self, correction_id: int) -> dict:
        """Get effectiveness stats for a correction."""
        if self._feedback:
            return self._feedback.get_effectiveness(correction_id)
        return {"error": "Feedback tracker not initialized"}

    def get_feedback_summary(self) -> dict:
        """Get overall summary of how corrections are performing."""
        if self._feedback:
            return self._feedback.get_feedback_summary()
        return {"error": "Feedback tracker not initialized"}

    # ─── SEED & DOMAIN MANAGEMENT ─────────────────────────────

    def _ensure_seeds(self):
        """Load seed corrections into the in-memory cache."""
        global _SEEDS_CACHE
        if _SEEDS_CACHE is not None:
            self._seeds_loaded = True
            return

        # Try loading from domain modules first
        try:
            from domains import DomainLoader
            self._domain_loader = DomainLoader()
            if self._active_domains:
                corrections = self._domain_loader.get_all_corrections(self._active_domains)
            else:
                corrections = self._domain_loader.get_all_corrections()
            _SEEDS_CACHE = corrections
        except ImportError:
            # Fallback to seeds.json
            if SEEDS_PATH.exists():
                with open(SEEDS_PATH) as f:
                    _SEEDS_CACHE = json.load(f).get("corrections", [])
            else:
                _SEEDS_CACHE = []

        self._seeds_loaded = True

    def seed(self, seeds_path: Optional[str] = None):
        """Load pre-built corrections into the database."""
        path = Path(seeds_path) if seeds_path else SEEDS_PATH
        if not path.exists():
            print(f"Seeds file not found: {path}")
            return 0

        with open(path) as f:
            data = json.load(f)

        count = 0
        for correction in data.get("corrections", []):
            content = (
                f"SEED CORRECTION [{correction['id']}]: {correction.get('domain', 'general')}\n"
                f"What goes wrong: {correction['what_went_wrong']}\n"
                f"Correct approach: {correction['correct_approach']}\n"
                f"Detection: {correction['detection']}"
            )

            tags = ["seed", "common-sense", "correction"] + correction.get("tags", [])
            importance = self._severity_to_importance(correction.get("severity", "medium"))

            self._store_memory(content, tags=tags, importance=importance,
                               domain=correction.get("domain", "general"))
            count += 1

        self._invalidate_search()
        print(f"Seeded {count} corrections")
        return count

    # ─── PATTERN SYNTHESIS ─────────────────────────────────────

    def synthesize(self) -> list:
        """Analyze accumulated corrections for patterns.

        Uses the kernel_gen domain classifier for more accurate grouping.
        Returns clusters of related corrections with insights.
        """
        try:
            from kernel_gen import classify_domain
            use_classifier = True
        except ImportError:
            use_classifier = False

        # Get all corrections
        if self._search and self.db_path:
            try:
                from search import KeywordSearch
                kw = KeywordSearch(self.db_path)
                corrections = kw.search("CORRECTION", limit=200, status=None)
                correction_data = [{"content": r.content, "id": r.id} for r in corrections]
            except Exception:
                correction_data = self._memory_search("CORRECTION", memory_type="correction")
        else:
            correction_data = self._memory_search("CORRECTION", memory_type="correction")

        # Group by domain
        domains = {}
        for c in correction_data:
            content = c.get("content", c.content if hasattr(c, 'content') else "")
            if use_classifier:
                domain = classify_domain(content)
            else:
                domain = "General"
                for d in ["filesystem", "git", "network", "execution", "scope",
                          "deployment", "data", "identity"]:
                    if d in content.lower():
                        domain = d
                        break

            domains.setdefault(domain, []).append(content)

        patterns = []
        for domain, items in domains.items():
            if len(items) >= 2:
                patterns.append({
                    "domain": domain,
                    "count": len(items),
                    "insight": f"Recurring issues in {domain} ({len(items)} corrections). Review and consider adding a pre-check.",
                    "items": items[:5]
                })

        return sorted(patterns, key=lambda p: p["count"], reverse=True)

    # ─── QUALITY MANAGEMENT ────────────────────────────────────

    def cleanup(self, dry_run: bool = True) -> dict:
        """Run quality cleanup on the database.

        Removes fragments, deduplicates, auto-transitions lifecycle.
        Use dry_run=True to preview changes before applying.
        """
        if not self.db_path:
            return {"error": "No database configured"}
        try:
            from quality import cleanup_database
            result = cleanup_database(self.db_path, dry_run=dry_run)
            if not dry_run:
                self._invalidate_search()
            return result
        except ImportError:
            return {"error": "quality module not available"}

    def get_stale(self, days: int = 90) -> list:
        """Get corrections that are old and never been validated."""
        if self._feedback:
            return self._feedback.get_stale_corrections(days=days)
        return []

    # ─── INTERNALS ─────────────────────────────────────────────

    def _recall_corrections(self, action: str, context: str = "") -> list:
        """Search for corrections relevant to this action.

        Uses three strategies in order:
        1. Direct seed matching (fast, no DB needed)
        2. Pluggable search backend (best available)
        3. Keyword fallback (if search backend unavailable)
        """
        results = []

        # Strategy 1: Match directly against seed detection patterns
        seed_matches = self._match_seeds(action)
        results.extend(seed_matches)

        # Strategy 2: Use pluggable search backend
        query = f"{action} {context}".strip()
        if self._search and self.db_path:
            try:
                search_results = self._search.search(
                    query, memory_type="correction",
                    project=self.project, limit=10
                )
                # Deduplicate against seed matches
                seen = {r.get("id", r.get("correct_approach", "")) for r in results}
                for r in search_results:
                    key = str(r.id) if hasattr(r, 'id') else r.get("id", "")
                    content = r.content if hasattr(r, 'content') else r.get("content", "")
                    if key not in seen:
                        results.append({
                            "id": key,
                            "content": content,
                            "correct_approach": content,
                            "severity": "medium",
                            "score": r.score if hasattr(r, 'score') else 0,
                        })
                        seen.add(key)
            except Exception as e:
                print(f"Search backend error: {e}", file=sys.stderr)
                # Fall through to keyword fallback
                self._keyword_fallback(query, results)
        else:
            # Strategy 3: Keyword fallback
            self._keyword_fallback(query, results)

        return results

    def _keyword_fallback(self, query: str, results: list):
        """Fallback to keyword search when no search backend is available."""
        try:
            db_results = self._keyword_search(query, memory_type="correction")
            seen = {r.get("id", r.get("correct_approach", "")) for r in results}
            for r in db_results:
                key = r.get("id", r.get("correct_approach", r.get("content", "")))
                if key not in seen:
                    results.append(r)
                    seen.add(key)
        except Exception:
            pass

    def _match_seeds(self, action: str) -> list:
        """Match an action directly against seed detection patterns. No DB needed."""
        global _SEEDS_CACHE

        if _SEEDS_CACHE is None:
            if SEEDS_PATH.exists():
                with open(SEEDS_PATH) as f:
                    _SEEDS_CACHE = json.load(f).get("corrections", [])
            else:
                _SEEDS_CACHE = []

        action_lower = action.lower()
        action_words = set(action_lower.split())
        matches = []

        for seed in _SEEDS_CACHE:
            detection = seed.get("detection", "").lower()

            # Check detection keywords against action
            detection_words = set(detection.replace(",", " ").replace("/", " ").split())
            overlap = action_words & detection_words
            # Also check for substring matches (phrases like "rm -rf")
            phrase_match = any(phrase.strip() in action_lower
                              for phrase in detection.split(",") if len(phrase.strip()) > 2)

            if len(overlap) >= 2 or phrase_match:
                matches.append({
                    "id": seed.get("id", "seed"),
                    "content": f"SEED: {seed.get('what_went_wrong', '')}",
                    "correct_approach": seed.get("correct_approach", ""),
                    "severity": seed.get("severity", "medium"),
                    "domain": seed.get("domain", seed.get("_domain", "general")),
                })

        return matches

    def _keyword_search(self, query: str, memory_type: str = None) -> list:
        """Keyword-decomposed SQLite search (fallback when no search backend)."""
        if not self.db_path:
            return []

        stop_words = {"a", "an", "the", "to", "in", "on", "at", "is", "it",
                      "of", "and", "or", "all", "for"}
        keywords = [w for w in query.lower().split() if len(w) > 2 and w not in stop_words]

        if not keywords:
            return self._search_sqlite(query, memory_type)

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            like_clauses = " OR ".join(["content LIKE ?" for _ in keywords])
            score_expr = " + ".join(["(content LIKE ?)" for _ in keywords])
            sql = f"SELECT *, ({score_expr}) as match_score FROM memories WHERE ({like_clauses})"
            params = [f"%{kw}%" for kw in keywords] * 2

            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type)

            if self.project and self.project != "general":
                sql += " AND (project = ? OR project IS NULL OR project = 'general')"
                params.append(self.project)

            sql += " AND (status IS NULL OR status != 'deprecated')"
            sql += " ORDER BY match_score DESC, importance DESC LIMIT 10"

            cursor = conn.execute(sql, params)
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results
        except Exception as e:
            print(f"Keyword search failed: {e}", file=sys.stderr)
            return self._search_sqlite(query, memory_type)

    def _memory_search(self, query: str, memory_type: str = None) -> list:
        """Generic memory search."""
        if self.db_path:
            return self._search_sqlite(query, memory_type)
        return []

    def _search_sqlite(self, query: str, memory_type: str = None) -> list:
        """Direct SQLite LIKE search (simplest fallback)."""
        if not self.db_path:
            return []
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            sql = "SELECT * FROM memories WHERE content LIKE ?"
            params = [f"%{query}%"]

            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type)

            if self.project and self.project != "general":
                sql += " AND (project = ? OR project IS NULL OR project = 'general')"
                params.append(self.project)

            sql += " ORDER BY importance DESC, created_at DESC LIMIT 10"

            cursor = conn.execute(sql, params)
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results
        except Exception as e:
            print(f"SQLite search failed: {e}", file=sys.stderr)
            return []

    def _store_memory(self, content: str, tags: list = None, importance: int = 5,
                      domain: str = None, content_hash: str = None):
        """Store a memory entry with optional domain and hash."""
        if not self.db_path:
            return

        try:
            conn = sqlite3.connect(self.db_path)

            # Check which columns exist for backward compat
            cursor = conn.execute("PRAGMA table_info(memories)")
            cols = {row[1] for row in cursor.fetchall()}

            if "domain" in cols and "content_hash" in cols:
                conn.execute(
                    """INSERT INTO memories
                       (content, tags, importance, project, memory_type, created_at,
                        domain, content_hash, status)
                       VALUES (?, ?, ?, ?, 'correction', datetime('now'), ?, ?, 'active')""",
                    (content, json.dumps(tags or []), importance, self.project,
                     domain, content_hash)
                )
            else:
                conn.execute(
                    """INSERT INTO memories
                       (content, tags, importance, project, memory_type, created_at)
                       VALUES (?, ?, ?, ?, 'correction', datetime('now'))""",
                    (content, json.dumps(tags or []), importance, self.project)
                )

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Store failed: {e}", file=sys.stderr)

    def _invalidate_search(self):
        """Notify search backend that data changed."""
        if self._search and hasattr(self._search, 'invalidate'):
            self._search.invalidate()

    @staticmethod
    def _severity_to_importance(severity: str) -> int:
        return {"critical": 10, "high": 8, "medium": 6, "low": 4}.get(severity, 5)


# ─── STANDALONE CLI ─────────────────────────────────────────────

def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Common Sense Engine v2.0")
    parser.add_argument("command",
                        choices=["seed", "synthesize", "check", "cleanup",
                                 "feedback", "stale"],
                        help="Command to run")
    parser.add_argument("--project", default="general", help="Project context")
    parser.add_argument("--action", help="Action to check")
    parser.add_argument("--db", help="Path to memory SQLite database")
    parser.add_argument("--seeds", help="Path to seeds JSON file")
    parser.add_argument("--backend", default="auto",
                        choices=["auto", "keyword", "tfidf", "embedding"],
                        help="Search backend")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without making changes")
    parser.add_argument("--days", type=int, default=90,
                        help="Days threshold for stale corrections")

    args = parser.parse_args()
    cs = CommonSense(project=args.project, db_path=args.db,
                     search_backend=args.backend)

    if args.command == "seed":
        count = cs.seed(args.seeds)
        print(f"Done. {count} corrections loaded.")

    elif args.command == "synthesize":
        patterns = cs.synthesize()
        if patterns:
            for p in patterns:
                print(f"\n[{p['domain'].upper()}] {p['count']} corrections")
                print(f"  Insight: {p['insight']}")
                for item in p["items"]:
                    preview = item[:100] if isinstance(item, str) else str(item)[:100]
                    print(f"    - {preview}...")
        else:
            print("No patterns found yet. Need more corrections.")

    elif args.command == "check":
        if not args.action:
            print("--action required for check command")
            sys.exit(1)
        result = cs.before(args.action)
        if result.blocked:
            print(f"BLOCKED: {result.reason}")
        elif result.warnings:
            print(f"WARNINGS ({len(result.warnings)}):")
            for w in result.warnings:
                print(f"  - {w}")
        else:
            print(f"OK (confidence: {result.confidence:.0%})")
        if result.corrections:
            print(f"\nCorrections surfaced: {len(result.corrections)}")
            for c in result.corrections:
                print(f"  [{c.get('severity', '?')}] {c.get('id', '?')}: "
                      f"{c.get('correct_approach', c.get('content', ''))[:80]}")

    elif args.command == "cleanup":
        result = cs.cleanup(dry_run=args.dry_run)
        prefix = "[DRY RUN] " if args.dry_run else ""
        print(f"{prefix}Cleanup results:")
        for k, v in result.items():
            print(f"  {k}: {v}")

    elif args.command == "feedback":
        summary = cs.get_feedback_summary()
        print("Feedback Summary:")
        for k, v in summary.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.1%}")
            else:
                print(f"  {k}: {v}")

    elif args.command == "stale":
        stale = cs.get_stale(days=args.days)
        print(f"Stale corrections (>{args.days} days, never tested): {len(stale)}")
        for s in stale[:20]:
            print(f"  [{s.get('id', '?')}] {s.get('content', '')[:80]}...")


if __name__ == "__main__":
    main()
