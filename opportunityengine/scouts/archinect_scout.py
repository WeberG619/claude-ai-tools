"""Archinect Jobs Scout - finds BIM/tech roles from the architecture community.

Archinect is the most established architecture community online.
Tech roles (BIM Manager, Computational Designer) get far fewer applicants
than traditional architecture roles. Uses RSS feed.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
import urllib.error
from typing import Optional
from xml.etree import ElementTree

from scouts.base_scout import BaseScout
from core.database import Database
from core.models import Opportunity, CompetitionLevel

logger = logging.getLogger("opportunityengine.scouts.archinect")

ARCHINECT_RSS = "https://archinect.com/feed/11/jobs"
ARCHINECT_BASE = "https://archinect.com"

# Job titles/keywords that match our BIM automation niche
TECH_KEYWORDS = [
    "bim manager", "bim coordinator", "bim specialist", "bim lead",
    "computational design", "digital practice", "technology",
    "revit", "dynamo", "navisworks", "automation",
    "plugin", "developer", "programmer", "software",
    "digital twin", "data", "scripting", "python",
    "c#", ".net", "api", "integration",
    "vdc", "virtual design", "construction technology",
]

# Keywords that signal consulting/freelance (not just full-time employment)
FREELANCE_SIGNALS = [
    "consultant", "contract", "freelance", "part-time",
    "remote", "project-based", "temporary", "per diem",
]


class ArchinectScout(BaseScout):
    """Scans Archinect job listings for BIM/tech positions."""

    def __init__(self, db: Database, max_results: int = 30):
        super().__init__(db)
        self.max_results = max_results

    @property
    def source_name(self) -> str:
        return "archinect"

    def _fetch_opportunities(self) -> list[Opportunity]:
        """Fetch job listings from Archinect RSS feed."""
        req = urllib.request.Request(ARCHINECT_RSS, headers={
            "User-Agent": "OpportunityEngine/1.0 (BIM automation scout)",
        })

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                xml_data = resp.read()
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            logger.warning(f"Archinect RSS failed: {e}")
            return []

        # Archinect injects a <script> tag after </feed> — strip it
        xml_str = xml_data.decode("utf-8", errors="replace")
        feed_end = xml_str.find("</feed>")
        if feed_end > 0:
            xml_str = xml_str[:feed_end + len("</feed>")]
        xml_data = xml_str.encode("utf-8")

        try:
            root = ElementTree.fromstring(xml_data)
        except ElementTree.ParseError as e:
            logger.warning(f"Archinect RSS parse error: {e}")
            return []

        # Try RSS items first, then Atom entries
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item")
        is_atom = False

        if not items:
            # Atom feed format
            items = root.findall("atom:entry", ns) or root.findall("{http://www.w3.org/2005/Atom}entry")
            is_atom = True

        opportunities = []
        for item in items[:self.max_results * 2]:
            opp = self._item_to_opportunity(item, is_atom, ns)
            if opp:
                opportunities.append(opp)
                if len(opportunities) >= self.max_results:
                    break

        return opportunities

    def _item_to_opportunity(self, item, is_atom: bool = False, ns: dict = None) -> Optional[Opportunity]:
        """Convert an RSS/Atom item to an Opportunity if it's a tech role."""
        if is_atom:
            atom_ns = "http://www.w3.org/2005/Atom"
            title_el = item.find(f"{{{atom_ns}}}title")
            desc_el = item.find(f"{{{atom_ns}}}content") or item.find(f"{{{atom_ns}}}summary")
            link_el = item.find(f"{{{atom_ns}}}link")
            pub_date_el = item.find(f"{{{atom_ns}}}updated") or item.find(f"{{{atom_ns}}}published")

            title = title_el.text if title_el is not None and title_el.text else ""
            description = desc_el.text if desc_el is not None and desc_el.text else ""
            link = link_el.get("href", "") if link_el is not None else ""
            pub_date = pub_date_el.text if pub_date_el is not None and pub_date_el.text else ""
        else:
            title_el = item.find("title")
            desc_el = item.find("description")
            link_el = item.find("link")
            pub_date_el = item.find("pubDate")

            title = title_el.text if title_el is not None and title_el.text else ""
            description = desc_el.text if desc_el is not None and desc_el.text else ""
            link = link_el.text if link_el is not None and link_el.text else ""
            pub_date = pub_date_el.text if pub_date_el is not None and pub_date_el.text else ""

        if not title:
            return None

        # Strip HTML from description
        description_clean = re.sub(r'<[^>]+>', ' ', description).strip()
        full_text = f"{title} {description_clean}".lower()

        # Must match a tech keyword — we don't want generic architecture jobs
        is_tech = any(kw in full_text for kw in TECH_KEYWORDS)
        if not is_tech:
            return None

        # Bonus for freelance/remote signals
        is_freelance = any(kw in full_text for kw in FREELANCE_SIGNALS)

        # Extract salary/budget
        budget = self._extract_salary(full_text)

        # Skills
        skills = self._extract_skills(full_text)

        # Low competition for tech roles on an architecture job board
        competition = CompetitionLevel.LOW

        source_id = f"archinect:{link}" if link else f"archinect:{title[:80]}"

        tag = "[Archinect Contract]" if is_freelance else "[Archinect]"

        return Opportunity(
            source="archinect",
            source_id=source_id,
            title=f"{tag} {title[:200]}",
            description=description_clean[:5000],
            budget_min=budget,
            budget_max=budget,
            currency="USD",
            skills_required=skills,
            competition_level=competition,
            client_info={
                "type": "contract" if is_freelance else "position",
                "proposals_count": 3,  # Low competition estimate
            },
            raw_data={
                "url": link,
                "pub_date": pub_date,
            },
        )

    def _extract_salary(self, text: str) -> Optional[float]:
        """Extract salary or hourly rate from job listing."""
        # Hourly rate
        hourly = re.search(r'\$\s*([\d,]+)\s*(?:[-/]\s*\$?\s*[\d,]+)?\s*(?:per|/|an?)\s*(?:hour|hr)', text)
        if hourly:
            try:
                rate = float(hourly.group(1).replace(",", ""))
                return rate * 160  # Convert to monthly equivalent
            except ValueError:
                pass

        # Annual salary → monthly
        annual = re.search(r'\$\s*([\d,]+)(?:k)?\s*(?:[-/]\s*\$?\s*[\d,]+(?:k)?)?\s*(?:per|/|a)?\s*(?:year|annual|yr)', text)
        if annual:
            try:
                val = annual.group(1).replace(",", "")
                amount = float(val)
                if amount < 500:  # Likely in thousands (e.g., $120k)
                    amount *= 1000
                return amount / 12  # Monthly
            except ValueError:
                pass

        # Generic dollar amount
        generic = re.search(r'\$\s*([\d,]+)', text)
        if generic:
            try:
                amount = float(generic.group(1).replace(",", ""))
                if 500 <= amount <= 500000:
                    return amount
            except ValueError:
                pass

        return None

    def _extract_skills(self, text: str) -> list[str]:
        """Extract skills from job listing."""
        skills = []
        skill_map = {
            "Revit": ["revit"],
            "BIM": ["bim", "building information"],
            "Dynamo": ["dynamo"],
            "Navisworks": ["navisworks"],
            "AutoCAD": ["autocad"],
            "Rhino/Grasshopper": ["rhino", "grasshopper"],
            "Python": ["python"],
            "C#": ["c#", ".net"],
            "Computational Design": ["computational design", "parametric"],
            "VDC": ["vdc", "virtual design and construction"],
            "Digital Twin": ["digital twin"],
            "Automation": ["automation", "automate"],
        }

        for skill, keywords in skill_map.items():
            if any(kw in text for kw in keywords):
                skills.append(skill)

        return skills
