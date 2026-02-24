#!/usr/bin/env python3
"""
Adaptive Retry Engine — Strategy escalation for failed operations.

Strategy ladder:
  1. quick-fix  (2 attempts) — minimal change
  2. refactor   (1 attempt)  — read more context, different approach
  3. alternative (1 attempt) — completely different approach
  4. escalate   (1 attempt)  — detailed failure report for user

Logs all attempts to board.db retry_log table.
"""

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

STRATEGIES_FILE = Path(__file__).parent / "strategies.json"
BOARD_DB = Path("/mnt/d/_CLAUDE-TOOLS/task-board/board.db")


def _now() -> str:
    return datetime.now().isoformat()


def _load_strategies() -> Dict:
    """Load strategy definitions."""
    if STRATEGIES_FILE.exists():
        return json.loads(STRATEGIES_FILE.read_text())
    # Fallback defaults
    return {
        "strategies": [
            {"name": "quick-fix", "max_attempts": 2, "prompt_modifier": "Fix the specific error.", "timeout_multiplier": 1.0},
            {"name": "refactor", "max_attempts": 1, "prompt_modifier": "Try a different approach.", "timeout_multiplier": 1.5},
            {"name": "alternative", "max_attempts": 1, "prompt_modifier": "Try a completely different approach.", "timeout_multiplier": 2.0},
            {"name": "escalate", "max_attempts": 1, "prompt_modifier": "Prepare a failure report.", "timeout_multiplier": 1.0},
        ],
        "max_total_attempts": 5,
        "hard_timeout_minutes": 15,
    }


class RetryAttempt:
    """Record of a single retry attempt."""

    def __init__(self, strategy: str, attempt: int, success: bool,
                 error: str = "", duration: float = 0, context: Dict = None):
        self.strategy = strategy
        self.attempt = attempt
        self.success = success
        self.error = error
        self.duration = duration
        self.context = context or {}


class AdaptiveRetryLoop:
    """Executes operations with escalating retry strategies."""

    def __init__(self, task_id: str = None, operation: str = ""):
        self.task_id = task_id
        self.operation = operation
        self.config = _load_strategies()
        self.strategies = self.config["strategies"]
        self.max_total = self.config.get("max_total_attempts", 5)
        self.hard_timeout = self.config.get("hard_timeout_minutes", 15) * 60
        self.attempts: List[RetryAttempt] = []
        self.start_time = time.time()

    def should_continue(self) -> bool:
        """Check if we should keep retrying."""
        if len(self.attempts) >= self.max_total:
            return False
        if time.time() - self.start_time > self.hard_timeout:
            return False
        # Check if last attempt succeeded
        if self.attempts and self.attempts[-1].success:
            return False
        return True

    def current_strategy(self) -> Dict:
        """Get the current strategy based on attempt count."""
        attempt_count = len(self.attempts)
        cumulative = 0
        for strategy in self.strategies:
            cumulative += strategy.get("max_attempts", 1)
            if attempt_count < cumulative:
                return strategy
        # Past all strategies — return last one (escalate)
        return self.strategies[-1]

    def current_strategy_name(self) -> str:
        return self.current_strategy().get("name", "unknown")

    def current_prompt_modifier(self) -> str:
        return self.current_strategy().get("prompt_modifier", "")

    def attempt_number_in_strategy(self) -> int:
        """Get the attempt number within the current strategy."""
        strategy = self.current_strategy()
        cumulative = 0
        for s in self.strategies:
            if s["name"] == strategy["name"]:
                return len(self.attempts) - cumulative + 1
            cumulative += s.get("max_attempts", 1)
        return 1

    def record_attempt(self, success: bool, error: str = "", context: Dict = None) -> RetryAttempt:
        """Record a retry attempt."""
        duration = time.time() - (self.attempts[-1].duration if self.attempts else self.start_time)
        attempt = RetryAttempt(
            strategy=self.current_strategy_name(),
            attempt=len(self.attempts) + 1,
            success=success,
            error=error,
            duration=duration,
            context=context,
        )
        self.attempts.append(attempt)
        self._log_to_db(attempt)
        return attempt

    def build_retry_prompt(self, original_error: str, previous_errors: List[str] = None) -> str:
        """Build a prompt with strategy context for the next attempt."""
        strategy = self.current_strategy()
        parts = [strategy.get("prompt_modifier", "")]

        if original_error:
            parts.append(f"\nOriginal error:\n{original_error}")

        if previous_errors:
            parts.append("\nPrevious attempts that failed:")
            for i, err in enumerate(previous_errors, 1):
                parts.append(f"  Attempt {i}: {err[:200]}")

        parts.append(f"\nThis is strategy '{strategy['name']}', attempt {self.attempt_number_in_strategy()} of {strategy.get('max_attempts', 1)}.")
        parts.append(f"Total attempts so far: {len(self.attempts)} of {self.max_total} max.")

        return "\n".join(parts)

    def summary(self) -> str:
        """Generate a summary of all retry attempts."""
        if not self.attempts:
            return "No attempts made."

        lines = [f"Retry Summary for: {self.operation}"]
        lines.append(f"Total attempts: {len(self.attempts)}")
        lines.append(f"Total time: {time.time() - self.start_time:.1f}s")

        for a in self.attempts:
            status = "OK" if a.success else "FAIL"
            lines.append(f"  [{status}] Strategy: {a.strategy}, Attempt #{a.attempt}: {a.error[:100] if a.error else 'success'}")

        final = self.attempts[-1]
        if final.success:
            lines.append(f"\nResolved with strategy: {final.strategy}")
        else:
            lines.append(f"\nFailed after exhausting all strategies.")

        return "\n".join(lines)

    def _log_to_db(self, attempt: RetryAttempt):
        """Log attempt to board.db retry_log table."""
        if not BOARD_DB.exists():
            return
        try:
            conn = sqlite3.connect(str(BOARD_DB))
            conn.execute("""
                INSERT INTO retry_log (task_id, operation, strategy, attempt, success,
                                       error, duration_seconds, context, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.task_id, self.operation, attempt.strategy, attempt.attempt,
                1 if attempt.success else 0, attempt.error, attempt.duration,
                json.dumps(attempt.context), _now(),
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

    @staticmethod
    def get_history(operation: str = None, limit: int = 20) -> List[Dict]:
        """Get retry history from DB."""
        if not BOARD_DB.exists():
            return []
        try:
            conn = sqlite3.connect(str(BOARD_DB))
            conn.row_factory = sqlite3.Row
            if operation:
                rows = conn.execute("""
                    SELECT * FROM retry_log WHERE operation = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (operation, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM retry_log ORDER BY timestamp DESC LIMIT ?
                """, (limit,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def get_stats() -> Dict:
        """Get retry statistics."""
        if not BOARD_DB.exists():
            return {}
        try:
            conn = sqlite3.connect(str(BOARD_DB))
            total = conn.execute("SELECT COUNT(*) FROM retry_log").fetchone()[0]
            successes = conn.execute("SELECT COUNT(*) FROM retry_log WHERE success = 1").fetchone()[0]
            by_strategy = dict(conn.execute("""
                SELECT strategy, COUNT(*) FROM retry_log GROUP BY strategy
            """).fetchall())
            success_by_strategy = dict(conn.execute("""
                SELECT strategy, COUNT(*) FROM retry_log WHERE success = 1 GROUP BY strategy
            """).fetchall())
            conn.close()
            return {
                "total_attempts": total,
                "total_successes": successes,
                "success_rate": round(successes / total * 100, 1) if total else 0,
                "by_strategy": by_strategy,
                "success_by_strategy": success_by_strategy,
            }
        except Exception:
            return {}
