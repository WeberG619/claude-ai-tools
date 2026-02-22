#!/usr/bin/env python3
"""
Test Google APIs - Gmail, Calendar, and Drive
For weberg619@gmail.com
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Installing required packages...")
    os.system("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

# Base directory for tools
BASE_DIR = Path("/mnt/d/_CLAUDE-TOOLS")

def test_gmail():
    """Test Gmail API access."""
    print("\n" + "="*60)
    print("TESTING GMAIL API")
    print("="*60)

    try:
        # Gmail uses IMAP with hardcoded credentials
        gmail_script = BASE_DIR / "gmail-attachments" / "imap_download.py"
        if gmail_script.exists():
            print("✓ Gmail IMAP script found")
            print(f"  Location: {gmail_script}")
            print("  Account: weberg619@gmail.com")
            print("  Method: IMAP with app password")

            # Test basic connectivity
            import subprocess
            result = subprocess.run(
                [sys.executable, str(gmail_script), "--list", "--limit", "1"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                print("✓ Gmail IMAP connection successful!")
                return True
            else:
                print(f"✗ Gmail IMAP error: {result.stderr}")
                return False
        else:
            print("✗ Gmail script not found")
            return False

    except Exception as e:
        print(f"✗ Gmail test failed: {e}")
        return False

def test_calendar():
    """Test Google Calendar API access."""
    print("\n" + "="*60)
    print("TESTING GOOGLE CALENDAR API")
    print("="*60)

    try:
        token_file = BASE_DIR / "google-calendar-mcp" / "token.json"
        creds_file = BASE_DIR / "google-calendar-mcp" / "credentials.json"

        if not creds_file.exists():
            print("✗ Calendar credentials.json not found")
            return False

        print(f"✓ Credentials found: {creds_file}")

        # Load token
        creds = None
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file))
            print("✓ Token file found and loaded")

        # Check if valid
        if creds and creds.valid:
            service = build('calendar', 'v3', credentials=creds)

            # Get calendar list
            calendars = service.calendarList().list().execute()
            print(f"✓ Connected to Google Calendar!")
            print(f"  Primary calendar: {calendars['items'][0]['summary']}")
            print(f"  Total calendars: {len(calendars['items'])}")

            # Get today's events
            now = datetime.utcnow()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            print(f"  Today's events: {len(events)}")

            return True
        else:
            print("✗ Calendar token invalid or missing - needs reauthorization")
            print("  Run: python /mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/calendar_client.py auth")
            return False

    except Exception as e:
        print(f"✗ Calendar test failed: {e}")
        return False

def test_drive():
    """Test Google Drive API access."""
    print("\n" + "="*60)
    print("TESTING GOOGLE DRIVE API")
    print("="*60)

    try:
        token_file = BASE_DIR / "google-drive-mcp" / "token.json"
        creds_file = BASE_DIR / "google-drive-mcp" / "credentials.json"

        if not creds_file.exists():
            print("✗ Drive credentials.json not found")
            return False

        print(f"✓ Credentials found: {creds_file}")

        # Load token
        creds = None
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file))
            print("✓ Token file found and loaded")

        # Check if valid
        if creds and creds.valid:
            service = build('drive', 'v3', credentials=creds)

            # List some files
            results = service.files().list(
                pageSize=5,
                fields="files(id, name, mimeType, modifiedTime)"
            ).execute()

            files = results.get('files', [])
            print(f"✓ Connected to Google Drive!")
            print(f"  Recent files: {len(files)}")

            for file in files[:3]:
                print(f"    - {file['name']}")

            return True
        else:
            print("✗ Drive token invalid or missing - needs reauthorization")
            print("  Run: python /mnt/d/_CLAUDE-TOOLS/google-drive-mcp/manual_auth.py")
            return False

    except Exception as e:
        print(f"✗ Drive test failed: {e}")
        return False

def main():
    """Test all Google APIs."""
    print("\n" + "="*60)
    print(" GOOGLE API TEST SUITE")
    print(" Account: weberg619@gmail.com")
    print("="*60)

    results = {
        "Gmail": test_gmail(),
        "Calendar": test_calendar(),
        "Drive": test_drive()
    }

    print("\n" + "="*60)
    print(" SUMMARY")
    print("="*60)

    for api, status in results.items():
        icon = "✓" if status else "✗"
        print(f"  {icon} {api}: {'Connected' if status else 'Needs Setup'}")

    print("\n" + "="*60)
    print(" QUICK ACCESS COMMANDS")
    print("="*60)

    print("\nGMAIL (via IMAP):")
    print("  python /mnt/d/_CLAUDE-TOOLS/gmail-attachments/imap_download.py --list")
    print("  python /mnt/d/_CLAUDE-TOOLS/gmail-attachments/imap_download.py --search 'from:sender' --download /path/")

    print("\nCALENDAR:")
    print("  python /mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/calendar_client.py today")
    print("  python /mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/calendar_client.py week")
    print("  python /mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/calendar_client.py add 'Meeting' '2026-01-28T14:00:00' '2026-01-28T15:00:00'")

    print("\nDRIVE:")
    print("  python /mnt/d/_CLAUDE-TOOLS/google-drive-mcp/drive_client.py list")
    print("  python /mnt/d/_CLAUDE-TOOLS/google-drive-mcp/drive_client.py upload /path/to/file")
    print("  python /mnt/d/_CLAUDE-TOOLS/google-drive-mcp/drive_client.py download <file_id>")

    print("\n" + "="*60)

if __name__ == "__main__":
    main()