#!/usr/bin/env python3
"""
PostToolUse Hook — Evaluate Revit MCP operations through the cognitive core.

Fires after every Revit MCP create/place/wall/door/window operation.
Reads the tool name, input, and output from stdin and:
1. Calls evaluator.evaluate() with the action, result, and inferred goal
2. Persists the evaluation to cognitive.db
3. Outputs the score for Claude's context

This feeds the self-evaluation loop — every Revit operation gets scored,
building calibration data over time.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

LOG_FILE = Path("/mnt/d/_CLAUDE-TOOLS/logs/cognitive_hooks.log")


def log(msg: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{ts}] revit_eval: {msg}\n")


def extract_action_description(tool_name: str, tool_input: dict) -> str:
    """Convert MCP tool call to a human-readable action description."""
    method = tool_name.split("__")[-1] if "__" in tool_name else tool_name

    parts = [method]
    if isinstance(tool_input, dict):
        # Extract key params
        if "wallType" in tool_input or "wallTypeId" in tool_input:
            parts.append(f"wall type: {tool_input.get('wallType', tool_input.get('wallTypeId', ''))}")
        if "levelId" in tool_input or "level" in tool_input:
            parts.append(f"level: {tool_input.get('level', tool_input.get('levelId', ''))}")
        if "sheetNumber" in tool_input:
            parts.append(f"sheet: {tool_input['sheetNumber']}")
        if "viewName" in tool_input:
            parts.append(f"view: {tool_input['viewName']}")

    return " — ".join(parts)


def truncate_result(tool_output: str, max_len: int = 500) -> str:
    """Truncate tool output for evaluation context."""
    if not tool_output:
        return "No output"
    if len(tool_output) <= max_len:
        return tool_output
    return tool_output[:max_len] + "..."


def main():
    try:
        if sys.stdin.isatty():
            return
        data = json.load(sys.stdin)
    except Exception:
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    tool_output = data.get("tool_output", "")

    if not tool_name or "revit" not in tool_name.lower():
        return

    # Parse tool input
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except Exception:
            tool_input = {}

    action = extract_action_description(tool_name, tool_input)
    result = truncate_result(tool_output)

    # Infer goal from the method name
    method = tool_name.split("__")[-1] if "__" in tool_name else tool_name
    goal = f"Revit operation: {method}"

    try:
        from evaluator import Evaluator
        ev = Evaluator()
        evaluation = ev.evaluate(
            action=action,
            result=result,
            goal=goal,
            domain="revit",
            context={"tool_name": tool_name, "tool_input": tool_input},
        )

        log(f"Eval {evaluation.eval_id}: {action[:60]} → {evaluation.score}/10 "
            f"({evaluation.decision})")

        # Only output if score is noteworthy
        if evaluation.score < 7:
            print(f"Cognitive eval: {evaluation.score}/10 ({evaluation.decision}) — "
                  f"{evaluation.reasoning[:100]}")
            if evaluation.suggestions:
                print(f"  Suggestions: {'; '.join(evaluation.suggestions[:2])}")

    except Exception as e:
        log(f"Evaluation error: {e}")


if __name__ == "__main__":
    main()
