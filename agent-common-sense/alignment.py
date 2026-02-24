"""
Alignment Core v1.0
====================
Auto-injection of kernel, corrections, and strong agent framework into
sub-agents. Solves the single biggest problem: sub-agents don't get alignment
data unless the main agent manually copy-pastes it.

Three injection layers:
  A. compile_prompt() CLI — main agent calls before each Task tool launch
  B. PreToolUse hook — safety net catches missed injections
  C. Direct import — agent_dispatcher.py imports and injects per dispatch

Usage:
    from alignment import AlignmentCore

    core = AlignmentCore()

    # Compile a prompt prefix for a sub-agent
    prefix = core.compile_prompt(
        agent_name="revit-builder",
        task_description="Create walls from PDF spec",
        project="Avon Park"
    )
    full_prompt = prefix + "\\n\\n" + task_prompt

    # Register alignment principles
    core.register_principle(
        layer="domain", domain="bim",
        principle="Always validate dimensions against PDF source",
        priority=8
    )

    # Check for drift
    report = core.get_drift_report()

CLI:
    python alignment.py compile --agent-name test --task "read a file"
    python alignment.py principles [--domain bim]
    python alignment.py drift
    python alignment.py verify --agent-name test --result "file was read"
"""

import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# ─── PATHS ─────────────────────────────────────────────────────

TOOLS_ROOT = Path("/mnt/d/_CLAUDE-TOOLS")
KERNEL_PATH = TOOLS_ROOT / "agent-common-sense" / "kernel.md"
KERNEL_CORE_PATH = TOOLS_ROOT / "agent-common-sense" / "kernel-core.md"
STRONG_AGENT_PATH = TOOLS_ROOT / "agent-boost" / "strong_agent.md"
KERNEL_CORRECTIONS_PATH = TOOLS_ROOT / "agent-common-sense" / "kernel-corrections.md"

# Token budget limits (rough char estimates, ~4 chars/token)
MAX_TOTAL_CHARS = 16000  # ~4000 tokens
MAX_KERNEL_CHARS = 6000
MAX_STRONG_AGENT_CHARS = 4000
MAX_CORRECTIONS_CHARS = 4000

# ─── DOMAIN KEYWORDS ──────────────────────────────────────────

DOMAIN_KEYWORDS = {
    "bim": ["revit", "bim", "wall", "door", "window", "floor plan", "model",
            "schedule", "family", "element", "parameter", "view"],
    "development": ["code", "python", "build", "test", "git", "commit",
                     "function", "class", "module", "api", "deploy"],
    "excel": ["excel", "spreadsheet", "worksheet", "cell", "formula",
              "chart", "pivot", "column", "row"],
    "client": ["client", "proposal", "invoice", "email", "meeting",
               "deliverable", "report", "communication"],
    "filesystem": ["file", "directory", "path", "copy", "move", "delete",
                    "rename", "permission"],
    "desktop": ["window", "monitor", "screenshot", "click", "browser",
                "dpi", "position", "focus"],
    "research": ["research", "analyze", "study", "paper", "report", "survey",
                  "investigate", "compare", "literature", "findings"],
    "business": ["business", "market", "revenue", "strategy", "competitor",
                  "pricing", "customer", "opportunity", "commercialize", "roi"],
    "code": ["script", "csv", "parse", "automate", "batch", "cli",
              "process", "pipeline", "utility", "tool"],
}


# ─── DATA CLASSES ──────────────────────────────────────────────

@dataclass
class AlignmentPrinciple:
    """A registered alignment rule."""
    id: int = 0
    layer: str = "domain"  # core|domain|correction|user
    domain: str = "universal"
    principle: str = ""
    priority: int = 5
    active: bool = True
    source: str = ""
    created_at: str = ""
    violations: int = 0
    last_violated: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "layer": self.layer,
            "domain": self.domain,
            "principle": self.principle,
            "priority": self.priority,
            "active": self.active,
            "source": self.source,
        }


@dataclass
class InjectionResult:
    """Result of an alignment injection attempt with quality metrics."""
    success: bool = False
    prefix: str = ""
    char_count: int = 0
    components_present: dict = field(default_factory=dict)
    error: str = ""
    quality_score: float = 0.0  # 0.0 (empty) to 1.0 (all components present)

    @property
    def meets_minimum(self) -> bool:
        """Check if injection meets minimum quality threshold."""
        return self.success and self.char_count >= 100 and self.quality_score >= 0.3

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "char_count": self.char_count,
            "quality_score": self.quality_score,
            "meets_minimum": self.meets_minimum,
            "components": self.components_present,
            "error": self.error,
        }


@dataclass
class AlignmentProfile:
    """Compiled alignment data for a sub-agent."""
    agent_name: str = ""
    task_domain: str = "general"
    principles: list[AlignmentPrinciple] = field(default_factory=list)
    kernel_content: str = ""
    corrections_content: str = ""
    strong_agent_content: str = ""
    total_char_estimate: int = 0
    permission_scope: Optional[object] = None  # permissions.PermissionScope if available

    @property
    def total_token_estimate(self) -> int:
        return self.total_char_estimate // 4


# ─── ALIGNMENT CORE ───────────────────────────────────────────

class AlignmentCore:
    """
    Manages alignment principles, compiles injection profiles,
    and tracks drift/violations.
    """

    VALID_LAYERS = {"core", "domain", "correction", "user"}

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._find_db()
        if self.db_path:
            try:
                self._ensure_schema()
                self._ensure_core_principles()
            except Exception:
                self.db_path = None  # Degrade gracefully

    def _find_db(self) -> Optional[str]:
        candidates = [
            Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"),
            Path.home() / ".claude-memory" / "memories.db",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return None

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS alignment_principles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer TEXT NOT NULL DEFAULT 'domain',
                domain TEXT DEFAULT 'universal',
                principle TEXT NOT NULL,
                priority INTEGER DEFAULT 5,
                active INTEGER DEFAULT 1,
                source TEXT DEFAULT '',
                created_at TEXT,
                violations INTEGER DEFAULT 0,
                last_violated TEXT
            );

            CREATE TABLE IF NOT EXISTS alignment_drift_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT DEFAULT '',
                agent_name TEXT DEFAULT '',
                principle_id INTEGER,
                violation_type TEXT DEFAULT '',
                description TEXT DEFAULT '',
                severity TEXT DEFAULT 'medium',
                detected_at TEXT,
                resolved INTEGER DEFAULT 0,
                resolved_at TEXT,
                FOREIGN KEY (principle_id) REFERENCES alignment_principles(id)
            );
        """)
        conn.commit()
        conn.close()

    def _ensure_core_principles(self):
        """Register core alignment principles if none exist."""
        conn = self._conn()
        count = conn.execute(
            "SELECT COUNT(*) as c FROM alignment_principles WHERE layer = 'core'"
        ).fetchone()["c"]
        if count > 0:
            conn.close()
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        core_principles = [
            ("Verify work before reporting done — take screenshots for visual tasks", 10),
            ("Never skip corrections — always check memory before actions", 9),
            ("Use DPI-aware positioning for multi-monitor window management", 9),
            ("Store corrections when user corrects you — close the feedback loop", 8),
            ("Speak summaries after completing significant tasks", 7),
            ("Proactively suggest next steps — don't wait for obvious actions", 6),
        ]
        for principle, priority in core_principles:
            conn.execute("""
                INSERT INTO alignment_principles
                (layer, domain, principle, priority, active, source, created_at)
                VALUES ('core', 'universal', ?, ?, 1, 'system', ?)
            """, (principle, priority, now))
        conn.commit()
        conn.close()

    # ─── PRINCIPLES ────────────────────────────────────────────

    def register_principle(self, principle: str, layer: str = "domain",
                           domain: str = "universal", priority: int = 5,
                           source: str = "") -> int:
        """Register an alignment principle. Returns the principle ID."""
        if layer not in self.VALID_LAYERS:
            raise ValueError(f"Invalid layer: {layer}. Must be one of {self.VALID_LAYERS}")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        cursor = conn.execute("""
            INSERT INTO alignment_principles
            (layer, domain, principle, priority, active, source, created_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
        """, (layer, domain, principle, priority, source, now))
        pid = cursor.lastrowid
        conn.commit()
        conn.close()
        return pid

    def deactivate_principle(self, principle_id: int) -> bool:
        """Deactivate a principle (soft delete)."""
        conn = self._conn()
        conn.execute(
            "UPDATE alignment_principles SET active = 0 WHERE id = ?",
            (principle_id,)
        )
        changed = conn.total_changes
        conn.commit()
        conn.close()
        return changed > 0

    def get_principles(self, domain: Optional[str] = None,
                       layer: Optional[str] = None,
                       active_only: bool = True) -> list[AlignmentPrinciple]:
        """Get alignment principles with optional filters."""
        conn = self._conn()
        sql = "SELECT * FROM alignment_principles WHERE 1=1"
        params = []

        if active_only:
            sql += " AND active = 1"
        if domain:
            sql += " AND (domain = ? OR domain = 'universal')"
            params.append(domain)
        if layer:
            sql += " AND layer = ?"
            params.append(layer)

        sql += " ORDER BY priority DESC"
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [self._row_to_principle(r) for r in rows]

    def resolve_conflicts(self, principles: list[AlignmentPrinciple]) -> list[AlignmentPrinciple]:
        """Resolve conflicts between principles using precedence rules:
        1. Higher priority number wins
        2. Specific domain wins over 'universal'
        3. CORE layer is never overridden
        4. CORRECTION layer overrides DOMAIN (experience > theory)
        """
        layer_order = {"core": 4, "correction": 3, "user": 2, "domain": 1}

        def sort_key(p):
            return (
                layer_order.get(p.layer, 0),
                0 if p.domain == "universal" else 1,
                p.priority,
            )

        return sorted(principles, key=sort_key, reverse=True)

    # ─── COMPILATION (THE KEY METHOD) ──────────────────────────

    def _detect_worktree_recommendation(self, task_description: str) -> str:
        """Detect if task warrants worktree isolation."""
        desc_lower = task_description.lower()
        risk_patterns = ["refactor", "rewrite", "restructure", "rename across",
                         "migrate", "overhaul", "rearchitect"]
        multi_file_patterns = [".py, ", ".md, ", ".cs, ", "multiple files",
                               "all files", "across the codebase"]

        has_risk = any(p in desc_lower for p in risk_patterns)
        has_multi = any(p in desc_lower for p in multi_file_patterns)

        # Count file path references
        import re
        path_refs = len(re.findall(r'[\w/]+\.\w{1,4}', task_description))

        if has_risk or has_multi or path_refs >= 3:
            return ("\n**Worktree recommended:** This task modifies multiple files or involves "
                    "risky changes. Consider using `isolation: \"worktree\"` in the Task tool, "
                    "or `git worktree add /tmp/worktree-<id> -b task/<id>` manually.\n")
        return ""

    def compile_profile(self, agent_name: str, task_description: str,
                        project: str = "") -> AlignmentProfile:
        """Compile a full alignment profile for a sub-agent."""
        profile = AlignmentProfile(agent_name=agent_name)

        # Detect domain
        profile.task_domain = self.detect_domain(task_description)

        # Get relevant principles
        principles = self.get_principles(domain=profile.task_domain)
        profile.principles = self.resolve_conflicts(principles)

        # Load kernel
        profile.kernel_content = self.get_kernel_for_domain(profile.task_domain)

        # Load strong agent framework (trimmed)
        profile.strong_agent_content = self._load_strong_agent_trimmed()

        # Load relevant corrections
        profile.corrections_content = self.get_corrections_for_task(
            task_description, project
        )

        # Attach permission scope if available
        try:
            from permissions import get_scope_for_agent
            profile.permission_scope = get_scope_for_agent(agent_name)
        except ImportError:
            pass

        # Calculate total size
        profile.total_char_estimate = (
            len(profile.kernel_content) +
            len(profile.strong_agent_content) +
            len(profile.corrections_content)
        )

        # Trim if over budget
        self._trim_to_budget(profile)

        return profile

    def compile_prompt(self, agent_name: str, task_description: str,
                       project: str = "") -> str:
        """Compile a prompt prefix string for a sub-agent.
        This is the primary method for alignment injection."""
        profile = self.compile_profile(agent_name, task_description, project)
        return self._profile_to_prompt(profile)

    def detect_domain(self, text: str) -> str:
        """Detect the domain of a task from its description."""
        text_lower = text.lower()
        scores = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[domain] = score

        if not scores:
            return "general"
        return max(scores, key=scores.get)

    # ─── HOOK INTEGRATION ─────────────────────────────────────

    def pre_task_hook(self, tool_input: dict) -> dict:
        """PreToolUse hook handler for Task tool.
        Returns JSON that Claude Code hooks can use."""
        description = tool_input.get("prompt", tool_input.get("description", ""))
        agent_name = tool_input.get("subagent_type", "unknown")

        prefix = self.compile_prompt(agent_name, description)

        if not prefix.strip():
            return {"status": "pass"}

        return {
            "status": "pass",
            "alignment_prefix": prefix,
            "message": f"[Alignment] Compiled {len(prefix)} chars for {agent_name} ({self.detect_domain(description)})"
        }

    # ─── AUTONOMOUS AGENT INTEGRATION ─────────────────────────

    def get_injection_for_autonomous(self, agent_name: str,
                                      task_description: str,
                                      event_data: Optional[dict] = None) -> str:
        """Build alignment prefix for autonomous agent dispatcher.
        Called by agent_dispatcher.py before every dispatch."""
        project = ""
        if event_data:
            project = event_data.get("project", event_data.get("project_name", ""))

        return self.compile_prompt(agent_name, task_description, project)

    def get_injection_with_verification(self, agent_name: str,
                                         task_description: str,
                                         event_data: Optional[dict] = None) -> "InjectionResult":
        """
        Build alignment prefix with quality verification.
        Returns an InjectionResult with quality metrics so the caller
        can make fail-open/fail-closed decisions.

        Quality score:
          - kernel_content present and > 500 chars: +0.3
          - corrections_content present: +0.2
          - principles present (at least 2): +0.2
          - strong_agent_content present: +0.2
          - total char count > 500: +0.1
        """
        try:
            project = ""
            if event_data:
                project = event_data.get("project", event_data.get("project_name", ""))

            profile = self.compile_profile(agent_name, task_description, project)
            prefix = self._profile_to_prompt(profile)

            score = 0.0
            components = {}

            components["kernel"] = len(profile.kernel_content) > 500
            if components["kernel"]:
                score += 0.3

            components["corrections"] = len(profile.corrections_content) > 0
            if components["corrections"]:
                score += 0.2

            components["principles"] = len(profile.principles) >= 2
            if components["principles"]:
                score += 0.2

            components["strong_agent"] = len(profile.strong_agent_content) > 100
            if components["strong_agent"]:
                score += 0.2

            if len(prefix) > 500:
                score += 0.1

            return InjectionResult(
                success=True,
                prefix=prefix,
                char_count=len(prefix),
                components_present=components,
                quality_score=round(score, 2),
            )

        except Exception as e:
            return InjectionResult(
                success=False,
                error=str(e),
            )

    # ─── VERIFICATION ──────────────────────────────────────────

    def verify_outcome(self, agent_name: str, task_description: str,
                       result: str) -> dict:
        """Check a result against alignment principles. Returns verification report."""
        domain = self.detect_domain(task_description)
        principles = self.get_principles(domain=domain)

        violations = []
        for p in principles:
            # Simple keyword check — real verification would be more sophisticated
            principle_keywords = set(re.findall(r'[a-z]{4,}', p.principle.lower()))
            result_lower = result.lower()

            # Check for specific violation patterns
            if "verify" in p.principle.lower() and "verified" not in result_lower and "screenshot" not in result_lower:
                if p.priority >= 8:
                    violations.append({
                        "principle_id": p.id,
                        "principle": p.principle,
                        "severity": "high" if p.priority >= 8 else "medium",
                        "reason": "Result doesn't mention verification",
                    })

        return {
            "agent_name": agent_name,
            "domain": domain,
            "principles_checked": len(principles),
            "violations": violations,
            "aligned": len(violations) == 0,
        }

    # ─── DRIFT TRACKING ───────────────────────────────────────

    def record_violation(self, agent_name: str, principle_id: int,
                         violation_type: str, description: str,
                         severity: str = "medium",
                         session_id: str = "") -> int:
        """Record an alignment violation."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()

        cursor = conn.execute("""
            INSERT INTO alignment_drift_log
            (session_id, agent_name, principle_id, violation_type,
             description, severity, detected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, agent_name, principle_id,
              violation_type, description, severity, now))
        vid = cursor.lastrowid

        # Update violation count on principle
        conn.execute("""
            UPDATE alignment_principles
            SET violations = violations + 1, last_violated = ?
            WHERE id = ?
        """, (now, principle_id))

        conn.commit()
        conn.close()
        return vid

    def detect_drift(self, window_hours: int = 24) -> list[dict]:
        """Detect patterns of alignment drift in recent violations."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT d.*, p.principle, p.layer
            FROM alignment_drift_log d
            LEFT JOIN alignment_principles p ON p.id = d.principle_id
            WHERE d.detected_at >= datetime('now', ?)
            AND d.resolved = 0
            ORDER BY d.detected_at DESC
        """, (f"-{window_hours} hours",)).fetchall()
        conn.close()

        # Group by principle
        by_principle = {}
        for r in rows:
            pid = r["principle_id"]
            if pid not in by_principle:
                by_principle[pid] = {
                    "principle": r["principle"],
                    "count": 0,
                    "agents": set(),
                    "latest": r["detected_at"],
                }
            by_principle[pid]["count"] += 1
            by_principle[pid]["agents"].add(r["agent_name"])

        drift_patterns = []
        for pid, info in by_principle.items():
            if info["count"] >= 2:
                drift_patterns.append({
                    "principle_id": pid,
                    "principle": info["principle"],
                    "violation_count": info["count"],
                    "affected_agents": list(info["agents"]),
                    "latest_violation": info["latest"],
                    "severity": "high" if info["count"] >= 5 else "medium",
                })

        return sorted(drift_patterns, key=lambda d: d["violation_count"], reverse=True)

    def get_drift_report(self) -> dict:
        """Generate a drift report."""
        conn = self._conn()

        total_violations = conn.execute(
            "SELECT COUNT(*) as c FROM alignment_drift_log"
        ).fetchone()["c"]
        unresolved = conn.execute(
            "SELECT COUNT(*) as c FROM alignment_drift_log WHERE resolved = 0"
        ).fetchone()["c"]
        most_violated = conn.execute("""
            SELECT p.principle, p.violations, p.layer
            FROM alignment_principles p
            WHERE p.violations > 0
            ORDER BY p.violations DESC LIMIT 5
        """).fetchall()
        conn.close()

        return {
            "total_violations": total_violations,
            "unresolved": unresolved,
            "drift_patterns": self.detect_drift(),
            "most_violated_principles": [
                {"principle": r["principle"], "violations": r["violations"], "layer": r["layer"]}
                for r in most_violated
            ],
        }

    # ─── CONTENT LOADING ──────────────────────────────────────

    def get_kernel_for_domain(self, domain: str) -> str:
        """Load and optionally filter kernel content for a domain."""
        # Use kernel-core for non-user-specific agents
        kernel_path = KERNEL_CORE_PATH if KERNEL_CORE_PATH.exists() else KERNEL_PATH
        if not kernel_path.exists():
            return ""

        content = kernel_path.read_text()

        # For specific domains, extract relevant sections
        if domain != "general" and len(content) > MAX_KERNEL_CHARS:
            content = self._extract_kernel_sections(content, domain)

        return content[:MAX_KERNEL_CHARS]

    def get_corrections_for_task(self, task_description: str,
                                 project: str = "") -> str:
        """Get relevant corrections for a task."""
        if not self.db_path:
            return ""

        # Try to get corrections via memory search
        try:
            conn = self._conn()
            # Check if memories table exists
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
            ).fetchone()
            if not tables:
                conn.close()
                return ""

            # Search for corrections related to the task
            keywords = set(re.findall(r'[a-z]{3,}', task_description.lower()))
            keywords -= {"the", "and", "for", "with", "this", "that", "from"}

            if not keywords:
                conn.close()
                return ""

            # Build search query
            like_clauses = " OR ".join(["content LIKE ?" for _ in list(keywords)[:5]])
            params = [f"%{kw}%" for kw in list(keywords)[:5]]

            rows = conn.execute(f"""
                SELECT content, importance FROM memories
                WHERE memory_type = 'correction'
                AND ({like_clauses})
                AND (status IS NULL OR status != 'deprecated')
                ORDER BY importance DESC
                LIMIT 5
            """, params).fetchall()
            conn.close()

            if not rows:
                return ""

            lines = ["## Relevant Corrections", ""]
            for r in rows:
                content = r["content"][:200]
                lines.append(f"- {content}")

            result = "\n".join(lines)
            return result[:MAX_CORRECTIONS_CHARS]

        except Exception:
            return ""

    def _load_strong_agent_trimmed(self) -> str:
        """Load the strong agent framework, trimmed to key sections."""
        if not STRONG_AGENT_PATH.exists():
            return ""

        content = STRONG_AGENT_PATH.read_text()

        # If it fits, return as-is
        if len(content) <= MAX_STRONG_AGENT_CHARS:
            return content

        # Extract key sections: look for ## headers and keep most important ones
        sections = content.split("\n## ")
        if len(sections) <= 1:
            return content[:MAX_STRONG_AGENT_CHARS]

        # Keep first section (intro) and prioritize execution-related sections
        priority_keywords = ["execution", "quality", "verify", "decision", "phase"]
        kept = [sections[0]]
        for section in sections[1:]:
            section_lower = section.lower()
            if any(kw in section_lower for kw in priority_keywords):
                kept.append("## " + section)

        result = "\n".join(kept)
        return result[:MAX_STRONG_AGENT_CHARS]

    def _extract_kernel_sections(self, content: str, domain: str) -> str:
        """Extract domain-relevant sections from kernel."""
        # Always keep DECISION LOOP and VERIFY LOOP
        essential_patterns = ["DECISION LOOP", "VERIFY LOOP", "CRITICAL",
                              "MANDATORY", "ALWAYS"]
        domain_keywords = DOMAIN_KEYWORDS.get(domain, [])

        lines = content.split("\n")
        kept_lines = []
        in_relevant_section = True  # Start keeping from the top

        for line in lines:
            line_lower = line.lower()
            # Always keep headers and essential content
            if line.startswith("#") or any(p.lower() in line_lower for p in essential_patterns):
                in_relevant_section = True
            elif any(kw in line_lower for kw in domain_keywords):
                in_relevant_section = True

            if in_relevant_section:
                kept_lines.append(line)

            # Stop keeping after blank lines following non-relevant content
            if not line.strip() and not in_relevant_section:
                continue

        return "\n".join(kept_lines)

    def _trim_to_budget(self, profile: AlignmentProfile):
        """Trim profile content to stay within token budget."""
        while profile.total_char_estimate > MAX_TOTAL_CHARS:
            # Trim corrections first (lowest priority)
            if len(profile.corrections_content) > 500:
                lines = profile.corrections_content.split("\n")
                profile.corrections_content = "\n".join(lines[:-2])
            # Then trim kernel
            elif len(profile.kernel_content) > 2000:
                profile.kernel_content = profile.kernel_content[:2000] + "\n[trimmed]"
            # Then trim strong agent
            elif len(profile.strong_agent_content) > 1000:
                profile.strong_agent_content = profile.strong_agent_content[:1000] + "\n[trimmed]"
            else:
                break

            profile.total_char_estimate = (
                len(profile.kernel_content) +
                len(profile.strong_agent_content) +
                len(profile.corrections_content)
            )

    def _profile_to_prompt(self, profile: AlignmentProfile) -> str:
        """Convert an AlignmentProfile into a prompt prefix string."""
        parts = []

        if profile.strong_agent_content:
            parts.append("# Agent Execution Framework\n")
            parts.append(profile.strong_agent_content)

        if profile.kernel_content:
            parts.append("\n# Common Sense Kernel\n")
            parts.append(profile.kernel_content)

        if profile.corrections_content:
            parts.append("\n" + profile.corrections_content)

        # Worktree recommendation for risky tasks
        worktree_note = self._detect_worktree_recommendation(
            profile.agent_name + " " + profile.task_domain
        )
        if worktree_note:
            parts.append(worktree_note)

        if profile.principles:
            parts.append("\n# Alignment Principles\n")
            for p in profile.principles[:10]:
                parts.append(f"- [{p.layer.upper()}] {p.principle}")

        if profile.permission_scope is not None:
            try:
                from permissions import compile_permission_prompt
                perm_text = compile_permission_prompt(profile.permission_scope, profile.agent_name)
                if perm_text:
                    parts.append("\n" + perm_text)
            except ImportError:
                pass

        return "\n".join(parts)

    def _row_to_principle(self, row: sqlite3.Row) -> AlignmentPrinciple:
        return AlignmentPrinciple(
            id=row["id"],
            layer=row["layer"] or "domain",
            domain=row["domain"] or "universal",
            principle=row["principle"],
            priority=row["priority"] or 5,
            active=bool(row["active"]),
            source=row["source"] or "",
            created_at=row["created_at"] or "",
            violations=row["violations"] or 0,
            last_violated=row["last_violated"] or "",
        )


# ─── CLI ───────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Alignment Core v1.0")
    sub = parser.add_subparsers(dest="command")

    # compile
    p_compile = sub.add_parser("compile", help="Compile alignment prompt")
    p_compile.add_argument("--agent-name", required=True)
    p_compile.add_argument("--task", required=True)
    p_compile.add_argument("--project", default="")
    p_compile.add_argument("--db", default=None)

    # principles
    p_principles = sub.add_parser("principles", help="List principles")
    p_principles.add_argument("--domain", default=None)
    p_principles.add_argument("--layer", default=None)
    p_principles.add_argument("--db", default=None)

    # drift
    p_drift = sub.add_parser("drift", help="Show drift report")
    p_drift.add_argument("--db", default=None)

    # add-correction
    p_corr = sub.add_parser("add-correction", help="Add a domain correction")
    p_corr.add_argument("--domain", required=True)
    p_corr.add_argument("--correction", required=True)
    p_corr.add_argument("--priority", type=int, default=7)
    p_corr.add_argument("--db", default=None)

    # verify
    p_verify = sub.add_parser("verify", help="Verify outcome")
    p_verify.add_argument("--agent-name", required=True)
    p_verify.add_argument("--task", required=True)
    p_verify.add_argument("--result", required=True)
    p_verify.add_argument("--db", default=None)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    db = getattr(args, "db", None)
    core = AlignmentCore(db_path=db)

    if args.command == "compile":
        prefix = core.compile_prompt(args.agent_name, args.task, args.project)
        print(prefix)

    elif args.command == "principles":
        principles = core.get_principles(domain=args.domain, layer=args.layer)
        if not principles:
            print("No principles registered.")
            return
        print(f"Alignment principles ({len(principles)}):\n")
        for p in principles:
            status = "active" if p.active else "inactive"
            print(f"  [{p.layer.upper():10s}] [{p.domain:12s}] (prio {p.priority:2d}) {p.principle}")
            if p.violations > 0:
                print(f"  {'':26s} violations: {p.violations}")

    elif args.command == "drift":
        report = core.get_drift_report()
        print(f"Alignment Drift Report")
        print(f"  Total violations: {report['total_violations']}")
        print(f"  Unresolved: {report['unresolved']}")
        if report["drift_patterns"]:
            print(f"\n  Drift patterns:")
            for d in report["drift_patterns"]:
                print(f"    [{d['severity']}] {d['principle']} ({d['violation_count']}x)")
        if report["most_violated_principles"]:
            print(f"\n  Most violated:")
            for m in report["most_violated_principles"]:
                print(f"    [{m['layer']}] {m['principle'][:50]} ({m['violations']}x)")

    elif args.command == "add-correction":
        pid = core.register_principle(
            principle=args.correction,
            layer="correction",
            domain=args.domain,
            priority=args.priority,
            source="cli"
        )
        print(f"Added correction #{pid} [{args.domain}]: {args.correction}")

    elif args.command == "verify":
        result = core.verify_outcome(args.agent_name, args.task, args.result)
        if result["aligned"]:
            print(f"ALIGNED: {result['principles_checked']} principles checked, no violations")
        else:
            print(f"VIOLATIONS ({len(result['violations'])}):")
            for v in result["violations"]:
                print(f"  [{v['severity']}] {v['principle'][:60]}")
                print(f"    Reason: {v['reason']}")


if __name__ == "__main__":
    main()
