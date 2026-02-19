"""
Correction summarizer for the Common Sense Engine.

Clusters corrections by topic, finds recurring patterns, and distills
them into concise high-level rules. Reduces noise by merging 10 similar
corrections into 1 clear rule.

Output:
  - kernel-rules.md: auto-generated high-level rules
  - Can be injected alongside kernel.md for sub-agents

Usage:
    from summarizer import CorrectionSummarizer

    summarizer = CorrectionSummarizer(db_path)
    rules = summarizer.generate_rules()
    summarizer.write_rules()

CLI:
    python summarizer.py                    # Generate kernel-rules.md
    python summarizer.py --dry-run          # Preview only
    python summarizer.py --stats            # Show clustering stats
"""

import json
import re
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


OUTPUT_PATH = Path(__file__).parent / "kernel-rules.md"


@dataclass
class Rule:
    """A distilled rule from a cluster of corrections."""
    title: str
    description: str
    domain: str
    source_count: int  # How many corrections this was derived from
    severity: str = "medium"
    examples: list = field(default_factory=list)
    effectiveness: float = 0.0  # Average effectiveness of source corrections


@dataclass
class CorrectionCluster:
    """A group of related corrections."""
    domain: str
    theme: str  # Common theme/topic
    corrections: list = field(default_factory=list)
    keywords: set = field(default_factory=set)


# ─── CLUSTERING ──────────────────────────────────────────────────

# Theme detection patterns — groups of keywords that indicate a theme
THEME_PATTERNS = {
    "wrong_path": ["path", "directory", "folder", "deploy", "install", "location"],
    "wrong_identity": ["name", "user", "identity", "rick", "weber", "email", "account"],
    "wrong_tool": ["tool", "browser", "click", "api", "mcp", "method", "instead"],
    "wrong_coordinates": ["coordinate", "position", "location", "x=", "y=", "monitor",
                          "dpi", "screen", "window"],
    "wrong_parameters": ["parameter", "params", "argument", "key", "value", "format"],
    "missing_verification": ["verify", "check", "confirm", "screenshot", "visual",
                              "validate", "before"],
    "wrong_sequence": ["first", "before", "after", "order", "sequence", "step", "then"],
    "wrong_assumption": ["assumed", "guessed", "invented", "without checking",
                          "without verifying"],
    "wrong_attribution": ["attributed", "firm", "architect", "client", "author", "credit"],
    "api_misuse": ["api", "method", "call", "null", "reference", "exception", "error",
                    "failed"],
    "scale_units": ["feet", "inches", "millimeters", "scale", "size", "thickness",
                     "dimension"],
}


def detect_theme(content: str) -> str:
    """Detect the theme of a correction based on keyword analysis."""
    content_lower = content.lower()
    scores = {}

    for theme, keywords in THEME_PATTERNS.items():
        score = sum(1 for kw in keywords if kw in content_lower)
        if score > 0:
            scores[theme] = score

    if scores:
        return max(scores, key=scores.get)
    return "general"


def cluster_corrections(corrections: list[dict], threshold: float = 0.4) -> list[CorrectionCluster]:
    """Group corrections into clusters by domain and theme.

    Uses keyword overlap and domain classification.
    """
    # First pass: group by domain
    by_domain = defaultdict(list)
    for c in corrections:
        domain = c.get("domain", "general")
        if not domain:
            # Try to classify
            try:
                from kernel_gen import classify_domain
                domain = classify_domain(c.get("content", ""))
            except ImportError:
                domain = "general"
        by_domain[domain].append(c)

    # Second pass: sub-group by theme within each domain
    clusters = []
    for domain, domain_corrections in by_domain.items():
        theme_groups = defaultdict(list)

        for c in domain_corrections:
            content = c.get("content", "")
            theme = detect_theme(content)
            theme_groups[theme].append(c)

        for theme, items in theme_groups.items():
            # Extract common keywords
            all_words = set()
            for item in items:
                words = set(re.findall(r'[a-z]{3,}', item.get("content", "").lower()))
                all_words.update(words)

            cluster = CorrectionCluster(
                domain=domain,
                theme=theme,
                corrections=items,
                keywords=all_words,
            )
            clusters.append(cluster)

    return clusters


# ─── RULE DISTILLATION ──────────────────────────────────────────

def distill_rule(cluster: CorrectionCluster) -> Rule:
    """Distill a cluster of corrections into a single concise rule.

    Extracts the common pattern and creates an actionable rule.
    """
    corrections = cluster.corrections

    # Extract the "correct approach" from each correction
    approaches = []
    wrong_actions = []

    for c in corrections:
        content = c.get("content", "")

        # Try to extract structured parts
        right_match = re.search(r'(?:Right|Correct|Do instead)[:\s]+(.+?)(?:\n|$)',
                                content, re.IGNORECASE)
        wrong_match = re.search(r'(?:Wrong|WRONG)[:\s]+(.+?)(?:\n|$)',
                                content, re.IGNORECASE)

        if right_match:
            approaches.append(right_match.group(1).strip())
        if wrong_match:
            wrong_actions.append(wrong_match.group(1).strip())

        # Fallback: use the full content
        if not right_match:
            # Clean and truncate
            clean = re.sub(r'CORRECTION\s*\[.*?\]:\s*', '', content)
            clean = re.sub(r'SEED\s+CORRECTION\s*\[.*?\]:\s*', '', clean)
            clean = clean.strip()
            if clean:
                approaches.append(clean[:150])

    # Build rule title from theme
    theme_titles = {
        "wrong_path": "Verify target paths before operations",
        "wrong_identity": "Use correct identities and names",
        "wrong_tool": "Use the right tool for the job",
        "wrong_coordinates": "Use DPI-aware coordinates and verify positions",
        "wrong_parameters": "Check parameter names and formats",
        "missing_verification": "Always verify results visually",
        "wrong_sequence": "Follow correct operation order",
        "wrong_assumption": "Never assume — always verify",
        "wrong_attribution": "Verify attribution and ownership",
        "api_misuse": "Check API requirements before calling",
        "scale_units": "Verify units and scale factors",
        "general": f"Common issues in {cluster.domain}",
    }

    title = theme_titles.get(cluster.theme,
                              f"Rule for {cluster.domain}/{cluster.theme}")

    # Build description from the most common approaches
    if approaches:
        # Deduplicate similar approaches
        unique_approaches = []
        for a in approaches:
            if not any(_simple_similarity(a, u) > 0.6 for u in unique_approaches):
                unique_approaches.append(a)

        description = "; ".join(unique_approaches[:3])
    else:
        description = f"Multiple corrections found in {cluster.domain}"

    # Calculate average effectiveness
    total_helped = sum(c.get("helped_count", 0) or 0 for c in corrections)
    total_not = sum(c.get("not_helped_count", 0) or 0 for c in corrections)
    total = total_helped + total_not
    effectiveness = total_helped / total if total > 0 else 0.5

    # Determine severity from highest in cluster
    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    max_severity = "medium"
    for c in corrections:
        content = c.get("content", "").upper()
        for sev in ["CRITICAL", "HIGH"]:
            if sev in content:
                if severity_order.get(sev.lower(), 0) > severity_order.get(max_severity, 0):
                    max_severity = sev.lower()

    # Build examples (top 2 most important)
    sorted_corrections = sorted(corrections,
                                 key=lambda c: c.get("importance", 5),
                                 reverse=True)
    examples = []
    for c in sorted_corrections[:2]:
        ex = c.get("content", "")[:150]
        ex = re.sub(r'CORRECTION\s*\[.*?\]:\s*', '', ex).strip()
        if ex:
            examples.append(ex)

    return Rule(
        title=title,
        description=description,
        domain=cluster.domain,
        source_count=len(corrections),
        severity=max_severity,
        examples=examples,
        effectiveness=effectiveness,
    )


def _simple_similarity(a: str, b: str) -> float:
    """Quick word-overlap similarity."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


# ─── MAIN SUMMARIZER ────────────────────────────────────────────

class CorrectionSummarizer:
    """Summarizes corrections into high-level rules."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._find_db()
        self.rules: list[Rule] = []
        self.stats: dict = {}

    def _find_db(self) -> str:
        candidates = [
            Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"),
            Path.home() / ".claude-memory" / "memories.db",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return ""

    def generate_rules(self) -> list[Rule]:
        """Generate high-level rules from all corrections in the database."""
        if not self.db_path:
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            # Check which columns exist
            cursor = conn.execute("PRAGMA table_info(memories)")
            cols = {row[1] for row in cursor.fetchall()}

            sql = "SELECT * FROM memories WHERE memory_type = 'correction'"
            if "status" in cols:
                sql += " AND (status IS NULL OR status != 'deprecated')"
            sql += " ORDER BY importance DESC"

            rows = conn.execute(sql).fetchall()
            conn.close()
        except Exception as e:
            self.stats["error"] = str(e)
            return []

        corrections = [dict(r) for r in rows]
        self.stats["total_corrections"] = len(corrections)

        if not corrections:
            return []

        # Classify domains for corrections that don't have one
        for c in corrections:
            if not c.get("domain"):
                try:
                    from kernel_gen import classify_domain
                    c["domain"] = classify_domain(c.get("content", ""))
                except ImportError:
                    c["domain"] = "general"

        # Cluster
        clusters = cluster_corrections(corrections)
        self.stats["clusters"] = len(clusters)

        # Distill each cluster into a rule
        self.rules = []
        for cluster in clusters:
            if len(cluster.corrections) >= 1:  # Include even single-correction clusters
                rule = distill_rule(cluster)
                self.rules.append(rule)

        # Sort by source_count (most corrections = most important rule)
        self.rules.sort(key=lambda r: r.source_count, reverse=True)

        self.stats["rules_generated"] = len(self.rules)
        self.stats["domains"] = list(set(r.domain for r in self.rules))

        return self.rules

    def write_rules(self, output_path: Path = None, dry_run: bool = False) -> str:
        """Write rules to kernel-rules.md.

        Returns the generated content.
        """
        if not self.rules:
            self.generate_rules()

        output = output_path or OUTPUT_PATH
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines = [
            "# Auto-Generated Rules (Distilled from Corrections)",
            f"# Generated: {now} — {len(self.rules)} rules from "
            f"{self.stats.get('total_corrections', 0)} corrections",
            "# Regenerate with: python summarizer.py",
            "",
        ]

        # Group rules by domain
        by_domain = defaultdict(list)
        for rule in self.rules:
            by_domain[rule.domain].append(rule)

        # Sort domains by total correction count
        sorted_domains = sorted(
            by_domain.items(),
            key=lambda kv: sum(r.source_count for r in kv[1]),
            reverse=True,
        )

        for domain, rules in sorted_domains:
            total_sources = sum(r.source_count for r in rules)
            lines.append(f"## {domain} ({len(rules)} rules from {total_sources} corrections)")
            lines.append("")

            for rule in rules:
                severity_icon = {
                    "critical": "!!!",
                    "high": "!!",
                    "medium": "!",
                    "low": "~",
                }.get(rule.severity, "!")

                eff_note = ""
                if rule.effectiveness > 0 and rule.effectiveness != 0.5:
                    eff_note = f" [effectiveness: {rule.effectiveness:.0%}]"

                lines.append(f"### [{severity_icon}] {rule.title}")
                lines.append(f"**{rule.description}**{eff_note}")
                lines.append(f"*Based on {rule.source_count} correction(s)*")

                if rule.examples:
                    lines.append("")
                    for ex in rule.examples:
                        lines.append(f"  - {ex}")

                lines.append("")

        content = "\n".join(lines)

        if not dry_run:
            with open(output, "w") as f:
                f.write(content)

        return content

    def get_stats(self) -> dict:
        """Get summarization statistics."""
        if not self.rules:
            self.generate_rules()
        return self.stats


# ─── CLI ─────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Summarize corrections into rules")
    parser.add_argument("--db", help="Path to memory database")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--stats", action="store_true", help="Show stats only")
    args = parser.parse_args()

    summarizer = CorrectionSummarizer(db_path=args.db)
    rules = summarizer.generate_rules()

    if args.stats:
        stats = summarizer.get_stats()
        print("Summarization stats:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        print(f"\nRules by domain:")
        by_domain = defaultdict(int)
        for r in rules:
            by_domain[r.domain] += 1
        for domain, count in sorted(by_domain.items(), key=lambda kv: kv[1], reverse=True):
            print(f"  {domain:30s} {count:3d} rules")
        return

    content = summarizer.write_rules(
        output_path=Path(args.output) if args.output else None,
        dry_run=args.dry_run,
    )

    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"{prefix}Generated {len(rules)} rules from "
          f"{summarizer.stats.get('total_corrections', 0)} corrections")
    print(f"Domains: {', '.join(summarizer.stats.get('domains', []))}")

    if not args.dry_run:
        print(f"Written to: {args.output or OUTPUT_PATH}")

    if args.dry_run:
        print("\n--- Preview ---")
        print(content[:2000])


if __name__ == "__main__":
    main()
