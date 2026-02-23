#!/usr/bin/env python3
"""
Intelligence Report - Daily aggregation of all system data.

Aggregates:
- OpportunityEngine: pipeline status, new opportunities, proposals
- Autonomous Agent: tasks completed, agents dispatched
- Property/permit intelligence: new leads, permit status changes
- Email summary: needs-response count, urgent items
- Financial: market overview (from financial-mcp)
- System health: all services status, memory usage
- Actionable recommendations

Delivered via Telegram at 8:00 AM or on-demand via /intel command.
"""

import json
import logging
import os
import psutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("proactive.intelligence")

# Paths
TOOLS_DIR = "/mnt/d/_CLAUDE-TOOLS"
OE_DB = f"{TOOLS_DIR}/opportunityengine/pipeline.db"
AGENT_QUEUE_DB = f"{TOOLS_DIR}/autonomous-agent/queues/tasks.db"
LIVE_STATE_FILE = f"{TOOLS_DIR}/system-bridge/live_state.json"
PID_DIR = f"{TOOLS_DIR}/gateway/pids"


def generate_intelligence_report() -> str:
    """Generate the full daily intelligence report."""
    sections = []
    recommendations = []

    now = datetime.now()
    sections.append(f"*Daily Intelligence Report*\n{now.strftime('%A, %B %d, %Y %I:%M %p')}\n")

    # ── OpportunityEngine Pipeline ──
    oe_section, oe_recs = _get_oe_status()
    sections.append(oe_section)
    recommendations.extend(oe_recs)

    # ── Autonomous Agent ──
    agent_section, agent_recs = _get_agent_status()
    sections.append(agent_section)
    recommendations.extend(agent_recs)

    # ── Email Summary ──
    email_section, email_recs = _get_email_status()
    sections.append(email_section)
    recommendations.extend(email_recs)

    # ── System Health ──
    health_section, health_recs = _get_system_health()
    sections.append(health_section)
    recommendations.extend(health_recs)

    # ── Recommendations ──
    if recommendations:
        rec_text = "*Recommendations:*\n"
        for i, rec in enumerate(recommendations[:5], 1):
            rec_text += f"{i}. {rec}\n"
        sections.append(rec_text)
    else:
        sections.append("*Recommendations:* All systems nominal. No action needed.")

    return "\n---\n".join(sections)


def _get_oe_status() -> tuple[str, list[str]]:
    """Get OpportunityEngine pipeline status."""
    recs = []
    try:
        if not os.path.exists(OE_DB):
            return "*OE Pipeline:* Database not found", []

        conn = sqlite3.connect(OE_DB)
        conn.row_factory = sqlite3.Row

        # Counts by status
        statuses = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM opportunities GROUP BY status"
        ).fetchall()
        status_map = {r["status"]: r["cnt"] for r in statuses}

        total = sum(status_map.values())
        qualified = status_map.get("qualified", 0)
        submitted = status_map.get("submitted", 0)
        won = status_map.get("won", 0)

        # Recent 24h
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        new_24h = conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE discovered_at > ?", (yesterday,)
        ).fetchone()[0]

        # Proposals
        proposals_draft = conn.execute(
            "SELECT COUNT(*) FROM proposals WHERE status = 'draft'"
        ).fetchone()[0]
        proposals_submitted = conn.execute(
            "SELECT COUNT(*) FROM proposals WHERE status = 'submitted'"
        ).fetchone()[0]

        # Revenue tracking
        total_won = conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE status = 'won'"
        ).fetchone()[0]

        conn.close()

        section = (
            f"*OE Pipeline:*\n"
            f"Total: {total} | New (24h): {new_24h}\n"
            f"Qualified: {qualified} | Submitted: {submitted} | Won: {won}\n"
            f"Drafts pending: {proposals_draft} | Proposals out: {proposals_submitted}"
        )

        if proposals_draft > 0:
            recs.append(f"Review {proposals_draft} draft proposals awaiting approval")
        if qualified > 5:
            recs.append(f"{qualified} qualified opportunities need attention")

        return section, recs

    except Exception as e:
        return f"*OE Pipeline:* Error: {e}", []


def _get_agent_status() -> tuple[str, list[str]]:
    """Get autonomous agent task queue status."""
    recs = []
    try:
        if not os.path.exists(AGENT_QUEUE_DB):
            return "*Agent Queue:* Database not found", []

        conn = sqlite3.connect(AGENT_QUEUE_DB)

        pending = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'pending'"
        ).fetchone()[0]
        in_progress = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'in_progress'"
        ).fetchone()[0]

        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        completed_24h = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'completed' AND completed_at > ?",
            (yesterday,)
        ).fetchone()[0]
        failed_24h = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'failed' AND completed_at > ?",
            (yesterday,)
        ).fetchone()[0]

        conn.close()

        section = (
            f"*Agent Queue:*\n"
            f"Pending: {pending} | In Progress: {in_progress}\n"
            f"Completed (24h): {completed_24h} | Failed (24h): {failed_24h}"
        )

        if failed_24h > 3:
            recs.append(f"{failed_24h} agent tasks failed in 24h - investigate errors")
        if pending > 10:
            recs.append(f"{pending} tasks queued - consider increasing parallelism")

        return section, recs

    except Exception as e:
        return f"*Agent Queue:* Error: {e}", []


def _get_email_status() -> tuple[str, list[str]]:
    """Get email summary from live state."""
    recs = []
    try:
        if not os.path.exists(LIVE_STATE_FILE):
            return "*Email:* State file not found", []

        with open(LIVE_STATE_FILE) as f:
            state = json.load(f)

        email = state.get("email", {})
        unread = email.get("unread_count", 0)
        urgent = email.get("urgent_count", 0)
        needs_response = email.get("needs_response_count", 0)

        section = (
            f"*Email:*\n"
            f"Unread: {unread} | Urgent: {urgent} | Needs Response: {needs_response}"
        )

        alerts = email.get("alerts", [])
        if alerts:
            section += "\nAlerts:"
            for a in alerts[:3]:
                frm = a.get("from", "?").split("<")[0].strip()[:25]
                subj = a.get("subject", "?")[:40]
                section += f"\n  - {frm}: {subj}"

        if urgent > 0:
            recs.append(f"{urgent} urgent email(s) need immediate attention")
        if needs_response > 3:
            recs.append(f"{needs_response} emails awaiting your response")

        return section, recs

    except Exception as e:
        return f"*Email:* Error: {e}", []


def _get_system_health() -> tuple[str, list[str]]:
    """Get system resource and service health status."""
    recs = []

    # System resources
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)

    # Service health
    services = ["ps-bridge", "gateway-hub", "telegram-bot", "proactive",
                 "email-watcher", "autonomous-agent", "opportunityengine"]
    running = []
    dead = []

    for svc in services:
        pidfile = os.path.join(PID_DIR, f"{svc}.pid")
        if os.path.exists(pidfile):
            try:
                pid = int(open(pidfile).read().strip())
                os.kill(pid, 0)
                running.append(svc)
                continue
            except (ValueError, ProcessLookupError, PermissionError):
                pass
        dead.append(svc)

    section = (
        f"*System Health:*\n"
        f"CPU: {cpu:.0f}% | Memory: {mem.percent:.0f}% ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB)\n"
        f"Services: {len(running)}/{len(services)} running"
    )

    if dead:
        section += f"\nDead: {', '.join(dead)}"
        recs.append(f"Restart dead services: {', '.join(dead)}")

    if mem.percent > 85:
        recs.append(f"Memory at {mem.percent:.0f}% - consider closing unused apps")

    return section, recs


def generate_short_status() -> str:
    """Generate a shorter OE pipeline status for /oe command."""
    try:
        if not os.path.exists(OE_DB):
            return "OE database not found."

        conn = sqlite3.connect(OE_DB)
        conn.row_factory = sqlite3.Row

        statuses = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM opportunities GROUP BY status"
        ).fetchall()
        status_map = {r["status"]: r["cnt"] for r in statuses}

        total = sum(status_map.values())

        # Recent opportunities
        recent = conn.execute(
            "SELECT title, source, score, status FROM opportunities "
            "ORDER BY discovered_at DESC LIMIT 5"
        ).fetchall()

        # Proposal stats
        proposal_stats = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM proposals GROUP BY status"
        ).fetchall()
        p_map = {r["status"]: r["cnt"] for r in proposal_stats}

        conn.close()

        lines = [f"*OE Pipeline Status*\n"]
        lines.append(f"Total: {total}")
        for s in ["new", "qualified", "submitted", "won", "lost", "expired"]:
            if s in status_map:
                lines.append(f"  {s}: {status_map[s]}")

        if p_map:
            lines.append(f"\nProposals:")
            for s, c in p_map.items():
                lines.append(f"  {s}: {c}")

        if recent:
            lines.append(f"\nRecent:")
            for r in recent:
                score = r["score"] or 0
                lines.append(f"  [{score}] {r['title'][:45]} ({r['source']})")

        return "\n".join(lines)

    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "short":
        print(generate_short_status())
    else:
        print(generate_intelligence_report())
