#!/usr/bin/env python3
"""
Business Pulse Heartbeat Daemon
================================
Runs every hour via Windows Task Scheduler.
Checks the business database for things that need attention.
Writes alerts to pulse.json for Claude Code to pick up at session start.
Optionally auto-drafts follow-up emails for overdue invoices.

Usage:
  python heartbeat.py              # Run once (for Task Scheduler)
  python heartbeat.py --daemon     # Run continuously (every hour)
  python heartbeat.py --test       # Run once and print output

DB Path: D:\\_CLAUDE-TOOLS\\crm-accounting\\data\\business.db
Pulse:   D:\\_CLAUDE-TOOLS\\business-pulse\\pulse.json
"""

import sqlite3
import json
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Paths
DB_PATH = Path(r"D:\_CLAUDE-TOOLS\crm-accounting\data\business.db")
PULSE_PATH = Path(r"D:\_CLAUDE-TOOLS\business-pulse\pulse.json")
LOG_PATH = Path(r"D:\_CLAUDE-TOOLS\business-pulse\logs")
DRAFT_PATH = Path(r"D:\_CLAUDE-TOOLS\email-watcher\draft_responses.json")

# Ensure directories exist
LOG_PATH.mkdir(parents=True, exist_ok=True)
PULSE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH / f"heartbeat_{datetime.now():%Y%m%d}.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("heartbeat")


def get_db():
    """Get database connection."""
    if not DB_PATH.exists():
        log.error(f"Database not found: {DB_PATH}")
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def check_overdue_invoices(conn):
    """Find invoices past due date."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            i.id, i.invoice_number, c.name AS client_name, c.email AS client_email,
            i.total, i.amount_paid, (i.total - i.amount_paid) AS balance_due,
            i.date_due,
            CAST(julianday('now') - julianday(i.date_due) AS INTEGER) AS days_overdue
        FROM invoices i
        JOIN clients c ON i.client_id = c.id
        WHERE i.status IN ('sent', 'partial', 'overdue')
          AND julianday('now') > julianday(i.date_due)
        ORDER BY days_overdue DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]

    alerts = []
    for row in rows:
        days = row["days_overdue"]
        if days <= 7:
            action = "friendly_reminder"
            urgency = "low"
        elif days <= 14:
            action = "second_notice"
            urgency = "medium"
        elif days <= 30:
            action = "formal_request"
            urgency = "high"
        else:
            action = "final_notice"
            urgency = "critical"

        alerts.append({
            "type": "overdue_invoice",
            "urgency": urgency,
            "invoice_number": row["invoice_number"],
            "client": row["client_name"],
            "client_email": row["client_email"],
            "balance_due": row["balance_due"],
            "days_overdue": days,
            "recommended_action": action,
            "message": f"{row['invoice_number']} — {row['client_name']} owes ${row['balance_due']:,.2f} ({days} days overdue)"
        })

    return alerts


def check_unbilled_time(conn):
    """Find projects with significant unbilled time."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            c.name AS client_name, c.email AS client_email,
            p.id AS project_id, p.name AS project_name,
            SUM(t.hours) AS total_hours,
            SUM(t.hours * t.rate) AS total_amount,
            MIN(t.date) AS earliest_entry,
            MAX(t.date) AS latest_entry
        FROM time_entries t
        JOIN clients c ON t.client_id = c.id
        JOIN projects p ON t.project_id = p.id
        WHERE t.billable = 1 AND t.invoiced = 0
        GROUP BY p.id
        HAVING total_amount >= 500
        ORDER BY total_amount DESC
    """)

    alerts = []
    for row in cursor.fetchall():
        row = dict(row)
        urgency = "high" if row["total_amount"] >= 2000 else "medium" if row["total_amount"] >= 1000 else "low"
        alerts.append({
            "type": "unbilled_time",
            "urgency": urgency,
            "client": row["client_name"],
            "project": row["project_name"],
            "project_id": row["project_id"],
            "hours": round(row["total_hours"], 1),
            "amount": round(row["total_amount"], 2),
            "date_range": f"{row['earliest_entry']} to {row['latest_entry']}",
            "message": f"{row['project_name']} — {row['total_hours']:.1f} hrs (${row['total_amount']:,.2f}) unbilled"
        })

    return alerts


def check_due_this_week(conn):
    """Find invoices due in the next 7 days."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            i.invoice_number, c.name AS client_name,
            i.total, i.amount_paid, (i.total - i.amount_paid) AS balance_due,
            i.date_due,
            CAST(julianday(i.date_due) - julianday('now') AS INTEGER) AS days_until_due
        FROM invoices i
        JOIN clients c ON i.client_id = c.id
        WHERE i.status = 'sent'
          AND i.date_due BETWEEN date('now') AND date('now', '+7 days')
        ORDER BY i.date_due
    """)

    alerts = []
    for row in cursor.fetchall():
        row = dict(row)
        alerts.append({
            "type": "due_soon",
            "urgency": "info",
            "invoice_number": row["invoice_number"],
            "client": row["client_name"],
            "balance_due": row["balance_due"],
            "date_due": row["date_due"],
            "days_until_due": row["days_until_due"],
            "message": f"{row['invoice_number']} — {row['client_name']} ${row['balance_due']:,.2f} due in {row['days_until_due']} days"
        })

    return alerts


def check_recurring_expenses(conn):
    """Find recurring subscriptions not logged this month."""
    cursor = conn.cursor()
    # Find subscriptions that were logged last month but not this month
    cursor.execute("""
        SELECT description, vendor, amount, MAX(date) AS last_logged
        FROM expenses
        WHERE category = 'subscriptions'
        GROUP BY description, vendor
        HAVING last_logged < date('now', 'start of month')
    """)

    alerts = []
    for row in cursor.fetchall():
        row = dict(row)
        alerts.append({
            "type": "recurring_expense",
            "urgency": "low",
            "description": row["description"],
            "vendor": row["vendor"],
            "amount": row["amount"],
            "last_logged": row["last_logged"],
            "message": f"{row['description']} (${row['amount']:.2f}/mo from {row['vendor']}) — last logged {row['last_logged']}"
        })

    return alerts


def check_stale_clients(conn):
    """Find active clients with no activity in 30+ days."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            c.id, c.name, c.email, c.phone,
            MAX(COALESCE(p.updated_at, c.created_at)) AS last_activity,
            CAST(julianday('now') - julianday(MAX(COALESCE(p.updated_at, c.created_at))) AS INTEGER) AS days_inactive
        FROM clients c
        LEFT JOIN projects p ON c.id = p.client_id
        WHERE c.status = 'active'
        GROUP BY c.id
        HAVING days_inactive > 30
        ORDER BY days_inactive DESC
    """)

    alerts = []
    for row in cursor.fetchall():
        row = dict(row)
        alerts.append({
            "type": "stale_client",
            "urgency": "low",
            "client": row["name"],
            "client_email": row["email"],
            "days_inactive": row["days_inactive"],
            "last_activity": row["last_activity"],
            "message": f"{row['name']} — no activity in {row['days_inactive']} days. Follow up?"
        })

    return alerts


def check_project_health(conn):
    """Find active projects over budget or with no recent time entries."""
    cursor = conn.cursor()
    # Over budget
    cursor.execute("""
        SELECT
            p.name AS project_name, c.name AS client_name,
            p.budget,
            COALESCE(SUM(t.hours * t.rate), 0) AS actual_cost,
            COALESCE(SUM(t.hours * t.rate), 0) / p.budget * 100 AS pct_used
        FROM projects p
        JOIN clients c ON p.client_id = c.id
        LEFT JOIN time_entries t ON p.id = t.project_id
        WHERE p.status = 'active' AND p.budget IS NOT NULL AND p.budget > 0
        GROUP BY p.id
        HAVING actual_cost > budget * 0.9
        ORDER BY pct_used DESC
    """)

    alerts = []
    for row in cursor.fetchall():
        row = dict(row)
        over = row["actual_cost"] > row["budget"]
        alerts.append({
            "type": "budget_warning",
            "urgency": "high" if over else "medium",
            "project": row["project_name"],
            "client": row["client_name"],
            "budget": row["budget"],
            "actual": round(row["actual_cost"], 2),
            "pct_used": round(row["pct_used"], 1),
            "message": f"{row['project_name']} — {'OVER' if over else 'near'} budget: ${row['actual_cost']:,.0f} / ${row['budget']:,.0f} ({row['pct_used']:.0f}%)"
        })

    return alerts


def auto_draft_reminder(alert):
    """Auto-draft a follow-up email for overdue invoices."""
    if alert["urgency"] == "low":
        subject = f"Invoice {alert['invoice_number']} — Friendly Reminder"
        body = (
            f"Hi,\n\n"
            f"Just a quick reminder that invoice {alert['invoice_number']} for "
            f"${alert['balance_due']:,.2f} was due on {alert.get('date_due', 'recently')}.\n\n"
            f"Please let me know if you have any questions.\n\n"
            f"Payment can be sent via Zelle to weberg619@gmail.com.\n\n"
            f"Thanks!\nWeber"
        )
    elif alert["urgency"] == "medium":
        subject = f"Invoice {alert['invoice_number']} — Payment Reminder"
        body = (
            f"Hi,\n\n"
            f"Following up on invoice {alert['invoice_number']} for "
            f"${alert['balance_due']:,.2f}, which is now {alert['days_overdue']} days past due.\n\n"
            f"Please advise on payment status at your earliest convenience.\n\n"
            f"Best,\nWeber"
        )
    else:
        subject = f"Invoice {alert['invoice_number']} — Payment Required"
        body = (
            f"Hi,\n\n"
            f"This is a formal request regarding invoice {alert['invoice_number']} for "
            f"${alert['balance_due']:,.2f}, which is now {alert['days_overdue']} days overdue.\n\n"
            f"Please arrange payment immediately or contact me to discuss.\n\n"
            f"Regards,\nWeber Gouin\nBIM Ops Studio"
        )

    draft = {
        "id": f"pulse-{alert['invoice_number']}-{datetime.now():%Y%m%d}",
        "type": "overdue_followup",
        "to": alert.get("client_email", ""),
        "to_name": alert["client"],
        "subject": subject,
        "body": body,
        "status": "pending_review",
        "generated_at": datetime.now().isoformat(),
        "source": "business-pulse-heartbeat",
        "invoice_number": alert["invoice_number"],
        "days_overdue": alert["days_overdue"]
    }

    # Append to draft_responses.json
    try:
        if DRAFT_PATH.exists():
            with open(DRAFT_PATH, "r") as f:
                drafts = json.load(f)
        else:
            drafts = []

        # Don't duplicate — check if we already drafted for this invoice today
        existing_ids = {d.get("id") for d in drafts}
        if draft["id"] not in existing_ids:
            drafts.append(draft)
            with open(DRAFT_PATH, "w") as f:
                json.dump(drafts, f, indent=2)
            log.info(f"Auto-drafted email for {alert['invoice_number']} → {alert['client']}")
            return True
    except Exception as e:
        log.error(f"Failed to draft email: {e}")

    return False


def generate_pulse():
    """Run all checks and generate pulse.json."""
    conn = get_db()
    if not conn:
        return {"error": "Database not found", "timestamp": datetime.now().isoformat()}

    log.info("Running heartbeat checks...")

    all_alerts = []
    drafts_created = 0

    try:
        # Run all checks
        overdue = check_overdue_invoices(conn)
        all_alerts.extend(overdue)
        log.info(f"  Overdue invoices: {len(overdue)}")

        unbilled = check_unbilled_time(conn)
        all_alerts.extend(unbilled)
        log.info(f"  Unbilled time alerts: {len(unbilled)}")

        due_soon = check_due_this_week(conn)
        all_alerts.extend(due_soon)
        log.info(f"  Due this week: {len(due_soon)}")

        recurring = check_recurring_expenses(conn)
        all_alerts.extend(recurring)
        log.info(f"  Recurring expenses missed: {len(recurring)}")

        stale = check_stale_clients(conn)
        all_alerts.extend(stale)
        log.info(f"  Stale clients: {len(stale)}")

        budget = check_project_health(conn)
        all_alerts.extend(budget)
        log.info(f"  Budget warnings: {len(budget)}")

        # Auto-draft emails for overdue invoices (3+ days)
        for alert in overdue:
            if alert["days_overdue"] >= 3 and alert.get("client_email"):
                if auto_draft_reminder(alert):
                    drafts_created += 1

        # Quick financial snapshot
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')")
        mtd_revenue = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')")
        mtd_expenses = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(total - amount_paid), 0) FROM invoices WHERE status IN ('sent', 'partial', 'overdue')")
        total_ar = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(hours * rate), 0) FROM time_entries WHERE billable = 1 AND invoiced = 0")
        unbilled_total = cursor.fetchone()[0]

        snapshot = {
            "mtd_revenue": round(mtd_revenue, 2),
            "mtd_expenses": round(mtd_expenses, 2),
            "mtd_net": round(mtd_revenue - mtd_expenses, 2),
            "total_ar": round(total_ar, 2),
            "unbilled_total": round(unbilled_total, 2),
            "pipeline": round(total_ar + unbilled_total, 2)
        }

    except Exception as e:
        log.error(f"Error during checks: {e}")
        snapshot = {}
    finally:
        conn.close()

    # Sort alerts by urgency
    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    all_alerts.sort(key=lambda a: urgency_order.get(a.get("urgency", "info"), 5))

    # Build pulse
    pulse = {
        "generated_at": datetime.now().isoformat(),
        "next_check": (datetime.now() + timedelta(hours=1)).isoformat(),
        "status": "clean" if not all_alerts else "needs_attention",
        "summary": {
            "total_alerts": len(all_alerts),
            "critical": sum(1 for a in all_alerts if a.get("urgency") == "critical"),
            "high": sum(1 for a in all_alerts if a.get("urgency") == "high"),
            "medium": sum(1 for a in all_alerts if a.get("urgency") == "medium"),
            "low": sum(1 for a in all_alerts if a.get("urgency") == "low"),
            "drafts_created": drafts_created
        },
        "snapshot": snapshot,
        "alerts": all_alerts
    }

    # Write pulse
    with open(PULSE_PATH, "w") as f:
        json.dump(pulse, f, indent=2)

    log.info(f"Pulse written: {len(all_alerts)} alerts, {drafts_created} drafts created")
    return pulse


def run_daemon(interval_seconds=3600):
    """Run continuously."""
    log.info(f"Heartbeat daemon starting (interval: {interval_seconds}s)")
    while True:
        try:
            pulse = generate_pulse()
            if pulse.get("summary", {}).get("critical", 0) > 0:
                log.warning(f"CRITICAL alerts: {pulse['summary']['critical']}")
        except Exception as e:
            log.error(f"Heartbeat error: {e}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        run_daemon()
    elif "--test" in sys.argv:
        pulse = generate_pulse()
        print(json.dumps(pulse, indent=2))
    else:
        # Single run (for Task Scheduler)
        generate_pulse()
