"""
Database Models - SQLite storage for photos and projects.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import asdict

from photo_analyzer import PhotoAnalysis, PhotoTag


class Database:
    """SQLite database for photo intelligence data."""

    def __init__(self, db_path: str = "photo_intelligence.db"):
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def _create_tables(self):
        """Create database tables."""
        cursor = self.conn.cursor()

        # Projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                client TEXT,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Photos table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                description TEXT,
                room_type TEXT,
                floor_level TEXT,
                trade TEXT,
                work_stage TEXT,
                issue_count INTEGER DEFAULT 0,
                analyzed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        # Tags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id INTEGER,
                category TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL,
                FOREIGN KEY (photo_id) REFERENCES photos(id)
            )
        """)

        # Issues table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id INTEGER,
                issue_type TEXT,
                description TEXT,
                severity TEXT,
                resolved INTEGER DEFAULT 0,
                FOREIGN KEY (photo_id) REFERENCES photos(id)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_photos_project ON photos(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_photo ON tags(photo_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_category ON tags(category, value)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_issues_photo ON issues(photo_id)")

        self.conn.commit()

    # Project methods
    def create_project(self, name: str, client: str = None, address: str = None) -> int:
        """Create a new project."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO projects (name, client, address) VALUES (?, ?, ?)",
            (name, client, address)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_project(self, project_id: int) -> Optional[Dict]:
        """Get a project by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_projects(self) -> List[Dict]:
        """List all projects."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    # Photo methods
    def save_photo_analysis(self, project_id: int, file_path: str,
                           analysis: PhotoAnalysis) -> int:
        """Save photo analysis to database."""
        cursor = self.conn.cursor()

        # Insert photo
        cursor.execute("""
            INSERT INTO photos
            (project_id, filename, file_path, description, room_type,
             floor_level, trade, work_stage, issue_count, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            analysis.filename,
            file_path,
            analysis.description,
            analysis.room_type,
            analysis.floor_level,
            analysis.trade,
            analysis.work_stage,
            analysis.issue_count,
            analysis.analyzed_at.isoformat()
        ))
        photo_id = cursor.lastrowid

        # Insert tags
        for tag in analysis.tags:
            cursor.execute("""
                INSERT INTO tags (photo_id, category, value, confidence)
                VALUES (?, ?, ?, ?)
            """, (photo_id, tag.category, tag.value, tag.confidence))

        # Insert issues
        for issue in analysis.issues:
            cursor.execute("""
                INSERT INTO issues (photo_id, issue_type, description, severity)
                VALUES (?, ?, ?, ?)
            """, (
                photo_id,
                issue.get("type"),
                issue.get("description"),
                issue.get("severity", "medium")
            ))

        self.conn.commit()
        return photo_id

    def get_photo(self, photo_id: int) -> Optional[Dict]:
        """Get photo with all tags and issues."""
        cursor = self.conn.cursor()

        # Get photo
        cursor.execute("SELECT * FROM photos WHERE id = ?", (photo_id,))
        photo = cursor.fetchone()
        if not photo:
            return None

        photo_dict = dict(photo)

        # Get tags
        cursor.execute("SELECT * FROM tags WHERE photo_id = ?", (photo_id,))
        photo_dict["tags"] = [dict(row) for row in cursor.fetchall()]

        # Get issues
        cursor.execute("SELECT * FROM issues WHERE photo_id = ?", (photo_id,))
        photo_dict["issues"] = [dict(row) for row in cursor.fetchall()]

        return photo_dict

    def search_photos(self, project_id: int = None, room_type: str = None,
                      trade: str = None, has_issues: bool = None,
                      tag_value: str = None) -> List[Dict]:
        """Search photos by various criteria."""
        cursor = self.conn.cursor()

        query = "SELECT DISTINCT p.* FROM photos p"
        conditions = []
        params = []

        if tag_value:
            query += " LEFT JOIN tags t ON p.id = t.photo_id"
            conditions.append("t.value LIKE ?")
            params.append(f"%{tag_value}%")

        if project_id:
            conditions.append("p.project_id = ?")
            params.append(project_id)

        if room_type:
            conditions.append("p.room_type = ?")
            params.append(room_type)

        if trade:
            conditions.append("p.trade = ?")
            params.append(trade)

        if has_issues is not None:
            if has_issues:
                conditions.append("p.issue_count > 0")
            else:
                conditions.append("p.issue_count = 0")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY p.created_at DESC"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_project_stats(self, project_id: int) -> Dict:
        """Get statistics for a project."""
        cursor = self.conn.cursor()

        stats = {"project_id": project_id}

        # Photo count
        cursor.execute(
            "SELECT COUNT(*) FROM photos WHERE project_id = ?",
            (project_id,)
        )
        stats["photo_count"] = cursor.fetchone()[0]

        # Issue count
        cursor.execute("""
            SELECT COUNT(*) FROM issues i
            JOIN photos p ON i.photo_id = p.id
            WHERE p.project_id = ?
        """, (project_id,))
        stats["total_issues"] = cursor.fetchone()[0]

        # Unresolved issues
        cursor.execute("""
            SELECT COUNT(*) FROM issues i
            JOIN photos p ON i.photo_id = p.id
            WHERE p.project_id = ? AND i.resolved = 0
        """, (project_id,))
        stats["open_issues"] = cursor.fetchone()[0]

        # Photos by room
        cursor.execute("""
            SELECT room_type, COUNT(*) as count
            FROM photos WHERE project_id = ? AND room_type IS NOT NULL
            GROUP BY room_type
        """, (project_id,))
        stats["by_room"] = {row[0]: row[1] for row in cursor.fetchall()}

        # Photos by trade
        cursor.execute("""
            SELECT trade, COUNT(*) as count
            FROM photos WHERE project_id = ? AND trade IS NOT NULL
            GROUP BY trade
        """, (project_id,))
        stats["by_trade"] = {row[0]: row[1] for row in cursor.fetchall()}

        return stats

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
