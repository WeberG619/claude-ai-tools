#!/usr/bin/env python3
"""
Evening Summary - End-of-day recap at 6 PM.

Sends to Telegram only (no voice - non-disruptive at end of day).
Includes:
- Today's calendar recap
- Pending email responses
- Tomorrow's first event preview
"""

import json
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add calendar client to path
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/google-calendar-mcp")

logger = logging.getLogger("evening_summary")

ALERTS_FILE = Path("/mnt/d/_CLAUDE-TOOLS/email-watcher/email_alerts.json")


def _get_today_recap() -> str:
    """Get recap of today's calendar events."""
    try:
        from calendar_client import get_today_events, format_event
        events = get_today_events()

        if not events:
            return "No events today."

        lines = []
        for event in events:
            formatted = format_event(event)
            lines.append(f"  {formatted['start']} - {formatted['summary']}")

        return f"{len(events)} events today:\n" + "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to get today's events: {e}")
        return "Could not fetch today's events."


def _get_pending_emails() -> str:
    """Get count of pending email responses."""
    try:
        if ALERTS_FILE.exists():
            with open(ALERTS_FILE, "r") as f:
                alerts = json.load(f)

            urgent = alerts.get("urgent_count", 0)
            needs_response = alerts.get("needs_response_count", 0)
            total = urgent + needs_response

            if total == 0:
                return "All caught up on emails."

            parts = []
            if urgent > 0:
                parts.append(f"{urgent} urgent")
            if needs_response > 0:
                parts.append(f"{needs_response} need response")

            return f"{total} pending: " + ", ".join(parts)
        return "Email status unavailable."
    except (json.JSONDecodeError, IOError):
        return "Could not read email status."


def _get_tomorrow_preview() -> str:
    """Get tomorrow's first event as a preview."""
    try:
        from calendar_client import get_service
        service = get_service()

        tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_of_tomorrow = tomorrow + timedelta(days=1)

        events_result = service.events().list(
            calendarId="primary",
            timeMin=tomorrow.isoformat() + "Z",
            timeMax=end_of_tomorrow.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime",
            maxResults=5,
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return "No events tomorrow."

        lines = []
        for event in events:
            start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", ""))
            summary = event.get("summary", "(No title)")
            if "T" in start:
                dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                time_str = dt.strftime("%I:%M %p")
                lines.append(f"  {time_str} - {summary}")
            else:
                lines.append(f"  All day - {summary}")

        return f"{len(events)} events tomorrow:\n" + "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to get tomorrow's events: {e}")
        return "Could not fetch tomorrow's events."


def generate_evening_summary() -> str:
    """Generate the full evening summary."""
    now = datetime.now()
    day_name = now.strftime("%A, %B %d")

    today_recap = _get_today_recap()
    pending = _get_pending_emails()
    tomorrow = _get_tomorrow_preview()

    summary = f"""Evening Summary - {day_name}

TODAY'S RECAP:
{today_recap}

EMAIL STATUS:
{pending}

TOMORROW:
{tomorrow}

Have a good evening, Weber!"""

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    summary = generate_evening_summary()
    print(summary)

    if len(sys.argv) > 1 and sys.argv[1] == "--send":
        sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/proactive")
        from notify_channels import notify_telegram_only
        notify_telegram_only(summary)
        print("\nSent to Telegram.")
