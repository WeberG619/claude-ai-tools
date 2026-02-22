"""Qualification scoring engine for opportunities."""

from __future__ import annotations

import re
from typing import Optional

from core.config import (
    SKILLS,
    SKILL_LEVEL_WEIGHTS,
    SCORING_WEIGHTS,
    HOURLY_RATE,
    MIN_ACCEPTABLE_HOURLY,
    PREFERRED_BUDGET_MIN,
    PREFERRED_BUDGET_MAX,
    PORTFOLIO_PRIORITIES,
)
from core.models import Opportunity, CompetitionLevel


def score_opportunity(opp: Opportunity) -> tuple[int, dict]:
    """Score an opportunity from 0-100.

    Returns (total_score, breakdown_dict) where breakdown contains
    individual factor scores and explanations.
    """
    breakdown = {}

    # 1. Skill Match (35%)
    skill_score, skill_detail = _score_skill_match(opp)
    breakdown["skill_match"] = {"score": skill_score, "detail": skill_detail}

    # 2. Budget/ROI (25%)
    budget_score, budget_detail = _score_budget(opp)
    breakdown["budget_roi"] = {"score": budget_score, "detail": budget_detail}

    # 3. Competition (20%)
    comp_score, comp_detail = _score_competition(opp)
    breakdown["competition"] = {"score": comp_score, "detail": comp_detail}

    # 4. Effort Estimate (15%)
    effort_score, effort_detail = _score_effort(opp)
    breakdown["effort"] = {"score": effort_score, "detail": effort_detail}

    # 5. Strategic Fit (5%)
    strat_score, strat_detail = _score_strategic_fit(opp)
    breakdown["strategic_fit"] = {"score": strat_score, "detail": strat_detail}

    # Weighted total
    total = (
        skill_score * SCORING_WEIGHTS["skill_match"]
        + budget_score * SCORING_WEIGHTS["budget_roi"]
        + comp_score * SCORING_WEIGHTS["competition"]
        + effort_score * SCORING_WEIGHTS["effort"]
        + strat_score * SCORING_WEIGHTS["strategic_fit"]
    )

    # Apply job type modifier — penalize manual drafting, boost development/automation
    type_mod, type_detail = _job_type_modifier(opp)
    total += type_mod
    if type_mod != 0:
        breakdown["job_type"] = {"score": type_mod, "detail": type_detail}

    total_score = min(100, max(0, round(total)))
    breakdown["total"] = total_score

    return total_score, breakdown


# ── Drafting vs Development filter ──────────────────────────────────

# Keywords that signal manual drafting/design work (low value, not our niche)
_DRAFTING_SIGNALS = [
    "draw ", "drawing ", "draft ", "drafting", "draftsman", "draftsperson",
    "floor plan design", "house plan", "residential design", "home design",
    "architectural design needed", "create plans", "design a house",
    "design a building", "architectural drawing", "permit drawing",
    "need architect", "licensed architect", "architectural plans",
    "building design", "create architectural", "2d drawing",
    "cad drawing", "need plans", "design for permit",
    "stamped", "stamp", "architect of record",
]

# Keywords that signal development/automation work (high value, our niche)
_DEV_SIGNALS = [
    "plugin", "add-in", "addin", "script", "automate", "automation",
    "api", "integrate", "integration", "develop", "build a tool",
    "custom tool", "workflow", "pipeline", "bot", "agent",
    "mcp", "claude", "llm", "ai system", "machine learning",
    "data extract", "scraping", "web app", "dashboard",
    "python script", "c# develop", "software", "program",
]


def _job_type_modifier(opp: Opportunity) -> tuple[int, str]:
    """Penalize manual drafting jobs, boost development/automation jobs."""
    text = f"{opp.title} {opp.description}".lower()

    drafting_hits = sum(1 for kw in _DRAFTING_SIGNALS if kw in text)
    dev_hits = sum(1 for kw in _DEV_SIGNALS if kw in text)

    # If it's clearly a drafting job with no dev component
    if drafting_hits >= 2 and dev_hits == 0:
        return -30, f"Manual drafting/design job ({drafting_hits} signals) — not our niche"

    if drafting_hits >= 1 and dev_hits == 0:
        return -15, f"Likely manual drafting ({drafting_hits} signals)"

    # If it's clearly a development/automation job
    if dev_hits >= 3:
        return 15, f"Development/automation job ({dev_hits} signals) — our sweet spot"

    if dev_hits >= 1 and drafting_hits == 0:
        return 8, f"Development work ({dev_hits} signals)"

    # Mixed signals — could be either
    if dev_hits >= 1 and drafting_hits >= 1:
        return 0, f"Mixed signals (dev={dev_hits}, drafting={drafting_hits})"

    return 0, "Neutral"


def _score_skill_match(opp: Opportunity) -> tuple[int, str]:
    """Score 0-100 based on how well opportunity matches our skills."""
    text = f"{opp.title} {opp.description}".lower()
    required = [s.lower() for s in opp.skills_required]

    matched_skills = []
    best_level_score = 0.0

    for skill_name, skill_data in SKILLS.items():
        level_weight = SKILL_LEVEL_WEIGHTS[skill_data["level"]]
        for keyword in skill_data["keywords"]:
            kw_lower = keyword.lower()
            # Check required skills list and free text
            if kw_lower in text or any(kw_lower in r for r in required):
                matched_skills.append((skill_name, skill_data["level"]))
                best_level_score = max(best_level_score, level_weight)
                break

    if not matched_skills:
        return 20, "No skill matches found"

    # Score based on number of matches and best match level
    unique_skills = set(s[0] for s in matched_skills)
    count_score = min(100, len(unique_skills) * 25)  # 4+ matches = 100

    # Weight by skill level
    level_scores = []
    for name, level in matched_skills:
        level_scores.append(SKILL_LEVEL_WEIGHTS[level])
    avg_level = sum(level_scores) / len(level_scores)

    score = int(count_score * avg_level)
    detail = ", ".join(f"{s[0]}({s[1]})" for s in matched_skills[:5])
    if len(matched_skills) > 5:
        detail += f" +{len(matched_skills) - 5} more"

    return min(100, score), detail


def _score_budget(opp: Opportunity) -> tuple[int, str]:
    """Score 0-100 based on budget attractiveness and ROI."""
    budget = opp.budget_max or opp.budget_min

    if budget is None:
        return 50, "Budget not specified"

    if budget <= 0:
        return 10, "No budget"

    # Check if it's in the sweet spot
    if PREFERRED_BUDGET_MIN <= budget <= PREFERRED_BUDGET_MAX:
        base_score = 90
        detail = f"${budget:,.0f} - in sweet spot"
    elif budget > PREFERRED_BUDGET_MAX:
        base_score = 80  # Big projects are good but may be complex
        detail = f"${budget:,.0f} - large project"
    elif budget >= 100:
        base_score = 60
        detail = f"${budget:,.0f} - small but viable"
    else:
        base_score = 20
        detail = f"${budget:,.0f} - too small"

    # Estimate effective hourly rate if we can gauge effort
    effort_hours = _estimate_hours(opp)
    if effort_hours and effort_hours > 0:
        effective_rate = budget / effort_hours
        if effective_rate >= HOURLY_RATE:
            base_score = min(100, base_score + 10)
            detail += f" (~${effective_rate:.0f}/hr)"
        elif effective_rate < MIN_ACCEPTABLE_HOURLY:
            base_score = max(10, base_score - 20)
            detail += f" (~${effective_rate:.0f}/hr - low)"

    return base_score, detail


def _score_competition(opp: Opportunity) -> tuple[int, str]:
    """Score 0-100 based on competition level (higher = less competition)."""
    level = opp.competition_level

    if level == CompetitionLevel.LOW:
        return 90, "Low competition"
    elif level == CompetitionLevel.MEDIUM:
        return 60, "Medium competition"
    elif level == CompetitionLevel.HIGH:
        return 30, "High competition"

    # Try to infer from client_info or raw_data
    proposals_count = opp.client_info.get("proposals_count", None)
    if proposals_count is not None:
        if proposals_count <= 5:
            return 85, f"{proposals_count} proposals - low"
        elif proposals_count <= 15:
            return 55, f"{proposals_count} proposals - medium"
        elif proposals_count <= 30:
            return 35, f"{proposals_count} proposals - high"
        else:
            return 15, f"{proposals_count} proposals - very high"

    return 50, "Competition unknown"


def _score_effort(opp: Opportunity) -> tuple[int, str]:
    """Score 0-100 based on estimated effort (prefer manageable scope)."""
    hours = _estimate_hours(opp)

    if hours is None:
        return 50, "Effort unclear"

    # Sweet spot: 5-40 hours
    if 5 <= hours <= 40:
        return 85, f"~{hours}h - ideal scope"
    elif 2 <= hours < 5:
        return 70, f"~{hours}h - quick win"
    elif 40 < hours <= 100:
        return 60, f"~{hours}h - medium project"
    elif hours > 100:
        return 40, f"~{hours}h - large commitment"
    else:
        return 50, f"~{hours}h - very small"


def _score_strategic_fit(opp: Opportunity) -> tuple[int, str]:
    """Score 0-100 based on portfolio fit and strategic value."""
    text = f"{opp.title} {opp.description}".lower()
    reasons = []

    score = 50  # Baseline

    # Check portfolio priorities
    for priority_skill in PORTFOLIO_PRIORITIES:
        skill_data = SKILLS.get(priority_skill, {})
        for keyword in skill_data.get("keywords", []):
            if keyword.lower() in text:
                score += 15
                reasons.append(f"portfolio priority: {priority_skill}")
                break

    # Repeat client potential (look for keywords)
    if any(kw in text for kw in ["ongoing", "long-term", "retainer", "monthly"]):
        score += 10
        reasons.append("repeat potential")

    # Learning value for new tech
    if any(kw in text for kw in ["new technology", "cutting edge", "innovative"]):
        score += 5
        reasons.append("learning value")

    return min(100, score), "; ".join(reasons) if reasons else "Standard fit"


def _estimate_hours(opp: Opportunity) -> Optional[float]:
    """Rough effort estimation from description and budget."""
    text = f"{opp.title} {opp.description}".lower()

    # Look for explicit time mentions
    hour_match = re.search(r'(\d+)\s*(?:hours?|hrs?)', text)
    if hour_match:
        return float(hour_match.group(1))

    week_match = re.search(r'(\d+)\s*(?:weeks?|wks?)', text)
    if week_match:
        return float(week_match.group(1)) * 20  # 20 hrs/week

    day_match = re.search(r'(\d+)\s*(?:days?)', text)
    if day_match:
        return float(day_match.group(1)) * 5  # 5 hrs/day

    # Estimate from budget
    budget = opp.budget_max or opp.budget_min
    if budget:
        return budget / HOURLY_RATE  # Assume market rate

    # Estimate from description length (very rough heuristic)
    desc_len = len(opp.description)
    if desc_len < 200:
        return 5  # Simple task
    elif desc_len < 500:
        return 15
    elif desc_len < 1500:
        return 40
    else:
        return 80

    return None
