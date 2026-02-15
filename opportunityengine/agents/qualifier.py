"""Qualifier agent - scores and classifies discovered opportunities."""

from __future__ import annotations

import json
import logging
from datetime import datetime

from core.database import Database
from core.scoring import score_opportunity
from core.models import Opportunity, OpportunityStatus
from core.config import SCORE_HOT, SCORE_QUALIFIED, SCORE_LOG_ONLY

logger = logging.getLogger("opportunityengine.agents.qualifier")


class Qualifier:
    """Scores new opportunities and updates their status."""

    def __init__(self, db: Database):
        self.db = db

    def qualify_all_new(self) -> dict:
        """Score all discovered (unscored) opportunities.

        Returns summary: {hot: [...], qualified: [...], logged: int, dismissed: int}
        """
        new_opps = self.db.list_opportunities(status=OpportunityStatus.DISCOVERED, limit=10000)
        hot = []
        qualified = []
        logged = 0
        dismissed = 0

        for opp in new_opps:
            result = self.qualify(opp)
            if result == "hot":
                hot.append(opp)
            elif result == "qualified":
                qualified.append(opp)
            elif result == "logged":
                logged += 1
            else:
                dismissed += 1

        logger.info(
            f"Qualified {len(new_opps)} opportunities: "
            f"{len(hot)} hot, {len(qualified)} qualified, "
            f"{logged} logged, {dismissed} dismissed"
        )

        return {
            "hot": hot,
            "qualified": qualified,
            "logged": logged,
            "dismissed": dismissed,
            "total": len(new_opps),
        }

    def qualify(self, opp: Opportunity) -> str:
        """Score a single opportunity and update its status.

        Returns classification: 'hot', 'qualified', 'logged', or 'dismissed'.
        """
        score, breakdown = score_opportunity(opp)
        now = datetime.utcnow().isoformat()

        opp.score = score
        opp.score_breakdown = breakdown

        if score >= SCORE_HOT:
            classification = "hot"
            new_status = OpportunityStatus.QUALIFIED
        elif score >= SCORE_QUALIFIED:
            classification = "qualified"
            new_status = OpportunityStatus.QUALIFIED
        elif score >= SCORE_LOG_ONLY:
            classification = "logged"
            new_status = OpportunityStatus.DISCOVERED  # Keep as discovered
        else:
            classification = "dismissed"
            new_status = OpportunityStatus.DISMISSED

        self.db.update_opportunity(
            opp.id,
            score=score,
            score_breakdown=json.dumps(breakdown),
            status=new_status,
            qualified_at=now if new_status == OpportunityStatus.QUALIFIED else None,
            notes=_format_breakdown(breakdown),
        )

        logger.debug(
            f"[{opp.source}] '{opp.title[:50]}' -> score={score} ({classification})"
        )

        return classification

    def rescore(self, opp_id: int) -> tuple[int, dict]:
        """Re-score an existing opportunity (e.g., after config change)."""
        opp = self.db.get_opportunity(opp_id)
        if not opp:
            raise ValueError(f"Opportunity {opp_id} not found")

        score, breakdown = score_opportunity(opp)
        self.db.update_opportunity(
            opp_id,
            score=score,
            score_breakdown=json.dumps(breakdown),
            notes=_format_breakdown(breakdown),
        )
        return score, breakdown


def _format_breakdown(breakdown: dict) -> str:
    """Format score breakdown as human-readable text."""
    lines = []
    for key, data in breakdown.items():
        if key == "total":
            continue
        if isinstance(data, dict):
            lines.append(f"{key}: {data.get('score', '?')}/100 - {data.get('detail', '')}")
    return "\n".join(lines)
