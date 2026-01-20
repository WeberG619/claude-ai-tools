#!/usr/bin/env python3
"""
Pre-Flight Correction Check
Queries Claude Memory for relevant corrections before operations.
Surfaces past mistakes to prevent repeating them.
"""

import json
import sys
import subprocess
import re
from pathlib import Path

# Memory server communication
MEMORY_DB = Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db")

def query_corrections(keywords: list[str], limit: int = 5) -> list[dict]:
    """Query memory database for corrections matching keywords."""
    import sqlite3

    if not MEMORY_DB.exists():
        return []

    conn = sqlite3.connect(str(MEMORY_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Build search query
    search_terms = " OR ".join([f'content LIKE "%{kw}%"' for kw in keywords])

    query = f"""
        SELECT id, content, summary, memory_type, importance, project, created_at
        FROM memories
        WHERE memory_type = 'error'
        AND ({search_terms})
        ORDER BY importance DESC, created_at DESC
        LIMIT {limit}
    """

    try:
        cursor.execute(query)
        results = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        results = []
    finally:
        conn.close()

    return results


def extract_correction_advice(content: str) -> str:
    """Extract the 'correct approach' from a correction record."""
    # Look for patterns like "Correct Approach:" or "The right way:"
    patterns = [
        r"Correct Approach[:\s]+(.+?)(?:\n\n|\*\*|$)",
        r"The right way[:\s]+(.+?)(?:\n\n|\*\*|$)",
        r"✓\s*(.+?)(?:\n|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()[:200]

    return content[:150] + "..."


def check_operation(operation_context: str) -> dict:
    """
    Check if an operation has known issues.

    Args:
        operation_context: Description of what's about to happen

    Returns:
        dict with warnings and suggestions
    """
    # Extract keywords from context
    keywords = []

    # Common operation patterns
    keyword_map = {
        "wall": ["wall", "walls", "create wall", "place wall"],
        "dxf": ["dxf", "DXF", "cad", "CAD", "coordinates", "import"],
        "viewport": ["viewport", "sheet", "placement", "layout"],
        "floor plan": ["floor plan", "floorplan", "extraction", "trace"],
        "door": ["door", "doors", "opening", "insert"],
        "schedule": ["schedule", "parameter", "field"],
    }

    context_lower = operation_context.lower()

    for category, terms in keyword_map.items():
        if any(term in context_lower for term in terms):
            keywords.extend(terms)

    # Also add raw words from context
    words = re.findall(r'\b\w{4,}\b', context_lower)
    keywords.extend(words[:5])

    # Remove duplicates
    keywords = list(set(keywords))

    if not keywords:
        return {"warnings": [], "suggestions": [], "safe": True}

    # Query for corrections
    corrections = query_corrections(keywords)

    result = {
        "warnings": [],
        "suggestions": [],
        "safe": len(corrections) == 0,
        "correction_count": len(corrections)
    }

    for correction in corrections:
        advice = extract_correction_advice(correction.get("content", ""))
        result["warnings"].append({
            "id": correction.get("id"),
            "project": correction.get("project"),
            "importance": correction.get("importance"),
            "summary": correction.get("summary", advice),
            "advice": advice
        })
        result["suggestions"].append(advice)

    return result


def format_warning_banner(result: dict) -> str:
    """Format warnings as a visible banner."""
    if result["safe"]:
        return ""

    lines = [
        "",
        "=" * 60,
        "⚠️  PRE-FLIGHT CHECK: KNOWN ISSUES DETECTED",
        "=" * 60,
        f"Found {result['correction_count']} relevant correction(s):",
        ""
    ]

    for i, warning in enumerate(result["warnings"], 1):
        lines.append(f"  {i}. [{warning.get('project', 'general')}] (importance: {warning.get('importance', '?')})")
        lines.append(f"     → {warning['advice']}")
        lines.append("")

    lines.extend([
        "=" * 60,
        "RECOMMENDATION: Review these issues before proceeding.",
        "=" * 60,
        ""
    ])

    return "\n".join(lines)


def main():
    """Main entry point for CLI usage."""
    if len(sys.argv) < 2:
        print("Usage: pre_flight_check.py <operation_context>")
        print("Example: pre_flight_check.py 'creating walls from DXF coordinates'")
        sys.exit(1)

    context = " ".join(sys.argv[1:])
    result = check_operation(context)

    if result["safe"]:
        print("✅ Pre-flight check: No known issues for this operation.")
    else:
        print(format_warning_banner(result))
        # Return non-zero to signal warnings (for hook integration)
        sys.exit(0)  # Still allow operation, just warn


if __name__ == "__main__":
    main()
