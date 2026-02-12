#!/usr/bin/env python3
"""
Morning Briefing Generator

Generates daily briefings for Weber at 7 AM.
Integrates with calendar, email, and Revit project status.
"""

import subprocess
import sys
import json
from datetime import datetime
from pathlib import Path

# Add paths for other tools
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/google-calendar-mcp")
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/voice-mcp")

def get_calendar_events():
    """Get today's calendar events"""
    try:
        result = subprocess.run(
            ['python3', '/mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/calendar_client.py', 'today'],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip() if result.stdout else "No calendar events today."
    except Exception as e:
        return f"Could not fetch calendar: {e}"

def get_email_summary():
    """Get email summary from monitoring system"""
    try:
        state_file = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")
        if state_file.exists():
            state = json.loads(state_file.read_text())
            email = state.get('email', {})
            unread = email.get('unread_count', 0)
            urgent = email.get('urgent_count', 0)
            needs_response = email.get('needs_response_count', 0)

            summary = []
            if unread > 0:
                summary.append(f"{unread} unread emails")
            if urgent > 0:
                summary.append(f"{urgent} urgent")
            if needs_response > 0:
                summary.append(f"{needs_response} need response")

            return ", ".join(summary) if summary else "Inbox clear"
        return "Email status unavailable"
    except Exception as e:
        return f"Could not fetch email status: {e}"

def get_active_apps():
    """Get currently running apps from system state"""
    try:
        state_file = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")
        if state_file.exists():
            state = json.loads(state_file.read_text())
            apps = state.get('applications', [])

            important_apps = []
            for app in apps:
                name = app.get('ProcessName', '')
                title = app.get('MainWindowTitle', '')

                if name.lower() == 'revit':
                    important_apps.append(f"Revit: {title}")
                elif 'code' in name.lower():
                    important_apps.append(f"VS Code active")
                elif name.lower() == 'bluebeam' or name.lower() == 'revu':
                    important_apps.append(f"Bluebeam: {title}")

            return ", ".join(important_apps) if important_apps else "No BIM apps running"
        return "System status unavailable"
    except Exception as e:
        return f"Could not fetch system status: {e}"

def get_weather():
    """Get weather forecast (simple placeholder)"""
    # Could integrate with a weather API
    return "Check weather at weather.com"

def generate_briefing():
    """Generate the full morning briefing"""
    now = datetime.now()
    day_name = now.strftime("%A, %B %d, %Y")

    calendar = get_calendar_events()
    email = get_email_summary()
    apps = get_active_apps()

    briefing = f"""
Good morning, Weber! Here's your briefing for {day_name}.

CALENDAR:
{calendar}

EMAIL STATUS:
{email}

SYSTEM STATUS:
{apps}

Have a productive day!
""".strip()

    return briefing

def main():
    """Run the morning briefing"""
    print("=" * 60)
    print("GENERATING MORNING BRIEFING")
    print("=" * 60)

    briefing = generate_briefing()

    # Print to console
    print(briefing)

    # Send to Telegram + speak it
    try:
        from notify_channels import notify_all
        results = notify_all(briefing, voice=True)
        print(f"Notification results: {results}")
    except ImportError:
        # Fallback: just speak locally
        try:
            subprocess.run(
                ['python3', '/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py', briefing],
                timeout=60
            )
        except Exception as e:
            print(f"Voice fallback failed: {e}")

    return briefing

if __name__ == "__main__":
    main()
