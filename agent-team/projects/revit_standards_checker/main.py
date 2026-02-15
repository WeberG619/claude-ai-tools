"""
Revit Model Standards Checker - Main entry point.

Usage:
    python main.py <model_data.json> [--html report.html] [--json report.json]

The model_data.json should contain extracted Revit model data with:
- sheets, views, levels, families, worksets, links, cad_links, elements
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

from checkers import NamingChecker, ViewChecker, WorksetChecker, LinkChecker
from reports import HTMLReportGenerator, JSONReportGenerator


def load_model_data(filepath: str) -> Dict[str, Any]:
    """Load model data from JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_all_checks(model_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run all standards checkers on model data."""
    results = {}

    # Naming checks
    naming = NamingChecker()
    naming.check_sheet_names(model_data.get("sheets", []))
    naming.check_view_names(model_data.get("views", []))
    naming.check_level_names(model_data.get("levels", []))
    naming.check_family_names(model_data.get("families", []))
    results["naming"] = naming.get_summary()

    # View checks
    views = ViewChecker()
    views.check_view_templates(model_data.get("views", []))
    views.check_view_on_sheets(
        model_data.get("views", []),
        model_data.get("placed_view_ids", [])
    )
    views.check_duplicate_views(model_data.get("views", []))
    views.check_crop_regions(model_data.get("views", []))
    views.check_detail_level(model_data.get("views", []))
    results["views"] = views.get_summary()

    # Workset checks
    worksets = WorksetChecker()
    worksets.check_workset_naming(model_data.get("worksets", []))
    worksets.check_element_placement(
        model_data.get("worksets", []),
        model_data.get("elements", [])
    )
    worksets.check_workset_visibility(model_data.get("worksets", []))
    results["worksets"] = worksets.get_summary()

    # Link checks
    links = LinkChecker()
    links.check_link_status(model_data.get("links", []))
    links.check_link_paths(
        model_data.get("links", []),
        model_data.get("project_path", "")
    )
    links.check_link_versions(
        model_data.get("links", []),
        model_data.get("revit_version", "2026")
    )
    links.check_duplicate_links(model_data.get("links", []))
    links.check_cad_links(model_data.get("cad_links", []))
    results["links"] = links.get_summary()

    return results


def generate_reports(results: Dict[str, Any], project_name: str,
                     html_path: str = None, json_path: str = None):
    """Generate output reports."""
    if html_path:
        html_gen = HTMLReportGenerator()
        html_content = html_gen.generate(results, project_name)
        html_gen.save(html_content, html_path)
        print(f"HTML report saved: {html_path}")

    if json_path:
        json_gen = JSONReportGenerator()
        json_content = json_gen.generate(results, project_name)
        json_gen.save(json_content, json_path)
        print(f"JSON report saved: {json_path}")


def print_summary(results: Dict[str, Any]):
    """Print summary to console."""
    total_errors = 0
    total_warnings = 0
    total_info = 0

    print("\n" + "=" * 60)
    print("REVIT MODEL STANDARDS CHECK SUMMARY")
    print("=" * 60)

    for checker_name, data in results.items():
        if isinstance(data, dict) and "by_severity" in data:
            errors = data["by_severity"].get("error", 0)
            warnings = data["by_severity"].get("warning", 0)
            info = data["by_severity"].get("info", 0)

            total_errors += errors
            total_warnings += warnings
            total_info += info

            total = data.get("total_issues", 0) or data.get("total_violations", 0) or 0
            print(f"\n{checker_name.upper()}: {total} issues")
            if errors: print(f"  - Errors: {errors}")
            if warnings: print(f"  - Warnings: {warnings}")
            if info: print(f"  - Info: {info}")

    print("\n" + "-" * 60)
    weighted = total_errors * 10 + total_warnings * 3 + total_info
    score = max(0, 100 - min(weighted, 100))
    status = "PASSED" if score >= 80 else "NEEDS ATTENTION" if score >= 60 else "FAILED"

    print(f"COMPLIANCE SCORE: {score}% ({status})")
    print(f"Total: {total_errors} errors, {total_warnings} warnings, {total_info} info")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Check Revit model against BIM standards")
    parser.add_argument("model_data", help="Path to model data JSON file")
    parser.add_argument("--html", help="Output HTML report path")
    parser.add_argument("--json", help="Output JSON report path")
    parser.add_argument("--name", default="Revit Project", help="Project name for reports")

    args = parser.parse_args()

    # Load model data
    if not Path(args.model_data).exists():
        print(f"Error: Model data file not found: {args.model_data}")
        sys.exit(1)

    model_data = load_model_data(args.model_data)
    project_name = args.name or model_data.get("project_name", "Revit Project")

    # Run checks
    results = run_all_checks(model_data)

    # Output
    print_summary(results)

    # Generate reports if requested
    if args.html or args.json:
        generate_reports(results, project_name, args.html, args.json)


if __name__ == "__main__":
    main()
