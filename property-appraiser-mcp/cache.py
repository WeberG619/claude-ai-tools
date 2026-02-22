"""
SQLite cache layer for property appraiser data.

Property assessment data changes slowly (annually for most fields),
so a 7-day TTL is reasonable. This avoids hammering the county
websites for repeated lookups of the same property.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("property-appraiser-mcp")

# Default cache TTL: 7 days in seconds
DEFAULT_TTL_SECONDS = 7 * 24 * 3600

# Database file lives next to this module
DB_PATH = Path(__file__).parent / "property_cache.db"


class PropertyCache:
    """SQLite-backed cache for property appraiser data."""

    def __init__(self, db_path: Optional[Path] = None, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.db_path = db_path or DB_PATH
        self.ttl_seconds = ttl_seconds
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_db()

    def _ensure_db(self):
        """Create the database and table if they don't exist."""
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS property_cache (
                folio TEXT NOT NULL,
                county TEXT NOT NULL,
                data_type TEXT NOT NULL DEFAULT 'details',
                data TEXT NOT NULL,
                fetched_at REAL NOT NULL,
                PRIMARY KEY (folio, county, data_type)
            )
            """
        )
        # Index for TTL cleanup
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cache_fetched
            ON property_cache (fetched_at)
            """
        )
        self._conn.commit()
        logger.info(f"Cache database ready at {self.db_path}")

    def get(
        self, folio: str, county: str, data_type: str = "details"
    ) -> Optional[dict]:
        """Retrieve cached data if it exists and hasn't expired.

        Args:
            folio: Property folio number (normalized, no dashes)
            county: County name ('broward' or 'miami-dade')
            data_type: Type of data ('details', 'search', 'sales')

        Returns:
            Parsed JSON data dict, or None if cache miss or expired.
        """
        try:
            cursor = self._conn.execute(
                """
                SELECT data, fetched_at FROM property_cache
                WHERE folio = ? AND county = ? AND data_type = ?
                """,
                (folio, county, data_type),
            )
            row = cursor.fetchone()
            if not row:
                return None

            data_str, fetched_at = row
            age = time.time() - fetched_at

            if age > self.ttl_seconds:
                logger.debug(
                    f"Cache expired for {county}/{folio}/{data_type} "
                    f"(age: {age/3600:.1f}h, TTL: {self.ttl_seconds/3600:.1f}h)"
                )
                return None

            logger.info(
                f"Cache hit for {county}/{folio}/{data_type} "
                f"(age: {age/3600:.1f}h)"
            )
            return json.loads(data_str)

        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.warning(f"Cache read error: {e}")
            return None

    def put(
        self, folio: str, county: str, data: dict, data_type: str = "details"
    ):
        """Store data in the cache.

        Args:
            folio: Property folio number
            county: County name
            data: Data dict to cache (will be JSON-serialized)
            data_type: Type of data
        """
        try:
            data_str = json.dumps(data, default=str)
            self._conn.execute(
                """
                INSERT OR REPLACE INTO property_cache
                    (folio, county, data_type, data, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (folio, county, data_type, data_str, time.time()),
            )
            self._conn.commit()
            logger.debug(f"Cached {county}/{folio}/{data_type}")
        except sqlite3.Error as e:
            logger.warning(f"Cache write error: {e}")

    def put_search_results(
        self, query: str, county: str, results: list[dict]
    ):
        """Cache search results keyed by query string.

        Uses the query as the 'folio' key and 'search' as data_type.
        """
        try:
            data_str = json.dumps(results, default=str)
            self._conn.execute(
                """
                INSERT OR REPLACE INTO property_cache
                    (folio, county, data_type, data, fetched_at)
                VALUES (?, ?, 'search', ?, ?)
                """,
                (query, county, data_str, time.time()),
            )
            self._conn.commit()
            logger.debug(f"Cached search results for '{query}' in {county}")
        except sqlite3.Error as e:
            logger.warning(f"Cache write error (search): {e}")

    def get_search_results(
        self, query: str, county: str
    ) -> Optional[list[dict]]:
        """Retrieve cached search results."""
        result = self.get(query, county, data_type="search")
        if result is not None and isinstance(result, list):
            return result
        return None

    def cleanup_expired(self):
        """Remove all expired entries from the cache."""
        try:
            cutoff = time.time() - self.ttl_seconds
            cursor = self._conn.execute(
                "DELETE FROM property_cache WHERE fetched_at < ?",
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
        """Clear all cached data."""
        try:
            self._conn.execute("DELETE FROM property_cache")
            self._conn.commit()
            logger.info("Cache cleared")
        except sqlite3.Error as e:
            logger.warning(f"Cache clear error: {e}")

    def stats(self) -> dict:
        """Get cache statistics."""
        try:
            cursor = self._conn.execute(
                "SELECT COUNT(*), MIN(fetched_at), MAX(fetched_at) FROM property_cache"
            )
            count, oldest, newest = cursor.fetchone()

            now = time.time()
            fresh = 0
            if count > 0:
                cursor = self._conn.execute(
                    "SELECT COUNT(*) FROM property_cache WHERE fetched_at > ?",
                    (now - self.ttl_seconds,),
                )
                fresh = cursor.fetchone()[0]

            return {
                "total_entries": count or 0,
                "fresh_entries": fresh,
                "expired_entries": (count or 0) - fresh,
                "oldest_age_hours": round((now - oldest) / 3600, 1) if oldest else 0,
                "newest_age_hours": round((now - newest) / 3600, 1) if newest else 0,
                "ttl_hours": round(self.ttl_seconds / 3600, 1),
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
