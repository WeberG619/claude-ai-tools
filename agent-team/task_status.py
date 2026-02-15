#!/usr/bin/env python3
"""
Task Status Manager - Tracks what agents are working on.

Updates status files that the Live Monitor reads to display current activity.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

STATUS_DIR = Path("/tmp/agent_team_status")
STATUS_DIR.mkdir(exist_ok=True)

TASK_FILE = STATUS_DIR / "current_task.json"
AGENT_STATUS_FILE = STATUS_DIR / "agents.json"
ACTIVITY_FILE = STATUS_DIR / "activity.json"


def set_current_task(task: str, project: str = None):
    """Set the current task being worked on."""
    data = {
        "task": task,
        "project": project,
        "started_at": datetime.now().isoformat(),
        "status": "in_progress"
    }
    TASK_FILE.write_text(json.dumps(data, indent=2))
    log_activity("task_started", f"Started: {task[:50]}...")


def complete_task():
    """Mark current task as complete."""
    if TASK_FILE.exists():
        data = json.loads(TASK_FILE.read_text())
        data["status"] = "complete"
        data["completed_at"] = datetime.now().isoformat()
        TASK_FILE.write_text(json.dumps(data, indent=2))
        log_activity("task_complete", f"Completed: {data['task'][:50]}...")


def set_agent_status(agent: str, status: str, message: str = None):
    """
    Update an agent's status.

    Args:
        agent: planner, researcher, builder, critic, narrator
        status: idle, thinking, speaking, working, waiting
        message: What the agent is doing
    """
    # Load existing
    agents = {}
    if AGENT_STATUS_FILE.exists():
        try:
            agents = json.loads(AGENT_STATUS_FILE.read_text())
        except:
            pass

    agents[agent] = {
        "status": status,
        "message": message,
        "updated_at": datetime.now().isoformat()
    }

    AGENT_STATUS_FILE.write_text(json.dumps(agents, indent=2))


def log_activity(activity_type: str, message: str, details: Dict = None):
    """Log an activity for the monitor to display."""
    # Load existing
    activities = []
    if ACTIVITY_FILE.exists():
        try:
            activities = json.loads(ACTIVITY_FILE.read_text())
        except:
            pass

    activities.append({
        "type": activity_type,
        "message": message,
        "details": details or {},
        "timestamp": datetime.now().isoformat(),
        "time_str": datetime.now().strftime("%H:%M:%S")
    })

    # Keep last 100
    activities = activities[-100:]

    ACTIVITY_FILE.write_text(json.dumps(activities, indent=2))


def get_current_task() -> Optional[Dict]:
    """Get the current task."""
    if TASK_FILE.exists():
        try:
            return json.loads(TASK_FILE.read_text())
        except:
            pass
    return None


def get_agent_statuses() -> Dict:
    """Get all agent statuses."""
    if AGENT_STATUS_FILE.exists():
        try:
            return json.loads(AGENT_STATUS_FILE.read_text())
        except:
            pass
    return {}


def get_activities(limit: int = 20) -> List[Dict]:
    """Get recent activities."""
    if ACTIVITY_FILE.exists():
        try:
            activities = json.loads(ACTIVITY_FILE.read_text())
            return activities[-limit:]
        except:
            pass
    return []


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python task_status.py task 'Description of task'")
        print("  python task_status.py agent planner thinking 'Analyzing requirements'")
        print("  python task_status.py complete")
        print("  python task_status.py status")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "task" and len(sys.argv) > 2:
        set_current_task(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print(f"Task set: {sys.argv[2]}")

    elif cmd == "agent" and len(sys.argv) > 3:
        agent = sys.argv[2]
        status = sys.argv[3]
        message = sys.argv[4] if len(sys.argv) > 4 else None
        set_agent_status(agent, status, message)
        print(f"Agent {agent}: {status}")

    elif cmd == "complete":
        complete_task()
        print("Task marked complete")

    elif cmd == "status":
        task = get_current_task()
        agents = get_agent_statuses()
        print(f"Task: {task}")
        print(f"Agents: {json.dumps(agents, indent=2)}")

    else:
        print("Unknown command")
