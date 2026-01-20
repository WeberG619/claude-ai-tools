"""Check detailed error messages."""
import sqlite3

db_path = r"D:\_CLAUDE-TOOLS\spine-passive\data\knowledge.db"
conn = sqlite3.connect(db_path)

print("=== DETAILED ERROR MESSAGES ===\n")

errors = conn.execute("""
    SELECT filename, extraction_error
    FROM projects
    WHERE extraction_status = 'error'
    ORDER BY filename
""").fetchall()

for filename, error in errors:
    print(f"{filename}")
    print(f"  Error: {error}")
    print()

conn.close()
