"""RemoteOK Scout - finds remote jobs and contracts from RemoteOK.com.

Uses RemoteOK's free JSON API (no authentication needed).
Focuses on freelance-compatible remote positions.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
import urllib.error
from typing import Optional

from scouts.base_scout import BaseScout
from core.database import Database
from core.models import Opportunity, CompetitionLevel

logger = logging.getLogger("opportunityengine.scouts.remoteok")


class RemoteOKScout(BaseScout):
    """Scans RemoteOK.com for remote/freelance-compatible jobs."""

    def __init__(self, db: Database, max_results: int = 50):
        super().__init__(db)
        self.max_results = max_results

    @property
    def source_name(self) -> str:
        return "remoteok"

    def _fetch_opportunities(self) -> list[Opportunity]:
        """Fetch from RemoteOK JSON API."""
        url = "https://remoteok.com/api"

        req = urllib.request.Request(url, headers={
            "User-Agent": "OpportunityEngine/1.0 (automated job scanner)",
        })

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
            logger.error(f"RemoteOK API failed: {e}")
            return []

        # First item is often metadata, skip it
        jobs = data[1:] if len(data) > 1 else data

        opportunities = []
        for job in jobs[:self.max_results]:
            opp = self._job_to_opportunity(job)
            if opp:
                opportunities.append(opp)

        return opportunities

    def _job_to_opportunity(self, job: dict) -> Optional[Opportunity]:
        """Convert a RemoteOK job to an Opportunity."""
        position = job.get("position", "")
        company = job.get("company", "")
        description = job.get("description", "")
        tags = job.get("tags", [])
        slug = job.get("slug", "")
        date = job.get("date", "")
        salary_min = job.get("salary_min")
        salary_max = job.get("salary_max")

        if not position:
            return None

        # Filter for roles we could do (freelance, contract, or matching skills)
        text_lower = f"{position} {description} {' '.join(tags)}".lower()

        # Check if role matches any of our skills
        has_skill_match = self._has_skill_match(text_lower)
        if not has_skill_match:
            return None

        # Convert salary to project budget estimate
        budget_min = None
        budget_max = None
        if salary_min:
            try:
                budget_min = float(salary_min)
            except (ValueError, TypeError):
                pass
        if salary_max:
            try:
                budget_max = float(salary_max)
            except (ValueError, TypeError):
                pass

        # Extract skills from tags
        skills = [t for t in tags if t] if isinstance(tags, list) else []

        source_id = f"remoteok:{slug}" if slug else f"remoteok:{company}/{position[:50]}"
        url = f"https://remoteok.com/remote-jobs/{slug}" if slug else ""

        title = f"{company} - {position}" if company else position

        return Opportunity(
            source="remoteok",
            source_id=source_id,
            title=title,
            description=self._clean_html(description)[:5000],
            budget_min=budget_min,
            budget_max=budget_max,
            currency="USD",
            skills_required=skills[:10],
            competition_level=CompetitionLevel.UNKNOWN,
            client_info={
                "company": company,
                "url": url,
            },
            raw_data={
                "url": url,
                "date": date,
                "slug": slug,
                "original_tags": tags,
                "apply_url": job.get("apply_url", ""),
            },
        )

    def _has_skill_match(self, text: str) -> bool:
        """Check if the job matches any of our core skills."""
        matching_keywords = [
            # Expert skills
            "python", "c#", "csharp", ".net", "revit", "bim", "autocad",
            "automation", "ai agent", "llm", "claude", "mcp",
            # Strong skills
            "javascript", "typescript", "react", "node", "full stack",
            "api", "rest api", "graphql", "sql", "postgresql",
            # General software
            "software engineer", "developer", "programmer", "backend",
            "frontend", "full-stack", "devops",
            # Data/AI
            "data engineer", "machine learning", "data science",
            "web scraping", "automation engineer",
        ]
        return any(kw in text for kw in matching_keywords)

    def _clean_html(self, text: str) -> str:
        """Strip HTML tags from description."""
        return re.sub(r'<[^>]+>', ' ', text).strip()
