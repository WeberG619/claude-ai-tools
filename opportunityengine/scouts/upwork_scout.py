"""Upwork Scout - finds freelance opportunities on Upwork.

Primary method: RSS feeds (may require auth cookies).
Fallback: Upwork API v3 or browser automation via autonomous-browser.

Note: Upwork RSS feeds may return 410 Gone without proper authentication.
To use browser-based scraping, ensure autonomous-browser is configured with
Upwork credentials in the vault.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.request import urlopen, Request
from urllib.parse import quote_plus
from html import unescape

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
from core.config import UPWORK_SEARCH_TERMS

logger = logging.getLogger("opportunityengine.scouts.upwork")

# Upwork RSS feed base URL
UPWORK_RSS_BASE = "https://www.upwork.com/ab/feed/jobs/rss"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class UpworkScout(BaseScout):
    """Scans Upwork for freelance opportunities using RSS feeds."""

    def __init__(self, db: Database, max_per_term: int = 20):
        super().__init__(db)
        self.max_per_term = max_per_term

    @property
    def source_name(self) -> str:
        return "upwork"

    def _fetch_opportunities(self) -> list[Opportunity]:
        opportunities = []

        # Primary: Playwright CDP via Windows Python (runs on Windows side)
        logger.info("Using Playwright CDP browser scraping")
        opportunities = self._search_playwright_cdp()

        if not opportunities:
            # Fallback: try RSS (may be deprecated)
            logger.info("Playwright returned nothing, trying RSS fallback")
            for term in UPWORK_SEARCH_TERMS[:5]:
                try:
                    opps = self._search_rss(term)
                    opportunities.extend(opps)
                except Exception as e:
                    if "410" in str(e) or "403" in str(e):
                        break
                    logger.warning(f"Upwork RSS failed for '{term}': {e}")

        # Dedup within batch
        seen = set()
        unique = []
        for opp in opportunities:
            if opp.source_id not in seen:
                seen.add(opp.source_id)
                unique.append(opp)

        return unique

    def _search_playwright_cdp(self) -> list[Opportunity]:
        """Primary: run upwork_browser.py on Windows via PowerShell + Playwright CDP."""
        import subprocess as sp
        import json as _json

        script = r"D:\_CLAUDE-TOOLS\opportunityengine\scouts\upwork_browser.py"
        opportunities = []

        for term in UPWORK_SEARCH_TERMS[:5]:  # Limit terms to avoid rate limiting
            try:
                cmd = f"cd 'D:\\_CLAUDE-TOOLS\\opportunityengine\\scouts'; python upwork_browser.py '{term}'"
                result = _run_ps(cmd, timeout=60)
                if result.returncode != 0:
                    logger.warning(f"Playwright scrape failed for '{term}': {result.stderr[:200]}")
                    continue

                # Parse JSON output (skip any non-JSON preamble lines)
                stdout = result.stdout.strip()
                # Find the JSON array start
                json_start = stdout.find("[")
                if json_start == -1:
                    json_start = stdout.find("{")
                if json_start == -1:
                    logger.warning(f"No JSON in output for '{term}'")
                    continue

                data = _json.loads(stdout[json_start:])
                if isinstance(data, dict) and data.get("error"):
                    logger.warning(f"Scraper error for '{term}': {data['error']}")
                    if data["error"] == "login_required":
                        logger.error("Upwork login required - need to authenticate in CDP browser")
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
                logger.warning(f"Playwright scrape timed out for '{term}'")
            except Exception as e:
                logger.error(f"Playwright scrape error for '{term}': {e}")

        return opportunities

    def _browser_result_to_opportunity(self, item: dict, search_term: str) -> Optional[Opportunity]:
        """Convert a browser scrape result dict to an Opportunity."""
        title = item.get("title", "").strip()
        if not title:
            return None

        url = item.get("url", "")
        source_id = url.split("?")[0].rstrip("/") if url else f"upwork/{title[:40]}"

        budget_min = item.get("budget_min")
        budget_max = item.get("budget_max")
        skills = item.get("skills", [])

        client_info = {}
        if item.get("client_info"):
            client_info["raw"] = item["client_info"]
        if item.get("proposals_count"):
            client_info["proposals_count"] = item["proposals_count"]

        return Opportunity(
            source="upwork",
            source_id=source_id,
            title=title,
            description=item.get("description", ""),
            budget_min=budget_min,
            budget_max=budget_max,
            currency="USD",
            skills_required=skills,
            competition_level=CompetitionLevel.UNKNOWN,
            client_info=client_info,
            raw_data={"search_term": search_term, "url": url, "posted": item.get("posted", "")},
        )

    def _search_browser(self) -> list[Opportunity]:
        """Fallback: scrape Upwork search results via autonomous-browser."""
        try:
            import sys
            sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/autonomous-browser")
            from browser.stealth_browser import get_browser
            from vault.credentials import get_vault

            browser = get_browser(headless=True)
            browser.start()

            # Restore Upwork session if available
            vault = get_vault()
            cookies = vault.get_cookies("upwork.com")
            if cookies.get("status") == "success":
                browser.set_cookies(cookies["cookies"])

            opportunities = []
            for term in UPWORK_SEARCH_TERMS[:5]:  # Limit to avoid rate limiting
                url = f"https://www.upwork.com/nx/search/jobs/?q={quote_plus(term)}&sort=recency"
                browser.navigate(url)
                import time
                time.sleep(3)  # Wait for JS rendering

                source = browser.get_page_source()
                if source.get("status") == "success":
                    opps = self._parse_search_page(source["html"], term)
                    opportunities.extend(opps)

            browser.stop()
            return opportunities

        except Exception as e:
            logger.error(f"Browser scraping failed: {e}")
            return []

    def _parse_search_page(self, html: str, search_term: str) -> list[Opportunity]:
        """Parse Upwork search results page HTML."""
        opportunities = []

        # Extract job cards from search results
        # Upwork uses data attributes and specific class patterns
        import re
        job_sections = re.findall(
            r'<section[^>]*data-test="JobTile"[^>]*>(.*?)</section>',
            html, re.DOTALL
        )

        for section in job_sections[:self.max_per_term]:
            title_match = re.search(r'<a[^>]*class="[^"]*job-title[^"]*"[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', section)
            if not title_match:
                continue

            link = "https://www.upwork.com" + title_match.group(1)
            title = title_match.group(2).strip()
            desc_match = re.search(r'<span[^>]*data-test="UpCLineClamp[^"]*"[^>]*>(.*?)</span>', section, re.DOTALL)
            description = self._clean_html(desc_match.group(1)) if desc_match else ""

            budget_min, budget_max = self._extract_budget(section)

            opp = Opportunity(
                source="upwork",
                source_id=link.split("?")[0],
                title=title,
                description=description,
                budget_min=budget_min,
                budget_max=budget_max,
                skills_required=self._extract_skills(section),
                client_info=self._extract_client_info(section),
                raw_data={"search_term": search_term, "link": link},
            )
            opportunities.append(opp)

        return opportunities

    def _search_rss(self, search_term: str) -> list[Opportunity]:
        """Fetch and parse Upwork RSS feed for a search term."""
        url = f"{UPWORK_RSS_BASE}?q={quote_plus(search_term)}&sort=recency"

        req = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(req, timeout=15) as resp:
                xml_data = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            logger.error(f"RSS fetch error for '{search_term}': {e}")
            return []

        return self._parse_rss(xml_data, search_term)

    def _parse_rss(self, xml_data: str, search_term: str) -> list[Opportunity]:
        """Parse Upwork RSS XML into Opportunity objects."""
        opportunities = []

        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError as e:
            logger.error(f"RSS XML parse error: {e}")
            return []

        channel = root.find("channel")
        if channel is None:
            return []

        for item in channel.findall("item")[:self.max_per_term]:
            opp = self._item_to_opportunity(item, search_term)
            if opp:
                opportunities.append(opp)

        return opportunities

    def _item_to_opportunity(self, item: ET.Element, search_term: str) -> Optional[Opportunity]:
        """Convert an RSS item to an Opportunity."""
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        description_html = item.findtext("description", "")
        pub_date = item.findtext("pubDate", "")

        if not title or not link:
            return None

        # Parse the HTML description
        description = self._clean_html(description_html)

        # Extract budget from description
        budget_min, budget_max = self._extract_budget(description_html)

        # Extract skills from description
        skills = self._extract_skills(description_html)

        # Extract client info
        client_info = self._extract_client_info(description_html)

        # Generate source_id from link
        source_id = link.split("?")[0].rstrip("/")  # Remove query params

        return Opportunity(
            source="upwork",
            source_id=source_id,
            title=title,
            description=description,
            budget_min=budget_min,
            budget_max=budget_max,
            currency="USD",
            skills_required=skills,
            competition_level=CompetitionLevel.UNKNOWN,
            client_info=client_info,
            raw_data={
                "search_term": search_term,
                "link": link,
                "pub_date": pub_date,
                "description_html": description_html[:3000],
            },
        )

    def _clean_html(self, html: str) -> str:
        """Strip HTML tags and clean up text."""
        text = unescape(html)
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()[:5000]

    def _extract_budget(self, html: str) -> tuple[Optional[float], Optional[float]]:
        """Extract budget range from Upwork description HTML."""
        text = unescape(html)

        # Fixed price: "$500" or "$500 - $1,000"
        fixed = re.search(
            r'Budget[:\s]*\$\s*([\d,]+(?:\.\d{2})?)\s*(?:-\s*\$\s*([\d,]+(?:\.\d{2})?))?',
            text, re.IGNORECASE
        )
        if fixed:
            try:
                lo = float(fixed.group(1).replace(",", ""))
                hi = float(fixed.group(2).replace(",", "")) if fixed.group(2) else lo
                return lo, hi
            except ValueError:
                pass

        # Hourly: "$25 - $50/hr"
        hourly = re.search(
            r'Hourly[:\s]*\$\s*([\d.]+)\s*-\s*\$\s*([\d.]+)',
            text, re.IGNORECASE
        )
        if hourly:
            try:
                lo = float(hourly.group(1))
                hi = float(hourly.group(2))
                # Estimate total at 40 hours
                return lo * 40, hi * 40
            except ValueError:
                pass

        # Generic dollar amounts
        generic = re.search(r'\$\s*([\d,]+(?:\.\d{2})?)', text)
        if generic:
            try:
                amount = float(generic.group(1).replace(",", ""))
                if 50 <= amount <= 500000:
                    return amount, amount
            except ValueError:
                pass

        return None, None

    def _extract_skills(self, html: str) -> list[str]:
        """Extract skill tags from Upwork HTML description."""
        skills = []

        # Upwork includes skills in specific HTML patterns
        skill_matches = re.findall(
            r'<b>Skills</b>:?\s*(.*?)(?:<br|</)',
            html, re.IGNORECASE | re.DOTALL
        )
        if skill_matches:
            raw = self._clean_html(skill_matches[0])
            skills = [s.strip() for s in raw.split(",") if s.strip()]

        # Also check for common Upwork skill tags in links
        link_skills = re.findall(
            r'<a[^>]*>([^<]+)</a>',
            html
        )
        for s in link_skills:
            s = s.strip()
            if s and len(s) < 50 and s not in skills:
                skills.append(s)

        return skills[:20]  # Cap at 20 skills

    def _extract_client_info(self, html: str) -> dict:
        """Extract client metadata from Upwork description."""
        info = {}
        text = unescape(html)

        # Client rating
        rating_match = re.search(r'Rating[:\s]*([\d.]+)', text, re.IGNORECASE)
        if rating_match:
            info["rating"] = float(rating_match.group(1))

        # Client spend
        spend_match = re.search(r'\$\s*([\d,]+(?:K|M)?)\s*(?:total\s*)?spent', text, re.IGNORECASE)
        if spend_match:
            info["total_spent"] = spend_match.group(1)

        # Country
        country_match = re.search(r'Country[:\s]*([A-Za-z\s]+?)(?:\s*<|$)', text, re.IGNORECASE)
        if country_match:
            info["country"] = country_match.group(1).strip()

        # Number of proposals
        proposals_match = re.search(r'(\d+)\s*(?:to\s*\d+\s*)?proposals?', text, re.IGNORECASE)
        if proposals_match:
            info["proposals_count"] = int(proposals_match.group(1))

        return info
