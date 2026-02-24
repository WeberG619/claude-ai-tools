#!/usr/bin/env python3
"""
Meta-Router — Decides which execution framework handles a task.

The system has multiple execution paths:
- Direct: Simple, immediate execution (no sub-agent)
- Strong Agent: 5-phase framework for standard tasks
- Pipeline: Multi-stage SPEC→ARCHITECT→IMPLEMENT→REVIEW
- Swarm: Parallel decomposition for large, parallelizable tasks

Currently, the human picks. The meta-router makes this decision autonomously
based on task properties, historical outcomes, and domain knowledge.

Usage:
    from meta_router import MetaRouter
    router = MetaRouter()

    decision = router.route(
        "Fix the wall join issue at grid B-3 in the Revit model",
        context={"project": "ResidentialA", "files_affected": 1}
    )
    print(decision.framework)   # "strong_agent"
    print(decision.model_tier)  # "sonnet"
    print(decision.reasoning)   # "Single-domain Revit fix, standard complexity..."

    # After task completes, record outcome for learning
    router.record_outcome(decision.decision_id, success=True, notes="Fixed in 3 turns")
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "cognitive.db"


@dataclass
class RoutingDecision:
    """The result of routing a task to an execution framework."""
    decision_id: str = ""
    framework: str = "strong_agent"     # direct | strong_agent | pipeline | swarm
    model_tier: str = "sonnet"          # haiku | sonnet | opus
    max_turns: int = 25
    agent_type: str = ""                # Specific agent from the fleet (optional)
    reasoning: str = ""
    confidence: float = 0.7
    use_worktree: bool = False          # Git worktree isolation
    run_in_background: bool = False
    priority_signals: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "framework": self.framework,
            "model_tier": self.model_tier,
            "max_turns": self.max_turns,
            "agent_type": self.agent_type,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "use_worktree": self.use_worktree,
            "run_in_background": self.run_in_background,
        }


# Task property analyzers
FRAMEWORK_SIGNALS = {
    "direct": {
        "signals": ["fix typo", "rename", "change one", "update value",
                    "simple", "quick", "trivial", "single line"],
        "max_complexity": "small",
        "max_files": 1,
    },
    "strong_agent": {
        "signals": ["implement", "create", "build", "fix", "update",
                    "add", "modify", "configure", "set up"],
        "max_complexity": "large",
        "max_files": 5,
    },
    "pipeline": {
        "signals": ["design and implement", "spec to code", "full feature",
                    "multi-stage", "architect", "end to end", "from scratch"],
        "max_complexity": "huge",
        "max_files": 999,
    },
    "swarm": {
        "signals": ["batch", "all files", "every", "across the codebase",
                    "scan all", "update all", "migrate", "bulk"],
        "max_complexity": "huge",
        "max_files": 999,
    },
}

MODEL_SIGNALS = {
    "haiku": {
        "signals": ["search", "find", "list", "check", "status",
                    "read", "explore", "what is", "where is", "look up",
                    "count", "verify", "confirm"],
        "max_complexity": "small",
    },
    "sonnet": {
        "signals": ["implement", "create", "build", "fix", "refactor",
                    "add feature", "write test", "code review",
                    "update", "modify", "configure"],
        "max_complexity": "large",
    },
    "opus": {
        "signals": ["architect", "design system", "complex debug",
                    "novel", "unprecedented", "critical", "production",
                    "multi-system", "integration", "security audit"],
        "max_complexity": "huge",
    },
}


class MetaRouter:
    """Routes tasks to the optimal execution framework."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_schema(self):
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS routing_decisions (
                id TEXT PRIMARY KEY,
                task_description TEXT NOT NULL,
                framework TEXT NOT NULL,
                model_tier TEXT NOT NULL,
                agent_type TEXT DEFAULT '',
                reasoning TEXT,
                confidence REAL,
                success INTEGER,
                turns_used INTEGER,
                duration_seconds REAL,
                notes TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS routing_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                framework TEXT NOT NULL,
                model_tier TEXT NOT NULL,
                domain TEXT,
                complexity TEXT,
                success INTEGER NOT NULL,
                turns_used INTEGER,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_routing_framework ON routing_decisions(framework);
            CREATE INDEX IF NOT EXISTS idx_routing_success ON routing_decisions(success);
            CREATE INDEX IF NOT EXISTS idx_outcomes_framework ON routing_outcomes(framework);
        """)
        conn.commit()
        conn.close()

    def route(self, task_description: str, context: dict = None) -> RoutingDecision:
        """
        Route a task to the optimal execution framework.

        Analysis pipeline:
        1. Analyze task properties (domain, complexity, scope)
        2. Score each framework based on signals
        3. Check historical outcomes for similar tasks
        4. Select model tier
        5. Determine additional settings (worktree, background, turns)
        """
        import uuid
        context = context or {}
        task_lower = task_description.lower()

        # Analyze task properties
        properties = self._analyze_task(task_description, context)

        # Score frameworks
        framework_scores = self._score_frameworks(task_lower, properties, context)

        # Apply historical bias
        framework_scores = self._apply_historical_bias(framework_scores, properties)

        # Select best framework
        framework = max(framework_scores, key=framework_scores.get)

        # Select model tier
        model_tier = self._select_model(task_lower, properties)

        # Determine settings
        max_turns = self._estimate_turns(framework, properties)
        use_worktree = self._should_use_worktree(properties, context)
        run_in_background = properties.get("estimated_duration", "short") == "long"

        # Select specialized agent if available
        agent_type = self._select_agent(properties)

        # Reasoning
        reasoning = self._build_reasoning(
            framework, model_tier, properties, framework_scores
        )

        decision = RoutingDecision(
            decision_id=uuid.uuid4().hex[:10],
            framework=framework,
            model_tier=model_tier,
            max_turns=max_turns,
            agent_type=agent_type,
            reasoning=reasoning,
            confidence=min(0.95, framework_scores[framework] / 10),
            use_worktree=use_worktree,
            run_in_background=run_in_background,
            priority_signals=properties,
        )

        # Store decision
        self._store_decision(decision, task_description)

        return decision

    def _analyze_task(self, task: str, context: dict) -> dict:
        """Analyze task properties."""
        task_lower = task.lower()

        # Domain detection
        domain = "general"
        domain_keywords = {
            "revit": ["revit", "wall", "floor", "door", "sheet", "view", "bim",
                     "family", "parameter", "element"],
            "code": ["code", "function", "class", "test", "build", "api",
                    "endpoint", "refactor", "debug"],
            "desktop": ["excel", "bluebeam", "browser", "window", "screenshot",
                       "click", "navigate"],
            "pipeline": ["pipeline", "workflow", "extract", "process"],
        }
        for dom, keywords in domain_keywords.items():
            if any(kw in task_lower for kw in keywords):
                domain = dom
                break

        # Complexity
        word_count = len(task.split())
        and_count = task_lower.count(" and ")
        step_count = task_lower.count("then") + task_lower.count("after") + 1

        if word_count <= 10 and and_count == 0:
            complexity = "small"
        elif word_count <= 25 and and_count <= 1:
            complexity = "medium"
        elif word_count <= 50:
            complexity = "large"
        else:
            complexity = "huge"

        # Scope
        files_affected = context.get("files_affected", None)
        if files_affected is None:
            multi_file_signals = ["all", "every", "across", "multiple", "batch"]
            files_affected = 5 if any(s in task_lower for s in multi_file_signals) else 2

        # Is it read-only?
        read_only_signals = ["search", "find", "list", "check", "what", "where",
                            "how", "explain", "show", "count", "status"]
        is_read_only = any(task_lower.startswith(s) for s in read_only_signals)

        # Duration estimate
        if complexity in ("small", "trivial") or is_read_only:
            duration = "short"
        elif complexity == "medium":
            duration = "medium"
        else:
            duration = "long"

        # Parallelizable?
        parallel_signals = ["batch", "all files", "every module", "each"]
        is_parallel = any(s in task_lower for s in parallel_signals)

        return {
            "domain": domain,
            "complexity": complexity,
            "files_affected": files_affected,
            "is_read_only": is_read_only,
            "step_count": step_count,
            "estimated_duration": duration,
            "is_parallel": is_parallel,
            "word_count": word_count,
        }

    def _score_frameworks(self, task_lower: str, properties: dict,
                          context: dict) -> dict:
        """Score each framework for this task."""
        scores = {"direct": 0, "strong_agent": 0, "pipeline": 0, "swarm": 0}

        for fw, config in FRAMEWORK_SIGNALS.items():
            # Signal matching
            for signal in config["signals"]:
                if signal in task_lower:
                    scores[fw] += 2

            # Complexity fit
            complexity_order = ["trivial", "small", "medium", "large", "huge"]
            task_complexity = properties.get("complexity", "medium")
            max_complexity = config.get("max_complexity", "huge")
            if complexity_order.index(task_complexity) <= complexity_order.index(max_complexity):
                scores[fw] += 1

            # File count fit
            files = properties.get("files_affected", 2)
            if files <= config.get("max_files", 999):
                scores[fw] += 1

        # Special rules
        if properties.get("is_read_only"):
            scores["direct"] += 3
            scores["swarm"] -= 2

        if properties.get("is_parallel"):
            scores["swarm"] += 4

        if properties.get("step_count", 1) >= 4:
            scores["pipeline"] += 3

        if properties.get("complexity") in ("trivial", "small"):
            scores["direct"] += 3
            scores["pipeline"] -= 2
            scores["swarm"] -= 2

        if properties.get("complexity") == "huge":
            scores["direct"] -= 3
            scores["pipeline"] += 2
            scores["swarm"] += 2

        # Ensure non-negative
        for fw in scores:
            scores[fw] = max(0, scores[fw])

        # Default: if all low, strong_agent wins
        if max(scores.values()) < 3:
            scores["strong_agent"] += 3

        return scores

    def _apply_historical_bias(self, scores: dict, properties: dict) -> dict:
        """Adjust scores based on past routing outcomes."""
        conn = self._conn()
        domain = properties.get("domain", "general")
        complexity = properties.get("complexity", "medium")

        for framework in scores:
            rows = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes
                FROM routing_outcomes
                WHERE framework = ?
                AND (domain = ? OR domain IS NULL)
                AND timestamp > datetime('now', '-30 days')
            """, (framework, domain)).fetchone()

            if rows and rows["total"] >= 3:
                success_rate = rows["successes"] / rows["total"]
                # Bias: +2 for high success rate, -2 for low
                bias = round((success_rate - 0.5) * 4)
                scores[framework] += bias

        conn.close()
        return scores

    def _select_model(self, task_lower: str, properties: dict) -> str:
        """Select the optimal model tier."""
        scores = {"haiku": 0, "sonnet": 0, "opus": 0}

        for tier, config in MODEL_SIGNALS.items():
            for signal in config["signals"]:
                if signal in task_lower:
                    scores[tier] += 2

        # Complexity-based
        complexity = properties.get("complexity", "medium")
        if complexity in ("trivial", "small"):
            scores["haiku"] += 3
        elif complexity == "medium":
            scores["sonnet"] += 3
        elif complexity in ("large", "huge"):
            scores["opus"] += 1
            scores["sonnet"] += 2  # Sonnet is still default for large

        # Read-only tasks → haiku
        if properties.get("is_read_only"):
            scores["haiku"] += 4

        return max(scores, key=scores.get)

    def _estimate_turns(self, framework: str, properties: dict) -> int:
        """Estimate max turns needed."""
        base = {
            "direct": 5,
            "strong_agent": 25,
            "pipeline": 30,
            "swarm": 15,
        }.get(framework, 25)

        complexity_mult = {
            "trivial": 0.3,
            "small": 0.5,
            "medium": 1.0,
            "large": 1.5,
            "huge": 2.0,
        }.get(properties.get("complexity", "medium"), 1.0)

        return max(5, min(50, round(base * complexity_mult)))

    def _should_use_worktree(self, properties: dict, context: dict) -> bool:
        """Determine if git worktree isolation is needed."""
        files = properties.get("files_affected", 1)
        complexity = properties.get("complexity", "medium")
        return files >= 3 and complexity in ("large", "huge")

    def _select_agent(self, properties: dict) -> str:
        """Select a specialized agent from the fleet if applicable."""
        domain = properties.get("domain", "general")
        agent_map = {
            "revit": "revit-developer",
            "code": "code-architect",
            "desktop": "orchestrator",
            "pipeline": "orchestrator",
        }
        return agent_map.get(domain, "")

    def _build_reasoning(self, framework: str, model: str,
                         properties: dict, scores: dict) -> str:
        """Build explanation for the routing decision."""
        domain = properties.get("domain", "general")
        complexity = properties.get("complexity", "medium")
        files = properties.get("files_affected", "unknown")

        parts = [
            f"{complexity.capitalize()} {domain} task.",
            f"~{files} files affected.",
        ]

        if properties.get("is_read_only"):
            parts.append("Read-only task.")
        if properties.get("is_parallel"):
            parts.append("Parallelizable.")

        # Score breakdown
        sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
        top = sorted_scores[0]
        runner = sorted_scores[1] if len(sorted_scores) > 1 else None
        parts.append(f"Best fit: {top[0]} (score {top[1]}).")
        if runner and runner[1] > 0:
            parts.append(f"Runner-up: {runner[0]} ({runner[1]}).")

        return " ".join(parts)

    def record_outcome(self, decision_id: str, success: bool,
                       turns_used: int = None, duration_seconds: float = None,
                       notes: str = ""):
        """Record the outcome of a routing decision for learning."""
        conn = self._conn()

        # Update the decision
        conn.execute("""
            UPDATE routing_decisions
            SET success = ?, turns_used = ?, duration_seconds = ?, notes = ?
            WHERE id = ?
        """, (1 if success else 0, turns_used, duration_seconds, notes, decision_id))

        # Get the decision details for the outcomes table
        row = conn.execute(
            "SELECT framework, model_tier FROM routing_decisions WHERE id = ?",
            (decision_id,)
        ).fetchone()

        if row:
            # Extract domain and complexity from the stored reasoning
            conn.execute("""
                INSERT INTO routing_outcomes
                (framework, model_tier, success, turns_used, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (row["framework"], row["model_tier"], 1 if success else 0,
                  turns_used, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def _store_decision(self, decision: RoutingDecision, task_description: str):
        """Store routing decision."""
        conn = self._conn()
        conn.execute("""
            INSERT INTO routing_decisions
            (id, task_description, framework, model_tier, agent_type,
             reasoning, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision.decision_id, task_description, decision.framework,
            decision.model_tier, decision.agent_type, decision.reasoning,
            decision.confidence, datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def get_stats(self) -> dict:
        """Get routing statistics."""
        conn = self._conn()

        total = conn.execute("SELECT COUNT(*) FROM routing_decisions").fetchone()[0]
        by_framework = dict(conn.execute("""
            SELECT framework, COUNT(*) FROM routing_decisions GROUP BY framework
        """).fetchall())

        # Success rates by framework
        success_rates = {}
        for fw in by_framework:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes
                FROM routing_decisions
                WHERE framework = ? AND success IS NOT NULL
            """, (fw,)).fetchone()
            if row["total"] > 0:
                success_rates[fw] = round(row["successes"] / row["total"], 2)

        # Model tier distribution
        by_model = dict(conn.execute("""
            SELECT model_tier, COUNT(*) FROM routing_decisions GROUP BY model_tier
        """).fetchall())

        conn.close()

        return {
            "total_decisions": total,
            "by_framework": by_framework,
            "success_rates": success_rates,
            "by_model_tier": by_model,
        }


# ── CLI ──────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Meta-Router")
    sub = parser.add_subparsers(dest="command")

    rt = sub.add_parser("route", help="Route a task")
    rt.add_argument("task", help="Task description")
    sub.add_parser("stats", help="Routing statistics")

    args = parser.parse_args()
    router = MetaRouter()

    if args.command == "route":
        decision = router.route(args.task)
        print(f"Framework: {decision.framework}")
        print(f"Model: {decision.model_tier}")
        print(f"Max turns: {decision.max_turns}")
        print(f"Worktree: {decision.use_worktree}")
        print(f"Background: {decision.run_in_background}")
        if decision.agent_type:
            print(f"Agent: {decision.agent_type}")
        print(f"Reasoning: {decision.reasoning}")

    elif args.command == "stats":
        stats = router.get_stats()
        for k, v in stats.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
