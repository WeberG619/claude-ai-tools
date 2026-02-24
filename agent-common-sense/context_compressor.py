#!/usr/bin/env python3
"""
Context Compressor — Utility for compressing verbose tool results.

Not a hook (too slow for PostToolUse). Called by agents to manage context budget.

Usage:
    from context_compressor import summarize_tool_result, compress_json
    short = summarize_tool_result("mcp__excel-mcp__read_range", huge_json_string)
"""

import json
import re
from typing import Any, Optional


def summarize_tool_result(tool_name: str, result: str, max_chars: int = 500) -> str:
    """Compress a large tool result into a summary.

    Args:
        tool_name: The tool that produced the result
        result: Raw result string (may be JSON or plain text)
        max_chars: Target maximum characters

    Returns:
        Compressed summary string
    """
    if not result or len(result) <= max_chars:
        return result

    # Try JSON compression first
    try:
        data = json.loads(result)
        return compress_json(data, max_chars, tool_name)
    except (json.JSONDecodeError, TypeError):
        pass

    # Plain text compression: keep first 3 + last 3 lines
    return compress_text(result, max_chars)


def compress_json(data: Any, max_chars: int = 500, context: str = "") -> str:
    """Compress JSON data to a summary string.

    Strategies:
    - Dict: extract status/count/error keys, summarize nested structures
    - List: show count + first/last items
    - Scalar: return as-is
    """
    if isinstance(data, dict):
        return _compress_dict(data, max_chars)
    elif isinstance(data, list):
        return _compress_list(data, max_chars)
    else:
        return str(data)[:max_chars]


def compress_text(text: str, max_chars: int = 500) -> str:
    """Compress plain text: keep first 3 + last 3 lines, omit middle."""
    lines = text.strip().split("\n")
    if len(lines) <= 8:
        return text[:max_chars]

    head = lines[:3]
    tail = lines[-3:]
    omitted = len(lines) - 6

    parts = head + [f"  ... ({omitted} lines omitted) ..."] + tail
    result = "\n".join(parts)

    if len(result) > max_chars:
        return result[:max_chars - 20] + "\n... [truncated]"
    return result


def _compress_dict(data: dict, max_chars: int) -> str:
    """Compress a dict — prioritize status/error/count keys."""
    # Priority keys to always include
    priority_keys = ["status", "success", "error", "message", "count",
                     "total", "id", "name", "result", "action"]

    summary = {}

    # First pass: priority keys
    for key in priority_keys:
        if key in data:
            val = data[key]
            if isinstance(val, (str, int, float, bool, type(None))):
                summary[key] = val
            elif isinstance(val, list):
                summary[key] = f"[{len(val)} items]"
            elif isinstance(val, dict):
                summary[key] = f"{{{len(val)} keys}}"

    # Second pass: remaining keys (abbreviated)
    remaining = {k: v for k, v in data.items() if k not in summary}
    if remaining:
        for key, val in remaining.items():
            if len(json.dumps(summary, default=str)) > max_chars - 100:
                summary["_remaining"] = f"... +{len(remaining)} more keys"
                break
            if isinstance(val, (str, int, float, bool, type(None))):
                if isinstance(val, str) and len(val) > 80:
                    summary[key] = val[:77] + "..."
                else:
                    summary[key] = val
            elif isinstance(val, list):
                summary[key] = f"[{len(val)} items]"
            elif isinstance(val, dict):
                summary[key] = f"{{{len(val)} keys}}"

    result = json.dumps(summary, indent=2, default=str)
    if len(result) > max_chars:
        return result[:max_chars - 20] + "\n... [truncated]"
    return result


def _compress_list(data: list, max_chars: int) -> str:
    """Compress a list — show count + first/last items."""
    n = len(data)
    if n == 0:
        return "[]"
    if n <= 3:
        result = json.dumps(data, default=str)
        return result[:max_chars] if len(result) > max_chars else result

    first = json.dumps(data[0], default=str)[:150]
    last = json.dumps(data[-1], default=str)[:150]

    return f"[{n} items, first: {first}, last: {last}]"


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token)."""
    return len(text) // 4


def budget_report(sections: dict) -> str:
    """Generate a context budget report.

    Args:
        sections: Dict of {section_name: content_string}

    Returns:
        Formatted budget report
    """
    total = 0
    lines = ["Context Budget:"]
    for name, content in sections.items():
        chars = len(content) if content else 0
        tokens = estimate_tokens(content) if content else 0
        total += tokens
        lines.append(f"  {name:30s} {chars:6d} chars  ~{tokens:5d} tokens")

    lines.append(f"  {'TOTAL':30s} {'':6s}       ~{total:5d} tokens")
    return "\n".join(lines)


if __name__ == "__main__":
    # Demo
    big_json = json.dumps({
        "status": "success",
        "data": [{"id": i, "name": f"item_{i}", "value": i * 100} for i in range(50)],
        "metadata": {"page": 1, "total": 500, "query": "test"},
        "error": None,
    })

    print("=== JSON compression ===")
    print(f"Original: {len(big_json)} chars")
    compressed = summarize_tool_result("test_tool", big_json)
    print(f"Compressed: {len(compressed)} chars")
    print(compressed)

    print("\n=== Text compression ===")
    big_text = "\n".join([f"Line {i}: {'x' * 80}" for i in range(100)])
    print(f"Original: {len(big_text)} chars")
    compressed = summarize_tool_result("test_tool", big_text)
    print(f"Compressed: {len(compressed)} chars")
    print(compressed)

    print("\n=== Budget report ===")
    print(budget_report({
        "kernel": "x" * 4000,
        "corrections": "x" * 2000,
        "strong_agent": "x" * 3000,
        "task_context": "x" * 1000,
    }))
