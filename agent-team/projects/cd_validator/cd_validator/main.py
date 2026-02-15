#!/usr/bin/env python3
"""
CD Validator - Construction Document Validation CLI

Validates Revit construction documents against AIA standards,
checks for broken references, and ensures BIM naming conventions.

Requires:
- Revit 2026 running with MCP Bridge server started
- pywin32 package (pip install pywin32)

Usage:
    python -m cd_validator                    # Run all validators
    python -m cd_validator --sheets           # Sheet validation only
    python -m cd_validator --references       # Reference validation only
    python -m cd_validator --standards        # BIM standards only
    python -m cd_validator --json             # Output as JSON
    python -m cd_validator --output report.json  # Save to file
"""

import argparse
import json
import sys
from datetime import datetime
from typing import List, Dict, Any

from cd_validator.core.base_validator import (
    BaseValidator,
    ValidationResult,
    ValidationSeverity,
    RevitMCPConnection,
)
from cd_validator.validators.sheet_validator import SheetValidator
from cd_validator.validators.reference_validator import ReferenceValidator
from cd_validator.validators.bim_standards_validator import BIMStandardsValidator


# Exit codes
EXIT_SUCCESS = 0          # All validations passed
EXIT_VALIDATION_FAILED = 1  # Validation completed but found errors/critical issues
EXIT_CONNECTION_FAILED = 2  # Could not connect to RevitMCPBridge
EXIT_PARTIAL_VALIDATION = 3 # Some validators failed to complete
EXIT_INVALID_ARGUMENTS = 4  # Invalid command line arguments


# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def severity_color(severity: ValidationSeverity) -> str:
    """Get color code for severity level."""
    return {
        ValidationSeverity.INFO: Colors.BLUE,
        ValidationSeverity.WARNING: Colors.YELLOW,
        ValidationSeverity.ERROR: Colors.RED,
        ValidationSeverity.CRITICAL: Colors.RED + Colors.BOLD,
    }.get(severity, Colors.ENDC)


def print_header(text: str) -> None:
    """Print formatted header."""
    print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  {text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}")


def print_result(result: ValidationResult, show_details: bool = True) -> None:
    """Print a single validation result."""
    color = severity_color(result.severity)
    icon = {
        ValidationSeverity.INFO: "i",
        ValidationSeverity.WARNING: "!",
        ValidationSeverity.ERROR: "X",
        ValidationSeverity.CRITICAL: "!!",
    }.get(result.severity, "?")

    print(f"  {color}[{icon}]{Colors.ENDC} [{result.rule_id}] {result.message}")

    if show_details:
        if result.location:
            print(f"      Location: {result.location}")
        if result.suggestion:
            print(f"      {Colors.GREEN}Suggestion: {result.suggestion}{Colors.ENDC}")


def print_summary(validators: List[BaseValidator]) -> Dict[str, Any]:
    """Print overall validation summary."""
    total_issues = 0
    total_by_severity = {s.value: 0 for s in ValidationSeverity}
    validator_summaries = []

    for validator in validators:
        summary = validator.get_summary()
        validator_summaries.append(summary)
        total_issues += summary["total_issues"]
        for sev, count in summary["by_severity"].items():
            total_by_severity[sev] += count

    print_header("VALIDATION SUMMARY")

    print(f"\n  Total Issues: {total_issues}")
    print(f"    {Colors.RED}Critical: {total_by_severity['critical']}{Colors.ENDC}")
    print(f"    {Colors.RED}Errors:   {total_by_severity['error']}{Colors.ENDC}")
    print(f"    {Colors.YELLOW}Warnings: {total_by_severity['warning']}{Colors.ENDC}")
    print(f"    {Colors.BLUE}Info:     {total_by_severity['info']}{Colors.ENDC}")

    print("\n  By Validator:")
    for summary in validator_summaries:
        status = f"{Colors.GREEN}PASS{Colors.ENDC}" if summary["passed"] else f"{Colors.RED}FAIL{Colors.ENDC}"
        print(f"    {summary['validator']}: {summary['total_issues']} issues [{status}]")

    passed = total_by_severity["critical"] == 0 and total_by_severity["error"] == 0
    print(f"\n  {Colors.BOLD}Overall: {'PASSED' if passed else 'FAILED'}{Colors.ENDC}")

    return {
        "total_issues": total_issues,
        "by_severity": total_by_severity,
        "passed": passed,
        "validators": validator_summaries,
    }


def run_validators(
    validators: List[BaseValidator],
    json_output: bool = False,
    output_file: str = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Run all validators and return combined results."""
    all_results = []

    for validator in validators:
        if verbose and not json_output:
            print_header(f"{validator.name}")
            print(f"  {validator.description}\n")

        results = validator.validate()
        all_results.extend(results)

        if verbose and not json_output:
            if not results:
                print(f"  {Colors.GREEN}No issues found{Colors.ENDC}")
            else:
                # Group by severity
                by_severity = {}
                for result in results:
                    sev = result.severity.value
                    if sev not in by_severity:
                        by_severity[sev] = []
                    by_severity[sev].append(result)

                # Print in severity order
                for sev in ["critical", "error", "warning", "info"]:
                    if sev in by_severity:
                        for result in by_severity[sev]:
                            print_result(result)

    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": print_summary(validators) if not json_output else None,
        "validators": [],
    }

    for validator in validators:
        report["validators"].append({
            "name": validator.name,
            "description": validator.description,
            "summary": validator.get_summary(),
            "results": [r.to_dict() for r in validator.results],
        })

    if json_output:
        # Calculate summary without printing
        total_issues = sum(v.get_summary()["total_issues"] for v in validators)
        total_by_severity = {s.value: 0 for s in ValidationSeverity}
        for v in validators:
            for sev, count in v.get_summary()["by_severity"].items():
                total_by_severity[sev] += count

        report["summary"] = {
            "total_issues": total_issues,
            "by_severity": total_by_severity,
            "passed": total_by_severity["critical"] == 0 and total_by_severity["error"] == 0,
        }

    # Output
    if json_output:
        json_str = json.dumps(report, indent=2)
        if output_file:
            with open(output_file, "w") as f:
                f.write(json_str)
            print(f"Report saved to: {output_file}", file=sys.stderr)
        else:
            print(json_str)
    elif output_file:
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n  Report saved to: {output_file}")

    return report


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Revit Construction Documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m cd_validator                    Run all validators
  python -m cd_validator --sheets           Sheet validation only
  python -m cd_validator --json             JSON output for automation
  python -m cd_validator -o report.json     Save detailed report

Requires Revit 2026 with MCP Bridge server running.
        """
    )

    parser.add_argument(
        "--sheets", "-s",
        action="store_true",
        help="Run sheet validation only"
    )
    parser.add_argument(
        "--references", "-r",
        action="store_true",
        help="Run reference validation only"
    )
    parser.add_argument(
        "--standards", "-b",
        action="store_true",
        help="Run BIM standards validation only"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Save report to file"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress detailed output"
    )

    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse exits with code 2 for errors, we use 4 for invalid arguments
        if e.code == 2:
            sys.exit(EXIT_INVALID_ARGUMENTS)
        raise

    # Check connection first
    try:
        connection = RevitMCPConnection()
        if not connection.is_connected():
            print(f"{Colors.RED}Error: Cannot connect to RevitMCPBridge{Colors.ENDC}")
            print("Make sure:")
            print("  1. Revit 2026 is running")
            print("  2. A project is open")
            print("  3. MCP Bridge server is started (click 'Start Server' in Revit)")
            sys.exit(EXIT_CONNECTION_FAILED)
    except RuntimeError as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
        sys.exit(EXIT_CONNECTION_FAILED)

    # Determine which validators to run
    if args.sheets or args.references or args.standards:
        validators = []
        if args.sheets:
            validators.append(SheetValidator(connection))
        if args.references:
            validators.append(ReferenceValidator(connection))
        if args.standards:
            validators.append(BIMStandardsValidator(connection))
    else:
        # Run all validators
        validators = [
            SheetValidator(connection),
            ReferenceValidator(connection),
            BIMStandardsValidator(connection),
        ]

    # Print banner
    if not args.json:
        print(f"\n{Colors.BOLD}CD VALIDATOR{Colors.ENDC} - Construction Document Validation")
        print(f"Connecting to RevitMCPBridge...")

    # Run validation
    report = run_validators(
        validators,
        json_output=args.json,
        output_file=args.output,
        verbose=not args.quiet,
    )

    # Check for partial validation (any validator had critical fetch failures)
    partial_failure = False
    for validator_report in report["validators"]:
        for result in validator_report.get("results", []):
            if result.get("severity") == "critical" and "Failed to fetch" in result.get("message", ""):
                partial_failure = True
                break
        if partial_failure:
            break

    # Exit code based on results
    if partial_failure:
        sys.exit(EXIT_PARTIAL_VALIDATION)
    elif report["summary"]["passed"]:
        sys.exit(EXIT_SUCCESS)
    else:
        sys.exit(EXIT_VALIDATION_FAILED)


if __name__ == "__main__":
    main()
