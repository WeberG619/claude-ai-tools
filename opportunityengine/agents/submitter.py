"""Submitter agent - actually submits proposals to platforms.

Routes to the correct platform-specific submission method.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import Optional

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
from core.models import Opportunity, Proposal

logger = logging.getLogger("opportunityengine.agents.submitter")


class BaseSubmitter(ABC):
    """Base class for platform-specific submitters."""

    @abstractmethod
    def submit(self, opp: Opportunity, proposal: Proposal) -> dict:
        """Submit a proposal to the platform.

        Returns:
            dict with keys:
                - success: bool
                - message: str
                - reference: str (platform-specific confirmation)
        """
        ...


class GitHubSubmitter(BaseSubmitter):
    """Submit proposals by commenting on GitHub issues."""

    def submit(self, opp: Opportunity, proposal: Proposal) -> dict:
        issue_url = opp.source_id  # Full GitHub issue URL
        if not issue_url or "github.com" not in issue_url:
            # Try to reconstruct from client_info
            repo = opp.client_info.get("repo", "")
            issue_num = opp.client_info.get("issue_number", "")
            if repo and issue_num:
                issue_url = f"https://github.com/{repo}/issues/{issue_num}"
            else:
                return {"success": False, "message": "No valid GitHub issue URL", "reference": ""}

        # Extract repo and issue number from URL
        # URL format: https://github.com/owner/repo/issues/123
        parts = issue_url.rstrip("/").split("/")
        try:
            issue_idx = parts.index("issues")
            owner_repo = "/".join(parts[issue_idx - 2:issue_idx])
            issue_number = parts[issue_idx + 1]
        except (ValueError, IndexError):
            return {"success": False, "message": f"Cannot parse issue URL: {issue_url}", "reference": ""}

        # Use gh CLI to comment
        comment_body = proposal.content
        if proposal.pricing and proposal.pricing != "To be discussed":
            comment_body += f"\n\n**Proposed budget:** {proposal.pricing}"

        try:
            result = subprocess.run(
                [
                    "gh", "issue", "comment", issue_number,
                    "--repo", owner_repo,
                    "--body", comment_body,
                ],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                logger.info(f"GitHub comment posted on {owner_repo}#{issue_number}")
                return {
                    "success": True,
                    "message": f"Comment posted on {owner_repo}#{issue_number}",
                    "reference": f"{owner_repo}#{issue_number}",
                }
            else:
                return {
                    "success": False,
                    "message": f"gh CLI error: {result.stderr[:200]}",
                    "reference": "",
                }
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return {"success": False, "message": f"gh CLI failed: {e}", "reference": ""}


class FreelancerSubmitter(BaseSubmitter):
    """Submit bids on Freelancer.com via CDP browser automation."""

    def submit(self, opp: Opportunity, proposal: Proposal) -> dict:
        url = opp.raw_data.get("url", "")
        if not url or "freelancer.com" not in url:
            return {"success": False, "message": "No valid Freelancer URL", "reference": ""}

        bid_amount = proposal.pricing.replace("$", "").replace(",", "").strip()
        try:
            bid_float = float(bid_amount)
        except (ValueError, TypeError):
            bid_float = 0

        if bid_float <= 0:
            return {"success": False, "message": "No valid bid amount", "reference": ""}

        # Write submission data to shared D: drive (accessible from both WSL and Windows)
        script_data = {
            "url": url,
            "bid_amount": bid_float,
            "proposal_text": proposal.content,
            "currency": opp.currency or "USD",
        }

        tmp_path = "/mnt/d/_CLAUDE-TOOLS/opportunityengine/.tmp_submit.json"
        win_tmp_path = r"D:\_CLAUDE-TOOLS\opportunityengine\.tmp_submit.json"
        with open(tmp_path, "w") as f:
            json.dump(script_data, f)

        try:
            cmd = (f"cd 'D:\\_CLAUDE-TOOLS\\opportunityengine\\scouts'; "
                   f"python freelancer_submit.py '{win_tmp_path}'")
            result = _run_ps(cmd, timeout=120)

            stdout = result.stdout.strip()
            json_start = stdout.find("{")
            if json_start >= 0:
                resp = json.loads(stdout[json_start:])
                return {
                    "success": resp.get("success", False),
                    "message": resp.get("message", "Unknown"),
                    "reference": resp.get("reference", ""),
                }

            if result.returncode == 0:
                return {"success": True, "message": "Bid submitted", "reference": url}
            else:
                return {
                    "success": False,
                    "message": f"Script error: {result.stderr[:200]}",
                    "reference": "",
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Submission timed out", "reference": ""}
        except Exception as e:
            return {"success": False, "message": str(e), "reference": ""}


class RedditSubmitter(BaseSubmitter):
    """Submit proposals by replying to Reddit posts.

    NOTE: Reddit is strict about automated posting. This uses a cautious approach
    with rate limiting. For high-value posts, it's often better to DM the poster
    directly via browser.
    """

    def submit(self, opp: Opportunity, proposal: Proposal) -> dict:
        # Reddit automated replies are risky - hold for manual submission
        url = opp.raw_data.get("url", "")
        return {
            "success": False,
            "message": f"Reddit requires manual submission. Post at: {url}",
            "reference": url,
        }


class ManualSubmitter(BaseSubmitter):
    """Fallback for platforms that need manual submission."""

    def submit(self, opp: Opportunity, proposal: Proposal) -> dict:
        url = opp.raw_data.get("url", "") or opp.raw_data.get("apply_url", "")
        return {
            "success": False,
            "message": f"Manual submission needed. Apply at: {url}",
            "reference": url,
        }


# Registry of submitters by source
SUBMITTERS: dict[str, BaseSubmitter] = {
    "github": GitHubSubmitter(),
    "freelancer": FreelancerSubmitter(),
    "reddit": RedditSubmitter(),
    "hackernews": ManualSubmitter(),
    "remoteok": ManualSubmitter(),
    "upwork": ManualSubmitter(),
}


def get_submitter(source: str) -> BaseSubmitter:
    """Get the submitter for a given source."""
    return SUBMITTERS.get(source, ManualSubmitter())


def submit_proposal(db: Database, opp_id: int) -> dict:
    """Submit a proposal for an opportunity to its platform.

    Returns dict with success, message, reference.
    """
    opp = db.get_opportunity(opp_id)
    if not opp:
        return {"success": False, "message": f"Opportunity {opp_id} not found", "reference": ""}

    from core.models import ProposalStatus
    prop = db.get_proposal_for_opportunity(opp_id)
    if not prop:
        return {"success": False, "message": "No proposal found", "reference": ""}

    if prop.status not in (ProposalStatus.APPROVED, ProposalStatus.SUBMITTED):
        return {"success": False, "message": f"Proposal status is '{prop.status}', needs approval first", "reference": ""}

    submitter = get_submitter(opp.source)
    result = submitter.submit(opp, prop)

    if result["success"]:
        from datetime import datetime
        from core.models import OpportunityStatus
        now = datetime.utcnow().isoformat()
        db.update_proposal(prop.id, status=ProposalStatus.SUBMITTED, submitted_at=now)
        db.update_opportunity(opp_id, status=OpportunityStatus.SUBMITTED, submitted_at=now)
        logger.info(f"Submitted proposal for opp [{opp_id}] on {opp.source}: {result['message']}")
    else:
        logger.warning(f"Submission failed for opp [{opp_id}]: {result['message']}")

    return result
