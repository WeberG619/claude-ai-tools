"""Check error file paths for patterns."""
import sqlite3
from collections import Counter

db_path = r"D:\_CLAUDE-TOOLS\spine-passive\data\knowledge.db"
conn = sqlite3.connect(db_path)

errors = conn.execute("""
    SELECT filepath FROM projects WHERE extraction_status = 'error'
""").fetchall()

# Extract folder names
folders = []
for (path,) in errors:
    # Convert WSL path
    if path.startswith("/mnt/"):
        parts = path[5:].split("/", 1)
        if len(parts) >= 1:
            drive = parts[0].upper()
            rest = parts[1] if len(parts) > 1 else ""
            path = f"{drive}:\\{rest.replace('/', '\\')}"

    # Get parent folder
    if "\\" in path:
        folder = "\\".join(path.split("\\")[:-1])
    else:
        folder = path.rsplit("/", 1)[0] if "/" in path else path
    folders.append(folder)

print("=== ERROR FILES BY FOLDER ===\n")
for folder, count in Counter(folders).most_common():
    print(f"{count:3d} files: {folder}")

# Check for backup files
print("\n=== BACKUP FILE CHECK ===")
backup_count = 0
for (path,) in errors:
    filename = path.split("/")[-1].split("\\")[-1]
    if "backup" in filename.lower() or "bak" in filename.lower():
        backup_count += 1
        print(f"  {filename}")

print(f"\nTotal backup files in errors: {backup_count}")

conn.close()
