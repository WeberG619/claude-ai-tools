#!/usr/bin/env python3
"""OpportunityEngine CLI - `oe` command interface."""

from __future__ import annotations

import argparse
import sys
import os

from core.database import Database, DEFAULT_DB_PATH
from core.models import OpportunityStatus, ProposalStatus
from core.config import SCORE_HOT, SCORE_QUALIFIED


def get_db() -> Database:
    return Database(os.environ.get("OE_DB_PATH", DEFAULT_DB_PATH))


# ── Scan ─────────────────────────────────────────────────────────────

def cmd_scan(args):
    """Run scouts to discover opportunities."""
    db = get_db()
    sources = []

    if args.all or args.source == "all":
        sources = ["freelancer", "github", "reddit", "hackernews", "remoteok"]
    elif args.source:
        sources = [args.source]
    else:
        print("Specify --source <name> or --all")
        return

    for source in sources:
        print(f"🔍 Scanning {source}...")
        try:
            if source == "upwork":
                from scouts.upwork_scout import UpworkScout
                scout = UpworkScout(db)
            elif source == "github":
                from scouts.github_scout import GitHubScout
                scout = GitHubScout(db)
            elif source == "freelancer":
                from scouts.freelancer_scout import FreelancerScout
                scout = FreelancerScout(db)
            elif source == "reddit":
                from scouts.reddit_scout import RedditScout
                scout = RedditScout(db)
            elif source == "hackernews":
                from scouts.hn_scout import HNScout
                scout = HNScout(db)
            elif source == "remoteok":
                from scouts.remoteok_scout import RemoteOKScout
                scout = RemoteOKScout(db)
            else:
                print(f"  Unknown source: {source}")
                continue

            log = scout.scan()
            print(
                f"  Found {log.opportunities_found}, "
                f"{log.new_opportunities} new, "
                f"{log.duration_ms}ms"
            )
            if log.errors:
                print(f"  Errors: {log.errors}")
        except Exception as e:
            print(f"  Error: {e}")

    # Auto-qualify new discoveries
    from agents.qualifier import Qualifier
    qualifier = Qualifier(db)
    result = qualifier.qualify_all_new()
    if result["total"]:
        print(
            f"\n📊 Qualified: {result['total']} total - "
            f"🔥 {len(result['hot'])} hot, "
            f"✅ {len(result['qualified'])} qualified, "
            f"📝 {result['logged']} logged, "
            f"❌ {result['dismissed']} dismissed"
        )

        # Alert for hot opportunities
        for opp in result["hot"]:
            print(f"\n  🔥 HOT [{opp.score}]: {opp.title}")
            print(f"     {opp.budget_display} | {opp.source}")
            _try_notify(opp)

    db.close()


def _try_notify(opp):
    """Send notification for hot opportunities."""
    try:
        sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/autonomous-agent")
        from core.notifier import Notifier
        import asyncio

        notifier = Notifier()
        msg = (
            f"🔥 Hot Opportunity [{opp.score}/100]\n\n"
            f"{opp.title}\n"
            f"Budget: {opp.budget_display}\n"
            f"Source: {opp.source}\n"
            f"Skills: {', '.join(opp.skills_required[:5])}\n\n"
            f"Run: oe show {opp.id}"
        )
        asyncio.run(notifier.send("Hot Opportunity", msg, priority="high"))
    except Exception:
        pass  # Notification is best-effort


# ── Pipeline ─────────────────────────────────────────────────────────

def cmd_pipeline(args):
    """Show pipeline overview."""
    db = get_db()
    from agents.tracker import Tracker
    tracker = Tracker(db)
    summary = tracker.pipeline_summary()

    print("═══ OpportunityEngine Pipeline ═══\n")

    # Funnel
    status_order = [
        ("discovered", "🔍"),
        ("qualified", "✅"),
        ("proposal_drafted", "✏️"),
        ("submitted", "📤"),
        ("won", "🏆"),
        ("lost", "❌"),
        ("expired", "⏰"),
        ("dismissed", "🚫"),
    ]

    by_status = summary.get("by_status", {})
    total = summary.get("total", 0)
    for status, icon in status_order:
        count = by_status.get(status, 0)
        if count > 0:
            bar = "█" * min(50, count)
            print(f"  {icon} {status:20s} {count:4d}  {bar}")

    print(f"\n  Total: {total}")
    if summary.get("win_rate", 0) > 0:
        print(f"  Win rate: {summary['win_rate']}%")
    print(f"  Proposals submitted: {summary.get('proposals_submitted', 0)}")

    # Action items
    ai = summary.get("action_items", {})
    actions = []
    if ai.get("draft_proposals_for"):
        actions.append(f"  📝 Draft proposals for: {ai['draft_proposals_for']}")
    if ai.get("review_drafts"):
        actions.append(f"  👀 Review drafts: {ai['review_drafts']}")
    if ai.get("submit_approved"):
        actions.append(f"  📤 Submit approved: {ai['submit_approved']}")

    if actions:
        print("\n📋 Action Items:")
        for a in actions:
            print(a)

    db.close()


# ── List ─────────────────────────────────────────────────────────────

def cmd_list(args):
    """List opportunities with optional filters."""
    db = get_db()
    opps = db.list_opportunities(
        status=args.status,
        source=args.source,
        min_score=args.min_score or 0,
        limit=args.limit,
    )

    if not opps:
        print("No opportunities found.")
        db.close()
        return

    print(f"\n{'ID':>5}  {'Score':>5}  {'Status':12s}  {'Source':8s}  {'Budget':>14s}  Title")
    print("-" * 90)

    for opp in opps:
        title = opp.title[:45] + "..." if len(opp.title) > 48 else opp.title
        print(
            f"{opp.id:>5}  "
            f"{opp.score:>5}  "
            f"{opp.status:12s}  "
            f"{opp.source:8s}  "
            f"{opp.budget_display:>14s}  "
            f"{title}"
        )

    print(f"\n{len(opps)} opportunities shown")
    db.close()


# ── Show ─────────────────────────────────────────────────────────────

def cmd_show(args):
    """Show detailed opportunity info."""
    db = get_db()
    opp = db.get_opportunity(args.id)

    if not opp:
        print(f"Opportunity #{args.id} not found.")
        db.close()
        return

    print(f"\n═══ Opportunity #{opp.id} ═══")
    print(f"Title:       {opp.title}")
    print(f"Source:      {opp.source}")
    print(f"Source ID:   {opp.source_id}")
    print(f"Status:      {opp.status}")
    print(f"Score:       {opp.score}/100")
    print(f"Budget:      {opp.budget_display}")
    print(f"Discovered:  {opp.discovered_at}")
    if opp.deadline:
        print(f"Deadline:    {opp.deadline}")
    if opp.skills_required:
        print(f"Skills:      {', '.join(opp.skills_required)}")
    if opp.competition_level and opp.competition_level != "unknown":
        print(f"Competition: {opp.competition_level}")

    print(f"\n── Description ──")
    print(opp.description[:2000] if opp.description else "(no description)")

    if opp.notes:
        print(f"\n── Score Breakdown ──")
        print(opp.notes)

    if opp.client_info:
        print(f"\n── Client Info ──")
        for k, v in opp.client_info.items():
            print(f"  {k}: {v}")

    # Show proposal if exists
    prop = db.get_proposal_for_opportunity(opp.id)
    if prop:
        print(f"\n── Proposal (#{prop.id}) ──")
        print(f"Status:   {prop.status}")
        print(f"Template: {prop.template_used}")
        print(f"Pricing:  {prop.pricing}")
        if args.full:
            print(f"\n{prop.content}")

    db.close()


# ── Propose ──────────────────────────────────────────────────────────

def cmd_propose(args):
    """Draft a proposal for an opportunity."""
    db = get_db()
    from agents.proposal_agent import ProposalAgent
    agent = ProposalAgent(db)

    try:
        prop = agent.draft_proposal(args.id)
        print(f"\n✏️ Proposal drafted for opportunity #{args.id}")
        print(f"   Template: {prop.template_used}")
        print(f"   Pricing:  {prop.pricing}")
        print(f"\n{prop.content}")
        print(f"\nRun `oe approve {args.id}` to approve for submission.")
    except ValueError as e:
        print(f"Error: {e}")

    db.close()


# ── Approve ──────────────────────────────────────────────────────────

def cmd_approve(args):
    """Approve a proposal for submission."""
    db = get_db()
    from agents.proposal_agent import ProposalAgent
    agent = ProposalAgent(db)

    try:
        prop = agent.approve_proposal(args.id)
        print(f"✅ Proposal for opportunity #{args.id} approved")
        print(f"Run `oe submit {args.id}` to mark as submitted.")
    except ValueError as e:
        print(f"Error: {e}")

    db.close()


# ── Submit ───────────────────────────────────────────────────────────

def cmd_submit(args):
    """Submit a proposal to the actual platform."""
    db = get_db()
    from agents.submitter import submit_proposal

    result = submit_proposal(db, args.id)
    if result["success"]:
        print(f"📤 Proposal for opportunity #{args.id} submitted!")
        print(f"   {result['message']}")
        if result.get("reference"):
            print(f"   Reference: {result['reference']}")
    else:
        print(f"⚠️ Submission: {result['message']}")
        if result.get("reference"):
            print(f"   Apply manually at: {result['reference']}")

    db.close()


# ── Win/Loss ─────────────────────────────────────────────────────────

def cmd_won(args):
    """Record a win."""
    db = get_db()
    from agents.proposal_agent import ProposalAgent
    agent = ProposalAgent(db)
    agent.record_outcome(args.id, won=True, lessons=args.notes or "")
    print(f"🏆 Opportunity #{args.id} recorded as WON!")
    db.close()


def cmd_lost(args):
    """Record a loss."""
    db = get_db()
    from agents.proposal_agent import ProposalAgent
    agent = ProposalAgent(db)
    agent.record_outcome(args.id, won=False, lessons=args.notes or "")
    print(f"❌ Opportunity #{args.id} recorded as LOST")
    db.close()


# ── Stats ────────────────────────────────────────────────────────────

def cmd_stats(args):
    """Show pipeline analytics."""
    db = get_db()

    if args.source:
        stats = db.source_stats(args.source)
        print(f"\n═══ Stats: {args.source} ═══")
        print(f"Total:    {stats['total']}")
        print(f"Win rate: {stats['win_rate']}%")
        print(f"Avg score: {stats['avg_score']}")
        for status, count in sorted(stats["by_status"].items()):
            print(f"  {status}: {count}")
    else:
        stats = db.pipeline_stats()
        print(f"\n═══ OpportunityEngine Stats ═══")
        print(f"Total opportunities: {stats['total']}")
        print(f"Win rate:           {stats['win_rate']}%")
        print(f"Wins:               {stats['wins']}")
        print(f"Losses:             {stats['losses']}")
        print(f"Proposals submitted: {stats['proposals_submitted']}")
        print(f"\nBy source:")
        for source, count in sorted(stats["by_source"].items()):
            print(f"  {source}: {count}")
        print(f"\nBy status:")
        for status, count in sorted(stats["by_status"].items()):
            print(f"  {status}: {count}")

    # Template performance
    templates = db.list_templates()
    if templates:
        print(f"\n── Template Performance ──")
        for t in templates:
            print(
                f"  {t.name:20s}  used={t.times_used}  "
                f"wins={t.wins}  losses={t.losses}  "
                f"rate={t.win_rate:.0f}%"
            )

    db.close()


# ── Digest ───────────────────────────────────────────────────────────

def cmd_digest(args):
    """Generate and optionally send daily digest."""
    db = get_db()
    from agents.tracker import Tracker
    tracker = Tracker(db)

    digest = tracker.get_daily_digest()
    message = tracker.format_digest_message(digest)
    print(message)

    if args.send:
        _try_send_digest(message)

    db.close()


def _try_send_digest(message: str):
    try:
        sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/autonomous-agent")
        from core.notifier import Notifier
        import asyncio
        notifier = Notifier()
        asyncio.run(notifier.send("Daily Digest", message, priority="medium"))
        print("\n📨 Digest sent via Telegram")
    except Exception as e:
        print(f"\n⚠️ Could not send digest: {e}")


# ── Main ─────────────────────────────────────────────────────────────

def main():
    # Ensure we can import from the package
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)

    parser = argparse.ArgumentParser(
        prog="oe",
        description="OpportunityEngine - Autonomous Business Development Pipeline",
    )
    sub = parser.add_subparsers(dest="command")

    # scan
    p_scan = sub.add_parser("scan", help="Run scouts")
    p_scan.add_argument("--source", "-s", help="Scout source (freelancer, github, upwork)")
    p_scan.add_argument("--all", "-a", action="store_true", help="Scan all sources")
    p_scan.set_defaults(func=cmd_scan)

    # pipeline
    p_pipe = sub.add_parser("pipeline", help="Show pipeline overview")
    p_pipe.set_defaults(func=cmd_pipeline)

    # list
    p_list = sub.add_parser("list", help="List opportunities")
    p_list.add_argument("--status", help="Filter by status")
    p_list.add_argument("--source", help="Filter by source")
    p_list.add_argument("--min-score", type=int, help="Minimum score")
    p_list.add_argument("--limit", type=int, default=50, help="Max results")
    p_list.set_defaults(func=cmd_list)

    # show
    p_show = sub.add_parser("show", help="Show opportunity details")
    p_show.add_argument("id", type=int, help="Opportunity ID")
    p_show.add_argument("--full", action="store_true", help="Show full proposal text")
    p_show.set_defaults(func=cmd_show)

    # propose
    p_prop = sub.add_parser("propose", help="Draft proposal")
    p_prop.add_argument("id", type=int, help="Opportunity ID")
    p_prop.set_defaults(func=cmd_propose)

    # approve
    p_approve = sub.add_parser("approve", help="Approve proposal")
    p_approve.add_argument("id", type=int, help="Opportunity ID")
    p_approve.set_defaults(func=cmd_approve)

    # submit
    p_submit = sub.add_parser("submit", help="Mark proposal as submitted")
    p_submit.add_argument("id", type=int, help="Opportunity ID")
    p_submit.set_defaults(func=cmd_submit)

    # won
    p_won = sub.add_parser("won", help="Record a win")
    p_won.add_argument("id", type=int, help="Opportunity ID")
    p_won.add_argument("--notes", help="Lessons learned")
    p_won.set_defaults(func=cmd_won)

    # lost
    p_lost = sub.add_parser("lost", help="Record a loss")
    p_lost.add_argument("id", type=int, help="Opportunity ID")
    p_lost.add_argument("--notes", help="Lessons learned")
    p_lost.set_defaults(func=cmd_lost)

    # stats
    p_stats = sub.add_parser("stats", help="Show analytics")
    p_stats.add_argument("--source", help="Per-source stats")
    p_stats.set_defaults(func=cmd_stats)

    # digest
    p_digest = sub.add_parser("digest", help="Generate daily digest")
    p_digest.add_argument("--send", action="store_true", help="Send via Telegram")
    p_digest.set_defaults(func=cmd_digest)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
