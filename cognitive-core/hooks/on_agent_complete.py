#!/usr/bin/env python3
"""
PostToolUse Hook — Extract self-evaluation from sub-agent output.

Fires after every Task tool completion. Looks for the Phase 4.5
self-eval pattern in the agent's output and persists it to cognitive.db.

Without this hook, agent self-evaluations exist only as text in reports.
This hook makes them structured, queryable, and available for calibration.

Expected pattern in agent output:
    **Self-Eval:** 8/10 — All walls placed correctly, verified via screenshot
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

LOG_FILE = Path("/mnt/d/_CLAUDE-TOOLS/logs/cognitive_hooks.log")

# Patterns to extract self-eval from agent output
SELF_EVAL_PATTERNS = [
    r"\*\*Self-Eval:?\*\*\s*(\d+)/10\s*[—–-]\s*(.+?)(?:\n|$)",
    r"Self-Eval(?:uation)?:\s*(\d+)/10\s*[—–-]\s*(.+?)(?:\n|$)",
    r"Score:\s*(\d+)/10\s*[—–-]\s*(.+?)(?:\n|$)",
    r"self.?eval.*?(\d+)\s*/\s*10.*?[—–-]\s*(.+?)(?:\n|$)",
]


def log(msg: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{ts}] agent_eval: {msg}\n")


def extract_self_eval(output: str) -> tuple:
    """Extract self-eval score and reasoning from agent output."""
    if not output:
        return None, None

    for pattern in SELF_EVAL_PATTERNS:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            reasoning = match.group(2).strip()
            if 1 <= score <= 10:
                return score, reasoning

    return None, None


def infer_domain(output: str, agent_type: str) -> str:
    """Infer evaluation domain from agent output and type."""
    text = f"{output} {agent_type}".lower()
    if any(w in text for w in ["revit", "wall", "sheet", "viewport", "bim", "model"]):
        return "revit"
    if any(w in text for w in ["code", "function", "class", "test", "build", "compile"]):
        return "code"
    if any(w in text for w in ["desktop", "window", "excel", "bluebeam", "browser"]):
        return "desktop"
    if any(w in text for w in ["pipeline", "workflow", "orchestrat"]):
        return "pipeline"
    return "general"


def extract_task_description(tool_input: dict) -> str:
    """Extract a task description from the tool input."""
    if isinstance(tool_input, dict):
        desc = tool_input.get("description", "")
        prompt = tool_input.get("prompt", "")
        return desc or prompt[:150]
    return "Sub-agent task"


def main():
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

    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except Exception:
            tool_input = {}

    if not tool_output or len(tool_output) < 20:
        return

    # Extract self-eval from output
    score, reasoning = extract_self_eval(tool_output)
    if score is None:
        return  # No self-eval found — agent didn't follow Phase 4.5

    agent_type = tool_input.get("subagent_type", "unknown")
    domain = infer_domain(tool_output, agent_type)
    task_desc = extract_task_description(tool_input)

    try:
        from evaluator import Evaluator
        ev = Evaluator()

        # Store as a proper evaluation
        evaluation = ev.evaluate(
            action=f"Agent ({agent_type}): {task_desc}",
            result=f"Self-eval: {score}/10 — {reasoning}",
            goal=task_desc,
            domain=domain,
        )

        log(f"Agent self-eval captured: {agent_type} scored {score}/10 "
            f"(cognitive eval: {evaluation.score}/10, domain: {domain})")

        # If agent self-eval diverges significantly from cognitive eval,
        # record it as a calibration data point
        if abs(score - evaluation.score) >= 3:
            ev.record_human_override(
                evaluation.eval_id,
                human_score=score,
                notes=f"Agent self-eval diverged: agent={score}, cognitive={evaluation.score}. "
                      f"Reasoning: {reasoning[:100]}"
            )
            log(f"Calibration point: agent says {score}, evaluator says {evaluation.score}")

    except Exception as e:
        log(f"Error persisting agent eval: {e}")


if __name__ == "__main__":
    main()
