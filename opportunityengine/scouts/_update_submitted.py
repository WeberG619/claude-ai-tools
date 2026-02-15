"""Update pipeline.db - mark opps #139 and #143 as submitted (already on Upwork)."""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('/mnt/d/_CLAUDE-TOOLS/opportunityengine/pipeline.db')
now = datetime.utcnow().isoformat()

for opp_id in [139, 143]:
    conn.execute(
        "UPDATE opportunities SET status='submitted', submitted_at=? WHERE id=? AND status != 'submitted'",
        (now, opp_id)
    )
    conn.execute(
        "UPDATE proposals SET status='submitted', submitted_at=? WHERE opportunity_id=? AND status != 'submitted'",
        (now, opp_id)
    )
    print(f"Opp #{opp_id}: marked submitted")

conn.commit()

# Verify
for opp_id in [139, 143]:
    row = conn.execute('SELECT id, title, status, submitted_at FROM opportunities WHERE id=?', (opp_id,)).fetchone()
    print(f"  Opp #{row[0]}: {row[2]} | submitted_at={row[3]}")
    p = conn.execute('SELECT id, status, submitted_at FROM proposals WHERE opportunity_id=?', (opp_id,)).fetchone()
    if p:
        print(f"  Proposal #{p[0]}: {p[1]} | submitted_at={p[2]}")

conn.close()
print("\nDone.")
