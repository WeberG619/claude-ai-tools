# -*- coding: utf-8 -*-
"""Update pipeline.db with latest submission results."""
import sqlite3
import json
from datetime import datetime

db_path = '/mnt/d/_CLAUDE-TOOLS/opportunityengine/pipeline.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

now = datetime.now().isoformat()

# New submissions from _submit_claude_jobs.py
new_opps = [
    {
        'source': 'upwork',
        'title': 'Sales Representative for SEO Analysis Tool (MISMATCH - sent Claude Code proposal)',
        'source_id': 'https://www.upwork.com/jobs/Sales-Representative-for-SEO-Analysis-Tool_~022021393',
        'status': 'submitted',
        'score': 20,
        'notes': 'Mismatched search result - sent Claude Code expert proposal to SEO sales job. Waste of connects.',
    },
    {
        'source': 'upwork',
        'title': 'Need Claude-Code Expert for Rapid Learning Sessions',
        'source_id': 'https://www.upwork.com/jobs/Need-Claude-Code-Expert-for-Rapid-Learning-Sessions_',
        'status': 'submitted',
        'score': 95,
        'notes': 'Perfect match. $35/hr rate. Filled 2 screening questions. Submitted successfully.',
    },
]

for opp in new_opps:
    c.execute("""INSERT INTO opportunities (source, title, source_id, status, score, notes, discovered_at, submitted_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
              (opp['source'], opp['title'], opp['source_id'], opp['status'], opp['score'], opp['notes'], now, now))
    print(f"  Added: {opp['title'][:60]} [{opp['status']}]")

conn.commit()

# Summary stats
c.execute("SELECT status, COUNT(*) FROM opportunities GROUP BY status ORDER BY COUNT(*) DESC")
stats = c.fetchall()
print(f"\nPipeline Summary:")
for status, count in stats:
    print(f"  {status}: {count}")

c.execute("SELECT COUNT(*) FROM opportunities WHERE status = 'submitted' AND source = 'upwork'")
upwork_submitted = c.fetchone()[0]
print(f"\nUpwork proposals submitted: {upwork_submitted}")

c.execute("SELECT COUNT(*) FROM opportunities WHERE status = 'submitted' AND source = 'reddit'")
reddit_submitted = c.fetchone()[0]
print(f"Reddit DMs sent: {reddit_submitted}")

c.execute("SELECT title, score FROM opportunities WHERE status = 'submitted' ORDER BY submitted_at DESC LIMIT 15")
recent = c.fetchall()
print(f"\nRecent submissions:")
for title, score in recent:
    print(f"  [{score}] {title[:65]}")

conn.close()
