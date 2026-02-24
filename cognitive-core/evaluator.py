#!/usr/bin/env python3
"""
Self-Evaluation Engine — The system judges its own output.

After every significant action, the evaluator scores the result,
decides whether to accept/retry/escalate, and tracks accuracy
over time to calibrate confidence.

The key insight: self-evaluation must be structured and criteria-based,
not just "did it work?" Each domain has specific quality criteria.

Usage:
    from evaluator import Evaluator
    ev = Evaluator()

    # After completing work
    result = ev.evaluate(
        action="Created 12 walls from floor plan extraction",
        result="All walls placed, 2 warnings about join geometry",
        goal="Extract floor plan from PDF and create Revit walls",
        domain="revit"
    )

    if result.decision == "retry":
        # Try again with the evaluator's suggestions
        ...
    elif result.decision == "escalate":
        # Flag for human review
        ...

    # Track calibration over time
    ev.record_human_override(eval_id, human_score=4, notes="Walls were off by 6 inches")
    stats = ev.get_calibration_stats()
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


DB_PATH = Path(__file__).parent / "cognitive.db"
MEMORY_DB = Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db")


@dataclass
class Evaluation:
    """Result of self-evaluating an action."""
    eval_id: str = ""
    score: int = 5                      # 1-10
    reasoning: str = ""                  # Why this score
    decision: str = "accept"             # accept | retry | escalate
    criteria_scores: dict = field(default_factory=dict)  # Per-criterion breakdown
    suggestions: list = field(default_factory=list)       # What to improve
    confidence: float = 0.7              # How confident in this evaluation
    retry_strategy: str = ""             # If retry, what to do differently

    @property
    def passed(self) -> bool:
        return self.decision == "accept"

    def to_dict(self) -> dict:
        return {
            "eval_id": self.eval_id,
            "score": self.score,
            "reasoning": self.reasoning,
            "decision": self.decision,
            "criteria_scores": self.criteria_scores,
            "suggestions": self.suggestions,
            "confidence": self.confidence,
            "retry_strategy": self.retry_strategy,
        }


# Domain-specific evaluation criteria
# Each criterion has: name, weight (0-1), description
DOMAIN_CRITERIA = {
    "revit": [
        ("correctness", 0.30, "Elements placed correctly per spec (dimensions, types, locations)"),
        ("completeness", 0.25, "All requested elements created, nothing missing"),
        ("model_quality", 0.20, "Clean joins, no overlaps, proper constraints"),
        ("standards", 0.15, "Matches BIM standards (naming, parameters, families)"),
        ("verification", 0.10, "Results verified via screenshot or element query"),
    ],
    "code": [
        ("correctness", 0.30, "Code does what was requested, no bugs"),
        ("tests", 0.20, "Tests pass, coverage adequate"),
        ("style", 0.15, "Matches existing patterns and conventions"),
        ("security", 0.15, "No injection, no secrets, proper validation"),
        ("minimal", 0.10, "Minimum viable change, no over-engineering"),
        ("verification", 0.10, "Build passes, no regressions"),
    ],
    "desktop": [
        ("correctness", 0.30, "Action completed as requested"),
        ("visual_verify", 0.30, "Screenshot confirms expected state"),
        ("dpi_aware", 0.20, "Used DPI-safe patterns (SetWindowPos, not window_move)"),
        ("focus_check", 0.10, "Correct window had focus before input"),
        ("cleanup", 0.10, "No leftover state (temp files, wrong focus)"),
    ],
    "pipeline": [
        ("goal_achieved", 0.30, "End-to-end goal was met"),
        ("stage_quality", 0.20, "Each stage produced valid output"),
        ("no_data_loss", 0.20, "No information lost between stages"),
        ("checkpoints", 0.15, "Proper checkpoints saved for resumability"),
        ("efficiency", 0.15, "No unnecessary retries or wasted work"),
    ],
    "general": [
        ("correctness", 0.35, "Action achieved the stated goal"),
        ("completeness", 0.25, "Nothing missing from the deliverable"),
        ("quality", 0.20, "Output meets professional standard"),
        ("verification", 0.20, "Results verified before claiming done"),
    ],
}

# Score thresholds for decisions
ACCEPT_THRESHOLD = 7    # Score >= 7: accept
RETRY_THRESHOLD = 4     # Score 4-6: retry with suggestions
                        # Score < 4: escalate to human


class Evaluator:
    """Self-evaluation engine with domain-specific criteria and calibration tracking."""

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
            CREATE TABLE IF NOT EXISTS evaluations (
                id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                result_summary TEXT,
                goal TEXT,
                domain TEXT DEFAULT 'general',
                score INTEGER,
                reasoning TEXT,
                decision TEXT,
                criteria_scores TEXT DEFAULT '{}',
                suggestions TEXT DEFAULT '[]',
                confidence REAL DEFAULT 0.7,
                retry_strategy TEXT DEFAULT '',
                human_override_score INTEGER,
                human_notes TEXT,
                calibration_delta INTEGER,
                created_at TEXT NOT NULL,
                session_id TEXT
            );

            CREATE TABLE IF NOT EXISTS calibration_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT,
                self_score INTEGER,
                human_score INTEGER,
                delta INTEGER,
                timestamp TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_eval_domain ON evaluations(domain);
            CREATE INDEX IF NOT EXISTS idx_eval_decision ON evaluations(decision);
            CREATE INDEX IF NOT EXISTS idx_eval_created ON evaluations(created_at);
        """)
        conn.commit()
        conn.close()

    def evaluate(self, action: str, result: str, goal: str,
                 domain: str = "general", context: dict = None) -> Evaluation:
        """
        Evaluate an action's result against domain-specific criteria.

        This is the core method. It:
        1. Selects criteria based on domain
        2. Scores each criterion based on textual analysis
        3. Computes weighted overall score
        4. Makes accept/retry/escalate decision
        5. Generates actionable suggestions if score is low
        6. Stores for calibration tracking
        """
        import uuid
        eval_id = uuid.uuid4().hex[:10]

        criteria = DOMAIN_CRITERIA.get(domain, DOMAIN_CRITERIA["general"])
        criteria_scores = {}
        suggestions = []

        # Score each criterion using heuristic analysis
        for name, weight, description in criteria:
            score, suggestion = self._score_criterion(
                name, action, result, goal, context or {}
            )
            criteria_scores[name] = {
                "score": score,
                "weight": weight,
                "weighted": round(score * weight, 2),
            }
            if score < ACCEPT_THRESHOLD and suggestion:
                suggestions.append(suggestion)

        # Weighted overall score
        total_weight = sum(c["weight"] for c in criteria_scores.values())
        if total_weight > 0:
            raw_score = sum(c["weighted"] for c in criteria_scores.values()) / total_weight
        else:
            raw_score = 5.0
        score = max(1, min(10, round(raw_score)))

        # Apply calibration bias (learn from past over/under-scoring)
        bias = self._get_calibration_bias(domain)
        adjusted_score = max(1, min(10, score + bias))

        # Decision
        if adjusted_score >= ACCEPT_THRESHOLD:
            decision = "accept"
        elif adjusted_score >= RETRY_THRESHOLD:
            decision = "retry"
        else:
            decision = "escalate"

        # Generate retry strategy if needed
        retry_strategy = ""
        if decision == "retry":
            weak_criteria = sorted(
                criteria_scores.items(),
                key=lambda x: x[1]["score"]
            )[:2]
            retry_strategy = f"Focus on improving: {', '.join(c[0] for c in weak_criteria)}. "
            retry_strategy += "; ".join(suggestions[:3])

        # Reasoning
        reasoning = self._build_reasoning(
            action, result, goal, criteria_scores, adjusted_score, decision
        )

        # Confidence based on how much calibration data we have
        cal_count = self._get_calibration_count(domain)
        confidence = min(0.95, 0.5 + (cal_count * 0.05))  # More data = more confident

        evaluation = Evaluation(
            eval_id=eval_id,
            score=adjusted_score,
            reasoning=reasoning,
            decision=decision,
            criteria_scores=criteria_scores,
            suggestions=suggestions,
            confidence=confidence,
            retry_strategy=retry_strategy,
        )

        # Store for tracking
        self._store_evaluation(evaluation, action, result, goal, domain)

        return evaluation

    def _score_criterion(self, criterion: str, action: str, result: str,
                         goal: str, context: dict) -> tuple:
        """
        Score a single criterion heuristically.

        Returns (score: int, suggestion: str or None).
        This uses pattern matching and keyword analysis.
        Not perfect — but calibration corrects over time.
        """
        result_lower = result.lower()
        action_lower = action.lower()

        # Negative signals that reduce any score
        error_signals = ["error", "failed", "exception", "traceback", "warning",
                         "could not", "unable to", "not found", "timeout"]
        has_errors = any(s in result_lower for s in error_signals)
        error_penalty = -3 if has_errors else 0

        # Positive signals
        success_signals = ["success", "completed", "created", "passed", "verified",
                          "confirmed", "all tests pass", "build succeeded"]
        has_success = any(s in result_lower for s in success_signals)
        success_bonus = 2 if has_success else 0

        if criterion == "correctness":
            base = 7
            if has_errors:
                return max(1, base + error_penalty), "Errors detected in result — verify correctness"
            if has_success:
                return min(10, base + success_bonus), None
            # Check if result mentions the goal's key terms
            goal_words = set(goal.lower().split()) - {"the", "a", "an", "to", "in", "on", "for"}
            result_words = set(result_lower.split())
            overlap = len(goal_words & result_words) / max(len(goal_words), 1)
            score = base + round(overlap * 3)
            if score < 7:
                return score, "Result may not fully match the stated goal"
            return min(10, score), None

        elif criterion == "completeness":
            base = 6
            partial_signals = ["partial", "some", "most", "remaining", "todo",
                             "not yet", "will need", "missing"]
            if any(s in result_lower for s in partial_signals):
                return max(1, base - 2), "Work appears incomplete — check for missing elements"
            if has_success:
                return min(10, base + success_bonus), None
            return base, None

        elif criterion == "verification" or criterion == "visual_verify":
            base = 5  # Default low — verification must be explicit
            verify_signals = ["screenshot", "verified", "confirmed", "checked",
                            "re-read", "test pass", "build pass", "queried"]
            if any(s in result_lower for s in verify_signals):
                return 9, None
            return base, "No verification evidence found — always verify before claiming done"

        elif criterion == "tests":
            base = 5
            if "test" in result_lower and "pass" in result_lower:
                return 9, None
            if "test" in result_lower and "fail" in result_lower:
                return 3, "Tests are failing — fix before accepting"
            if "no test" in result_lower or "skip" in result_lower:
                return 4, "Tests skipped or missing — consider adding coverage"
            return base, "Test status unclear — run tests to verify"

        elif criterion == "security":
            base = 7
            security_issues = ["password", "secret", "api_key", "token",
                             "injection", "eval(", "exec(", ".env"]
            if any(s in result_lower for s in security_issues):
                return 3, "Potential security concern detected in output"
            return base, None

        elif criterion == "style" or criterion == "standards":
            base = 7
            style_signals = ["convention", "pattern", "consistent", "matches"]
            if any(s in result_lower for s in style_signals):
                return 8, None
            return base, None

        elif criterion == "minimal":
            base = 7
            overengineering_signals = ["refactored", "also added", "bonus",
                                      "extra", "additionally", "while I was at it"]
            if any(s in result_lower for s in overengineering_signals):
                return 4, "May have over-engineered — stick to minimum viable change"
            return base, None

        elif criterion == "model_quality":
            base = 6
            quality_signals = ["clean join", "no overlap", "constrained", "proper"]
            issue_signals = ["overlap", "gap", "disjoin", "orphan", "warning"]
            if any(s in result_lower for s in issue_signals):
                return 4, "Model quality issues detected (overlaps, gaps, or warnings)"
            if any(s in result_lower for s in quality_signals):
                return 8, None
            return base, None

        elif criterion == "dpi_aware":
            base = 7
            bad_patterns = ["window_move", "showwindow", "sw_maximize"]
            good_patterns = ["setwindowpos", "dpiaware", "setprocessdpiaware"]
            if any(s in result_lower for s in bad_patterns):
                return 2, "Used non-DPI-safe window positioning — use SetWindowPos pattern"
            if any(s in result_lower for s in good_patterns):
                return 9, None
            return base, None

        elif criterion == "focus_check":
            base = 6
            if "focus" in result_lower and ("wrong" in result_lower or "incorrect" in result_lower):
                return 3, "Wrong window had focus — always verify focus before sending keys"
            if "focus" in result_lower and ("set" in result_lower or "activated" in result_lower):
                return 8, None
            return base, None

        elif criterion == "goal_achieved":
            base = 6
            if has_success and not has_errors:
                return 9, None
            if has_errors:
                return max(1, base + error_penalty), "Goal may not have been achieved due to errors"
            return base, None

        elif criterion == "no_data_loss":
            base = 7
            loss_signals = ["lost", "missing data", "truncated", "dropped", "incomplete"]
            if any(s in result_lower for s in loss_signals):
                return 3, "Possible data loss detected between pipeline stages"
            return base, None

        elif criterion == "checkpoints":
            base = 5
            if "checkpoint" in result_lower or "saved state" in result_lower:
                return 8, None
            return base, "No checkpoints mentioned — long tasks should save state"

        elif criterion == "efficiency":
            base = 7
            waste_signals = ["retry", "retried", "attempt #", "third try", "starting over"]
            if any(s in result_lower for s in waste_signals):
                return 5, "Multiple retries suggest inefficiency — analyze root cause"
            return base, None

        else:
            # Unknown criterion — neutral score
            return 6 + error_penalty + success_bonus, None

    def _build_reasoning(self, action: str, result: str, goal: str,
                         criteria_scores: dict, score: int, decision: str) -> str:
        """Build human-readable reasoning for the evaluation."""
        strong = [name for name, cs in criteria_scores.items() if cs["score"] >= 8]
        weak = [name for name, cs in criteria_scores.items() if cs["score"] < 6]

        parts = [f"Overall score: {score}/10 -> {decision.upper()}."]

        if strong:
            parts.append(f"Strong on: {', '.join(strong)}.")
        if weak:
            parts.append(f"Weak on: {', '.join(weak)}.")

        if decision == "retry":
            parts.append("Recommend retry with focused improvements on weak areas.")
        elif decision == "escalate":
            parts.append("Score too low for autonomous handling — needs human review.")

        return " ".join(parts)

    def _get_calibration_bias(self, domain: str) -> int:
        """
        Calculate scoring bias based on past calibration data.

        If we consistently over-score (self > human), apply negative bias.
        If we consistently under-score (self < human), apply positive bias.
        """
        conn = self._conn()
        row = conn.execute("""
            SELECT AVG(delta) as avg_delta, COUNT(*) as cnt
            FROM calibration_log
            WHERE domain = ? AND timestamp > datetime('now', '-30 days')
        """, (domain,)).fetchone()
        conn.close()

        if row and row["cnt"] and row["cnt"] >= 3:
            avg_delta = row["avg_delta"]
            # If avg_delta is negative (we over-score), apply negative bias
            # If avg_delta is positive (we under-score), apply positive bias
            return max(-2, min(2, round(avg_delta)))
        return 0

    def _get_calibration_count(self, domain: str) -> int:
        """Get number of calibration data points for confidence calculation."""
        conn = self._conn()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM calibration_log WHERE domain = ?",
            (domain,)
        ).fetchone()
        conn.close()
        return row["cnt"] if row else 0

    def record_human_override(self, eval_id: str, human_score: int,
                               notes: str = "") -> bool:
        """
        Record when a human disagrees with the self-evaluation.

        This is the critical feedback loop. Over time, the evaluator
        learns whether it over- or under-scores in each domain.
        """
        conn = self._conn()
        row = conn.execute(
            "SELECT score, domain FROM evaluations WHERE id = ?", (eval_id,)
        ).fetchone()

        if not row:
            conn.close()
            return False

        self_score = row["score"]
        domain = row["domain"]
        delta = human_score - self_score  # Positive = we under-scored

        conn.execute("""
            UPDATE evaluations
            SET human_override_score = ?, human_notes = ?, calibration_delta = ?
            WHERE id = ?
        """, (human_score, notes, delta, eval_id))

        conn.execute("""
            INSERT INTO calibration_log (domain, self_score, human_score, delta, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (domain, self_score, human_score, delta, datetime.now().isoformat()))

        conn.commit()
        conn.close()
        return True

    def get_calibration_stats(self, domain: str = None) -> dict:
        """Get calibration statistics — how accurate is the self-evaluation?"""
        conn = self._conn()

        if domain:
            rows = conn.execute(
                "SELECT * FROM calibration_log WHERE domain = ? ORDER BY timestamp DESC",
                (domain,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM calibration_log ORDER BY timestamp DESC"
            ).fetchall()
        conn.close()

        if not rows:
            return {
                "total_calibrations": 0,
                "message": "No calibration data yet. Use record_human_override() to build calibration."
            }

        deltas = [r["delta"] for r in rows]
        abs_deltas = [abs(d) for d in deltas]

        return {
            "total_calibrations": len(rows),
            "mean_absolute_error": round(sum(abs_deltas) / len(abs_deltas), 2),
            "mean_bias": round(sum(deltas) / len(deltas), 2),  # + = under-scoring, - = over-scoring
            "perfect_matches": sum(1 for d in deltas if d == 0),
            "within_1": sum(1 for d in abs_deltas if d <= 1),
            "within_2": sum(1 for d in abs_deltas if d <= 2),
            "over_scoring": sum(1 for d in deltas if d < 0),
            "under_scoring": sum(1 for d in deltas if d > 0),
        }

    def get_recent_evaluations(self, limit: int = 20, domain: str = None) -> list:
        """Get recent evaluations for review."""
        conn = self._conn()
        sql = "SELECT * FROM evaluations"
        params = []
        if domain:
            sql += " WHERE domain = ?"
            params.append(domain)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_retry_rate(self, domain: str = None) -> dict:
        """Get retry and escalation rates by domain."""
        conn = self._conn()
        if domain:
            rows = conn.execute("""
                SELECT decision, COUNT(*) as cnt
                FROM evaluations WHERE domain = ?
                GROUP BY decision
            """, (domain,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT decision, COUNT(*) as cnt
                FROM evaluations
                GROUP BY decision
            """).fetchall()
        conn.close()

        counts = {r["decision"]: r["cnt"] for r in rows}
        total = sum(counts.values())
        if total == 0:
            return {"total": 0}

        return {
            "total": total,
            "accept_rate": round(counts.get("accept", 0) / total, 3),
            "retry_rate": round(counts.get("retry", 0) / total, 3),
            "escalation_rate": round(counts.get("escalate", 0) / total, 3),
        }

    def _store_evaluation(self, ev: Evaluation, action: str, result: str,
                          goal: str, domain: str):
        """Persist evaluation for tracking."""
        conn = self._conn()
        conn.execute("""
            INSERT INTO evaluations
            (id, action, result_summary, goal, domain, score, reasoning,
             decision, criteria_scores, suggestions, confidence, retry_strategy,
             created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ev.eval_id, action, result, goal, domain, ev.score, ev.reasoning,
            ev.decision, json.dumps(ev.criteria_scores), json.dumps(ev.suggestions),
            ev.confidence, ev.retry_strategy, datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()


# ── CLI ──────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Self-Evaluation Engine")
    sub = parser.add_subparsers(dest="command")

    # Evaluate
    ev_parser = sub.add_parser("evaluate", help="Evaluate an action")
    ev_parser.add_argument("--action", required=True)
    ev_parser.add_argument("--result", required=True)
    ev_parser.add_argument("--goal", required=True)
    ev_parser.add_argument("--domain", default="general")

    # Override
    ov_parser = sub.add_parser("override", help="Record human override")
    ov_parser.add_argument("--eval-id", required=True)
    ov_parser.add_argument("--score", type=int, required=True)
    ov_parser.add_argument("--notes", default="")

    # Stats
    sub.add_parser("stats", help="Show calibration stats")
    sub.add_parser("rates", help="Show retry/escalation rates")

    # Recent
    rec_parser = sub.add_parser("recent", help="Show recent evaluations")
    rec_parser.add_argument("--limit", type=int, default=10)
    rec_parser.add_argument("--domain", default=None)

    args = parser.parse_args()
    evaluator = Evaluator()

    if args.command == "evaluate":
        result = evaluator.evaluate(args.action, args.result, args.goal, args.domain)
        print(f"Score: {result.score}/10")
        print(f"Decision: {result.decision}")
        print(f"Reasoning: {result.reasoning}")
        if result.suggestions:
            print(f"Suggestions:")
            for s in result.suggestions:
                print(f"  - {s}")
        if result.retry_strategy:
            print(f"Retry strategy: {result.retry_strategy}")

    elif args.command == "override":
        ok = evaluator.record_human_override(args.eval_id, args.score, args.notes)
        print("Recorded." if ok else "Evaluation not found.")

    elif args.command == "stats":
        stats = evaluator.get_calibration_stats()
        for k, v in stats.items():
            print(f"  {k}: {v}")

    elif args.command == "rates":
        rates = evaluator.get_retry_rate()
        for k, v in rates.items():
            print(f"  {k}: {v}")

    elif args.command == "recent":
        evals = evaluator.get_recent_evaluations(args.limit, args.domain)
        for e in evals:
            print(f"  [{e['eval_id'][:8]}] {e['domain']:10s} {e['score']}/10 "
                  f"{e['decision']:10s} {e['action'][:50]}")


if __name__ == "__main__":
    main()
