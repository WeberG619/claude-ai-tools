"""
JSON Report Generator - Machine-readable standards report.
"""
import json
from typing import Dict, Any
from datetime import datetime


class JSONReportGenerator:
    """Generates JSON reports for programmatic processing."""

    def generate(self, results: Dict[str, Any], project_name: str) -> Dict[str, Any]:
        """Generate structured JSON report."""
        # Count totals
        total_errors = 0
        total_warnings = 0
        total_info = 0
        all_issues = []

        for checker_name, data in results.items():
            if isinstance(data, dict):
                severities = data.get("by_severity", {})
                total_errors += severities.get("error", 0)
                total_warnings += severities.get("warning", 0)
                total_info += severities.get("info", 0)

                for issue in data.get("issues", []):
                    issue["checker"] = checker_name
                    all_issues.append(issue)

        # Calculate compliance score
        total_issues = total_errors + total_warnings + total_info
        weighted_score = total_errors * 10 + total_warnings * 3 + total_info
        compliance_score = max(0, 100 - min(weighted_score, 100))

        return {
            "report": {
                "project_name": project_name,
                "generated_at": datetime.now().isoformat(),
                "version": "1.0"
            },
            "summary": {
                "compliance_score": compliance_score,
                "total_issues": total_issues,
                "by_severity": {
                    "errors": total_errors,
                    "warnings": total_warnings,
                    "info": total_info
                },
                "passed": compliance_score >= 80
            },
            "details": results,
            "all_issues": sorted(all_issues,
                                 key=lambda x: {"error": 0, "warning": 1, "info": 2}.get(x.get("severity", "info"), 2))
        }

    def save(self, data: Dict[str, Any], filepath: str):
        """Save JSON to file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
