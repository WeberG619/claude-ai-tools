"""
SQLite cache layer for eTRAKiT permit data.

Permit data changes frequently (inspections, reviews, status updates),
so we use a 30-minute TTL. This avoids hammering the eTRAKiT portals
while still keeping data reasonably fresh.

Also tracks "last known status" for each permit to support
the monitor_permit_status tool.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("etrakit-mcp")

# Default cache TTL: 30 minutes in seconds
DEFAULT_TTL_SECONDS = 30 * 60

# Database file lives next to this module
DB_PATH = Path(__file__).parent / "permit_cache.db"


class PermitCache:
    """SQLite-backed cache for eTRAKiT permit data."""

    def __init__(self, db_path: Optional[Path] = None, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.db_path = db_path or DB_PATH
        self.ttl_seconds = ttl_seconds
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_db()

    def _ensure_db(self):
        """Create the database and tables if they don't exist."""
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")

        # Main cache table for all permit data
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS permit_cache (
                cache_key TEXT NOT NULL,
                city TEXT NOT NULL,
                data_type TEXT NOT NULL DEFAULT 'details',
                data TEXT NOT NULL,
                fetched_at REAL NOT NULL,
                PRIMARY KEY (cache_key, city, data_type)
            )
            """
        )

        # Status tracking table for monitoring changes
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS permit_status (
                permit_number TEXT NOT NULL,
                city TEXT NOT NULL,
                status TEXT NOT NULL,
                last_checked REAL NOT NULL,
                details_snapshot TEXT,
                PRIMARY KEY (permit_number, city)
            )
            """
        )

        # Indexes
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cache_fetched
            ON permit_cache (fetched_at)
            """
        )
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_status_checked
            ON permit_status (last_checked)
            """
        )

        self._conn.commit()
        logger.info(f"Cache database ready at {self.db_path}")

    # ---- General Cache ----

    def get(
        self, cache_key: str, city: str, data_type: str = "details"
    ) -> Optional[dict]:
        """Retrieve cached data if it exists and hasn't expired.

        Args:
            cache_key: Cache key (permit number, search query, etc.)
            city: City identifier (e.g., 'coral-springs')
            data_type: Type of data ('details', 'search', 'inspections', 'comments')

        Returns:
            Parsed JSON data, or None if cache miss or expired.
        """
        try:
            cursor = self._conn.execute(
                """
                SELECT data, fetched_at FROM permit_cache
                WHERE cache_key = ? AND city = ? AND data_type = ?
                """,
                (cache_key, city, data_type),
            )
            row = cursor.fetchone()
            if not row:
                return None

            data_str, fetched_at = row
            age = time.time() - fetched_at

            if age > self.ttl_seconds:
                logger.debug(
                    f"Cache expired for {city}/{cache_key}/{data_type} "
                    f"(age: {age/60:.1f}m, TTL: {self.ttl_seconds/60:.1f}m)"
                )
                return None

            logger.info(
                f"Cache hit for {city}/{cache_key}/{data_type} "
                f"(age: {age/60:.1f}m)"
            )
            return json.loads(data_str)

        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.warning(f"Cache read error: {e}")
            return None

    def put(
        self, cache_key: str, city: str, data, data_type: str = "details"
    ):
        """Store data in the cache.

        Args:
            cache_key: Cache key (permit number, search query, etc.)
            city: City identifier
            data: Data to cache (will be JSON-serialized)
            data_type: Type of data
        """
        try:
            data_str = json.dumps(data, default=str)
            self._conn.execute(
                """
                INSERT OR REPLACE INTO permit_cache
                    (cache_key, city, data_type, data, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (cache_key, city, data_type, data_str, time.time()),
            )
            self._conn.commit()
            logger.debug(f"Cached {city}/{cache_key}/{data_type}")
        except sqlite3.Error as e:
            logger.warning(f"Cache write error: {e}")

    def put_search_results(
        self, query: str, city: str, results: list[dict]
    ):
        """Cache search results keyed by query string."""
        try:
            data_str = json.dumps(results, default=str)
            self._conn.execute(
                """
                INSERT OR REPLACE INTO permit_cache
                    (cache_key, city, data_type, data, fetched_at)
                VALUES (?, ?, 'search', ?, ?)
                """,
                (query, city, data_str, time.time()),
            )
            self._conn.commit()
            logger.debug(f"Cached search results for '{query}' in {city}")
        except sqlite3.Error as e:
            logger.warning(f"Cache write error (search): {e}")

    def get_search_results(
        self, query: str, city: str
    ) -> Optional[list[dict]]:
        """Retrieve cached search results."""
        result = self.get(query, city, data_type="search")
        if result is not None and isinstance(result, list):
            return result
        return None

    # ---- Status Monitoring ----

    def get_last_status(self, permit_number: str, city: str) -> Optional[dict]:
        """Get the last known status for a permit.

        Returns:
            Dict with: status, last_checked, details_snapshot
            or None if never tracked.
        """
        try:
            cursor = self._conn.execute(
                """
                SELECT status, last_checked, details_snapshot
                FROM permit_status
                WHERE permit_number = ? AND city = ?
                """,
                (permit_number, city),
            )
            row = cursor.fetchone()
            if not row:
                return None

            return {
                "status": row[0],
                "last_checked": row[1],
                "details_snapshot": json.loads(row[2]) if row[2] else None,
            }
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.warning(f"Status read error: {e}")
            return None

    def update_status(
        self, permit_number: str, city: str, status: str,
        details_snapshot: Optional[dict] = None
    ):
        """Update the tracked status for a permit.

        Args:
            permit_number: Permit number
            city: City identifier
            status: Current permit status
            details_snapshot: Optional snapshot of key details for diff comparison
        """
        try:
            snapshot_str = json.dumps(details_snapshot, default=str) if details_snapshot else None
            self._conn.execute(
                """
                INSERT OR REPLACE INTO permit_status
                    (permit_number, city, status, last_checked, details_snapshot)
                VALUES (?, ?, ?, ?, ?)
                """,
                (permit_number, city, status, time.time(), snapshot_str),
            )
            self._conn.commit()
            logger.debug(f"Updated status for {city}/{permit_number}: {status}")
        except sqlite3.Error as e:
            logger.warning(f"Status write error: {e}")

    def compare_status(
        self, permit_number: str, city: str, current_details: dict
    ) -> dict:
        """Compare current permit details against the last known snapshot.

        Returns a dict with:
            changed: bool - whether any changes were detected
            status_changed: bool - whether the overall status changed
            old_status: previous status (or None)
            new_status: current status
            changes: list of change descriptions
        """
        last = self.get_last_status(permit_number, city)

        # Extract current status from details
        current_status = ""
        permit_info = current_details.get("permit_info", {})
        for key, val in permit_info.items():
            if "status" in key.lower():
                current_status = val
                break

        result = {
            "changed": False,
            "status_changed": False,
            "old_status": None,
            "new_status": current_status,
            "changes": [],
            "first_check": last is None,
        }

        if last is None:
            result["changed"] = True
            result["changes"].append("First time checking this permit")
            return result

        result["old_status"] = last["status"]

        # Check status change
        if current_status and last["status"] and current_status != last["status"]:
            result["changed"] = True
            result["status_changed"] = True
            result["changes"].append(
                f"Status changed: '{last['status']}' -> '{current_status}'"
            )

        # Compare snapshots if available
        old_snapshot = last.get("details_snapshot") or {}

        # Check for new inspections
        old_insp_count = len(old_snapshot.get("inspections", []))
        new_insp_count = len(current_details.get("inspections", []))
        if new_insp_count > old_insp_count:
            result["changed"] = True
            diff = new_insp_count - old_insp_count
            result["changes"].append(f"{diff} new inspection(s) added")

        # Check for new chronology entries
        old_chron_count = len(old_snapshot.get("chronology", []))
        new_chron_count = len(current_details.get("chronology", []))
        if new_chron_count > old_chron_count:
            result["changed"] = True
            diff = new_chron_count - old_chron_count
            result["changes"].append(f"{diff} new chronology entry/entries")

        # Check for new reviews
        old_rev_count = len(old_snapshot.get("reviews", []))
        new_rev_count = len(current_details.get("reviews", []))
        if new_rev_count > old_rev_count:
            result["changed"] = True
            diff = new_rev_count - old_rev_count
            result["changes"].append(f"{diff} new review(s)")

        # Check for new conditions
        old_cond_count = len(old_snapshot.get("conditions", []))
        new_cond_count = len(current_details.get("conditions", []))
        if new_cond_count > old_cond_count:
            result["changed"] = True
            diff = new_cond_count - old_cond_count
            result["changes"].append(f"{diff} new condition(s)")

        # Check for fee changes
        old_fee_count = len(old_snapshot.get("fees", []))
        new_fee_count = len(current_details.get("fees", []))
        if new_fee_count > old_fee_count:
            result["changed"] = True
            diff = new_fee_count - old_fee_count
            result["changes"].append(f"{diff} new fee entry/entries")

        return result

    # ---- Maintenance ----

    def cleanup_expired(self):
        """Remove all expired cache entries."""
        try:
            cutoff = time.time() - self.ttl_seconds
            cursor = self._conn.execute(
                "DELETE FROM permit_cache WHERE fetched_at < ?",
                (cutoff,),
            )
            deleted = cursor.rowcount
            self._conn.commit()
            if deleted > 0:
                logger.info(f"Cache cleanup: removed {deleted} expired entries")
            return deleted
        except sqlite3.Error as e:
            logger.warning(f"Cache cleanup error: {e}")
            return 0

    def clear(self):
        """Clear all cached data (but keep status tracking)."""
        try:
            self._conn.execute("DELETE FROM permit_cache")
            self._conn.commit()
            logger.info("Cache cleared")
        except sqlite3.Error as e:
            logger.warning(f"Cache clear error: {e}")

    def clear_all(self):
        """Clear everything including status tracking."""
        try:
            self._conn.execute("DELETE FROM permit_cache")
            self._conn.execute("DELETE FROM permit_status")
            self._conn.commit()
            logger.info("Cache and status tracking cleared")
        except sqlite3.Error as e:
            logger.warning(f"Cache clear error: {e}")

    def stats(self) -> dict:
        """Get cache statistics."""
        try:
            cursor = self._conn.execute(
                "SELECT COUNT(*), MIN(fetched_at), MAX(fetched_at) FROM permit_cache"
            )
            count, oldest, newest = cursor.fetchone()

            now = time.time()
            fresh = 0
            if count and count > 0:
                cursor = self._conn.execute(
                    "SELECT COUNT(*) FROM permit_cache WHERE fetched_at > ?",
                    (now - self.ttl_seconds,),
                )
                fresh = cursor.fetchone()[0]

            # Count tracked permits
            cursor = self._conn.execute("SELECT COUNT(*) FROM permit_status")
            tracked = cursor.fetchone()[0]

            return {
                "total_entries": count or 0,
                "fresh_entries": fresh,
                "expired_entries": (count or 0) - fresh,
                "tracked_permits": tracked,
                "oldest_age_minutes": round((now - oldest) / 60, 1) if oldest else 0,
                "newest_age_minutes": round((now - newest) / 60, 1) if newest else 0,
                "ttl_minutes": round(self.ttl_seconds / 60, 1),
                "db_path": str(self.db_path),
            }
        except sqlite3.Error as e:
            return {"error": str(e)}

    def close(self):
        """Close the database connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
