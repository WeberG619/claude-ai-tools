#!/usr/bin/env python3
"""
Claude Command Interface
Unified CLI for interacting with the intelligent system.

Commands:
    status      - Full system status report
    think       - Process natural language input
    learn       - Run learning cycle
    fix         - Suggest fixes for issues
    find        - Find Revit models and project files
    switch      - Switch project context
    voice       - Parse voice input
    revit       - Execute Revit commands
    notify      - Send notification
    help        - Show this help

Examples:
    python claude_cmd.py status
    python claude_cmd.py think "create 5 walls in revit"
    python claude_cmd.py voice "open reddit and add doors"
    python claude_cmd.py find "clematis"
    python claude_cmd.py revit getActiveView
"""

import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Add system-bridge to path
sys.path.insert(0, str(Path(__file__).parent))

from claude_brain import ClaudeBrain
from voice_intent import IntentParser, VoiceCorrections, CommandExecutor
from project_intelligence import ProjectIntelligence
from workflow_engine import ActionRecorder, AutoFixer

BASE_DIR = Path(r"D:\_CLAUDE-TOOLS\system-bridge")


def cmd_status():
    """Full system status."""
    brain = ClaudeBrain()
    print(brain.startup_sequence())


def cmd_think(text: str):
    """Process input through the brain."""
    brain = ClaudeBrain()
    result = brain.think(text)
    print(json.dumps(result, indent=2))


def cmd_voice(text: str):
    """Parse voice input with corrections."""
    # First apply corrections
    corrected, corrections = VoiceCorrections.apply_corrections(text)

    print(f"Original:  {text}")
    print(f"Corrected: {corrected}")
    if corrections:
        print(f"Changes:   {', '.join(corrections)}")
    print()

    # Parse intent
    parser = IntentParser()
    intent = parser.parse(text)

    print(f"Intent:    {intent.action}")
    print(f"Target:    {intent.target}")
    print(f"Params:    {json.dumps(intent.parameters)}")
    print(f"Confidence: {intent.confidence:.0%}")

    # Get execution plan
    if intent.confidence >= 0.7:
        executor = CommandExecutor()
        plan = executor.execute(intent)
        print()
        print("Execution Plan:")
        print(json.dumps(plan, indent=2))


def cmd_find(query: str):
    """Find Revit models and project files."""
    print(f"Searching for: {query}")
    print("=" * 50)

    # Search for .rvt files
    ps_cmd = f'''
    Get-ChildItem "D:\\*" -Recurse -Include "*.rvt" -ErrorAction SilentlyContinue |
    Where-Object {{ $_.Name -like "*{query}*" -or $_.DirectoryName -like "*{query}*" }} |
    Select-Object FullName, LastWriteTime, @{{n='SizeMB';e={{[math]::Round($_.Length/1MB,1)}}}} |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 10 |
    ConvertTo-Json
    '''

    try:
        result = subprocess.run(
            ['powershell', '-Command', ps_cmd],
            capture_output=True, text=True, timeout=30
        )

        files = json.loads(result.stdout) if result.stdout.strip() else []
        if not isinstance(files, list):
            files = [files]

        if files:
            print(f"\nFound {len(files)} Revit model(s):\n")
            for f in files:
                print(f"  [{f.get('SizeMB', '?')} MB] {f.get('FullName', 'Unknown')}")
                print(f"         Modified: {f.get('LastWriteTime', 'Unknown')}")
        else:
            print("No Revit models found matching query.")
    except Exception as e:
        print(f"Search error: {e}")

    # Also check project intelligence
    print()
    print("Project Pattern Matches:")
    intel = ProjectIntelligence()
    correlator = intel.correlator

    for proj_id, config in correlator.project_patterns.items():
        for alias in config.get("aliases", []):
            if query.lower() in alias.lower():
                print(f"  - {proj_id}: {config.get('path', 'No path')}")
                break


def cmd_revit(method: str, params: str = "{}"):
    """Execute Revit MCP command."""
    params_dict = json.loads(params)

    print(f"Calling Revit MCP: {method}")
    print(f"Parameters: {params_dict}")
    print()

    # Use mcp_call.py
    mcp_script = Path(r"D:\RevitMCPBridge2026\mcp_call.py")

    if params_dict:
        cmd = f"python {mcp_script} {method} '{json.dumps(params_dict)}'"
    else:
        cmd = f"python {mcp_script} {method}"

    try:
        result = subprocess.run(
            ['powershell', '-Command', cmd],
            capture_output=True, text=True, timeout=30
        )
        print("Response:")
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
    except Exception as e:
        print(f"Error: {e}")


def cmd_fix(issue_type: str):
    """Suggest fixes for an issue."""
    fixer = AutoFixer()

    # Build context from current state
    try:
        with open(BASE_DIR / "live_state.json") as f:
            state = json.load(f)
    except:
        state = {}

    context = {
        "revit_project": state.get("revit", {}).get("document"),
        "bluebeam_project": state.get("bluebeam", {}).get("document"),
    }

    suggestion = fixer.suggest_fix(issue_type, context)

    if suggestion:
        print(f"Issue: {suggestion.get('issue', 'Unknown')}")
        print()
        print("Fix Options:")
        for i, opt in enumerate(suggestion.get("options", []), 1):
            print(f"  {i}. {opt.get('label')}")
            print(f"     Action: {opt.get('action')}")
    else:
        print(f"No fix available for: {issue_type}")
        print("Available issue types: project_mismatch, missing_tags, unclosed_dimensions")


def cmd_switch(project: str):
    """Switch to a project context."""
    intel = ProjectIntelligence()
    correlator = intel.correlator

    # Find matching project
    project_lower = project.lower()
    matched = None

    for proj_id, config in correlator.project_patterns.items():
        if project_lower in proj_id:
            matched = (proj_id, config)
            break
        for alias in config.get("aliases", []):
            if project_lower in alias.lower():
                matched = (proj_id, config)
                break
        if matched:
            break

    if matched:
        proj_id, config = matched
        print(f"Switching to project: {proj_id}")
        print(f"Aliases: {', '.join(config.get('aliases', []))}")

        if config.get("path"):
            print(f"Path: {config['path']}")
            # Open in explorer
            subprocess.run(['powershell', '-Command', f'explorer "{config["path"]}"'], capture_output=True)

        if config.get("revit_models"):
            print(f"Known Revit models: {', '.join(config['revit_models'])}")
    else:
        print(f"Project not found: {project}")
        print()
        print("Available projects:")
        for proj_id in correlator.project_patterns.keys():
            print(f"  - {proj_id}")


def cmd_notify(message: str, title: str = "Claude Code"):
    """Send a notification."""
    from notification_system import NotificationEngine, Notification, Priority

    engine = NotificationEngine()
    notif = Notification(
        title=title,
        message=message,
        priority=Priority.MEDIUM,
        category="info",
        timestamp=datetime.now().isoformat()
    )

    engine.send_windows_toast(notif)
    print(f"Notification sent: {title}")


def cmd_learn():
    """Run learning cycle."""
    brain = ClaudeBrain()
    learnings = brain.learn()
    print(json.dumps(learnings, indent=2))


def cmd_help():
    """Show help."""
    print(__doc__)


def main():
    if len(sys.argv) < 2:
        cmd_help()
        return

    command = sys.argv[1].lower()
    args = sys.argv[2:]

    commands = {
        "status": (cmd_status, 0),
        "think": (cmd_think, 1),
        "voice": (cmd_voice, 1),
        "find": (cmd_find, 1),
        "revit": (cmd_revit, 1),  # method required, params optional
        "fix": (cmd_fix, 1),
        "switch": (cmd_switch, 1),
        "notify": (cmd_notify, 1),
        "learn": (cmd_learn, 0),
        "help": (cmd_help, 0),
    }

    if command in commands:
        func, min_args = commands[command]
        if len(args) < min_args:
            print(f"Error: '{command}' requires at least {min_args} argument(s)")
            return

        if min_args == 0:
            func()
        elif min_args == 1:
            if command == "revit" and len(args) > 1:
                func(args[0], args[1])
            else:
                func(args[0])
        else:
            func(*args[:min_args])
    else:
        print(f"Unknown command: {command}")
        print("Use 'help' for available commands.")


if __name__ == "__main__":
    main()
