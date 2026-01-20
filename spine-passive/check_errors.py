"""Check error files and categorize them."""
import sqlite3
import os

db_path = r"D:\_CLAUDE-TOOLS\spine-passive\data\knowledge.db"
conn = sqlite3.connect(db_path)

print("=== ERROR FILES ANALYSIS ===\n")

# Get all error projects
errors = conn.execute("""
    SELECT filename, filepath, extraction_error
    FROM projects
    WHERE extraction_status = 'error'
    ORDER BY extraction_error
""").fetchall()

print(f"Total error files: {len(errors)}\n")

# Categorize errors
categories = {}
for filename, filepath, error in errors:
    # Simplify error message for categorization
    if error:
        if "not found" in error.lower():
            cat = "File not found"
        elif "timeout" in error.lower():
            cat = "Timeout"
        elif "corrupt" in error.lower():
            cat = "Corrupt file"
        elif "version" in error.lower():
            cat = "Version mismatch"
        elif "open" in error.lower():
            cat = "Could not open"
        else:
            cat = error[:50] if len(error) > 50 else error
    else:
        cat = "Unknown error"

    if cat not in categories:
        categories[cat] = []
    categories[cat].append((filename, filepath))

# Print by category
for cat, files in sorted(categories.items(), key=lambda x: -len(x[1])):
    print(f"\n--- {cat} ({len(files)} files) ---")
    for filename, filepath in files[:5]:  # Show first 5 of each
        print(f"  {filename}")
    if len(files) > 5:
        print(f"  ... and {len(files) - 5} more")

# Check if files actually exist
print("\n\n=== FILE EXISTENCE CHECK ===")
missing = 0
exists = 0
for filename, filepath, error in errors:
    # Convert WSL path to Windows if needed
    win_path = filepath
    if filepath.startswith("/mnt/"):
        parts = filepath[5:].split("/", 1)
        if len(parts) >= 1:
            drive = parts[0].upper()
            rest = parts[1] if len(parts) > 1 else ""
            win_path = f"{drive}:\\{rest.replace('/', '\\')}"

    if os.path.exists(win_path):
        exists += 1
    else:
        missing += 1

print(f"Files that exist: {exists}")
print(f"Files missing: {missing}")

conn.close()
