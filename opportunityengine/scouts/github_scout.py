"""GitHub Bounty Scout - finds paid issues and bounties on GitHub."""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Optional

from scouts.base_scout import BaseScout
from core.database import Database
from core.models import Opportunity, CompetitionLevel
from core.config import GITHUB_SEARCH_TERMS, GITHUB_LANGUAGES

logger = logging.getLogger("opportunityengine.scouts.github")


class GitHubScout(BaseScout):
    """Scans GitHub for bounty/paid issues using the gh CLI."""

    def __init__(self, db: Database, max_results_per_query: int = 30):
        super().__init__(db)
        self.max_results = max_results_per_query

    @property
    def source_name(self) -> str:
        return "github"

    def _fetch_opportunities(self) -> list[Opportunity]:
        opportunities = []

        # Search for bounty-labeled issues
        for term in GITHUB_SEARCH_TERMS:
            opps = self._search_issues(term)
            opportunities.extend(opps)

        # Search Algora bounties (common bounty platform)
        algora_opps = self._search_issues("algora bounty", label_filter="bounty")
        opportunities.extend(algora_opps)

        # Dedup within this batch by source_id
        seen = set()
        unique = []
        for opp in opportunities:
            if opp.source_id not in seen:
                seen.add(opp.source_id)
                unique.append(opp)

        return unique

    def _search_issues(
        self,
        query: str,
        label_filter: Optional[str] = None,
    ) -> list[Opportunity]:
        """Search GitHub issues via gh CLI."""
        cmd = [
            "gh", "search", "issues",
            query,
            "--state", "open",
            "--limit", str(self.max_results),
            "--json", "number,title,body,url,repository,labels,createdAt,commentsCount,author",
        ]

        if label_filter:
            cmd.extend(["--label", label_filter])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                logger.warning(f"gh search failed: {result.stderr[:200]}")
                return []

            issues = json.loads(result.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"GitHub search error: {e}")
            return []

        opportunities = []
        for issue in issues:
            opp = self._issue_to_opportunity(issue)
            if opp:
                opportunities.append(opp)

        return opportunities

    def _issue_to_opportunity(self, issue: dict) -> Optional[Opportunity]:
        """Convert a GitHub issue to an Opportunity."""
        repo = issue.get("repository", {})
        repo_name = repo.get("nameWithOwner", "") if isinstance(repo, dict) else str(repo)
        url = issue.get("url", "")
        title = issue.get("title", "")
        body = issue.get("body", "") or ""
        labels = [l.get("name", "") if isinstance(l, dict) else str(l) for l in issue.get("labels", [])]

        # Extract bounty amount from labels or body
        bounty_amount = self._extract_bounty_amount(labels, body, title)

        # Determine competition from comments count
        comments = issue.get("commentsCount", issue.get("comments", 0))
        if isinstance(comments, list):
            comments = len(comments)
        if comments <= 2:
            competition = CompetitionLevel.LOW
        elif comments <= 10:
            competition = CompetitionLevel.MEDIUM
        else:
            competition = CompetitionLevel.HIGH

        # Detect relevant languages/skills from labels
        skills = self._extract_skills(labels, body, repo_name)

        return Opportunity(
            source="github",
            source_id=url or f"{repo_name}#{issue.get('number', '')}",
            title=f"[{repo_name}] {title}",
            description=body[:5000],  # Truncate very long bodies
            budget_min=bounty_amount,
            budget_max=bounty_amount,
            currency="USD",
            skills_required=skills,
            competition_level=competition,
            client_info={
                "repo": repo_name,
                "issue_number": issue.get("number"),
                "labels": labels,
                "comments_count": comments,
                "author": issue.get("author", {}).get("login", "") if isinstance(issue.get("author"), dict) else "",
            },
            raw_data=issue,
        )

    def _extract_bounty_amount(self, labels: list[str], body: str, title: str) -> Optional[float]:
        """Try to extract bounty dollar amount from issue data."""
        import re

        all_text = " ".join(labels) + " " + body + " " + title

        # Common patterns: "$500", "500 USD", "bounty: $200", "$1,000"
        patterns = [
            r'\$\s*([\d,]+(?:\.\d{2})?)',
            r'([\d,]+(?:\.\d{2})?)\s*(?:USD|usd|\$)',
            r'bounty[:\s]*\$?\s*([\d,]+)',
            r'reward[:\s]*\$?\s*([\d,]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, all_text)
            if match:
                try:
                    amount = float(match.group(1).replace(",", ""))
                    if 10 <= amount <= 100000:  # Sanity check
                        return amount
                except ValueError:
                    continue

        # Check Algora-style labels like "💰 $500"
        for label in labels:
            match = re.search(r'(\d[\d,]*)', label)
            if match and any(kw in label.lower() for kw in ["bounty", "$", "💰", "reward"]):
                try:
                    return float(match.group(1).replace(",", ""))
                except ValueError:
                    continue

        return None

    def _extract_skills(self, labels: list[str], body: str, repo_name: str) -> list[str]:
        """Extract relevant skill tags from issue data."""
        skills = []
        text = " ".join(labels).lower() + " " + body[:2000].lower() + " " + repo_name.lower()

        skill_keywords = {
            "Python": ["python", "django", "flask", "fastapi"],
            "TypeScript": ["typescript", "ts"],
            "JavaScript": ["javascript", "node", "react", "nextjs"],
            "C#": ["c#", "csharp", ".net", "dotnet"],
            "Rust": ["rust", "cargo"],
            "Go": [" go ", "golang"],
            "API": ["api", "rest", "graphql"],
            "Docker": ["docker", "container"],
            "AI/ML": ["ai", "llm", "machine learning", "claude", "openai"],
        }

        for skill, keywords in skill_keywords.items():
            if any(kw in text for kw in keywords):
                skills.append(skill)

        return skills
