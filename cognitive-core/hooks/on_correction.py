#!/usr/bin/env python3
"""
UserPromptSubmit Hook — Calibrate evaluator from corrections.

Fires on every user message. When a correction is detected:
1. Finds the most recent evaluation in cognitive.db
2. Calls record_human_override() with a low score (the user had to correct us)
3. This trains the evaluator to adjust its scoring over time

Also detects positive feedback and records it as success confirmation.

This is the calibration loop — without it, the evaluator never learns
whether it over- or under-scores.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

LOG_FILE = Path("/mnt/d/_CLAUDE-TOOLS/logs/cognitive_hooks.log")

# Correction patterns (subset — full list in detect_correction_hook.py)
CORRECTION_PATTERNS = [
    r"no[,.]?\s*that'?s\s*(wrong|incorrect|not\s*right)",
    r"actually[,.]",
    r"no[,.]?\s*i\s*meant",
    r"wrong\s*(approach|way)",
    r"you\s*should\s*have",
    r"you\s*made\s*a\s*mistake",
    r"don'?t\s*do\s*that",
    r"stop\s*doing\s*that",
    r"you'?re\s*(wrong|mistaken)",
    r"no[,!]+\s*no[,!]*",
]

# Positive patterns (success confirmation)
POSITIVE_PATTERNS = [
    r"\b(perfect|excellent|great\s*job|well\s*done|nice|good\s*job)\b",
    r"\bthat'?s\s*(right|correct|exactly|perfect)\b",
    r"\byou\s*nailed\s*it\b",
    r"\blooks?\s*(good|great|perfect)\b",
]


def log(msg: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{ts}] correction: {msg}\n")


def detect_intent(message: str) -> tuple:
    """Detect correction or positive feedback. Returns (type, matched)."""
    if not message or len(message) > 500:
        return None, []

    msg_lower = message.lower()

    # Check corrections first
    for pattern in CORRECTION_PATTERNS:
        if re.search(pattern, msg_lower):
            return "correction", [pattern]

    # Check positive feedback
    for pattern in POSITIVE_PATTERNS:
        if re.search(pattern, msg_lower):
            return "positive", [pattern]

    return None, []


def get_most_recent_evaluation():
    """Get the most recent evaluation from cognitive.db."""
    import sqlite3
    db_path = Path(__file__).parent.parent / "cognitive.db"
    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT id, score, domain, action, created_at
            FROM evaluations
            WHERE human_override_score IS NULL
            ORDER BY created_at DESC
            LIMIT 1
        """).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def main():
    try:
        stdin_data = sys.stdin.read()
        if not stdin_data.strip():
            return
        hook_input = json.loads(stdin_data)
    except (json.JSONDecodeError, Exception):
        return

    user_prompt = hook_input.get("user_prompt", "")
    if not user_prompt:
        return

    intent, patterns = detect_intent(user_prompt)
    if not intent:
        return

    recent_eval = get_most_recent_evaluation()

    if intent == "correction" and recent_eval:
        # User corrected us — our self-score was too high
        from evaluator import Evaluator
        ev = Evaluator()
        # Correction implies real score is ~3/10 (we got it wrong)
        human_score = 3
        success = ev.record_human_override(
            recent_eval["id"],
            human_score=human_score,
            notes=f"User correction detected: {user_prompt[:100]}"
        )
        if success:
            delta = human_score - recent_eval["score"]
            log(f"Calibration: eval {recent_eval['id']} self={recent_eval['score']} "
                f"human={human_score} delta={delta} domain={recent_eval['domain']}")
            print(f"Cognitive calibration: self-score {recent_eval['score']} "
                  f"→ human override {human_score} (domain: {recent_eval['domain']})")

    elif intent == "positive" and recent_eval:
        # User confirmed our work — our self-score was about right
        from evaluator import Evaluator
        ev = Evaluator()
        # Positive feedback confirms score of 8+
        human_score = max(recent_eval["score"], 8)
        success = ev.record_human_override(
            recent_eval["id"],
            human_score=human_score,
            notes=f"Positive feedback detected: {user_prompt[:100]}"
        )
        if success:
            log(f"Positive confirmation: eval {recent_eval['id']} confirmed at {human_score}")

        # Also store as known-good pattern (lightweight direct DB write)
        try:
            import sqlite3
            db_path = "/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"
            conn = sqlite3.connect(db_path)
            action = recent_eval.get("action", "unknown")
            domain = recent_eval.get("domain", "general")
            conn.execute("""
                INSERT INTO memories (content, summary, memory_type, project, tags, importance, created_at, accessed_at, domain, source, status)
                VALUES (?, ?, 'pattern', ?, 'known-good,success,positive', 8, datetime('now'), datetime('now'), ?, 'cognitive-core', 'active')
            """, (
                f"SUCCESS PATTERN: {action}. User confirmed: {user_prompt[:100]}",
                f"Known-good: {action[:80]}",
                domain,
                domain,
            ))
            conn.commit()
            conn.close()
            log(f"Stored known-good pattern for action: {action[:50]}")
        except Exception as e:
            log(f"Could not store known-good: {e}")


if __name__ == "__main__":
    main()
