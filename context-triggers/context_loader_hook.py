#!/usr/bin/env python3
"""
Context Loader Hook — UserPromptSubmit hook that detects when context
files should be loaded based on keyword triggers.

Reads user prompt, scans against context_map.yaml triggers, and suggests
loading relevant files. Tracks loaded contexts per session to avoid
double-loading.

Hook config (settings.json UserPromptSubmit):
{
    "type": "command",
    "command": "python3 /mnt/d/_CLAUDE-TOOLS/context-triggers/context_loader_hook.py",
    "timeout": 2,
    "statusMessage": "Checking context triggers..."
}

Input: JSON on stdin with {prompt, session_id}
Output: JSON {status: "pass", message: "..."} on stdout
"""

import json
import sys
from pathlib import Path

CONTEXT_MAP = Path("/mnt/d/_CLAUDE-TOOLS/context-triggers/context_map.yaml")
LOADED_STATE = Path("/mnt/d/_CLAUDE-TOOLS/context-triggers/loaded_contexts.json")


def load_context_map() -> list:
    """Load trigger definitions from context_map.yaml."""
    if not CONTEXT_MAP.exists():
        return []

    text = CONTEXT_MAP.read_text()
    triggers = []
    current = None

    for line in text.split("\n"):
        stripped = line.strip()

        if stripped.startswith("- id:"):
            if current:
                triggers.append(current)
            current = {"id": stripped.split(":", 1)[1].strip(), "keywords": []}

        elif stripped.startswith("- ") and current and "keywords" not in line:
            # keyword list item
            kw = stripped[2:].strip().strip('"').strip("'")
            if kw and current:
                current["keywords"].append(kw)

        elif stripped.startswith("file:") and current:
            current["file"] = stripped.split(":", 1)[1].strip()

        elif stripped.startswith("description:") and current:
            current["description"] = stripped.split(":", 1)[1].strip()

    if current:
        triggers.append(current)

    return triggers


def get_loaded_contexts(session_id: str) -> set:
    """Get set of context IDs already loaded this session."""
    try:
        if LOADED_STATE.exists():
            data = json.loads(LOADED_STATE.read_text())
            if data.get("session_id") == session_id:
                return set(data.get("loaded", []))
    except Exception:
        pass
    return set()


def mark_loaded(session_id: str, context_id: str):
    """Mark a context as loaded for this session."""
    try:
        data = {"session_id": session_id, "loaded": []}
        if LOADED_STATE.exists():
            existing = json.loads(LOADED_STATE.read_text())
            if existing.get("session_id") == session_id:
                data = existing

        data["session_id"] = session_id
        if context_id not in data.get("loaded", []):
            data.setdefault("loaded", []).append(context_id)

        LOADED_STATE.parent.mkdir(parents=True, exist_ok=True)
        LOADED_STATE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def check_triggers(prompt: str, session_id: str) -> list:
    """Check prompt against all triggers. Returns list of matched triggers."""
    triggers = load_context_map()
    loaded = get_loaded_contexts(session_id)
    prompt_lower = prompt.lower()

    matches = []
    for trigger in triggers:
        tid = trigger.get("id", "")
        if tid in loaded:
            continue

        keywords = trigger.get("keywords", [])
        for kw in keywords:
            if kw.lower() in prompt_lower:
                matches.append(trigger)
                break

    return matches


def main():
    """Hook entry point."""
    try:
        stdin_data = sys.stdin.read()
        hook_input = json.loads(stdin_data) if stdin_data.strip() else {}
    except Exception:
        print(json.dumps({"status": "pass"}))
        return

    prompt = hook_input.get("prompt", "")
    session_id = hook_input.get("session_id", "unknown")

    if not prompt:
        print(json.dumps({"status": "pass"}))
        return

    try:
        matches = check_triggers(prompt, session_id)

        if matches:
            suggestions = []
            for m in matches:
                mid = m.get("id", "unknown")
                filepath = m.get("file", "")
                desc = m.get("description", mid)
                suggestions.append(f"Load {mid} — read {filepath}")
                mark_loaded(session_id, mid)

            message = "Context trigger: " + "; ".join(suggestions)
            print(json.dumps({"status": "pass"}), file=sys.stderr)
            print(json.dumps({"status": "pass", "message": message}))
        else:
            print(json.dumps({"status": "pass"}))

    except Exception:
        # Fail silent — never block on context loading errors
        print(json.dumps({"status": "pass"}))


if __name__ == "__main__":
    main()
