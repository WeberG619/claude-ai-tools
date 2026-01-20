#!/usr/bin/env python3
"""
File Indexer for Claude System
Builds and maintains an index of important files (RVT, PDF, DWG, etc.)
for instant lookups without slow disk scanning.

Usage:
    python file_indexer.py build     # Build/rebuild full index
    python file_indexer.py update    # Update changed files only
    python file_indexer.py find <query>  # Search index
    python file_indexer.py stats     # Show index stats
"""

import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

BASE_DIR = Path(r"D:\_CLAUDE-TOOLS\system-bridge")
INDEX_DB = BASE_DIR / "file_index.db"

# Directories to index
INDEX_PATHS = [
    r"D:\001 - PROJECTS",
    r"D:\RevitMCPBridge2026",
    r"D:\BIM_Ops_Studio",
    r"D:\014-REVIT-TOOLS",
    r"D:\_REVIT-PROJECTS",
]

# File extensions to index
INDEX_EXTENSIONS = [".rvt", ".rfa", ".pdf", ".dwg", ".dxf", ".ifc", ".nwc"]


class FileIndex:
    """File index database manager."""

    def __init__(self):
        self.db_path = INDEX_DB
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                extension TEXT NOT NULL,
                size_bytes INTEGER,
                modified TEXT,
                directory TEXT,
                project TEXT,
                indexed_at TEXT
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_name ON files(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_ext ON files(extension)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_project ON files(project)")

        conn.commit()
        conn.close()

    def build_index(self, paths: List[str] = None) -> Dict:
        """Build full file index from scratch using PowerShell script."""
        paths = paths or INDEX_PATHS
        stats = {"scanned": 0, "indexed": 0, "errors": 0}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Clear existing index
        cursor.execute("DELETE FROM files")

        for base_path in paths:
            print(f"Indexing: {base_path}")

            # Use PowerShell script for file scanning
            ps_script = BASE_DIR / "scan_files.ps1"
            json_output = BASE_DIR / "scanned_files.json"

            try:
                result = subprocess.run(
                    ['powershell.exe', '-ExecutionPolicy', 'Bypass',
                     '-File', str(ps_script),
                     '-BasePath', base_path,
                     '-OutputFile', str(json_output)],
                    capture_output=True, text=True, timeout=180
                )

                # Read the JSON output file
                if json_output.exists():
                    with open(json_output, 'r', encoding='utf-8-sig') as f:
                        content = f.read()
                        if content.strip():
                            files = json.loads(content)
                            if not isinstance(files, list):
                                files = [files] if files else []

                            for f in files:
                                stats["scanned"] += 1
                                try:
                                    path = f.get("FullName", "")
                                    name = f.get("Name", "")
                                    ext = f.get("Extension", "").lower()
                                    size = f.get("Length", 0)
                                    modified = f.get("LastWriteTime", "")
                                    directory = f.get("Directory", str(Path(path).parent))

                                    # Detect project from path
                                    project = self._detect_project(path)

                                    cursor.execute("""
                                        INSERT OR REPLACE INTO files
                                        (path, name, extension, size_bytes, modified, directory, project, indexed_at)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (
                                        path, name, ext, size, modified, directory,
                                        project, datetime.now().isoformat()
                                    ))

                                    stats["indexed"] += 1

                                except Exception as e:
                                    stats["errors"] += 1

                            print(f"  Found {len(files)} files")

            except subprocess.TimeoutExpired:
                print(f"  Timeout scanning {base_path}")
                stats["errors"] += 1
            except Exception as e:
                print(f"  Error: {e}")
                stats["errors"] += 1

        conn.commit()
        conn.close()

        print(f"\nIndex built: {stats['indexed']} files indexed")
        return stats

    def _detect_project(self, path: str) -> Optional[str]:
        """Detect project name from file path."""
        path_lower = path.lower()

        # Project detection patterns
        patterns = [
            ("ap builder", "ap_builder"),
            ("avon park", "ap_builder"),
            ("south golf cove", "south_golf_cove"),
            ("sgc", "south_golf_cove"),
            ("clematis", "512_clematis"),
            ("pierr torres", "pierr_torres"),
            ("church project", "church_project"),
            ("dania", "dania_beach"),
            ("west park", "west_park"),
            ("lehigh acres", "lehigh_acres"),
            ("north lauderdale", "north_lauderdale"),
            ("revitmcpbridge", "revitmcpbridge"),
            ("bim_ops", "bim_ops_studio"),
        ]

        for pattern, project in patterns:
            if pattern in path_lower:
                return project

        return None

    def search(self, query: str, extension: str = None, limit: int = 20) -> List[Dict]:
        """Search the index."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query_pattern = f"%{query}%"

        if extension:
            cursor.execute("""
                SELECT * FROM files
                WHERE (name LIKE ? OR path LIKE ? OR project LIKE ?)
                AND extension = ?
                ORDER BY modified DESC
                LIMIT ?
            """, (query_pattern, query_pattern, query_pattern, extension, limit))
        else:
            cursor.execute("""
                SELECT * FROM files
                WHERE name LIKE ? OR path LIKE ? OR project LIKE ?
                ORDER BY modified DESC
                LIMIT ?
            """, (query_pattern, query_pattern, query_pattern, limit))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def find_revit_models(self, query: str = None) -> List[Dict]:
        """Find Revit models (.rvt files)."""
        if query:
            return self.search(query, extension=".rvt")
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM files
                WHERE extension = '.rvt'
                ORDER BY modified DESC
                LIMIT 50
            """)
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results

    def find_families(self, query: str = None) -> List[Dict]:
        """Find Revit family files (.rfa)."""
        return self.search(query or "", extension=".rfa")

    def get_stats(self) -> Dict:
        """Get index statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM files")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT extension, COUNT(*) as cnt FROM files GROUP BY extension ORDER BY cnt DESC")
        by_extension = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("SELECT project, COUNT(*) as cnt FROM files WHERE project IS NOT NULL GROUP BY project ORDER BY cnt DESC")
        by_project = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("SELECT MAX(indexed_at) FROM files")
        last_indexed = cursor.fetchone()[0]

        conn.close()

        return {
            "total_files": total,
            "by_extension": by_extension,
            "by_project": by_project,
            "last_indexed": last_indexed,
        }

    def get_recent_models(self, limit: int = 10) -> List[Dict]:
        """Get recently modified Revit models."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM files
            WHERE extension = '.rvt'
            ORDER BY modified DESC
            LIMIT ?
        """, (limit,))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results


def format_size(bytes_val: int) -> str:
    """Format bytes to human readable."""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val/1024:.1f} KB"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val/(1024*1024):.1f} MB"
    else:
        return f"{bytes_val/(1024*1024*1024):.2f} GB"


def main():
    indexer = FileIndex()

    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "build":
        print("Building file index...")
        stats = indexer.build_index()
        print(json.dumps(stats, indent=2))

    elif cmd == "update":
        # For now, same as build - could be optimized later
        print("Updating file index...")
        stats = indexer.build_index()
        print(json.dumps(stats, indent=2))

    elif cmd == "find" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        results = indexer.search(query)

        print(f"Search results for: {query}")
        print("=" * 60)

        if results:
            for r in results:
                size = format_size(r.get("size_bytes", 0))
                print(f"\n[{r.get('extension', '?')}] {r.get('name')}")
                print(f"     Size: {size}")
                print(f"     Path: {r.get('path')}")
                print(f"     Project: {r.get('project', 'Unknown')}")
        else:
            print("No results found.")

    elif cmd == "rvt":
        query = sys.argv[2] if len(sys.argv) > 2 else None
        results = indexer.find_revit_models(query)

        print(f"Revit Models" + (f" matching '{query}':" if query else ":"))
        print("=" * 60)

        for r in results:
            size = format_size(r.get("size_bytes", 0))
            print(f"\n{r.get('name')} [{size}]")
            print(f"   Project: {r.get('project', 'Unknown')}")
            print(f"   Path: {r.get('path')}")

    elif cmd == "stats":
        stats = indexer.get_stats()
        print("File Index Statistics")
        print("=" * 40)
        print(f"Total files: {stats['total_files']}")
        print(f"Last indexed: {stats['last_indexed']}")
        print()
        print("By Extension:")
        for ext, count in stats["by_extension"].items():
            print(f"  {ext}: {count}")
        print()
        print("By Project:")
        for proj, count in stats["by_project"].items():
            print(f"  {proj}: {count}")

    elif cmd == "recent":
        results = indexer.get_recent_models()
        print("Recently Modified Revit Models:")
        print("=" * 60)
        for r in results:
            size = format_size(r.get("size_bytes", 0))
            print(f"\n{r.get('name')} [{size}]")
            print(f"   Modified: {r.get('modified', 'Unknown')}")
            print(f"   Project: {r.get('project', 'Unknown')}")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
