#!/usr/bin/env python3
"""
Spine Passive Learner - CLI Entry Point

Learn BIM patterns from your Revit projects.

Usage:
    python -m spine_passive init
    python -m spine_passive scan "D:\\001 - PROJECTS" --recursive
    python -m spine_passive extract --limit 20
    python -m spine_passive extract --overnight
    python -m spine_passive analyze
    python -m spine_passive stats
    python -m spine_passive recommend "path/to/project.rvt"
    python -m spine_passive export patterns.json
"""

import argparse
import logging
import sys
import json
from pathlib import Path
from datetime import datetime

from .database import Database
from .extractor import RevitExtractor, scan_for_revit_files
from .analyzer import PatternAnalyzer
from .recommender import ProjectRecommender, export_to_json

# Setup logging
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging(verbose: bool = False, log_file: bool = True):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_path = LOG_DIR / f"spine_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        handlers.append(logging.FileHandler(log_path))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers
    )

    return logging.getLogger(__name__)


def cmd_init(args):
    """Initialize the database."""
    logger = setup_logging(args.verbose, log_file=False)
    logger.info("Initializing Spine Passive Learner database...")

    db = Database()
    db.initialize()

    logger.info(f"Database created at: {db.db_path}")
    print(f"\nDatabase initialized: {db.db_path}")
    print("\nNext steps:")
    print("  1. Scan for projects: python -m spine_passive scan \"D:\\001 - PROJECTS\" --recursive")
    print("  2. Start Revit with MCP Bridge")
    print("  3. Run extraction: python -m spine_passive extract --overnight")


def cmd_scan(args):
    """Scan directories for Revit files."""
    logger = setup_logging(args.verbose)
    db = Database()

    # Initialize if needed
    if not db.db_path.exists():
        db.initialize()

    paths = args.paths if args.paths else ["."]

    total_results = {"scanned": 0, "added": 0, "updated": 0, "skipped": 0}

    for scan_path in paths:
        logger.info(f"Scanning: {scan_path}")
        results = scan_for_revit_files(scan_path, db, recursive=args.recursive)

        if "error" in results:
            logger.error(results["error"])
            continue

        total_results["scanned"] += results["scanned"]
        total_results["added"] += results["added"]
        total_results["updated"] += results["updated"]
        total_results["skipped"] += results["skipped"]

        logger.info(f"  Found: {results['scanned']}, Added: {results['added']}, "
                   f"Updated: {results['updated']}, Skipped: {results['skipped']}")

    print(f"\n=== Scan Complete ===")
    print(f"Total scanned: {total_results['scanned']}")
    print(f"New projects: {total_results['added']}")
    print(f"Updated: {total_results['updated']}")
    print(f"Skipped (backups): {total_results['skipped']}")

    # Show pending count
    pending = db.get_pending_projects()
    print(f"\nPending extraction: {len(pending)} projects")


def cmd_extract(args):
    """Extract data from Revit projects."""
    logger = setup_logging(args.verbose)
    db = Database()

    if not db.db_path.exists():
        print("Database not initialized. Run: python -m spine_passive init")
        return

    extractor = RevitExtractor(db, revit_version=args.revit_version)

    # Check if Revit is running
    if not extractor.is_revit_running():
        print("ERROR: Revit MCP Bridge not responding.")
        print(f"Make sure Revit {args.revit_version} is running with MCP Bridge loaded.")
        return

    logger.info("Revit MCP Bridge connected!")

    if args.project:
        # Extract single project
        filepath = str(Path(args.project).resolve())
        project = db.get_project_by_path(filepath)

        if not project:
            # Add to database first
            stat = Path(filepath).stat()
            db.add_project(
                filepath=filepath,
                filename=Path(filepath).name,
                file_size=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime)
            )
            project = db.get_project_by_path(filepath)

        logger.info(f"Extracting: {filepath}")
        success, msg = extractor.open_project(filepath)
        if success:
            results = extractor.extract_all(project["id"])
            extractor.close_project(save=False)
            print(json.dumps(results, indent=2))
        else:
            print(f"Failed to open: {msg}")
    else:
        # Batch extraction
        limit = args.limit
        if args.overnight:
            limit = None  # No limit for overnight
            logger.info("=== OVERNIGHT EXTRACTION MODE ===")

        results = extractor.run_batch_extraction(limit=limit, cooldown=args.cooldown)

        print(f"\n=== Extraction Complete ===")
        print(f"Total: {results['total']}")
        print(f"Success: {results['success']}")
        print(f"Failed: {results['failed']}")
        print(f"Skipped: {results['skipped']}")

        # Run analysis after extraction
        if results["success"] > 0 and not args.skip_analysis:
            logger.info("Running pattern analysis...")
            analyzer = PatternAnalyzer(db)
            analyzer.analyze_all()
            logger.info("Pattern analysis complete!")


def cmd_analyze(args):
    """Analyze patterns from extracted data."""
    logger = setup_logging(args.verbose, log_file=False)
    db = Database()

    if not db.db_path.exists():
        print("Database not initialized. Run: python -m spine_passive init")
        return

    analyzer = PatternAnalyzer(db)

    if args.type:
        # Analyze specific type
        method_map = {
            "sheets": analyzer.analyze_sheet_patterns,
            "sizes": analyzer.analyze_size_patterns,
            "families": analyzer.analyze_family_usage,
            "views": analyzer.analyze_view_patterns,
            "rooms": analyzer.analyze_room_patterns,
            "walls": analyzer.analyze_wall_patterns,
        }

        if args.type in method_map:
            results = method_map[args.type]()
            print(json.dumps(results, indent=2, default=str))
        else:
            print(f"Unknown analysis type: {args.type}")
            print(f"Available: {', '.join(method_map.keys())}")
    else:
        # Run all analyses
        results = analyzer.analyze_all()

        # Print summary
        print(analyzer.get_pattern_summary())


def cmd_stats(args):
    """Show database statistics."""
    db = Database()

    if not db.db_path.exists():
        print("Database not initialized. Run: python -m spine_passive init")
        return

    stats = db.get_stats()

    print("=== Spine Passive Learner Statistics ===\n")

    print("Projects:")
    proj = stats["projects"]
    print(f"  Total tracked: {proj['total']}")
    print(f"  Pending: {proj['pending']}")
    print(f"  Complete: {proj['complete']}")
    print(f"  Errors: {proj['errors']}")

    print(f"\nExtracted Data:")
    print(f"  Sheets: {stats['total_sheets']}")
    print(f"  Views: {stats['total_views']}")
    print(f"  Levels: {stats['total_levels']}")
    print(f"  Families: {stats['total_families']}")
    print(f"  Wall Types: {stats['total_wall_types']}")
    print(f"  Rooms: {stats['total_rooms']}")

    print(f"\nLearned Patterns: {stats['total_patterns']}")

    if stats["averages"] and stats["averages"].get("avg_sheets"):
        print(f"\nAverages (completed projects):")
        avg = stats["averages"]
        print(f"  Sheets per project: {avg['avg_sheets']:.1f}")
        print(f"  Views per project: {avg['avg_views']:.1f}")
        print(f"  Levels per project: {avg['avg_levels']:.1f}")
        print(f"  Rooms per project: {avg['avg_rooms']:.1f}")


def cmd_recommend(args):
    """Get recommendations for a project."""
    logger = setup_logging(args.verbose, log_file=False)
    db = Database()

    if not db.db_path.exists():
        print("Database not initialized. Run: python -m spine_passive init")
        return

    # Check if project is in database
    filepath = str(Path(args.project).resolve())
    project = db.get_project_by_path(filepath)

    if not project or project["extraction_status"] != "complete":
        print(f"Project not extracted yet: {args.project}")
        print("Run extraction first, or the recommender will use limited data.")

        # Try to get data from Revit directly
        extractor = RevitExtractor(db)
        if extractor.is_revit_running():
            print("Attempting to get live data from Revit...")
            success, msg = extractor.open_project(filepath)
            if success:
                project_data = {
                    "sheet_count": len(extractor.get_sheets()),
                    "level_count": len(extractor.get_levels()),
                    "view_count": len(extractor.get_views()),
                    "room_count": len(extractor.get_rooms()),
                    "sheets": extractor.get_sheets()
                }
                extractor.close_project(save=False)
            else:
                print(f"Could not open project: {msg}")
                return
        else:
            print("Revit not running. Cannot analyze project.")
            return
    else:
        # Use extracted data
        project_data = {
            "sheet_count": project["sheet_count"],
            "level_count": project["level_count"],
            "view_count": project["view_count"],
            "room_count": project["room_count"],
            "sheets": db.get_sheets_for_project(project["id"])
        }

    recommender = ProjectRecommender(db)

    if args.quick:
        print(recommender.get_quick_summary(project_data))
    else:
        analysis = recommender.analyze_new_project(project_data)
        print(json.dumps(analysis, indent=2, default=str))


def cmd_export(args):
    """Export patterns to JSON or Claude Memory."""
    logger = setup_logging(args.verbose, log_file=False)
    db = Database()

    if not db.db_path.exists():
        print("Database not initialized. Run: python -m spine_passive init")
        return

    if args.to_memory:
        # Export to Claude Memory MCP
        print("Exporting to Claude Memory...")
        patterns = db.get_patterns()
        print(f"Would export {len(patterns)} patterns to Claude Memory MCP")
        print("(Claude Memory integration coming soon)")
    else:
        # Export to JSON file
        output = args.output or "exports/patterns.json"
        output_path = Path(__file__).parent.parent.parent / output

        result = export_to_json(db, str(output_path))
        print(f"Exported {result['pattern_count']} patterns to: {result['path']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Spine Passive Learner - Learn BIM patterns from your Revit projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m spine_passive init
  python -m spine_passive scan "D:\\001 - PROJECTS" --recursive
  python -m spine_passive extract --overnight --limit 50
  python -m spine_passive analyze
  python -m spine_passive stats
  python -m spine_passive recommend "path/to/project.rvt"
"""
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init
    p_init = subparsers.add_parser("init", help="Initialize database")
    p_init.set_defaults(func=cmd_init)

    # scan
    p_scan = subparsers.add_parser("scan", help="Scan directories for .rvt files")
    p_scan.add_argument("paths", nargs="*", help="Directories to scan")
    p_scan.add_argument("-r", "--recursive", action="store_true", default=True,
                        help="Scan recursively (default: True)")
    p_scan.add_argument("--no-recursive", action="store_false", dest="recursive",
                        help="Don't scan recursively")
    p_scan.set_defaults(func=cmd_scan)

    # extract
    p_extract = subparsers.add_parser("extract", help="Extract data from Revit projects")
    p_extract.add_argument("--project", "-p", help="Extract single project")
    p_extract.add_argument("--limit", "-l", type=int, help="Limit number of projects")
    p_extract.add_argument("--overnight", action="store_true",
                           help="Overnight mode (no limit, full extraction)")
    p_extract.add_argument("--cooldown", type=int, default=5,
                           help="Seconds between projects (default: 5)")
    p_extract.add_argument("--revit-version", default="2026", choices=["2025", "2026"],
                           help="Revit version (default: 2026)")
    p_extract.add_argument("--skip-analysis", action="store_true",
                           help="Skip pattern analysis after extraction")
    p_extract.set_defaults(func=cmd_extract)

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze patterns from extracted data")
    p_analyze.add_argument("--type", "-t",
                           choices=["sheets", "sizes", "families", "views", "rooms", "walls"],
                           help="Analyze specific type only")
    p_analyze.set_defaults(func=cmd_analyze)

    # stats
    p_stats = subparsers.add_parser("stats", help="Show database statistics")
    p_stats.set_defaults(func=cmd_stats)

    # recommend
    p_recommend = subparsers.add_parser("recommend", help="Get recommendations for a project")
    p_recommend.add_argument("project", help="Path to .rvt file")
    p_recommend.add_argument("--quick", "-q", action="store_true",
                             help="Quick one-line summary")
    p_recommend.set_defaults(func=cmd_recommend)

    # export
    p_export = subparsers.add_parser("export", help="Export patterns")
    p_export.add_argument("output", nargs="?", help="Output JSON file path")
    p_export.add_argument("--to-memory", action="store_true",
                          help="Export to Claude Memory MCP")
    p_export.set_defaults(func=cmd_export)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
