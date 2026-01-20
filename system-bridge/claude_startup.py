#!/usr/bin/env python3
r"""
Claude Code Startup Script
Run this at the start of every Claude Code session to:
1. Load system state (open apps, monitors, Revit status)
2. Run Project Intelligence Engine (detect project, mismatches)
3. Load relevant memories from database
4. Load corrections (highest priority)
5. Show unfinished work and suggested actions

Usage from WSL:
  powershell.exe -Command "cd D:\_CLAUDE-TOOLS\system-bridge; python claude_startup.py"

Usage from Windows:
  python D:\_CLAUDE-TOOLS\system-bridge\claude_startup.py
"""

import json
import sqlite3
import subprocess
import os
from datetime import datetime
from pathlib import Path

# Paths
MEMORY_DB = Path(r"D:\_CLAUDE-TOOLS\claude-memory-server\data\memories.db")

def get_open_applications():
    """Get all open windows with titles."""
    ps_cmd = '''
    $apps = Get-Process | Where-Object {$_.MainWindowTitle -ne ""} |
    Select-Object ProcessName, MainWindowTitle
    $apps | ForEach-Object { "$($_.ProcessName): $($_.MainWindowTitle)" }
    '''
    try:
        result = subprocess.run(
            ['powershell', '-Command', ps_cmd],
            capture_output=True, text=True, timeout=10
        )
        apps = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        return apps
    except Exception as e:
        return [f"Error: {e}"]

def get_monitor_count():
    """Get number of monitors."""
    ps_cmd = 'Get-CimInstance -Namespace root\\wmi -ClassName WmiMonitorBasicDisplayParams | Measure-Object | Select-Object -ExpandProperty Count'
    try:
        result = subprocess.run(
            ['powershell', '-Command', ps_cmd],
            capture_output=True, text=True, timeout=10
        )
        return int(result.stdout.strip())
    except:
        return 0

def get_revit_status():
    """Get Revit MCP status."""
    try:
        import win32file
        PIPE_NAME = r'\\.\pipe\RevitMCPBridge2026'
        handle = win32file.CreateFile(
            PIPE_NAME,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0, None, win32file.OPEN_EXISTING, 0, None
        )
        request = {"method": "getActiveView", "params": {}}
        message = json.dumps(request) + '\n'
        win32file.WriteFile(handle, message.encode('utf-8'))
        result, response = win32file.ReadFile(handle, 64 * 1024)
        win32file.CloseHandle(handle)
        data = json.loads(response.decode('utf-8').strip())
        if data.get('success'):
            return f"Connected - {data.get('viewName', 'Unknown')} ({data.get('viewType', '')})"
        return "Connected but no active view"
    except Exception as e:
        return f"Not connected: {e}"

def get_corrections():
    """Get corrections from memory database."""
    if not MEMORY_DB.exists():
        return []

    try:
        conn = sqlite3.connect(MEMORY_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT content, project, created_at
            FROM memories
            WHERE memory_type = 'error' AND tags LIKE '%correction%'
            ORDER BY created_at DESC
            LIMIT 5
        """)

        corrections = []
        for row in cursor.fetchall():
            content = row["content"]
            # Extract just the correct approach
            if '### Correct Approach:' in content:
                approach = content.split('### Correct Approach:')[1]
                approach = approach.split('**Category**')[0].strip()
                corrections.append({
                    "project": row["project"],
                    "approach": approach[:300]
                })

        conn.close()
        return corrections
    except Exception as e:
        return []

def get_unfinished_work():
    """Get sessions with pending next steps."""
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
            LIMIT 3
        """)

        unfinished = []
        for row in cursor.fetchall():
            content = row["content"]
            if '### Next Steps' in content:
                steps_section = content.split('### Next Steps')[1]
                steps = [s.strip() for s in steps_section.split('\n') if s.strip().startswith('-')]
                if steps:
                    unfinished.append({
                        "project": row["project"],
                        "date": row["created_at"][:10],
                        "next_steps": steps[:3]
                    })

        conn.close()
        return unfinished
    except Exception as e:
        return []

def get_projects():
    """Get known projects."""
    if not MEMORY_DB.exists():
        return []

    try:
        conn = sqlite3.connect(MEMORY_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.name, p.status, COUNT(m.id) as memories
            FROM projects p
            LEFT JOIN memories m ON p.name = m.project
            GROUP BY p.name
            ORDER BY p.last_accessed DESC
            LIMIT 7
        """)

        projects = []
        for row in cursor.fetchall():
            projects.append({
                "name": row["name"],
                "status": row["status"],
                "memories": row["memories"]
            })

        conn.close()
        return projects
    except Exception as e:
        return []

def get_memory_stats():
    """Get memory statistics."""
    if not MEMORY_DB.exists():
        return None

    try:
        conn = sqlite3.connect(MEMORY_DB)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM projects")
        projects = cursor.fetchone()[0]

        conn.close()
        return {"total": total, "projects": projects}
    except:
        return None

def main():
    print("=" * 60)
    print(" CLAUDE CODE STARTUP - SYSTEM STATE LOADED")
    print("=" * 60)
    print(f" Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Monitors
    monitors = get_monitor_count()
    print(f"## HARDWARE")
    print(f"   Monitors: {monitors}")
    print()

    # Revit Status
    print(f"## REVIT MCP")
    revit = get_revit_status()
    print(f"   Status: {revit}")
    print()

    # Memory Stats
    stats = get_memory_stats()
    if stats:
        print(f"## MEMORY DATABASE")
        print(f"   Total memories: {stats['total']}")
        print(f"   Projects: {stats['projects']}")
        print()

    # Open Applications
    print(f"## OPEN APPLICATIONS")
    apps = get_open_applications()
    for app in apps[:15]:
        print(f"   - {app}")
    if len(apps) > 15:
        print(f"   ... and {len(apps) - 15} more")
    print()

    # Corrections (HIGH PRIORITY)
    corrections = get_corrections()
    if corrections:
        print(f"## [!] CORRECTIONS TO REMEMBER")
        for corr in corrections:
            print(f"   [{corr['project'] or 'General'}]")
            print(f"   > {corr['approach'][:200]}...")
            print()

    # Unfinished Work
    unfinished = get_unfinished_work()
    if unfinished:
        print(f"## [TODO] UNFINISHED WORK")
        for item in unfinished:
            print(f"   {item['project']} ({item['date']})")
            for step in item['next_steps']:
                print(f"      {step}")
            print()

    # Projects
    projects = get_projects()
    if projects:
        print(f"## KNOWN PROJECTS")
        for proj in projects:
            print(f"   - {proj['name']} [{proj['status']}] ({proj['memories']} memories)")
        print()

    # Run Project Intelligence
    try:
        from project_intelligence import ProjectIntelligence
        intel = ProjectIntelligence()
        context = intel.analyze()

        print("## PROJECT INTELLIGENCE")
        print(f"   Detected: {context.project_name} ({context.confidence:.0%} confidence)")
        print(f"   Sources: {', '.join(context.sources[:3])}")

        if context.mismatches:
            print()
            print("## [!!!] MISMATCH ALERT")
            for m in context.mismatches:
                print(f"   {m}")

        if context.suggested_actions:
            print()
            print("## SUGGESTED ACTIONS")
            for action in context.suggested_actions[:3]:
                print(f"   - {action}")
        print()
    except Exception as e:
        print(f"## PROJECT INTELLIGENCE: Error - {e}")
        print()

    print("=" * 60)
    print(" Ready to work. What would you like to do?")
    print("=" * 60)

if __name__ == "__main__":
    main()
