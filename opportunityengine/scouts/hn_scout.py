"""HackerNews Scout - finds freelance work from monthly hiring threads.

Uses the HN Algolia API (free, no auth needed).
Scans "Who is Hiring?", "Freelancer? Seeking Freelancer?" threads.
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

logger = logging.getLogger("opportunityengine.scouts.hn")


class HNScout(BaseScout):
    """Scans HackerNews monthly hiring threads for freelance opportunities."""

    def __init__(self, db: Database, max_results: int = 100):
        super().__init__(db)
        self.max_results = max_results

    @property
    def source_name(self) -> str:
        return "hackernews"

    def _fetch_opportunities(self) -> list[Opportunity]:
        opportunities = []

        # Search for freelancer threads and hiring threads
        queries = [
            "Freelancer? Seeking Freelancer?",
            "Who is Hiring?",
        ]

        for query in queries:
            try:
                opps = self._search_hn(query)
                opportunities.extend(opps)
            except Exception as e:
                logger.error(f"HN search error for '{query}': {e}")

        # Dedup
        seen = set()
        unique = []
        for opp in opportunities:
            if opp.source_id not in seen:
                seen.add(opp.source_id)
                unique.append(opp)

        return unique

    def _search_hn(self, query: str) -> list[Opportunity]:
        """Search HN via Algolia API for hiring thread comments."""
        import time

        # Only fetch threads from the last 90 days
        cutoff = int(time.time()) - (90 * 24 * 3600)

        # First, find the most recent thread
        thread_url = (
            f"https://hn.algolia.com/api/v1/search?"
            f"query={urllib.request.quote(query)}"
            f"&tags=story"
            f"&numericFilters=created_at_i>{cutoff}"
            f"&hitsPerPage=3"
        )

        req = urllib.request.Request(thread_url, headers={
            "User-Agent": "OpportunityEngine/1.0",
        })

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            logger.warning(f"HN thread search failed: {e}")
            return []

        hits = data.get("hits", [])
        if not hits:
            return []

        opportunities = []

        # Get comments from the most recent thread
        for thread in hits[:2]:  # Check last 2 threads
            thread_id = thread.get("objectID")
            if not thread_id:
                continue

            comments = self._get_thread_comments(thread_id)
            for comment in comments:
                opp = self._comment_to_opportunity(comment, thread)
                if opp:
                    opportunities.append(opp)

        return opportunities

    def _get_thread_comments(self, thread_id: str) -> list[dict]:
        """Get top-level comments from a thread."""
        url = (
            f"https://hn.algolia.com/api/v1/search?"
            f"tags=comment,story_{thread_id}"
            f"&hitsPerPage={self.max_results}"
        )

        req = urllib.request.Request(url, headers={
            "User-Agent": "OpportunityEngine/1.0",
        })

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            logger.warning(f"HN comments fetch failed: {e}")
            return []

        return data.get("hits", [])

    def _comment_to_opportunity(self, comment: dict, thread: dict) -> Optional[Opportunity]:
        """Convert a HN hiring comment to an Opportunity."""
        text = comment.get("comment_text", "")
        if not text:
            return None

        # Clean HTML tags
        text_clean = re.sub(r'<[^>]+>', ' ', text)
        text_lower = text_clean.lower()

        # For "Freelancer? Seeking Freelancer?" threads,
        # look for "SEEKING FREELANCER" posts (companies looking for help)
        is_freelancer_thread = "freelancer" in thread.get("title", "").lower()

        if is_freelancer_thread:
            # Only want "SEEKING FREELANCER" posts, not "FREELANCER" (offering services)
            first_100 = text_lower[:100]
            if any(kw in first_100 for kw in ["seeking work", "freelancer -", "for hire"]):
                return None
            if not any(kw in first_100 for kw in ["seeking freelancer", "seeking", "looking for", "hiring", "need"]):
                return None
        else:
            # For "Who is Hiring?" - these are all hiring posts, keep them
            # But filter for remote/freelance/contract
            if not any(kw in text_lower for kw in [
                "remote", "freelance", "contract", "part-time", "part time",
                "consulting", "contractor", "anywhere"
            ]):
                return None

        # Extract company/title from first line
        first_line = text_clean.split('\n')[0].strip()[:200]
        if not first_line:
            first_line = text_clean[:200]

        # Extract budget/rate
        budget = self._extract_rate(text_lower)

        # Extract skills
        skills = self._extract_skills(text_lower)

        author = comment.get("author", "")
        comment_id = comment.get("objectID", "")
        source_id = f"hn:{comment_id}"

        return Opportunity(
            source="hackernews",
            source_id=source_id,
            title=first_line,
            description=text_clean[:5000],
            budget_min=budget,
            budget_max=budget,
            currency="USD",
            skills_required=skills,
            competition_level=CompetitionLevel.UNKNOWN,
            client_info={
                "author": author,
                "thread_title": thread.get("title", ""),
                "thread_id": thread.get("objectID", ""),
            },
            raw_data={
                "url": f"https://news.ycombinator.com/item?id={comment_id}",
                "thread_url": f"https://news.ycombinator.com/item?id={thread.get('objectID', '')}",
                "created_at": comment.get("created_at", ""),
            },
        )

    def _extract_rate(self, text: str) -> Optional[float]:
        """Extract salary/rate from text."""
        # Look for hourly rates
        hourly = re.search(r'\$\s*([\d,]+)\s*(?:[-/])\s*\$?\s*([\d,]+)\s*(?:per|/)\s*(?:hour|hr)', text)
        if hourly:
            try:
                return float(hourly.group(2).replace(",", ""))
            except ValueError:
                pass

        rate = re.search(r'\$\s*([\d,]+)\s*(?:per|/)\s*(?:hour|hr)', text)
        if rate:
            try:
                return float(rate.group(1).replace(",", ""))
            except ValueError:
                pass

        # Look for project budgets
        budget = re.search(r'\$\s*([\d,]+(?:k)?)\s*(?:budget|project|fixed|total)', text)
        if budget:
            try:
                val = budget.group(1).replace(",", "")
                if val.endswith("k"):
                    return float(val[:-1]) * 1000
                return float(val)
            except ValueError:
                pass

        return None

    def _extract_skills(self, text: str) -> list[str]:
        """Extract skills from HN comment."""
        skills = []
        skill_map = {
            "Python": ["python", "django", "flask", "fastapi"],
            "JavaScript": ["javascript", "node.js", "react", "vue.js", "angular"],
            "TypeScript": ["typescript"],
            "C#": ["c#", ".net"],
            "Rust": ["rust "],
            "Go": ["golang", " go "],
            "Ruby": ["ruby", "rails"],
            "Java": ["java "],
            "Elixir": ["elixir", "phoenix"],
            "DevOps": ["devops", "docker", "kubernetes", "terraform", "aws"],
            "ML/AI": ["machine learning", "ml ", "ai ", "llm", "gpt", "claude"],
            "Data": ["data engineer", "data science", "analytics"],
            "Frontend": ["frontend", "css", "html", "ui/ux"],
            "Backend": ["backend", "microservices", "api"],
            "Mobile": ["ios", "android", "react native", "flutter"],
            "Blockchain": ["blockchain", "web3", "solidity"],
        }

        for skill, keywords in skill_map.items():
            if any(kw in text for kw in keywords):
                skills.append(skill)

        return skills
