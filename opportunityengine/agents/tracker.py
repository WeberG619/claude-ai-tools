"""Tracker agent - manages pipeline state, follow-ups, and analytics."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from core.database import Database
from core.models import OpportunityStatus, ProposalStatus

logger = logging.getLogger("opportunityengine.agents.tracker")


class Tracker:
    """Manages the opportunity pipeline and triggers follow-up actions."""

    def __init__(self, db: Database):
        self.db = db

    def pipeline_summary(self) -> dict:
        """Get a full pipeline summary with counts and key items."""
        stats = self.db.pipeline_stats()

        # Get actionable items
        needs_proposal = self.db.list_opportunities(
            status=OpportunityStatus.QUALIFIED, limit=10
        )
        needs_approval = self.db.list_proposals(status=ProposalStatus.DRAFT, limit=10)
        needs_submission = self.db.list_proposals(status=ProposalStatus.APPROVED, limit=10)

        return {
            **stats,
            "needs_proposal": len(needs_proposal),
            "needs_approval": len(needs_approval),
            "needs_submission": len(needs_submission),
            "action_items": {
                "draft_proposals_for": [o.id for o in needs_proposal],
                "review_drafts": [p.opportunity_id for p in needs_approval],
                "submit_approved": [p.opportunity_id for p in needs_submission],
            },
        }

    def expire_stale(self, days: int = 14) -> int:
        """Expire opportunities that have been sitting too long without action."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        stale_statuses = [
            OpportunityStatus.DISCOVERED,
            OpportunityStatus.QUALIFIED,
            OpportunityStatus.PROPOSAL_DRAFTED,
        ]
        count = 0

        for status in stale_statuses:
            opps = self.db.list_opportunities(status=status, limit=500)
            for opp in opps:
                if opp.discovered_at < cutoff:
                    self.db.update_opportunity(
                        opp.id,
                        status=OpportunityStatus.EXPIRED,
                        resolved_at=datetime.utcnow().isoformat(),
                    )
                    count += 1

        if count:
            logger.info(f"Expired {count} stale opportunities (>{days} days)")
        return count

    def get_daily_digest(self) -> dict:
        """Build a daily digest of pipeline activity."""
        # Recent hot opportunities
        hot = self.db.list_opportunities(min_score=80, limit=10)
        hot_new = [o for o in hot if o.status == OpportunityStatus.QUALIFIED]

        # Qualified needing proposals
        qualified = self.db.list_opportunities(
            status=OpportunityStatus.QUALIFIED, limit=20
        )

        # Pending proposals
        draft_proposals = self.db.list_proposals(status=ProposalStatus.DRAFT)
        approved_proposals = self.db.list_proposals(status=ProposalStatus.APPROVED)

        # Recent wins/losses
        recent_won = self.db.list_opportunities(status=OpportunityStatus.WON, limit=5)
        recent_lost = self.db.list_opportunities(status=OpportunityStatus.LOST, limit=5)

        # Scan health - dynamic from actual sources in DB
        source_counts = self.db.count_by_source()
        sources = list(source_counts.keys()) or ["freelancer", "github"]
        scan_health = {}
        for source in sources:
            last_scan = self.db.get_last_scan(source)
            if last_scan:
                scan_health[source] = {
                    "last_scan": last_scan.scanned_at,
                    "found": last_scan.opportunities_found,
                    "new": last_scan.new_opportunities,
                    "errors": last_scan.errors or "none",
                }
            else:
                scan_health[source] = {"last_scan": "never", "status": "not configured"}

        stats = self.db.pipeline_stats()

        return {
            "hot_opportunities": hot_new,
            "qualified_count": len(qualified),
            "draft_proposals": len(draft_proposals),
            "approved_proposals": len(approved_proposals),
            "recent_wins": len(recent_won),
            "recent_losses": len(recent_lost),
            "scan_health": scan_health,
            "stats": stats,
        }

    def format_digest_message(self, digest: dict) -> str:
        """Format digest into a Telegram-friendly message."""
        lines = ["📊 *OpportunityEngine Daily Digest*\n"]

        # Pipeline stats
        stats = digest["stats"]
        lines.append(f"📈 Pipeline: {stats['total']} total")
        for status, count in sorted(stats["by_status"].items()):
            lines.append(f"  • {status}: {count}")
        if stats["win_rate"] > 0:
            lines.append(f"🏆 Win rate: {stats['win_rate']}%")

        # Hot opportunities
        hot = digest["hot_opportunities"]
        if hot:
            lines.append(f"\n🔥 *Hot Opportunities ({len(hot)}):*")
            for opp in hot[:5]:
                lines.append(f"  #{opp.id} [{opp.score}] {opp.title[:60]}")
                lines.append(f"    {opp.budget_display} | {opp.source}")

        # Action items
        if digest["qualified_count"]:
            lines.append(f"\n📝 {digest['qualified_count']} qualified - need proposals")
        if digest["draft_proposals"]:
            lines.append(f"✏️ {digest['draft_proposals']} drafts - need review")
        if digest["approved_proposals"]:
            lines.append(f"📤 {digest['approved_proposals']} approved - need submission")

        # Scan health
        lines.append("\n🔍 *Scan Health:*")
        for source, health in digest["scan_health"].items():
            if health.get("last_scan") == "never":
                lines.append(f"  {source}: ⚠️ never scanned")
            else:
                lines.append(
                    f"  {source}: ✅ last={health['last_scan'][:16]} "
                    f"found={health.get('found', 0)} new={health.get('new', 0)}"
                )

        return "\n".join(lines)
