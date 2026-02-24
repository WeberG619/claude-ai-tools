#!/usr/bin/env python3
"""
Alignment Hook — PreToolUse safety net for Task tool.

Runs as a Claude Code hook on the Task tool matcher.
Reads CLAUDE_TOOL_INPUT env var, compiles an alignment profile,
and outputs JSON with the alignment prefix.

This is Layer B of the alignment injection system — catches cases
where the main agent forgets to call compile_prompt().

Also injects per-agent tool scoping constraints (from tool_profiles.yaml
via tool_scoping.py) into the sub-agent prompt preamble.

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


# ─── TOOL SCOPING INJECTION ────────────────────────────────────────────────────

def _extract_agent_name(tool_input: dict) -> str:
    """
    Extract the agent name from the Task tool input.
    Checks: subagent_type, agent_name, and scans prompt for known agent names.
    """
    # Direct fields
    for field in ("subagent_type", "agent_name", "agent"):
        name = tool_input.get(field, "")
        if name and isinstance(name, str):
            return name.strip().lower()

    # Scan the prompt for "agent: <name>" patterns
    prompt = tool_input.get("prompt", "")
    if prompt:
        import re
        patterns = [
            r"(?:agent|role|subagent)[:\s]+([a-z][a-z0-9-]+)",
            r"(?:as|using)\s+(?:the\s+)?([a-z][a-z0-9-]+)(?:\s+agent)?",
        ]
        for pat in patterns:
            m = re.search(pat, prompt, re.IGNORECASE)
            if m:
                candidate = m.group(1).lower()
                # Basic sanity check: reasonable agent name length
                if 3 <= len(candidate) <= 40:
                    return candidate

    return ""


def _get_tool_scope_block(agent_name: str) -> str:
    """
    Build the tool scoping block to inject into sub-agent prompts.
    Returns empty string if tool_scoping is unavailable or agent has full access.
    """
    if not agent_name:
        return ""
    try:
        import sys as _sys
        import os as _os
        # Ensure the agent-common-sense directory is on the path
        _here = _os.path.dirname(_os.path.abspath(__file__))
        if _here not in _sys.path:
            _sys.path.insert(0, _here)

        from tool_scoping import get_tool_restriction_prompt, load_agent_profile
        profile = load_agent_profile(agent_name)

        # Skip injection for full/admin agents (no meaningful restrictions to inject)
        if profile.profile_name == "full":
            return ""

        block = get_tool_restriction_prompt(agent_name)
        return block
    except Exception:
        return ""


def _inject_tool_scope(prompt: str, agent_name: str) -> str:
    """
    Inject tool scoping block at the start of the prompt if not already present.
    Returns the (possibly modified) prompt.
    """
    if "## Tool Access Scope" in prompt or "Tool scope:" in prompt:
        # Already injected — skip
        return prompt

    scope_block = _get_tool_scope_block(agent_name)
    if not scope_block:
        return prompt

    separator = "\n\n---\n\n"
    return scope_block + separator + prompt


# ─── MAIN HOOK ─────────────────────────────────────────────────────────────────

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
    if not prompt:
        print(json.dumps({"status": "pass"}))
        return

    # Check if alignment is already injected (avoid double-injection)
    if "# Agent Execution Framework" in prompt or "# Common Sense Kernel" in prompt:
        print(json.dumps({"status": "pass"}))
        return

    # ── Tool scoping injection ──────────────────────────────────────────────
    agent_name = _extract_agent_name(tool_input)
    if agent_name:
        try:
            modified_prompt = _inject_tool_scope(prompt, agent_name)
            if modified_prompt != prompt:
                # Update the tool input with the scoped prompt
                tool_input["prompt"] = modified_prompt
                print(json.dumps({
                    "status": "pass",
                    "message": f"Tool scope injected for agent: {agent_name}",
                }), file=sys.stderr)
        except Exception:
            pass  # Tool scoping errors never block

    # ── Alignment injection ─────────────────────────────────────────────────
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

        # Agent routing suggestion
        try:
            from router import AgentRouter
            router = AgentRouter()
            matches = router.route(prompt, top_n=3)
            if matches and matches[0].score > 0.3:
                suggestions = ", ".join(
                    f"{m.name} ({m.score:.2f})" for m in matches
                )
                print(json.dumps({
                    "status": "pass",
                    "message": f"Suggested agents: {suggestions}",
                }), file=sys.stderr)
        except Exception:
            pass  # Router errors never block

        # Always pass — this is advisory, not blocking
        print(json.dumps({"status": "pass"}))

    except Exception:
        # Never block on alignment errors
        print(json.dumps({"status": "pass"}), file=sys.stderr)
        print(json.dumps({"status": "pass"}))


if __name__ == "__main__":
    main()
