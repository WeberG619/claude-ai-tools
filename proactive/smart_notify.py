#!/usr/bin/env python3
"""
Smart Notification System

Monitors system state and sends proactive notifications
based on configurable rules.
"""

import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Callable, Dict, List, Any

# Important clients to watch for
IMPORTANT_CLIENTS = [
    "ifantal@lesfantal.com",      # Isa Fantal
    "bruce@bdarchitect.net",       # Bruce Davis
    "paola@bdarchitect.net",       # Paola Gomez
    "rachelle@afuriaesthetics.com" # Rachelle (Afuri)
]

class NotificationRule:
    """A rule for triggering notifications"""
    def __init__(self, name: str, trigger: str, condition: Callable,
                 action: str, message_template: str, cooldown_minutes: int = 5):
        self.name = name
        self.trigger = trigger
        self.condition = condition
        self.action = action
        self.message_template = message_template
        self.cooldown_minutes = cooldown_minutes
        self.last_triggered = None

    def should_trigger(self, event: Dict) -> bool:
        """Check if this rule should trigger"""
        # Check cooldown
        if self.last_triggered:
            elapsed = (datetime.now() - self.last_triggered).total_seconds() / 60
            if elapsed < self.cooldown_minutes:
                return False

        # Check condition
        return self.condition(event)

    def format_message(self, event: Dict) -> str:
        """Format the notification message"""
        return self.message_template.format(**event)

class SmartNotifier:
    """Smart notification manager"""

    def __init__(self):
        self.rules: List[NotificationRule] = []
        self.state_file = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")
        self.last_state = {}
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Set up default notification rules"""

        # Important email
        self.rules.append(NotificationRule(
            name="important_email",
            trigger="email_from_client",
            condition=lambda e: e.get('from', '') in IMPORTANT_CLIENTS,
            action="notify_all",
            message_template="Important email from {from}: {subject}",
            cooldown_minutes=1
        ))

        # Urgent email
        self.rules.append(NotificationRule(
            name="urgent_email",
            trigger="email_urgent",
            condition=lambda e: e.get('category') == 'urgent',
            action="notify_all",
            message_template="URGENT: {subject} from {from}",
            cooldown_minutes=1
        ))

        # Revit opened
        self.rules.append(NotificationRule(
            name="revit_opened",
            trigger="app_opened",
            condition=lambda e: 'revit' in e.get('app', '').lower(),
            action="log_only",
            message_template="Revit project opened: {title}",
            cooldown_minutes=60
        ))

        # High memory warning
        self.rules.append(NotificationRule(
            name="high_memory",
            trigger="system_status",
            condition=lambda e: e.get('memory_percent', 0) > 85,
            action="notify_local",
            message_template="High memory usage: {memory_percent}%. Consider closing some apps.",
            cooldown_minutes=30
        ))

        # Calendar reminder (15 min before)
        self.rules.append(NotificationRule(
            name="calendar_reminder",
            trigger="calendar_event",
            condition=lambda e: e.get('minutes_until', 999) <= 15,
            action="notify_all",
            message_template="Reminder: {title} in {minutes_until} minutes",
            cooldown_minutes=10
        ))

    def get_current_state(self) -> Dict:
        """Read current system state"""
        try:
            if self.state_file.exists():
                return json.loads(self.state_file.read_text())
        except:
            pass
        return {}

    def detect_events(self, old_state: Dict, new_state: Dict) -> List[Dict]:
        """Detect events by comparing states"""
        events = []

        # Check email changes
        old_email = old_state.get('email', {})
        new_email = new_state.get('email', {})

        for alert in new_email.get('alerts', []):
            events.append({
                'type': 'email_urgent' if alert.get('category') == 'urgent' else 'email_from_client',
                'from': alert.get('from', ''),
                'subject': alert.get('subject', ''),
                'category': alert.get('category', '')
            })

        # Check system status
        system = new_state.get('system', {})
        if system.get('memory_percent', 0) > 85:
            events.append({
                'type': 'system_status',
                'memory_percent': system.get('memory_percent', 0)
            })

        # Check app changes
        old_apps = {a.get('ProcessName', '') for a in old_state.get('applications', [])}
        new_apps = {a.get('ProcessName', '') for a in new_state.get('applications', [])}

        for app in new_state.get('applications', []):
            name = app.get('ProcessName', '')
            if name not in old_apps and 'revit' in name.lower():
                events.append({
                    'type': 'app_opened',
                    'app': name,
                    'title': app.get('MainWindowTitle', '')
                })

        return events

    def send_notification(self, message: str, action: str):
        """Send notification via specified action"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"

        try:
            from notify_channels import notify_all, notify_voice_only, notify_telegram_only
        except ImportError:
            notify_all = lambda m, **kw: print(f"NOTIFY: {m}")
            notify_voice_only = lambda m: print(f"VOICE: {m}")
            notify_telegram_only = lambda m: print(f"TELEGRAM: {m}")

        if action == "notify_all":
            print(f"NOTIFY ALL: {formatted}")
            notify_all(message, voice=True)

        elif action == "notify_local":
            print(f"LOCAL: {formatted}")
            notify_voice_only(message)

        elif action == "notify_telegram":
            print(f"TELEGRAM: {formatted}")
            notify_telegram_only(message)

        elif action == "log_only":
            print(f"LOG: {formatted}")

    def process_events(self, events: List[Dict]):
        """Process detected events against rules"""
        for event in events:
            for rule in self.rules:
                if rule.should_trigger(event):
                    message = rule.format_message(event)
                    self.send_notification(message, rule.action)
                    rule.last_triggered = datetime.now()

    def run_once(self):
        """Run one monitoring cycle"""
        new_state = self.get_current_state()
        events = self.detect_events(self.last_state, new_state)
        self.process_events(events)
        self.last_state = new_state

    def run_continuous(self, interval_seconds: int = 30):
        """Run continuous monitoring"""
        print("=" * 60)
        print("SMART NOTIFICATION SYSTEM ACTIVE")
        print(f"Monitoring every {interval_seconds} seconds...")
        print("=" * 60)

        while True:
            try:
                self.run_once()
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                print("\nStopping smart notifications...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(interval_seconds)

def main():
    """Main entry point"""
    notifier = SmartNotifier()

    # Check for one-time or continuous mode
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        notifier.run_once()
    else:
        notifier.run_continuous()

if __name__ == "__main__":
    main()
