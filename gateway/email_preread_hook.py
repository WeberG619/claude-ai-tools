#!/usr/bin/env python3
"""
Email Pre-Read Security Hook

This hook is called BEFORE Claude reads any email content.
It scans for malicious content and either:
1. Returns sanitized content if safe
2. Blocks the email with explanation if dangerous

Integration:
- Called by the email reading workflow
- Logs all threats to gateway/logs/email_threats.log
- Returns formatted safe content for Claude to process
"""

import sys
import json
from pathlib import Path

# Add gateway to path
sys.path.insert(0, str(Path(__file__).parent))

from email_security import EmailSecurityScanner, format_safe_email

def preread_scan(email_data: dict) -> dict:
    """
    Scan email before Claude reads it.

    Args:
        email_data: {
            "sender": str,
            "subject": str,
            "body": str,
            "attachments": list (optional)
        }

    Returns:
        {
            "safe": bool,
            "content": str,  # Formatted content for Claude
            "threats": list,
            "blocked": bool,
            "reason": str
        }
    """
    scanner = EmailSecurityScanner(strict_mode=True)

    sender = email_data.get("sender", "unknown")
    subject = email_data.get("subject", "No Subject")
    body = email_data.get("body", "")

    # Scan the email
    result = scanner.scan_and_sanitize(body, sender, subject)

    # Format for Claude
    formatted = format_safe_email(result, sender, subject)

    return {
        "safe": result["is_safe"],
        "content": formatted,
        "threats": result["threats"],
        "threat_count": result["threat_count"],
        "blocked": not result["is_safe"],
        "reason": result["recommendation"],
        "sender_known": result.get("sender_known", False)
    }


def main():
    """CLI interface for testing"""
    if len(sys.argv) < 2:
        print("Usage: python email_preread_hook.py <email_json_file>")
        print("   or: echo '<json>' | python email_preread_hook.py -")
        sys.exit(1)

    if sys.argv[1] == "-":
        # Read from stdin
        email_data = json.loads(sys.stdin.read())
    else:
        # Read from file
        with open(sys.argv[1]) as f:
            email_data = json.load(f)

    result = preread_scan(email_data)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
