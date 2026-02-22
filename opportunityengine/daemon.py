#!/usr/bin/env python3
"""OpportunityEngine daemon - autonomous revenue generation agent.

Runs 24/7. Scans platforms, qualifies opportunities, drafts proposals,
makes submit/hold decisions, follows up, and learns from outcomes.

The agent acts autonomously on low-risk opportunities and holds
high-value ones for human approval via Telegram.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta

# Ensure package imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import Database
from core.config import (
    SCAN_INTERVALS, DAILY_DIGEST_HOUR_UTC, PEAK_HOURS_UTC, DB_PATH,
    SCORE_HOT, SCORE_QUALIFIED,
)
from core.decision_rules import decide, Action, Decision
from core.models import Opportunity, OpportunityStatus, ProposalStatus
import threading
from scouts.github_scout import GitHubScout
from scouts.freelancer_scout import FreelancerScout
from scouts.reddit_scout import RedditScout
from scouts.hn_scout import HNScout
from scouts.remoteok_scout import RemoteOKScout
from scouts.upwork_scout import UpworkScout
from agents.qualifier import Qualifier
from agents.proposal_agent import ProposalAgent
from agents.tracker import Tracker
from agents.submitter import submit_proposal, get_submitter
from agents.response_monitor import ResponseMonitor

_log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daemon.log")
logger = logging.getLogger("opportunityengine.daemon")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    fh = logging.FileHandler(_log_file)
    fh.setFormatter(fmt)
    logger.addHandler(sh)
    logger.addHandler(fh)

RUNNING = True


def signal_handler(sig, frame):
    global RUNNING
    logger.info("Shutdown signal received")
    RUNNING = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


class OpportunityDaemon:
    """Autonomous revenue generation agent.

    Loop: Scan → Qualify → Decide → Propose → Submit/Hold → Follow Up → Learn
    """

    def __init__(self):
        self.db = Database(DB_PATH)
        # All scouts — CDP-based ones (upwork) run with timeout protection
        self.scouts = {
            "github": GitHubScout(self.db),
            "reddit": RedditScout(self.db),
            "hackernews": HNScout(self.db),
            "remoteok": RemoteOKScout(self.db),
            "upwork": UpworkScout(self.db),
        }
        # CDP-based scouts need timeout wrapping to prevent daemon hangs
        self._cdp_scouts = {"upwork"}
        self.qualifier = Qualifier(self.db)
        self.proposal_agent = ProposalAgent(self.db)
        self.tracker = Tracker(self.db)
        self.response_monitor = ResponseMonitor(self.db)

        # Timing state
        self.last_scan: dict[str, datetime] = {}
        self.last_digest: datetime | None = None
        self.last_expire: datetime | None = None
        self.last_proposal_run: datetime | None = None
        self.last_follow_up: datetime | None = None
        self.last_response_check: datetime | None = None

        # Daily counters (reset at midnight UTC)
        self.daily_submissions = 0
        self.daily_drafts = 0
        self.counter_date = datetime.utcnow().date()

        # Stats for this session
        self.session_stats = {
            "scans": 0,
            "opportunities_found": 0,
            "proposals_drafted": 0,
            "proposals_submitted": 0,
            "decisions_made": 0,
        }

    def run(self):
        """Main daemon loop."""
        logger.info("OpportunityEngine autonomous agent starting")
        self._notify("OpportunityEngine Started",
                     f"Autonomous agent started at {datetime.utcnow().isoformat()}\n"
                     f"Scouts: {', '.join(self.scouts.keys())}\n"
                     f"Mode: Autonomous (auto-propose + hold for review)")

        while RUNNING:
            try:
                self._tick()
            except Exception as e:
                logger.exception(f"Tick error: {e}")

            # Sleep 60 seconds between ticks (interruptible)
            for _ in range(60):
                if not RUNNING:
                    break
                time.sleep(1)

        logger.info(f"Daemon shutting down. Session stats: {self.session_stats}")
        self.db.close()

    def _tick(self):
        """Single daemon tick - the full autonomous pipeline."""
        now = datetime.utcnow()
        self._reset_daily_counters(now)

        # ── Phase 1: SCAN for new opportunities ──
        self._run_scouts(now)

        # ── Phase 2: DECIDE + ACT on qualified opportunities ──
        self._process_pipeline(now)

        # ── Phase 3: CHECK for responses to submitted proposals ──
        if self._should_check_responses(now):
            self._check_responses()
            self.last_response_check = now

        # ── Phase 4: FOLLOW UP on submitted proposals ──
        if self._should_follow_up(now):
            self._follow_up()
            self.last_follow_up = now

        # ── Phase 5: DAILY DIGEST ──
        if self._should_send_digest(now):
            self._send_digest()
            self.last_digest = now

        # ── Phase 6: MAINTENANCE ──
        if self.last_expire is None or (now - self.last_expire).days >= 1:
            expired = self.tracker.expire_stale(days=14)
            if expired:
                logger.info(f"Expired {expired} stale opportunities")
            self.last_expire = now

    # ── Phase 1: Scanning ──────────────────────────────────────────────

    def _run_scouts(self, now: datetime):
        """Run scouts based on their intervals."""
        for source, scout in self.scouts.items():
            interval = self._get_interval(source, now)
            last = self.last_scan.get(source)

            if last is None or (now - last).total_seconds() >= interval * 60:
                logger.info(f"Scanning {source}...")
                try:
                    # CDP-based scouts get a hard timeout to prevent daemon hangs
                    if source in self._cdp_scouts:
                        log = self._run_scout_with_timeout(scout, timeout=180)
                    else:
                        log = scout.scan()

                    if log is None:
                        logger.warning(f"  {source}: scan timed out")
                        self.last_scan[source] = now
                        continue

                    self.last_scan[source] = now
                    self.session_stats["scans"] += 1
                    self.session_stats["opportunities_found"] += log.new_opportunities

                    if log.new_opportunities > 0:
                        logger.info(f"  {source}: {log.new_opportunities} new opportunities")
                        result = self.qualifier.qualify_all_new()
                        hot = result.get("hot", [])
                        qualified = result.get("qualified", [])
                        if hot:
                            self._alert_hot(hot)
                        if qualified:
                            logger.info(f"  {len(qualified)} newly qualified")
                except Exception as e:
                    logger.error(f"Scout {source} failed: {e}")

    # ── Phase 2: Decision + Action Pipeline ────────────────────────────

    def _process_pipeline(self, now: datetime):
        """Process qualified opportunities through the decision engine."""
        # Only run proposal pipeline every 5 minutes
        if self.last_proposal_run and (now - self.last_proposal_run).total_seconds() < 300:
            return
        self.last_proposal_run = now

        # Get all qualified opportunities that don't have proposals yet
        qualified = self.db.list_opportunities(
            status=OpportunityStatus.QUALIFIED, limit=50
        )

        for opp in qualified:
            if not RUNNING:
                break

            # Check if proposal already exists
            existing = self.db.get_proposal_for_opportunity(opp.id)
            if existing:
                continue

            # Make decision
            decision = decide(opp, daily_submissions=self.daily_submissions)
            self.session_stats["decisions_made"] += 1

            logger.info(
                f"  Decision [{opp.id}] {opp.title[:40]}... -> "
                f"{decision.action.value} (confidence={decision.confidence:.0%})"
            )

            if decision.action == Action.AUTO_PROPOSE:
                self._auto_propose(opp, decision)
            elif decision.action == Action.DRAFT_AND_HOLD:
                self._draft_and_hold(opp, decision)
            elif decision.action == Action.HOLD_FOR_REVIEW:
                self._hold_for_review(opp, decision)
            # SKIP does nothing

        # Also process drafted proposals waiting for auto-submit
        self._process_pending_drafts()

    def _auto_propose(self, opp: Opportunity, decision: Decision):
        """Draft and auto-submit a proposal to the actual platform."""
        try:
            proposal = self.proposal_agent.draft_proposal(opp.id)
            if proposal:
                # Set the bid amount from decision
                if decision.auto_bid_amount:
                    self.db.update_proposal(proposal.id, pricing=f"${decision.auto_bid_amount:.0f}")

                # Auto-approve
                self.proposal_agent.approve_proposal(opp.id)
                self.session_stats["proposals_drafted"] += 1

                # Actually submit to the platform
                result = submit_proposal(self.db, opp.id)

                if result["success"]:
                    self.daily_submissions += 1
                    self.session_stats["proposals_submitted"] += 1

                    logger.info(
                        f"  AUTO-SUBMITTED [{opp.source}] [{opp.id}] {opp.title[:40]} "
                        f"@ ${decision.auto_bid_amount or 0:.0f} -> {result['message']}"
                    )

                    self._notify(
                        "Auto-Submitted Proposal",
                        f"Proposal submitted on {opp.source}:\n"
                        f"{opp.title}\n"
                        f"Bid: ${decision.auto_bid_amount or 0:.0f}\n"
                        f"Score: {opp.score}/100\n"
                        f"Result: {result['message']}",
                        priority="medium",
                    )
                else:
                    logger.warning(
                        f"  AUTO-SUBMIT FAILED [{opp.source}] [{opp.id}]: {result['message']}"
                    )
                    # Still notify for manual follow-up
                    if "manual" in result["message"].lower():
                        self._notify(
                            "Manual Submission Needed",
                            f"Proposal drafted but needs manual submission:\n"
                            f"{opp.title}\n"
                            f"Source: {opp.source}\n"
                            f"Apply at: {result.get('reference', 'see opportunity details')}",
                            priority="medium",
                        )

                self._remember(
                    f"{'Submitted' if result['success'] else 'Draft-only'} proposal for "
                    f"'{opp.title}' on {opp.source} at ${decision.auto_bid_amount or 0:.0f}. "
                    f"Score: {opp.score}. Result: {result['message']}",
                    tags=["proposal", "auto-submit", opp.source],
                )
        except Exception as e:
            logger.error(f"Auto-propose failed for [{opp.id}]: {e}")

    def _draft_and_hold(self, opp: Opportunity, decision: Decision):
        """Draft a proposal and hold for human approval."""
        try:
            proposal = self.proposal_agent.draft_proposal(opp.id)
            if proposal:
                if decision.auto_bid_amount:
                    self.db.update_proposal(proposal.id, pricing=f"${decision.auto_bid_amount:.0f}")

                self.daily_drafts += 1
                self.session_stats["proposals_drafted"] += 1

                logger.info(
                    f"  DRAFTED proposal for [{opp.id}] {opp.title[:40]} "
                    f"- awaiting approval"
                )

                # Only notify for high-priority holds
                if decision.priority >= 7:
                    self._notify(
                        "Proposal Ready for Review",
                        f"High-value opportunity needs your approval:\n\n"
                        f"{opp.title}\n"
                        f"Budget: {opp.budget_display}\n"
                        f"Score: {opp.score}/100\n"
                        f"Suggested bid: ${decision.auto_bid_amount or 0:.0f}\n"
                        f"Source: {opp.source}\n\n"
                        f"Run: oe approve {opp.id}\n"
                        f"Or: oe show {opp.id} --full",
                        priority="high",
                    )
        except Exception as e:
            logger.error(f"Draft failed for [{opp.id}]: {e}")

    def _hold_for_review(self, opp: Opportunity, decision: Decision):
        """Flag an opportunity for human review without drafting."""
        logger.info(f"  HOLD [{opp.id}] {opp.title[:40]} - {decision.reason}")

    def _process_pending_drafts(self):
        """Check for approved proposals that need submission."""
        approved = self.db.list_proposals(status=ProposalStatus.APPROVED)
        for proposal in approved:
            if not RUNNING:
                break

            # Track retry attempts — stop after 3 failures
            retry_key = f"submit_retries_{proposal.id}"
            retries = getattr(self, retry_key, 0)
            if retries >= 3:
                logger.warning(
                    f"  Giving up on proposal [{proposal.id}] for opp [{proposal.opportunity_id}] "
                    f"after {retries} failed attempts — marking as submitted (manual needed)"
                )
                self.db.update_proposal(proposal.id, status="submitted",
                                        lessons_learned="Auto-submission failed after 3 retries. Manual submission needed.")
                self.db.update_opportunity(proposal.opportunity_id, status="submitted",
                                           notes="Proposal needs manual submission")
                continue

            try:
                result = submit_proposal(self.db, proposal.opportunity_id)
                if result["success"]:
                    self.daily_submissions += 1
                    self.session_stats["proposals_submitted"] += 1
                    logger.info(
                        f"  Submitted approved proposal for opp [{proposal.opportunity_id}]: "
                        f"{result['message']}"
                    )
                else:
                    setattr(self, retry_key, retries + 1)
                    logger.warning(
                        f"  Submit failed for opp [{proposal.opportunity_id}] "
                        f"(attempt {retries + 1}/3): {result['message']}"
                    )
            except Exception as e:
                setattr(self, retry_key, retries + 1)
                logger.error(f"Submit failed for proposal [{proposal.id}] (attempt {retries + 1}/3): {e}")

    # ── Phase 3: Response Monitoring ────────────────────────────────────

    def _should_check_responses(self, now: datetime) -> bool:
        """Check for responses every 30 minutes."""
        if self.last_response_check is None:
            return True
        return (now - self.last_response_check).total_seconds() >= 1800

    def _check_responses(self):
        """Check platform inboxes for responses to submitted proposals."""
        try:
            responses = self.response_monitor.check_all()
            if responses:
                logger.info(f"  Found {len(responses)} new responses!")
                for resp in responses:
                    self._notify(
                        f"New Response on {resp['platform'].title()}!",
                        f"From: {resp['from']}\n"
                        f"Re: {resp['subject']}\n"
                        f"Preview: {resp['preview'][:150]}\n\n"
                        f"Check: {resp.get('url', '')}",
                        priority="high",
                    )
                    # Also speak it
                    try:
                        import subprocess
                        subprocess.run(
                            ["python3", "/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py",
                             f"New response on {resp['platform']} from {resp['from']}. "
                             f"Subject: {resp['subject']}"],
                            timeout=15, capture_output=True,
                        )
                    except Exception:
                        pass
            else:
                logger.info("  No new responses found")
        except Exception as e:
            logger.error(f"Response check failed: {e}")

    # ── Phase 4: Follow Up ─────────────────────────────────────────────

    def _should_follow_up(self, now: datetime) -> bool:
        """Check if it's time to follow up on submitted proposals."""
        if self.last_follow_up is None:
            return True
        return (now - self.last_follow_up).total_seconds() >= 6 * 3600  # Every 6 hours

    def _follow_up(self):
        """Check on submitted proposals and flag stale ones."""
        submitted = self.db.list_proposals(status=ProposalStatus.SUBMITTED)
        now = datetime.utcnow()
        stale = []

        for prop in submitted:
            if not prop.submitted_at:
                continue
            try:
                submitted_dt = datetime.fromisoformat(prop.submitted_at)
                days_since = (now - submitted_dt).days
                if days_since >= 7:
                    stale.append(prop)
            except (ValueError, TypeError):
                continue

        if stale:
            logger.info(f"  {len(stale)} proposals with no response after 7+ days")
            titles = [f"  - [{p.opportunity_id}] (submitted {p.submitted_at[:10]})"
                      for p in stale[:5]]
            self._notify(
                "Stale Proposals",
                f"{len(stale)} proposals have no response:\n" + "\n".join(titles) +
                "\n\nConsider following up or recording outcome:\n"
                "oe won <id> or oe lost <id>",
                priority="low",
            )

    # ── Notification & Memory ──────────────────────────────────────────

    def _notify(self, title: str, message: str, priority: str = "medium"):
        """Send notification via log + voice TTS for high priority."""
        import subprocess

        # Always log the notification
        logger.info(f"[NOTIFY:{priority}] {title}: {message[:120]}")

        # Log to notifications file for CLI review
        try:
            notif_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "notifications.log"
            )
            with open(notif_path, "a") as f:
                f.write(
                    f"{datetime.utcnow().isoformat()} [{priority.upper()}] {title}\n"
                    f"  {message}\n\n"
                )
        except Exception:
            pass

        # Voice TTS for high priority
        if priority == "high":
            try:
                subprocess.run(
                    ["python3", "/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py",
                     f"{title}. {message[:200]}"],
                    timeout=15, capture_output=True,
                )
            except Exception:
                pass

    def _alert_hot(self, hot_opps: list):
        """Send alerts for hot opportunities."""
        for opp in hot_opps:
            self._notify(
                f"HOT Opportunity [{opp.score}/100]",
                f"{opp.title}\n"
                f"Budget: {opp.budget_display}\n"
                f"Source: {opp.source}\n"
                f"Skills: {', '.join(opp.skills_required[:5])}\n\n"
                f"Run: oe show {opp.id}",
                priority="high",
            )

    def _remember(self, content: str, tags: list[str] | None = None):
        """Store information in Claude Memory for learning."""
        try:
            tag_str = ", ".join(tags) if tags else "opportunityengine"
            self.db._conn.execute(
                "INSERT INTO scan_log (source, scanned_at, errors) VALUES (?, ?, ?)",
                ("memory", datetime.utcnow().isoformat(), f"[{tag_str}] {content}"),
            )
            self.db._conn.commit()
        except Exception:
            pass  # Memory is best-effort

    # ── Digest ─────────────────────────────────────────────────────────

    def _should_send_digest(self, now: datetime) -> bool:
        if now.hour != DAILY_DIGEST_HOUR_UTC:
            return False
        if self.last_digest and (now - self.last_digest).total_seconds() < 3600:
            return False
        return True

    def _send_digest(self):
        """Build and send enhanced daily digest with action summary."""
        try:
            digest = self.tracker.get_daily_digest()
            message = self.tracker.format_digest_message(digest)

            # Add session stats
            message += (
                f"\n\nAgent Session Stats:\n"
                f"  Scans: {self.session_stats['scans']}\n"
                f"  New opportunities: {self.session_stats['opportunities_found']}\n"
                f"  Proposals drafted: {self.session_stats['proposals_drafted']}\n"
                f"  Auto-submitted: {self.session_stats['proposals_submitted']}\n"
                f"  Decisions made: {self.session_stats['decisions_made']}\n"
            )

            # Add pending actions for human
            qualified_no_proposal = self.db._conn.execute(
                "SELECT COUNT(*) FROM opportunities WHERE status = 'qualified' "
                "AND id NOT IN (SELECT opportunity_id FROM proposals)"
            ).fetchone()[0]

            drafts_pending = self.db._conn.execute(
                "SELECT COUNT(*) FROM proposals WHERE status = 'draft'"
            ).fetchone()[0]

            if qualified_no_proposal or drafts_pending:
                message += f"\nPending Actions:\n"
                if qualified_no_proposal:
                    message += f"  {qualified_no_proposal} qualified opportunities need proposals\n"
                if drafts_pending:
                    message += f"  {drafts_pending} draft proposals need your approval\n"

            self._notify("Daily Digest", message, priority="medium")
            logger.info("Daily digest sent")
        except Exception as e:
            logger.error(f"Digest failed: {e}")

    # ── Helpers ─────────────────────────────────────────────────────────

    def _run_scout_with_timeout(self, scout, timeout: int = 180):
        """Run a CDP scout in a separate process to avoid SQLite thread issues."""
        import subprocess as sp
        import json as _json

        source = scout.source_name
        oe_dir = os.path.dirname(os.path.abspath(__file__))

        # Run the scout in a child process with its own DB connection
        script = (
            f"import sys, os, json; "
            f"sys.path.insert(0, '{oe_dir}'); "
            f"from core.database import Database; "
            f"from core.config import DB_PATH; "
            f"from scouts.{source}_scout import {source.title()}Scout; "
            f"db = Database(DB_PATH); "
            f"scout = {source.title()}Scout(db); "
            f"log = scout.scan(); "
            f"print(json.dumps({{'new': log.new_opportunities, 'total': log.opportunities_found}})); "
            f"db.close()"
        )
        try:
            r = sp.run(
                ["python3", "-c", script],
                capture_output=True, text=True, timeout=timeout,
                cwd=oe_dir,
            )
            if r.returncode == 0 and r.stdout.strip():
                for line in r.stdout.strip().split("\n"):
                    line = line.strip()
                    if line.startswith("{"):
                        data = _json.loads(line)
                        class _Log:
                            new_opportunities = data.get("new", 0)
                            opportunities_found = data.get("total", 0)
                        return _Log()
            if r.stderr:
                logger.warning(f"Scout {source} subprocess stderr: {r.stderr[:300]}")
            return None
        except sp.TimeoutExpired:
            logger.warning(f"Scout {source} timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Scout {source} subprocess error: {e}")
            return None

    def _get_interval(self, source: str, now: datetime) -> int:
        base = SCAN_INTERVALS.get(source, 60)
        if now.hour in PEAK_HOURS_UTC:
            return max(10, base // 2)
        return base

    def _reset_daily_counters(self, now: datetime):
        today = now.date()
        if today != self.counter_date:
            logger.info(
                f"Day rollover - yesterday: {self.daily_submissions} submissions, "
                f"{self.daily_drafts} drafts"
            )
            self.daily_submissions = 0
            self.daily_drafts = 0
            self.counter_date = today


def main():
    daemon = OpportunityDaemon()
    daemon.run()


if __name__ == "__main__":
    main()
