#!/usr/bin/env python3
"""
Email Monitor - Pushes email alerts to Telegram in real-time.

Reads email_alerts.json (written by email-watcher daemon) and sends
notifications for client emails and urgent items.

Three notification tiers:
  1. Client emails (known domains) -> Telegram + voice
  2. urgent_response category -> Telegram + voice
  3. needs_response category -> Telegram only (no voice noise)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("email_monitor")

ALERTS_FILE = Path("/mnt/d/_CLAUDE-TOOLS/email-watcher/email_alerts.json")

# Important client email domains - emails from these domains get voice alerts
CLIENT_DOMAINS = [
    "bdarchitect.net",
    "lesfantal.com",
    "afuriaesthetics.com",
    "fantal.com",
    "bimopsstudio.com",
]

# Specific important contacts
CLIENT_EMAILS = [
    "ifantal@lesfantal.com",
    "bruce@bdarchitect.net",
    "paola@bdarchitect.net",
    "rachelle@afuriaesthetics.com",
]


def _is_client_email(sender: str) -> bool:
    """Check if sender is from a known client domain."""
    sender_lower = sender.lower()
    # Check specific addresses
    for addr in CLIENT_EMAILS:
        if addr in sender_lower:
            return True
    # Check domains
    for domain in CLIENT_DOMAINS:
        if domain in sender_lower:
            return True
    return False


def _extract_sender_name(from_field: str) -> str:
    """Extract readable name from email From field."""
    # "John Doe <john@example.com>" -> "John Doe"
    if "<" in from_field:
        name = from_field.split("<")[0].strip().strip('"')
        if name:
            return name
    return from_field


class EmailMonitor:
    """Monitors email alerts and pushes notifications."""

    def __init__(self, tracker_state):
        self.tracker = tracker_state

    def check(self):
        """Main check method - called every 60s by scheduler."""
        alerts = self._load_alerts()
        if not alerts:
            return

        alert_list = alerts.get("alerts", [])
        if not alert_list:
            return

        for alert in alert_list:
            email_id = alert.get("id", "")
            if not email_id:
                continue

            # Skip already notified
            if self.tracker.is_email_notified(email_id):
                continue

            category = alert.get("category", "")
            sender = alert.get("from", "")
            subject = alert.get("subject", "")

            # Determine notification tier
            is_client = _is_client_email(sender)
            is_urgent = category == "urgent_response"
            is_needs_response = category == "needs_response"

            if is_client or is_urgent:
                # Tier 1 & 2: Telegram + voice
                self._notify_priority(alert, is_client)
                self.tracker.mark_email_notified(email_id)
            elif is_needs_response:
                # Tier 3: Telegram only
                self._notify_standard(alert)
                self.tracker.mark_email_notified(email_id)

        # Clean old tracked emails periodically
        self.tracker.clean_old_emails(max_age_hours=48.0)

    def _load_alerts(self) -> Dict:
        """Load email alerts from JSON file."""
        try:
            if ALERTS_FILE.exists():
                with open(ALERTS_FILE, "r") as f:
                    return json.load(f)
        except json.JSONDecodeError:
            # File may be mid-write by email-watcher
            logger.debug("email_alerts.json parse error (likely mid-write)")
        except IOError as e:
            logger.error(f"Failed to read email alerts: {e}")
        return {}

    def _notify_priority(self, alert: Dict, is_client: bool):
        """Send priority notification (Telegram + voice)."""
        sender = _extract_sender_name(alert.get("from", "Unknown"))
        subject = alert.get("subject", "(No subject)")
        account = alert.get("account", "")

        label = "Client email" if is_client else "Urgent email"
        message = f"{label} from {sender}: {subject}"
        if account:
            message += f"\n({account})"

        logger.info(f"Priority email alert: {message}")

        try:
            from notify_channels import notify_all
            notify_all(message, voice=True)
        except Exception as e:
            logger.error(f"Failed to send priority email alert: {e}")

    def _notify_standard(self, alert: Dict):
        """Send standard notification (Telegram only, no voice)."""
        sender = _extract_sender_name(alert.get("from", "Unknown"))
        subject = alert.get("subject", "(No subject)")

        message = f"Email needs response from {sender}: {subject}"

        logger.info(f"Standard email alert: {message}")

        try:
            from notify_channels import notify_telegram_only
            notify_telegram_only(message)
        except Exception as e:
            logger.error(f"Failed to send standard email alert: {e}")


if __name__ == "__main__":
    # Manual test
    from tracker_state import TrackerState
    logging.basicConfig(level=logging.INFO)

    state = TrackerState()
    monitor = EmailMonitor(state)

    print(f"Alerts file: {ALERTS_FILE}")
    print(f"File exists: {ALERTS_FILE.exists()}")

    if ALERTS_FILE.exists():
        alerts = monitor._load_alerts()
        print(f"Total alerts: {len(alerts.get('alerts', []))}")
        print(f"Urgent: {alerts.get('urgent_count', 0)}")
        print(f"Needs response: {alerts.get('needs_response_count', 0)}")
        for a in alerts.get("alerts", []):
            print(f"  [{a.get('category')}] {a.get('from', '')[:40]} - {a.get('subject', '')[:50]}")
            print(f"    Client: {_is_client_email(a.get('from', ''))}")

    print("\nRunning check...")
    monitor.check()
    state.save()
    print("Done.")
