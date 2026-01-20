"""Complete project review for current Revit project."""
import sys
import json
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, r"D:\_CLAUDE-TOOLS\spine-passive\src")

from spine_passive.database import Database
from spine_passive.extractor import RevitExtractor

def main():
    db = Database(Path(r"D:\_CLAUDE-TOOLS\spine-passive\data\knowledge.db"))
    extractor = RevitExtractor(db, "2026")

    if not extractor.is_revit_running():
        print("ERROR: RevitMCPBridge2026 not responding.")
        return

    # Get project info
    project_info = extractor.get_project_info()
    if not project_info:
        print("No project open in Revit.")
        return

    print("=" * 70)
    print("FULL PROJECT REVIEW")
    print("=" * 70)
    print(f"\nProject: {project_info.get('name', 'Unknown')}")
    print(f"Number: {project_info.get('number', 'N/A')}")
    print(f"Address: {project_info.get('address', 'N/A')}")
    print(f"Client: {project_info.get('clientName', 'N/A')}")

    # Get all data
    print("\nGathering data...")
    sheets = extractor.get_sheets()
    views = extractor.get_views()
    levels = extractor.get_levels()

    print(f"  Sheets: {len(sheets)}")
    print(f"  Views: {len(views)}")
    print(f"  Levels: {len(levels)}")

    # === SHEET ANALYSIS ===
    print("\n" + "=" * 70)
    print("SHEET SET ANALYSIS")
    print("=" * 70)

    # Group sheets by discipline
    by_discipline = defaultdict(list)
    for sheet in sheets:
        num = sheet.get("sheetNumber", "") or sheet.get("sheet_number", "")
        name = sheet.get("sheetName", "") or sheet.get("sheet_name", "")
        if num:
            prefix = num[0].upper() if num[0].isalpha() else "?"
            by_discipline[prefix].append((num, name))

    print("\nSheets by Discipline:")
    discipline_names = {
        "A": "Architectural",
        "S": "Structural",
        "M": "Mechanical",
        "E": "Electrical",
        "P": "Plumbing",
        "F": "Fire Protection",
        "C": "Civil",
        "L": "Landscape",
        "G": "General",
        "I": "Interior",
        "T": "Title/Cover"
    }

    for prefix in sorted(by_discipline.keys()):
        sheets_list = by_discipline[prefix]
        disc_name = discipline_names.get(prefix, "Other")
        print(f"\n  [{prefix}] {disc_name} ({len(sheets_list)} sheets):")
        for num, name in sorted(sheets_list)[:10]:
            print(f"      {num}: {name}")
        if len(sheets_list) > 10:
            print(f"      ... and {len(sheets_list) - 10} more")

    # === SHEET SERIES ANALYSIS ===
    print("\n" + "=" * 70)
    print("SHEET SERIES BREAKDOWN")
    print("=" * 70)

    # Group by series (first 2-3 chars)
    by_series = defaultdict(list)
    for sheet in sheets:
        num = sheet.get("sheetNumber", "") or sheet.get("sheet_number", "")
        name = sheet.get("sheetName", "") or sheet.get("sheet_name", "")
        if num and len(num) >= 2:
            # Extract series (e.g., A1, A2, S1, etc.)
            series = ""
            for i, char in enumerate(num):
                if char.isalpha():
                    series += char.upper()
                elif char.isdigit():
                    series += char
                    break
            if series:
                by_series[series].append((num, name))

    for series in sorted(by_series.keys()):
        sheets_list = by_series[series]
        print(f"\n  {series}xx Series ({len(sheets_list)} sheets):")
        for num, name in sorted(sheets_list):
            print(f"      {num}: {name}")

    # === VIEW ANALYSIS ===
    print("\n" + "=" * 70)
    print("VIEW ANALYSIS")
    print("=" * 70)

    by_type = defaultdict(list)
    for view in views:
        vtype = view.get("viewType", "") or view.get("view_type", "Unknown")
        vname = view.get("viewName", "") or view.get("view_name", "")
        by_type[vtype].append(vname)

    print("\nViews by Type:")
    for vtype in sorted(by_type.keys(), key=lambda x: -len(by_type[x])):
        count = len(by_type[vtype])
        print(f"  {vtype}: {count}")

    # Check for views not on sheets
    views_on_sheets = set()
    # This would need sheet viewport data - skip for now

    # === LEVEL ANALYSIS ===
    print("\n" + "=" * 70)
    print("LEVEL ANALYSIS")
    print("=" * 70)

    if levels:
        print(f"\nLevels ({len(levels)}):")
        for level in sorted(levels, key=lambda x: x.get("elevation", 0)):
            name = level.get("name", "Unknown")
            elev = level.get("elevation", 0)
            print(f"  {name}: {elev:.2f}'")
    else:
        print("\n  No level data retrieved (API limitation)")

    # === COMPLETENESS CHECK ===
    print("\n" + "=" * 70)
    print("COMPLETENESS CHECK")
    print("=" * 70)

    issues = []
    warnings = []

    # Check for cover sheet
    has_cover = any("cover" in (s.get("sheetName", "") or s.get("sheet_name", "")).lower()
                    for s in sheets)
    if not has_cover:
        issues.append("No cover sheet detected")

    # Check for index
    has_index = any("index" in (s.get("sheetName", "") or s.get("sheet_name", "")).lower()
                    for s in sheets)
    if not has_index and len(sheets) > 5:
        warnings.append("No sheet index detected (recommended for sets > 5 sheets)")

    # Check architectural completeness
    arch_sheets = by_discipline.get("A", [])
    arch_series = set()
    for num, name in arch_sheets:
        if len(num) >= 2:
            for i, char in enumerate(num):
                if char.isdigit():
                    arch_series.add(num[0] + char)
                    break

    # Typical architectural series
    typical_arch = {"A1": "Floor Plans", "A2": "Roof/Ceiling Plans", "A3": "Elevations",
                    "A4": "Sections", "A5": "Wall Sections", "A6": "Stair Plans",
                    "A7": "Schedules/Details", "A8": "Window/Door Details"}

    missing_arch = []
    for series, desc in typical_arch.items():
        if series not in arch_series:
            missing_arch.append(f"{series} ({desc})")

    if missing_arch and len(arch_sheets) > 10:
        warnings.append(f"Potentially missing architectural series: {', '.join(missing_arch[:4])}")

    # Check for schedules
    has_door_schedule = any("door" in (s.get("sheetName", "") or "").lower() and
                           "schedule" in (s.get("sheetName", "") or "").lower()
                           for s in sheets)
    has_window_schedule = any("window" in (s.get("sheetName", "") or "").lower() and
                              "schedule" in (s.get("sheetName", "") or "").lower()
                              for s in sheets)

    if not has_door_schedule:
        warnings.append("No door schedule sheet detected")
    if not has_window_schedule:
        warnings.append("No window schedule sheet detected")

    # Print issues
    if issues:
        print("\n⚠️  ISSUES:")
        for issue in issues:
            print(f"    • {issue}")

    if warnings:
        print("\n📋 WARNINGS:")
        for warning in warnings:
            print(f"    • {warning}")

    if not issues and not warnings:
        print("\n✅ No major issues detected")

    # === OUTPUT RAW DATA ===
    print("\n" + "=" * 70)
    print("RAW DATA EXPORT")
    print("=" * 70)

    # Save to JSON for reference
    output = {
        "project_info": project_info,
        "sheet_count": len(sheets),
        "view_count": len(views),
        "level_count": len(levels),
        "sheets": sheets,
        "disciplines": {k: len(v) for k, v in by_discipline.items()},
        "series": {k: len(v) for k, v in by_series.items()},
        "issues": issues,
        "warnings": warnings
    }

    output_path = Path(r"D:\_CLAUDE-TOOLS\spine-passive\data\current_review.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nDetailed data saved to: {output_path}")

if __name__ == "__main__":
    main()
