"""
Office Tools - Integrations for the Office Command Center
=========================================================
Connects agents to real tools:
- Gmail (read/send emails)
- Google Calendar (schedule/view)
- Task tracking
- Document operations
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from urllib.parse import quote

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False

# Tool paths
GMAIL_IMAP_TOOL = Path("/mnt/d/_CLAUDE-TOOLS/gmail-attachments/imap_download.py")
CALENDAR_TOOL = Path("/mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/calendar_client.py")
VOICE_TOOL = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")

# User info
USER_EMAIL = "weberg619@gmail.com"
USER_NAME = "Weber Gouin"


class GmailTool:
    """Interface to Gmail for reading and sending emails."""

    @staticmethod
    def search_emails(query: str, limit: int = 10) -> List[Dict]:
        """Search emails using IMAP."""
        try:
            result = subprocess.run(
                ["python3", str(GMAIL_IMAP_TOOL), "--search", query, "--list", "--limit", str(limit)],
                capture_output=True,
                text=True,
                timeout=30
            )
            # Parse output (simplified - actual parsing depends on tool output format)
            return {"success": True, "output": result.stdout, "query": query}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def compose_email_url(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> str:
        """Generate Gmail compose URL for opening in Chrome."""
        base = "https://mail.google.com/mail/u/0/?view=cm&fs=1"
        params = [
            f"to={quote(to)}",
            f"su={quote(subject)}",
            f"body={quote(body)}"
        ]
        if cc:
            params.append(f"cc={quote(cc)}")
        if bcc:
            params.append(f"bcc={quote(bcc)}")
        return f"{base}&{'&'.join(params)}"

    @staticmethod
    def open_compose(to: str, subject: str, body: str) -> Dict:
        """Open Gmail compose in Chrome."""
        url = GmailTool.compose_email_url(to, subject, body)
        try:
            # Use PowerShell to open Chrome on Windows
            cmd = f'Start-Process "chrome.exe" -ArgumentList "{url}"'
            if _HAS_BRIDGE:
                _ps_bridge(cmd, timeout=10)
            else:
                subprocess.run(
                    ["powershell.exe", "-Command", cmd],
                    timeout=10
                )
            return {"success": True, "action": "opened_compose", "to": to, "subject": subject}
        except Exception as e:
            return {"success": False, "error": str(e)}


class CalendarTool:
    """Interface to Google Calendar."""

    @staticmethod
    def get_today() -> Dict:
        """Get today's events."""
        try:
            result = subprocess.run(
                ["python3", str(CALENDAR_TOOL), "today"],
                capture_output=True,
                text=True,
                timeout=30
            )
            return {"success": True, "events": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_week() -> Dict:
        """Get this week's events."""
        try:
            result = subprocess.run(
                ["python3", str(CALENDAR_TOOL), "week"],
                capture_output=True,
                text=True,
                timeout=30
            )
            return {"success": True, "events": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def add_event(title: str, start: str, end: str, description: str = "") -> Dict:
        """Add a calendar event."""
        try:
            result = subprocess.run(
                ["python3", str(CALENDAR_TOOL), "add", title, start, end, description],
                capture_output=True,
                text=True,
                timeout=30
            )
            return {"success": True, "output": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def search_events(query: str) -> Dict:
        """Search calendar events."""
        try:
            result = subprocess.run(
                ["python3", str(CALENDAR_TOOL), "search", query],
                capture_output=True,
                text=True,
                timeout=30
            )
            return {"success": True, "events": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}


class TaskTracker:
    """Simple task tracking for follow-ups and action items."""

    TASKS_FILE = Path("/mnt/d/_CLAUDE-TOOLS/office-team/tasks.json")

    @classmethod
    def _load_tasks(cls) -> List[Dict]:
        """Load tasks from file."""
        if cls.TASKS_FILE.exists():
            with open(cls.TASKS_FILE, 'r') as f:
                return json.load(f)
        return []

    @classmethod
    def _save_tasks(cls, tasks: List[Dict]):
        """Save tasks to file."""
        cls.TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(cls.TASKS_FILE, 'w') as f:
            json.dump(tasks, f, indent=2)

    @classmethod
    def add_task(cls, title: str, due_date: str = None, priority: str = "normal",
                 category: str = "general", notes: str = "") -> Dict:
        """Add a new task."""
        tasks = cls._load_tasks()
        task = {
            "id": len(tasks) + 1,
            "title": title,
            "due_date": due_date,
            "priority": priority,  # high, normal, low
            "category": category,  # email, meeting, project, follow-up
            "notes": notes,
            "status": "pending",
            "created": datetime.now().isoformat(),
            "completed": None
        }
        tasks.append(task)
        cls._save_tasks(tasks)
        return {"success": True, "task": task}

    @classmethod
    def get_tasks(cls, status: str = None, category: str = None) -> List[Dict]:
        """Get tasks, optionally filtered."""
        tasks = cls._load_tasks()
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        if category:
            tasks = [t for t in tasks if t["category"] == category]
        return tasks

    @classmethod
    def get_due_today(cls) -> List[Dict]:
        """Get tasks due today."""
        today = datetime.now().strftime("%Y-%m-%d")
        tasks = cls._load_tasks()
        return [t for t in tasks if t.get("due_date") == today and t["status"] == "pending"]

    @classmethod
    def get_overdue(cls) -> List[Dict]:
        """Get overdue tasks."""
        today = datetime.now().strftime("%Y-%m-%d")
        tasks = cls._load_tasks()
        return [t for t in tasks if t.get("due_date") and t["due_date"] < today and t["status"] == "pending"]

    @classmethod
    def complete_task(cls, task_id: int) -> Dict:
        """Mark a task as complete."""
        tasks = cls._load_tasks()
        for task in tasks:
            if task["id"] == task_id:
                task["status"] = "completed"
                task["completed"] = datetime.now().isoformat()
                cls._save_tasks(tasks)
                return {"success": True, "task": task}
        return {"success": False, "error": "Task not found"}


class OfficeBridge:
    """Main bridge connecting agents to office tools."""

    def __init__(self):
        self.gmail = GmailTool()
        self.calendar = CalendarTool()
        self.tasks = TaskTracker()
        self.action_log = []

    def execute_action(self, action_type: str, params: Dict) -> Dict:
        """Execute an office action and log it."""
        result = None

        if action_type == "search_emails":
            result = self.gmail.search_emails(params.get("query", ""))
        elif action_type == "compose_email":
            result = self.gmail.open_compose(
                params.get("to", ""),
                params.get("subject", ""),
                params.get("body", "")
            )
        elif action_type == "get_calendar_today":
            result = self.calendar.get_today()
        elif action_type == "get_calendar_week":
            result = self.calendar.get_week()
        elif action_type == "add_calendar_event":
            result = self.calendar.add_event(
                params.get("title", ""),
                params.get("start", ""),
                params.get("end", ""),
                params.get("description", "")
            )
        elif action_type == "add_task":
            result = self.tasks.add_task(
                params.get("title", ""),
                params.get("due_date"),
                params.get("priority", "normal"),
                params.get("category", "general"),
                params.get("notes", "")
            )
        elif action_type == "get_tasks":
            result = {"success": True, "tasks": self.tasks.get_tasks(
                params.get("status"),
                params.get("category")
            )}
        elif action_type == "complete_task":
            result = self.tasks.complete_task(params.get("task_id"))
        else:
            result = {"success": False, "error": f"Unknown action: {action_type}"}

        # Log the action
        self.action_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action_type,
            "params": params,
            "result": result
        })

        return result

    def get_action_log(self, limit: int = 10) -> List[Dict]:
        """Get recent actions."""
        return self.action_log[-limit:]


# Quick test
if __name__ == "__main__":
    bridge = OfficeBridge()

    # Test task creation
    result = bridge.execute_action("add_task", {
        "title": "Follow up with Bruce about project timeline",
        "due_date": "2026-02-05",
        "priority": "high",
        "category": "follow-up"
    })
    print(f"Task created: {result}")

    # Test getting tasks
    tasks = bridge.execute_action("get_tasks", {"status": "pending"})
    print(f"Pending tasks: {tasks}")
