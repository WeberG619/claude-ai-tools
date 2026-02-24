#!/usr/bin/env python3
"""
Agent Schema Validator — Validates YAML frontmatter in agent .md files.

Required fields: name, description, triggers (list), tier (read-only|write|admin)
Optional fields: tool_restrictions, color, squad, receives_from, hands_off_to

CLI: python3 agent_schema.py              # validate all agents
     python3 agent_schema.py --fix        # add missing fields with defaults
     python3 agent_schema.py --json       # output as JSON
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None

AGENTS_DIR = Path.home() / ".claude" / "agents"

REQUIRED_FIELDS = {"name", "description", "triggers", "tier"}
OPTIONAL_FIELDS = {"tool_restrictions", "color", "squad", "receives_from", "hands_off_to"}
VALID_TIERS = {"read-only", "write", "admin"}
VALID_COLORS = {"red", "orange", "yellow", "green", "blue", "purple", "pink", "gray",
                 "cyan", "teal", "gold", "brown", "magenta", "white", "black"}


def parse_yaml_frontmatter(filepath: Path) -> Tuple[Optional[Dict], str]:
    """Extract YAML frontmatter from a .md file. Returns (frontmatter_dict, body).

    Handles Claude Code agent format where frontmatter may contain
    Examples: blocks with multi-line XML-like content.
    """
    content = filepath.read_text(encoding="utf-8", errors="replace")

    if filepath.suffix == ".yaml":
        # Pure YAML file — parse entire content
        try:
            data = _parse_agent_fields(content)
            return data if data else None, ""
        except Exception:
            return None, content

    # Markdown files — look for --- delimited frontmatter
    if not content.startswith("---"):
        return None, content

    end = content.find("\n---", 3)
    if end == -1:
        return None, content

    yaml_block = content[3:end].strip()
    body = content[end + 4:]

    try:
        data = _parse_agent_fields(yaml_block)
        return data if data else None, body
    except Exception:
        return None, content


def _parse_agent_fields(text: str) -> Dict:
    """Extract known agent fields from frontmatter text.

    Robust against Claude Code agent format which includes Examples: blocks,
    XML-like tags, and multi-line content that breaks standard YAML parsers.
    Extracts only the fields we care about via targeted regex.
    """
    result = {}

    # name: value (single line)
    m = re.search(r'^name:\s*(.+)$', text, re.MULTILINE)
    if m:
        result["name"] = m.group(1).strip().strip('"').strip("'")

    # description: value (single line — first line only)
    m = re.search(r'^description:\s*(.+)$', text, re.MULTILINE)
    if m:
        result["description"] = m.group(1).strip().strip('"').strip("'")

    # tier: value
    m = re.search(r'^tier:\s*(.+)$', text, re.MULTILINE)
    if m:
        result["tier"] = m.group(1).strip().strip('"').strip("'")

    # color: value
    m = re.search(r'^color:\s*(.+)$', text, re.MULTILINE)
    if m:
        result["color"] = m.group(1).strip().strip('"').strip("'")

    # squad: value
    m = re.search(r'^squad:\s*(.+)$', text, re.MULTILINE)
    if m:
        result["squad"] = m.group(1).strip().strip('"').strip("'")

    # triggers: [inline list] or triggers:\n  - item\n  - item
    m = re.search(r'^triggers:\s*\[([^\]]+)\]', text, re.MULTILINE)
    if m:
        items = [v.strip().strip('"').strip("'") for v in m.group(1).split(",") if v.strip()]
        result["triggers"] = items
    else:
        # Multi-line list format
        m = re.search(r'^triggers:\s*$', text, re.MULTILINE)
        if m:
            items = []
            remaining = text[m.end():]
            for line in remaining.split("\n"):
                stripped = line.strip()
                if stripped.startswith("- "):
                    items.append(stripped[2:].strip().strip('"').strip("'"))
                elif stripped and not stripped.startswith("#"):
                    break
            if items:
                result["triggers"] = items

    # tool_restrictions: [inline] or multi-line
    m = re.search(r'^tool_restrictions:\s*\[([^\]]+)\]', text, re.MULTILINE)
    if m:
        items = [v.strip().strip('"').strip("'") for v in m.group(1).split(",") if v.strip()]
        result["tool_restrictions"] = items

    return result


def validate_agent(filepath: Path) -> List[str]:
    """Validate an agent file. Returns list of issues (empty = valid)."""
    issues = []
    fm, _ = parse_yaml_frontmatter(filepath)

    if fm is None:
        issues.append("missing YAML frontmatter")
        return issues

    for field in REQUIRED_FIELDS:
        if field not in fm:
            issues.append(f"missing required field: {field}")

    if "triggers" in fm:
        if not isinstance(fm["triggers"], list):
            issues.append("triggers must be a list")
        elif len(fm["triggers"]) == 0:
            issues.append("triggers list is empty")

    if "tier" in fm:
        if fm["tier"] not in VALID_TIERS:
            issues.append(f"invalid tier '{fm['tier']}' — must be one of {VALID_TIERS}")

    if "color" in fm and fm["color"] not in VALID_COLORS:
        issues.append(f"invalid color '{fm['color']}' — must be one of {VALID_COLORS}")

    return issues


def validate_all(agents_dir: Path = AGENTS_DIR) -> Dict[str, List[str]]:
    """Validate all agent files. Returns {filename: [issues]}."""
    results = {}
    for f in sorted(agents_dir.iterdir()):
        if f.suffix in (".md", ".yaml") and f.name != "AGENT_PROTOCOL.md":
            issues = validate_agent(f)
            results[f.name] = issues
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent Schema Validator")
    parser.add_argument("--dir", default=str(AGENTS_DIR), help="Agents directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--fix", action="store_true", help="Report fixable issues")
    args = parser.parse_args()

    agents_dir = Path(args.dir)
    if not agents_dir.exists():
        print(f"Error: {agents_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    results = validate_all(agents_dir)

    if args.json:
        print(json.dumps(results, indent=2))
        sys.exit(0)

    total = len(results)
    valid = sum(1 for issues in results.values() if not issues)
    invalid = total - valid

    print(f"Agent Schema Validation: {valid}/{total} pass\n")

    if invalid:
        for name, issues in results.items():
            if issues:
                print(f"  FAIL  {name}")
                for issue in issues:
                    print(f"        - {issue}")
        print()

    for name, issues in results.items():
        if not issues:
            print(f"  OK    {name}")

    print(f"\nSummary: {valid} valid, {invalid} need fixes")
    sys.exit(1 if invalid else 0)


if __name__ == "__main__":
    main()
