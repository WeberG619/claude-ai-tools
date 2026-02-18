"""
Clean kernel-corrections.md generator for the Common Sense Engine.

Fixes all known issues with the previous generator:
  - Truncation: entries are trimmed to complete sentences, never cut mid-word
  - Miscategorization: entries are categorized by content analysis, not position
  - Deduplication: similar entries are merged
  - Validation: fragments and garbage entries are filtered out
  - Scoring: entries are ranked by effectiveness and importance

Usage:
    python kernel_gen.py                    # Generate from database
    python kernel_gen.py --db path/to.db    # Custom DB path
    python kernel_gen.py --dry-run          # Preview without writing
    python kernel_gen.py --stats            # Show statistics only
"""

import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from quality import (
    content_hash, text_similarity, validate_correction,
    CorrectionStatus, decay_score,
)

OUTPUT_PATH = Path(__file__).parent / "kernel-corrections.md"
MAX_ENTRY_LENGTH = 300  # Max chars per entry in the generated file
MIN_ENTRY_LENGTH = 30   # Skip entries shorter than this


# ─── DOMAIN CLASSIFICATION ──────────────────────────────────────

DOMAIN_KEYWORDS = {
    "Revit / BIM": [
        "revit", "bim", "wall", "floor plan", "level", "family", "viewport",
        "sheet", "drafting", "titleblock", "mcp bridge", "revitmcp", "getElements",
        "createWall", "setActiveDocument", "loadFamily", "getLevel", "annotation",
        "room", "door", "window", "elevation", "section", "schedule",
        "cad", "detail line", "view template", "construction document",
    ],
    "Git & Version Control": [
        "git", "commit", "push", "branch", "merge", "rebase", "pull request",
        "staged", "unstaged", "remote", "force-push", ".gitignore", "submodule",
    ],
    "Window Management": [
        "window", "monitor", "dpi", "display", "setwindowpos", "setforeground",
        "screenshot", "browser_screenshot", "window_move", "maximize", "screen",
        "focus", "showwindow",
    ],
    "Excel & Desktop Automation": [
        "excel", "com object", "chart", "worksheet", "workbook", "cell",
        "formula", "autofit", "conditional format", "sparkline", "csv",
        "powerpoint", "word document",
    ],
    "Bluebeam / PDF": [
        "bluebeam", "pdf", "markup", "annotation", "page", "measurement",
        "scale", "calibrat",
    ],
    "Email & Communication": [
        "email", "gmail", "outlook", "smtp", "imap", "send email",
        "recipient", "compose", "calendar", "appointment", "schedule meeting",
    ],
    "Deployment & Paths": [
        "deploy", "dll", "addins", "appdata", "install", "path",
        "roaming", "production", "staging",
    ],
    "Architecture & Design": [
        "architect", "floor plan", "parcel", "legal description", "zoning",
        "title block", "firm", "project info", "drawing", "specification",
    ],
    "User Preferences": [
        "weber", "user name", "preference", "identity", "always use",
        "never use", "default", "configured",
    ],
    "General": [],  # Catch-all
}


def classify_domain(content: str) -> str:
    """Classify a correction into a domain based on content analysis.

    Scores each domain by keyword matches and returns the best fit.
    """
    content_lower = content.lower()
    scores = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        if not keywords:
            continue
        score = sum(1 for kw in keywords if kw in content_lower)
        if score > 0:
            scores[domain] = score

    if not scores:
        return "General"

    return max(scores, key=scores.get)


# ─── ENTRY CLEANING ─────────────────────────────────────────────

def clean_entry(content: str) -> Optional[str]:
    """Clean a correction entry for inclusion in kernel-corrections.md.

    Returns None if the entry is garbage/unrecoverable.
    """
    if not content or not content.strip():
        return None

    text = content.strip()

    # Remove common prefixes
    for prefix in ["CORRECTION:", "CORRECTION [", "SEED CORRECTION", "SEED:"]:
        if text.upper().startswith(prefix.upper()):
            idx = text.find("]:")
            if idx > 0:
                text = text[idx + 2:].strip()
            elif text.upper().startswith(prefix.upper()):
                text = text[len(prefix):].strip()

    # Remove "## Correction Record" header format from memory DB entries
    text = re.sub(r'^#+\s*Correction Record\s*', '', text, flags=re.IGNORECASE).strip()
    # Extract the "Wrong" and "Correct" parts from the structured format
    text = re.sub(r'#+\s*What Claude Said/Did \(WRONG\):\s*', '', text).strip()
    text = re.sub(r'#+\s*Why It Was Wrong:\s*', ' — ', text).strip()
    text = re.sub(r'#+\s*Correct Approach:\s*', 'Do instead: ', text).strip()
    # Clean markdown header artifacts
    text = re.sub(r'#+\s+', '', text).strip()

    # Remove "Wrong:" and "Right:" prefixes — extract the actionable part
    lines = text.split("\n")
    actionable_parts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip meta-lines
        if line.startswith("Wrong:") or line.startswith("What went wrong:"):
            continue
        if line.startswith("Right:") or line.startswith("Correct approach:"):
            actionable_parts.append(line.split(":", 1)[1].strip())
        elif line.startswith("Domain:") or line.startswith("Category:"):
            continue
        elif line.startswith("Detection:"):
            continue
        else:
            actionable_parts.append(line)

    text = " ".join(actionable_parts).strip()

    if not text:
        return None

    # Reject fragments
    fragment_patterns = [
        r'^\d+\.\s*$',
        r'^instead of\s+\w+\.?\s*$',
        r'^\w{1,5}\s*$',
        r'^\|.*\|$',
        r'^-\s*same error\s*$',
        r'^should\s+\w+$',
        r'^must\s+\w{1,10}$',
    ]
    for pattern in fragment_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return None

    # Length check
    if len(text) < MIN_ENTRY_LENGTH:
        return None

    # Truncate to complete sentence if too long
    if len(text) > MAX_ENTRY_LENGTH:
        # Find the last sentence boundary before the limit
        truncated = text[:MAX_ENTRY_LENGTH]
        # Look for sentence-ending punctuation
        for end_char in [". ", "! ", "? "]:
            last_period = truncated.rfind(end_char)
            if last_period > MAX_ENTRY_LENGTH // 2:
                text = truncated[:last_period + 1]
                break
        else:
            # No good sentence boundary — cut at last space
            last_space = truncated.rfind(" ")
            if last_space > MAX_ENTRY_LENGTH // 2:
                text = truncated[:last_space].rstrip(",;:-") + "."
            else:
                text = truncated.rstrip(",;:-") + "."

    # Clean up formatting artifacts
    text = re.sub(r'\*\*Category\*\*:.*$', '', text).strip()
    text = re.sub(r'\[unscored\]', '', text).strip()
    text = re.sub(r'\[score:.*?\]', '', text).strip()
    text = re.sub(r'\s+', ' ', text)

    # Ensure ends with period
    if text and text[-1] not in '.!?':
        text += '.'

    return text


# ─── DEDUPLICATION ───────────────────────────────────────────────

def deduplicate_entries(entries: list[dict], threshold: float = 0.6) -> list[dict]:
    """Remove duplicate entries, keeping the highest-scored version."""
    if not entries:
        return []

    # Sort by score descending so we keep the best version
    sorted_entries = sorted(entries, key=lambda e: e.get("score", 0), reverse=True)

    kept = []
    kept_texts = []

    for entry in sorted_entries:
        text = entry.get("text", "")
        is_dupe = False

        for existing_text in kept_texts:
            if text_similarity(text, existing_text) >= threshold:
                is_dupe = True
                break

        if not is_dupe:
            kept.append(entry)
            kept_texts.append(text)

    return kept


# ─── MAIN GENERATOR ─────────────────────────────────────────────

def generate(db_path: str, output_path: Path = None,
             dry_run: bool = False) -> dict:
    """Generate a clean kernel-corrections.md from the database.

    Returns stats about the generation.
    """
    output = output_path or OUTPUT_PATH

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Check which columns exist for backward compatibility
        cursor = conn.execute("PRAGMA table_info(memories)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        has_status = "status" in existing_cols

        if has_status:
            rows = conn.execute("""
                SELECT * FROM memories
                WHERE memory_type = 'correction'
                AND (status IS NULL OR status != 'deprecated')
                ORDER BY importance DESC, created_at DESC
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM memories
                WHERE memory_type = 'correction'
                ORDER BY importance DESC, created_at DESC
            """).fetchall()

        conn.close()
    except Exception as e:
        return {"error": f"Database read failed: {e}"}

    rows = [dict(r) for r in rows]

    stats = {
        "total_in_db": len(rows),
        "cleaned": 0,
        "rejected_fragment": 0,
        "rejected_short": 0,
        "deduplicated": 0,
        "domains": {},
    }

    # 1. Clean each entry
    cleaned_entries = []
    for row in rows:
        text = clean_entry(row.get("content", ""))
        if text is None:
            stats["rejected_fragment"] += 1
            continue

        # Calculate decay-adjusted score
        score = decay_score(
            importance=row.get("importance", 5),
            created_at=row.get("created_at", ""),
            helped_count=row.get("helped_count", 0) or 0,
            not_helped_count=row.get("not_helped_count", 0) or 0,
        )

        # Classify domain
        domain = classify_domain(text)

        # Build effectiveness annotation
        helped = row.get("helped_count", 0) or 0
        not_helped = row.get("not_helped_count", 0) or 0
        total_checks = helped + not_helped

        annotation = ""
        if total_checks > 0:
            rate = helped / total_checks
            annotation = f" [effectiveness: {rate:.0%}, tested {total_checks}x]"

        cleaned_entries.append({
            "text": text,
            "domain": domain,
            "score": score,
            "importance": row.get("importance", 5),
            "annotation": annotation,
            "status": row.get("status", "active"),
        })

    stats["cleaned"] = len(cleaned_entries)

    # 2. Deduplicate
    before_dedup = len(cleaned_entries)
    cleaned_entries = deduplicate_entries(cleaned_entries)
    stats["deduplicated"] = before_dedup - len(cleaned_entries)

    # 3. Group by domain
    domains: dict[str, list[dict]] = defaultdict(list)
    for entry in cleaned_entries:
        domains[entry["domain"]].append(entry)

    # Sort entries within each domain by score
    for domain in domains:
        domains[domain].sort(key=lambda e: e["score"], reverse=True)
        stats["domains"][domain] = len(domains[domain])

    # 4. Generate markdown
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_entries = sum(len(v) for v in domains.values())

    lines = [
        "# Auto-Generated Correction Rules",
        f"# Generated: {now} from {stats['total_in_db']} corrections "
        f"({total_entries} after cleaning)",
        "# DO NOT EDIT — regenerate with: python kernel_gen.py",
        "",
    ]

    # Order domains by count (most corrections first)
    sorted_domains = sorted(domains.items(), key=lambda kv: len(kv[1]), reverse=True)

    for domain, entries in sorted_domains:
        lines.append(f"## {domain} ({len(entries)} corrections)")
        lines.append("")

        for entry in entries:
            status_marker = ""
            if entry["status"] == "reinforced":
                status_marker = " **[VERIFIED]**"

            lines.append(f"- {entry['text']}{entry['annotation']}{status_marker}")

        lines.append("")

    content = "\n".join(lines)

    if not dry_run:
        with open(output, "w") as f:
            f.write(content)

    stats["output_path"] = str(output)
    stats["output_lines"] = len(lines)

    return stats


# ─── CLI ─────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate kernel-corrections.md")
    parser.add_argument("--db", help="Path to memory SQLite database")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing")
    parser.add_argument("--stats", action="store_true",
                        help="Show statistics only")
    args = parser.parse_args()

    # Find database
    db_path = args.db
    if not db_path:
        candidates = [
            Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"),
            Path.home() / ".claude-memory" / "memories.db",
            Path("/mnt/d/_CLAUDE-TOOLS/claude-memory/memories.db"),
            Path.home() / ".claude" / "memory.db",
        ]
        for p in candidates:
            if p.exists():
                db_path = str(p)
                break

    if not db_path:
        print("No database found. Use --db to specify path.")
        sys.exit(1)

    output = Path(args.output) if args.output else OUTPUT_PATH

    stats = generate(db_path, output_path=output, dry_run=args.dry_run or args.stats)

    if "error" in stats:
        print(f"Error: {stats['error']}")
        sys.exit(1)

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Generation complete:")
    print(f"  Total in DB:       {stats['total_in_db']}")
    print(f"  Cleaned:           {stats['cleaned']}")
    print(f"  Rejected (fragment/short): {stats['rejected_fragment']}")
    print(f"  Deduplicated:      {stats['deduplicated']}")
    print(f"  Final entries:     {sum(stats['domains'].values())}")
    print(f"\n  Domains:")
    for domain, count in sorted(stats["domains"].items(), key=lambda kv: kv[1], reverse=True):
        print(f"    {domain:30s} {count:3d}")

    if not args.dry_run and not args.stats:
        print(f"\n  Written to: {stats['output_path']}")


if __name__ == "__main__":
    main()
