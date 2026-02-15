"""Reddit Scout - finds paid gigs and freelance work on Reddit.

Uses Reddit's public JSON API (no authentication needed).
Scans subreddits: r/forhire, r/freelance, r/slavelabour, r/hiring, r/jobbit
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

logger = logging.getLogger("opportunityengine.scouts.reddit")

# Subreddits to scan - these have [Hiring] tagged posts
SUBREDDITS = [
    "forhire",
    "slavelabour",
    "freelance_forhire",
    "hiring",
    "jobbit",
    "remotejs",
    "PythonJobs",
]

# Keywords that indicate someone is HIRING (not seeking work)
HIRING_PATTERNS = [
    r"\[hiring\]",
    r"\[for hire\].*looking for",
    r"hiring",
    r"looking for.*developer",
    r"looking for.*freelancer",
    r"need.*developer",
    r"need.*help with",
    r"paying.*\$",
    r"\$\d+",
]

# Keywords that indicate seeking work (skip these)
SEEKING_PATTERNS = [
    r"\[for hire\]",
    r"\[seeking work\]",
    r"available for",
    r"looking for work",
    r"seeking.*position",
]


class RedditScout(BaseScout):
    """Scans Reddit for freelance/paid gig posts using the public JSON API."""

    def __init__(self, db: Database, max_per_sub: int = 25):
        super().__init__(db)
        self.max_per_sub = max_per_sub

    @property
    def source_name(self) -> str:
        return "reddit"

    def _fetch_opportunities(self) -> list[Opportunity]:
        opportunities = []

        for sub in SUBREDDITS:
            try:
                opps = self._fetch_subreddit(sub)
                opportunities.extend(opps)
            except Exception as e:
                logger.error(f"Reddit r/{sub} error: {e}")

        # Dedup by source_id
        seen = set()
        unique = []
        for opp in opportunities:
            if opp.source_id not in seen:
                seen.add(opp.source_id)
                unique.append(opp)

        return unique

    def _fetch_subreddit(self, subreddit: str) -> list[Opportunity]:
        """Fetch recent posts from a subreddit via JSON API."""
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={self.max_per_sub}"

        req = urllib.request.Request(url, headers={
            "User-Agent": "OpportunityEngine/1.0 (automated job scanner)",
        })

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to fetch r/{subreddit}: {e}")
            return []

        posts = data.get("data", {}).get("children", [])
        opportunities = []

        for post_wrapper in posts:
            post = post_wrapper.get("data", {})
            opp = self._post_to_opportunity(post, subreddit)
            if opp:
                opportunities.append(opp)

        return opportunities

    def _post_to_opportunity(self, post: dict, subreddit: str) -> Optional[Opportunity]:
        """Convert a Reddit post to an Opportunity if it's a hiring post."""
        title = post.get("title", "")
        selftext = post.get("selftext", "")
        permalink = post.get("permalink", "")
        author = post.get("author", "")
        created_utc = post.get("created_utc", 0)
        score = post.get("score", 0)
        num_comments = post.get("num_comments", 0)

        full_text = f"{title} {selftext}".lower()

        # Skip seeking-work posts
        for pattern in SEEKING_PATTERNS:
            if re.search(pattern, full_text):
                return None

        # Must match a hiring pattern
        is_hiring = False
        for pattern in HIRING_PATTERNS:
            if re.search(pattern, full_text):
                is_hiring = True
                break

        if not is_hiring:
            return None

        # Extract budget
        budget = self._extract_budget(full_text)

        # Extract skills from text
        skills = self._extract_skills(full_text)

        # Competition from comments
        if num_comments <= 5:
            competition = CompetitionLevel.LOW
        elif num_comments <= 20:
            competition = CompetitionLevel.MEDIUM
        else:
            competition = CompetitionLevel.HIGH

        source_id = f"reddit:{permalink}" if permalink else f"reddit:{subreddit}/{title[:50]}"

        return Opportunity(
            source="reddit",
            source_id=source_id,
            title=f"[r/{subreddit}] {title[:200]}",
            description=selftext[:5000],
            budget_min=budget,
            budget_max=budget,
            currency="USD",
            skills_required=skills,
            competition_level=competition,
            client_info={
                "author": author,
                "subreddit": subreddit,
                "post_score": score,
                "num_comments": num_comments,
                "proposals_count": num_comments,  # Used by decision engine
            },
            raw_data={
                "permalink": permalink,
                "url": f"https://reddit.com{permalink}",
                "created_utc": created_utc,
            },
        )

    def _extract_budget(self, text: str) -> Optional[float]:
        """Extract budget/payment from post text."""
        patterns = [
            r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:per|/)\s*(?:hour|hr)',
            r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:budget|total|fixed|flat)',
            r'budget[:\s]*\$?\s*([\d,]+)',
            r'pay(?:ing)?[:\s]*\$?\s*([\d,]+)',
            r'\$\s*([\d,]+(?:\.\d{2})?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    amount = float(match.group(1).replace(",", ""))
                    if 5 <= amount <= 100000:
                        return amount
                except ValueError:
                    continue

        return None

    def _extract_skills(self, text: str) -> list[str]:
        """Extract skill tags from text."""
        skills = []
        skill_map = {
            "Python": ["python", "django", "flask", "fastapi"],
            "JavaScript": ["javascript", "node.js", "nodejs", "react", "vue", "angular"],
            "TypeScript": ["typescript"],
            "C#": ["c#", "csharp", ".net", "dotnet", "unity"],
            "PHP": ["php", "laravel", "wordpress"],
            "Ruby": ["ruby", "rails"],
            "Java": ["java ", "spring"],
            "Go": ["golang"],
            "Rust": ["rust "],
            "SQL": ["sql", "database", "postgresql", "mysql"],
            "AWS": ["aws", "amazon web services"],
            "DevOps": ["devops", "docker", "kubernetes", "ci/cd"],
            "AI/ML": ["ai", "machine learning", "llm", "gpt", "claude", "chatbot"],
            "Web Scraping": ["scraping", "scrapy", "selenium", "puppeteer"],
            "Data": ["data analysis", "data science", "pandas", "excel automation"],
            "Mobile": ["ios", "android", "react native", "flutter"],
            "Automation": ["automation", "bot", "scripting", "rpa"],
            "API": ["api", "rest", "graphql"],
            "Revit": ["revit", "bim", "autocad"],
        }

        for skill, keywords in skill_map.items():
            if any(kw in text for kw in keywords):
                skills.append(skill)

        return skills
