#!/usr/bin/env python3
"""
Post-Revit Operation Check

Called after Revit MCP operations to:
1. Log the operation for tracking
2. Surface relevant validation reminders
3. Suggest follow-up actions based on operation type
4. Track cumulative operations and recommend bim-validator when threshold reached
"""

import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# Log file for tracking operations
LOG_FILE = Path("/mnt/d/_CLAUDE-TOOLS/post-revit-check/operation_log.json")
SESSION_FILE = Path("/mnt/d/_CLAUDE-TOOLS/post-revit-check/session_tracker.json")

# Thresholds for triggering bim-validator recommendation
BIM_VALIDATOR_THRESHOLDS = {
    "operation_count": 5,        # After 5 element-creating operations
    "wall_count": 10,            # After 10 walls created
    "door_window_count": 5,      # After 5 doors/windows
    "batch_operation": True,     # After any batch operation
    "session_age_minutes": 30    # Max session age before reset
}

# Operation patterns and their follow-ups
OPERATION_FOLLOWUPS = {
    "createWall": {
        "validation": "Check wall position matches source/expected location",
        "next_steps": ["Verify endpoints connect at corners", "Check wall type is correct"],
        "auto_check": "getWallById to confirm placement"
    },
    "placeDoor": {
        "validation": "Verify door is hosted on correct wall",
        "next_steps": ["Check swing direction", "Verify door type"],
        "auto_check": "getDoorsByRoom to confirm"
    },
    "placeWindow": {
        "validation": "Verify window is hosted and at correct sill height",
        "next_steps": ["Check window type", "Verify rough opening"],
        "auto_check": "getWindowsByWall to confirm"
    },
    "placeViewOnSheet": {
        "validation": "Verify viewport position and no overlaps",
        "next_steps": ["Check viewport title visibility", "Verify scale"],
        "auto_check": "getViewportBoundingBoxes for sheet"
    },
    "createRoom": {
        "validation": "Verify room boundary is closed",
        "next_steps": ["Name the room", "Check room area"],
        "auto_check": "getRoomBoundaries to confirm"
    }
}


def get_session():
    """Get or create session tracker."""
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

    default_session = {
        "started": datetime.now().isoformat(),
        "operations": 0,
        "walls_created": 0,
        "doors_windows_created": 0,
        "other_elements": 0,
        "last_validation": None,
        "validator_triggered": False
    }

    if not SESSION_FILE.exists():
        return default_session

    try:
        with open(SESSION_FILE) as f:
            session = json.load(f)

        # Check if session is stale (> 30 minutes old)
        started = datetime.fromisoformat(session["started"])
        if datetime.now() - started > timedelta(minutes=BIM_VALIDATOR_THRESHOLDS["session_age_minutes"]):
            return default_session

        return session
    except:
        return default_session


def save_session(session: dict):
    """Save session tracker."""
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSION_FILE, 'w') as f:
        json.dump(session, f, indent=2)


def update_session(tool_name: str) -> dict:
    """Update session with new operation and return updated session."""
    session = get_session()
    session["operations"] += 1

    method = tool_name.lower()

    if "wall" in method and "create" in method:
        session["walls_created"] += 1
    elif "door" in method or "window" in method:
        session["doors_windows_created"] += 1
    elif "create" in method or "place" in method:
        session["other_elements"] += 1

    save_session(session)
    return session


def check_validator_threshold(session: dict) -> tuple[bool, str]:
    """Check if bim-validator should be recommended. Returns (should_trigger, reason)."""
    if session.get("validator_triggered"):
        return False, ""

    if session["operations"] >= BIM_VALIDATOR_THRESHOLDS["operation_count"]:
        return True, f"Created {session['operations']} elements this session"

    if session["walls_created"] >= BIM_VALIDATOR_THRESHOLDS["wall_count"]:
        return True, f"Created {session['walls_created']} walls"

    if session["doors_windows_created"] >= BIM_VALIDATOR_THRESHOLDS["door_window_count"]:
        return True, f"Created {session['doors_windows_created']} doors/windows"

    return False, ""


def mark_validator_triggered():
    """Mark that validator has been triggered to avoid repeat recommendations."""
    session = get_session()
    session["validator_triggered"] = True
    session["last_validation"] = datetime.now().isoformat()
    save_session(session)


def log_operation(tool_name: str, params: str, result: str):
    """Log operation to tracking file."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "params": params[:500] if params else "",
        "result_preview": result[:200] if result else ""
    }

    # Append to log (keep last 100 entries)
    log = []
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE) as f:
                log = json.load(f)
        except:
            log = []

    log.append(entry)
    log = log[-100:]  # Keep last 100

    with open(LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2)


def get_followup(tool_name: str) -> dict:
    """Get follow-up suggestions for an operation."""
    # Extract method name from tool (e.g., mcp__revit__createWall -> createWall)
    method = tool_name.split("__")[-1] if "__" in tool_name else tool_name

    # Check for matching pattern
    for pattern, followup in OPERATION_FOLLOWUPS.items():
        if pattern.lower() in method.lower():
            return followup

    # Default follow-up
    return {
        "validation": "Verify operation completed successfully",
        "next_steps": ["Check element exists in model"],
        "auto_check": "Visual verification recommended"
    }


def format_post_check(tool_name: str, followup: dict) -> str:
    """Format the post-operation check message."""
    lines = [
        "",
        "━━━ POST-REVIT CHECK ━━━",
        f"Operation: {tool_name}",
        f"Validation: {followup['validation']}",
        "Next steps:"
    ]

    for step in followup.get('next_steps', []):
        lines.append(f"  • {step}")

    lines.append(f"Auto-check: {followup.get('auto_check', 'N/A')}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)


def format_validator_alert(reason: str) -> str:
    """Format bim-validator recommendation alert."""
    return f"""
╔══════════════════════════════════════════════════════════════════╗
║  🔍 BIM VALIDATOR RECOMMENDED                                    ║
╠══════════════════════════════════════════════════════════════════╣
║  Reason: {reason:<54} ║
║                                                                  ║
║  Run: /verify-bim  OR  Task(bim-validator)                       ║
║                                                                  ║
║  This validates element placement accuracy and catches errors    ║
║  before they compound into larger issues.                        ║
╚══════════════════════════════════════════════════════════════════╝
"""


def main():
    """CLI entry point."""
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_params = os.environ.get("CLAUDE_TOOL_PARAMS", "")
    tool_result = os.environ.get("CLAUDE_TOOL_RESULT", "")

    # Also accept command line args
    if len(sys.argv) >= 2:
        tool_name = sys.argv[1]

    if not tool_name:
        return 0

    # Log the operation
    log_operation(tool_name, tool_params, tool_result)

    # Update session tracking
    session = update_session(tool_name)

    # Check if validator should be recommended
    should_validate, reason = check_validator_threshold(session)

    # Get and display follow-up
    followup = get_followup(tool_name)
    message = format_post_check(tool_name, followup)

    print(message, file=sys.stderr)

    # Print validator alert if threshold reached
    if should_validate:
        alert = format_validator_alert(reason)
        print(alert, file=sys.stderr)
        mark_validator_triggered()

    return 0


if __name__ == "__main__":
    sys.exit(main())
