#!/usr/bin/env python3
"""
Weekly Pattern Analysis Routine

Run this weekly to analyze patterns in stored memories and generate insights.
Can be run manually or scheduled via cron/Task Scheduler.

Usage:
    python weekly_analysis.py [--days=30] [--project=NAME]
"""

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

# Memory database location
MEMORY_DB = Path.home() / ".claude" / "claude_memory.db"
REPORT_DIR = Path("/mnt/d/_CLAUDE-TOOLS/pattern-analysis/reports")


def get_db_connection():
    """Connect to memory database."""
    if not MEMORY_DB.exists():
        print(f"Memory database not found at {MEMORY_DB}")
        sys.exit(1)
    return sqlite3.connect(MEMORY_DB)


def analyze_error_patterns(conn, days=30) -> dict:
    """Find recurring error patterns."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    cursor = conn.execute("""
        SELECT content, project, created_at
        FROM memories
        WHERE memory_type = 'error'
        AND created_at > ?
        ORDER BY created_at DESC
    """, (cutoff,))

    errors = cursor.fetchall()

    # Group by project
    by_project = {}
    for content, project, created_at in errors:
        project = project or "global"
        if project not in by_project:
            by_project[project] = []
        by_project[project].append(content)

    return {
        "total_errors": len(errors),
        "by_project": {p: len(e) for p, e in by_project.items()},
        "samples": errors[:5]
    }


def analyze_corrections(conn, days=30) -> dict:
    """Analyze correction patterns."""
    cursor = conn.execute("""
        SELECT content, project, importance, created_at
        FROM memories
        WHERE memory_type = 'error'
        AND content LIKE '%WRONG%' OR content LIKE '%Correct Approach%'
        ORDER BY importance DESC, created_at DESC
        LIMIT 50
    """)

    corrections = cursor.fetchall()

    # Count categories
    categories = Counter()
    for content, project, importance, _ in corrections:
        if "architecture" in content.lower():
            categories["architecture"] += 1
        elif "code" in content.lower():
            categories["code"] += 1
        elif "workflow" in content.lower():
            categories["workflow"] += 1
        else:
            categories["other"] += 1

    return {
        "total_corrections": len(corrections),
        "by_category": dict(categories),
        "high_importance": sum(1 for _, _, imp, _ in corrections if imp and imp >= 8)
    }


def analyze_project_activity(conn, days=30) -> dict:
    """Analyze activity by project."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    cursor = conn.execute("""
        SELECT project, COUNT(*) as count, MAX(created_at) as last_active
        FROM memories
        WHERE created_at > ?
        AND project IS NOT NULL
        GROUP BY project
        ORDER BY count DESC
        LIMIT 20
    """, (cutoff,))

    projects = cursor.fetchall()

    return {
        "active_projects": len(projects),
        "project_activity": [
            {"name": p, "memories": c, "last_active": l}
            for p, c, l in projects
        ]
    }


def analyze_decision_patterns(conn, days=30) -> dict:
    """Analyze decision type memories."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    cursor = conn.execute("""
        SELECT content, project, tags, created_at
        FROM memories
        WHERE memory_type = 'decision'
        AND created_at > ?
        ORDER BY created_at DESC
        LIMIT 30
    """, (cutoff,))

    decisions = cursor.fetchall()

    # Extract common tags
    all_tags = []
    for _, _, tags, _ in decisions:
        if tags:
            try:
                all_tags.extend(json.loads(tags))
            except:
                pass

    return {
        "total_decisions": len(decisions),
        "common_tags": dict(Counter(all_tags).most_common(10)),
        "recent": [d[0][:100] for d in decisions[:5]]
    }


def generate_report(days=30, project=None) -> str:
    """Generate full analysis report."""
    conn = get_db_connection()

    errors = analyze_error_patterns(conn, days)
    corrections = analyze_corrections(conn, days)
    projects = analyze_project_activity(conn, days)
    decisions = analyze_decision_patterns(conn, days)

    conn.close()

    report = f"""
# Weekly Pattern Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Analysis Period: {days} days

## Summary Statistics
- Total Errors Logged: {errors['total_errors']}
- Total Corrections: {corrections['total_corrections']}
- High-Priority Corrections: {corrections['high_importance']}
- Active Projects: {projects['active_projects']}
- Decisions Recorded: {decisions['total_decisions']}

## Error Distribution by Project
"""
    for proj, count in sorted(errors['by_project'].items(), key=lambda x: -x[1])[:10]:
        report += f"- {proj}: {count} errors\n"

    report += f"""
## Correction Categories
- Architecture: {corrections['by_category'].get('architecture', 0)}
- Code: {corrections['by_category'].get('code', 0)}
- Workflow: {corrections['by_category'].get('workflow', 0)}
- Other: {corrections['by_category'].get('other', 0)}

## Most Active Projects
"""
    for proj in projects['project_activity'][:5]:
        report += f"- {proj['name']}: {proj['memories']} memories (last: {proj['last_active'][:10]})\n"

    report += f"""
## Common Decision Tags
"""
    for tag, count in decisions['common_tags'].items():
        report += f"- {tag}: {count}x\n"

    report += """
## Recommendations

Based on this analysis:
1. Review high-priority corrections that may need to be compiled into validation rules
2. Projects with many errors may need workflow improvements
3. Common tags suggest focus areas for documentation
"""

    return report


def save_report(report: str, filename=None):
    """Save report to file."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not filename:
        filename = f"analysis_{datetime.now().strftime('%Y%m%d')}.md"

    filepath = REPORT_DIR / filename
    filepath.write_text(report)
    print(f"Report saved to: {filepath}")
    return filepath


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Weekly pattern analysis")
    parser.add_argument("--days", type=int, default=30, help="Days to analyze")
    parser.add_argument("--project", type=str, help="Focus on specific project")
    parser.add_argument("--output", type=str, help="Output filename")
    parser.add_argument("--print", action="store_true", help="Print report to stdout")

    args = parser.parse_args()

    report = generate_report(days=args.days, project=args.project)

    if args.print:
        print(report)
    else:
        save_report(report, args.output)
        print("\nKey findings printed. Full report saved.")
        # Print summary to stdout
        lines = report.split("\n")
        for line in lines[:30]:
            print(line)


if __name__ == "__main__":
    main()
