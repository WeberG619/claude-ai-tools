#!/usr/bin/env python3
"""
System State Bridge - Provides full system awareness to Claude Code
This runs on Windows and captures everything Claude needs to know.
"""

import json
import sqlite3
import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path

# Paths
MEMORY_DB = Path(r"D:\_CLAUDE-TOOLS\claude-memory-server\data\memories.db")
STATE_FILE = Path(r"D:\_CLAUDE-TOOLS\system-bridge\current_state.json")

def get_open_applications():
    """Get all open windows with titles."""
    ps_cmd = '''
    Get-Process | Where-Object {$_.MainWindowTitle -ne ""} |
    Select-Object ProcessName, Id, MainWindowTitle |
    ConvertTo-Json
    '''
    try:
        result = subprocess.run(
            ['powershell', '-Command', ps_cmd],
            capture_output=True, text=True, timeout=10
        )
        apps = json.loads(result.stdout) if result.stdout else []
        # Handle single result (not a list)
        if isinstance(apps, dict):
            apps = [apps]
        return apps
    except Exception as e:
        return [{"error": str(e)}]

def get_monitors():
    """Get monitor information."""
    ps_cmd = '''
    Get-CimInstance -Namespace root\\wmi -ClassName WmiMonitorBasicDisplayParams |
    Select-Object InstanceName, Active | ConvertTo-Json
    '''
    try:
        result = subprocess.run(
            ['powershell', '-Command', ps_cmd],
            capture_output=True, text=True, timeout=10
        )
        monitors = json.loads(result.stdout) if result.stdout else []
        if isinstance(monitors, dict):
            monitors = [monitors]
        return {"count": len(monitors), "details": monitors}
    except Exception as e:
        return {"count": 0, "error": str(e)}

def get_revit_status():
    """Get Revit MCP status if available."""
    try:
        import win32file
        import pywintypes

        PIPE_NAME = r'\\.\pipe\RevitMCPBridge2026'
        handle = win32file.CreateFile(
            PIPE_NAME,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0, None, win32file.OPEN_EXISTING, 0, None
        )

        # Query active view
        request = {"method": "getActiveView", "params": {}}
        message = json.dumps(request) + '\n'
        win32file.WriteFile(handle, message.encode('utf-8'))

        result, response = win32file.ReadFile(handle, 64 * 1024)
        win32file.CloseHandle(handle)

        return json.loads(response.decode('utf-8').strip())
    except Exception as e:
        return {"connected": False, "error": str(e)}

def get_recent_memories(limit=10):
    """Get recent memories from the database."""
    if not MEMORY_DB.exists():
        return []

    try:
        conn = sqlite3.connect(MEMORY_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, content, summary, project, memory_type, importance, created_at
            FROM memories
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        memories = []
        for row in cursor.fetchall():
            memories.append({
                "id": row["id"],
                "content": row["content"][:500] if row["content"] else None,
                "summary": row["summary"],
                "project": row["project"],
                "type": row["memory_type"],
                "importance": row["importance"],
                "created": row["created_at"]
            })

        conn.close()
        return memories
    except Exception as e:
        return [{"error": str(e)}]

def get_corrections(limit=5):
    """Get recent corrections (highest priority memories)."""
    if not MEMORY_DB.exists():
        return []

    try:
        conn = sqlite3.connect(MEMORY_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, content, project, created_at
            FROM memories
            WHERE memory_type = 'error' AND tags LIKE '%correction%'
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        corrections = []
        for row in cursor.fetchall():
            corrections.append({
                "id": row["id"],
                "content": row["content"],
                "project": row["project"],
                "created": row["created_at"]
            })

        conn.close()
        return corrections
    except Exception as e:
        return [{"error": str(e)}]

def get_projects():
    """Get all projects from memory database."""
    if not MEMORY_DB.exists():
        return []

    try:
        conn = sqlite3.connect(MEMORY_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.name, p.path, p.status, p.last_accessed,
                   COUNT(m.id) as memory_count
            FROM projects p
            LEFT JOIN memories m ON p.name = m.project
            GROUP BY p.name
            ORDER BY p.last_accessed DESC
        """)

        projects = []
        for row in cursor.fetchall():
            projects.append({
                "name": row["name"],
                "path": row["path"],
                "status": row["status"],
                "last_accessed": row["last_accessed"],
                "memories": row["memory_count"]
            })

        conn.close()
        return projects
    except Exception as e:
        return [{"error": str(e)}]

def get_unfinished_work():
    """Get sessions with open next steps."""
    if not MEMORY_DB.exists():
        return []

    try:
        conn = sqlite3.connect(MEMORY_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT content, project, created_at
            FROM memories
            WHERE memory_type = 'context'
            AND tags LIKE '%session-summary%'
            AND content LIKE '%### Next Steps%'
            ORDER BY created_at DESC
            LIMIT 5
        """)

        unfinished = []
        for row in cursor.fetchall():
            content = row["content"]
            next_steps = []
            if '### Next Steps' in content:
                steps_section = content.split('### Next Steps')[1]
                next_steps = [s.strip() for s in steps_section.split('\n') if s.strip().startswith('-')]

            unfinished.append({
                "project": row["project"],
                "created": row["created_at"],
                "next_steps": next_steps[:5]
            })

        conn.close()
        return unfinished
    except Exception as e:
        return [{"error": str(e)}]

def build_system_state():
    """Build complete system state."""
    state = {
        "timestamp": datetime.now().isoformat(),
        "applications": get_open_applications(),
        "monitors": get_monitors(),
        "revit": get_revit_status(),
        "memory": {
            "recent": get_recent_memories(10),
            "corrections": get_corrections(5),
            "projects": get_projects(),
            "unfinished": get_unfinished_work()
        }
    }
    return state

def save_state():
    """Build and save system state to file."""
    state = build_system_state()

    # Ensure directory exists
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

    return state

def store_memory(content, project=None, memory_type="context", importance=5, tags=None):
    """Store a new memory in the database."""
    if not MEMORY_DB.exists():
        return {"error": "Memory database not found"}

    try:
        conn = sqlite3.connect(MEMORY_DB)
        cursor = conn.cursor()

        tags_json = json.dumps(tags) if tags else None
        summary = content[:200] + "..." if len(content) > 200 else content

        cursor.execute("""
            INSERT INTO memories (content, summary, project, tags, importance, memory_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (content, summary, project, tags_json, importance, memory_type))

        memory_id = cursor.lastrowid

        # Update project last_accessed
        if project:
            cursor.execute("""
                INSERT INTO projects (name, last_accessed)
                VALUES (?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET last_accessed = CURRENT_TIMESTAMP
            """, (project,))

        conn.commit()
        conn.close()

        return {"success": True, "memory_id": memory_id}
    except Exception as e:
        return {"error": str(e)}

def store_correction(what_wrong, correct_approach, project=None, category=None):
    """Store a correction (highest priority memory)."""
    content = f"""## Correction Record

### What Was Wrong:
{what_wrong}

### Correct Approach:
{correct_approach}

**Category**: {category or 'general'}
"""
    tags = ["correction", "high-priority"]
    if category:
        tags.append(category)

    return store_memory(content, project, "error", 10, tags)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "state":
            state = save_state()
            print(json.dumps(state, indent=2))

        elif cmd == "apps":
            print(json.dumps(get_open_applications(), indent=2))

        elif cmd == "revit":
            print(json.dumps(get_revit_status(), indent=2))

        elif cmd == "memories":
            print(json.dumps(get_recent_memories(20), indent=2))

        elif cmd == "corrections":
            print(json.dumps(get_corrections(10), indent=2))

        elif cmd == "projects":
            print(json.dumps(get_projects(), indent=2))

        elif cmd == "unfinished":
            print(json.dumps(get_unfinished_work(), indent=2))

        elif cmd == "store":
            if len(sys.argv) >= 3:
                content = sys.argv[2]
                project = sys.argv[3] if len(sys.argv) > 3 else None
                result = store_memory(content, project)
                print(json.dumps(result))
            else:
                print('{"error": "Usage: system_state.py store <content> [project]"}')

        else:
            print(f'{{"error": "Unknown command: {cmd}"}}')
    else:
        # Default: build and save state, then print
        state = save_state()
        print(json.dumps(state, indent=2))
