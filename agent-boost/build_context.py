#!/usr/bin/env python3
"""
Agent Context Builder
Generates a full context payload for sub-agents by combining:
1. Static agent preamble (rules, identity, tools)
2. Live system state
3. Memory corrections and preferences
4. Conversation context (passed as argument)
5. Task-specific instructions

Usage:
  python3 build_context.py "task description" ["project_name"] ["conversation_context"]

Output:
  Prints the full context payload to stdout for injection into agent prompts.
"""

import json
import sys
import subprocess
from pathlib import Path

TOOLS_DIR = Path("/mnt/d/_CLAUDE-TOOLS")
PREAMBLE_PATH = TOOLS_DIR / "agent-boost" / "agent_preamble.md"
SYSTEM_STATE_PATH = TOOLS_DIR / "system-bridge" / "live_state.json"


def load_preamble():
    """Load the static agent preamble."""
    try:
        return PREAMBLE_PATH.read_text()
    except Exception:
        return "## AGENT PREAMBLE\nPreamble file not found. Proceed with task.\n"


def load_system_state():
    """Load current system state."""
    try:
        with open(SYSTEM_STATE_PATH) as f:
            state = json.load(f)

        lines = ["## CURRENT SYSTEM STATE"]
        if "active_window" in state:
            lines.append(f"- Active Window: {state['active_window']}")
        if "memory_percent" in state:
            lines.append(f"- Memory Usage: {state['memory_percent']}%")
        if "monitors" in state:
            lines.append(f"- Monitors: {state['monitors']}")
        if "recent_files" in state:
            files = state["recent_files"][:5] if isinstance(state["recent_files"], list) else str(state["recent_files"])
            lines.append(f"- Recent Files: {files}")
        if "running_apps" in state:
            apps = state["running_apps"][:10] if isinstance(state["running_apps"], list) else str(state["running_apps"])
            lines.append(f"- Open Apps: {apps}")

        return "\n".join(lines) + "\n"
    except Exception:
        return "## SYSTEM STATE\nUnavailable.\n"


def load_memory_corrections():
    """
    Load critical corrections from memory DB.
    This queries the SQLite DB directly for high-importance corrections.
    """
    db_path = None
    # Try common memory DB locations
    candidates = [
        Path.home() / ".claude-memory" / "memory.db",
        TOOLS_DIR / "claude-memory" / "memory.db",
        Path.home() / "claude-memory" / "memory.db",
    ]

    for candidate in candidates:
        if candidate.exists():
            db_path = candidate
            break

    if not db_path:
        # Try to find it
        try:
            result = subprocess.run(
                ["find", "/home/weber", "-name", "memory.db", "-path", "*claude*memory*", "-type", "f"],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                db_path = Path(result.stdout.strip().split("\n")[0])
        except Exception:
            pass

    if not db_path:
        return "## CORRECTIONS\nMemory DB not found. Use MCP memory tools to load corrections.\n"

    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get high-importance corrections
        cursor.execute("""
            SELECT content FROM memories
            WHERE memory_type = 'error' AND importance >= 8
            ORDER BY importance DESC, created_at DESC
            LIMIT 10
        """)
        corrections = cursor.fetchall()

        # Get core preferences
        cursor.execute("""
            SELECT content FROM memories
            WHERE memory_type = 'preference' AND importance >= 8
            ORDER BY importance DESC
            LIMIT 5
        """)
        preferences = cursor.fetchall()

        conn.close()

        lines = ["## CRITICAL CORRECTIONS (from memory)"]
        for (content,) in corrections:
            # Extract just the key point, first 200 chars
            summary = content.strip()[:200].replace("\n", " ")
            lines.append(f"- {summary}")

        if preferences:
            lines.append("\n## KEY PREFERENCES (from memory)")
            for (content,) in preferences:
                summary = content.strip()[:300].replace("\n", " ")
                lines.append(f"- {summary}")

        return "\n".join(lines) + "\n"
    except Exception as e:
        return f"## CORRECTIONS\nFailed to load: {e}\n"


def build_context(task: str, project: str = "", conversation_context: str = ""):
    """Build the full context payload."""
    sections = []

    # 1. Preamble
    sections.append(load_preamble())

    # 2. System state
    sections.append(load_system_state())

    # 3. Memory corrections & preferences
    sections.append(load_memory_corrections())

    # 4. Conversation context (if provided)
    if conversation_context:
        sections.append(f"## CONVERSATION CONTEXT\n{conversation_context}\n")

    # 5. Project context
    if project:
        sections.append(f"## ACTIVE PROJECT: {project}\n")

    # 6. Task
    sections.append(f"## YOUR TASK\n\n{task}\n")

    # 7. Reminders
    sections.append("""## REMINDERS
- You have access to all MCP tools listed above
- Use memory tools to store anything important you learn
- Be thorough but concise in your response
- Flag blockers or follow-up items clearly
""")

    return "\n---\n\n".join(sections)


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "No specific task provided."
    project = sys.argv[2] if len(sys.argv) > 2 else ""
    context = sys.argv[3] if len(sys.argv) > 3 else ""

    payload = build_context(task, project, context)
    print(payload)
