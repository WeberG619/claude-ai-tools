"""Qualification scoring engine for opportunities."""

from __future__ import annotations

import re
from datetime import datetime
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

    # Apply scam/gimmick filter — hard penalty for red flags
    scam_mod, scam_detail = _scam_filter(opp)
    total += scam_mod
    if scam_mod != 0:
        breakdown["scam_filter"] = {"score": scam_mod, "detail": scam_detail}

    # Apply freshness penalty — old posts are likely filled/dead
    fresh_mod, fresh_detail = _freshness_modifier(opp)
    total += fresh_mod
    if fresh_mod != 0:
        breakdown["freshness"] = {"score": fresh_mod, "detail": fresh_detail}

    # Apply not-hiring filter — SEEKING WORK posts from other devs, [OFFER] posts
    nothire_mod, nothire_detail = _not_hiring_filter(opp)
    total += nothire_mod
    if nothire_mod != 0:
        breakdown["not_hiring"] = {"score": nothire_mod, "detail": nothire_detail}

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


# ── Not-Hiring Filter ─────────────────────────────────────────────
# Detect posts from other people OFFERING their services (not hiring).
# These get scraped from HN "Who's Hiring?" threads, Reddit /r/forhire, etc.

_NOT_HIRING_SIGNALS = [
    r"(?:^|\b)seeking\s+work\b",
    r"(?:^|\b)seeking\s+freelanc",
    r"(?:^|\b)available\s+for\s+(?:hire|work|freelance|contract)",
    r"\[offer\]",
    r"(?:^|\b)i(?:'m|\s+am)\s+(?:looking\s+for|seeking)\s+(?:work|projects|clients|gigs|opportunities)",
    r"(?:^|\b)i\s+can\s+help\s+you\s+with\b",
    r"(?:^|\b)(?:my|our)\s+(?:services|skills|portfolio|expertise)\b.*\b(?:available|hire|contact)\b",
    r"(?:^|\b)(?:freelance|contract)\s+(?:developer|designer|engineer|consultant)\s+(?:available|here|looking)",
    r"(?:^|\b)open\s+(?:to|for)\s+(?:new\s+)?(?:opportunities|projects|work|freelance)",
    r"(?:^|\b)contact\s+me\s+at\b.*@",  # "Contact me at email@..." — offering services
]

_HIRING_SIGNALS = [
    r"\[hiring\]",
    r"(?:^|\b)hiring\b",
    r"(?:^|\b)(?:we|i)\s+(?:are|need|want)\s+(?:looking\s+for|hiring|seeking)\s+(?:a\s+)?(?:developer|engineer|freelancer|consultant)",
    r"(?:^|\b)looking\s+for\s+(?:a\s+)?(?:developer|engineer|freelancer|consultant|programmer|coder)",
    r"(?:^|\b)(?:job|position|role)\s+(?:available|opening|posted)",
    r"(?:^|\b)(?:help\s+(?:me|us)\s+(?:build|create|develop|automate))",
]


def _not_hiring_filter(opp: Opportunity) -> tuple[int, str]:
    """Detect posts from OTHER people offering services (not actual job postings)."""
    text = f"{opp.title} {opp.description}".lower()

    not_hiring_hits = sum(1 for p in _NOT_HIRING_SIGNALS if re.search(p, text))
    hiring_hits = sum(1 for p in _HIRING_SIGNALS if re.search(p, text))

    # Clear not-hiring signal with no hiring signal
    if not_hiring_hits >= 2 and hiring_hits == 0:
        return -60, f"Not a job post — someone offering their services ({not_hiring_hits} signals)"
    if not_hiring_hits >= 1 and hiring_hits == 0:
        return -30, f"Likely not hiring — appears to be someone offering services"

    # Mixed signals — slight penalty
    if not_hiring_hits >= 1 and hiring_hits >= 1:
        return -5, "Mixed hiring/offering signals"

    return 0, "Appears to be a real opportunity"


# ── Freshness Filter ───────────────────────────────────────────────

# HN item ID -> approximate date mapping for age estimation.
# HN item IDs are roughly sequential. These are known anchor points.
_HN_ID_ANCHORS = [
    (8_000_000, datetime(2014, 8, 1)),
    (10_000_000, datetime(2015, 7, 1)),
    (12_000_000, datetime(2016, 7, 1)),
    (15_000_000, datetime(2017, 9, 1)),
    (18_000_000, datetime(2018, 10, 1)),
    (21_000_000, datetime(2019, 10, 1)),
    (25_000_000, datetime(2020, 12, 1)),
    (30_000_000, datetime(2022, 2, 1)),
    (35_000_000, datetime(2023, 4, 1)),
    (38_000_000, datetime(2024, 1, 1)),
    (42_000_000, datetime(2025, 1, 1)),
    (44_000_000, datetime(2025, 8, 1)),
    (46_000_000, datetime(2026, 2, 1)),
]


def _estimate_hn_age_days(opp: Opportunity) -> Optional[int]:
    """Estimate age of a HackerNews post from its item ID."""
    if opp.source != "hackernews":
        return None

    # Try to extract item ID from source_id or raw_data URL
    item_id = None
    raw = opp.raw_data or {}
    url = raw.get("url", raw.get("link", ""))
    if "item?id=" in url:
        try:
            item_id = int(url.split("item?id=")[1].split("&")[0])
        except (ValueError, IndexError):
            pass
    if item_id is None and opp.source_id:
        try:
            item_id = int(opp.source_id)
        except (ValueError, TypeError):
            pass

    if item_id is None:
        return None

    # Interpolate between anchor points
    for i in range(len(_HN_ID_ANCHORS) - 1):
        id_lo, date_lo = _HN_ID_ANCHORS[i]
        id_hi, date_hi = _HN_ID_ANCHORS[i + 1]
        if id_lo <= item_id <= id_hi:
            frac = (item_id - id_lo) / (id_hi - id_lo)
            estimated_date = date_lo + (date_hi - date_lo) * frac
            return (datetime.utcnow() - estimated_date).days

    # Below lowest anchor
    if item_id < _HN_ID_ANCHORS[0][0]:
        return (datetime.utcnow() - _HN_ID_ANCHORS[0][1]).days + 365  # older than oldest anchor

    # Above highest anchor — very recent
    return 0


def _freshness_modifier(opp: Opportunity) -> tuple[int, str]:
    """Penalize old posts — they're likely filled or abandoned."""
    age_days = None

    # Try to get age from raw_data timestamps
    raw = opp.raw_data or {}
    for key in ("created_at", "post_time", "pub_date", "posted_date", "published_date"):
        ts = raw.get(key, "")
        if ts and isinstance(ts, str) and len(ts) > 8:
            try:
                # Handle various ISO formats
                clean = ts.split("+")[0].split("Z")[0].rstrip(".")
                dt = datetime.fromisoformat(clean)
                age_days = (datetime.utcnow() - dt).days
                break
            except (ValueError, TypeError):
                continue

    # HN-specific: estimate age from item ID if no timestamp
    if age_days is None:
        hn_age = _estimate_hn_age_days(opp)
        if hn_age is not None:
            age_days = hn_age

    # Fallback: use discovered_at
    if age_days is None:
        try:
            dt = datetime.fromisoformat(opp.discovered_at)
            # If discovered today, assume it's fresh
            discovered_days = (datetime.utcnow() - dt).days
            if discovered_days <= 1:
                return 0, "Just discovered"
        except (ValueError, TypeError):
            pass
        return 0, "Age unknown"

    # Fresh posts get a boost, stale posts get penalized
    if age_days <= 3:
        return 10, f"{age_days}d old — very fresh"
    elif age_days <= 14:
        return 5, f"{age_days}d old — fresh"
    elif age_days <= 30:
        return 0, f"{age_days}d old — recent"
    elif age_days <= 90:
        return -10, f"{age_days}d old — aging"
    elif age_days <= 180:
        return -20, f"{age_days}d old — stale"
    elif age_days <= 365:
        return -30, f"{age_days}d old — likely dead"
    else:
        return -40, f"{age_days}d old — ancient, almost certainly filled"


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


# ── Scam / Gimmick Filter ──────────────────────────────────────────

# Hard red flags — almost certainly a scam or waste of time
_SCAM_HARD = [
    r"earn\s+\$?\d+.*(?:per|a)\s*(?:day|hour|week)",
    r"make\s+\$?\d+.*(?:per|a)\s*(?:day|hour|week)",
    r"guaranteed\s+(?:income|earnings|profit)",
    r"(?:passive|residual)\s+income",
    r"(?:mlm|multi.?level|network\s+marketing|pyramid)",
    r"(?:forex|binary\s+option|crypto\s+trad)",
    r"(?:click\s+farm|click\s+worker|captcha\s+solv)",
    r"(?:money\s+mule|money\s+transfer|wire\s+transfer.*personal)",
    r"(?:send|share)\s+(?:your|personal)\s+(?:bank|account|ssn|id)",
    r"(?:advance|upfront)\s+(?:fee|payment|deposit).*(?:before|first)",
    r"(?:nigerian|lottery|inheritance).*(?:claim|won|prince)",
    r"(?:too\s+good\s+to\s+be\s+true)",
    r"no\s+(?:experience|skills?)\s+(?:needed|required|necessary)",
    r"(?:unlimited\s+earning|sky.?s\s+the\s+limit)",
    r"(?:work\s+from\s+(?:home|anywhere).*\$\d{3,}.*(?:day|hour))",
]

# Soft red flags — suspicious but not necessarily a scam
_SCAM_SOFT = [
    r"(?:just\s+)?(?:need|want)\s+(?:information|details|data)\s+(?:about|on|from)",
    r"(?:research|gather|collect)\s+(?:information|data|details)\s+(?:only|just)",
    r"(?:free|unpaid|volunteer|no\s+pay|exposure|equity\s+only)",
    r"(?:spec\s+work|on\s+spec|speculative)",
    r"(?:contest|competition).*(?:submit|design|logo)",
    r"(?:test|trial)\s+(?:project|task).*(?:unpaid|free)",
    r"(?:pay\s+(?:later|after|upon).*(?:success|results|sales))",
    r"(?:revenue\s+shar|profit\s+shar|commission\s+only)",
    r"(?:need\s+(?:asap|urgently|immediately).*(?:cheap|low\s+cost|budget))",
    r"(?:copy|clone|replicate)\s+(?:this\s+)?(?:website|app|software)",
    r"(?:scrape|hack|crack|bypass|exploit)\s+(?:website|security|password)",
    r"(?:fake|dummy|phishing|spoof)",
    r"(?:unlimited\s+revisions|until\s+(?:i|we)\s+(?:am|are)\s+satisfied)",
]

# Profitability red flags — jobs that can't be profitable
_UNPROFITABLE = [
    r"\$[0-5]\b",  # Budget under $5
    r"budget.*\$[0-9]{1,2}\b",  # Budget under $100 mentioned explicitly
    r"(?:quick|simple|easy)\s+(?:task|job).*\$[0-9]{1,2}\b",
]


def _scam_filter(opp: Opportunity) -> tuple[int, str]:
    """Detect scams, gimmicks, and unprofitable opportunities."""
    text = f"{opp.title} {opp.description}".lower()
    reasons = []

    hard_hits = 0
    for pattern in _SCAM_HARD:
        if re.search(pattern, text):
            hard_hits += 1
            m = re.search(pattern, text)
            reasons.append(f"SCAM: '{m.group()[:40]}'")

    soft_hits = 0
    for pattern in _SCAM_SOFT:
        if re.search(pattern, text):
            soft_hits += 1
            m = re.search(pattern, text)
            reasons.append(f"flag: '{m.group()[:40]}'")

    unprofit_hits = 0
    for pattern in _UNPROFITABLE:
        if re.search(pattern, text):
            unprofit_hits += 1
            reasons.append("unprofitable")

    # Hard scam signals — nuke the score
    if hard_hits >= 2:
        return -80, f"Scam ({hard_hits} hard flags): {'; '.join(reasons[:3])}"
    if hard_hits >= 1:
        return -50, f"Likely scam: {'; '.join(reasons[:3])}"

    # Soft flags stack up
    if soft_hits >= 3:
        return -30, f"Multiple red flags ({soft_hits}): {'; '.join(reasons[:3])}"
    if soft_hits >= 2:
        return -15, f"Suspicious ({soft_hits} flags): {'; '.join(reasons[:3])}"
    if soft_hits >= 1:
        return -5, f"Minor flag: {'; '.join(reasons[:1])}"

    # Unprofitable
    if unprofit_hits >= 1:
        return -20, f"Unprofitable: {'; '.join(reasons[:2])}"

    return 0, "Clean"


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
