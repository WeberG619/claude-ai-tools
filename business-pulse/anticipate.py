#!/usr/bin/env python3
"""
Anticipation Engine
====================
Forward-looking predictions based on current data and patterns:
- Projects approaching budget limits at current burn rate
- Estimated invoice dates based on project progress
- Client follow-up suggestions based on inactivity
- Cash flow forecast (upcoming payments vs. expenses)
- Workload prediction for the week

Writes anticipations.json for Claude to surface proactively.

Usage:
  python anticipate.py           # Generate anticipations
  python anticipate.py --print   # Print to stdout
"""

import sqlite3
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(r"D:\_CLAUDE-TOOLS\crm-accounting\data\business.db")
PATTERNS_PATH = Path(r"D:\_CLAUDE-TOOLS\business-pulse\patterns.json")
ANTICIPATIONS_PATH = Path(r"D:\_CLAUDE-TOOLS\business-pulse\anticipations.json")


def get_db():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def load_patterns():
    """Load historical patterns for prediction."""
    if PATTERNS_PATH.exists():
        with open(PATTERNS_PATH) as f:
            return json.load(f)
    return {}


def predict_budget_exhaustion(conn):
    """Predict when active projects will hit their budget."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            p.id, p.name AS project_name, c.name AS client_name,
            p.budget, p.start_date,
            COALESCE(SUM(t.hours * t.rate), 0) AS spent,
            COALESCE(SUM(t.hours), 0) AS total_hours,
            COUNT(DISTINCT t.date) AS work_days
        FROM projects p
        JOIN clients c ON p.client_id = c.id
        LEFT JOIN time_entries t ON p.id = t.project_id
        WHERE p.status = 'active' AND p.budget IS NOT NULL AND p.budget > 0
        GROUP BY p.id
    """)

    predictions = []
    for row in cursor.fetchall():
        row = dict(row)
        budget = row["budget"]
        spent = row["spent"]
        remaining = budget - spent
        work_days = row["work_days"]

        if work_days <= 0 or spent <= 0:
            continue

        # Daily burn rate
        daily_burn = spent / work_days
        days_remaining = remaining / daily_burn if daily_burn > 0 else float("inf")

        pct_used = spent / budget * 100

        if days_remaining < 14:  # Less than 2 weeks of budget left
            predictions.append({
                "type": "budget_exhaustion",
                "urgency": "high" if days_remaining < 5 else "medium",
                "project": row["project_name"],
                "client": row["client_name"],
                "budget": budget,
                "spent": round(spent, 2),
                "pct_used": round(pct_used, 1),
                "daily_burn": round(daily_burn, 2),
                "est_days_remaining": round(days_remaining, 0),
                "est_exhaustion_date": (datetime.now() + timedelta(days=days_remaining)).strftime("%Y-%m-%d"),
                "message": f"{row['project_name']} — ${remaining:,.0f} left at ${daily_burn:,.0f}/day burn → ~{days_remaining:.0f} work days remaining"
            })

    return predictions


def predict_invoice_readiness(conn):
    """Predict which projects are ready or nearly ready to invoice."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            p.id, p.name AS project_name, c.name AS client_name,
            COALESCE(SUM(CASE WHEN t.invoiced = 0 AND t.billable = 1 THEN t.hours * t.rate ELSE 0 END), 0) AS unbilled_amount,
            COALESCE(SUM(CASE WHEN t.invoiced = 0 AND t.billable = 1 THEN t.hours ELSE 0 END), 0) AS unbilled_hours,
            MAX(t.date) AS last_entry,
            p.budget,
            COALESCE(SUM(t.hours * t.rate), 0) AS total_billed_and_unbilled
        FROM projects p
        JOIN clients c ON p.client_id = c.id
        LEFT JOIN time_entries t ON p.id = t.project_id
        WHERE p.status IN ('active', 'completed')
        GROUP BY p.id
        HAVING unbilled_amount > 0
        ORDER BY unbilled_amount DESC
    """)

    predictions = []
    for row in cursor.fetchall():
        row = dict(row)
        amount = row["unbilled_amount"]
        hours = row["unbilled_hours"]

        # Suggest invoicing if: significant amount OR project completed OR milestone-worthy
        ready = False
        reason = ""
        if row.get("budget") and row["total_billed_and_unbilled"] >= row["budget"]:
            ready = True
            reason = "Project at/over budget — invoice now"
        elif amount >= 2000:
            ready = True
            reason = f"${amount:,.0f} unbilled — invoice now"
        elif amount >= 1000:
            ready = True
            reason = f"${amount:,.0f} unbilled — consider invoicing"
        elif amount >= 500:
            reason = f"${amount:,.0f} accumulating — invoice soon"

        if amount >= 500:
            predictions.append({
                "type": "invoice_ready",
                "urgency": "high" if ready and amount >= 2000 else "medium" if ready else "low",
                "project": row["project_name"],
                "client": row["client_name"],
                "unbilled_amount": round(amount, 2),
                "unbilled_hours": round(hours, 1),
                "last_entry": row["last_entry"],
                "reason": reason,
                "message": f"{row['project_name']} ({row['client_name']}) — {hours:.1f}h / ${amount:,.0f} → {reason}"
            })

    return predictions


def predict_cash_flow(conn, patterns):
    """Forecast cash flow for next 30 days."""
    cursor = conn.cursor()

    # Expected incoming: invoices due in next 30 days
    cursor.execute("""
        SELECT
            i.invoice_number, c.name AS client_name,
            (i.total - i.amount_paid) AS expected_amount,
            i.date_due
        FROM invoices i
        JOIN clients c ON i.client_id = c.id
        WHERE i.status IN ('sent', 'partial')
          AND i.date_due BETWEEN date('now') AND date('now', '+30 days')
    """)
    expected_in = [dict(r) for r in cursor.fetchall()]
    total_expected_in = sum(r["expected_amount"] for r in expected_in)

    # Known recurring expenses (estimate from patterns)
    cursor.execute("""
        SELECT
            description, vendor,
            AVG(amount) AS avg_amount
        FROM expenses
        WHERE category = 'subscriptions'
        GROUP BY description, vendor
    """)
    recurring = [dict(r) for r in cursor.fetchall()]
    total_recurring = sum(r["avg_amount"] for r in recurring)

    # Recent monthly average expenses
    cursor.execute("""
        SELECT AVG(monthly_total) AS avg_monthly
        FROM (
            SELECT strftime('%Y-%m', date) AS month, SUM(amount) AS monthly_total
            FROM expenses
            GROUP BY month
            ORDER BY month DESC
            LIMIT 3
        )
    """)
    avg_monthly_expense = (cursor.fetchone()["avg_monthly"] or 0)

    forecast = {
        "type": "cash_flow_forecast",
        "period": "next_30_days",
        "expected_incoming": round(total_expected_in, 2),
        "incoming_invoices": expected_in,
        "estimated_expenses": round(avg_monthly_expense, 2),
        "recurring_subscriptions": round(total_recurring, 2),
        "net_forecast": round(total_expected_in - avg_monthly_expense, 2),
        "message": f"Next 30 days: ${total_expected_in:,.0f} expected in, ~${avg_monthly_expense:,.0f} out → net ${total_expected_in - avg_monthly_expense:,.0f}"
    }

    return forecast


def predict_follow_ups(conn, patterns):
    """Suggest proactive client outreach."""
    cursor = conn.cursor()

    # Prospects that haven't been converted
    cursor.execute("""
        SELECT name, email, phone, created_at,
               CAST(julianday('now') - julianday(created_at) AS INTEGER) AS days_since_added
        FROM clients
        WHERE status = 'prospect'
        ORDER BY created_at DESC
    """)
    prospects = [dict(r) for r in cursor.fetchall()]

    # Completed projects with no recent follow-up
    cursor.execute("""
        SELECT
            c.name AS client_name, c.email,
            p.name AS project_name, p.end_date,
            CAST(julianday('now') - julianday(p.end_date) AS INTEGER) AS days_since_completed
        FROM projects p
        JOIN clients c ON p.client_id = c.id
        WHERE p.status = 'completed' AND p.end_date IS NOT NULL
        ORDER BY p.end_date DESC
        LIMIT 10
    """)
    completed = [dict(r) for r in cursor.fetchall()]

    suggestions = []

    for p in prospects:
        if p["days_since_added"] >= 7:
            suggestions.append({
                "type": "follow_up_prospect",
                "urgency": "medium" if p["days_since_added"] > 14 else "low",
                "client": p["name"],
                "email": p["email"],
                "days_waiting": p["days_since_added"],
                "message": f"Prospect {p['name']} added {p['days_since_added']} days ago — follow up?"
            })

    for c in completed:
        days = c["days_since_completed"]
        if 25 <= days <= 35:
            suggestions.append({
                "type": "follow_up_completed",
                "urgency": "low",
                "client": c["client_name"],
                "project": c["project_name"],
                "days_since": days,
                "message": f"{c['client_name']} — {c['project_name']} finished {days} days ago. Check-in email?"
            })

    return suggestions


def generate_anticipations():
    """Run all prediction engines."""
    conn = get_db()
    if not conn:
        return {"error": "Database not found"}

    patterns = load_patterns()

    try:
        budget_predictions = predict_budget_exhaustion(conn)
        invoice_predictions = predict_invoice_readiness(conn)
        cash_flow = predict_cash_flow(conn, patterns)
        follow_ups = predict_follow_ups(conn, patterns)

        anticipations = {
            "generated_at": datetime.now().isoformat(),
            "budget_predictions": budget_predictions,
            "invoice_readiness": invoice_predictions,
            "cash_flow": cash_flow,
            "follow_ups": follow_ups,
            "total_predictions": len(budget_predictions) + len(invoice_predictions) + len(follow_ups)
        }
    finally:
        conn.close()

    with open(ANTICIPATIONS_PATH, "w") as f:
        json.dump(anticipations, f, indent=2)

    return anticipations


if __name__ == "__main__":
    result = generate_anticipations()
    if "--print" in sys.argv:
        print(json.dumps(result, indent=2))
    else:
        print(f"Anticipations written to {ANTICIPATIONS_PATH}")
        print(f"  Budget warnings: {len(result.get('budget_predictions', []))}")
        print(f"  Invoice ready: {len(result.get('invoice_readiness', []))}")
        print(f"  Follow-ups: {len(result.get('follow_ups', []))}")
        cf = result.get("cash_flow", {})
        print(f"  Cash flow forecast: {cf.get('message', 'N/A')}")
