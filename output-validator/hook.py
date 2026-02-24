#!/usr/bin/env python3
"""
PostToolUse Hook — Validates sub-agent (Task tool) output against contracts.
Runs after every Task tool invocation. If validation fails, outputs a message
that Claude will see and can act on (retry).
"""

import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from validator import OutputValidator
from contracts import match_contract


def main():
    """Read tool output from stdin, validate, output result."""
    # Hook receives JSON on stdin with tool_name, tool_input, tool_output
    try:
        if sys.stdin.isatty():
            return
        data = json.load(sys.stdin)
    except Exception:
        return

    tool_name = data.get("tool_name", "")
    if tool_name != "Task":
        return

    tool_output = data.get("tool_output", "")
    tool_input = data.get("tool_input", {})

    if not tool_output or len(tool_output) < 20:
        return

    # Determine which contract to use based on agent type
    agent_type = ""
    if isinstance(tool_input, dict):
        agent_type = tool_input.get("subagent_type", "")
        description = tool_input.get("description", "")
    elif isinstance(tool_input, str):
        try:
            parsed = json.loads(tool_input)
            agent_type = parsed.get("subagent_type", "")
            description = parsed.get("description", "")
        except Exception:
            agent_type = ""
            description = ""

    contract = match_contract(agent_type=agent_type, task_type=description)
    if not contract:
        return

    # Validate
    validator = OutputValidator()
    result = validator.validate(tool_output, contract)

    if not result.passed:
        # Output validation failure for Claude to see
        print(f"VALIDATION FAILED ({contract.get('name', 'unknown')}): {result.summary()}")
        if contract.get("max_retries", 0) > 0:
            print(f"Contract allows {contract['max_retries']} retries. Consider retrying with more detail.")
    elif result.warnings:
        print(f"VALIDATION PASSED with warnings: {'; '.join(result.warnings)}")
    # Silent on clean pass


if __name__ == "__main__":
    main()
