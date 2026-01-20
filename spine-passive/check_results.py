"""Check extraction results."""
import sqlite3

db_path = r"D:\_CLAUDE-TOOLS\spine-passive\data\knowledge.db"
conn = sqlite3.connect(db_path)

print("=== EXTRACTION RESULTS ===")
print()

# Status counts
print("Project Status:")
for row in conn.execute("SELECT extraction_status, COUNT(*) FROM projects GROUP BY extraction_status"):
    print(f"  {row[0]}: {row[1]}")
print()

# Totals
print("Total sheets extracted:", conn.execute("SELECT COUNT(*) FROM sheets").fetchone()[0])
print("Total views extracted:", conn.execute("SELECT COUNT(*) FROM views").fetchone()[0])
print()

# Per-project breakdown
print("Completed Projects:")
for row in conn.execute("""
    SELECT p.filename,
           (SELECT COUNT(*) FROM sheets WHERE project_id = p.id) as sheets,
           (SELECT COUNT(*) FROM views WHERE project_id = p.id) as views
    FROM projects p
    WHERE p.extraction_status = 'complete'
    ORDER BY sheets DESC
"""):
    print(f"  {row[0]}: {row[1]} sheets, {row[2]} views")

conn.close()
