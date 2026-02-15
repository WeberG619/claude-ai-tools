#!/usr/bin/env python3
"""
Output Handlers - Route findings to voice, queue, or alerts.

Voice: Uses voice-mcp for TTS
Queue: Writes to ~/.claude/ambient_queue.json
Critical: Voice + queue + optional desktop notification
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from analysis_rules import Finding, FindingTier

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False


def _run_ps(cmd, timeout=30):
    if _HAS_BRIDGE:
        return _ps_bridge(cmd, timeout)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, timeout=timeout)
    class _R:
        stdout = r.stdout; stderr = r.stderr; returncode = r.returncode; success = r.returncode == 0
    return _R()


# Configuration
QUEUE_FILE = Path.home() / ".claude" / "ambient_queue.json"
VOICE_MCP_PATH = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")
MAX_QUEUE_SIZE = 100  # Keep last N entries


def speak_finding(finding: Finding) -> bool:
    """
    Announce finding via TTS.
    Returns True if successful.
    """
    message = finding.message

    # Add context for certain categories
    if finding.category == "unjoined_walls":
        count = finding.details.get("total_unjoined", 0)
        if count > 2:
            message = f"{finding.message}. Total unjoined: {count}"

    return speak(message)


def speak(text: str, voice: str = "andrew") -> bool:
    """
    Speak text using voice-mcp.
    Fallback to direct edge-tts if MCP fails.
    """
    try:
        # Try voice-mcp speak.py directly
        if VOICE_MCP_PATH.exists():
            result = subprocess.run(
                ["python3", str(VOICE_MCP_PATH), text],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print(f"[Voice] Spoke: {text}")
                return True

        # Fallback: Try PowerShell with edge-tts
        ps_script = f'''
$text = @"
{text}
"@
python "D:\\_CLAUDE-TOOLS\\voice-mcp\\speak.py" $text
'''
        result = _run_ps(ps_script, timeout=30)

        if result.returncode == 0:
            print(f"[Voice] Spoke (fallback): {text}")
            return True

        print(f"[Voice] Failed to speak: {result.stderr}", file=sys.stderr)
        return False

    except subprocess.TimeoutExpired:
        print("[Voice] TTS timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[Voice] Error: {e}", file=sys.stderr)
        return False


def queue_finding(finding: Finding) -> bool:
    """
    Add finding to the queue file for later review.
    """
    try:
        # Load existing queue
        queue = []
        if QUEUE_FILE.exists():
            try:
                with open(QUEUE_FILE) as f:
                    data = json.load(f)
                    queue = data.get("findings", [])
            except:
                queue = []

        # Add new finding
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tier": finding.tier.value,
            "category": finding.category,
            "message": finding.message,
            "details": finding.details
        }
        queue.append(entry)

        # Trim to max size
        if len(queue) > MAX_QUEUE_SIZE:
            queue = queue[-MAX_QUEUE_SIZE:]

        # Write back
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(QUEUE_FILE, "w") as f:
            json.dump({
                "updated": datetime.now().isoformat(),
                "count": len(queue),
                "findings": queue
            }, f, indent=2)

        print(f"[Queue] Added: {finding.message}")
        return True

    except Exception as e:
        print(f"[Queue] Error: {e}", file=sys.stderr)
        return False


def alert_critical(finding: Finding) -> bool:
    """
    Handle critical findings: voice + queue + optional notification.
    """
    # Always voice critical findings
    speak(f"Critical: {finding.message}")

    # Always queue
    queue_finding(finding)

    # Optional: Desktop notification (Windows toast)
    try:
        ps_script = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast>
    <visual>
        <binding template="ToastText02">
            <text id="1">Revit Monitor Alert</text>
            <text id="2">{finding.message}</text>
        </binding>
    </visual>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Revit Monitor").Show($toast)
'''
        _run_ps(ps_script, timeout=5)
    except:
        pass  # Notification is optional

    return True


def get_queue_summary() -> dict:
    """
    Get summary of queued findings for Claude Code session start.
    """
    if not QUEUE_FILE.exists():
        return {"count": 0, "findings": []}

    try:
        with open(QUEUE_FILE) as f:
            data = json.load(f)

        findings = data.get("findings", [])

        # Group by category
        by_category = {}
        for f in findings:
            cat = f.get("category", "unknown")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f)

        # Build summary
        summary_parts = []
        for cat, items in by_category.items():
            summary_parts.append(f"{cat}: {len(items)}")

        return {
            "count": len(findings),
            "by_category": by_category,
            "summary": ", ".join(summary_parts) if summary_parts else "No findings",
            "since": findings[0].get("timestamp") if findings else None
        }

    except Exception as e:
        return {"count": 0, "error": str(e)}


def clear_queue() -> bool:
    """Clear the queue after review."""
    try:
        if QUEUE_FILE.exists():
            QUEUE_FILE.unlink()
        return True
    except:
        return False


# CLI for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Output handler testing")
    parser.add_argument("--speak", "-s", help="Test speaking text")
    parser.add_argument("--summary", action="store_true", help="Show queue summary")
    parser.add_argument("--clear", action="store_true", help="Clear queue")

    args = parser.parse_args()

    if args.speak:
        speak(args.speak)
    elif args.summary:
        summary = get_queue_summary()
        print(json.dumps(summary, indent=2))
    elif args.clear:
        clear_queue()
        print("Queue cleared")
    else:
        parser.print_help()
