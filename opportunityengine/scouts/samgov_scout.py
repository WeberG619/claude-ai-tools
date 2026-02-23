"""SAM.gov Scout - finds federal contract opportunities for BIM/AEC/tech services.

Uses the official SAM.gov Opportunities API (free, no auth needed for public data).
Searches NAICS codes: 541330 (Engineering), 541511 (Custom Programming), 541512 (Systems Design).
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

logger = logging.getLogger("opportunityengine.scouts.samgov")

# SAM.gov Opportunities Public API
SAM_API_BASE = "https://api.sam.gov/opportunities/v2/search"

# NAICS codes relevant to our services
NAICS_CODES = [
    "541330",  # Engineering Services
    "541511",  # Custom Computer Programming Services
    "541512",  # Computer Systems Design Services
    "541519",  # Other Computer Related Services
    "541690",  # Other Scientific and Technical Consulting
]

# Keywords to search — BIM and automation focus
SEARCH_KEYWORDS = [
    "BIM",
    "building information modeling",
    "Revit",
    "scan to BIM",
    "digital twin",
    "CAD automation",
    "architectural modeling",
    "facility modeling",
    "3D modeling building",
    "construction technology",
]

# Keywords to verify relevance in results
RELEVANCE_KEYWORDS = [
    "bim", "revit", "autocad", "dynamo", "navisworks",
    "scan to bim", "point cloud", "3d model", "digital twin",
    "facility model", "building model", "architectural",
    "automation", "plugin", "software develop", "custom tool",
    "python", "c#", ".net", "api develop", "integration",
]


class SAMGovScout(BaseScout):
    """Scans SAM.gov for federal BIM/AEC technology contract opportunities."""

    def __init__(self, db: Database, api_key: str = "", max_results: int = 50):
        super().__init__(db)
        self.api_key = api_key
        self.max_results = max_results

    @property
    def source_name(self) -> str:
        return "samgov"

    def _fetch_opportunities(self) -> list[Opportunity]:
        opportunities = []

        for keyword in SEARCH_KEYWORDS:
            try:
                opps = self._search_opportunities(keyword)
                opportunities.extend(opps)
            except Exception as e:
                logger.error(f"SAM.gov search error for '{keyword}': {e}")

        # Dedup by source_id
        seen = set()
        unique = []
        for opp in opportunities:
            if opp.source_id not in seen:
                seen.add(opp.source_id)
                unique.append(opp)

        return unique

    def _search_opportunities(self, keyword: str) -> list[Opportunity]:
        """Search SAM.gov opportunities via official API or internal search."""
        if self.api_key:
            return self._search_official_api(keyword)
        return self._search_internal_api(keyword)

    def _search_official_api(self, keyword: str) -> list[Opportunity]:
        """Search via official SAM.gov public API (requires API key)."""
        date_from = (datetime.utcnow() - timedelta(days=90)).strftime("%m/%d/%Y")
        date_to = datetime.utcnow().strftime("%m/%d/%Y")

        params = {
            "api_key": self.api_key,
            "postedFrom": date_from,
            "postedTo": date_to,
            "keyword": keyword,
            "ptype": "o,k",
            "limit": str(self.max_results),
            "offset": "0",
            "ncode": ",".join(NAICS_CODES),
        }

        url = f"{SAM_API_BASE}?{urllib.parse.urlencode(params)}"

        req = urllib.request.Request(url, headers={
            "User-Agent": "OpportunityEngine/1.0 (BIM automation services)",
            "Accept": "application/json",
        })

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            logger.warning(f"SAM.gov official API error: {e}")
            return self._search_internal_api(keyword)
        except json.JSONDecodeError:
            return []

        opps_data = data.get("opportunitiesData", [])
        return [o for o in (self._item_to_opportunity(item) for item in opps_data) if o]

    def _search_internal_api(self, keyword: str) -> list[Opportunity]:
        """Search via SAM.gov internal search API (no key needed, browser-like)."""
        url = (
            f"https://sam.gov/api/prod/sgs/v1/search/"
            f"?index=opp"
            f"&q={urllib.parse.quote(keyword)}"
            f"&sort=-modifiedDate"
            f"&size={self.max_results}"
            f"&mode=search"
            f"&is_active=true"
        )

        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://sam.gov/search/",
            "Origin": "https://sam.gov",
        })

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            logger.warning(f"SAM.gov internal search failed: {e}")
            return []

        embedded = data.get("_embedded", {})
        results = embedded.get("results", [])
        opportunities = []

        for result in results:
            try:
                opp_id = result.get("_id", "")
                title = result.get("title", "")
                desc = result.get("description", "")
                org_list = result.get("organizationHierarchy", [])
                org_name = org_list[0].get("name", "") if org_list else ""
                modified = result.get("modifiedDate", "")
                sol_number = result.get("solicitationNumber", "")

                if not title:
                    continue

                full_text = f"{title} {desc}".lower()
                relevant = any(kw in full_text for kw in RELEVANCE_KEYWORDS)
                if not relevant:
                    continue

                skills = self._extract_skills(full_text)
                source_id = f"samgov:{opp_id}"

                opp = Opportunity(
                    source="samgov",
                    source_id=source_id,
                    title=f"[SAM.gov] {title[:200]}",
                    description=desc[:5000] if desc else title,
                    skills_required=skills,
                    competition_level=CompetitionLevel.LOW,
                    client_info={
                        "organization": org_name,
                        "solicitation_number": sol_number,
                        "type": "government",
                    },
                    raw_data={
                        "url": f"https://sam.gov/opp/{opp_id}/view",
                        "modified_date": modified,
                    },
                )
                opportunities.append(opp)
            except Exception:
                continue

        return opportunities

    def _fallback_search(self, keyword: str) -> list[Opportunity]:
        """Fallback: scrape SAM.gov search results page."""
        import re as _re

        search_url = (
            f"https://sam.gov/api/prod/sgs/v1/search/"
            f"?index=opp"
            f"&q={urllib.parse.quote(keyword)}"
            f"&sort=-modifiedDate"
            f"&size=25"
            f"&mode=search"
            f"&is_active=true"
        )

        req = urllib.request.Request(search_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            logger.debug(f"SAM.gov fallback also failed: {e}")
            return []

        # Parse search results
        embedded = data.get("_embedded", {})
        results = embedded.get("results", [])
        opportunities = []

        for result in results:
            try:
                opp_id = result.get("_id", "")
                title = result.get("title", "")
                desc = result.get("description", "")
                org = result.get("organizationHierarchy", [{}])
                org_name = org[0].get("name", "") if org else ""
                modified = result.get("modifiedDate", "")
                sol_number = result.get("solicitationNumber", "")

                if not title:
                    continue

                full_text = f"{title} {desc}".lower()
                relevant = any(kw in full_text for kw in RELEVANCE_KEYWORDS)
                if not relevant:
                    continue

                source_id = f"samgov:{opp_id}"
                opp = Opportunity(
                    source="samgov",
                    source_id=source_id,
                    title=f"[SAM.gov] {title[:200]}",
                    description=desc[:5000] if desc else title,
                    skills_required=self._extract_skills(full_text),
                    competition_level=CompetitionLevel.LOW,
                    client_info={
                        "organization": org_name,
                        "solicitation_number": sol_number,
                        "type": "government",
                    },
                    raw_data={
                        "url": f"https://sam.gov/opp/{opp_id}/view",
                        "modified_date": modified,
                    },
                )
                opportunities.append(opp)
            except Exception:
                continue

        return opportunities

    def _item_to_opportunity(self, item: dict) -> Optional[Opportunity]:
        """Convert a SAM.gov opportunity to our Opportunity model."""
        notice_id = item.get("noticeId", "")
        title = item.get("title", "")
        description = item.get("description", item.get("additionalInfoLink", ""))
        sol_number = item.get("solicitationNumber", "")
        posted_date = item.get("postedDate", "")
        response_deadline = item.get("responseDeadLine", item.get("archiveDate", ""))
        naics = item.get("naicsCode", "")
        set_aside = item.get("typeOfSetAside", "")
        org_name = item.get("fullParentPathName", item.get("organizationType", ""))
        dept = item.get("department", "")
        ui_link = item.get("uiLink", "")

        if not title:
            return None

        # Check relevance — must mention something we can actually do
        full_text = f"{title} {description}".lower()
        relevant = any(kw in full_text for kw in RELEVANCE_KEYWORDS)
        if not relevant:
            # Still include if it's in our NAICS codes — might be relevant
            if naics not in NAICS_CODES:
                return None

        # Government contracts are low competition for niche BIM work
        competition = CompetitionLevel.LOW
        if set_aside:
            competition = CompetitionLevel.LOW  # Set-asides = even less competition

        # Try to extract budget from description
        budget = self._extract_budget(full_text)

        # Extract skills from description
        skills = self._extract_skills(full_text)

        source_id = f"samgov:{notice_id or sol_number}"

        return Opportunity(
            source="samgov",
            source_id=source_id,
            title=f"[SAM.gov] {title[:200]}",
            description=description[:5000] if description else title,
            budget_min=budget,
            budget_max=budget,
            currency="USD",
            deadline=response_deadline,
            skills_required=skills,
            competition_level=competition,
            client_info={
                "organization": org_name,
                "department": dept,
                "naics": naics,
                "set_aside": set_aside,
                "solicitation_number": sol_number,
            },
            raw_data={
                "url": ui_link or f"https://sam.gov/opp/{notice_id}/view",
                "posted_date": posted_date,
                "response_deadline": response_deadline,
                "notice_id": notice_id,
            },
        )

    def _extract_budget(self, text: str) -> Optional[float]:
        """Extract budget/contract value from text."""
        patterns = [
            r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:million|m)\b',
            r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:thousand|k)\b',
            r'(?:estimated|approximate|total)\s+(?:value|cost|amount)[:\s]*\$?\s*([\d,]+)',
            r'\$\s*([\d,]+(?:\.\d{2})?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    val_str = match.group(1).replace(",", "")
                    amount = float(val_str)
                    if "million" in text[match.start():match.end()+10].lower() or "m" in text[match.start():match.end()+3].lower():
                        amount *= 1_000_000
                    elif "thousand" in text[match.start():match.end()+15].lower() or "k" in text[match.start():match.end()+3].lower():
                        amount *= 1_000
                    if 1000 <= amount <= 50_000_000:
                        return amount
                except ValueError:
                    continue

        return None

    def _extract_skills(self, text: str) -> list[str]:
        """Extract relevant skills from government opportunity description."""
        skills = []
        skill_map = {
            "BIM": ["bim", "building information model", "revit", "navisworks"],
            "CAD": ["autocad", "cad ", "drafting"],
            "3D Modeling": ["3d model", "point cloud", "scan to bim", "laser scan"],
            "Python": ["python", "script", "automat"],
            "C#": ["c#", ".net", "dotnet"],
            "API Development": ["api", "integration", "software develop"],
            "GIS": ["gis", "geographic", "arcgis", "mapping"],
            "Digital Twin": ["digital twin", "iot", "smart building"],
            "Facility Management": ["facility", "asset management", "maximo"],
            "Construction Tech": ["construction", "scheduling", "estimating"],
        }

        for skill, keywords in skill_map.items():
            if any(kw in text for kw in keywords):
                skills.append(skill)

        return skills
