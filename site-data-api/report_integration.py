#!/usr/bin/env python3
"""
Report Integration - Output Generation and Revit Parameter Write-back
=====================================================================
Generates compliance reports in multiple formats and writes compliance
status back to Revit element parameters.

Author: BIM Ops Studio
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

# Import local modules
try:
    from revit_mcp_client import RevitMCPClient, MCPResponse
    from revit_schedule_integration import ScheduleValidationResult, ComplianceIssue, ComplianceStatus
except ImportError as e:
    logging.warning(f"Import error: {e}. Some features may not be available.")

# Configure logging
logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """Output report formats."""
    TEXT = "text"
    HTML = "html"
    JSON = "json"
    MARKDOWN = "markdown"


@dataclass
class ParameterWriteResult:
    """Result of a single parameter write operation."""
    element_id: int
    parameter_name: str
    value: Any
    success: bool
    error: Optional[str] = None


@dataclass
class WriteBackSummary:
    """Summary of parameter write-back operations."""
    total_elements: int = 0
    successful_writes: int = 0
    failed_writes: int = 0
    skipped: int = 0
    results: List[ParameterWriteResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ComplianceReportGenerator:
    """
    Generate compliance reports and write parameters back to Revit.

    Provides:
    - Summary reports with pass/fail counts
    - Detailed reports with all issues
    - Multiple output formats (text, HTML, JSON, Markdown)
    - Parameter write-back to Revit elements

    Example:
        generator = ComplianceReportGenerator(mcp_client)
        report = generator.generate_detailed_report(results)
        generator.export_to_pdf(report, "compliance_report.pdf")
    """

    # Compliance parameters to write back to Revit
    COMPLIANCE_PARAMETERS = [
        "Compliance_Status",     # PASS / FAIL / WARNING
        "Compliance_Date",       # Last check date
        "Compliance_Notes",      # Issue descriptions
        "NOA_Number",            # Product approval number
        "NOA_Validated",         # Yes/No
        "NOA_Expiration",        # Approval expiration date
        "HVHZ_Required",         # High Velocity Hurricane Zone flag
        "FBC_Section",           # Applicable code section
    ]

    def __init__(self, mcp_client: RevitMCPClient = None):
        """
        Initialize the report generator.

        Args:
            mcp_client: RevitMCPClient for write-back operations (optional)
        """
        self.mcp_client = mcp_client

    # =========================================================================
    # REPORT GENERATION
    # =========================================================================

    def generate_summary_report(
        self,
        results: Dict[str, ScheduleValidationResult],
        project_name: str = "",
        project_address: str = "",
        hvhz: bool = True
    ) -> str:
        """
        Generate a summary compliance report.

        Args:
            results: Dict with schedule type keys and ScheduleValidationResult values
            project_name: Project name
            project_address: Project address
            hvhz: Whether HVHZ requirements apply

        Returns:
            Formatted summary report string
        """
        lines = []

        # Header
        lines.extend([
            "=" * 70,
            "COMPLIANCE SUMMARY REPORT",
            "=" * 70,
            ""
        ])

        if project_name:
            lines.append(f"Project: {project_name}")
        if project_address:
            lines.append(f"Address: {project_address}")

        lines.extend([
            f"Report Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            f"HVHZ Zone: {'Yes' if hvhz else 'No'}",
            ""
        ])

        # Calculate totals
        total_elements = 0
        total_passed = 0
        total_failed = 0
        total_warnings = 0
        total_review = 0

        for result in results.values():
            if result:
                total_elements += result.total_elements
                total_passed += result.passed
                total_failed += result.failed
                total_warnings += result.warnings
                total_review += result.needs_review

        pass_rate = (total_passed / total_elements * 100) if total_elements > 0 else 100.0

        # Summary stats
        lines.extend([
            "-" * 50,
            "OVERALL SUMMARY",
            "-" * 50,
            f"Total Elements Checked: {total_elements}",
            f"Passed: {total_passed}",
            f"Failed: {total_failed}",
            f"Warnings: {total_warnings}",
            f"Needs Review: {total_review}",
            f"Pass Rate: {pass_rate:.1f}%",
            ""
        ])

        # Per-schedule summary
        lines.extend([
            "-" * 50,
            "BY SCHEDULE TYPE",
            "-" * 50
        ])

        for schedule_type, result in results.items():
            if result and result.total_elements > 0:
                lines.append(f"\n{schedule_type.upper()}:")
                lines.append(f"  Total: {result.total_elements}")
                lines.append(f"  Passed: {result.passed} ({result.pass_rate:.1f}%)")
                lines.append(f"  Failed: {result.failed}")
                lines.append(f"  Warnings: {result.warnings}")

        lines.extend([
            "",
            "=" * 70,
            "END OF SUMMARY",
            "=" * 70
        ])

        return "\n".join(lines)

    def generate_detailed_report(
        self,
        results: Dict[str, ScheduleValidationResult],
        project_name: str = "",
        project_address: str = "",
        hvhz: bool = True,
        include_passed: bool = False
    ) -> str:
        """
        Generate a detailed compliance report with all issues.

        Args:
            results: Dict with schedule type keys and ScheduleValidationResult values
            project_name: Project name
            project_address: Project address
            hvhz: Whether HVHZ requirements apply
            include_passed: Whether to include passed elements

        Returns:
            Formatted detailed report string
        """
        lines = []

        # Header
        lines.extend([
            "=" * 70,
            "DETAILED COMPLIANCE REPORT",
            "=" * 70,
            ""
        ])

        if project_name:
            lines.append(f"Project: {project_name}")
        if project_address:
            lines.append(f"Address: {project_address}")

        lines.extend([
            f"Report Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            f"HVHZ Zone: {'Yes' if hvhz else 'No'}",
            ""
        ])

        # Issues by schedule
        for schedule_type, result in results.items():
            if result and result.issues:
                lines.extend([
                    "-" * 50,
                    f"{schedule_type.upper()} ISSUES ({len(result.issues)} found)",
                    "-" * 50
                ])

                # Group issues by severity
                fails = [i for i in result.issues if i.severity == ComplianceStatus.FAIL]
                warnings = [i for i in result.issues if i.severity == ComplianceStatus.WARNING]
                reviews = [i for i in result.issues if i.severity == ComplianceStatus.NEEDS_REVIEW]

                if fails:
                    lines.append("\n  FAILURES:")
                    for issue in fails:
                        lines.extend(self._format_issue(issue))

                if warnings:
                    lines.append("\n  WARNINGS:")
                    for issue in warnings:
                        lines.extend(self._format_issue(issue))

                if reviews:
                    lines.append("\n  NEEDS REVIEW:")
                    for issue in reviews:
                        lines.extend(self._format_issue(issue))

        lines.extend([
            "",
            "=" * 70,
            "END OF DETAILED REPORT",
            "=" * 70
        ])

        return "\n".join(lines)

    def _format_issue(self, issue: ComplianceIssue) -> List[str]:
        """Format a single issue for the report."""
        severity_icon = {
            ComplianceStatus.FAIL: "✗",
            ComplianceStatus.WARNING: "⚠",
            ComplianceStatus.NEEDS_REVIEW: "?"
        }.get(issue.severity, " ")

        return [
            f"\n    [{severity_icon}] {issue.element_mark}: {issue.issue_type}",
            f"        Description: {issue.description}",
            f"        Code Reference: {issue.code_reference}",
            f"        Recommendation: {issue.recommendation}"
        ]

    def generate_html_report(
        self,
        results: Dict[str, ScheduleValidationResult],
        project_name: str = "",
        project_address: str = "",
        hvhz: bool = True
    ) -> str:
        """
        Generate an HTML compliance report.

        Args:
            results: Dict with schedule type keys and ScheduleValidationResult values
            project_name: Project name
            project_address: Project address
            hvhz: Whether HVHZ requirements apply

        Returns:
            HTML report string
        """
        # Calculate totals
        total_elements = sum(r.total_elements for r in results.values() if r)
        total_passed = sum(r.passed for r in results.values() if r)
        total_failed = sum(r.failed for r in results.values() if r)
        total_warnings = sum(r.warnings for r in results.values() if r)
        pass_rate = (total_passed / total_elements * 100) if total_elements > 0 else 100.0

        # Status badge color
        if total_failed > 0:
            status_class = "danger"
            status_text = "ISSUES FOUND"
        elif total_warnings > 0:
            status_class = "warning"
            status_text = "WARNINGS"
        else:
            status_class = "success"
            status_text = "COMPLIANT"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Compliance Report - {project_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: #1a1a2e;
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
        }}
        .header p {{
            margin: 5px 0;
            opacity: 0.9;
        }}
        .badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
            margin-top: 10px;
        }}
        .badge.success {{ background: #28a745; }}
        .badge.warning {{ background: #ffc107; color: #000; }}
        .badge.danger {{ background: #dc3545; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{
            margin: 0;
            font-size: 2em;
            color: #1a1a2e;
        }}
        .stat-card p {{
            margin: 5px 0 0 0;
            color: #666;
        }}
        .section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            margin-top: 0;
            color: #1a1a2e;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        .issue {{
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
            border-left: 4px solid;
        }}
        .issue.fail {{
            background: #fff5f5;
            border-color: #dc3545;
        }}
        .issue.warning {{
            background: #fffaf0;
            border-color: #ffc107;
        }}
        .issue.review {{
            background: #f0f8ff;
            border-color: #17a2b8;
        }}
        .issue-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }}
        .issue-mark {{
            font-weight: bold;
            font-size: 1.1em;
        }}
        .issue-type {{
            color: #666;
        }}
        .issue-desc {{
            margin: 10px 0;
        }}
        .issue-code {{
            font-size: 0.9em;
            color: #666;
        }}
        .issue-fix {{
            font-size: 0.9em;
            color: #28a745;
            margin-top: 10px;
        }}
        .footer {{
            text-align: center;
            color: #666;
            padding: 20px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Compliance Report</h1>
        <p><strong>Project:</strong> {project_name or 'Unknown Project'}</p>
        <p><strong>Address:</strong> {project_address or 'Not specified'}</p>
        <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        <p><strong>HVHZ:</strong> {'Yes' if hvhz else 'No'}</p>
        <span class="badge {status_class}">{status_text}</span>
    </div>

    <div class="stats">
        <div class="stat-card">
            <h3>{total_elements}</h3>
            <p>Total Elements</p>
        </div>
        <div class="stat-card">
            <h3>{total_passed}</h3>
            <p>Passed</p>
        </div>
        <div class="stat-card">
            <h3>{total_failed}</h3>
            <p>Failed</p>
        </div>
        <div class="stat-card">
            <h3>{pass_rate:.1f}%</h3>
            <p>Pass Rate</p>
        </div>
    </div>
"""

        # Issues sections
        for schedule_type, result in results.items():
            if result and result.issues:
                html += f"""
    <div class="section">
        <h2>{schedule_type.title()} Issues ({len(result.issues)})</h2>
"""
                for issue in result.issues:
                    severity_class = {
                        ComplianceStatus.FAIL: "fail",
                        ComplianceStatus.WARNING: "warning",
                        ComplianceStatus.NEEDS_REVIEW: "review"
                    }.get(issue.severity, "")

                    html += f"""
        <div class="issue {severity_class}">
            <div class="issue-header">
                <span class="issue-mark">{issue.element_mark}</span>
                <span class="issue-type">{issue.issue_type}</span>
            </div>
            <div class="issue-desc">{issue.description}</div>
            <div class="issue-code"><strong>Code:</strong> {issue.code_reference}</div>
            <div class="issue-fix"><strong>Recommendation:</strong> {issue.recommendation}</div>
        </div>
"""
                html += "    </div>\n"

        html += f"""
    <div class="footer">
        Generated by BIM Ops Studio Compliance System<br>
        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</body>
</html>
"""
        return html

    def generate_json_report(
        self,
        results: Dict[str, ScheduleValidationResult],
        project_name: str = "",
        project_address: str = "",
        hvhz: bool = True
    ) -> str:
        """
        Generate a JSON compliance report.

        Args:
            results: Dict with schedule type keys and ScheduleValidationResult values
            project_name: Project name
            project_address: Project address
            hvhz: Whether HVHZ requirements apply

        Returns:
            JSON report string
        """
        report = {
            "project": {
                "name": project_name,
                "address": project_address,
                "hvhz": hvhz
            },
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_elements": sum(r.total_elements for r in results.values() if r),
                "passed": sum(r.passed for r in results.values() if r),
                "failed": sum(r.failed for r in results.values() if r),
                "warnings": sum(r.warnings for r in results.values() if r),
                "needs_review": sum(r.needs_review for r in results.values() if r)
            },
            "schedules": {}
        }

        for schedule_type, result in results.items():
            if result:
                report["schedules"][schedule_type] = {
                    "total": result.total_elements,
                    "passed": result.passed,
                    "failed": result.failed,
                    "warnings": result.warnings,
                    "needs_review": result.needs_review,
                    "pass_rate": result.pass_rate,
                    "issues": [
                        {
                            "element_id": issue.element_id,
                            "element_mark": issue.element_mark,
                            "issue_type": issue.issue_type,
                            "severity": issue.severity.value,
                            "description": issue.description,
                            "code_reference": issue.code_reference,
                            "recommendation": issue.recommendation
                        }
                        for issue in result.issues
                    ]
                }

        return json.dumps(report, indent=2)

    def export_to_file(
        self,
        report: str,
        output_path: str,
        format: ReportFormat = ReportFormat.TEXT
    ) -> bool:
        """
        Export report to file.

        Args:
            report: Report content
            output_path: Output file path
            format: Report format

        Returns:
            True if successful
        """
        try:
            # Add appropriate extension if not present
            if format == ReportFormat.HTML and not output_path.endswith('.html'):
                output_path += '.html'
            elif format == ReportFormat.JSON and not output_path.endswith('.json'):
                output_path += '.json'
            elif format == ReportFormat.MARKDOWN and not output_path.endswith('.md'):
                output_path += '.md'
            elif format == ReportFormat.TEXT and not output_path.endswith('.txt'):
                output_path += '.txt'

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)

            logger.info(f"Report exported to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export report: {e}")
            return False

    # =========================================================================
    # PARAMETER WRITE-BACK
    # =========================================================================

    def write_compliance_parameters(
        self,
        element_id: int,
        status: str,
        notes: str = "",
        noa_number: str = "",
        noa_validated: bool = False,
        code_section: str = ""
    ) -> ParameterWriteResult:
        """
        Write compliance parameters to a Revit element.

        Args:
            element_id: Revit element ID
            status: Compliance status (PASS/FAIL/WARNING)
            notes: Issue descriptions
            noa_number: NOA number if applicable
            noa_validated: Whether NOA was validated
            code_section: Applicable code section

        Returns:
            ParameterWriteResult
        """
        if not self.mcp_client:
            return ParameterWriteResult(
                element_id=element_id,
                parameter_name="",
                value="",
                success=False,
                error="MCP client not available"
            )

        updates = []

        if status:
            updates.append({
                "elementId": element_id,
                "parameterName": "Compliance_Status",
                "value": status
            })

        updates.append({
            "elementId": element_id,
            "parameterName": "Compliance_Date",
            "value": datetime.now().strftime("%Y-%m-%d")
        })

        if notes:
            updates.append({
                "elementId": element_id,
                "parameterName": "Compliance_Notes",
                "value": notes[:500]  # Truncate
            })

        if noa_number:
            updates.append({
                "elementId": element_id,
                "parameterName": "NOA_Number",
                "value": noa_number
            })
            updates.append({
                "elementId": element_id,
                "parameterName": "NOA_Validated",
                "value": "Yes" if noa_validated else "No"
            })

        if code_section:
            updates.append({
                "elementId": element_id,
                "parameterName": "FBC_Section",
                "value": code_section
            })

        # Send to Revit
        response = self.mcp_client.set_multiple_parameters(updates)

        return ParameterWriteResult(
            element_id=element_id,
            parameter_name="Multiple",
            value=f"{len(updates)} parameters",
            success=response.success,
            error=response.error
        )

    def batch_write_results(
        self,
        results: Dict[int, Tuple[str, str, str]],
        schedule_type: str = ""
    ) -> WriteBackSummary:
        """
        Batch write compliance results to multiple elements.

        Args:
            results: Dict of element_id -> (status, notes, code_section)
            schedule_type: Schedule type for logging

        Returns:
            WriteBackSummary
        """
        summary = WriteBackSummary(total_elements=len(results))

        if not self.mcp_client:
            summary.errors.append("MCP client not available")
            summary.skipped = len(results)
            return summary

        for element_id, (status, notes, code_section) in results.items():
            result = self.write_compliance_parameters(
                element_id=element_id,
                status=status,
                notes=notes,
                code_section=code_section
            )

            summary.results.append(result)

            if result.success:
                summary.successful_writes += 1
            else:
                summary.failed_writes += 1
                if result.error:
                    summary.errors.append(f"Element {element_id}: {result.error}")

        logger.info(f"Write-back complete for {schedule_type}: "
                   f"{summary.successful_writes} succeeded, "
                   f"{summary.failed_writes} failed")

        return summary


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("REPORT INTEGRATION TEST")
    print("=" * 70)

    # Create mock validation results
    from revit_schedule_integration import ScheduleValidationResult, ComplianceIssue, ComplianceStatus, ScheduleType

    door_result = ScheduleValidationResult(
        schedule_type=ScheduleType.DOOR,
        total_elements=5,
        passed=2,
        failed=2,
        warnings=1,
        needs_review=0,
        issues=[
            ComplianceIssue(
                element_id="12345",
                element_mark="D-102",
                issue_type="ADA Clear Width",
                severity=ComplianceStatus.FAIL,
                description="Door clear width 30\" is less than required 32\"",
                code_reference="ADA 404.2.3 / FBC 1010.1.1",
                recommendation="Increase door width to minimum 36\" nominal"
            ),
            ComplianceIssue(
                element_id="12346",
                element_mark="D-103",
                issue_type="Fire Door Closer",
                severity=ComplianceStatus.FAIL,
                description="Fire-rated door (90 min) requires self-closing device",
                code_reference="FBC 716.2.6.3",
                recommendation="Add listed door closer"
            ),
            ComplianceIssue(
                element_id="12347",
                element_mark="D-104",
                issue_type="HVHZ Product Approval",
                severity=ComplianceStatus.WARNING,
                description="Exterior door requires Miami-Dade NOA for HVHZ",
                code_reference="FBC 1609.1.2",
                recommendation="Provide NOA number or specify impact-rated assembly"
            )
        ]
    )

    window_result = ScheduleValidationResult(
        schedule_type=ScheduleType.WINDOW,
        total_elements=3,
        passed=1,
        failed=2,
        warnings=0,
        needs_review=0,
        issues=[
            ComplianceIssue(
                element_id="22345",
                element_mark="W-102",
                issue_type="HVHZ Product Approval",
                severity=ComplianceStatus.FAIL,
                description="Window requires Miami-Dade NOA for HVHZ",
                code_reference="FBC 1609.1.2",
                recommendation="Specify impact-rated window with valid NOA"
            )
        ]
    )

    results = {
        "door": door_result,
        "window": window_result
    }

    # Generate reports
    generator = ComplianceReportGenerator()

    print("\n" + "-" * 50)
    print("Summary Report:")
    print("-" * 50)
    summary = generator.generate_summary_report(
        results,
        project_name="Goulds Tower",
        project_address="11900 SW 216th St, Goulds, FL"
    )
    print(summary)

    print("\n" + "-" * 50)
    print("JSON Report (excerpt):")
    print("-" * 50)
    json_report = generator.generate_json_report(
        results,
        project_name="Goulds Tower",
        project_address="11900 SW 216th St, Goulds, FL"
    )
    parsed = json.loads(json_report)
    print(f"  Total elements: {parsed['summary']['total_elements']}")
    print(f"  Failed: {parsed['summary']['failed']}")
    print(f"  Schedules: {list(parsed['schedules'].keys())}")

    print("\n" + "-" * 50)
    print("HTML Report (saved to file):")
    print("-" * 50)
    html_report = generator.generate_html_report(
        results,
        project_name="Goulds Tower",
        project_address="11900 SW 216th St, Goulds, FL"
    )
    output_path = "/mnt/d/_CLAUDE-TOOLS/site-data-api/reports/test_compliance_report.html"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if generator.export_to_file(html_report, output_path, ReportFormat.HTML):
        print(f"  Saved to: {output_path}")
    else:
        print("  Failed to save")

    print("\n" + "=" * 70)
    print("Test complete")
    print("=" * 70)
