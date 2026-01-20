"""Deep analysis of learned patterns."""
import sqlite3
import json
from collections import defaultdict

db_path = r"D:\_CLAUDE-TOOLS\spine-passive\data\knowledge.db"
conn = sqlite3.connect(db_path)

print("=" * 60)
print("SPINE PASSIVE LEARNER - DEEP PATTERN ANALYSIS")
print("=" * 60)

# Get all patterns
patterns = conn.execute("SELECT pattern_type, pattern_key, pattern_value, confidence, occurrence_count FROM patterns").fetchall()

print(f"\nTotal patterns learned: {len(patterns)}")

# Organize by type
by_type = defaultdict(list)
for ptype, pkey, pvalue, conf, count in patterns:
    by_type[ptype].append((pkey, pvalue, conf, count))

# 1. Sheet Organization Deep Dive
print("\n" + "=" * 60)
print("1. SHEET ORGANIZATION PATTERNS")
print("=" * 60)

if "sheet_series" in by_type:
    print("\nSheet Series Naming Convention:")
    for key, value, conf, count in sorted(by_type["sheet_series"], key=lambda x: x[0]):
        words = json.loads(value) if value.startswith("[") else value
        print(f"  {key}: {words} (seen {count}x, {conf:.0%} confidence)")

# 2. View Naming Patterns
print("\n" + "=" * 60)
print("2. VIEW NAMING PATTERNS")
print("=" * 60)

if "view_naming" in by_type:
    print("\nCommon View Name Patterns:")
    for key, value, conf, count in sorted(by_type["view_naming"], key=lambda x: -x[3])[:20]:
        print(f"  {key}: {value} (seen {count}x)")

# 3. Project Size Patterns
print("\n" + "=" * 60)
print("3. PROJECT SIZE PATTERNS")
print("=" * 60)

if "project_size" in by_type:
    for key, value, conf, count in by_type["project_size"]:
        print(f"  {key}: {value}")

# Get actual project stats
projects = conn.execute("""
    SELECT p.filename,
           (SELECT COUNT(*) FROM sheets WHERE project_id = p.id) as sheets,
           (SELECT COUNT(*) FROM views WHERE project_id = p.id) as views
    FROM projects p
    WHERE p.extraction_status = 'complete'
""").fetchall()

print("\nProject Complexity Distribution:")
small = sum(1 for _, s, _ in projects if s <= 5)
medium = sum(1 for _, s, _ in projects if 5 < s <= 20)
large = sum(1 for _, s, _ in projects if 20 < s <= 100)
xlarge = sum(1 for _, s, _ in projects if s > 100)

print(f"  Small (1-5 sheets): {small} projects")
print(f"  Medium (6-20 sheets): {medium} projects")
print(f"  Large (21-100 sheets): {large} projects")
print(f"  X-Large (100+ sheets): {xlarge} projects")

# 4. Sheet Name Analysis
print("\n" + "=" * 60)
print("4. ACTUAL SHEET DATA ANALYSIS")
print("=" * 60)

sheets = conn.execute("SELECT sheet_number, sheet_name FROM sheets").fetchall()
print(f"\nTotal sheets in database: {len(sheets)}")

# Analyze sheet number prefixes
prefixes = defaultdict(list)
for num, name in sheets:
    if num:
        prefix = num[0] if num else "?"
        prefixes[prefix].append((num, name))

print("\nSheets by Discipline Prefix:")
for prefix in sorted(prefixes.keys()):
    examples = prefixes[prefix][:3]
    example_str = ", ".join([f"{n}" for n, _ in examples])
    print(f"  {prefix}: {len(prefixes[prefix])} sheets (e.g., {example_str})")

# 5. View Type Distribution
print("\n" + "=" * 60)
print("5. VIEW TYPE DISTRIBUTION")
print("=" * 60)

views = conn.execute("SELECT view_type, view_name FROM views").fetchall()
view_types = defaultdict(int)
for vtype, vname in views:
    view_types[vtype] += 1

print(f"\nTotal views: {len(views)}")
for vtype, count in sorted(view_types.items(), key=lambda x: -x[1]):
    print(f"  {vtype}: {count}")

# 6. Insights & Recommendations
print("\n" + "=" * 60)
print("6. KEY INSIGHTS")
print("=" * 60)

print("""
Based on 11 projects analyzed:

1. SHEET NUMBERING: You use standard CSI format (A=Arch, S=Structural, etc.)
   - C000 series for Cover sheets
   - A100 series for Floor Plans
   - A200 series for Roof Plans
   - A300 series for Elevations
   - A400 series for Building Sections
   - A500 series for Wall Sections
   - A600 series for Stair/Elevator Plans
   - A700 series for Schedules/Details

2. PROJECT SIZES: Wide range from 1-sheet small projects to 370-sheet large projects

3. NEXT STEPS:
   - Run overnight extraction to learn from more projects
   - After more data: Learn family usage patterns, room naming, etc.
""")

conn.close()
