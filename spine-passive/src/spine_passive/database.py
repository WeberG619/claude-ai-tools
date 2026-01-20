"""
Database module for Spine Passive Learner.
Handles SQLite schema creation and all CRUD operations.
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

# Default database location
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "knowledge.db"


class Database:
    """SQLite database manager for Spine knowledge base."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = None

    @contextmanager
    def connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """Create all database tables."""
        with self.connection() as conn:
            # Projects table - main tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filepath TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    file_hash TEXT,
                    file_size INTEGER,
                    last_modified TIMESTAMP,

                    -- Extraction status
                    scanned_at TIMESTAMP,
                    extraction_status TEXT DEFAULT 'pending',
                    extraction_error TEXT,
                    extraction_duration_sec REAL,

                    -- Project metadata (from Revit)
                    project_name TEXT,
                    project_number TEXT,
                    project_address TEXT,
                    client_name TEXT,
                    project_status TEXT,

                    -- Computed metrics
                    level_count INTEGER,
                    sheet_count INTEGER,
                    view_count INTEGER,
                    room_count INTEGER,
                    family_count INTEGER,
                    wall_type_count INTEGER,

                    -- Classification
                    building_type TEXT,
                    project_size TEXT,
                    estimated_completion_pct REAL,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Sheets table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sheets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    sheet_number TEXT NOT NULL,
                    sheet_name TEXT,

                    discipline TEXT,
                    sheet_series TEXT,

                    viewport_count INTEGER,
                    has_titleblock BOOLEAN,
                    titleblock_type TEXT,

                    UNIQUE(project_id, sheet_number)
                )
            """)

            # Views table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS views (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    view_name TEXT NOT NULL,
                    view_type TEXT,
                    level_name TEXT,

                    is_on_sheet BOOLEAN,
                    detail_level TEXT,
                    scale TEXT,

                    UNIQUE(project_id, view_name)
                )
            """)

            # Levels table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS levels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    level_name TEXT NOT NULL,
                    elevation_ft REAL,
                    is_building_story BOOLEAN,

                    UNIQUE(project_id, level_name)
                )
            """)

            # Families table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS families (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    family_name TEXT NOT NULL,
                    family_category TEXT,
                    instance_count INTEGER,
                    type_count INTEGER,

                    UNIQUE(project_id, family_name, family_category)
                )
            """)

            # Wall types table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wall_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    type_name TEXT NOT NULL,
                    wall_function TEXT,
                    width_inches REAL,
                    instance_count INTEGER,

                    UNIQUE(project_id, type_name)
                )
            """)

            # Rooms table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    room_name TEXT,
                    room_number TEXT,
                    level_name TEXT,
                    area_sqft REAL,

                    UNIQUE(project_id, room_number, level_name)
                )
            """)

            # Patterns table - aggregated learnings
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,
                    pattern_key TEXT NOT NULL,
                    pattern_value TEXT,
                    occurrence_count INTEGER DEFAULT 1,
                    confidence REAL,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,

                    UNIQUE(pattern_type, pattern_key)
                )
            """)

            # Extraction log table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS extraction_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    status TEXT,
                    sheets_extracted INTEGER,
                    views_extracted INTEGER,
                    families_extracted INTEGER,
                    error_message TEXT
                )
            """)

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(extraction_status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_filepath ON projects(filepath)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sheets_project ON sheets(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_views_project ON views(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_families_project ON families(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type)")

    # ----- Project Operations -----

    def add_project(self, filepath: str, filename: str, file_size: int,
                    last_modified: datetime, file_hash: Optional[str] = None) -> int:
        """Add a new project to track. Returns project ID."""
        with self.connection() as conn:
            cursor = conn.execute("""
                INSERT INTO projects (filepath, filename, file_size, last_modified, file_hash, scanned_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(filepath) DO UPDATE SET
                    file_size = excluded.file_size,
                    last_modified = excluded.last_modified,
                    file_hash = excluded.file_hash,
                    scanned_at = excluded.scanned_at
            """, (filepath, filename, file_size, last_modified, file_hash, datetime.now()))
            return cursor.lastrowid

    def get_project_by_path(self, filepath: str) -> Optional[Dict]:
        """Get project by filepath."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE filepath = ?", (filepath,)
            ).fetchone()
            return dict(row) if row else None

    def get_pending_projects(self, limit: Optional[int] = None) -> List[Dict]:
        """Get projects pending extraction."""
        with self.connection() as conn:
            query = """
                SELECT * FROM projects
                WHERE extraction_status = 'pending'
                ORDER BY scanned_at ASC
            """
            if limit:
                query += f" LIMIT {limit}"
            return [dict(row) for row in conn.execute(query).fetchall()]

    def update_project_status(self, project_id: int, status: str,
                               error: Optional[str] = None,
                               duration: Optional[float] = None) -> None:
        """Update project extraction status."""
        with self.connection() as conn:
            conn.execute("""
                UPDATE projects
                SET extraction_status = ?, extraction_error = ?, extraction_duration_sec = ?
                WHERE id = ?
            """, (status, error, duration, project_id))

    def update_project_metadata(self, project_id: int, metadata: Dict) -> None:
        """Update project metadata from Revit extraction."""
        with self.connection() as conn:
            conn.execute("""
                UPDATE projects
                SET project_name = ?, project_number = ?, project_address = ?,
                    client_name = ?, project_status = ?,
                    level_count = ?, sheet_count = ?, view_count = ?,
                    room_count = ?, family_count = ?, wall_type_count = ?
                WHERE id = ?
            """, (
                metadata.get('project_name'),
                metadata.get('project_number'),
                metadata.get('project_address'),
                metadata.get('client_name'),
                metadata.get('project_status'),
                metadata.get('level_count'),
                metadata.get('sheet_count'),
                metadata.get('view_count'),
                metadata.get('room_count'),
                metadata.get('family_count'),
                metadata.get('wall_type_count'),
                project_id
            ))

    def get_all_projects(self) -> List[Dict]:
        """Get all tracked projects."""
        with self.connection() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM projects ORDER BY filename").fetchall()]

    # ----- Sheet Operations -----

    def add_sheet(self, project_id: int, sheet_number: str, sheet_name: str,
                  discipline: str, sheet_series: str, viewport_count: int,
                  titleblock_type: Optional[str] = None) -> int:
        """Add a sheet to a project."""
        with self.connection() as conn:
            cursor = conn.execute("""
                INSERT INTO sheets (project_id, sheet_number, sheet_name, discipline,
                                    sheet_series, viewport_count, has_titleblock, titleblock_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, sheet_number) DO UPDATE SET
                    sheet_name = excluded.sheet_name,
                    discipline = excluded.discipline,
                    sheet_series = excluded.sheet_series,
                    viewport_count = excluded.viewport_count,
                    titleblock_type = excluded.titleblock_type
            """, (project_id, sheet_number, sheet_name, discipline, sheet_series,
                  viewport_count, titleblock_type is not None, titleblock_type))
            return cursor.lastrowid

    def get_sheets_for_project(self, project_id: int) -> List[Dict]:
        """Get all sheets for a project."""
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM sheets WHERE project_id = ? ORDER BY sheet_number", (project_id,)
            ).fetchall()]

    # ----- View Operations -----

    def add_view(self, project_id: int, view_name: str, view_type: str,
                 level_name: Optional[str], is_on_sheet: bool,
                 detail_level: Optional[str], scale: Optional[str]) -> int:
        """Add a view to a project."""
        with self.connection() as conn:
            cursor = conn.execute("""
                INSERT INTO views (project_id, view_name, view_type, level_name,
                                   is_on_sheet, detail_level, scale)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, view_name) DO UPDATE SET
                    view_type = excluded.view_type,
                    level_name = excluded.level_name,
                    is_on_sheet = excluded.is_on_sheet,
                    detail_level = excluded.detail_level,
                    scale = excluded.scale
            """, (project_id, view_name, view_type, level_name, is_on_sheet, detail_level, scale))
            return cursor.lastrowid

    def get_views_for_project(self, project_id: int) -> List[Dict]:
        """Get all views for a project."""
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM views WHERE project_id = ? ORDER BY view_name", (project_id,)
            ).fetchall()]

    # ----- Level Operations -----

    def add_level(self, project_id: int, level_name: str,
                  elevation_ft: float, is_building_story: bool) -> int:
        """Add a level to a project."""
        with self.connection() as conn:
            cursor = conn.execute("""
                INSERT INTO levels (project_id, level_name, elevation_ft, is_building_story)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_id, level_name) DO UPDATE SET
                    elevation_ft = excluded.elevation_ft,
                    is_building_story = excluded.is_building_story
            """, (project_id, level_name, elevation_ft, is_building_story))
            return cursor.lastrowid

    def get_levels_for_project(self, project_id: int) -> List[Dict]:
        """Get all levels for a project."""
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM levels WHERE project_id = ? ORDER BY elevation_ft", (project_id,)
            ).fetchall()]

    # ----- Family Operations -----

    def add_family(self, project_id: int, family_name: str, family_category: str,
                   instance_count: int, type_count: int) -> int:
        """Add a family to a project."""
        with self.connection() as conn:
            cursor = conn.execute("""
                INSERT INTO families (project_id, family_name, family_category, instance_count, type_count)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(project_id, family_name, family_category) DO UPDATE SET
                    instance_count = excluded.instance_count,
                    type_count = excluded.type_count
            """, (project_id, family_name, family_category, instance_count, type_count))
            return cursor.lastrowid

    def get_families_for_project(self, project_id: int) -> List[Dict]:
        """Get all families for a project."""
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM families WHERE project_id = ? ORDER BY family_category, family_name",
                (project_id,)
            ).fetchall()]

    def get_all_families(self) -> List[Dict]:
        """Get all families across all projects with usage counts."""
        with self.connection() as conn:
            return [dict(row) for row in conn.execute("""
                SELECT family_name, family_category,
                       COUNT(DISTINCT project_id) as project_count,
                       SUM(instance_count) as total_instances
                FROM families
                GROUP BY family_name, family_category
                ORDER BY project_count DESC
            """).fetchall()]

    # ----- Wall Type Operations -----

    def add_wall_type(self, project_id: int, type_name: str,
                      wall_function: Optional[str], width_inches: Optional[float],
                      instance_count: int) -> int:
        """Add a wall type to a project."""
        with self.connection() as conn:
            cursor = conn.execute("""
                INSERT INTO wall_types (project_id, type_name, wall_function, width_inches, instance_count)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(project_id, type_name) DO UPDATE SET
                    wall_function = excluded.wall_function,
                    width_inches = excluded.width_inches,
                    instance_count = excluded.instance_count
            """, (project_id, type_name, wall_function, width_inches, instance_count))
            return cursor.lastrowid

    def get_wall_types_for_project(self, project_id: int) -> List[Dict]:
        """Get all wall types for a project."""
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM wall_types WHERE project_id = ? ORDER BY type_name", (project_id,)
            ).fetchall()]

    # ----- Room Operations -----

    def add_room(self, project_id: int, room_name: str, room_number: str,
                 level_name: str, area_sqft: float) -> int:
        """Add a room to a project."""
        with self.connection() as conn:
            cursor = conn.execute("""
                INSERT INTO rooms (project_id, room_name, room_number, level_name, area_sqft)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(project_id, room_number, level_name) DO UPDATE SET
                    room_name = excluded.room_name,
                    area_sqft = excluded.area_sqft
            """, (project_id, room_name, room_number, level_name, area_sqft))
            return cursor.lastrowid

    def get_rooms_for_project(self, project_id: int) -> List[Dict]:
        """Get all rooms for a project."""
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM rooms WHERE project_id = ? ORDER BY level_name, room_number", (project_id,)
            ).fetchall()]

    # ----- Pattern Operations -----

    def upsert_pattern(self, pattern_type: str, pattern_key: str,
                       pattern_value: Any, confidence: float = 1.0) -> int:
        """Insert or update a pattern."""
        value_json = json.dumps(pattern_value) if not isinstance(pattern_value, str) else pattern_value
        with self.connection() as conn:
            cursor = conn.execute("""
                INSERT INTO patterns (pattern_type, pattern_key, pattern_value, confidence, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(pattern_type, pattern_key) DO UPDATE SET
                    pattern_value = excluded.pattern_value,
                    occurrence_count = occurrence_count + 1,
                    confidence = excluded.confidence,
                    updated_at = excluded.updated_at
            """, (pattern_type, pattern_key, value_json, confidence, datetime.now()))
            return cursor.lastrowid

    def get_patterns(self, pattern_type: Optional[str] = None) -> List[Dict]:
        """Get patterns, optionally filtered by type."""
        with self.connection() as conn:
            if pattern_type:
                rows = conn.execute(
                    "SELECT * FROM patterns WHERE pattern_type = ? ORDER BY occurrence_count DESC",
                    (pattern_type,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM patterns ORDER BY pattern_type, occurrence_count DESC"
                ).fetchall()
            return [dict(row) for row in rows]

    # ----- Extraction Log Operations -----

    def log_extraction_start(self, project_id: int) -> int:
        """Log start of extraction."""
        with self.connection() as conn:
            cursor = conn.execute("""
                INSERT INTO extraction_log (project_id, started_at, status)
                VALUES (?, ?, 'started')
            """, (project_id, datetime.now()))
            return cursor.lastrowid

    def log_extraction_complete(self, log_id: int, sheets: int, views: int,
                                 families: int, status: str = 'complete',
                                 error: Optional[str] = None) -> None:
        """Log completion of extraction."""
        with self.connection() as conn:
            conn.execute("""
                UPDATE extraction_log
                SET completed_at = ?, status = ?, sheets_extracted = ?,
                    views_extracted = ?, families_extracted = ?, error_message = ?
                WHERE id = ?
            """, (datetime.now(), status, sheets, views, families, error, log_id))

    # ----- Statistics -----

    def get_stats(self) -> Dict:
        """Get overall database statistics."""
        with self.connection() as conn:
            stats = {}

            # Project counts
            row = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN extraction_status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN extraction_status = 'complete' THEN 1 ELSE 0 END) as complete,
                    SUM(CASE WHEN extraction_status = 'error' THEN 1 ELSE 0 END) as errors
                FROM projects
            """).fetchone()
            stats['projects'] = dict(row)

            # Total counts
            stats['total_sheets'] = conn.execute("SELECT COUNT(*) FROM sheets").fetchone()[0]
            stats['total_views'] = conn.execute("SELECT COUNT(*) FROM views").fetchone()[0]
            stats['total_levels'] = conn.execute("SELECT COUNT(*) FROM levels").fetchone()[0]
            stats['total_families'] = conn.execute("SELECT COUNT(*) FROM families").fetchone()[0]
            stats['total_wall_types'] = conn.execute("SELECT COUNT(*) FROM wall_types").fetchone()[0]
            stats['total_rooms'] = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
            stats['total_patterns'] = conn.execute("SELECT COUNT(*) FROM patterns").fetchone()[0]

            # Average metrics
            row = conn.execute("""
                SELECT
                    AVG(sheet_count) as avg_sheets,
                    AVG(view_count) as avg_views,
                    AVG(level_count) as avg_levels,
                    AVG(room_count) as avg_rooms
                FROM projects
                WHERE extraction_status = 'complete'
            """).fetchone()
            stats['averages'] = dict(row) if row else {}

            return stats

    # ----- Utility -----

    @staticmethod
    def compute_file_hash(filepath: str) -> str:
        """Compute MD5 hash of a file (first 64KB for speed)."""
        md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            md5.update(f.read(65536))  # First 64KB
        return md5.hexdigest()

    def clear_project_data(self, project_id: int) -> None:
        """Clear all extracted data for a project (for re-extraction)."""
        with self.connection() as conn:
            conn.execute("DELETE FROM sheets WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM views WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM levels WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM families WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM wall_types WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM rooms WHERE project_id = ?", (project_id,))
            conn.execute("""
                UPDATE projects
                SET extraction_status = 'pending', extraction_error = NULL
                WHERE id = ?
            """, (project_id,))
