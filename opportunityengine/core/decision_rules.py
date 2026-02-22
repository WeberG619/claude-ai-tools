"""Decision rules for autonomous opportunity processing.

Defines when the agent acts on its own vs when it holds for human review.
The goal: maximize revenue while minimizing risk of wasted bids/connects.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.models import Opportunity
from core.config import SCORE_HOT, SCORE_QUALIFIED, HOURLY_RATE


class Action(str, Enum):
    """What the agent should do with an opportunity."""
    AUTO_PROPOSE = "auto_propose"       # Draft + submit without asking
    DRAFT_AND_HOLD = "draft_and_hold"   # Draft proposal, wait for human approval
    HOLD_FOR_REVIEW = "hold_for_review" # Flag for human to look at
    SKIP = "skip"                       # Not worth pursuing
    FOLLOW_UP = "follow_up"            # Check status on submitted proposal


@dataclass
class Decision:
    """A decision about what to do with an opportunity."""
    action: Action
    reason: str
    confidence: float  # 0.0-1.0
    auto_bid_amount: Optional[float] = None
    priority: int = 0  # Higher = more urgent (0-10)


# ── Thresholds ──────────────────────────────────────────────────────────
# These control autonomous behavior. Conservative to start, loosen as we win.

# Auto-submit without asking if ALL of these are true
AUTO_SUBMIT_MAX_BID = 1000          # Don't auto-bid more than this
AUTO_SUBMIT_MIN_SCORE = 65          # Qualified is good enough to act
AUTO_SUBMIT_MIN_SKILL_SCORE = 50    # Reasonable skill match
AUTO_SUBMIT_MAX_COMPETITION = 20    # Allow more competitive fields

# Draft but hold for approval
DRAFT_MIN_SCORE = 60                # Worth drafting a proposal

# Connects/credits budget per day (Upwork uses connects, Freelancer uses bids)
DAILY_BID_BUDGET = 10               # Max auto-submissions per day
DAILY_CONNECT_BUDGET = 50           # Max Upwork connects to spend per day

# Follow-up timing
FOLLOW_UP_AFTER_HOURS = 48          # Check on proposals after 2 days
STALE_PROPOSAL_DAYS = 7             # Flag proposals with no response after 7 days


def decide(opp: Opportunity, daily_submissions: int = 0) -> Decision:
    """Make a decision about what to do with an opportunity.

    Args:
        opp: The opportunity to decide on
        daily_submissions: How many auto-submissions already made today

    Returns:
        Decision with action, reason, confidence, and optional bid amount
    """
    score = opp.score or 0
    breakdown = opp.score_breakdown or {}

    # ── Skip conditions ──
    if score < 40:
        return Decision(
            action=Action.SKIP,
            reason=f"Score too low ({score})",
            confidence=0.95,
        )

    if opp.raw_data.get("already_applied"):
        return Decision(
            action=Action.SKIP,
            reason="Already applied",
            confidence=1.0,
        )

    # ── Extract scoring details ──
    skill_score = _get_sub_score(breakdown, "skill_match")
    budget_score = _get_sub_score(breakdown, "budget_roi")
    competition_score = _get_sub_score(breakdown, "competition")

    budget = opp.budget_max or opp.budget_min or 0
    proposals_count = opp.client_info.get("proposals_count", None)

    # ── Auto-submit conditions ──
    can_auto = (
        score >= AUTO_SUBMIT_MIN_SCORE
        and skill_score >= AUTO_SUBMIT_MIN_SKILL_SCORE
        and daily_submissions < DAILY_BID_BUDGET
        and (proposals_count is None or proposals_count <= AUTO_SUBMIT_MAX_COMPETITION)
    )

    if can_auto:
        bid = _calculate_bid(opp)
        if bid and bid <= AUTO_SUBMIT_MAX_BID:
            return Decision(
                action=Action.AUTO_PROPOSE,
                reason=f"High score ({score}), strong skill match, bid ${bid:.0f}",
                confidence=0.8,
                auto_bid_amount=bid,
                priority=8,
            )

    # ── Draft and hold for big opportunities ──
    if score >= SCORE_HOT:
        bid = _calculate_bid(opp)
        return Decision(
            action=Action.DRAFT_AND_HOLD,
            reason=f"Hot opportunity ({score}) - drafting proposal for your review",
            confidence=0.85,
            auto_bid_amount=bid,
            priority=9,
        )

    # ── Draft for qualified opportunities ──
    if score >= DRAFT_MIN_SCORE:
        bid = _calculate_bid(opp)
        return Decision(
            action=Action.DRAFT_AND_HOLD,
            reason=f"Qualified ({score}) - proposal drafted, awaiting approval",
            confidence=0.7,
            auto_bid_amount=bid,
            priority=5 if score >= SCORE_QUALIFIED else 3,
        )

    # ── Hold for review (borderline) ──
    if score >= 50:
        return Decision(
            action=Action.HOLD_FOR_REVIEW,
            reason=f"Borderline ({score}) - needs manual review",
            confidence=0.5,
            priority=1,
        )

    # ── Default skip ──
    return Decision(
        action=Action.SKIP,
        reason=f"Below threshold ({score})",
        confidence=0.9,
    )


def _calculate_bid(opp: Opportunity) -> Optional[float]:
    """Calculate competitive bid amount."""
    budget = opp.budget_max or opp.budget_min
    if not budget or budget <= 0:
        return None

    # For hourly jobs, bid our rate
    if opp.raw_data.get("is_hourly"):
        hourly_max = opp.raw_data.get("hourly_max", 0)
        if hourly_max > 0:
            # Bid slightly below the max to be competitive
            return min(HOURLY_RATE, hourly_max * 0.85)
        return HOURLY_RATE

    # For fixed price: bid at 60% of their max budget for competitiveness
    # but never below our minimum viable rate
    proposals_count = opp.client_info.get("proposals_count", 0)

    if proposals_count and proposals_count > 10:
        # High competition - bid lower to win
        bid = budget * 0.50
    elif proposals_count and proposals_count <= 3:
        # Low competition - bid closer to budget
        bid = budget * 0.80
    else:
        # Medium - standard bid
        bid = budget * 0.65

    # Floor: at least $25/hr estimated
    min_bid = 25 * max(1, (budget / HOURLY_RATE))
    return max(bid, min(min_bid, budget * 0.9))


def _get_sub_score(breakdown: dict, key: str) -> int:
    """Extract a sub-score from the scoring breakdown."""
    data = breakdown.get(key, {})
    if isinstance(data, dict):
        return data.get("score", 0)
    return 0
