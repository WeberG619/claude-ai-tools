"""Response monitor - checks for replies to submitted proposals.

Periodically checks platform inboxes via Playwright CDP for messages
related to our submitted proposals. Sends notifications when responses
are detected.
"""

from __future__ import annotations

import json
import logging
import subprocess
import os
import sys
from datetime import datetime

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

from core.database import Database
from core.models import ProposalStatus, OpportunityStatus

logger = logging.getLogger("opportunityengine.agents.response_monitor")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_windows_script(script_name: str, timeout: int = 60) -> str:
    """Run a Python script on Windows via PowerShell and return stdout."""
    script_path = os.path.join(BASE_DIR, "scouts", script_name)
    try:
        cmd = f"cd 'D:\\_CLAUDE-TOOLS\\opportunityengine\\scouts'; python {script_name}"
        result = _run_ps(cmd, timeout=timeout)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.warning(f"Script {script_name} timed out after {timeout}s")
        return ""
    except Exception as e:
        logger.error(f"Script {script_name} failed: {e}")
        return ""


class ResponseMonitor:
    """Monitors platform inboxes for responses to submitted proposals."""

    def __init__(self, db: Database):
        self.db = db
        self._last_known_messages: dict[str, list[str]] = {}

    def check_all(self) -> list[dict]:
        """Check all platforms for new responses. Returns list of new messages."""
        responses = []

        # Get submitted proposals
        submitted = self.db.list_proposals(status=ProposalStatus.SUBMITTED)
        if not submitted:
            logger.info("No submitted proposals to monitor")
            return responses

        sources = set()
        for prop in submitted:
            opp = self.db.get_opportunity(prop.opportunity_id)
            if opp:
                sources.add(opp.source)

        logger.info(f"Monitoring {len(submitted)} submitted proposals across: {sources}")

        # Check each platform
        if "reddit" in sources:
            reddit_msgs = self._check_reddit()
            responses.extend(reddit_msgs)

        if "upwork" in sources:
            upwork_msgs = self._check_upwork()
            responses.extend(upwork_msgs)

        if "freelancer" in sources:
            freelancer_msgs = self._check_freelancer()
            responses.extend(freelancer_msgs)

        return responses

    def _check_reddit(self) -> list[dict]:
        """Check Reddit inbox for DM replies."""
        responses = []
        try:
            # Use the Reddit JSON API to check inbox (needs cookies from browser)
            # Simpler approach: run a Playwright script to check inbox
            output = _run_windows_script("check_reddit_inbox.py", timeout=45)
            if output:
                messages = json.loads(output) if output.startswith("[") else []
                for msg in messages:
                    if msg.get("is_new"):
                        responses.append({
                            "platform": "reddit",
                            "from": msg.get("author", "unknown"),
                            "subject": msg.get("subject", ""),
                            "preview": msg.get("body", "")[:200],
                            "url": msg.get("url", ""),
                        })
                        logger.info(f"Reddit response from {msg.get('author')}: {msg.get('subject')}")
        except Exception as e:
            logger.error(f"Reddit inbox check failed: {e}")
        return responses

    def _check_upwork(self) -> list[dict]:
        """Check Upwork messages for client responses."""
        responses = []
        try:
            output = _run_windows_script("check_upwork_messages.py", timeout=45)
            if output:
                messages = json.loads(output) if output.startswith("[") else []
                for msg in messages:
                    if msg.get("is_new"):
                        responses.append({
                            "platform": "upwork",
                            "from": msg.get("client", "unknown"),
                            "subject": msg.get("job_title", ""),
                            "preview": msg.get("message", "")[:200],
                            "url": msg.get("url", ""),
                        })
                        logger.info(f"Upwork response from {msg.get('client')}: {msg.get('job_title')}")
        except Exception as e:
            logger.error(f"Upwork message check failed: {e}")
        return responses

    def _check_freelancer(self) -> list[dict]:
        """Check Freelancer messages/awards."""
        responses = []
        try:
            output = _run_windows_script("check_freelancer_messages.py", timeout=45)
            if output:
                messages = json.loads(output) if output.startswith("[") else []
                for msg in messages:
                    if msg.get("is_new"):
                        responses.append({
                            "platform": "freelancer",
                            "from": msg.get("client", "unknown"),
                            "subject": msg.get("project", ""),
                            "preview": msg.get("message", "")[:200],
                            "url": msg.get("url", ""),
                        })
                        logger.info(f"Freelancer response: {msg.get('project')}")
        except Exception as e:
            logger.error(f"Freelancer message check failed: {e}")
        return responses
