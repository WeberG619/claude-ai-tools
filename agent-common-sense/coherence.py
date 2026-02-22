"""
Coherence Monitor v1.0
=======================
Lightweight post-step coherence checking for agent pipelines.
Detects when an agent's output has drifted from its stated objective.

After each pipeline step, compares the step's output against:
  1. The step's title/description (immediate coherence)
  2. The pipeline's overall goal (trajectory coherence)
  3. Known drift signals (structural coherence)

Usage:
    from coherence import CoherenceMonitor

    monitor = CoherenceMonitor()
    check = monitor.check_step_coherence(
        output=agent_output,
        step_title="Extract walls from PDF",
        step_description="Parse floor plan geometry",
        pipeline_goal="PDF to Revit model",
    )

    if check.recommendation == "halt":
        abort_pipeline()
"""

import re
import sqlite3
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# ─── DRIFT SIGNALS ─────────────────────────────────────────────

CONFUSION_SIGNALS = [
    re.compile(r"I(?:'m| am) not sure (?:what|how|if)", re.IGNORECASE),
    re.compile(r"I don(?:'t| not) (?:understand|know)", re.IGNORECASE),
    re.compile(r"I have no idea", re.IGNORECASE),
    re.compile(r"(?:Let me|I'll) start over", re.IGNORECASE),
    re.compile(r"I(?:'m| am) (?:confused|lost|stuck)", re.IGNORECASE),
    re.compile(r"(?:This|That) (?:doesn't|does not) make sense", re.IGNORECASE),
    re.compile(r"makes no sense", re.IGNORECASE),
    re.compile(r"I (?:can't|cannot) (?:figure out|determine|find)", re.IGNORECASE),
    re.compile(r"no idea (?:what|how|why)", re.IGNORECASE),
]

REFUSAL_SIGNALS = [
    re.compile(r"I (?:can't|cannot|won't|will not) (?:do|help|assist|perform)", re.IGNORECASE),
    re.compile(r"(?:not|isn't|is not) (?:possible|feasible|supported)", re.IGNORECASE),
    re.compile(r"(?:outside|beyond) (?:my|the) (?:scope|capability|abilities)", re.IGNORECASE),
]

APOLOGY_SIGNALS = [
    re.compile(r"I (?:apologize|am sorry|regret)", re.IGNORECASE),
    re.compile(r"Unfortunately,?\s+I", re.IGNORECASE),
    re.compile(r"I'm afraid I", re.IGNORECASE),
]

# Stop words to exclude from keyword extraction
STOP_WORDS = frozenset({
    "the", "and", "for", "with", "this", "that", "from", "have", "has",
    "are", "was", "were", "been", "being", "will", "would", "could",
    "should", "can", "may", "might", "shall", "must", "not", "but",
    "its", "it's", "they", "them", "their", "into", "also", "than",
    "then", "each", "only", "just", "more", "most", "some", "such",
    "very", "about", "over", "after", "before", "between", "through",
    "during", "without", "within", "along", "across", "where", "when",
    "which", "what", "how", "who", "whom", "whose", "there", "here",
    "all", "any", "both", "few", "other", "our", "out", "own", "same",
    "use", "used", "using", "make", "made", "does", "did", "done",
})


@dataclass
class CoherenceCheck:
    """Result of checking output coherence against the stated goal."""
    coherent: bool = True
    score: float = 1.0  # 0.0 (completely off-topic) to 1.0 (perfectly aligned)
    goal_keywords_found: int = 0
    total_goal_keywords: int = 0
    overlap_ratio: float = 0.0
    drift_indicators: list[str] = field(default_factory=list)
    recommendation: str = "proceed"  # proceed|warn|halt

    def to_dict(self) -> dict:
        return {
            "coherent": self.coherent,
            "score": round(self.score, 3),
            "overlap_ratio": round(self.overlap_ratio, 3),
            "drift_indicators": self.drift_indicators,
            "recommendation": self.recommendation,
        }


class CoherenceMonitor:
    """
    Lightweight post-step coherence checking.

    After each pipeline step, compares the step's output against
    the step's title/description and pipeline goal to detect drift.
    """

    THRESHOLD_WARN = 0.3   # Below this: warn
    THRESHOLD_HALT = 0.1   # Below this: halt pipeline
    MAX_OUTPUT_CHARS = 10000  # Only check first N chars

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._find_db()
        if self.db_path:
            try:
                self._ensure_schema()
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS coherence_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_name TEXT NOT NULL DEFAULT '',
                step_index INTEGER NOT NULL DEFAULT 0,
                agent_name TEXT NOT NULL DEFAULT '',
                coherence_score REAL NOT NULL DEFAULT 0.0,
                goal_keyword_overlap REAL NOT NULL DEFAULT 0.0,
                drift_indicators TEXT DEFAULT '[]',
                recommendation TEXT NOT NULL DEFAULT 'proceed',
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    # ─── MAIN API ──────────────────────────────────────────────

    def check_step_coherence(self, output: str, step_title: str,
                              step_description: str = "",
                              pipeline_goal: str = "",
                              expected_data_key: str = "") -> CoherenceCheck:
        """
        Main coherence check. Called after each pipeline step.

        Combines three signals:
          1. Keyword overlap between step description and output
          2. Drift indicators in output (confusion, refusal, apology)
          3. Structural coherence (expected outputs present)
        """
        check = CoherenceCheck()

        # Empty goal = can't evaluate
        if not step_title and not step_description and not pipeline_goal:
            check.recommendation = "proceed"
            return check

        # Truncate long output for performance
        output_trimmed = output[:self.MAX_OUTPUT_CHARS] if output else ""

        # Handle empty/very short output
        if len(output_trimmed.strip()) < 20:
            check.score = 0.05
            check.coherent = False
            check.drift_indicators.append("Output is empty or nearly empty")
            check.recommendation = "halt"
            return check

        # 1. Keyword overlap
        goal_text = f"{step_title} {step_description} {pipeline_goal}"
        goal_keywords = self._extract_keywords(goal_text)
        output_keywords = self._extract_keywords(output_trimmed)

        check.total_goal_keywords = len(goal_keywords)
        if goal_keywords:
            found = goal_keywords & output_keywords
            check.goal_keywords_found = len(found)
            check.overlap_ratio = len(found) / len(goal_keywords)
        else:
            check.overlap_ratio = 1.0  # No keywords to check against

        # 2. Drift signal detection
        check.drift_indicators = self.detect_drift_signals(output_trimmed)

        # 3. Structural coherence
        structural_score = self._check_structural_coherence(
            output_trimmed, expected_data_key
        )

        # Zero keyword overlap is itself a strong drift signal
        if check.total_goal_keywords > 3 and check.overlap_ratio == 0.0:
            check.drift_indicators.append("Zero keyword overlap with goal — output may be completely off-topic")
            # Zero overlap should suppress neutral structural score
            structural_score = min(structural_score, 0.2)

        # Combine scores
        # Weight: overlap 60%, structural 20%, drift penalty 20%
        drift_penalty = min(len(check.drift_indicators) * 0.15, 0.6)
        raw_score = (
            check.overlap_ratio * 0.6 +
            structural_score * 0.2 +
            (1.0 - drift_penalty) * 0.2
        )
        check.score = max(0.0, min(1.0, raw_score))
        check.coherent = check.score >= self.THRESHOLD_WARN

        # Determine recommendation
        if check.score < self.THRESHOLD_HALT:
            check.recommendation = "halt"
        elif check.score < self.THRESHOLD_WARN:
            check.recommendation = "warn"
        else:
            check.recommendation = "proceed"

        return check

    def check_trajectory_coherence(self, step_outputs: list[str],
                                    pipeline_goal: str) -> CoherenceCheck:
        """
        Check whether the sequence of outputs is converging toward the goal.

        Each step should add new goal-relevant keywords. If a step adds
        none, the trajectory is stalling.
        """
        check = CoherenceCheck()
        goal_keywords = self._extract_keywords(pipeline_goal)

        if not goal_keywords or not step_outputs:
            check.recommendation = "proceed"
            return check

        check.total_goal_keywords = len(goal_keywords)
        cumulative_found = set()
        stall_count = 0

        for i, output in enumerate(step_outputs):
            output_kw = self._extract_keywords(output[:self.MAX_OUTPUT_CHARS])
            new_found = (goal_keywords & output_kw) - cumulative_found
            if not new_found and i > 0:
                stall_count += 1
                check.drift_indicators.append(f"Step {i+1} added no new goal-relevant keywords")
            cumulative_found |= (goal_keywords & output_kw)

        check.goal_keywords_found = len(cumulative_found)
        check.overlap_ratio = len(cumulative_found) / len(goal_keywords) if goal_keywords else 1.0

        # Score based on coverage and stalls
        coverage_score = check.overlap_ratio
        stall_penalty = stall_count * 0.2
        check.score = max(0.0, coverage_score - stall_penalty)
        check.coherent = check.score >= self.THRESHOLD_WARN

        if check.score < self.THRESHOLD_HALT:
            check.recommendation = "halt"
        elif check.score < self.THRESHOLD_WARN:
            check.recommendation = "warn"
        else:
            check.recommendation = "proceed"

        return check

    # ─── DRIFT DETECTION ──────────────────────────────────────

    def detect_drift_signals(self, output: str) -> list[str]:
        """Scan output for known drift indicators."""
        signals = []

        # Check confusion signals
        for pattern in CONFUSION_SIGNALS:
            if pattern.search(output):
                signals.append(f"Confusion: '{pattern.pattern}'")
                break  # One confusion signal is enough

        # Check refusal signals
        for pattern in REFUSAL_SIGNALS:
            if pattern.search(output):
                signals.append(f"Refusal: '{pattern.pattern}'")
                break

        # Check apology signals
        for pattern in APOLOGY_SIGNALS:
            if pattern.search(output):
                signals.append(f"Apology/hedging detected")
                break

        # Check for excessive repetition (same phrase 3+ times)
        words = re.findall(r'[a-z]+', output.lower())
        if len(words) > 20:
            # Check for repeated 3-grams
            trigrams = [" ".join(words[i:i+3]) for i in range(len(words)-2)]
            trigram_counts = {}
            for tg in trigrams:
                trigram_counts[tg] = trigram_counts.get(tg, 0) + 1
            repeated = [tg for tg, c in trigram_counts.items() if c >= 3 and len(tg) > 10]
            if repeated:
                signals.append(f"Excessive repetition detected ({len(repeated)} phrases)")

        # Check output length vs typical
        if len(output.strip()) < 50:
            signals.append("Suspiciously short output")

        return signals

    # ─── HELPERS ───────────────────────────────────────────────

    def _extract_keywords(self, text: str) -> set[str]:
        """Extract meaningful keywords from text."""
        words = re.findall(r'[a-z]{3,}', text.lower())
        return {w for w in words if w not in STOP_WORDS and len(w) >= 3}

    def _check_structural_coherence(self, output: str, expected_data_key: str) -> float:
        """Check if output has expected structural elements."""
        if not expected_data_key:
            return 0.7  # No expectation = neutral score

        output_lower = output.lower()
        key_lower = expected_data_key.lower()

        # Check for common structural patterns by data key type
        checks = {
            "spec": ["dimension", "wall", "room", "floor", "width", "height", "length", "area"],
            "model": ["created", "placed", "built", "added", "element", "family", "instance"],
            "validation": ["pass", "fail", "valid", "error", "check", "verified", "issue"],
            "report": ["finding", "result", "summary", "recommendation", "conclusion", "analysis"],
            "data": ["{", "[", ":", "value", "key", "record"],
        }

        expected_terms = checks.get(key_lower, [key_lower])
        found = sum(1 for term in expected_terms if term in output_lower)
        return min(1.0, found / max(len(expected_terms) * 0.5, 1))

    # ─── LOGGING ──────────────────────────────────────────────

    def log_coherence(self, pipeline_name: str, step_index: int,
                       check: CoherenceCheck, agent_name: str = ""):
        """Log coherence check result to DB."""
        if not self.db_path:
            return
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = self._conn()
            conn.execute("""
                INSERT INTO coherence_log
                (pipeline_name, step_index, agent_name, coherence_score,
                 goal_keyword_overlap, drift_indicators, recommendation, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (pipeline_name, step_index, agent_name, check.score,
                  check.overlap_ratio, json.dumps(check.drift_indicators),
                  check.recommendation, now))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def get_stats(self, pipeline_name: str = "") -> dict:
        """Get coherence statistics."""
        if not self.db_path:
            return {"total": 0}
        conn = self._conn()
        sql = "SELECT * FROM coherence_log"
        params = []
        if pipeline_name:
            sql += " WHERE pipeline_name = ?"
            params.append(pipeline_name)
        sql += " ORDER BY timestamp DESC LIMIT 100"
        rows = conn.execute(sql, params).fetchall()
        conn.close()

        if not rows:
            return {"total": 0}

        scores = [r["coherence_score"] for r in rows]
        recs = [r["recommendation"] for r in rows]
        return {
            "total": len(rows),
            "avg_coherence_score": round(sum(scores) / len(scores), 3),
            "min_score": round(min(scores), 3),
            "halts": recs.count("halt"),
            "warns": recs.count("warn"),
            "proceeds": recs.count("proceed"),
        }


# ─── CLI ───────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Coherence Monitor v1.0")
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="Check text coherence against a goal")
    p_check.add_argument("--output", required=True, help="Agent output text or file path")
    p_check.add_argument("--goal", required=True, help="The step/pipeline goal")
    p_check.add_argument("--data-key", default="", help="Expected output type")

    p_stats = sub.add_parser("stats", help="Show coherence statistics")
    p_stats.add_argument("--pipeline", default="")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    monitor = CoherenceMonitor()

    if args.command == "check":
        text = args.output
        if Path(text).exists():
            text = Path(text).read_text()

        check = monitor.check_step_coherence(
            output=text,
            step_title=args.goal,
            expected_data_key=args.data_key,
        )
        print(f"Coherence Score: {check.score:.2f}")
        print(f"Recommendation: {check.recommendation}")
        print(f"Keyword overlap: {check.overlap_ratio:.1%} ({check.goal_keywords_found}/{check.total_goal_keywords})")
        if check.drift_indicators:
            print(f"Drift signals:")
            for d in check.drift_indicators:
                print(f"  - {d}")

    elif args.command == "stats":
        stats = monitor.get_stats(args.pipeline)
        print("Coherence Stats:")
        for k, v in stats.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
