#!/usr/bin/env python3
"""
Session Start Script - BULLETPROOF daemon auto-start and state loading.
Called by Claude Code SessionStart hook on EVERY session.

This script ensures the system bridge daemon is ALWAYS running
and auto-loads relevant context based on detected project.
"""

import sys
from pathlib import Path

# Add base dir to path for imports
BASE_DIR = Path(r"D:\_CLAUDE-TOOLS\system-bridge")
ORCHESTRATION_DIR = Path(r"D:\_CLAUDE-TOOLS\orchestration")
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(ORCHESTRATION_DIR))

from daemon_manager import ensure_daemon_running
import json


def load_orchestration_context():
    """Load project-aware context from orchestration system."""
    try:
        from context_loader import load_context, format_output
        context = load_context()
        return format_output(context)
    except ImportError:
        return None
    except Exception as e:
        return f"Context loading error: {e}"


def main():
    """
    Main entry point - called by Claude Code hook.

    1. Ensures daemon is running (starts if needed)
    2. Loads orchestration context (project detection, knowledge triggers)
    3. Outputs system state for Claude to read
    4. Returns success message
    """
    result = ensure_daemon_running()

    # Report daemon status
    if result["action_taken"] == "started":
        print("Drop Zone System Ready! Daemon started fresh.")
    elif result["action_taken"] == "restarted":
        print("Drop Zone System Ready! Daemon restarted (was unhealthy).")
    else:
        print("Drop Zone System Ready! Commands: dzc, dropzone, revitzone, adz, raz")

    print("Claude Code + Revit integration loaded!")

    # Load orchestration context
    orchestration_output = load_orchestration_context()
    if orchestration_output:
        print(f"\n{orchestration_output}")

    # Output daemon status
    print(f"Daemon started - status: {result.get('status', 'unknown')}")

    # Output live state JSON for Claude to parse
    state_file = Path(r"D:\_CLAUDE-TOOLS\system-bridge\live_state.json")
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding='utf-8'))
            print(json.dumps(state, indent=2))
        except Exception as e:
            print(json.dumps({"error": f"Failed to read state: {e}"}))

    return 0


if __name__ == "__main__":
    sys.exit(main())
