#!/usr/bin/env python3
"""
Hook Runner for Pre-Flight Check
Lightweight script for Claude Code hooks integration.
Called before Revit MCP operations to surface relevant corrections.

Flow:
1. Rule Engine (deterministic) - can BLOCK operations
2. Correction Check (fuzzy) - warns about past mistakes
"""

import sys
import os
import json

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pre_flight_check import check_operation as fuzzy_check, format_warning_banner
from context_detector import detect_operation, should_check
from rule_engine import check_operation as rule_check, get_stats

# Cognitive compiled rules integration
COGNITIVE_RULES_FILE = "/mnt/d/_CLAUDE-TOOLS/cognitive-core/compiled_rules.md"


def _check_cognitive_rules(tool_name: str, params: dict) -> str:
    """Check cognitive compiled rules for relevant BLOCKING warnings.

    Reads compiled_rules.md and does keyword matching against the
    current operation. Returns warning text or empty string.
    """
    import re
    rules_path = COGNITIVE_RULES_FILE
    try:
        with open(rules_path) as f:
            content = f.read()
    except FileNotFoundError:
        return ""

    # Build context string from operation
    context = f"{tool_name} {json.dumps(params)}".lower()

    # Extract BLOCKING rules
    blocking_rules = re.findall(
        r'\*\*\[BLOCKING\]\*\*\s*(.*?)(?=\n\s*\n|\n-\s*\*\*\[|\Z)',
        content, re.DOTALL
    )

    matched = []
    # Check rules relevant to current operation
    for rule in blocking_rules:
        rule_lower = rule.lower()
        # Extract meaningful keywords (5+ chars, not common words)
        stopwords = {"which", "should", "would", "could", "about", "after",
                     "before", "their", "there", "these", "those", "other",
                     "wrong", "correction", "record", "claude"}
        keywords = [w for w in re.findall(r'\b\w{5,}\b', rule_lower)
                    if w not in stopwords][:20]
        # Count how many rule keywords appear in context
        hits = sum(1 for kw in keywords if kw in context)
        # Need at least 2 specific keyword matches
        if hits >= 2:
            first_line = rule.strip().split('\n')[0][:120]
            matched.append(first_line)

    if matched:
        lines = ["╔══ COGNITIVE COMPILED RULES ══╗"]
        for m in matched[:3]:
            lines.append(f"║ ⚠ {m[:70]}")
        lines.append("╚═════════════════════════════╝")
        return "\n".join(lines)

    return ""


def run_hook(tool_name: str = "", params: str = "") -> int:
    """
    Run pre-flight check for a hook invocation.

    Args:
        tool_name: Name of the tool being called
        params: JSON string of parameters

    Returns:
        0 for success/warnings, 1 for BLOCKED (rule engine)
    """
    # Parse params if provided
    param_dict = {}
    if params:
        try:
            param_dict = json.loads(params)
        except:
            pass

    # =========================================================================
    # PHASE 1: Rule Engine (Deterministic - can block)
    # =========================================================================
    allowed, rule_message = rule_check(tool_name, param_dict)

    if not allowed:
        # Rule violation with ERROR severity - BLOCK the operation
        print(rule_message, file=sys.stderr)
        return 1  # Non-zero exit = hook failure = operation blocked

    if rule_message:
        # Rule violation with WARN severity - show warning but allow
        print(rule_message, file=sys.stderr)

    # =========================================================================
    # PHASE 1.5: Cognitive Compiled Rules (keyword match from compiled_rules.md)
    # =========================================================================
    try:
        cognitive_warning = _check_cognitive_rules(tool_name, param_dict)
        if cognitive_warning:
            print(cognitive_warning, file=sys.stderr)
    except Exception:
        pass  # Never block due to cognitive rule check failure

    # =========================================================================
    # PHASE 2: Fuzzy Correction Check (Warns only)
    # =========================================================================
    # Build context string for fuzzy matching
    context_parts = []
    if tool_name:
        context_parts.append(tool_name)
    if param_dict:
        context_parts.append(json.dumps(param_dict))

    context = " ".join(context_parts)

    # Check if fuzzy check should run
    should_run, keywords = should_check(context)

    if should_run:
        result = fuzzy_check(context)
        if not result["safe"]:
            banner = format_warning_banner(result)
            print(banner, file=sys.stderr)

    return 0


def main():
    """CLI entry point for hook integration."""
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    params = os.environ.get("CLAUDE_TOOL_PARAMS", "")

    # Also accept command line args
    if len(sys.argv) >= 2:
        tool_name = sys.argv[1]
    if len(sys.argv) >= 3:
        params = sys.argv[2]

    return run_hook(tool_name, params)


if __name__ == "__main__":
    sys.exit(main())
