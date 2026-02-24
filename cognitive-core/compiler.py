#!/usr/bin/env python3
"""
Learning Compiler — Turns corrections into enforced rules.

The gap in the current system: corrections are stored as memories and
*hopefully* recalled when relevant. That's weak. The compiler fixes this by:

1. Analyzing all corrections + patterns
2. Clustering related corrections into rules
3. Generating domain-specific pre-flight checklists
4. Creating compiled_rules.md that gets injected alongside kernel-corrections.md
5. Rules are ENFORCED (blocking), not just ADVISORY (memories)

Think of it as: corrections are raw data, compiled rules are the executable code.

Usage:
    from compiler import LearningCompiler
    lc = LearningCompiler()

    # Compile all learnings into rules
    rules = lc.compile()

    # Generate a pre-flight checklist for a domain
    checklist = lc.preflight("revit")

    # Get enforced rules (these block execution, not just warn)
    enforced = lc.get_enforced_rules()

    # Export to markdown for injection
    lc.export_rules_md()
"""

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "cognitive.db"
MEMORY_DB = Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db")
RULES_OUTPUT = Path(__file__).parent / "compiled_rules.md"
KERNEL_CORRECTIONS = Path("/mnt/d/_CLAUDE-TOOLS/agent-common-sense/kernel-corrections.md")


@dataclass
class Rule:
    """A compiled rule derived from one or more corrections."""
    id: str = ""
    domain: str = "general"
    level: str = "warning"           # advisory | warning | blocking
    rule: str = ""                   # The rule statement
    source_corrections: list = field(default_factory=list)  # IDs of source corrections
    evidence_count: int = 0          # How many corrections support this
    confidence: float = 0.0
    checklist_item: str = ""         # Formatted as a checklist item
    tags: list = field(default_factory=list)


@dataclass
class CompiledRules:
    """The full compiled rule set."""
    rules: list = field(default_factory=list)
    checklists: dict = field(default_factory=dict)  # domain -> list of checklist items
    total_corrections_analyzed: int = 0
    total_rules_generated: int = 0
    compiled_at: str = ""

    def to_dict(self) -> dict:
        return {
            "rules": [r.__dict__ for r in self.rules],
            "checklists": self.checklists,
            "total_corrections_analyzed": self.total_corrections_analyzed,
            "total_rules_generated": self.total_rules_generated,
            "compiled_at": self.compiled_at,
        }


# Domain keyword classifier (matches kernel_gen.py pattern)
DOMAIN_KEYWORDS = {
    "Revit / BIM": ["revit", "wall", "door", "window", "element", "family",
                    "parameter", "bim", "model", "sheet", "view", "level",
                    "grid", "room", "annotation", "category", "namedpipe",
                    "mcp_revit", "revitmcpbridge"],
    "Desktop / DPI": ["window_move", "showwindow", "dpi", "setwindowpos",
                     "monitor", "screenshot", "focus", "excel", "bluebeam",
                     "browser", "chrome", "edge"],
    "Git / Code": ["git", "commit", "branch", "merge", "push", "pull",
                  "build", "compile", "test", "deploy", "code", "function",
                  "class", "refactor"],
    "Memory / Identity": ["weber", "rick", "name", "email", "outlook",
                         "identity", "memory", "correction"],
    "Filesystem": ["path", "file", "directory", "folder", "permission",
                  "symlink", "mount"],
    "Pipeline": ["pipeline", "stage", "phase", "checkpoint", "workflow",
                "extract", "transform"],
}


class LearningCompiler:
    """Compiles corrections into enforced rules with pre-flight checklists."""

    def __init__(self, db_path: Path = DB_PATH, memory_db: Path = MEMORY_DB):
        self.db_path = db_path
        self.memory_db = memory_db
        self._ensure_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _mem_conn(self) -> Optional[sqlite3.Connection]:
        if not self.memory_db.exists():
            return None
        conn = sqlite3.connect(str(self.memory_db))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS compiled_rules (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                level TEXT DEFAULT 'warning',
                rule TEXT NOT NULL,
                source_corrections TEXT DEFAULT '[]',
                evidence_count INTEGER DEFAULT 1,
                confidence REAL DEFAULT 0.5,
                checklist_item TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS compilation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                corrections_analyzed INTEGER,
                rules_generated INTEGER,
                rules_updated INTEGER,
                rules_deprecated INTEGER,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_rules_domain ON compiled_rules(domain);
            CREATE INDEX IF NOT EXISTS idx_rules_level ON compiled_rules(level);
            CREATE INDEX IF NOT EXISTS idx_rules_active ON compiled_rules(active);
        """)
        conn.commit()
        conn.close()

    def compile(self) -> CompiledRules:
        """
        Full compilation pipeline:
        1. Read all corrections from memory DB
        2. Classify by domain
        3. Cluster related corrections
        4. Generate rules from clusters
        5. Set enforcement level based on evidence
        6. Generate pre-flight checklists
        7. Store and export
        """
        corrections = self._load_corrections()
        if not corrections:
            return CompiledRules(compiled_at=datetime.now().isoformat())

        # Classify by domain
        domain_groups = self._classify_corrections(corrections)

        # Cluster within each domain
        rules = []
        for domain, corr_list in domain_groups.items():
            clusters = self._cluster_corrections(corr_list)
            for cluster in clusters:
                rule = self._generate_rule(domain, cluster)
                if rule:
                    rules.append(rule)

        # Generate checklists
        checklists = self._generate_checklists(rules)

        # Store rules
        self._store_rules(rules)

        # Log compilation
        conn = self._conn()
        conn.execute("""
            INSERT INTO compilation_log
            (corrections_analyzed, rules_generated, rules_updated, rules_deprecated, timestamp)
            VALUES (?, ?, 0, 0, ?)
        """, (len(corrections), len(rules), datetime.now().isoformat()))
        conn.commit()
        conn.close()

        result = CompiledRules(
            rules=rules,
            checklists=checklists,
            total_corrections_analyzed=len(corrections),
            total_rules_generated=len(rules),
            compiled_at=datetime.now().isoformat(),
        )

        # Export to markdown
        self.export_rules_md(result)

        return result

    def _load_corrections(self) -> list:
        """Load all corrections from memory DB."""
        conn = self._mem_conn()
        if not conn:
            return []

        try:
            rows = conn.execute("""
                SELECT id, content, tags, importance, project,
                       COALESCE(helped_count, 0) as helped_count,
                       COALESCE(not_helped_count, 0) as not_helped_count,
                       COALESCE(domain, '') as domain,
                       created_at
                FROM memories
                WHERE memory_type = 'correction'
                AND (status IS NULL OR status != 'deprecated')
                ORDER BY importance DESC
            """).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            conn.close()
            return []

    def _classify_corrections(self, corrections: list) -> dict:
        """Group corrections by domain."""
        groups = defaultdict(list)

        for corr in corrections:
            content = corr.get("content", "").lower()
            domain = corr.get("domain", "")

            if not domain:
                # Classify from content
                domain = "General"
                best_score = 0
                for dom_name, keywords in DOMAIN_KEYWORDS.items():
                    score = sum(1 for kw in keywords if kw in content)
                    if score > best_score:
                        best_score = score
                        domain = dom_name

            groups[domain].append(corr)

        return dict(groups)

    def _cluster_corrections(self, corrections: list) -> list:
        """
        Cluster related corrections using keyword overlap.

        Returns list of clusters, where each cluster is a list of corrections
        that are related enough to form a single rule.
        """
        if len(corrections) <= 1:
            return [corrections] if corrections else []

        # Simple keyword-overlap clustering
        clusters = []
        assigned = set()

        for i, corr in enumerate(corrections):
            if i in assigned:
                continue

            cluster = [corr]
            assigned.add(i)
            words_i = set(corr.get("content", "").lower().split())

            for j, other in enumerate(corrections):
                if j in assigned:
                    continue
                words_j = set(other.get("content", "").lower().split())
                # Jaccard similarity
                intersection = len(words_i & words_j)
                union = len(words_i | words_j)
                if union > 0 and intersection / union > 0.25:
                    cluster.append(other)
                    assigned.add(j)

            clusters.append(cluster)

        return clusters

    def _generate_rule(self, domain: str, cluster: list) -> Optional[Rule]:
        """Generate a rule from a cluster of related corrections."""
        if not cluster:
            return None

        import uuid

        # Extract the common pattern
        contents = [c.get("content", "") for c in cluster]
        importance_scores = [c.get("importance", 5) for c in cluster]
        helped = sum(c.get("helped_count", 0) for c in cluster)
        not_helped = sum(c.get("not_helped_count", 0) for c in cluster)

        # Find the most representative correction (highest importance)
        best = max(cluster, key=lambda c: c.get("importance", 5))
        content = best.get("content", "")

        # Extract the "correct approach" from the content
        rule_text = content
        for prefix in ["Right:", "Correct:", "correct_approach:"]:
            if prefix in content:
                rule_text = content.split(prefix, 1)[1].strip().split("\n")[0]
                break

        if len(rule_text) > 200:
            rule_text = rule_text[:200] + "..."

        # Determine enforcement level
        avg_importance = sum(importance_scores) / len(importance_scores)
        evidence = len(cluster)

        if avg_importance >= 9 or evidence >= 5:
            level = "blocking"
        elif avg_importance >= 7 or evidence >= 3:
            level = "warning"
        else:
            level = "advisory"

        # Boost level if correction has been verified as helpful
        if helped > 3 and level == "advisory":
            level = "warning"
        if helped > 5 and level == "warning":
            level = "blocking"

        # Confidence based on evidence and feedback
        total_feedback = helped + not_helped
        if total_feedback > 0:
            confidence = helped / total_feedback
        else:
            confidence = 0.5 + (evidence * 0.1)
        confidence = min(0.99, confidence)

        # Generate checklist item
        checklist_item = f"[ ] {rule_text[:120]}"

        return Rule(
            id=uuid.uuid4().hex[:10],
            domain=domain,
            level=level,
            rule=rule_text,
            source_corrections=[c.get("id", "") for c in cluster],
            evidence_count=evidence,
            confidence=round(confidence, 2),
            checklist_item=checklist_item,
            tags=[domain.lower().replace(" / ", "-").replace(" ", "-")],
        )

    def _generate_checklists(self, rules: list) -> dict:
        """Generate domain-specific pre-flight checklists from rules."""
        checklists = defaultdict(list)

        for rule in rules:
            if rule.level in ("warning", "blocking"):
                checklists[rule.domain].append({
                    "item": rule.checklist_item,
                    "level": rule.level,
                    "rule_id": rule.id,
                })

        # Sort by level (blocking first)
        level_order = {"blocking": 0, "warning": 1, "advisory": 2}
        for domain in checklists:
            checklists[domain].sort(key=lambda x: level_order.get(x["level"], 3))

        return dict(checklists)

    def _store_rules(self, rules: list):
        """Persist compiled rules."""
        conn = self._conn()
        now = datetime.now().isoformat()

        for rule in rules:
            conn.execute("""
                INSERT OR REPLACE INTO compiled_rules
                (id, domain, level, rule, source_corrections, evidence_count,
                 confidence, checklist_item, tags, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                rule.id, rule.domain, rule.level, rule.rule,
                json.dumps(rule.source_corrections), rule.evidence_count,
                rule.confidence, rule.checklist_item, json.dumps(rule.tags),
                now, now,
            ))

        conn.commit()
        conn.close()

    def preflight(self, domain: str) -> list:
        """Get the pre-flight checklist for a domain."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT * FROM compiled_rules
            WHERE domain = ? AND active = 1
            ORDER BY
                CASE level WHEN 'blocking' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END,
                confidence DESC
        """, (domain,)).fetchall()
        conn.close()

        return [dict(r) for r in rows]

    def get_enforced_rules(self, domain: str = None) -> list:
        """Get all blocking rules (enforced, not advisory)."""
        conn = self._conn()
        sql = "SELECT * FROM compiled_rules WHERE level = 'blocking' AND active = 1"
        params = []
        if domain:
            sql += " AND domain = ?"
            params.append(domain)
        sql += " ORDER BY confidence DESC"

        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def check_against_rules(self, action: str, domain: str = None) -> dict:
        """
        Check an action against compiled rules.

        Returns: {"allowed": bool, "violations": list, "warnings": list}
        """
        rules = self.get_enforced_rules(domain) if domain else self.get_enforced_rules()
        violations = []
        warnings = []

        action_lower = action.lower()

        for rule in rules:
            rule_keywords = set(rule["rule"].lower().split()[:10])
            action_words = set(action_lower.split())
            overlap = rule_keywords & action_words

            if len(overlap) >= 2:  # Potential match
                if rule["level"] == "blocking":
                    violations.append({
                        "rule_id": rule["id"],
                        "rule": rule["rule"][:100],
                        "level": "blocking",
                    })
                else:
                    warnings.append({
                        "rule_id": rule["id"],
                        "rule": rule["rule"][:100],
                        "level": rule["level"],
                    })

        return {
            "allowed": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
        }

    def export_rules_md(self, compiled: CompiledRules = None) -> str:
        """Export compiled rules as markdown for injection into agents."""
        if compiled is None:
            conn = self._conn()
            rows = conn.execute("""
                SELECT * FROM compiled_rules WHERE active = 1
                ORDER BY domain,
                    CASE level WHEN 'blocking' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END
            """).fetchall()
            conn.close()
            rules_data = [dict(r) for r in rows]
        else:
            rules_data = [r.__dict__ for r in compiled.rules]

        lines = [
            "# Compiled Rules (Auto-Generated)",
            "",
            f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"> Total rules: {len(rules_data)}",
            "",
            "These rules are compiled from accumulated corrections.",
            "BLOCKING rules must be followed. WARNINGS should be heeded.",
            "",
        ]

        # Group by domain
        by_domain = defaultdict(list)
        for r in rules_data:
            by_domain[r.get("domain", "General")].append(r)

        for domain, rules in sorted(by_domain.items()):
            lines.append(f"## {domain}")
            lines.append("")

            for r in rules:
                level = r.get("level", "advisory").upper()
                rule_text = r.get("rule", "")[:150]
                evidence = r.get("evidence_count", 1)
                conf = r.get("confidence", 0.5)

                icon = {"BLOCKING": "!!!", "WARNING": "!!", "ADVISORY": "!"}
                lines.append(f"- **[{level}]** {rule_text}")
                lines.append(f"  Evidence: {evidence} corrections, confidence: {conf:.0%}")
                lines.append("")

        content = "\n".join(lines)

        # Write to file
        RULES_OUTPUT.write_text(content)
        return content

    def get_stats(self) -> dict:
        """Get compilation statistics."""
        conn = self._conn()
        total = conn.execute("SELECT COUNT(*) FROM compiled_rules WHERE active = 1").fetchone()[0]
        by_level = dict(conn.execute("""
            SELECT level, COUNT(*) FROM compiled_rules WHERE active = 1 GROUP BY level
        """).fetchall())
        by_domain = dict(conn.execute("""
            SELECT domain, COUNT(*) FROM compiled_rules WHERE active = 1 GROUP BY domain
        """).fetchall())

        last_compile = conn.execute(
            "SELECT * FROM compilation_log ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        conn.close()

        return {
            "total_active_rules": total,
            "by_level": by_level,
            "by_domain": by_domain,
            "last_compilation": dict(last_compile) if last_compile else None,
        }


# ── CLI ──────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Learning Compiler")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("compile", help="Compile corrections into rules")
    pf = sub.add_parser("preflight", help="Get pre-flight checklist")
    pf.add_argument("domain", help="Domain name")
    sub.add_parser("enforced", help="Show all blocking rules")
    sub.add_parser("stats", help="Compilation statistics")
    chk = sub.add_parser("check", help="Check action against rules")
    chk.add_argument("action", help="Action to check")
    chk.add_argument("--domain", default=None)
    sub.add_parser("export", help="Export rules to markdown")

    args = parser.parse_args()
    lc = LearningCompiler()

    if args.command == "compile":
        result = lc.compile()
        print(f"Analyzed {result.total_corrections_analyzed} corrections")
        print(f"Generated {result.total_rules_generated} rules")
        for domain, items in result.checklists.items():
            print(f"\n  {domain}: {len(items)} checklist items")
        print(f"\nRules exported to: {RULES_OUTPUT}")

    elif args.command == "preflight":
        items = lc.preflight(args.domain)
        if items:
            print(f"Pre-flight checklist for {args.domain}:")
            for item in items:
                level = item['level'].upper()
                print(f"  [{level}] {item['rule'][:80]}")
        else:
            print(f"No rules for domain: {args.domain}")

    elif args.command == "enforced":
        rules = lc.get_enforced_rules()
        print(f"Blocking rules ({len(rules)}):")
        for r in rules:
            print(f"  [{r['domain']}] {r['rule'][:80]} (conf: {r['confidence']:.0%})")

    elif args.command == "check":
        result = lc.check_against_rules(args.action, args.domain)
        if result["allowed"]:
            print("ALLOWED")
            if result["warnings"]:
                print(f"  Warnings: {len(result['warnings'])}")
                for w in result["warnings"]:
                    print(f"    - {w['rule']}")
        else:
            print("BLOCKED")
            for v in result["violations"]:
                print(f"  - {v['rule']}")

    elif args.command == "stats":
        stats = lc.get_stats()
        for k, v in stats.items():
            print(f"  {k}: {v}")

    elif args.command == "export":
        content = lc.export_rules_md()
        print(f"Exported {len(content)} chars to {RULES_OUTPUT}")


if __name__ == "__main__":
    main()
