#!/usr/bin/env python3
"""
Stop Hook — Cognitive session reflection.

Fires at session end, AFTER the existing session_end_hook.py has
exported the conversation and updated brain.json. This hook:
1. Reads session data from brain.json (just updated by session_end_hook)
2. Reads the operation log for Revit operations this session
3. Calls reflector.reflect() to score the session and update goals
4. Writes cognitive state (goals, last reflection) back to brain.json
   so the NEXT session's briefing includes cognitive context

This is what closes the cross-session learning loop.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add cognitive core to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BRAIN_FILE = Path("/mnt/d/_CLAUDE-TOOLS/brain-state/brain.json")
OPERATION_LOG = Path("/mnt/d/_CLAUDE-TOOLS/post-revit-check/operation_log.json")
LOG_FILE = Path("/mnt/d/_CLAUDE-TOOLS/logs/cognitive_hooks.log")


def log(msg: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{ts}] session_end: {msg}\n")


def get_session_data() -> dict:
    """Extract session data from brain.json and operation logs."""
    session_data = {
        "session_id": "",
        "goals_stated": [],
        "actions_taken": [],
        "corrections_applied": 0,
        "errors_encountered": [],
        "duration_minutes": 0,
    }

    # Read brain.json for session info
    try:
        if BRAIN_FILE.exists():
            brain = json.loads(BRAIN_FILE.read_text())
            last = brain.get("last_session", {})
            session_data["session_id"] = last.get("session_id", "")

            # Extract active task as a goal
            checkpoint = brain.get("session_checkpoint", {})
            active_task = checkpoint.get("active_task", "")
            if active_task:
                session_data["goals_stated"].append(active_task[:150])

            # Extract open items
            open_items = last.get("open_items", "")
            if open_items and open_items != active_task:
                session_data["goals_stated"].append(open_items[:150])
    except Exception as e:
        log(f"Error reading brain.json: {e}")

    # Read Revit operation log for actions taken this session
    try:
        if OPERATION_LOG.exists():
            ops = json.loads(OPERATION_LOG.read_text())
            # Get operations from the last hour (approximate session)
            recent_ops = []
            cutoff = datetime.now().timestamp() - 3600
            for op in ops:
                try:
                    op_time = datetime.fromisoformat(op["timestamp"]).timestamp()
                    if op_time > cutoff:
                        recent_ops.append(op)
                except (ValueError, KeyError):
                    pass

            for op in recent_ops:
                tool = op.get("tool", "unknown")
                session_data["actions_taken"].append(f"Revit: {tool}")
                if "error" in op.get("result_preview", "").lower():
                    session_data["errors_encountered"].append(
                        f"{tool}: {op.get('result_preview', '')[:80]}"
                    )
    except Exception as e:
        log(f"Error reading operation log: {e}")

    return session_data


def write_cognitive_to_brain(reflection):
    """Write cognitive state back to brain.json for next session's briefing."""
    try:
        if not BRAIN_FILE.exists():
            return

        brain = json.loads(BRAIN_FILE.read_text())

        # Add cognitive section
        brain["cognitive"] = {
            "last_reflection": {
                "quality_score": reflection.quality_score,
                "momentum": reflection.momentum,
                "summary": reflection.summary[:200],
                "goals_achieved": reflection.goals_achieved[:3],
                "recommendations": reflection.recommendations[:3],
                "timestamp": datetime.now().isoformat(),
            },
        }

        # Add active goals from cognitive.db
        from reflector import SessionReflector
        ref = SessionReflector()
        goals = ref.get_active_goals()
        if goals:
            brain["cognitive"]["active_goals"] = [
                {
                    "title": g["title"][:100],
                    "progress": g["progress"],
                    "status": g["status"],
                }
                for g in goals[:5]
            ]

        BRAIN_FILE.write_text(json.dumps(brain, indent=2))
        log("Wrote cognitive state to brain.json")

    except Exception as e:
        log(f"Error writing to brain.json: {e}")


def main():
    try:
        session_data = get_session_data()

        # Only reflect if we have meaningful data
        if not session_data["goals_stated"] and not session_data["actions_taken"]:
            log("No meaningful session data — skipping reflection")
            print("Cognitive: No session data to reflect on")
            return

        from reflector import SessionReflector
        reflector = SessionReflector()
        reflection = reflector.reflect(session_data)

        # Write back to brain.json
        write_cognitive_to_brain(reflection)

        log(f"Reflection complete: {reflection.quality_score}/10, "
            f"momentum={reflection.momentum}")
        print(f"Cognitive reflection: {reflection.quality_score}/10 "
              f"({reflection.momentum}) — {reflection.summary[:80]}")

    except Exception as e:
        log(f"Hook error: {e}")
        # Never block session end


if __name__ == "__main__":
    main()
