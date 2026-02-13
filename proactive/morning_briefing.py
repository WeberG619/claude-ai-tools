#!/usr/bin/env python3
"""
Morning Briefing Generator

Generates daily briefings for Weber at 7 AM.
Integrates with calendar, email, weather, and system status.
"""

import json
import sys
import logging
import urllib.request
from datetime import datetime
from pathlib import Path

# Add paths for other tools
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/google-calendar-mcp")
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/voice-mcp")

logger = logging.getLogger("morning_briefing")

ALERTS_FILE = Path("/mnt/d/_CLAUDE-TOOLS/email-watcher/email_alerts.json")


def get_calendar_events():
    """Get today's calendar events via direct import."""
    try:
        from calendar_client import get_today_events, format_event
        events = get_today_events()

        if not events:
            return "No calendar events today."

        lines = []
        for event in events:
            formatted = format_event(event)
            lines.append(f"  {formatted['start']} - {formatted['summary']}")
            if formatted['location']:
                lines.append(f"    Location: {formatted['location']}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Calendar fetch failed: {e}")
        return f"Could not fetch calendar: {e}"


def get_weather():
    """Get weather from wttr.in (free, no API key). Retries with fallback formats."""
    # Try multiple formats in case one fails
    urls = [
        "https://wttr.in/Miami?format=3",
        "https://wttr.in/Miami?format=%l:+%c+%t+%w",
        "https://wttr.in/Miami?format=4",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                weather = resp.read().decode().strip()
                if weather and len(weather) > 3:
                    return weather
        except Exception as e:
            logger.debug(f"Weather fetch failed for {url}: {e}")
            continue
    return "Weather unavailable"


def get_email_summary():
    """Get email summary from monitoring system."""
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


def get_email_priorities():
    """Get specific priority emails from email_alerts.json."""
    try:
        if ALERTS_FILE.exists():
            with open(ALERTS_FILE, "r") as f:
                alerts = json.load(f)

            items = alerts.get("alerts", [])
            if not items:
                return None

            lines = []
            for alert in items[:5]:  # Top 5
                category = alert.get("category", "")
                sender = alert.get("from", "")
                subject = alert.get("subject", "")

                # Shorten sender
                if "<" in sender:
                    sender = sender.split("<")[0].strip().strip('"')

                tag = "URGENT" if category == "urgent_response" else "REPLY"
                lines.append(f"  [{tag}] {sender}: {subject[:50]}")

            return "\n".join(lines)
    except (json.JSONDecodeError, IOError):
        pass
    return None


def get_active_apps():
    """Get currently running apps from system state."""
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


def generate_briefing():
    """Generate the full morning briefing."""
    now = datetime.now()
    day_name = now.strftime("%A, %B %d, %Y")

    calendar = get_calendar_events()
    weather = get_weather()
    email = get_email_summary()
    priorities = get_email_priorities()
    apps = get_active_apps()

    briefing = f"""Good morning, Weber! Here's your briefing for {day_name}.

WEATHER:
  {weather}

CALENDAR:
{calendar}

EMAIL STATUS:
  {email}"""

    if priorities:
        briefing += f"""

PRIORITY EMAILS:
{priorities}"""

    briefing += f"""

SYSTEM STATUS:
  {apps}

Have a productive day!"""

    return briefing


def main():
    """Run the morning briefing."""
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
            import subprocess
            subprocess.run(
                ['python3', '/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py', briefing],
                timeout=60
            )
        except Exception as e:
            print(f"Voice fallback failed: {e}")

    return briefing


if __name__ == "__main__":
    main()
