"""Autodesk Community Forums Scout - finds paid opportunities hidden in help threads.

Uses the Khoros/Lithium LiQL REST API (public, no auth needed).
Monitors the Revit API, Revit Architecture, Revit MEP, and Dynamo forums
for posts where people need expert help they're willing to pay for.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional

from scouts.base_scout import BaseScout
from core.database import Database
from core.models import Opportunity, CompetitionLevel

logger = logging.getLogger("opportunityengine.scouts.autodesk_forum")

API_BASE = "https://forums.autodesk.com/api/2.0/search"

# Simple keyword searches — LiQL doesn't support complex AND/OR well
# Each query searches one keyword across subject+body
SEARCH_KEYWORDS = [
    "hire",
    "consultant",
    "freelance",
    "custom plugin",
    "custom add-in",
    "automate revit",
    "paid project",
    "need developer",
    "looking for developer",
    "need someone plugin",
    "automation script",
    "willing to pay",
    "budget revit",
]

# Signals that someone wants to hire
HIRING_SIGNALS = [
    r"(?:hire|hiring|contract|freelanc|consult)",
    r"(?:willing|happy|ready)\s+to\s+pay",
    r"(?:budget|compensation|rate)\s*[:\$]",
    r"\$\s*\d+",
    r"(?:paid|paying)\s+(?:work|project|gig|job|opportunity)",
    r"(?:need|looking for)\s+(?:a |an )?(?:developer|programmer|expert|consultant)",
    r"(?:anyone available|who can build|someone who can)",
    r"(?:beyond my|over my|past my)\s+(?:skill|abilit|knowledge)",
    r"(?:too complex|can't figure|struggling with|stuck on|desperate)",
    r"(?:custom |need a )(?:plugin|add-in|addin|tool|script|macro)",
    r"(?:automate|automation)\s+(?:this|our|my|the)",
    r"(?:develop|build|create)\s+(?:a |an )?(?:plugin|tool|script|add-in)",
]


class AutodeskForumScout(BaseScout):
    """Scans Autodesk Community Forums via LiQL API for BIM opportunities."""

    def __init__(self, db: Database, max_per_query: int = 15):
        super().__init__(db)
        self.max_per_query = max_per_query

    @property
    def source_name(self) -> str:
        return "autodesk_forum"

    def _fetch_opportunities(self) -> list[Opportunity]:
        opportunities = []

        for keyword in SEARCH_KEYWORDS:
            try:
                opps = self._search_api(keyword)
                opportunities.extend(opps)
            except Exception as e:
                logger.error(f"Autodesk Forum API error for '{keyword}': {e}")

        # Dedup
        seen = set()
        unique = []
        for opp in opportunities:
            if opp.source_id not in seen:
                seen.add(opp.source_id)
                unique.append(opp)

        return unique

    def _search_api(self, keyword: str) -> list[Opportunity]:
        """Search Autodesk forums via LiQL API with a keyword."""
        query = (
            f'SELECT subject, body, post_time, author.login, view_href '
            f'FROM messages WHERE subject MATCHES "{keyword}" '
            f'ORDER BY post_time DESC LIMIT {self.max_per_query}'
        )

        url = f"{API_BASE}?q={urllib.parse.quote(query)}"

        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            logger.warning(f"Autodesk Forum API failed: {e}")
            return []
        except json.JSONDecodeError:
            logger.warning("Autodesk Forum API returned invalid JSON")
            return []

        if data.get("status") != "success":
            logger.warning(f"Autodesk Forum API non-success: {data.get('message', '?')}")
            return []

        items = data.get("data", {}).get("items", [])
        opportunities = []

        for item in items:
            opp = self._item_to_opportunity(item)
            if opp:
                opportunities.append(opp)

        return opportunities

    def _item_to_opportunity(self, item: dict) -> Optional[Opportunity]:
        """Convert a LiQL result to an Opportunity."""
        subject = item.get("subject", "")
        body = item.get("body", "")
        post_time = item.get("post_time", "")
        view_href = item.get("view_href", "")
        kudos = item.get("kudos", {}).get("count", 0) if isinstance(item.get("kudos"), dict) else 0

        # Author can be nested
        author_obj = item.get("author", {})
        author = author_obj.get("login", "") if isinstance(author_obj, dict) else str(author_obj)

        if not subject:
            return None

        # Strip HTML from body
        body_clean = re.sub(r'<[^>]+>', ' ', body).strip() if body else ""
        full_text = f"{subject} {body_clean}".lower()

        # Check hiring signals
        hiring_score = sum(1 for p in HIRING_SIGNALS if re.search(p, full_text))
        if hiring_score == 0:
            return None

        # Determine which forum this came from
        label = "Revit"  # Default
        if "dynamo" in view_href.lower():
            label = "Dynamo"
        elif "revit-api" in view_href.lower():
            label = "Revit API"
        elif "revit-mep" in view_href.lower():
            label = "Revit MEP"

        # Extract budget
        budget = self._extract_budget(full_text)

        # Skills
        skills = ["Revit"]
        if "dynamo" in full_text:
            skills.append("Dynamo")
        if "api" in full_text or "plugin" in full_text or "add-in" in full_text:
            skills.append("Revit API")
        if "python" in full_text:
            skills.append("Python")
        if "c#" in full_text or "csharp" in full_text:
            skills.append("C#")
        if "navisworks" in full_text:
            skills.append("Navisworks")
        if "automate" in full_text or "automation" in full_text:
            skills.append("Automation")

        # Very low competition
        competition = CompetitionLevel.LOW

        # Build full URL
        link = f"https://forums.autodesk.com{view_href}" if view_href and not view_href.startswith("http") else view_href
        source_id = f"autodesk_forum:{view_href}" if view_href else f"autodesk_forum:{subject[:80]}"

        return Opportunity(
            source="autodesk_forum",
            source_id=source_id,
            title=f"[Autodesk {label}] {subject[:200]}",
            description=body_clean[:5000],
            budget_min=budget,
            budget_max=budget,
            currency="USD",
            skills_required=list(set(skills)),
            competition_level=competition,
            client_info={
                "author": author,
                "forum": label,
                "hiring_signals": hiring_score,
                "kudos": kudos,
                "proposals_count": 0,
            },
            raw_data={
                "url": link,
                "post_time": post_time,
            },
        )

    def _extract_budget(self, text: str) -> Optional[float]:
        """Extract budget from forum post."""
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
