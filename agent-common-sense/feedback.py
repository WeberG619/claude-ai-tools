"""
Outcome tracking for the Common Sense Engine.

Closes the feedback loop: track whether corrections actually help,
and use that data to prioritize, reinforce, or deprecate corrections.

Usage:
    from feedback import FeedbackTracker

    tracker = FeedbackTracker(db_path)

    # After a correction was surfaced and followed
    tracker.correction_helped(correction_id=42, helped=True, notes="caught wrong deploy path")

    # Check how effective a correction is
    stats = tracker.get_effectiveness(correction_id=42)
    print(f"Help rate: {stats['help_rate']:.0%}")

    # Find the most valuable corrections
    top = tracker.get_top_corrections(domain="revit", limit=5)

    # Find stale corrections that need review
    stale = tracker.get_stale_corrections(days=90)
"""

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from typing import Optional


class FeedbackTracker:
    """Tracks correction outcomes to close the learning loop."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        """Add feedback columns to the memories table if they don't exist."""
        if not self.db_path:
            return

        try:
            conn = sqlite3.connect(self.db_path)

            # Check existing columns
            cursor = conn.execute("PRAGMA table_info(memories)")
            existing_cols = {row[1] for row in cursor.fetchall()}

            migrations = {
                "helped_count": "ALTER TABLE memories ADD COLUMN helped_count INTEGER DEFAULT 0",
                "not_helped_count": "ALTER TABLE memories ADD COLUMN not_helped_count INTEGER DEFAULT 0",
                "last_helped": "ALTER TABLE memories ADD COLUMN last_helped TEXT",
                "status": "ALTER TABLE memories ADD COLUMN status TEXT DEFAULT 'active'",
                "domain": "ALTER TABLE memories ADD COLUMN domain TEXT",
                "content_hash": "ALTER TABLE memories ADD COLUMN content_hash TEXT",
            }

            for col, sql in migrations.items():
                if col not in existing_cols:
                    try:
                        conn.execute(sql)
                    except sqlite3.OperationalError:
                        pass  # Column already exists (race condition)

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Schema migration failed: {e}", file=sys.stderr)

    def correction_helped(self, correction_id: int, helped: bool,
                          notes: str = "") -> bool:
        """Record whether following a correction helped with the current task.

        Args:
            correction_id: The memory/correction ID
            helped: True if following the correction prevented a mistake
            notes: Brief explanation of how it helped or why it didn't

        Returns:
            True if recorded successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)

            if helped:
                conn.execute("""
                    UPDATE memories
                    SET helped_count = COALESCE(helped_count, 0) + 1,
                        last_helped = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), correction_id))
            else:
                conn.execute("""
                    UPDATE memories
                    SET not_helped_count = COALESCE(not_helped_count, 0) + 1
                    WHERE id = ?
                """, (correction_id,))

            # Log the feedback event
            feedback_entry = {
                "correction_id": correction_id,
                "helped": helped,
                "notes": notes,
                "timestamp": datetime.now().isoformat(),
            }
            conn.execute("""
                INSERT INTO memories (content, tags, importance, project, memory_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                f"FEEDBACK: correction #{correction_id} {'helped' if helped else 'did not help'}. {notes}",
                json.dumps(["feedback", "outcome-tracking"]),
                2,  # Low importance — metadata, not actionable
                "general",
                "feedback",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Feedback recording failed: {e}", file=sys.stderr)
            return False

    def get_effectiveness(self, correction_id: int) -> dict:
        """Get effectiveness stats for a specific correction.

        Returns:
            Dict with helped_count, not_helped_count, help_rate,
            total_checks, last_helped, status
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?",
                (correction_id,)
            ).fetchone()
            conn.close()

            if not row:
                return {"error": f"Correction {correction_id} not found"}

            row = dict(row)
            helped = row.get("helped_count", 0) or 0
            not_helped = row.get("not_helped_count", 0) or 0
            total = helped + not_helped

            return {
                "correction_id": correction_id,
                "helped_count": helped,
                "not_helped_count": not_helped,
                "total_checks": total,
                "help_rate": helped / total if total > 0 else None,
                "last_helped": row.get("last_helped"),
                "status": row.get("status", "active"),
                "content_preview": (row.get("content", ""))[:100],
            }

        except Exception as e:
            return {"error": str(e)}

    def get_top_corrections(self, domain: str = None,
                            limit: int = 10) -> list[dict]:
        """Get the most effective corrections, ranked by help rate.

        Only includes corrections that have been checked at least once.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            sql = """
                SELECT *,
                    COALESCE(helped_count, 0) as h,
                    COALESCE(not_helped_count, 0) as nh,
                    CASE WHEN COALESCE(helped_count, 0) + COALESCE(not_helped_count, 0) > 0
                        THEN CAST(COALESCE(helped_count, 0) AS REAL) /
                             (COALESCE(helped_count, 0) + COALESCE(not_helped_count, 0))
                        ELSE 0.5
                    END as help_rate
                FROM memories
                WHERE memory_type = 'correction'
                AND (COALESCE(helped_count, 0) + COALESCE(not_helped_count, 0)) > 0
            """
            params = []

            if domain:
                sql += " AND (domain = ? OR content LIKE ?)"
                params.extend([domain, f"%{domain}%"])

            sql += " ORDER BY help_rate DESC, helped_count DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                row = dict(row)
                results.append({
                    "id": row["id"],
                    "content": row.get("content", "")[:200],
                    "helped_count": row.get("helped_count", 0),
                    "not_helped_count": row.get("not_helped_count", 0),
                    "help_rate": row.get("help_rate", 0.5),
                    "importance": row.get("importance", 5),
                    "domain": row.get("domain", ""),
                    "status": row.get("status", "active"),
                })

            conn.close()
            return results

        except Exception as e:
            print(f"Top corrections query failed: {e}", file=sys.stderr)
            return []

    def get_stale_corrections(self, days: int = 90) -> list[dict]:
        """Find corrections that are old and never been tested.

        These need review: are they still relevant?
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            cursor = conn.execute("""
                SELECT * FROM memories
                WHERE memory_type = 'correction'
                AND created_at < ?
                AND COALESCE(helped_count, 0) = 0
                AND COALESCE(not_helped_count, 0) = 0
                AND (status IS NULL OR status = 'active')
                ORDER BY created_at ASC
            """, (cutoff,))

            results = []
            for row in cursor.fetchall():
                row = dict(row)
                results.append({
                    "id": row["id"],
                    "content": row.get("content", "")[:200],
                    "created_at": row.get("created_at", ""),
                    "importance": row.get("importance", 5),
                    "domain": row.get("domain", ""),
                    "recommendation": "Review and either validate or deprecate",
                })

            conn.close()
            return results

        except Exception as e:
            print(f"Stale query failed: {e}", file=sys.stderr)
            return []

    def get_feedback_summary(self) -> dict:
        """Get an overall summary of feedback tracking.

        Returns total corrections, how many have been tested,
        average help rate, and domain breakdown.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM memories WHERE memory_type = 'correction'"
            ).fetchone()["cnt"]

            tested = conn.execute("""
                SELECT COUNT(*) as cnt FROM memories
                WHERE memory_type = 'correction'
                AND (COALESCE(helped_count, 0) + COALESCE(not_helped_count, 0)) > 0
            """).fetchone()["cnt"]

            # Aggregate help rate
            stats = conn.execute("""
                SELECT
                    SUM(COALESCE(helped_count, 0)) as total_helped,
                    SUM(COALESCE(not_helped_count, 0)) as total_not_helped
                FROM memories WHERE memory_type = 'correction'
            """).fetchone()

            total_helped = stats["total_helped"] or 0
            total_not_helped = stats["total_not_helped"] or 0
            total_checks = total_helped + total_not_helped

            # Status breakdown
            status_rows = conn.execute("""
                SELECT COALESCE(status, 'active') as s, COUNT(*) as cnt
                FROM memories WHERE memory_type = 'correction'
                GROUP BY s
            """).fetchall()
            status_breakdown = {row["s"]: row["cnt"] for row in status_rows}

            conn.close()

            return {
                "total_corrections": total,
                "tested_corrections": tested,
                "untested_corrections": total - tested,
                "test_coverage": tested / total if total > 0 else 0,
                "total_feedback_events": total_checks,
                "total_helped": total_helped,
                "total_not_helped": total_not_helped,
                "overall_help_rate": total_helped / total_checks if total_checks > 0 else None,
                "status_breakdown": status_breakdown,
            }

        except Exception as e:
            return {"error": str(e)}

    def bulk_deprecate_stale(self, days: int = 180, dry_run: bool = True) -> int:
        """Deprecate all corrections older than N days with no feedback.

        Returns count of corrections deprecated.
        """
        stale = self.get_stale_corrections(days=days)

        if dry_run:
            return len(stale)

        count = 0
        try:
            conn = sqlite3.connect(self.db_path)
            for correction in stale:
                conn.execute(
                    "UPDATE memories SET status = 'deprecated' WHERE id = ?",
                    (correction["id"],)
                )
                count += 1
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Bulk deprecate failed: {e}", file=sys.stderr)

        return count
