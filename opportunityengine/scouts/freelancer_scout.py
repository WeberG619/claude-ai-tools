"""Freelancer.com Scout - finds freelance opportunities on Freelancer.

Primary method: Playwright CDP browser scraping via Windows Python.
Connects to existing Chrome CDP session with logged-in Freelancer account.
"""

from __future__ import annotations

import json
import logging
import sys
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
    import subprocess as sp
    r = sp.run(["powershell.exe", "-NoProfile", "-Command", cmd],
               capture_output=True, text=True, timeout=timeout)
    class _R:
        stdout = r.stdout; stderr = r.stderr; returncode = r.returncode; success = r.returncode == 0
    return _R()

from scouts.base_scout import BaseScout
from core.database import Database
from core.models import Opportunity, CompetitionLevel
from core.config import FREELANCER_SEARCH_TERMS

logger = logging.getLogger("opportunityengine.scouts.freelancer")


class FreelancerScout(BaseScout):
    """Scans Freelancer.com for freelance opportunities using CDP browser scraping."""

    def __init__(self, db: Database, max_per_term: int = 20):
        super().__init__(db)
        self.max_per_term = max_per_term

    @property
    def source_name(self) -> str:
        return "freelancer"

    def _fetch_opportunities(self) -> list[Opportunity]:
        opportunities = self._search_playwright_cdp()

        # Dedup within batch
        seen = set()
        unique = []
        for opp in opportunities:
            if opp.source_id not in seen:
                seen.add(opp.source_id)
                unique.append(opp)

        return unique

    def _search_playwright_cdp(self) -> list[Opportunity]:
        """Run freelancer_browser.py on Windows via PowerShell + Playwright CDP."""
        import subprocess as sp

        script = r"D:\_CLAUDE-TOOLS\opportunityengine\scouts\freelancer_browser.py"
        opportunities = []

        for term in FREELANCER_SEARCH_TERMS:
            try:
                cmd = f"cd 'D:\\_CLAUDE-TOOLS\\opportunityengine\\scouts'; python freelancer_browser.py '{term}' 2>$null"
                result = _run_ps(cmd, timeout=60)

                stdout = result.stdout.strip()

                # Check for JSON output first — Node deprecation warnings on stderr
                # cause PowerShell to return non-zero even when the script succeeds
                if not stdout or (result.returncode != 0 and "[" not in stdout and "{" not in stdout):
                    logger.warning(f"Freelancer scrape failed for '{term}': {result.stderr[:200] if result.stderr else 'no output'}")
                    continue
                json_start = stdout.find("[")
                if json_start == -1:
                    json_start = stdout.find("{")
                if json_start == -1:
                    logger.warning(f"No JSON in output for '{term}'")
                    continue

                data = json.loads(stdout[json_start:])
                if isinstance(data, dict) and data.get("error"):
                    logger.warning(f"Scraper error for '{term}': {data['error']}")
                    if data["error"] == "login_required":
                        logger.error("Freelancer login required - need to authenticate in CDP browser")
                        break
                    continue

                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("error"):
                        continue
                    opp = self._browser_result_to_opportunity(item, term)
                    if opp:
                        opportunities.append(opp)

            except sp.TimeoutExpired:
                logger.warning(f"Freelancer scrape timed out for '{term}'")
            except Exception as e:
                logger.error(f"Freelancer scrape error for '{term}': {e}")

        return opportunities

    def _browser_result_to_opportunity(self, item: dict, search_term: str) -> Optional[Opportunity]:
        """Convert a browser scrape result dict to an Opportunity."""
        title = item.get("title", "").strip()
        if not title:
            return None

        url = item.get("url", "")
        # Use project URL path as source_id (strip query params)
        source_id = url.split("?")[0].rstrip("/") if url else f"freelancer/{title[:40]}"

        budget_min = item.get("budget_min")
        budget_max = item.get("budget_max")
        skills = item.get("skills", [])

        # Determine competition level from bids count
        bids = item.get("bids_count")
        if bids is not None:
            if bids <= 5:
                competition = CompetitionLevel.LOW
            elif bids <= 20:
                competition = CompetitionLevel.MEDIUM
            else:
                competition = CompetitionLevel.HIGH
        else:
            competition = CompetitionLevel.UNKNOWN

        client_info = {}
        if bids is not None:
            client_info["proposals_count"] = bids
        if item.get("payment_verified"):
            client_info["payment_verified"] = True
        if item.get("sealed"):
            client_info["sealed"] = True

        return Opportunity(
            source="freelancer",
            source_id=source_id,
            title=title,
            description=item.get("description", ""),
            budget_min=budget_min,
            budget_max=budget_max,
            currency=item.get("currency", "USD"),
            skills_required=skills,
            competition_level=competition,
            client_info=client_info,
            raw_data={
                "search_term": search_term,
                "url": url,
                "posted": item.get("posted", ""),
                "time_left": item.get("time_left", ""),
                "is_hourly": item.get("is_hourly"),
            },
        )
