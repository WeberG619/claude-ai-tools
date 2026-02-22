#!/usr/bin/env python3
"""
Alignment Hook — PreToolUse safety net for Task tool.

Runs as a Claude Code hook on the Task tool matcher.
Reads CLAUDE_TOOL_INPUT env var, compiles an alignment profile,
and outputs JSON with the alignment prefix.

This is Layer B of the alignment injection system — catches cases
where the main agent forgets to call compile_prompt().

Hook config (settings.json):
{
    "matcher": "Task",
    "hooks": [{
        "type": "command",
        "command": "python3 /mnt/d/_CLAUDE-TOOLS/agent-common-sense/alignment_hook.py",
        "timeout": 5,
        "statusMessage": "Compiling alignment profile..."
    }]
}
"""

import json
import os
import sys


def main():
    tool_input_raw = os.environ.get("CLAUDE_TOOL_INPUT", "{}")
    try:
        tool_input = json.loads(tool_input_raw)
    except json.JSONDecodeError:
        # Can't parse input, pass through
        print(json.dumps({"status": "pass"}))
        return

    # Only process Task tool calls with prompts
    prompt = tool_input.get("prompt", "")
    agent_type = tool_input.get("subagent_type", "")
    if not prompt:
        print(json.dumps({"status": "pass"}))
        return

    # Check if alignment is already injected (avoid double-injection)
    if "# Agent Execution Framework" in prompt or "# Common Sense Kernel" in prompt:
        print(json.dumps({"status": "pass"}))
        return

    try:
        from alignment import AlignmentCore
        core = AlignmentCore()
        result = core.pre_task_hook(tool_input)

        # Log the injection
        prefix = result.get("alignment_prefix", "")
        if prefix:
            msg = result.get("message", "Alignment compiled")
            print(json.dumps({
                "status": "pass",
                "message": msg,
            }), file=sys.stderr)

        # Always pass — this is advisory, not blocking
        print(json.dumps({"status": "pass"}))

    except Exception as e:
        # Never block on alignment errors
        print(json.dumps({"status": "pass"}), file=sys.stderr)
        print(json.dumps({"status": "pass"}))


if __name__ == "__main__":
    main()
