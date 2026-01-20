#!/usr/bin/env python3
"""
Memory System Maintenance Script
Run monthly to keep the memory system healthy.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "memories.db"

def get_stats():
    """Get current memory statistics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Total count
    cursor.execute("SELECT COUNT(*) FROM memories")
    total = cursor.fetchone()[0]

    # By type
    cursor.execute("""
        SELECT memory_type, COUNT(*)
        FROM memories
        GROUP BY memory_type
        ORDER BY COUNT(*) DESC
    """)
    by_type = cursor.fetchall()

    # By project
    cursor.execute("""
        SELECT project, COUNT(*)
        FROM memories
        WHERE project IS NOT NULL
        GROUP BY project
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    by_project = cursor.fetchall()

    # Database size
    db_size = os.path.getsize(DB_PATH) / 1024  # KB

    conn.close()

    return {
        'total': total,
        'by_type': by_type,
        'by_project': by_project,
        'db_size_kb': db_size
    }

def find_duplicates():
    """Find potential duplicate memories."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find memories with very similar summaries
    cursor.execute("""
        SELECT m1.id, m1.summary, m2.id, m2.summary
        FROM memories m1
        JOIN memories m2 ON m1.id < m2.id
        WHERE m1.summary = m2.summary
        OR (m1.project = m2.project AND m1.memory_type = m2.memory_type
            AND substr(m1.content, 1, 100) = substr(m2.content, 1, 100))
    """)
    duplicates = cursor.fetchall()
    conn.close()

    return duplicates

def find_low_value_old():
    """Find old, low-importance memories."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cutoff = (datetime.now() - timedelta(days=90)).isoformat()
    cursor.execute("""
        SELECT id, summary, importance, created_at, project
        FROM memories
        WHERE importance <= 3
        AND created_at < ?
        ORDER BY created_at
    """, (cutoff,))

    old_low = cursor.fetchall()
    conn.close()

    return old_low

def find_orphan_projects():
    """Find projects with very few memories."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT project, COUNT(*) as cnt
        FROM memories
        WHERE project IS NOT NULL
        GROUP BY project
        HAVING cnt <= 2
        ORDER BY cnt
    """)

    orphans = cursor.fetchall()
    conn.close()

    return orphans

def verify_backups():
    """Check backup health."""
    backup_dir = DB_PATH.parent.parent / "backups"

    hourly = list((backup_dir / "hourly").glob("*.db"))
    daily = list((backup_dir / "daily").glob("*.db"))
    weekly = list((backup_dir / "weekly").glob("*.db"))

    return {
        'hourly': len(hourly),
        'daily': len(daily),
        'weekly': len(weekly),
        'latest_hourly': max(hourly, key=lambda x: x.stat().st_mtime).name if hourly else None
    }

def run_health_check():
    """Run full health check and print report."""
    print("=" * 60)
    print("MEMORY SYSTEM HEALTH CHECK")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Stats
    stats = get_stats()
    print(f"\n📊 STATISTICS")
    print(f"   Total memories: {stats['total']}")
    print(f"   Database size: {stats['db_size_kb']:.1f} KB")
    print(f"\n   By Type:")
    for t, c in stats['by_type']:
        print(f"      {t}: {c}")
    print(f"\n   Top Projects:")
    for p, c in stats['by_project']:
        print(f"      {p}: {c}")

    # Duplicates
    duplicates = find_duplicates()
    print(f"\n🔍 DUPLICATES: {len(duplicates)} potential duplicates found")
    if duplicates:
        for d in duplicates[:5]:
            print(f"   IDs {d[0]} and {d[2]}: {d[1][:50]}...")

    # Old low-value
    old_low = find_low_value_old()
    print(f"\n📅 OLD LOW-VALUE: {len(old_low)} memories (>90 days, importance ≤3)")
    if old_low:
        for m in old_low[:5]:
            print(f"   ID {m[0]}: {m[1][:40]}... (importance: {m[2]})")

    # Orphan projects
    orphans = find_orphan_projects()
    print(f"\n👻 ORPHAN PROJECTS: {len(orphans)} projects with ≤2 memories")
    for p, c in orphans:
        print(f"   {p}: {c} memories")

    # Backups
    backups = verify_backups()
    print(f"\n💾 BACKUPS")
    print(f"   Hourly: {backups['hourly']} files")
    print(f"   Daily: {backups['daily']} files")
    print(f"   Weekly: {backups['weekly']} files")
    print(f"   Latest: {backups['latest_hourly']}")

    # Health assessment
    print(f"\n" + "=" * 60)
    health_score = 100
    issues = []

    if stats['total'] > 5000:
        health_score -= 20
        issues.append("High memory count - consider archiving")
    if stats['db_size_kb'] > 50000:
        health_score -= 20
        issues.append("Large database - consider cleanup")
    if len(duplicates) > 10:
        health_score -= 10
        issues.append("Many duplicates detected")
    if len(old_low) > 50:
        health_score -= 10
        issues.append("Many old low-value memories")
    if backups['hourly'] < 10:
        health_score -= 10
        issues.append("Backup frequency may be low")

    status = "✅ HEALTHY" if health_score >= 80 else "⚠️ NEEDS ATTENTION" if health_score >= 60 else "❌ CRITICAL"
    print(f"HEALTH SCORE: {health_score}/100 {status}")
    if issues:
        print("Issues:")
        for i in issues:
            print(f"   - {i}")
    print("=" * 60)

if __name__ == "__main__":
    run_health_check()
