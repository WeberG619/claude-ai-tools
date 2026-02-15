#!/usr/bin/env python3
"""
PDF Markup Analyzer - CLI Entry Point

Extract, categorize, and convert PDF markups to actionable tasks.

Usage:
    python -m pdf_markup_analyzer <input_file> [options]
    python -m pdf_markup_analyzer plans.pdf --output-dir ./reports
    python -m pdf_markup_analyzer markups.csv --format bluebeam --tasks
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Local imports
try:
    from .extractors.pdf_extractor import PyMuPDFExtractor, PYMUPDF_AVAILABLE
    from .extractors.bluebeam_extractor import BluebeamCSVExtractor
    from .categorizer import MarkupCategorizer, MarkupCategory
    from .task_generator import TaskGenerator, TaskPriority
    from .exporters import export_json, export_csv, export_markdown, export_all
except ImportError:
    # Direct execution
    from extractors.pdf_extractor import PyMuPDFExtractor, PYMUPDF_AVAILABLE
    from extractors.bluebeam_extractor import BluebeamCSVExtractor
    from categorizer import MarkupCategorizer, MarkupCategory
    from task_generator import TaskGenerator, TaskPriority
    from exporters import export_json, export_csv, export_markdown, export_all


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="pdf_markup_analyzer",
        description="Extract, categorize, and convert PDF markups to actionable tasks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s document.pdf
      Extract markups from PDF using PyMuPDF

  %(prog)s markups.csv --format bluebeam
      Parse Bluebeam CSV export

  %(prog)s document.pdf --tasks --output-dir ./reports
      Generate tasks and export to multiple formats

  %(prog)s document.pdf --filter-category RFI CORRECTION
      Only process RFI and Correction markups

  %(prog)s markups.csv --format bluebeam --min-priority High
      Generate only High and Critical priority tasks
"""
    )

    # Input
    parser.add_argument(
        "input_file",
        help="Input file (PDF or CSV)"
    )

    parser.add_argument(
        "--format", "-f",
        choices=["auto", "pdf", "bluebeam"],
        default="auto",
        help="Input format (default: auto-detect)"
    )

    # Processing options
    parser.add_argument(
        "--tasks", "-t",
        action="store_true",
        help="Generate tasks from markups"
    )

    parser.add_argument(
        "--project",
        default="Project",
        help="Project name for task generation"
    )

    parser.add_argument(
        "--filter-category",
        nargs="+",
        choices=[c.value for c in MarkupCategory],
        help="Only process these categories"
    )

    parser.add_argument(
        "--min-priority",
        choices=[p.value for p in TaskPriority],
        help="Minimum task priority to include"
    )

    # Output options
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory (default: same as input file)"
    )

    parser.add_argument(
        "--output-format",
        nargs="+",
        choices=["json", "csv", "markdown", "all"],
        default=["json"],
        help="Output format(s)"
    )

    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="Print summary to console"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress all console output except errors"
    )

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Determine format
    input_format = args.format
    if input_format == "auto":
        if input_path.suffix.lower() == ".pdf":
            input_format = "pdf"
        elif input_path.suffix.lower() == ".csv":
            input_format = "bluebeam"
        else:
            print(f"Error: Cannot auto-detect format for {input_path.suffix}", file=sys.stderr)
            sys.exit(1)

    # Set output directory
    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    if not args.quiet:
        print(f"Processing: {input_path}")
        print(f"Format: {input_format}")

    # Extract markups
    try:
        markups = extract_markups(input_path, input_format, args.verbose)
    except Exception as e:
        print(f"Error extracting markups: {e}", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"Extracted: {len(markups)} markups")

    if not markups:
        print("No markups found in document.")
        sys.exit(0)

    # Categorize markups
    categorizer = MarkupCategorizer()
    categorized = categorizer.categorize_batch(markups)

    if not args.quiet and args.verbose:
        print("\nCategories found:")
        cat_counts = {}
        for m in categorized:
            cat = m.get("category", "Unknown")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")

    # Filter by category if specified
    if args.filter_category:
        categorized = [
            m for m in categorized
            if m.get("category") in args.filter_category
        ]
        if not args.quiet:
            print(f"After category filter: {len(categorized)} markups")

    # Generate tasks if requested
    output_data = categorized
    base_name = input_path.stem + "_markups"

    if args.tasks:
        generator = TaskGenerator(
            project_name=args.project,
            auto_assign=True,
            generate_due_dates=True
        )

        # Get filter categories as enum
        filter_cats = None
        if args.filter_category:
            filter_cats = [MarkupCategory(c) for c in args.filter_category]

        # Get min priority as enum
        min_priority = None
        if args.min_priority:
            min_priority = TaskPriority(args.min_priority)

        tasks = generator.generate_tasks(
            categorized,
            filter_categories=filter_cats,
            min_priority=min_priority
        )

        output_data = [t.to_dict() for t in tasks]
        base_name = input_path.stem + "_tasks"

        if not args.quiet:
            print(f"Generated: {len(tasks)} tasks")

    # Print summary if requested
    if args.summary and not args.quiet:
        print_summary(output_data, is_tasks=args.tasks)

    # Export
    output_formats = args.output_format
    if "all" in output_formats:
        output_formats = ["json", "csv", "markdown"]

    results = export_all(
        output_data,
        str(output_dir),
        base_name,
        formats=output_formats
    )

    if not args.quiet:
        print("\nExported:")
        for fmt, path in results.items():
            print(f"  {fmt}: {path}")

    return 0


def extract_markups(
    input_path: Path,
    input_format: str,
    verbose: bool = False
) -> List[Dict[str, Any]]:
    """Extract markups from input file."""

    if input_format == "pdf":
        if not PYMUPDF_AVAILABLE:
            raise ImportError(
                "PyMuPDF not installed. Install with: pip install PyMuPDF"
            )

        extractor = PyMuPDFExtractor()
        markups = extractor.extract(str(input_path))
        return [m.to_dict() for m in markups]

    elif input_format == "bluebeam":
        extractor = BluebeamCSVExtractor()
        markups = extractor.extract_from_csv(str(input_path))
        return [m.to_dict() for m in markups]

    else:
        raise ValueError(f"Unknown format: {input_format}")


def print_summary(data: List[Dict[str, Any]], is_tasks: bool = False):
    """Print summary to console."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"\nTotal items: {len(data)}")

    if is_tasks:
        # Task summary
        by_priority = {}
        by_type = {}
        by_status = {}

        for item in data:
            priority = item.get("priority", "Unknown")
            task_type = item.get("task_type", "Unknown")
            status = item.get("status", "Unknown")

            by_priority[priority] = by_priority.get(priority, 0) + 1
            by_type[task_type] = by_type.get(task_type, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1

        print("\nBy Priority:")
        for pri in ["Critical", "High", "Medium", "Low"]:
            if pri in by_priority:
                print(f"  {pri}: {by_priority[pri]}")

        print("\nBy Type:")
        for typ, count in sorted(by_type.items(), key=lambda x: -x[1]):
            print(f"  {typ}: {count}")

    else:
        # Markup summary
        by_category = {}
        by_page = {}

        for item in data:
            category = item.get("category", "Unknown")
            page = item.get("page", "?")

            by_category[category] = by_category.get(category, 0) + 1
            by_page[page] = by_page.get(page, 0) + 1

        print("\nBy Category:")
        for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")

        print(f"\nPages with markups: {len(by_page)}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    sys.exit(main())
