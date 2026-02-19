"""
Claude Code hook integration for the Common Sense Engine.

Provides enhanced hook scripts that use the Common Sense Engine's
search backend directly instead of raw memory queries.

Hooks:
  - pre_action_hook: PreToolUse — checks corrections before risky operations
  - post_action_hook: PostToolUse — records outcomes for feedback loop
  - correction_detect_hook: UserPromptSubmit — detects+stores corrections

These replace/enhance the existing hooks in self-improvement-hooks/.

Usage:
    # As PreToolUse hook (reads stdin JSON with tool_name/tool_input):
    echo '{"tool_name":"Edit","tool_input":{"file_path":"/etc/config"}}' | python hooks.py pre

    # As PostToolUse hook:
    echo '{"tool_name":"Bash","tool_input":{"command":"git push"}}' | python hooks.py post

    # As UserPromptSubmit hook:
    echo '{"user_prompt":"No that is wrong..."}' | python hooks.py detect
"""

import json
import os
import sys
from pathlib import Path

# Ensure engine modules are importable
sys.path.insert(0, str(Path(__file__).parent))


# ─── RISK CLASSIFICATION ────────────────────────────────────────

RISK_PROFILES = {
    # Tool pattern → (risk_level, search_domains)
    "mcp__.*revit": ("high", ["revit", "bim"]),
    "mcp__.*bluebeam": ("medium", ["bluebeam", "pdf"]),
    "mcp__.*excel": ("medium", ["excel"]),
    "mcp__.*window": ("low", ["window"]),
    "Edit": ("medium", ["filesystem", "code"]),
    "Write": ("medium", ["filesystem", "code"]),
    "Bash": ("high", ["execution", "filesystem", "git", "deployment"]),
}

# Keywords that elevate risk
HIGH_RISK_KEYWORDS = [
    "delete", "remove", "drop", "truncate", "rm ", "rm -",
    "force", "reset --hard", "push --force", "clean -f",
    "deploy", "production", "send", "email", "publish",
    "overwrite", "destroy", "purge", "wipe",
]

# Keywords for domain-specific matching
DOMAIN_KEYWORDS = {
    "revit": ["revit", "wall", "floor", "level", "family", "viewport",
              "sheet", "mcp", "createwall", "getelements", "bim"],
    "git": ["git", "commit", "push", "branch", "merge", "rebase",
            "force-push", "reset", "checkout"],
    "filesystem": ["path", "file", "folder", "directory", "deploy",
                    "dll", "addin", "appdata"],
    "email": ["email", "gmail", "send", "recipient", "compose"],
    "deployment": ["deploy", "production", "staging", "release",
                    "install", "addin"],
    "window": ["window", "monitor", "screen", "display", "dpi",
               "coordinate", "position"],
    "excel": ["excel", "cell", "chart", "worksheet", "formula",
              "workbook"],
}


def classify_risk(tool_name: str, tool_input: dict) -> tuple[str, list[str]]:
    """Classify risk level and relevant domains for a tool call.

    Returns (risk_level, domains) where risk_level is "low"/"medium"/"high".
    """
    import re

    risk_level = "low"
    domains = set()

    # Match against tool patterns
    for pattern, (level, pattern_domains) in RISK_PROFILES.items():
        if re.match(pattern, tool_name, re.IGNORECASE):
            risk_level = max(risk_level, level, key=lambda x: ["low", "medium", "high"].index(x))
            domains.update(pattern_domains)

    # Check input content for high-risk keywords
    input_str = json.dumps(tool_input).lower()
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in input_str:
            risk_level = "high"
            break

    # Detect domains from input content
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in input_str for kw in keywords):
            domains.add(domain)

    return risk_level, list(domains)


def extract_search_query(tool_name: str, tool_input: dict) -> str:
    """Build a search query from tool name and input for correction lookup."""
    parts = [tool_name.replace("_", " ").replace("mcp__", "")]

    # Extract meaningful string values from input
    def extract_strings(obj, depth=0):
        if depth > 2:
            return
        if isinstance(obj, str) and 3 < len(obj) < 150:
            parts.append(obj)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and 3 < len(v) < 150:
                    parts.append(f"{k}: {v}")
                else:
                    extract_strings(v, depth + 1)
        elif isinstance(obj, list):
            for item in obj[:3]:
                extract_strings(item, depth + 1)

    extract_strings(tool_input)
    return " ".join(parts[:10])


# ─── PRE-ACTION HOOK ────────────────────────────────────────────

def pre_action_hook(tool_name: str, tool_input: dict) -> dict:
    """Check for relevant corrections before executing a tool.

    Uses the Common Sense Engine's search backend for better matching.
    Returns dict with warnings/corrections found.
    """
    risk_level, domains = classify_risk(tool_name, tool_input)

    # Low risk: skip check
    if risk_level == "low":
        return {"checked": True, "risk": "low", "corrections": []}

    # Build search query
    query = extract_search_query(tool_name, tool_input)

    # Try using CommonSense engine
    corrections = []
    try:
        from sense import CommonSense
        cs = CommonSense(project="general")

        result = cs.before(query)
        if result.blocked:
            corrections.append({
                "severity": "critical",
                "message": result.reason,
            })
        for warning in result.warnings:
            corrections.append({
                "severity": "high" if "[HIGH]" in warning else "medium",
                "message": warning,
            })
    except Exception:
        # Fallback: direct keyword search
        try:
            from search import KeywordSearch
            db_path = _find_db()
            if db_path:
                kw = KeywordSearch(db_path)
                results = kw.search(query, memory_type="correction", limit=5)
                for r in results:
                    if r.score > 0.3:
                        corrections.append({
                            "severity": "medium",
                            "message": r.content[:200],
                            "score": r.score,
                        })
        except Exception:
            pass

    return {
        "checked": True,
        "risk": risk_level,
        "domains": domains,
        "corrections": corrections,
    }


# ─── POST-ACTION HOOK ───────────────────────────────────────────

def post_action_hook(tool_name: str, tool_input: dict,
                     tool_output: str = "") -> dict:
    """Record tool execution context for potential feedback tracking.

    This doesn't store anything directly — it surfaces relevant
    corrections so Claude can call correction_helped() if applicable.
    """
    risk_level, domains = classify_risk(tool_name, tool_input)

    if risk_level == "low":
        return {"tracked": False, "reason": "low risk"}

    query = extract_search_query(tool_name, tool_input)

    # Check if any corrections were relevant to this action
    relevant = []
    try:
        from sense import CommonSense
        cs = CommonSense(project="general")
        result = cs.before(query)
        for c in result.corrections:
            relevant.append({
                "id": c.get("id"),
                "content": c.get("correct_approach", c.get("content", ""))[:150],
            })
    except Exception:
        pass

    if relevant:
        return {
            "tracked": True,
            "relevant_corrections": relevant,
            "instruction": (
                "These corrections were relevant to this action. "
                "If they helped, call correction_helped(id, True). "
                "If they didn't apply, call correction_helped(id, False)."
            ),
        }

    return {"tracked": False, "reason": "no relevant corrections"}


# ─── CORRECTION DETECTION HOOK ───────────────────────────────────

def correction_detect_hook(user_prompt: str) -> dict:
    """Detect and auto-capture corrections from user messages.

    Enhanced version that uses autocapture module for extraction.
    """
    try:
        from autocapture import CorrectionCapture

        db_path = _find_db()
        capture = CorrectionCapture(db_path=db_path)
        captured = capture.check_message(user_prompt)

        if captured and captured.confidence >= 0.6:
            return {
                "type": "correction_detected",
                "confidence": captured.confidence,
                "what_wrong": captured.what_wrong[:200],
                "correct_approach": captured.correct_approach[:200],
                "domain": captured.domain,
                "severity": captured.severity,
                "instruction": (
                    "CORRECTION DETECTED in user message. "
                    "1. Acknowledge the mistake. "
                    "2. Use memory_store_correction() to save it. "
                    "3. Apply the correct approach."
                ),
            }
    except Exception:
        pass

    return {"type": "no_correction"}


# ─── UTILITIES ───────────────────────────────────────────────────

def _find_db() -> str:
    """Locate the memory database."""
    candidates = [
        Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"),
        Path.home() / ".claude-memory" / "memories.db",
        Path("/mnt/d/_CLAUDE-TOOLS/claude-memory/memories.db"),
        Path.home() / ".claude" / "memory.db",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return ""


# ─── CLI ENTRY POINTS ───────────────────────────────────────────

def _run_pre_hook():
    """CLI entry for PreToolUse hook."""
    try:
        stdin_data = sys.stdin.read()
        if not stdin_data.strip():
            sys.exit(0)
        hook_input = json.loads(stdin_data)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    tool_name = hook_input.get('tool_name', '')
    tool_input = hook_input.get('tool_input', {})

    if not tool_name:
        sys.exit(0)

    result = pre_action_hook(tool_name, tool_input)

    if result.get("corrections"):
        output = {
            "type": "pre_action_correction_check",
            "tool": tool_name,
            "risk_level": result["risk"],
            "domains": result.get("domains", []),
            "warnings": [c["message"][:300] for c in result["corrections"][:3]],
        }
        print(json.dumps(output, indent=2))

    sys.exit(0)


def _run_post_hook():
    """CLI entry for PostToolUse hook."""
    try:
        stdin_data = sys.stdin.read()
        if not stdin_data.strip():
            sys.exit(0)
        hook_input = json.loads(stdin_data)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    tool_name = hook_input.get('tool_name', '')
    tool_input = hook_input.get('tool_input', {})
    tool_output = hook_input.get('tool_output', '')

    if not tool_name:
        sys.exit(0)

    result = post_action_hook(tool_name, tool_input, tool_output)

    if result.get("relevant_corrections"):
        output = {
            "type": "post_action_feedback_prompt",
            "tool": tool_name,
            "relevant_corrections": result["relevant_corrections"][:3],
            "instruction": result.get("instruction", ""),
        }
        print(json.dumps(output, indent=2))

    sys.exit(0)


def _run_detect_hook():
    """CLI entry for UserPromptSubmit hook."""
    try:
        stdin_data = sys.stdin.read()
        if not stdin_data.strip():
            sys.exit(0)
        hook_input = json.loads(stdin_data)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    user_prompt = hook_input.get('user_prompt', '')
    if not user_prompt:
        sys.exit(0)

    result = correction_detect_hook(user_prompt)

    if result.get("type") == "correction_detected":
        print(json.dumps(result))

    sys.exit(0)


def main():
    """CLI dispatcher."""
    if len(sys.argv) < 2:
        print("Usage: python hooks.py [pre|post|detect]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "pre":
        _run_pre_hook()
    elif command == "post":
        _run_post_hook()
    elif command == "detect":
        _run_detect_hook()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
