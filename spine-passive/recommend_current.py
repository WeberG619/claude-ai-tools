"""Get recommendations for the currently open Revit project."""
import sys
import json
from pathlib import Path
sys.path.insert(0, r"D:\_CLAUDE-TOOLS\spine-passive\src")

from spine_passive.database import Database
from spine_passive.extractor import RevitExtractor
from spine_passive.recommender import ProjectRecommender

def main():
    print("=" * 60)
    print("SPINE RECOMMENDATIONS FOR CURRENT PROJECT")
    print("=" * 60)

    db = Database(Path(r"D:\_CLAUDE-TOOLS\spine-passive\data\knowledge.db"))
    extractor = RevitExtractor(db, "2026")

    # Check if Revit is running
    if not extractor.is_revit_running():
        print("\nERROR: RevitMCPBridge2026 not responding.")
        print("Make sure Revit 2026 is running with MCP Bridge loaded.")
        return

    print("\nConnected to Revit. Getting project data...")

    # Get current project info
    project_info = extractor.get_project_info()
    if not project_info:
        print("\nNo project open in Revit. Open a project first.")
        return

    project_name = project_info.get("name", "Unknown Project")
    print(f"\nProject: {project_name}")

    # Get sheets, views, levels
    sheets = extractor.get_sheets()
    views = extractor.get_views()
    levels = extractor.get_levels()

    print(f"  Sheets: {len(sheets)}")
    print(f"  Views: {len(views)}")
    print(f"  Levels: {len(levels)}")

    # Build project data for recommender
    project_data = {
        "project_name": project_name,
        "sheet_count": len(sheets),
        "view_count": len(views),
        "level_count": len(levels),
        "sheets": sheets
    }

    # Get recommendations
    recommender = ProjectRecommender(db)
    analysis = recommender.analyze_new_project(project_data)

    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)

    # Phase estimate
    phase = analysis["phase_estimate"]
    print(f"\nEstimated Phase: {phase['phase']} ({phase['confidence']:.0%} confidence)")

    # Completion estimate
    completion = analysis["completion_estimate"]
    print(f"\nCompletion: ~{completion['completion_percent']}%")
    print(f"  Current sheets: {completion['current_sheets']}")
    print(f"  Typical for this size: {completion['typical_sheets']}")
    print(f"  Remaining estimate: {completion['sheets_remaining']} sheets")

    # Similar projects
    similar = analysis["similar_projects"]
    if similar:
        print("\nSimilar Completed Projects:")
        for p in similar[:3]:
            print(f"  - {p['name']}: {p['sheets']} sheets, {p['levels']} levels")

    # Missing sheets
    missing = analysis["missing_sheets"]
    if missing:
        print("\nPotentially Missing Sheet Series:")
        for m in missing[:5]:
            content = ", ".join(m["typical_content"][:3])
            print(f"  - {m['series']}: {content}")

    # Suggestions
    print("\n" + "=" * 60)
    print("SUGGESTIONS")
    print("=" * 60)
    for i, suggestion in enumerate(analysis["suggestions"], 1):
        print(f"  {i}. {suggestion}")

    # Quick summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(recommender.get_quick_summary(project_data))

if __name__ == "__main__":
    main()
