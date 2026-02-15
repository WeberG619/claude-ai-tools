"""
Client File Organizer - Main entry point.

Automatically organizes files into client/project folder structures.

Usage:
    # Preview organization
    python main.py preview /path/to/inbox --base /path/to/projects

    # Organize files (copy)
    python main.py organize /path/to/inbox --base /path/to/projects

    # Organize files (move)
    python main.py organize /path/to/inbox --base /path/to/projects --move

    # With configuration file
    python main.py organize /path/to/inbox --config clients.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

from matchers import ClientMatcher, ProjectMatcher, FileTypeMatcher
from organizers import FileOrganizer, BatchOrganizer


def load_config(config_path: str) -> Dict:
    """Load configuration from JSON file."""
    with open(config_path) as f:
        return json.load(f)


def print_preview(preview: Dict):
    """Print preview results."""
    print("\n" + "=" * 60)
    print("FILE ORGANIZATION PREVIEW")
    print("=" * 60)

    print(f"\nTotal files scanned: {preview['total_files']}")
    print(f"Would organize: {len(preview['would_organize'])}")
    print(f"Would skip: {len(preview['would_skip'])}")

    if preview['would_organize']:
        print("\n--- Files to organize ---")
        for item in preview['would_organize'][:20]:  # Limit output
            print(f"\n  {Path(item['source']).name}")
            print(f"    → {item['destination']}")
            if item['client']:
                print(f"    Client: {item['client']}")
            if item['project']:
                print(f"    Project: {item['project']}")

        if len(preview['would_organize']) > 20:
            print(f"\n  ... and {len(preview['would_organize']) - 20} more files")

    if preview['would_skip']:
        print("\n--- Files to skip ---")
        for item in preview['would_skip'][:10]:
            print(f"  {Path(item['source']).name}: {item['reason']}")

    print("\n" + "=" * 60)


def print_results(results, summary: Dict):
    """Print organization results."""
    print("\n" + "=" * 60)
    print("FILE ORGANIZATION COMPLETE")
    print("=" * 60)

    print(f"\nTotal files processed: {summary['total_files']}")

    print("\nActions taken:")
    for action, count in summary['by_action'].items():
        print(f"  {action}: {count}")

    if summary['by_client']:
        print("\nBy client:")
        for client, count in sorted(summary['by_client'].items()):
            print(f"  {client}: {count}")

    if summary['by_project']:
        print("\nBy project:")
        for project, count in sorted(summary['by_project'].items())[:10]:
            print(f"  {project}: {count}")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Organize files into project folders")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Preview command
    preview_parser = subparsers.add_parser("preview", help="Preview file organization")
    preview_parser.add_argument("source", help="Source directory to scan")
    preview_parser.add_argument("--base", required=True, help="Base directory for organized files")
    preview_parser.add_argument("--config", help="Configuration file path")
    preview_parser.add_argument("--extensions", nargs="+", help="File extensions to include")
    preview_parser.add_argument("--no-recursive", action="store_true", help="Don't scan subdirectories")

    # Organize command
    org_parser = subparsers.add_parser("organize", help="Organize files")
    org_parser.add_argument("source", help="Source directory to organize")
    org_parser.add_argument("--base", required=True, help="Base directory for organized files")
    org_parser.add_argument("--config", help="Configuration file path")
    org_parser.add_argument("--move", action="store_true", help="Move files instead of copy")
    org_parser.add_argument("--extensions", nargs="+", help="File extensions to include")
    org_parser.add_argument("--no-recursive", action="store_true", help="Don't scan subdirectories")
    org_parser.add_argument("--output", help="Export results to file")

    args = parser.parse_args()

    # Load configuration
    client_config = {}
    project_registry = {}

    if args.config:
        config = load_config(args.config)
        client_config = config.get("clients", {})
        project_registry = config.get("projects", {})

    # Create organizer
    organizer = FileOrganizer(
        base_path=args.base,
        client_config=client_config,
        project_registry=project_registry
    )
    batch = BatchOrganizer(organizer)

    # Determine extensions
    extensions = args.extensions
    if not extensions:
        # Default architecture file types
        extensions = [
            ".pdf", ".dwg", ".dxf", ".rvt", ".rfa",
            ".jpg", ".jpeg", ".png", ".xlsx", ".docx"
        ]

    recursive = not args.no_recursive

    if args.command == "preview":
        files = batch.scan_directory(args.source, extensions, recursive)
        preview = batch.preview(files)
        print_preview(preview)

    elif args.command == "organize":
        mode = "move" if args.move else "copy"
        results = batch.organize_directory(
            args.source,
            extensions=extensions,
            mode=mode,
            recursive=recursive
        )
        summary = organizer.get_summary()
        print_results(results, summary)

        if args.output:
            batch.export_results(args.output)
            print(f"\nResults exported to: {args.output}")


if __name__ == "__main__":
    main()
