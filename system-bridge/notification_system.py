#!/usr/bin/env python3
"""
Proactive Notification System
Monitors system state and generates alerts/notifications for:
1. Project mismatches
2. Unusual patterns
3. Reminders for unfinished work
4. Suggested optimizations
5. Quality checks

Can notify via:
- Windows toast notifications
- Sound alerts
- Log file
- Console output
"""

import json
import subprocess
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

# Paths
BASE_DIR = Path(r"D:\_CLAUDE-TOOLS\system-bridge")
NOTIFICATIONS_LOG = BASE_DIR / "notifications.jsonl"
STATE_FILE = BASE_DIR / "live_state.json"
MEMORY_DB = Path(r"D:\_CLAUDE-TOOLS\claude-memory-server\data\memories.db")

class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Notification:
    """A notification to show the user."""
    title: str
    message: str
    priority: Priority
    category: str  # mismatch, reminder, suggestion, warning, info
    timestamp: str
    actions: List[Dict] = None
    auto_dismiss_seconds: int = 0

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "message": self.message,
            "priority": self.priority.name,
            "category": self.category,
            "timestamp": self.timestamp,
            "actions": self.actions or [],
            "auto_dismiss_seconds": self.auto_dismiss_seconds
        }


class NotificationEngine:
    """Engine for generating and delivering notifications."""

    def __init__(self):
        self.delivered = set()  # Track delivered notifications to avoid duplicates

    def _get_notification_id(self, notification: Notification) -> str:
        """Generate unique ID for a notification."""
        return f"{notification.category}:{notification.title}:{notification.message[:50]}"

    def send_windows_toast(self, notification: Notification) -> bool:
        """Send Windows toast notification."""
        ps_script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

        $template = @"
        <toast>
            <visual>
                <binding template="ToastText02">
                    <text id="1">{notification.title}</text>
                    <text id="2">{notification.message[:200]}</text>
                </binding>
            </visual>
        </toast>
"@

        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Claude Code").Show($toast)
        '''

        try:
            subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True, timeout=10
            )
            return True
        except Exception as e:
            print(f"Toast notification failed: {e}")
            return False

    def send_sound_alert(self, priority: Priority):
        """Play a sound alert based on priority."""
        sounds = {
            Priority.LOW: "ms-winsoundevent:Notification.Default",
            Priority.MEDIUM: "ms-winsoundevent:Notification.Mail",
            Priority.HIGH: "ms-winsoundevent:Notification.Reminder",
            Priority.CRITICAL: "ms-winsoundevent:Notification.Looping.Alarm"
        }

        ps_script = f'''
        $sound = New-Object System.Media.SoundPlayer
        $sound.SoundLocation = "C:\\Windows\\Media\\notify.wav"
        $sound.Play()
        '''

        try:
            subprocess.run(['powershell', '-Command', ps_script], capture_output=True, timeout=5)
        except:
            pass

    def log_notification(self, notification: Notification):
        """Log notification to file."""
        with open(NOTIFICATIONS_LOG, 'a') as f:
            f.write(json.dumps(notification.to_dict()) + '\n')

    def deliver(self, notification: Notification, toast: bool = True, sound: bool = False):
        """Deliver a notification through configured channels."""
        notif_id = self._get_notification_id(notification)

        # Check for duplicate
        if notif_id in self.delivered:
            return False

        self.delivered.add(notif_id)

        # Log
        self.log_notification(notification)

        # Toast
        if toast and notification.priority.value >= Priority.MEDIUM.value:
            self.send_windows_toast(notification)

        # Sound
        if sound and notification.priority.value >= Priority.HIGH.value:
            self.send_sound_alert(notification.priority)

        return True


class ProactiveMonitor:
    """Monitors system and generates proactive notifications."""

    def __init__(self):
        self.engine = NotificationEngine()
        self.last_check = {}

    def check_project_mismatch(self, state: Dict) -> Optional[Notification]:
        """Check for project mismatches."""
        revit = state.get("revit", {})
        bluebeam = state.get("bluebeam", {})

        if not revit.get("connected") or not bluebeam.get("running"):
            return None

        revit_doc = revit.get("document", "").lower()
        bluebeam_doc = bluebeam.get("document", "").lower()

        # Simple mismatch detection
        if revit_doc and bluebeam_doc:
            # Extract project names
            revit_words = set(revit_doc.replace("-", " ").replace("_", " ").split())
            bluebeam_words = set(bluebeam_doc.replace("-", " ").replace("_", " ").split())

            # Check for overlap
            common = revit_words & bluebeam_words
            significant_common = {w for w in common if len(w) > 3}

            if len(significant_common) < 2:  # Not enough overlap
                return Notification(
                    title="Project Mismatch Detected",
                    message=f"Revit: {revit.get('document', 'Unknown')}\nBluebeam: {bluebeam.get('document', 'Unknown')}",
                    priority=Priority.HIGH,
                    category="mismatch",
                    timestamp=datetime.now().isoformat(),
                    actions=[
                        {"label": "Switch Revit", "action": "switch_revit"},
                        {"label": "Switch Bluebeam", "action": "switch_bluebeam"},
                        {"label": "Ignore", "action": "ignore"}
                    ]
                )

        return None

    def check_unfinished_work(self) -> List[Notification]:
        """Check for unfinished work reminders."""
        notifications = []

        if not MEMORY_DB.exists():
            return notifications

        conn = sqlite3.connect(MEMORY_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Find session summaries with next steps
        cursor.execute("""
            SELECT content, project, created_at FROM memories
            WHERE tags LIKE '%session-summary%'
            AND content LIKE '%### Next Steps%'
            ORDER BY created_at DESC
            LIMIT 3
        """)

        for row in cursor.fetchall():
            created = datetime.fromisoformat(row['created_at'].replace(' ', 'T'))

            # Only remind if > 1 hour old
            if datetime.now() - created > timedelta(hours=1):
                content = row['content']
                if '### Next Steps' in content:
                    steps = content.split('### Next Steps')[1].split('###')[0]
                    first_step = steps.strip().split('\n')[0] if steps else "Continue work"

                    notifications.append(Notification(
                        title=f"Unfinished: {row['project'] or 'Project'}",
                        message=first_step[:100],
                        priority=Priority.MEDIUM,
                        category="reminder",
                        timestamp=datetime.now().isoformat()
                    ))

        conn.close()
        return notifications

    def check_time_based_reminders(self) -> List[Notification]:
        """Generate time-based reminders."""
        notifications = []
        now = datetime.now()

        # End of day reminder (after 5 PM)
        if now.hour >= 17:
            notifications.append(Notification(
                title="End of Day",
                message="Consider summarizing today's work before ending session.",
                priority=Priority.LOW,
                category="reminder",
                timestamp=now.isoformat(),
                auto_dismiss_seconds=300
            ))

        # Save reminder (every hour)
        if now.minute == 0:
            notifications.append(Notification(
                title="Periodic Save Reminder",
                message="Make sure to save your Revit model.",
                priority=Priority.LOW,
                category="reminder",
                timestamp=now.isoformat(),
                auto_dismiss_seconds=60
            ))

        return notifications

    def check_quality_issues(self, state: Dict) -> List[Notification]:
        """Check for quality issues that need attention."""
        notifications = []

        # This would integrate with Revit MCP to check:
        # - Untagged elements
        # - Missing dimensions
        # - View warnings
        # - Schedule inconsistencies

        # Placeholder for when integrated
        revit = state.get("revit", {})
        if revit.get("connected"):
            view_name = revit.get("viewName", "")
            if "Copy" in view_name:
                notifications.append(Notification(
                    title="Working View Detected",
                    message=f"You're on '{view_name}'. Is this the sheet view?",
                    priority=Priority.LOW,
                    category="info",
                    timestamp=datetime.now().isoformat()
                ))

        return notifications

    def run_checks(self, state: Dict = None) -> List[Dict]:
        """Run all checks and return notifications."""
        if state is None:
            if STATE_FILE.exists():
                with open(STATE_FILE) as f:
                    state = json.load(f)
            else:
                state = {}

        all_notifications = []

        # Project mismatch
        mismatch = self.check_project_mismatch(state)
        if mismatch:
            all_notifications.append(mismatch)

        # Unfinished work
        all_notifications.extend(self.check_unfinished_work())

        # Time-based
        all_notifications.extend(self.check_time_based_reminders())

        # Quality
        all_notifications.extend(self.check_quality_issues(state))

        # Deliver all
        results = []
        for notif in all_notifications:
            delivered = self.engine.deliver(notif, toast=True, sound=False)
            results.append({
                **notif.to_dict(),
                "delivered": delivered
            })

        return results


def main():
    """CLI interface."""
    import sys

    monitor = ProactiveMonitor()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "check":
            results = monitor.run_checks()
            print(json.dumps({"notifications": results}, indent=2))

        elif cmd == "mismatch":
            # Quick mismatch check
            state = {
                "revit": {"connected": True, "document": sys.argv[2] if len(sys.argv) > 2 else "Unknown"},
                "bluebeam": {"running": True, "document": sys.argv[3] if len(sys.argv) > 3 else "Unknown"}
            }
            result = monitor.check_project_mismatch(state)
            if result:
                print(json.dumps(result.to_dict(), indent=2))
            else:
                print('{"status": "no_mismatch"}')

        elif cmd == "toast":
            # Send a test toast
            notif = Notification(
                title="Test Notification",
                message=sys.argv[2] if len(sys.argv) > 2 else "This is a test from Claude Code",
                priority=Priority.MEDIUM,
                category="info",
                timestamp=datetime.now().isoformat()
            )
            monitor.engine.send_windows_toast(notif)
            print('{"status": "sent"}')

        else:
            print(f'{{"error": "Unknown command: {cmd}"}}')
    else:
        # Default: run all checks
        results = monitor.run_checks()
        print(json.dumps({"notifications": results}, indent=2))


if __name__ == "__main__":
    main()
