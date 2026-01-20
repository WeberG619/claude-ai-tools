"""Fix stuck in_progress files."""
import sqlite3

db_path = r"D:\_CLAUDE-TOOLS\spine-passive\data\knowledge.db"
conn = sqlite3.connect(db_path)
conn.execute("UPDATE projects SET extraction_status = 'pending' WHERE extraction_status = 'in_progress'")
conn.commit()
print("Fixed in_progress files")

# Show updated stats
for row in conn.execute("SELECT extraction_status, COUNT(*) FROM projects GROUP BY extraction_status"):
    print(f"  {row[0]}: {row[1]}")
conn.close()
