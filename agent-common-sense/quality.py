"""
Correction quality pipeline for the Common Sense Engine.

Handles:
  - Validation: ensure corrections have required fields and minimum quality
  - Deduplication: detect and merge similar corrections
  - Lifecycle: manage correction states (draft → active → reinforced → deprecated)
  - Temporal decay: weight corrections by age and reinforcement

Usage:
    from quality import validate_correction, deduplicate, decay_score, CorrectionStatus

    # Before storing
    errors = validate_correction(correction_dict)
    if errors:
        print(f"Invalid: {errors}")

    # Find duplicates
    dupes = deduplicate(db_path, new_content="deploy to wrong path")

    # Score with decay
    score = decay_score(importance=8, created_at="2026-01-15", helped_count=3)
"""

import hashlib
import json
import math
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from typing import Optional


# ─── CORRECTION LIFECYCLE ────────────────────────────────────────

class CorrectionStatus(str, Enum):
    """Lifecycle states for corrections."""
    DRAFT = "draft"          # Just created, not yet validated
    ACTIVE = "active"        # Validated and in use
    REINFORCED = "reinforced"  # Confirmed helpful multiple times
    DEPRECATED = "deprecated"  # No longer relevant or superseded


STATUS_TRANSITIONS = {
    CorrectionStatus.DRAFT: {CorrectionStatus.ACTIVE, CorrectionStatus.DEPRECATED},
    CorrectionStatus.ACTIVE: {CorrectionStatus.REINFORCED, CorrectionStatus.DEPRECATED},
    CorrectionStatus.REINFORCED: {CorrectionStatus.DEPRECATED},
    CorrectionStatus.DEPRECATED: {CorrectionStatus.ACTIVE},  # Can be reactivated
}


def can_transition(current: str, target: str) -> bool:
    """Check if a status transition is valid."""
    try:
        current_status = CorrectionStatus(current)
        target_status = CorrectionStatus(target)
        return target_status in STATUS_TRANSITIONS.get(current_status, set())
    except ValueError:
        return False


def auto_transition(status: str, helped_count: int, not_helped_count: int,
                    days_old: int) -> Optional[str]:
    """Suggest automatic status transitions based on metrics.

    Rules:
      - Active → Reinforced: helped 3+ times with >70% help rate
      - Active → Deprecated: not helped 5+ times with <20% help rate
      - Active → Deprecated: older than 180 days with 0 helped/not-helped (never tested)
    """
    total = helped_count + not_helped_count
    help_rate = helped_count / total if total > 0 else 0.5

    if status == CorrectionStatus.ACTIVE:
        if helped_count >= 3 and help_rate >= 0.7:
            return CorrectionStatus.REINFORCED
        if not_helped_count >= 5 and help_rate < 0.2:
            return CorrectionStatus.DEPRECATED
        if total == 0 and days_old > 180:
            return CorrectionStatus.DEPRECATED

    return None


# ─── VALIDATION ──────────────────────────────────────────────────

@dataclass
class ValidationResult:
    """Result of validating a correction."""
    valid: bool
    errors: list[str]
    warnings: list[str]


def validate_correction(correction: dict) -> ValidationResult:
    """Validate a correction dict before storing.

    Checks:
      - Required fields present
      - Content not too short (likely a fragment)
      - Content not too long (likely noise)
      - No formatting artifacts
      - Category is valid
    """
    errors = []
    warnings = []

    # Required fields
    required = ["content"]
    for field in required:
        if field not in correction or not correction[field]:
            errors.append(f"Missing required field: {field}")

    content = correction.get("content", "")

    # Length checks
    if len(content) < 20:
        errors.append(f"Content too short ({len(content)} chars). Likely a fragment.")

    if len(content) > 2000:
        warnings.append(f"Content very long ({len(content)} chars). Consider splitting.")

    # Fragment detection - common garbage patterns
    fragment_patterns = [
        r'^\d+\.\s*$',               # Just a number like "2." or "5."
        r'^instead of\s+\w+\.?\s*$',  # "instead of top."
        r'^\w{1,3}\s*$',             # Very short single word
        r'^\|.*\|$',                  # Pipe-delimited table row
        r'^- same error\s*$',         # Contextless fragment
    ]
    for pattern in fragment_patterns:
        if re.match(pattern, content.strip()):
            errors.append(f"Content looks like a fragment: '{content.strip()[:50]}'")
            break

    # Truncation detection
    if content.rstrip().endswith("...") and len(content) > 100:
        warnings.append("Content appears truncated (ends with ...)")

    # Category validation
    valid_categories = {
        "filesystem", "git", "network", "execution", "scope",
        "deployment", "data", "identity", "code", "workflow",
        "architecture", "preferences", "communication", "general",
    }
    category = correction.get("category", "general")
    if category not in valid_categories:
        warnings.append(f"Non-standard category: '{category}'. "
                        f"Consider: {', '.join(sorted(valid_categories))}")

    # Importance range
    importance = correction.get("importance", 5)
    if not (1 <= importance <= 10):
        errors.append(f"Importance must be 1-10, got {importance}")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# ─── DEDUPLICATION ───────────────────────────────────────────────

def content_hash(content: str) -> str:
    """Generate a normalized hash for deduplication.

    Normalizes whitespace, case, and punctuation before hashing.
    """
    normalized = content.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def text_similarity(a: str, b: str) -> float:
    """Simple word-overlap similarity (Jaccard index).

    Fast, no dependencies. Good enough for dedup detection.
    """
    words_a = set(re.findall(r'[a-z0-9]+', a.lower()))
    words_b = set(re.findall(r'[a-z0-9]+', b.lower()))

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def find_duplicates(db_path: str, new_content: str,
                    threshold: float = 0.6,
                    memory_type: str = None) -> list[dict]:
    """Find existing corrections similar to new_content.

    Args:
        db_path: Path to SQLite database
        new_content: The new correction content to check against
        threshold: Minimum similarity score to consider a duplicate (0-1)
        memory_type: Optional filter by memory type

    Returns:
        List of dicts with 'id', 'content', 'similarity' for matches above threshold
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        sql = "SELECT id, content FROM memories"
        params = []
        if memory_type:
            sql += " WHERE memory_type = ?"
            params.append(memory_type)

        cursor = conn.execute(sql, params)
        matches = []

        for row in cursor.fetchall():
            sim = text_similarity(new_content, row["content"])
            if sim >= threshold:
                matches.append({
                    "id": row["id"],
                    "content": row["content"],
                    "similarity": sim,
                })

        conn.close()
        return sorted(matches, key=lambda m: m["similarity"], reverse=True)

    except Exception as e:
        print(f"Dedup search failed: {e}", file=sys.stderr)
        return []


def merge_corrections(existing: dict, new: dict) -> dict:
    """Merge a new correction into an existing one.

    Keeps the more detailed/longer content. Merges tags.
    Takes the higher importance. Updates timestamp.
    """
    # Keep the longer (presumably more complete) content
    existing_content = existing.get("content", "")
    new_content = new.get("content", "")
    merged_content = new_content if len(new_content) > len(existing_content) else existing_content

    # Merge tags
    existing_tags = json.loads(existing.get("tags", "[]")) if isinstance(existing.get("tags"), str) else existing.get("tags", [])
    new_tags = json.loads(new.get("tags", "[]")) if isinstance(new.get("tags"), str) else new.get("tags", [])
    merged_tags = list(set(existing_tags + new_tags))

    # Higher importance wins
    merged_importance = max(
        existing.get("importance", 5),
        new.get("importance", 5)
    )

    return {
        "id": existing.get("id"),
        "content": merged_content,
        "tags": json.dumps(merged_tags),
        "importance": merged_importance,
        "memory_type": existing.get("memory_type", new.get("memory_type", "correction")),
        "project": existing.get("project", new.get("project", "general")),
    }


def deduplicate_database(db_path: str, threshold: float = 0.7,
                         dry_run: bool = True) -> list[dict]:
    """Scan the entire database for duplicate corrections and optionally merge them.

    Args:
        db_path: Path to SQLite database
        threshold: Similarity threshold for duplicate detection
        dry_run: If True, only report duplicates without merging

    Returns:
        List of duplicate groups found
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, content, importance, tags FROM memories ORDER BY importance DESC"
        ).fetchall()
        conn.close()

        rows = [dict(r) for r in rows]
        seen = set()
        duplicate_groups = []

        for i, row_a in enumerate(rows):
            if row_a["id"] in seen:
                continue

            group = [row_a]
            for j, row_b in enumerate(rows[i + 1:], start=i + 1):
                if row_b["id"] in seen:
                    continue
                sim = text_similarity(row_a["content"], row_b["content"])
                if sim >= threshold:
                    group.append(row_b)
                    seen.add(row_b["id"])

            if len(group) > 1:
                seen.add(row_a["id"])
                duplicate_groups.append({
                    "keep": group[0],  # Highest importance
                    "duplicates": group[1:],
                    "count": len(group),
                })

                if not dry_run:
                    # Merge all duplicates into the keeper
                    keeper = group[0]
                    for dupe in group[1:]:
                        keeper = merge_corrections(keeper, dupe)

                    conn = sqlite3.connect(db_path)
                    conn.execute(
                        "UPDATE memories SET content=?, tags=?, importance=? WHERE id=?",
                        (keeper["content"], keeper["tags"], keeper["importance"], keeper["id"])
                    )
                    for dupe in group[1:]:
                        conn.execute("DELETE FROM memories WHERE id=?", (dupe["id"],))
                    conn.commit()
                    conn.close()

        return duplicate_groups

    except Exception as e:
        print(f"Dedup scan failed: {e}", file=sys.stderr)
        return []


# ─── TEMPORAL DECAY ──────────────────────────────────────────────

def decay_score(importance: int, created_at: str,
                helped_count: int = 0, not_helped_count: int = 0,
                half_life_days: int = 90) -> float:
    """Calculate a time-decayed relevance score for a correction.

    Formula:
        base_score = importance (1-10)
        time_factor = 0.5 ^ (days_old / half_life_days)
        effectiveness_boost = 1 + (helped_count * 0.2)
        penalty = max(0.1, 1 - (not_helped_count * 0.1))

        final = base_score * time_factor * effectiveness_boost * penalty

    Reinforced corrections decay slower. Unhelpful ones decay faster.
    """
    try:
        # Handle various datetime formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                created = datetime.strptime(created_at.split(".")[0], fmt)
                break
            except (ValueError, AttributeError):
                continue
        else:
            created = datetime.now()  # Fallback: treat as fresh

        days_old = max(0, (datetime.now() - created).days)
    except Exception:
        days_old = 0

    base_score = importance / 10.0  # Normalize to 0-1
    time_factor = math.pow(0.5, days_old / half_life_days)

    # Effectiveness adjustments
    effectiveness_boost = 1.0 + (helped_count * 0.2)  # Each help adds 20%
    penalty = max(0.1, 1.0 - (not_helped_count * 0.1))  # Each not-help removes 10%, floor at 0.1

    return base_score * time_factor * effectiveness_boost * penalty


def get_stale_corrections(db_path: str, days: int = 90) -> list[dict]:
    """Find corrections that are old and have never been validated.

    These are candidates for deprecation or review.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # Try to use helped_count columns if they exist
        try:
            cursor = conn.execute("""
                SELECT * FROM memories
                WHERE created_at < ?
                AND (helped_count IS NULL OR helped_count = 0)
                AND (not_helped_count IS NULL OR not_helped_count = 0)
                AND memory_type = 'correction'
                AND (status IS NULL OR status = 'active')
                ORDER BY created_at ASC
            """, (cutoff,))
        except sqlite3.OperationalError:
            # Columns don't exist yet
            cursor = conn.execute("""
                SELECT * FROM memories
                WHERE created_at < ?
                AND memory_type = 'correction'
                ORDER BY created_at ASC
            """, (cutoff,))

        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    except Exception as e:
        print(f"Stale query failed: {e}", file=sys.stderr)
        return []


# ─── BATCH CLEANUP ───────────────────────────────────────────────

def cleanup_database(db_path: str, dry_run: bool = True) -> dict:
    """Run all quality checks on the database.

    Returns a summary of findings and actions taken.
    """
    summary = {
        "fragments_removed": 0,
        "duplicates_merged": 0,
        "auto_deprecated": 0,
        "auto_reinforced": 0,
    }

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM memories WHERE memory_type = 'correction'").fetchall()
        conn.close()

        rows = [dict(r) for r in rows]

        # 1. Remove fragments
        for row in rows:
            result = validate_correction(row)
            if not result.valid:
                summary["fragments_removed"] += 1
                if not dry_run:
                    conn = sqlite3.connect(db_path)
                    conn.execute("DELETE FROM memories WHERE id = ?", (row["id"],))
                    conn.commit()
                    conn.close()

        # 2. Deduplicate
        dupes = deduplicate_database(db_path, dry_run=dry_run)
        summary["duplicates_merged"] = sum(g["count"] - 1 for g in dupes)

        # 3. Auto-transition lifecycle
        for row in rows:
            try:
                created = datetime.strptime(row.get("created_at", "").split(".")[0],
                                            "%Y-%m-%d %H:%M:%S")
                days_old = (datetime.now() - created).days
            except (ValueError, AttributeError):
                days_old = 0

            new_status = auto_transition(
                status=row.get("status", "active"),
                helped_count=row.get("helped_count", 0),
                not_helped_count=row.get("not_helped_count", 0),
                days_old=days_old,
            )
            if new_status:
                if new_status == CorrectionStatus.DEPRECATED:
                    summary["auto_deprecated"] += 1
                elif new_status == CorrectionStatus.REINFORCED:
                    summary["auto_reinforced"] += 1

                if not dry_run:
                    conn = sqlite3.connect(db_path)
                    conn.execute(
                        "UPDATE memories SET status = ? WHERE id = ?",
                        (new_status, row["id"])
                    )
                    conn.commit()
                    conn.close()

    except Exception as e:
        summary["error"] = str(e)

    return summary
