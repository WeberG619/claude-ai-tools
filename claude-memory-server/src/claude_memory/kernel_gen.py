#!/usr/bin/env python3
"""
Kernel Evolution — Auto-generate common sense rules from corrections.

Reads all corrections from the memory database, categorizes them by domain,
and generates a supplementary kernel file with concise rules weighted by
effectiveness scores.

Usage:
    python -m claude_memory.kernel_gen
    python -m claude_memory.kernel_gen --output /path/to/output.md
    python -m claude_memory.kernel_gen --db /path/to/memories.db
"""

import argparse
import re
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Category detection
# ---------------------------------------------------------------------------

CATEGORIES = {
    "window-management": {
        "keywords": [
            "window", "dpi", "monitor", "display", "setwindowpos",
            "setforegroundwindow", "sw_maximize", "window_move",
            "positioning", "screen", "resolution", "scaling",
        ],
        "label": "Window Management",
    },
    "revit": {
        "keywords": [
            "revit", "api", "parameter", "family", "element",
            "named pipe", "mcp bridge", "bim", "model",
        ],
        "label": "Revit / BIM",
    },
    "excel": {
        "keywords": [
            "excel", "com", "chart", "worksheet", "cell",
            "formatting", "spreadsheet", "workbook", "autofit",
        ],
        "label": "Excel",
    },
    "navigation": {
        "keywords": [
            "keyboard", "send_keys", "focus", "ctrl+", "browser",
            "desktop", "click", "navigate", "shortcut",
        ],
        "label": "Navigation & Input",
    },
    "git": {
        "keywords": [
            "git", "commit", "branch", "push", "merge",
            "rebase", "pull request", "pr",
        ],
        "label": "Git & Version Control",
    },
    "bluebeam": {
        "keywords": [
            "bluebeam", "pdf", "markup", "annotation",
        ],
        "label": "Bluebeam / PDF",
    },
}


def categorize(content: str, tags: str) -> str:
    """Determine the best category for a correction."""
    text = (content + " " + tags).lower()
    scores = {}
    for cat_id, cat in CATEGORIES.items():
        score = sum(1 for kw in cat["keywords"] if kw in text)
        if score > 0:
            scores[cat_id] = score
    if scores:
        return max(scores, key=scores.get)
    return "general"


# ---------------------------------------------------------------------------
# Correction parsing
# ---------------------------------------------------------------------------

def extract_rule(content: str) -> Optional[str]:
    """Extract the 'Correct Approach' section from a correction's markdown."""
    # Try structured format first
    match = re.search(
        r"###?\s*Correct Approach[:\s]*\n(.*?)(?=\n###?\s|\n---|\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        text = match.group(1).strip()
        # Take first meaningful paragraph (skip empty lines)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            # Cap at ~200 chars for conciseness
            rule = " ".join(lines)
            if len(rule) > 250:
                rule = rule[:247] + "..."
            return rule

    # Fallback: try to find any actionable sentence
    match = re.search(r"(?:ALWAYS|NEVER|MUST|should|instead)[^.]*\.", content, re.IGNORECASE)
    if match:
        return match.group(0).strip()

    return None


def extract_what_wrong(content: str) -> Optional[str]:
    """Extract the 'What Was Wrong' section."""
    match = re.search(
        r"###?\s*(?:What Claude Said/Did \(WRONG\)|What Was Wrong|Why It Was Wrong)[:\s]*\n(.*?)(?=\n###?\s|\n---|\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        text = match.group(1).strip()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            return lines[0][:150]
    return None


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------

def generate_kernel(
    db_path: Path,
    output_path: Path,
) -> dict:
    """Generate kernel-corrections.md from the database.

    Returns dict with stats about what was generated.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT id, content, tags, importance, memory_type,
               effectiveness_score, times_helped, times_surfaced
        FROM memories
        WHERE memory_type IN ('error', 'correction')
           OR tags LIKE '%correction%'
        ORDER BY effectiveness_score DESC NULLS LAST, importance DESC
    """).fetchall()
    conn.close()

    if not rows:
        print("No corrections found in database.")
        return {"total": 0}

    # Categorize
    categorized = defaultdict(list)
    for row in rows:
        cat = categorize(row["content"], row["tags"] or "")
        rule = extract_rule(row["content"])
        if rule:
            categorized[cat].append({
                "id": row["id"],
                "rule": rule,
                "wrong": extract_what_wrong(row["content"]),
                "score": row["effectiveness_score"] or 0,
                "helped": row["times_helped"] or 0,
                "surfaced": row["times_surfaced"] or 0,
                "importance": row["importance"] or 5,
            })

    # Build output
    lines = [
        "# Auto-Generated Correction Rules",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} from {len(rows)} corrections",
        "# DO NOT EDIT — regenerated by: python -m claude_memory.kernel_gen",
        "",
    ]

    # Sort categories: most corrections first, general last
    sorted_cats = sorted(
        categorized.keys(),
        key=lambda c: (c == "general", -len(categorized[c])),
    )

    stats = {"total": len(rows), "rules": 0, "categories": {}}

    for cat in sorted_cats:
        items = categorized[cat]
        label = CATEGORIES.get(cat, {}).get("label", "General")
        lines.append(f"## {label} ({len(items)} corrections)")
        lines.append("")

        stats["categories"][cat] = len(items)

        for item in items:
            score_str = f"score: {item['score']:.1f}" if item["score"] else "unscored"
            helped_str = f"helped: {item['helped']}x" if item["helped"] else ""
            meta_parts = [s for s in [score_str, helped_str] if s]
            meta = f" [{', '.join(meta_parts)}]" if meta_parts else ""

            # Bold for high-scoring, regular for others
            if item["score"] and item["score"] >= 7.0:
                lines.append(f"- **{item['rule']}**{meta}")
            else:
                lines.append(f"- {item['rule']}{meta}")

            stats["rules"] += 1

        lines.append("")

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    print(f"Generated {output_path} — {stats['rules']} rules from {stats['total']} corrections")

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate common sense kernel rules from correction database",
    )
    parser.add_argument(
        "--db",
        type=Path,
        help="Path to memories.db (default: auto-detect from server config)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output path for kernel-corrections.md",
    )
    args = parser.parse_args()

    # Resolve DB path
    if args.db:
        db_path = args.db
    else:
        # Try to import from server
        try:
            from claude_memory.server import DB_PATH
            db_path = DB_PATH
        except ImportError:
            # Fallback: look relative to this file
            db_path = Path(__file__).parent.parent.parent / "data" / "memories.db"

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        raise SystemExit(1)

    # Resolve output path
    if args.output:
        output_path = args.output
    else:
        # Default: agent-common-sense directory (sibling to claude-memory-server)
        tools_dir = Path(__file__).parent.parent.parent.parent
        output_path = tools_dir / "agent-common-sense" / "kernel-corrections.md"

    generate_kernel(db_path, output_path)


if __name__ == "__main__":
    main()
