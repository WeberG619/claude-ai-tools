#!/usr/bin/env python3
"""
Shared notification sender for proactive features.
Sends messages to Telegram (and WhatsApp via gateway hub) directly.
"""

import os
import asyncio
import subprocess
import json
import logging
from datetime import datetime

logger = logging.getLogger("notify_channels")

# Telegram config (same as telegram-gateway/bot.py)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8101819463")

# Gateway hub for WhatsApp relay
GATEWAY_HUB_URL = "ws://127.0.0.1:18789"


def send_telegram(message: str) -> bool:
    """Send a message to Weber's Telegram using the bot API directly."""
    import urllib.request
    import urllib.parse

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # Try Markdown first, fall back to plain text if special chars cause 400
    for parse_mode in ("Markdown", None):
        try:
            params = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
            }
            if parse_mode:
                params["parse_mode"] = parse_mode

            data = urllib.parse.urlencode(params).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                if result.get("ok"):
                    logger.info(f"Telegram sent: {message[:50]}...")
                    return True
                else:
                    logger.error(f"Telegram API error: {result}")
                    return False
        except urllib.error.HTTPError as e:
            if e.code == 400 and parse_mode:
                logger.debug(f"Markdown parse failed, retrying as plain text")
                continue
            logger.error(f"Telegram send failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False
    return False


def send_voice(message: str, max_chars: int = 500) -> bool:
    """Speak the message using voice-mcp TTS. Truncates long messages."""
    try:
        # Truncate long messages for voice (keep first section)
        voice_text = message
        if len(voice_text) > max_chars:
            voice_text = voice_text[:max_chars].rsplit('\n', 1)[0] + "\n\n...and more details on Telegram."

        subprocess.run(
            ['python3', '/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py', voice_text],
            timeout=120,
            capture_output=True
        )
        return True
    except Exception as e:
        logger.error(f"Voice failed: {e}")
        return False


def notify_all(message: str, voice: bool = True):
    """Send notification to all channels: Telegram + voice."""
    results = {}

    # Always send to Telegram
    results["telegram"] = send_telegram(message)

    # Speak locally if requested
    if voice:
        results["voice"] = send_voice(message)

    timestamp = datetime.now().strftime("%H:%M:%S")
    logger.info(f"[{timestamp}] notify_all results: {results}")
    return results


def notify_telegram_only(message: str):
    """Send notification only to Telegram (silent, no voice)."""
    return send_telegram(message)


def notify_voice_only(message: str):
    """Speak only, no push notification."""
    return send_voice(message)


def request_approval(action: str, description: str, details: str = "",
                     timeout_minutes: int = 10, auto_approve: bool = True) -> str:
    """
    Request Weber's approval via Telegram before taking a sensitive action.
    Returns approval_id. Use check_approval() or wait_for_approval() to get result.

    Example:
        aid = request_approval("send_email", "Reply to Bruce about permits",
                               details="Hi Bruce, the permit is ready...")
        status = wait_for_approval(aid)
        if status in ("approved", "timed_out"):
            send_the_email()
    """
    import sys
    sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/gateway")
    from approval_system import request_approval as _request
    return _request(action, description, details, timeout_minutes, auto_approve)


def check_approval(approval_id: str) -> str:
    """Check approval status: pending/approved/cancelled/edited/timed_out."""
    import sys
    sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/gateway")
    from approval_system import check_approval as _check
    return _check(approval_id)


def wait_for_approval(approval_id: str, poll_interval: int = 5) -> str:
    """Block until approval resolves. Returns final status string."""
    import sys
    sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/gateway")
    from approval_system import wait_for_approval as _wait
    return _wait(approval_id, poll_interval)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
        print(f"Sending: {msg}")
        results = notify_all(msg)
        print(f"Results: {results}")
    else:
        print("Usage: python notify_channels.py <message>")
