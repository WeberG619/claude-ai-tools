"""CAD Crowd Scout - BIM/CAD specific freelance marketplace.

Far fewer freelancers than Upwork. Clients here specifically need CAD/BIM work.
5-15 bids per project versus 50+ on Upwork.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
import urllib.error
from typing import Optional
from html.parser import HTMLParser

from scouts.base_scout import BaseScout
from core.database import Database
from core.models import Opportunity, CompetitionLevel

logger = logging.getLogger("opportunityengine.scouts.cadcrowd")

CADCROWD_BASE = "https://www.cadcrowd.com"
# Project categories relevant to our work
PROJECT_URLS = [
    f"{CADCROWD_BASE}/projects",
]

# Keywords that match our BIM/automation niche
NICHE_KEYWORDS = [
    "revit", "bim", "dynamo", "navisworks", "autocad",
    "plugin", "add-in", "automation", "script", "api",
    "3d model", "scan to bim", "point cloud",
    "architectural", "mep", "structural",
    "python", "c#", ".net",
    "ifc", "cobiee",
]


class _ProjectListParser(HTMLParser):
    """Minimal HTML parser to extract project cards from CAD Crowd listings."""

    def __init__(self):
        super().__init__()
        self.projects = []
        self._current = None
        self._in_title = False
        self._in_desc = False
        self._in_budget = False
        self._in_bids = False
        self._capture_text = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")
        href = attrs_dict.get("href", "")

        if tag == "a" and "project-title" in cls:
            self._current = {"title": "", "url": href, "description": "", "budget": "", "bids": ""}
            self._in_title = True
        elif tag == "div" and "project-description" in cls:
            self._in_desc = True
        elif tag == "span" and "project-budget" in cls:
            self._in_budget = True
        elif tag == "span" and ("bid-count" in cls or "project-bids" in cls):
            self._in_bids = True

    def handle_endtag(self, tag):
        if self._in_title and tag == "a":
            if self._current:
                self._current["title"] = self._capture_text.strip()
            self._in_title = False
            self._capture_text = ""
        elif self._in_desc and tag == "div":
            if self._current:
                self._current["description"] = self._capture_text.strip()
            self._in_desc = False
            self._capture_text = ""
        elif self._in_budget and tag == "span":
            if self._current:
                self._current["budget"] = self._capture_text.strip()
            self._in_budget = False
            self._capture_text = ""
        elif self._in_bids and tag == "span":
            if self._current:
                self._current["bids"] = self._capture_text.strip()
                self.projects.append(self._current)
                self._current = None
            self._in_bids = False
            self._capture_text = ""

    def handle_data(self, data):
        if any([self._in_title, self._in_desc, self._in_budget, self._in_bids]):
            self._capture_text += data


class CADCrowdScout(BaseScout):
    """Scans CAD Crowd for BIM/CAD freelance projects."""

    def __init__(self, db: Database, max_per_page: int = 20):
        super().__init__(db)
        self.max_per_page = max_per_page

    @property
    def source_name(self) -> str:
        return "cadcrowd"

    def _fetch_opportunities(self) -> list[Opportunity]:
        opportunities = []

        for url in PROJECT_URLS:
            try:
                opps = self._scrape_projects(url)
                opportunities.extend(opps)
            except Exception as e:
                logger.error(f"CAD Crowd scrape error for {url}: {e}")

        # Dedup
        seen = set()
        unique = []
        for opp in opportunities:
            if opp.source_id not in seen:
                seen.add(opp.source_id)
                unique.append(opp)

        return unique

    def _scrape_projects(self, url: str) -> list[Opportunity]:
        """Scrape project listings from a CAD Crowd category page."""
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html",
        })

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            logger.warning(f"CAD Crowd fetch failed: {e}")
            return []

        # Parse project listings
        parser = _ProjectListParser()
        try:
            parser.feed(html)
        except Exception as e:
            logger.warning(f"CAD Crowd parse error: {e}")
            # Fallback: regex extraction
            return self._regex_extract(html)

        opportunities = []
        for project in parser.projects[:self.max_per_page]:
            opp = self._project_to_opportunity(project)
            if opp:
                opportunities.append(opp)

        # If HTML parser found nothing, try regex fallback
        if not opportunities:
            return self._regex_extract(html)

        return opportunities

    def _regex_extract(self, html: str) -> list[Opportunity]:
        """Fallback regex extraction if HTML parser doesn't match the structure."""
        # Look for project links and titles in the HTML
        pattern = r'href="(/projects?/[^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)

        opportunities = []
        for href, title in matches[:self.max_per_page]:
            title = title.strip()
            if not title or len(title) < 10:
                continue

            full_text = title.lower()
            # Only include if it matches our niche
            if not any(kw in full_text for kw in NICHE_KEYWORDS):
                continue

            source_id = f"cadcrowd:{href}"
            project_url = f"{CADCROWD_BASE}{href}" if href.startswith("/") else href

            opp = Opportunity(
                source="cadcrowd",
                source_id=source_id,
                title=f"[CAD Crowd] {title[:200]}",
                description=title,
                skills_required=self._extract_skills(full_text),
                competition_level=CompetitionLevel.MEDIUM,
                client_info={"proposals_count": 10},  # Estimate
                raw_data={"url": project_url},
            )
            opportunities.append(opp)

        return opportunities

    def _project_to_opportunity(self, project: dict) -> Optional[Opportunity]:
        """Convert a scraped project to an Opportunity."""
        title = project.get("title", "")
        description = project.get("description", "")
        budget_str = project.get("budget", "")
        bids_str = project.get("bids", "")
        url = project.get("url", "")

        if not title:
            return None

        full_text = f"{title} {description}".lower()

        # Filter for relevance to our niche
        relevant = any(kw in full_text for kw in NICHE_KEYWORDS)
        if not relevant:
            return None

        # Parse budget
        budget = self._parse_budget(budget_str)

        # Parse bid count for competition
        bid_count = 0
        bid_match = re.search(r'(\d+)', bids_str)
        if bid_match:
            bid_count = int(bid_match.group(1))

        if bid_count <= 5:
            competition = CompetitionLevel.LOW
        elif bid_count <= 15:
            competition = CompetitionLevel.MEDIUM
        else:
            competition = CompetitionLevel.HIGH

        # Skills
        skills = self._extract_skills(full_text)

        source_id = f"cadcrowd:{url or title[:80]}"
        project_url = f"{CADCROWD_BASE}{url}" if url and url.startswith("/") else url

        return Opportunity(
            source="cadcrowd",
            source_id=source_id,
            title=f"[CAD Crowd] {title[:200]}",
            description=description[:5000] if description else title,
            budget_min=budget,
            budget_max=budget,
            currency="USD",
            skills_required=skills,
            competition_level=competition,
            client_info={
                "bid_count": bid_count,
                "proposals_count": bid_count,
            },
            raw_data={"url": project_url},
        )

    def _parse_budget(self, budget_str: str) -> Optional[float]:
        """Parse budget string like '$500 - $1,000' or '$5,000'."""
        if not budget_str:
            return None

        # Try to find the max value
        amounts = re.findall(r'\$?\s*([\d,]+)', budget_str)
        if amounts:
            try:
                # Use the highest value
                values = [float(a.replace(",", "")) for a in amounts]
                return max(values)
            except ValueError:
                pass
        return None

    def _extract_skills(self, text: str) -> list[str]:
        """Extract skills from project text."""
        skills = []
        skill_map = {
            "Revit": ["revit"],
            "BIM": ["bim", "building information"],
            "AutoCAD": ["autocad"],
            "Dynamo": ["dynamo"],
            "3D Modeling": ["3d model", "modeling", "modelling"],
            "Architecture": ["architectural", "architecture"],
            "MEP": ["mep", "mechanical", "electrical", "plumbing"],
            "Structural": ["structural"],
            "Python": ["python"],
            "C#": ["c#", ".net"],
            "Automation": ["automation", "automate", "script"],
        }

        for skill, keywords in skill_map.items():
            if any(kw in text for kw in keywords):
                skills.append(skill)

        return skills
