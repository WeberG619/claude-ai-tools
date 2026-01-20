#!/usr/bin/env python3
"""
Project Database - Central Project Tracking System

Tracks all architecture projects with:
- Project info (name, address, client, status)
- Site data links (JSON files, reports)
- Revit file associations
- Document tracking
- Timeline/milestones

Uses SQLite for portability - no server needed.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


# Default database location
DEFAULT_DB_PATH = Path(__file__).parent / "projects.db"

# Project status options
PROJECT_STATUSES = [
    "prospect",      # Initial inquiry
    "proposal",      # Proposal stage
    "contracted",    # Contract signed
    "sd",            # Schematic Design
    "dd",            # Design Development
    "cd",            # Construction Documents
    "permit",        # Permit submission
    "permit_review", # Under permit review
    "permitted",     # Permit approved
    "bidding",       # Bidding/GC selection
    "construction",  # Under construction
    "co",            # Certificate of Occupancy
    "completed",     # Project complete
    "on_hold",       # On hold
    "cancelled"      # Cancelled
]

# Document types
DOCUMENT_TYPES = [
    "site_analysis",
    "zoning_analysis",
    "code_analysis",
    "soil_report",
    "survey",
    "revit_model",
    "permit_drawings",
    "specifications",
    "contract",
    "proposal",
    "correspondence",
    "photo",
    "other"
]


class ProjectDatabase:
    """Central project tracking database"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DEFAULT_DB_PATH)
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_number TEXT UNIQUE,
                name TEXT NOT NULL,
                address TEXT,
                city TEXT,
                state TEXT DEFAULT 'FL',
                zip_code TEXT,
                county TEXT,

                client_name TEXT,
                client_email TEXT,
                client_phone TEXT,

                project_type TEXT,
                building_type TEXT,
                scope TEXT,

                status TEXT DEFAULT 'prospect',
                phase TEXT,

                latitude REAL,
                longitude REAL,

                site_data_json TEXT,
                zoning_data_json TEXT,

                revit_file_path TEXT,
                project_folder TEXT,

                contract_amount REAL,
                contract_date TEXT,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

                notes TEXT
            )
        """)

        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                doc_type TEXT NOT NULL,
                name TEXT NOT NULL,
                file_path TEXT,
                description TEXT,
                version TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        # Milestones table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                milestone TEXT NOT NULL,
                target_date TEXT,
                actual_date TEXT,
                status TEXT DEFAULT 'pending',
                notes TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        # Contacts table (for project team)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                name TEXT NOT NULL,
                company TEXT,
                email TEXT,
                phone TEXT,
                notes TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        # Site data history (track multiple analyses)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS site_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                analysis_date TEXT DEFAULT CURRENT_TIMESTAMP,
                data_json TEXT NOT NULL,
                report_path TEXT,
                notes TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        conn.commit()
        conn.close()

    def create_project(self,
                       name: str,
                       address: str = None,
                       client_name: str = None,
                       project_type: str = None,
                       **kwargs) -> int:
        """
        Create a new project

        Returns:
            Project ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Generate project number (YYYY-NNN format)
        year = datetime.now().year
        cursor.execute(
            "SELECT COUNT(*) FROM projects WHERE project_number LIKE ?",
            (f"{year}-%",)
        )
        count = cursor.fetchone()[0] + 1
        project_number = f"{year}-{count:03d}"

        # Build insert query
        fields = ["project_number", "name", "address", "client_name", "project_type"]
        values = [project_number, name, address, client_name, project_type]

        # Add optional fields
        optional_fields = [
            "city", "state", "zip_code", "county", "client_email", "client_phone",
            "building_type", "scope", "status", "latitude", "longitude",
            "revit_file_path", "project_folder", "notes"
        ]

        for field in optional_fields:
            if field in kwargs and kwargs[field] is not None:
                fields.append(field)
                values.append(kwargs[field])

        placeholders = ",".join(["?" for _ in fields])
        field_names = ",".join(fields)

        cursor.execute(
            f"INSERT INTO projects ({field_names}) VALUES ({placeholders})",
            values
        )

        project_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return project_id

    def get_project(self, project_id: int = None, project_number: str = None) -> Optional[Dict]:
        """Get project by ID or project number"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if project_id:
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        elif project_number:
            cursor.execute("SELECT * FROM projects WHERE project_number = ?", (project_number,))
        else:
            conn.close()
            return None

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def search_projects(self,
                        query: str = None,
                        status: str = None,
                        client: str = None,
                        city: str = None,
                        limit: int = 50) -> List[Dict]:
        """Search projects"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        sql = "SELECT * FROM projects WHERE 1=1"
        params = []

        if query:
            sql += " AND (name LIKE ? OR address LIKE ? OR project_number LIKE ? OR client_name LIKE ?)"
            q = f"%{query}%"
            params.extend([q, q, q, q])

        if status:
            sql += " AND status = ?"
            params.append(status)

        if client:
            sql += " AND client_name LIKE ?"
            params.append(f"%{client}%")

        if city:
            sql += " AND city LIKE ?"
            params.append(f"%{city}%")

        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_project(self, project_id: int, **kwargs) -> bool:
        """Update project fields"""
        if not kwargs:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build update query
        set_clauses = []
        values = []

        for field, value in kwargs.items():
            set_clauses.append(f"{field} = ?")
            values.append(value)

        # Always update timestamp
        set_clauses.append("updated_at = ?")
        values.append(datetime.now().isoformat())

        values.append(project_id)

        cursor.execute(
            f"UPDATE projects SET {', '.join(set_clauses)} WHERE id = ?",
            values
        )

        conn.commit()
        success = cursor.rowcount > 0
        conn.close()

        return success

    def update_status(self, project_id: int, status: str) -> bool:
        """Update project status"""
        if status not in PROJECT_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {PROJECT_STATUSES}")
        return self.update_project(project_id, status=status)

    def store_site_data(self, project_id: int, site_data: Dict, report_path: str = None) -> int:
        """Store site analysis data for a project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Store in site_analyses table
        cursor.execute(
            """INSERT INTO site_analyses (project_id, data_json, report_path)
               VALUES (?, ?, ?)""",
            (project_id, json.dumps(site_data), report_path)
        )

        analysis_id = cursor.lastrowid

        # Also update project with latest data
        cursor.execute(
            """UPDATE projects SET
               site_data_json = ?,
               latitude = ?,
               longitude = ?,
               updated_at = ?
               WHERE id = ?""",
            (
                json.dumps(site_data),
                site_data.get("latitude"),
                site_data.get("longitude"),
                datetime.now().isoformat(),
                project_id
            )
        )

        conn.commit()
        conn.close()

        return analysis_id

    def get_site_data(self, project_id: int, latest_only: bool = True) -> Optional[Dict]:
        """Get site data for a project"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if latest_only:
            cursor.execute(
                """SELECT * FROM site_analyses
                   WHERE project_id = ?
                   ORDER BY analysis_date DESC LIMIT 1""",
                (project_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                result = dict(row)
                result["data"] = json.loads(result["data_json"])
                return result
            return None
        else:
            cursor.execute(
                """SELECT * FROM site_analyses
                   WHERE project_id = ?
                   ORDER BY analysis_date DESC""",
                (project_id,)
            )
            rows = cursor.fetchall()
            conn.close()

            results = []
            for row in rows:
                r = dict(row)
                r["data"] = json.loads(r["data_json"])
                results.append(r)
            return results

    def add_document(self,
                     project_id: int,
                     doc_type: str,
                     name: str,
                     file_path: str = None,
                     description: str = None,
                     version: str = None) -> int:
        """Add a document to a project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO documents (project_id, doc_type, name, file_path, description, version)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (project_id, doc_type, name, file_path, description, version)
        )

        doc_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return doc_id

    def get_documents(self, project_id: int, doc_type: str = None) -> List[Dict]:
        """Get documents for a project"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if doc_type:
            cursor.execute(
                "SELECT * FROM documents WHERE project_id = ? AND doc_type = ?",
                (project_id, doc_type)
            )
        else:
            cursor.execute(
                "SELECT * FROM documents WHERE project_id = ?",
                (project_id,)
            )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def add_milestone(self,
                      project_id: int,
                      milestone: str,
                      target_date: str = None,
                      notes: str = None) -> int:
        """Add a milestone to a project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO milestones (project_id, milestone, target_date, notes)
               VALUES (?, ?, ?, ?)""",
            (project_id, milestone, target_date, notes)
        )

        milestone_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return milestone_id

    def complete_milestone(self, milestone_id: int, actual_date: str = None) -> bool:
        """Mark a milestone as complete"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        actual = actual_date or datetime.now().strftime("%Y-%m-%d")

        cursor.execute(
            "UPDATE milestones SET status = 'completed', actual_date = ? WHERE id = ?",
            (actual, milestone_id)
        )

        conn.commit()
        success = cursor.rowcount > 0
        conn.close()

        return success

    def get_milestones(self, project_id: int) -> List[Dict]:
        """Get milestones for a project"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM milestones WHERE project_id = ? ORDER BY target_date",
            (project_id,)
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def add_contact(self,
                    project_id: int,
                    role: str,
                    name: str,
                    company: str = None,
                    email: str = None,
                    phone: str = None) -> int:
        """Add a contact to a project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO contacts (project_id, role, name, company, email, phone)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (project_id, role, name, company, email, phone)
        )

        contact_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return contact_id

    def get_contacts(self, project_id: int) -> List[Dict]:
        """Get contacts for a project"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM contacts WHERE project_id = ?",
            (project_id,)
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def link_revit_file(self, project_id: int, revit_path: str) -> bool:
        """Link a Revit file to a project"""
        return self.update_project(project_id, revit_file_path=revit_path)

    def find_project_by_revit(self, revit_path: str) -> Optional[Dict]:
        """Find project by Revit file path"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Try exact match first
        cursor.execute(
            "SELECT * FROM projects WHERE revit_file_path = ?",
            (revit_path,)
        )
        row = cursor.fetchone()

        if not row:
            # Try filename match
            filename = os.path.basename(revit_path)
            cursor.execute(
                "SELECT * FROM projects WHERE revit_file_path LIKE ?",
                (f"%{filename}",)
            )
            row = cursor.fetchone()

        conn.close()

        if row:
            return dict(row)
        return None

    def find_project_by_address(self, address: str) -> Optional[Dict]:
        """Find project by address (fuzzy match)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM projects WHERE address LIKE ? ORDER BY updated_at DESC LIMIT 1",
            (f"%{address}%",)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        # Total projects
        cursor.execute("SELECT COUNT(*) FROM projects")
        stats["total_projects"] = cursor.fetchone()[0]

        # Projects by status
        cursor.execute(
            "SELECT status, COUNT(*) FROM projects GROUP BY status"
        )
        stats["by_status"] = dict(cursor.fetchall())

        # Active projects (not completed/cancelled/on_hold)
        cursor.execute(
            """SELECT COUNT(*) FROM projects
               WHERE status NOT IN ('completed', 'cancelled', 'on_hold')"""
        )
        stats["active_projects"] = cursor.fetchone()[0]

        # Projects this year
        year = datetime.now().year
        cursor.execute(
            "SELECT COUNT(*) FROM projects WHERE project_number LIKE ?",
            (f"{year}-%",)
        )
        stats["projects_this_year"] = cursor.fetchone()[0]

        # Recent projects
        cursor.execute(
            """SELECT project_number, name, status, updated_at
               FROM projects ORDER BY updated_at DESC LIMIT 5"""
        )
        stats["recent"] = [
            {"number": r[0], "name": r[1], "status": r[2], "updated": r[3]}
            for r in cursor.fetchall()
        ]

        conn.close()
        return stats

    def export_project(self, project_id: int) -> Dict:
        """Export complete project data as JSON"""
        project = self.get_project(project_id=project_id)
        if not project:
            return None

        project["documents"] = self.get_documents(project_id)
        project["milestones"] = self.get_milestones(project_id)
        project["contacts"] = self.get_contacts(project_id)
        project["site_analyses"] = self.get_site_data(project_id, latest_only=False)

        return project


def format_project_summary(project: Dict) -> str:
    """Format project as readable summary"""
    lines = [
        "=" * 60,
        f"PROJECT: {project.get('project_number', 'N/A')} - {project.get('name', 'Unnamed')}",
        "=" * 60,
        "",
        f"Status: {project.get('status', 'unknown').upper()}",
        f"Address: {project.get('address', 'N/A')}",
        f"City: {project.get('city', 'N/A')}, {project.get('state', 'FL')} {project.get('zip_code', '')}",
        "",
        f"Client: {project.get('client_name', 'N/A')}",
        f"Email: {project.get('client_email', 'N/A')}",
        f"Phone: {project.get('client_phone', 'N/A')}",
        "",
        f"Project Type: {project.get('project_type', 'N/A')}",
        f"Building Type: {project.get('building_type', 'N/A')}",
        "",
        f"Revit File: {project.get('revit_file_path', 'Not linked')}",
        f"Project Folder: {project.get('project_folder', 'Not set')}",
        "",
        f"Created: {project.get('created_at', 'N/A')}",
        f"Updated: {project.get('updated_at', 'N/A')}",
        "",
        "=" * 60,
    ]

    if project.get("notes"):
        lines.extend(["", "NOTES:", project["notes"], ""])

    return "\n".join(lines)


# Convenience functions for quick access
_default_db = None

def get_db() -> ProjectDatabase:
    """Get default database instance"""
    global _default_db
    if _default_db is None:
        _default_db = ProjectDatabase()
    return _default_db


def quick_create_project(name: str, address: str = None, client: str = None) -> int:
    """Quick project creation"""
    return get_db().create_project(name=name, address=address, client_name=client)


def quick_search(query: str) -> List[Dict]:
    """Quick project search"""
    return get_db().search_projects(query=query)


if __name__ == "__main__":
    # Demo/test
    db = ProjectDatabase()

    print("Project Database initialized!")
    print(f"Database location: {db.db_path}")

    # Show stats
    stats = db.get_dashboard_stats()
    print(f"\nDashboard Stats:")
    print(f"  Total Projects: {stats['total_projects']}")
    print(f"  Active Projects: {stats['active_projects']}")
    print(f"  Projects This Year: {stats['projects_this_year']}")

    if stats['by_status']:
        print(f"\n  By Status:")
        for status, count in stats['by_status'].items():
            print(f"    {status}: {count}")
