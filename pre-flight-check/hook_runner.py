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
