"""Reset all projects to pending status for re-extraction."""
import sqlite3

db_path = r"D:\_CLAUDE-TOOLS\spine-passive\data\knowledge.db"
conn = sqlite3.connect(db_path)

# Reset all projects to pending
conn.execute("UPDATE projects SET extraction_status = 'pending', extraction_error = NULL")
conn.commit()

# Verify
count = conn.execute("SELECT COUNT(*) FROM projects WHERE extraction_status = 'pending'").fetchone()[0]
print(f"Reset {count} projects to pending status")

conn.close()
