#!/usr/bin/env python3
"""
Claude System Initialization
Master startup script that initializes the full intelligent system.

This is the SINGLE entry point for Claude Code sessions.
Run at the start of every session for full system awareness.

Usage:
    python claude_init.py           # Full startup
    python claude_init.py quick     # Quick status only
    python claude_init.py refresh   # Refresh system state
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Set working directory
BASE_DIR = Path(r"D:\_CLAUDE-TOOLS\system-bridge")
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))

# Import subsystems
from claude_brain import ClaudeBrain
from file_indexer import FileIndex
from project_intelligence import ProjectIntelligence


def full_startup():
    """Full system startup with all components."""
    print("=" * 70)
    print(" CLAUDE INTELLIGENT SYSTEM - FULL INITIALIZATION")
    print("=" * 70)
    print(f" Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. Check file index freshness
    indexer = FileIndex()
    stats = indexer.get_stats()

    if stats["total_files"] == 0:
        print("## FILE INDEX")
        print("   [!] No files indexed - building index...")
        indexer.build_index()
        stats = indexer.get_stats()

    print(f"## FILE INDEX")
    print(f"   Total files: {stats['total_files']}")
    print(f"   Revit models: {stats['by_extension'].get('.rvt', 0)}")
    print(f"   Revit families: {stats['by_extension'].get('.rfa', 0)}")
    print(f"   PDFs: {stats['by_extension'].get('.pdf', 0)}")
    print(f"   Last indexed: {stats.get('last_indexed', 'Never')[:19]}")
    print()

    # 2. Run the brain startup
    brain = ClaudeBrain()
    print(brain.startup_sequence())

    # 3. Show quick commands
    print()
    print("## QUICK COMMANDS")
    print("   claude_cmd.py status     - Full status")
    print("   claude_cmd.py think <x>  - Process input")
    print("   claude_cmd.py voice <x>  - Parse voice")
    print("   claude_cmd.py find <x>   - Search files")
    print("   claude_cmd.py revit <x>  - Revit command")
    print()


def quick_status():
    """Quick status check."""
    print("=" * 50)
    print(" CLAUDE SYSTEM - QUICK STATUS")
    print("=" * 50)

    # Get project context
    intel = ProjectIntelligence()
    context = intel.analyze()

    print(f" Project: {context.project_name} ({context.confidence:.0%})")

    if context.mismatches:
        print()
        print(" [!!!] ALERTS:")
        for m in context.mismatches:
            print(f"    {m}")

    # File stats
    indexer = FileIndex()
    stats = indexer.get_stats()
    print()
    print(f" Files indexed: {stats['total_files']}")
    print(f" Revit models: {stats['by_extension'].get('.rvt', 0)}")

    print()
    print("=" * 50)


def refresh_state():
    """Refresh system state without full startup."""
    print("Refreshing system state...")

    # Update live state
    import subprocess
    subprocess.run(
        ['powershell.exe', '-ExecutionPolicy', 'Bypass',
         '-File', str(BASE_DIR / 'get_apps.ps1')],
        capture_output=True
    )

    # Re-run intelligence
    intel = ProjectIntelligence()
    context = intel.analyze()

    result = {
        "timestamp": datetime.now().isoformat(),
        "project": context.project_name,
        "confidence": context.confidence,
        "mismatches": context.mismatches,
        "suggestions": context.suggested_actions[:3],
    }

    print(json.dumps(result, indent=2))


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "quick":
            quick_status()
        elif cmd == "refresh":
            refresh_state()
        else:
            print(f"Unknown command: {cmd}")
            print("Use: full (default), quick, refresh")
    else:
        full_startup()


if __name__ == "__main__":
    main()
