"""UK Contracts Finder Scout - finds BIM opportunities from UK government procurement.

The UK has the world's strongest BIM mandates (Level 2 BIM required since 2016).
This creates constant demand for BIM technology consulting.
Uses the Contracts Finder API (free, no auth needed).
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

from scouts.base_scout import BaseScout
from core.database import Database
from core.models import Opportunity, CompetitionLevel

logger = logging.getLogger("opportunityengine.scouts.govuk")

# UK Contracts Finder API
CF_API_BASE = "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"

# Search keywords for BIM/tech opportunities
SEARCH_TERMS = [
    "BIM",
    "building information modelling",
    "building information modeling",
    "Revit",
    "digital twin",
    "scan to BIM",
    "3D modelling",
    "CAD automation",
    "construction technology",
]

# Relevance keywords for filtering
RELEVANCE_KEYWORDS = [
    "bim", "revit", "building information", "3d model",
    "scan to bim", "point cloud", "digital twin",
    "navisworks", "dynamo", "autocad",
    "automation", "plugin", "software", "develop",
    "technology", "digital", "information model",
]


class GovUKScout(BaseScout):
    """Scans UK Contracts Finder for BIM/AEC technology contract opportunities."""

    def __init__(self, db: Database, max_results: int = 30):
        super().__init__(db)
        self.max_results = max_results

    @property
    def source_name(self) -> str:
        return "govuk"

    def _fetch_opportunities(self) -> list[Opportunity]:
        opportunities = []

        for term in SEARCH_TERMS:
            try:
                opps = self._search_contracts(term)
                opportunities.extend(opps)
            except Exception as e:
                logger.error(f"GovUK search error for '{term}': {e}")

        # Dedup
        seen = set()
        unique = []
        for opp in opportunities:
            if opp.source_id not in seen:
                seen.add(opp.source_id)
                unique.append(opp)

        return unique

    def _search_contracts(self, keyword: str) -> list[Opportunity]:
        """Search the UK Contracts Finder API."""
        # Look for notices published in the last 90 days
        date_from = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%dT00:00:00Z")

        params = {
            "keyword": keyword,
            "publishedFrom": date_from,
            "size": str(self.max_results),
            "stages": "tender",  # Active tenders only
        }

        url = f"{CF_API_BASE}?{urllib.parse.urlencode(params)}"

        req = urllib.request.Request(url, headers={
            "User-Agent": "OpportunityEngine/1.0 (BIM automation services)",
            "Accept": "application/json",
        })

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            logger.warning(f"GovUK API error: {e}")
            return []
        except json.JSONDecodeError:
            logger.warning("GovUK returned invalid JSON")
            return []

        releases = data.get("releases", [])
        opportunities = []

        for release in releases:
            opp = self._release_to_opportunity(release)
            if opp:
                opportunities.append(opp)

        return opportunities

    def _release_to_opportunity(self, release: dict) -> Optional[Opportunity]:
        """Convert an OCDS release to an Opportunity."""
        tender = release.get("tender", {})
        planning = release.get("planning", {})
        buyer = release.get("buyer", {})

        ocid = release.get("ocid", "")
        title = tender.get("title", "")
        description = tender.get("description", "")

        if not title:
            return None

        # Check relevance
        full_text = f"{title} {description}".lower()
        relevant = any(kw in full_text for kw in RELEVANCE_KEYWORDS)
        if not relevant:
            return None

        # Extract value
        value_obj = tender.get("value", {}) or tender.get("minValue", {})
        budget = None
        currency = "GBP"
        if value_obj:
            budget = value_obj.get("amount")
            currency = value_obj.get("currency", "GBP")

        # Deadline
        tender_period = tender.get("tenderPeriod", {})
        deadline = tender_period.get("endDate", "")

        # Buyer info
        buyer_name = buyer.get("name", "")
        buyer_id = buyer.get("id", "")

        # Documents/links
        documents = tender.get("documents", [])
        doc_urls = [d.get("url", "") for d in documents if d.get("url")]

        # UK government BIM tenders have relatively low international competition
        competition = CompetitionLevel.LOW

        # Skills
        skills = self._extract_skills(full_text)

        source_id = f"govuk:{ocid}"
        notice_url = f"https://www.contractsfinder.service.gov.uk/Notice/{ocid.split('-')[-1] if '-' in ocid else ocid}"

        return Opportunity(
            source="govuk",
            source_id=source_id,
            title=f"[UK Gov] {title[:200]}",
            description=description[:5000],
            budget_min=budget,
            budget_max=budget,
            currency=currency,
            deadline=deadline,
            skills_required=skills,
            competition_level=competition,
            client_info={
                "buyer": buyer_name,
                "buyer_id": buyer_id,
                "country": "UK",
                "type": "government",
            },
            raw_data={
                "url": notice_url,
                "ocid": ocid,
                "documents": doc_urls[:5],
                "published_date": release.get("date", ""),
            },
        )

    def _extract_skills(self, text: str) -> list[str]:
        """Extract skills from UK tender description."""
        skills = []
        skill_map = {
            "BIM": ["bim", "building information model"],
            "Revit": ["revit"],
            "3D Modeling": ["3d model", "point cloud", "scan to bim", "laser scan"],
            "Digital Twin": ["digital twin", "iot", "smart building"],
            "CAD": ["autocad", "cad"],
            "Navisworks": ["navisworks"],
            "Python": ["python"],
            "C#": ["c#", ".net"],
            "GIS": ["gis", "geographic", "mapping"],
            "Construction Tech": ["construction technol", "contech"],
            "IFC": ["ifc", "openbim", "open bim", "buildingsmart"],
        }

        for skill, keywords in skill_map.items():
            if any(kw in text for kw in keywords):
                skills.append(skill)

        return skills
