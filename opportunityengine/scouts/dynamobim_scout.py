"""Dynamo BIM Forum Scout - finds paid Dynamo/Revit work from the forum jobs category.

The Dynamo BIM Forum runs on Discourse, which has a built-in JSON API.
People who post here have already tried to solve their problem and failed — they're ready to pay.
This is arguably the single highest-value source for BIM automation work.
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

logger = logging.getLogger("opportunityengine.scouts.dynamobim")

# Discourse JSON API endpoints
FORUM_BASE = "https://forum.dynamobim.com"
JOBS_CATEGORY_ID = 14
JOBS_RSS = f"{FORUM_BASE}/c/jobs/{JOBS_CATEGORY_ID}.rss"
JOBS_JSON = f"{FORUM_BASE}/c/jobs/{JOBS_CATEGORY_ID}.json"

# Also monitor the main forum for "need help" posts that are really paid gigs
HELP_CATEGORIES = [
    ("Revit", f"{FORUM_BASE}/c/15.json"),
    ("Packages", f"{FORUM_BASE}/c/7.json"),
    ("Issues", f"{FORUM_BASE}/c/5.json"),
]

# Signals that someone is willing to pay (not just asking for free help)
PAID_SIGNALS = [
    r"(?:willing|happy|ready)\s+to\s+pay",
    r"(?:hire|hiring|contract|freelanc|consult)",
    r"(?:budget|pay|compensation|rate|hourly)\s*[:\$]",
    r"\$\s*\d+",
    r"(?:paid|paying)\s+(?:work|project|gig|job)",
    r"(?:need|looking for)\s+(?:a |an )?(?:developer|programmer|expert|specialist|consultant)",
    r"(?:anyone available|who can|someone who)",
    r"(?:beyond my|over my|past my)\s+(?:skill|abilit|capabilit)",
    r"(?:too complex|can't figure|struggling|stuck|desperate)",
    r"(?:urgent|asap|deadline)",
]


class DynamoBIMScout(BaseScout):
    """Scans the Dynamo BIM Forum for paid work opportunities."""

    def __init__(self, db: Database, max_topics: int = 30):
        super().__init__(db)
        self.max_topics = max_topics

    @property
    def source_name(self) -> str:
        return "dynamobim"

    def _fetch_opportunities(self) -> list[Opportunity]:
        opportunities = []

        # 1. Check the Jobs category (explicit paid work)
        try:
            jobs = self._fetch_category_topics(JOBS_JSON, is_jobs=True)
            opportunities.extend(jobs)
        except Exception as e:
            logger.error(f"DynamoBIM jobs fetch error: {e}")

        # 2. Check help categories for disguised paid work
        for cat_name, cat_url in HELP_CATEGORIES:
            try:
                help_opps = self._fetch_category_topics(cat_url, is_jobs=False)
                opportunities.extend(help_opps)
            except Exception as e:
                logger.error(f"DynamoBIM {cat_name} fetch error: {e}")

        # Dedup
        seen = set()
        unique = []
        for opp in opportunities:
            if opp.source_id not in seen:
                seen.add(opp.source_id)
                unique.append(opp)

        return unique

    def _fetch_category_topics(self, url: str, is_jobs: bool) -> list[Opportunity]:
        """Fetch topics from a Discourse category via JSON API."""
        req = urllib.request.Request(url, headers={
            "User-Agent": "OpportunityEngine/1.0 (BIM automation scout)",
            "Accept": "application/json",
        })

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
            logger.warning(f"DynamoBIM fetch failed for {url}: {e}")
            return []

        topics = data.get("topic_list", {}).get("topics", [])
        opportunities = []

        for topic in topics[:self.max_topics]:
            opp = self._topic_to_opportunity(topic, is_jobs)
            if opp:
                opportunities.append(opp)

        return opportunities

    def _topic_to_opportunity(self, topic: dict, is_jobs: bool) -> Optional[Opportunity]:
        """Convert a Discourse topic to an Opportunity."""
        topic_id = topic.get("id")
        title = topic.get("title", "")
        slug = topic.get("slug", "")
        excerpt = topic.get("excerpt", topic.get("fancy_title", ""))
        reply_count = topic.get("reply_count", topic.get("posts_count", 1)) - 1
        views = topic.get("views", 0)
        created_at = topic.get("created_at", "")
        pinned = topic.get("pinned", False)

        if not title or pinned:
            return None

        # For non-jobs categories, check if this looks like a paid opportunity
        if not is_jobs:
            full_text = f"{title} {excerpt}".lower()
            is_paid = any(re.search(p, full_text) for p in PAID_SIGNALS)
            if not is_paid:
                return None

        # Fetch the full topic body for better analysis
        description = excerpt or ""
        try:
            description = self._fetch_topic_body(topic_id)
        except Exception:
            pass  # Use excerpt as fallback

        # Competition is very low on this forum
        if reply_count <= 2:
            competition = CompetitionLevel.LOW
        elif reply_count <= 5:
            competition = CompetitionLevel.MEDIUM
        else:
            competition = CompetitionLevel.HIGH

        # Extract budget if mentioned
        budget = self._extract_budget(f"{title} {description}".lower())

        # Skills are always Dynamo/Revit related
        skills = ["Dynamo", "Revit"]
        text_lower = f"{title} {description}".lower()
        if "python" in text_lower:
            skills.append("Python")
        if "c#" in text_lower or "csharp" in text_lower:
            skills.append("C#")
        if any(kw in text_lower for kw in ["api", "plugin", "add-in", "addin"]):
            skills.append("Revit API")
        if any(kw in text_lower for kw in ["automate", "automation", "script"]):
            skills.append("Automation")

        source_id = f"dynamobim:{topic_id}"
        topic_url = f"{FORUM_BASE}/t/{slug}/{topic_id}"

        prefix = "[DynamoBIM Jobs]" if is_jobs else "[DynamoBIM]"

        return Opportunity(
            source="dynamobim",
            source_id=source_id,
            title=f"{prefix} {title[:200]}",
            description=description[:5000],
            budget_min=budget,
            budget_max=budget,
            currency="USD",
            skills_required=skills,
            competition_level=competition,
            client_info={
                "reply_count": reply_count,
                "views": views,
                "proposals_count": reply_count,  # Used by scoring engine
                "is_jobs_category": is_jobs,
            },
            raw_data={
                "url": topic_url,
                "topic_id": topic_id,
                "created_at": created_at,
            },
        )

    def _fetch_topic_body(self, topic_id: int) -> str:
        """Fetch the first post body of a topic."""
        url = f"{FORUM_BASE}/t/{topic_id}.json"
        req = urllib.request.Request(url, headers={
            "User-Agent": "OpportunityEngine/1.0",
            "Accept": "application/json",
        })

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        posts = data.get("post_stream", {}).get("posts", [])
        if posts:
            raw = posts[0].get("cooked", "")
            # Strip HTML tags
            return re.sub(r'<[^>]+>', ' ', raw).strip()
        return ""

    def _extract_budget(self, text: str) -> Optional[float]:
        """Extract budget from topic text."""
        patterns = [
            r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:per|/)\s*(?:hour|hr)',
            r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:budget|total|fixed)',
            r'budget[:\s]*\$?\s*([\d,]+)',
            r'pay(?:ing)?[:\s]*\$?\s*([\d,]+)',
            r'\$\s*([\d,]+(?:\.\d{2})?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    amount = float(match.group(1).replace(",", ""))
                    if 25 <= amount <= 50000:
                        return amount
                except ValueError:
                    continue

        return None
