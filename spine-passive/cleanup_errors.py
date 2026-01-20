"""Clean up error files - remove backups and families, reset others."""
import sqlite3

db_path = r"D:\_CLAUDE-TOOLS\spine-passive\data\knowledge.db"
conn = sqlite3.connect(db_path)

# Get all error projects
errors = conn.execute("""
    SELECT id, filename, filepath FROM projects WHERE extraction_status = 'error'
""").fetchall()

to_remove = []
to_retry = []

for pid, filename, filepath in errors:
    filename_lower = filename.lower()
    filepath_lower = filepath.lower()

    # Remove backup files
    if "backup" in filename_lower or "-bak" in filename_lower or "_bak" in filename_lower:
        to_remove.append((pid, filename, "backup file"))
        continue

    # Remove family files (in Family folders)
    if "/family/" in filepath_lower or "\\family\\" in filepath_lower:
        to_remove.append((pid, filename, "family file"))
        continue

    # Reset others for retry
    to_retry.append((pid, filename))

print("=== FILES TO REMOVE FROM TRACKING ===")
for pid, filename, reason in to_remove:
    print(f"  {filename} ({reason})")

print(f"\n=== FILES TO RETRY ({len(to_retry)}) ===")
for pid, filename in to_retry[:5]:
    print(f"  {filename}")
if len(to_retry) > 5:
    print(f"  ... and {len(to_retry) - 5} more")

# Confirm and execute
print(f"\nRemoving {len(to_remove)} files from tracking...")
for pid, filename, reason in to_remove:
    conn.execute("DELETE FROM projects WHERE id = ?", (pid,))

print(f"Resetting {len(to_retry)} files to pending for retry...")
for pid, filename in to_retry:
    conn.execute("UPDATE projects SET extraction_status = 'pending', extraction_error = NULL WHERE id = ?", (pid,))

conn.commit()
print("\nDone!")

# Show updated stats
print("\n=== UPDATED STATS ===")
for row in conn.execute("SELECT extraction_status, COUNT(*) FROM projects GROUP BY extraction_status"):
    print(f"  {row[0]}: {row[1]}")

conn.close()
