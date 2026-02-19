"""
Self-Check Hooks v1.0
======================
Post-execution validation for individual agent outputs. Checks whether
an agent's output actually addresses its assigned task BEFORE the output
is returned to the pipeline or user.

Different from CoherenceMonitor: coherence checks between pipeline steps
(is step N's output relevant to step N+1?). Self-check validates a single
agent's output against its assigned task.

Usage:
    from selfcheck import SelfChecker

    checker = SelfChecker()
    result = checker.check(
        agent_output="Found 10 walls, 3 rooms, 2 doors",
        task_description="Extract walls and rooms from floor plan",
        agent_name="floor-plan-processor",
        expected_artifacts=["wall", "room", "dimension"],
    )

    if not result.passed:
        if result.retriable:
            # Retry with feedback
            retry_prompt = result.retry_feedback
        else:
            # Too bad to salvage
            log_failure(result)

CLI:
    python selfcheck.py check --task "Extract walls" --output "Found 10 walls, 3 rooms"
    python selfcheck.py stats --agent floor-plan-processor
"""

import re
import json
import hashlib
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Import drift signal patterns from coherence (not duplicated)
from coherence import CONFUSION_SIGNALS, REFUSAL_SIGNALS, APOLOGY_SIGNALS, STOP_WORDS


# ─── DATA CLASSES ──────────────────────────────────────────────

@dataclass
class SelfCheckResult:
    """Result of self-checking an agent's output against its task."""
    passed: bool = False
    score: float = 0.0  # 0.0 (total failure) to 1.0 (perfect)
    checks_run: dict = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    retriable: bool = False
    retry_feedback: str = ""

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "score": round(self.score, 3),
            "checks_run": self.checks_run,
            "failures": self.failures,
            "retriable": self.retriable,
            "retry_feedback": self.retry_feedback,
        }


# ─── SELF-CHECKER ──────────────────────────────────────────────

class SelfChecker:
    """
    Post-execution validation for agent outputs.

    Runs five weighted checks on an agent's output:
      1. task_addressal (0.35) — keyword overlap with task description
      2. completeness   (0.25) — not empty, not short, has structure
      3. drift_free     (0.20) — no confusion/refusal/apology signals
      4. artifacts      (0.10) — expected output terms mentioned
      5. scope_compliance (0.10) — permission scope verification
    """

    PASS_THRESHOLD = 0.4
    RETRY_THRESHOLD = 0.2  # Below this: not worth retrying

    # Check weights
    WEIGHTS = {
        "task_addressal": 0.35,
        "completeness": 0.25,
        "drift_free": 0.20,
        "artifacts": 0.10,
        "scope_compliance": 0.10,
    }

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._find_db()
        if self.db_path:
            try:
                self._ensure_schema()
            except Exception:
                self.db_path = None

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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS selfcheck_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL DEFAULT '',
                task_hash TEXT DEFAULT '',
                passed INTEGER NOT NULL DEFAULT 0,
                score REAL NOT NULL DEFAULT 0.0,
                checks_json TEXT DEFAULT '{}',
                failures_json TEXT DEFAULT '[]',
                retried INTEGER DEFAULT 0,
                checked_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    # ─── MAIN CHECK ────────────────────────────────────────────

    def check(self, agent_output: str, task_description: str,
              agent_name: str = "", expected_artifacts: Optional[list[str]] = None,
              permission_scope=None) -> SelfCheckResult:
        """
        Run all checks on agent output. Returns SelfCheckResult with
        pass/fail, score, and retry feedback if applicable.
        """
        result = SelfCheckResult()

        # Sanitize inputs
        output = (agent_output or "").strip()
        task = (task_description or "").strip()

        # Individual check scores
        checks = {}

        # 1. Task addressal — keyword overlap
        checks["task_addressal"] = self._check_task_addressal(output, task)

        # 2. Completeness — not empty/short, has structure
        checks["completeness"] = self._check_completeness(output)

        # 3. Drift-free — no confusion/refusal/apology
        checks["drift_free"] = self._check_drift_free(output)

        # 4. Artifact presence
        checks["artifacts"] = self._check_artifacts(output, expected_artifacts)

        # 5. Scope compliance
        checks["scope_compliance"] = self._check_scope_compliance(output, permission_scope)

        result.checks_run = checks

        # Calculate weighted score
        score = sum(checks[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        result.score = max(0.0, min(1.0, score))

        # Collect failures
        if checks["task_addressal"] < 0.3:
            result.failures.append("Output does not address the assigned task")
        if checks["completeness"] < 0.3:
            result.failures.append("Output is empty, too short, or lacks structure")
        if checks["drift_free"] < 0.5:
            result.failures.append("Output contains confusion, refusal, or apology signals")
        if expected_artifacts and checks["artifacts"] < 0.3:
            missing = self._find_missing_artifacts(output, expected_artifacts)
            if missing:
                result.failures.append(f"Missing expected artifacts: {', '.join(missing)}")
        if checks["scope_compliance"] < 0.5:
            result.failures.append("Output may violate permission scope")

        # Determine pass/fail/retriable
        if result.score >= self.PASS_THRESHOLD:
            result.passed = True
        elif result.score >= self.RETRY_THRESHOLD:
            result.retriable = True
            result.retry_feedback = self.build_retry_feedback(result, task)
        else:
            result.retriable = False

        # Log
        self.log_check(agent_name, result, task)

        return result

    # ─── INDIVIDUAL CHECKS ─────────────────────────────────────

    def _check_task_addressal(self, output: str, task: str) -> float:
        """Score how well the output addresses the task (keyword overlap)."""
        if not task:
            return 0.7  # No task = neutral score

        task_keywords = self._extract_keywords(task)
        if not task_keywords:
            return 0.7

        output_keywords = self._extract_keywords(output[:5000])
        if not output_keywords:
            return 0.0

        overlap = task_keywords & output_keywords
        ratio = len(overlap) / len(task_keywords)

        # Scale: 0% overlap = 0.0, 50% overlap = 0.7, 100% = 1.0
        if ratio >= 0.5:
            return 0.7 + (ratio - 0.5) * 0.6  # 0.7-1.0
        else:
            return ratio * 1.4  # 0.0-0.7

    def _check_completeness(self, output: str) -> float:
        """Score output completeness: not empty, not too short, has structure."""
        if not output:
            return 0.0

        length = len(output)

        # Very short = likely incomplete
        if length < 20:
            return 0.05
        if length < 50:
            return 0.2
        if length < 100:
            return 0.4

        score = 0.5  # Baseline for adequate length

        # Structure bonus: headings, lists, sections
        if re.search(r'^#+\s', output, re.MULTILINE):
            score += 0.15  # Has headings
        if re.search(r'^[-*]\s', output, re.MULTILINE):
            score += 0.1   # Has bullet lists
        if re.search(r'\d+[.)]\s', output):
            score += 0.1   # Has numbered items
        if len(output.split('\n')) > 3:
            score += 0.1   # Multi-line
        if length > 500:
            score += 0.05  # Substantial

        return min(1.0, score)

    def _check_drift_free(self, output: str) -> float:
        """Score absence of drift signals (confusion, refusal, apology)."""
        if not output:
            return 0.5  # Empty = neutral

        output_check = output[:5000]
        signals_found = 0

        for pattern in CONFUSION_SIGNALS:
            if pattern.search(output_check):
                signals_found += 1
                break

        for pattern in REFUSAL_SIGNALS:
            if pattern.search(output_check):
                signals_found += 1
                break

        for pattern in APOLOGY_SIGNALS:
            if pattern.search(output_check):
                signals_found += 1
                break

        # Score: 0 signals = 1.0, 1 = 0.5, 2 = 0.2, 3 = 0.0
        scores = {0: 1.0, 1: 0.5, 2: 0.2, 3: 0.0}
        return scores.get(signals_found, 0.0)

    def _check_artifacts(self, output: str, expected: Optional[list[str]]) -> float:
        """Score presence of expected artifacts in output."""
        if not expected:
            return 0.7  # No expectations = neutral

        output_lower = output.lower()
        found = sum(1 for a in expected if a.lower() in output_lower)

        if len(expected) == 0:
            return 0.7

        return found / len(expected)

    def _check_scope_compliance(self, output: str, permission_scope) -> float:
        """Delegate to permissions.verify_output_compliance if scope provided."""
        if permission_scope is None:
            return 0.7  # No scope = neutral

        try:
            from permissions import verify_output_compliance
            result = verify_output_compliance(output, permission_scope)
            if result.compliant:
                return 1.0
            # Scale by severity: high violations = 0.0, medium = 0.3
            high_count = sum(1 for v in result.violations if v.get("severity") == "high")
            if high_count > 0:
                return 0.0
            return 0.3
        except ImportError:
            return 0.7  # Module not available = neutral

    # ─── HELPERS ───────────────────────────────────────────────

    def _extract_keywords(self, text: str) -> set[str]:
        """Extract meaningful keywords from text."""
        words = re.findall(r'[a-z]{3,}', text.lower())
        return {w for w in words if w not in STOP_WORDS and len(w) >= 3}

    def _find_missing_artifacts(self, output: str, expected: list[str]) -> list[str]:
        """Return list of expected artifacts not found in output."""
        output_lower = output.lower()
        return [a for a in expected if a.lower() not in output_lower]

    # ─── RETRY FEEDBACK ───────────────────────────────────────

    def build_retry_feedback(self, result: SelfCheckResult, task: str) -> str:
        """Construct feedback prompt for retrying a failed check."""
        lines = []
        lines.append("Your previous output did not adequately address the task.")
        lines.append(f"Task: {task}")
        lines.append("")
        lines.append("Issues found:")
        for f in result.failures:
            lines.append(f"- {f}")
        lines.append("")
        lines.append(f"Score: {result.score:.2f} (minimum: {self.PASS_THRESHOLD})")
        lines.append("")
        lines.append("Please retry, focusing specifically on the task requirements above.")
        return "\n".join(lines)

    # ─── LOGGING ───────────────────────────────────────────────

    def log_check(self, agent_name: str, result: SelfCheckResult, task: str = ""):
        """Log self-check result to database."""
        if not self.db_path:
            return

        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            task_hash = hashlib.sha256(task.encode()).hexdigest()[:16] if task else ""

            conn = self._conn()
            conn.execute("""
                INSERT INTO selfcheck_log
                (agent_name, task_hash, passed, score, checks_json, failures_json, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                agent_name, task_hash,
                1 if result.passed else 0,
                result.score,
                json.dumps(result.checks_run),
                json.dumps(result.failures),
                now,
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def get_stats(self, agent_name: str = "") -> dict:
        """Get self-check statistics."""
        if not self.db_path:
            return {"total": 0}

        try:
            conn = self._conn()
            sql = "SELECT * FROM selfcheck_log"
            params = []
            if agent_name:
                sql += " WHERE agent_name = ?"
                params.append(agent_name)
            sql += " ORDER BY checked_at DESC LIMIT 100"
            rows = conn.execute(sql, params).fetchall()
            conn.close()

            if not rows:
                return {"total": 0}

            scores = [r["score"] for r in rows]
            passed = sum(1 for r in rows if r["passed"])
            return {
                "total": len(rows),
                "passed": passed,
                "failed": len(rows) - passed,
                "pass_rate": round(passed / len(rows), 3),
                "avg_score": round(sum(scores) / len(scores), 3),
                "min_score": round(min(scores), 3),
                "max_score": round(max(scores), 3),
            }
        except Exception:
            return {"total": 0}


# ─── CLI ───────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Self-Check Hooks v1.0")
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="Check output against task")
    p_check.add_argument("--task", required=True, help="Task description")
    p_check.add_argument("--output", required=True, help="Agent output text or file path")
    p_check.add_argument("--agent", default="", help="Agent name")
    p_check.add_argument("--artifacts", default="", help="Comma-separated expected artifacts")

    p_stats = sub.add_parser("stats", help="Show self-check statistics")
    p_stats.add_argument("--agent", default="")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    checker = SelfChecker()

    if args.command == "check":
        text = args.output
        if Path(text).exists():
            text = Path(text).read_text()

        artifacts = [a.strip() for a in args.artifacts.split(",") if a.strip()] if args.artifacts else None

        result = checker.check(
            agent_output=text,
            task_description=args.task,
            agent_name=args.agent,
            expected_artifacts=artifacts,
        )

        status = "PASSED" if result.passed else ("RETRIABLE" if result.retriable else "FAILED")
        print(f"Self-Check: {status}")
        print(f"Score: {result.score:.2f} (threshold: {checker.PASS_THRESHOLD})")
        print(f"Checks: {json.dumps(result.checks_run, indent=2)}")
        if result.failures:
            print(f"Failures:")
            for f in result.failures:
                print(f"  - {f}")
        if result.retry_feedback:
            print(f"\nRetry feedback:\n{result.retry_feedback}")

    elif args.command == "stats":
        stats = checker.get_stats(args.agent)
        print("Self-Check Stats:")
        for k, v in stats.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
