#!/usr/bin/env python3
"""
Proactive Memory Surfacer

Surfaces relevant memories based on:
1. Current context (open apps, files, project)
2. Task keywords
3. Known correction patterns

Integrates with Claude's startup sequence and pre-flight checks.
"""

import json
import sqlite3
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Configuration
MEMORY_DB = Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db")
SYSTEM_STATE_FILE = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")


class MemorySurfacer:
    """Proactively surfaces relevant memories based on context."""

    def __init__(self):
        self.conn = None
        if MEMORY_DB.exists():
            self.conn = sqlite3.connect(str(MEMORY_DB))
            self.conn.row_factory = sqlite3.Row

    def close(self):
        if self.conn:
            self.conn.close()

    def _query(self, sql: str, params: tuple = ()) -> list:
        """Execute SQL query and return results."""
        if not self.conn:
            return []
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Query error: {e}")
            return []

    def get_system_context(self) -> dict:
        """Get current system context from system bridge."""
        try:
            if SYSTEM_STATE_FILE.exists():
                with open(SYSTEM_STATE_FILE) as f:
                    return json.load(f)
        except:
            pass
        return {}

    def detect_project_from_context(self, context: dict) -> Optional[str]:
        """Detect current project from system context."""
        # Check active window
        active_window = context.get("active_window", "")

        # Revit project detection
        if "Revit" in active_window:
            # Extract project name from title
            # Format: "Autodesk Revit 202X.X - [PROJECT NAME - View: VIEW NAME]"
            match = re.search(r'\[([^\]]+)', active_window)
            if match:
                project_name = match.group(1).split(" - ")[0]
                return project_name

        # Bluebeam document detection
        bluebeam = context.get("bluebeam", {})
        if bluebeam.get("running") and bluebeam.get("document"):
            return bluebeam["document"]

        # VS Code project detection
        for app in context.get("applications", []):
            if app.get("ProcessName") == "Code":
                title = app.get("MainWindowTitle", "")
                if " - " in title:
                    return title.split(" - ")[0]

        return None

    def get_recent_corrections(self, limit: int = 5) -> list:
        """Get most recent corrections."""
        sql = """
            SELECT id, content, summary, project, created_at
            FROM memories
            WHERE memory_type = 'error'
            AND importance >= 8
            ORDER BY created_at DESC
            LIMIT ?
        """
        return self._query(sql, (limit,))

    def get_project_corrections(self, project: str, limit: int = 5) -> list:
        """Get corrections for a specific project."""
        sql = """
            SELECT id, content, summary, project, created_at
            FROM memories
            WHERE memory_type = 'error'
            AND project LIKE ?
            ORDER BY importance DESC, created_at DESC
            LIMIT ?
        """
        return self._query(sql, (f"%{project}%", limit))

    def get_relevant_decisions(self, project: str = None, limit: int = 5) -> list:
        """Get relevant decisions that should inform current work."""
        if project:
            sql = """
                SELECT id, content, summary, project, created_at
                FROM memories
                WHERE memory_type = 'decision'
                AND project LIKE ?
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
            """
            return self._query(sql, (f"%{project}%", limit))
        else:
            sql = """
                SELECT id, content, summary, project, created_at
                FROM memories
                WHERE memory_type = 'decision'
                AND importance >= 7
                ORDER BY created_at DESC
                LIMIT ?
            """
            return self._query(sql, (limit,))

    def get_unfinished_work(self, project: str = None) -> list:
        """Get sessions with open questions or next steps."""
        if project:
            sql = """
                SELECT id, content, summary, project, created_at
                FROM memories
                WHERE memory_type IN ('context', 'outcome')
                AND content LIKE '%next_steps%' OR content LIKE '%open_questions%'
                AND project LIKE ?
                ORDER BY created_at DESC
                LIMIT 5
            """
            return self._query(sql, (f"%{project}%",))
        else:
            sql = """
                SELECT id, content, summary, project, created_at
                FROM memories
                WHERE memory_type IN ('context', 'outcome')
                AND (content LIKE '%next_steps%' OR content LIKE '%open_questions%')
                ORDER BY created_at DESC
                LIMIT 5
            """
            return self._query(sql)

    def search_keyword_corrections(self, keywords: list, limit: int = 5) -> list:
        """Search for corrections matching keywords."""
        if not keywords:
            return []

        conditions = " OR ".join([f"content LIKE ?" for _ in keywords])
        params = tuple(f"%{kw}%" for kw in keywords)

        sql = f"""
            SELECT id, content, summary, project, importance, created_at
            FROM memories
            WHERE memory_type = 'error'
            AND ({conditions})
            ORDER BY importance DESC, created_at DESC
            LIMIT ?
        """
        return self._query(sql, params + (limit,))

    def surface_for_context(self, context: dict = None) -> dict:
        """
        Main method: Surface all relevant memories for current context.

        Returns a structured summary of what the user/Claude should know.
        """
        if context is None:
            context = self.get_system_context()

        result = {
            "timestamp": datetime.now().isoformat(),
            "detected_project": None,
            "critical_corrections": [],
            "relevant_decisions": [],
            "unfinished_work": [],
            "context_warnings": []
        }

        # Detect project
        project = self.detect_project_from_context(context)
        result["detected_project"] = project

        # Get corrections (both recent and project-specific)
        recent_corrections = self.get_recent_corrections(3)
        result["critical_corrections"].extend(recent_corrections)

        if project:
            project_corrections = self.get_project_corrections(project, 3)
            # Add project-specific corrections that aren't duplicates
            existing_ids = {c["id"] for c in result["critical_corrections"]}
            for c in project_corrections:
                if c["id"] not in existing_ids:
                    result["critical_corrections"].append(c)

        # Get relevant decisions
        result["relevant_decisions"] = self.get_relevant_decisions(project, 3)

        # Get unfinished work
        result["unfinished_work"] = self.get_unfinished_work(project)

        # Add context-specific warnings
        if "Revit" in context.get("active_window", ""):
            # Revit-specific warnings
            wall_corrections = self.search_keyword_corrections(["wall", "DXF", "coordinate"])
            if len(wall_corrections) > 3:
                result["context_warnings"].append({
                    "type": "repeated_issue",
                    "message": f"Found {len(wall_corrections)} corrections about wall/coordinate issues",
                    "action": "Review corrections before placing walls"
                })

        return result

    def format_for_display(self, surfaced: dict) -> str:
        """Format surfaced memories for display to user."""
        lines = ["# Proactive Context Load", ""]

        if surfaced.get("detected_project"):
            lines.append(f"**Detected Project:** {surfaced['detected_project']}")
            lines.append("")

        if surfaced.get("critical_corrections"):
            lines.append("## ⚠️ Critical Corrections to Remember")
            for c in surfaced["critical_corrections"][:5]:
                summary = c.get("summary") or (c.get("content", "")[:100] + "...")
                lines.append(f"- [{c.get('project', 'general')}] {summary}")
            lines.append("")

        if surfaced.get("context_warnings"):
            lines.append("## 🚨 Context Warnings")
            for w in surfaced["context_warnings"]:
                lines.append(f"- **{w['type']}**: {w['message']}")
                lines.append(f"  → {w['action']}")
            lines.append("")

        if surfaced.get("relevant_decisions"):
            lines.append("## 📋 Recent Decisions")
            for d in surfaced["relevant_decisions"][:3]:
                summary = d.get("summary") or (d.get("content", "")[:80] + "...")
                lines.append(f"- {summary}")
            lines.append("")

        if surfaced.get("unfinished_work"):
            lines.append("## 📌 Unfinished Work")
            for u in surfaced["unfinished_work"][:3]:
                project = u.get("project", "unknown")
                lines.append(f"- [{project}] Check for open items")
            lines.append("")

        return "\n".join(lines)


def main():
    """CLI entry point."""
    import sys

    surfacer = MemorySurfacer()

    try:
        if len(sys.argv) > 1:
            if sys.argv[1] == "--json":
                # Output as JSON
                result = surfacer.surface_for_context()
                print(json.dumps(result, indent=2, default=str))
            elif sys.argv[1] == "--keywords":
                # Search by keywords
                keywords = sys.argv[2:]
                corrections = surfacer.search_keyword_corrections(keywords)
                print(json.dumps(corrections, indent=2, default=str))
            else:
                print("Usage:")
                print("  memory_surfacer.py          # Display formatted output")
                print("  memory_surfacer.py --json   # Output as JSON")
                print("  memory_surfacer.py --keywords wall dxf  # Search by keywords")
        else:
            # Default: formatted output
            result = surfacer.surface_for_context()
            print(surfacer.format_for_display(result))
    finally:
        surfacer.close()


if __name__ == "__main__":
    main()
