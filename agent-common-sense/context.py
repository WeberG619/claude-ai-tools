"""
Context-aware correction activation for the Common Sense Engine.

Reads the current system state (open apps, active files, active project)
and scores corrections by relevance to the current context. Only surfaces
corrections that matter right now.

This solves the "correction fatigue" problem — instead of showing all
62 corrections every time, only show the 3-5 most relevant ones.

Usage:
    from context import ContextEngine

    engine = ContextEngine()
    state = engine.read_system_state()

    # Get only relevant corrections for current context
    relevant = engine.get_relevant_corrections(state, limit=5)

    # Get context-aware injection for sub-agents
    injection = engine.get_contextual_injection()

From CLI:
    python context.py                   # Show relevant corrections now
    python context.py --state           # Show current system state
    python context.py --inject          # Output context-aware injection text
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


LIVE_STATE_PATH = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")


@dataclass
class SystemState:
    """Current system state snapshot."""
    active_window: str = ""
    open_apps: list = field(default_factory=list)
    revit_open: bool = False
    revit_document: str = ""
    bluebeam_open: bool = False
    excel_open: bool = False
    browser_open: bool = False
    active_project: str = ""
    recent_files: list = field(default_factory=list)
    monitors: int = 1
    memory_pct: float = 0.0

    @property
    def active_domains(self) -> list[str]:
        """Determine which domains are active based on system state."""
        domains = []

        if self.revit_open:
            domains.extend(["revit", "bim"])
        if self.bluebeam_open:
            domains.extend(["bluebeam", "pdf"])
        if self.excel_open:
            domains.append("excel")
        if self.browser_open:
            domains.append("web")

        # Check active window for additional context
        active_lower = self.active_window.lower()
        if "visual studio" in active_lower or "code" in active_lower:
            domains.extend(["code", "git", "filesystem"])
        if "chrome" in active_lower or "edge" in active_lower:
            domains.append("web")
        if "gmail" in active_lower or "outlook" in active_lower:
            domains.append("email")
        if "terminal" in active_lower or "cmd" in active_lower:
            domains.extend(["execution", "deployment"])

        return list(set(domains))


# ─── STATE READING ───────────────────────────────────────────────

class ContextEngine:
    """Context-aware correction engine."""

    def __init__(self, db_path: Optional[str] = None,
                 state_path: Path = LIVE_STATE_PATH):
        self.db_path = db_path or self._find_db()
        self.state_path = state_path

    def _find_db(self) -> str:
        candidates = [
            Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"),
            Path.home() / ".claude-memory" / "memories.db",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return ""

    def read_system_state(self) -> SystemState:
        """Read the current system state from live_state.json.

        Falls back to a default state if the file doesn't exist.
        """
        state = SystemState()

        if not self.state_path.exists():
            return state

        try:
            data = json.loads(self.state_path.read_text())

            state.active_window = data.get("active_window", {}).get("title", "")

            # Parse open apps
            apps = data.get("open_apps", [])
            if isinstance(apps, list):
                state.open_apps = apps
            elif isinstance(apps, dict):
                state.open_apps = list(apps.keys())

            # Check specific apps
            apps_lower = " ".join(str(a).lower() for a in state.open_apps)
            state.revit_open = "revit" in apps_lower
            state.bluebeam_open = "bluebeam" in apps_lower
            state.excel_open = "excel" in apps_lower
            state.browser_open = any(b in apps_lower for b in ["chrome", "edge", "firefox"])

            # Revit document
            revit_info = data.get("revit", {})
            if isinstance(revit_info, dict):
                state.revit_document = revit_info.get("document", "")

            # Active project from various sources
            state.active_project = data.get("active_project", "")

            # Recent files
            state.recent_files = data.get("recent_files", [])
            if isinstance(state.recent_files, dict):
                state.recent_files = list(state.recent_files.values())

            # System info
            monitors_data = data.get("monitors", {})
            if isinstance(monitors_data, dict):
                state.monitors = monitors_data.get("count", 1)
            elif isinstance(monitors_data, list):
                state.monitors = len(monitors_data)

            state.memory_pct = data.get("memory", {}).get("percent", 0)

        except (json.JSONDecodeError, Exception):
            pass

        return state

    def get_relevant_corrections(self, state: SystemState = None,
                                  limit: int = 10) -> list[dict]:
        """Get corrections most relevant to the current system context.

        Scores each correction by:
        - Domain match (does it match open apps?) — 40%
        - Effectiveness (has it helped before?) — 30%
        - Importance (severity weight) — 20%
        - Recency (temporal decay) — 10%
        """
        if state is None:
            state = self.read_system_state()

        if not self.db_path:
            return []

        active_domains = state.active_domains

        try:
            import sqlite3
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
        except Exception:
            return []

        corrections = [dict(r) for r in rows]

        # Score each correction
        scored = []
        for c in corrections:
            score = self._score_correction(c, active_domains)
            if score > 0.1:  # Minimum relevance threshold
                scored.append({
                    "id": c.get("id"),
                    "content": c.get("content", "")[:300],
                    "domain": c.get("domain", ""),
                    "importance": c.get("importance", 5),
                    "relevance_score": round(score, 3),
                    "helped_count": c.get("helped_count", 0) or 0,
                    "not_helped_count": c.get("not_helped_count", 0) or 0,
                    "status": c.get("status", "active"),
                })

        # Sort by relevance score
        scored.sort(key=lambda c: c["relevance_score"], reverse=True)
        return scored[:limit]

    def _score_correction(self, correction: dict,
                           active_domains: list[str]) -> float:
        """Score a single correction against current context."""
        content = correction.get("content", "").lower()
        domain = correction.get("domain", "").lower()
        importance = correction.get("importance", 5)
        helped = correction.get("helped_count", 0) or 0
        not_helped = correction.get("not_helped_count", 0) or 0

        # Domain match score (40%)
        domain_score = 0.0
        if domain and domain in [d.lower() for d in active_domains]:
            domain_score = 1.0
        elif active_domains:
            # Check content for domain keywords
            for ad in active_domains:
                if ad in content:
                    domain_score = max(domain_score, 0.6)
        else:
            # No context available — give everything a base score
            domain_score = 0.3

        # Effectiveness score (30%)
        total = helped + not_helped
        if total > 0:
            eff_score = helped / total
        else:
            eff_score = 0.5  # Unknown = neutral

        # Importance score (20%)
        imp_score = importance / 10.0

        # Recency score (10%)
        recency_score = 0.5  # Default
        try:
            from quality import decay_score
            recency_score = decay_score(
                importance=importance,
                created_at=correction.get("created_at", ""),
                helped_count=helped,
                not_helped_count=not_helped,
            )
        except ImportError:
            pass

        # Weighted combination
        total_score = (
            domain_score * 0.40 +
            eff_score * 0.30 +
            imp_score * 0.20 +
            recency_score * 0.10
        )

        return total_score

    def get_contextual_injection(self, state: SystemState = None,
                                  limit: int = 10) -> str:
        """Generate a context-aware injection for sub-agents.

        Only includes corrections relevant to the current context.
        """
        if state is None:
            state = self.read_system_state()

        relevant = self.get_relevant_corrections(state, limit=limit)

        if not relevant:
            return ""

        lines = [
            "## Context-Aware Corrections (Active Right Now)",
            f"## Active domains: {', '.join(state.active_domains)}",
            "",
        ]

        for c in relevant:
            score_pct = f"{c['relevance_score']:.0%}"
            content = c["content"]
            # Clean up common prefixes
            content = re.sub(r'^CORRECTION\s*\[.*?\]:\s*', '', content)
            content = re.sub(r'^SEED\s+CORRECTION\s*\[.*?\]:\s*', '', content)
            content = content.strip()
            if len(content) > 200:
                # Truncate to sentence boundary
                cut = content[:200]
                last_period = cut.rfind(". ")
                if last_period > 100:
                    content = cut[:last_period + 1]
                else:
                    content = cut.rstrip(",;:-") + "..."

            lines.append(f"- [{score_pct}] {content}")

        lines.append("")
        return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Context-aware corrections")
    parser.add_argument("--db", help="Path to memory database")
    parser.add_argument("--state", action="store_true",
                        help="Show current system state")
    parser.add_argument("--inject", action="store_true",
                        help="Output context-aware injection")
    parser.add_argument("--limit", type=int, default=10,
                        help="Max corrections to show")
    parser.add_argument("--state-file", help="Path to live_state.json")
    args = parser.parse_args()

    state_path = Path(args.state_file) if args.state_file else LIVE_STATE_PATH
    engine = ContextEngine(db_path=args.db, state_path=state_path)

    state = engine.read_system_state()

    if args.state:
        print("Current System State:")
        print(f"  Active window:  {state.active_window}")
        print(f"  Open apps:      {', '.join(state.open_apps[:10])}")
        print(f"  Revit:          {'open' if state.revit_open else 'closed'}")
        if state.revit_document:
            print(f"  Revit doc:      {state.revit_document}")
        print(f"  Bluebeam:       {'open' if state.bluebeam_open else 'closed'}")
        print(f"  Excel:          {'open' if state.excel_open else 'closed'}")
        print(f"  Browser:        {'open' if state.browser_open else 'closed'}")
        print(f"  Monitors:       {state.monitors}")
        print(f"  Memory:         {state.memory_pct:.0f}%")
        print(f"  Active domains: {', '.join(state.active_domains)}")
        return

    if args.inject:
        injection = engine.get_contextual_injection(state, limit=args.limit)
        print(injection)
        return

    # Default: show relevant corrections
    relevant = engine.get_relevant_corrections(state, limit=args.limit)
    print(f"System context: {', '.join(state.active_domains) or 'none detected'}")
    print(f"Relevant corrections ({len(relevant)}):\n")

    for c in relevant:
        domain = c.get("domain", "?")
        score = c["relevance_score"]
        content = c["content"][:120]
        content = re.sub(r'^CORRECTION\s*\[.*?\]:\s*', '', content).strip()
        print(f"  [{score:.0%}] ({domain}) {content}")


if __name__ == "__main__":
    main()
