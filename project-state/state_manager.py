#!/usr/bin/env python3
"""
Project State Manager

Tracks workflow state across sessions for autonomous continuity.
Each project has a state file that persists:
- Current pipeline and phase
- Checkpoint status
- Last actions and next steps
- Session history
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

# State files location
STATE_DIR = Path("/mnt/d/_CLAUDE-TOOLS/project-state/projects")
STATE_DIR.mkdir(parents=True, exist_ok=True)

# System state file for cross-project tracking
SYSTEM_STATE_FILE = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")


def slugify(name: str) -> str:
    """Convert project name to safe filename."""
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[\s_-]+', '-', slug)
    return slug.strip('-')[:50]


def get_state_path(project_name: str) -> Path:
    """Get state file path for a project."""
    return STATE_DIR / f"{slugify(project_name)}.json"


def create_initial_state(project_name: str, project_number: str = "",
                         project_path: str = "") -> Dict:
    """Create initial state structure for a new project."""
    return {
        "schema_version": 1,
        "project": {
            "name": project_name,
            "number": project_number,
            "path": project_path,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat()
        },
        "workflow": {
            "current_pipeline": None,  # e.g., "cd-set-assembly"
            "current_phase": None,     # e.g., "Phase 3 - Detail Sheet Layout"
            "phase_number": 0,
            "started_at": None,
            "status": "idle"           # idle, in_progress, paused, completed
        },
        "checkpoints": {
            "passed": [],              # List of passed checkpoint names
            "current": None,           # Current checkpoint waiting for approval
            "failed": []               # Checkpoints that failed (with reasons)
        },
        "last_session": {
            "date": None,
            "duration_minutes": 0,
            "actions_completed": [],
            "summary": None
        },
        "next_actions": [],            # Queue of next actions to take
        "context": {
            "active_sheet": None,
            "active_view": None,
            "elements_created": [],
            "elements_modified": [],
            "pending_validation": []
        },
        "notes": [],                   # Free-form notes
        "history": []                  # Session history log
    }


def load_state(project_name: str) -> Optional[Dict]:
    """Load state for a project. Returns None if no state exists."""
    state_path = get_state_path(project_name)
    if state_path.exists():
        try:
            with open(state_path) as f:
                state = json.load(f)
                # Update last accessed
                state["project"]["last_accessed"] = datetime.now().isoformat()
                return state
        except Exception as e:
            print(f"Error loading state: {e}")
            return None
    return None


def save_state(state: Dict) -> bool:
    """Save state to file."""
    try:
        project_name = state["project"]["name"]
        state_path = get_state_path(project_name)
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        return True
    except Exception as e:
        print(f"Error saving state: {e}")
        return False


def get_or_create_state(project_name: str, project_number: str = "",
                        project_path: str = "") -> Dict:
    """Get existing state or create new one."""
    state = load_state(project_name)
    if state is None:
        state = create_initial_state(project_name, project_number, project_path)
        save_state(state)
    return state


def start_pipeline(state: Dict, pipeline_name: str,
                   first_phase: str = "Phase 1") -> Dict:
    """Start a new pipeline workflow."""
    state["workflow"]["current_pipeline"] = pipeline_name
    state["workflow"]["current_phase"] = first_phase
    state["workflow"]["phase_number"] = 1
    state["workflow"]["started_at"] = datetime.now().isoformat()
    state["workflow"]["status"] = "in_progress"
    state["checkpoints"]["passed"] = []
    state["checkpoints"]["current"] = None
    state["checkpoints"]["failed"] = []

    # Log to history
    state["history"].append({
        "timestamp": datetime.now().isoformat(),
        "event": "pipeline_started",
        "details": f"Started {pipeline_name}"
    })

    save_state(state)
    return state


def advance_phase(state: Dict, next_phase: str) -> Dict:
    """Move to the next phase in the pipeline."""
    prev_phase = state["workflow"]["current_phase"]
    state["workflow"]["current_phase"] = next_phase
    state["workflow"]["phase_number"] += 1

    state["history"].append({
        "timestamp": datetime.now().isoformat(),
        "event": "phase_advanced",
        "details": f"{prev_phase} -> {next_phase}"
    })

    save_state(state)
    return state


def pass_checkpoint(state: Dict, checkpoint_name: str,
                    notes: str = "") -> Dict:
    """Mark a checkpoint as passed."""
    state["checkpoints"]["passed"].append({
        "name": checkpoint_name,
        "passed_at": datetime.now().isoformat(),
        "notes": notes
    })
    state["checkpoints"]["current"] = None

    state["history"].append({
        "timestamp": datetime.now().isoformat(),
        "event": "checkpoint_passed",
        "details": checkpoint_name
    })

    save_state(state)
    return state


def set_current_checkpoint(state: Dict, checkpoint_name: str) -> Dict:
    """Set the current checkpoint waiting for approval."""
    state["checkpoints"]["current"] = {
        "name": checkpoint_name,
        "waiting_since": datetime.now().isoformat()
    }
    state["workflow"]["status"] = "paused"

    save_state(state)
    return state


def fail_checkpoint(state: Dict, checkpoint_name: str,
                    reason: str) -> Dict:
    """Mark a checkpoint as failed."""
    state["checkpoints"]["failed"].append({
        "name": checkpoint_name,
        "failed_at": datetime.now().isoformat(),
        "reason": reason
    })
    state["checkpoints"]["current"] = None

    state["history"].append({
        "timestamp": datetime.now().isoformat(),
        "event": "checkpoint_failed",
        "details": f"{checkpoint_name}: {reason}"
    })

    save_state(state)
    return state


def complete_pipeline(state: Dict, summary: str = "") -> Dict:
    """Mark the current pipeline as completed."""
    state["workflow"]["status"] = "completed"
    state["workflow"]["completed_at"] = datetime.now().isoformat()

    state["history"].append({
        "timestamp": datetime.now().isoformat(),
        "event": "pipeline_completed",
        "details": summary or f"Completed {state['workflow']['current_pipeline']}"
    })

    save_state(state)
    return state


def add_action(state: Dict, action: str, completed: bool = False) -> Dict:
    """Add an action to tracking."""
    if completed:
        state["last_session"]["actions_completed"].append({
            "action": action,
            "completed_at": datetime.now().isoformat()
        })
    else:
        state["next_actions"].append(action)

    save_state(state)
    return state


def set_next_actions(state: Dict, actions: List[str]) -> Dict:
    """Set the queue of next actions."""
    state["next_actions"] = actions
    save_state(state)
    return state


def clear_completed_actions(state: Dict) -> Dict:
    """Clear the completed actions list (usually at session start)."""
    state["last_session"]["actions_completed"] = []
    save_state(state)
    return state


def update_context(state: Dict, **kwargs) -> Dict:
    """Update context values (active_sheet, active_view, etc.)."""
    for key, value in kwargs.items():
        if key in state["context"]:
            state["context"][key] = value
    save_state(state)
    return state


def add_note(state: Dict, note: str) -> Dict:
    """Add a free-form note."""
    state["notes"].append({
        "timestamp": datetime.now().isoformat(),
        "note": note
    })
    save_state(state)
    return state


def end_session(state: Dict, summary: str, duration_minutes: int = 0) -> Dict:
    """End a work session with summary."""
    state["last_session"]["date"] = datetime.now().isoformat()
    state["last_session"]["duration_minutes"] = duration_minutes
    state["last_session"]["summary"] = summary

    state["history"].append({
        "timestamp": datetime.now().isoformat(),
        "event": "session_ended",
        "details": summary
    })

    save_state(state)
    return state


def format_state_summary(state: Dict) -> str:
    """Format state as human-readable summary for Claude."""
    lines = [
        "=" * 50,
        "PROJECT STATE",
        "=" * 50,
        "",
        f"Project: {state['project']['name']}",
        f"Number: {state['project'].get('number', 'N/A')}",
        f"Last Accessed: {state['project']['last_accessed'][:10]}",
        ""
    ]

    # Workflow status
    wf = state["workflow"]
    if wf["current_pipeline"]:
        lines.append("WORKFLOW:")
        lines.append(f"  Pipeline: {wf['current_pipeline']}")
        lines.append(f"  Phase: {wf['current_phase']}")
        lines.append(f"  Status: {wf['status'].upper()}")
        lines.append("")
    else:
        lines.append("WORKFLOW: No active pipeline")
        lines.append("")

    # Checkpoints
    cp = state["checkpoints"]
    if cp["passed"]:
        lines.append(f"CHECKPOINTS PASSED: {len(cp['passed'])}")
        for p in cp["passed"][-3:]:  # Last 3
            lines.append(f"  [✓] {p['name']}")
    if cp["current"]:
        lines.append(f"CURRENT CHECKPOINT: {cp['current']['name']}")
        lines.append(f"  Waiting since: {cp['current']['waiting_since'][:16]}")
    lines.append("")

    # Last session
    ls = state["last_session"]
    if ls["date"]:
        lines.append("LAST SESSION:")
        lines.append(f"  Date: {ls['date'][:10]}")
        if ls["summary"]:
            lines.append(f"  Summary: {ls['summary'][:100]}")
        if ls["actions_completed"]:
            lines.append(f"  Actions: {len(ls['actions_completed'])} completed")
        lines.append("")

    # Next actions
    if state["next_actions"]:
        lines.append("NEXT ACTIONS:")
        for i, action in enumerate(state["next_actions"][:5], 1):
            lines.append(f"  {i}. {action}")
        lines.append("")

    # Context
    ctx = state["context"]
    if ctx["active_sheet"] or ctx["active_view"]:
        lines.append("CONTEXT:")
        if ctx["active_sheet"]:
            lines.append(f"  Active Sheet: {ctx['active_sheet']}")
        if ctx["active_view"]:
            lines.append(f"  Active View: {ctx['active_view']}")
        lines.append("")

    lines.append("=" * 50)

    return "\n".join(lines)


def detect_project_from_system() -> Optional[Dict]:
    """Detect current project from system state."""
    try:
        if SYSTEM_STATE_FILE.exists():
            with open(SYSTEM_STATE_FILE) as f:
                sys_state = json.load(f)

            # Check for Revit - find actual projects, not Home screen
            revit_projects = []
            for app in sys_state.get("applications", []):
                if app.get("ProcessName") == "Revit":
                    title = app.get("MainWindowTitle", "")
                    # Skip Home screens
                    if "[Home]" in title:
                        continue
                    # Parse: "Autodesk Revit 202X.X - [PROJECT NAME - View: ...]"
                    match = re.search(r'\[([^\]]+)', title)
                    if match:
                        parts = match.group(1).split(" - ")
                        project_name = parts[0]
                        # Skip if it's just "Home" or empty
                        if project_name and project_name.lower() != "home":
                            revit_projects.append({
                                "name": project_name,
                                "source": "revit",
                                "full_title": title
                            })

            # Return the first actual project found
            if revit_projects:
                return revit_projects[0]

            # Check for Bluebeam
            bb = sys_state.get("bluebeam", {})
            if bb.get("document"):
                return {
                    "name": bb["document"],
                    "source": "bluebeam"
                }
    except Exception as e:
        print(f"Error detecting project: {e}")

    return None


def list_all_projects() -> List[Dict]:
    """List all projects with state files."""
    projects = []
    for state_file in STATE_DIR.glob("*.json"):
        try:
            with open(state_file) as f:
                state = json.load(f)
                projects.append({
                    "name": state["project"]["name"],
                    "number": state["project"].get("number", ""),
                    "last_accessed": state["project"]["last_accessed"],
                    "status": state["workflow"]["status"],
                    "pipeline": state["workflow"]["current_pipeline"]
                })
        except:
            pass

    # Sort by last accessed
    projects.sort(key=lambda x: x["last_accessed"], reverse=True)
    return projects


# CLI interface
def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  state_manager.py detect          - Detect project from system")
        print("  state_manager.py load <name>     - Load project state")
        print("  state_manager.py list            - List all projects")
        print("  state_manager.py summary <name>  - Show state summary")
        return

    cmd = sys.argv[1]

    if cmd == "detect":
        project = detect_project_from_system()
        if project:
            print(f"Detected: {project['name']} (from {project['source']})")
            state = load_state(project['name'])
            if state:
                print("\nExisting state found:")
                print(format_state_summary(state))
            else:
                print("\nNo existing state. Use 'load' to create.")
        else:
            print("No project detected")

    elif cmd == "load":
        if len(sys.argv) < 3:
            print("Usage: state_manager.py load <project_name>")
            return
        name = " ".join(sys.argv[2:])
        state = get_or_create_state(name)
        print(format_state_summary(state))

    elif cmd == "list":
        projects = list_all_projects()
        if projects:
            print("Projects with state:")
            for p in projects:
                status = f"[{p['status']}]" if p['status'] != 'idle' else ""
                print(f"  - {p['name']} {status}")
        else:
            print("No projects with state files")

    elif cmd == "summary":
        if len(sys.argv) < 3:
            print("Usage: state_manager.py summary <project_name>")
            return
        name = " ".join(sys.argv[2:])
        state = load_state(name)
        if state:
            print(format_state_summary(state))
        else:
            print(f"No state found for: {name}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
