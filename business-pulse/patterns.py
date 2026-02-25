#!/usr/bin/env python3
"""
Business Pattern Analyzer
==========================
Analyzes historical data to find patterns:
- Average days to payment per client
- Revenue trends (growing/shrinking)
- Work patterns (what days/projects get most hours)
- Client concentration risk
- Seasonal patterns

Writes patterns.json for Claude to reference when making suggestions.

Usage:
  python patterns.py           # Analyze and write patterns.json
  python patterns.py --print   # Analyze and print to stdout
"""

import sqlite3
import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(r"D:\_CLAUDE-TOOLS\crm-accounting\data\business.db")
PATTERNS_PATH = Path(r"D:\_CLAUDE-TOOLS\business-pulse\patterns.json")


def get_db():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def analyze_payment_speed(conn):
    """Average days to payment per client."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            c.name AS client_name,
            AVG(julianday(i.date_paid) - julianday(i.date_issued)) AS avg_days_to_pay,
            MIN(julianday(i.date_paid) - julianday(i.date_issued)) AS fastest_pay,
            MAX(julianday(i.date_paid) - julianday(i.date_issued)) AS slowest_pay,
            COUNT(*) AS paid_invoices
        FROM invoices i
        JOIN clients c ON i.client_id = c.id
        WHERE i.status = 'paid' AND i.date_paid IS NOT NULL
        GROUP BY c.id
        ORDER BY avg_days_to_pay
    """)

    results = []
    for row in cursor.fetchall():
        row = dict(row)
        results.append({
            "client": row["client_name"],
            "avg_days": round(row["avg_days_to_pay"] or 0, 1),
            "fastest": round(row["fastest_pay"] or 0, 1),
            "slowest": round(row["slowest_pay"] or 0, 1),
            "sample_size": row["paid_invoices"],
            "reliability": "fast" if (row["avg_days_to_pay"] or 0) < 15 else "normal" if (row["avg_days_to_pay"] or 0) < 30 else "slow"
        })

    return results


def analyze_revenue_trend(conn):
    """Monthly revenue trend — growing or shrinking?"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            strftime('%Y-%m', date) AS month,
            SUM(amount) AS revenue
        FROM payments
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    """)

    months = [dict(r) for r in cursor.fetchall()]
    months.reverse()

    if len(months) < 2:
        return {"trend": "insufficient_data", "months": months}

    # Simple trend: compare last 3 months average to previous 3
    recent = months[-3:] if len(months) >= 3 else months[-1:]
    older = months[-6:-3] if len(months) >= 6 else months[:len(months)//2]

    recent_avg = sum(m["revenue"] for m in recent) / len(recent) if recent else 0
    older_avg = sum(m["revenue"] for m in older) / len(older) if older else 0

    if older_avg == 0:
        pct_change = 0
    else:
        pct_change = ((recent_avg - older_avg) / older_avg) * 100

    return {
        "trend": "growing" if pct_change > 10 else "shrinking" if pct_change < -10 else "stable",
        "pct_change": round(pct_change, 1),
        "recent_avg": round(recent_avg, 2),
        "older_avg": round(older_avg, 2),
        "months": months
    }


def analyze_client_concentration(conn):
    """How much revenue depends on top clients."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            c.name AS client_name,
            SUM(p.amount) AS total_revenue
        FROM payments p
        JOIN clients c ON p.client_id = c.id
        WHERE strftime('%Y', p.date) = strftime('%Y', 'now')
        GROUP BY c.id
        ORDER BY total_revenue DESC
    """)

    clients = [dict(r) for r in cursor.fetchall()]
    total = sum(c["total_revenue"] for c in clients)

    if total == 0:
        return {"risk": "no_data", "clients": []}

    for c in clients:
        c["pct_of_total"] = round(c["total_revenue"] / total * 100, 1)

    top_client_pct = clients[0]["pct_of_total"] if clients else 0
    top_3_pct = sum(c["pct_of_total"] for c in clients[:3])

    risk = "high" if top_client_pct > 50 else "medium" if top_3_pct > 80 else "healthy"

    return {
        "risk": risk,
        "total_ytd_revenue": round(total, 2),
        "top_client_pct": top_client_pct,
        "top_3_pct": round(top_3_pct, 1),
        "clients": clients[:10],
        "insight": f"Top client = {top_client_pct}% of revenue" if risk == "high"
                   else f"Top 3 clients = {top_3_pct:.0f}% of revenue" if risk == "medium"
                   else "Revenue is well-distributed"
    }


def analyze_work_patterns(conn):
    """When and what Weber works on most."""
    cursor = conn.cursor()

    # Hours by day of week
    cursor.execute("""
        SELECT
            CASE CAST(strftime('%w', date) AS INTEGER)
                WHEN 0 THEN 'Sunday'
                WHEN 1 THEN 'Monday'
                WHEN 2 THEN 'Tuesday'
                WHEN 3 THEN 'Wednesday'
                WHEN 4 THEN 'Thursday'
                WHEN 5 THEN 'Friday'
                WHEN 6 THEN 'Saturday'
            END AS day_name,
            CAST(strftime('%w', date) AS INTEGER) AS day_num,
            SUM(hours) AS total_hours,
            AVG(hours) AS avg_hours_per_day,
            COUNT(*) AS entries
        FROM time_entries
        GROUP BY day_num
        ORDER BY day_num
    """)
    by_day = [dict(r) for r in cursor.fetchall()]

    # Hours by project type
    cursor.execute("""
        SELECT
            p.type AS project_type,
            SUM(t.hours) AS total_hours,
            SUM(t.hours * t.rate) AS total_revenue
        FROM time_entries t
        JOIN projects p ON t.project_id = p.id
        GROUP BY p.type
        ORDER BY total_hours DESC
    """)
    by_type = [dict(r) for r in cursor.fetchall()]

    # Average billable rate
    cursor.execute("""
        SELECT
            AVG(rate) AS avg_rate,
            SUM(CASE WHEN billable = 1 THEN hours ELSE 0 END) AS billable_hours,
            SUM(CASE WHEN billable = 0 THEN hours ELSE 0 END) AS non_billable_hours
        FROM time_entries
    """)
    rate_row = dict(cursor.fetchone())
    total_hours = (rate_row.get("billable_hours") or 0) + (rate_row.get("non_billable_hours") or 0)
    billable_ratio = (rate_row.get("billable_hours") or 0) / total_hours * 100 if total_hours > 0 else 0

    return {
        "by_day_of_week": by_day,
        "by_project_type": by_type,
        "avg_billable_rate": round(rate_row.get("avg_rate") or 0, 2),
        "billable_ratio": round(billable_ratio, 1),
        "busiest_day": max(by_day, key=lambda d: d["total_hours"])["day_name"] if by_day else None
    }


def analyze_expense_patterns(conn):
    """Expense trends and categories."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            category,
            SUM(amount) AS total,
            COUNT(*) AS count,
            AVG(amount) AS avg_amount
        FROM expenses
        WHERE strftime('%Y', date) = strftime('%Y', 'now')
        GROUP BY category
        ORDER BY total DESC
    """)
    by_category = [dict(r) for r in cursor.fetchall()]

    total_expenses = sum(c["total"] for c in by_category)
    for c in by_category:
        c["pct_of_total"] = round(c["total"] / total_expenses * 100, 1) if total_expenses > 0 else 0
        c["avg_amount"] = round(c["avg_amount"], 2)

    return {
        "ytd_total": round(total_expenses, 2),
        "by_category": by_category,
        "largest_category": by_category[0]["category"] if by_category else None
    }


def generate_patterns():
    """Run all pattern analyses."""
    conn = get_db()
    if not conn:
        return {"error": "Database not found"}

    try:
        patterns = {
            "generated_at": datetime.now().isoformat(),
            "payment_speed": analyze_payment_speed(conn),
            "revenue_trend": analyze_revenue_trend(conn),
            "client_concentration": analyze_client_concentration(conn),
            "work_patterns": analyze_work_patterns(conn),
            "expense_patterns": analyze_expense_patterns(conn)
        }
    finally:
        conn.close()

    with open(PATTERNS_PATH, "w") as f:
        json.dump(patterns, f, indent=2)

    return patterns


if __name__ == "__main__":
    patterns = generate_patterns()
    if "--print" in sys.argv:
        print(json.dumps(patterns, indent=2))
    else:
        print(f"Patterns written to {PATTERNS_PATH}")
        print(f"  Payment speed entries: {len(patterns.get('payment_speed', []))}")
        print(f"  Revenue trend: {patterns.get('revenue_trend', {}).get('trend', 'unknown')}")
        print(f"  Client risk: {patterns.get('client_concentration', {}).get('risk', 'unknown')}")
