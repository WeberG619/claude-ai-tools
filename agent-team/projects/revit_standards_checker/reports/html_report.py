"""
HTML Report Generator - Creates visual standards compliance reports.
"""
from typing import Dict, Any
from datetime import datetime


class HTMLReportGenerator:
    """Generates HTML reports for standards compliance."""

    def __init__(self):
        self.template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Revit Standards Report - {project_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ font-size: 24px; margin-bottom: 10px; }}
        .header .meta {{ color: #8b9dc3; font-size: 14px; }}
        .summary-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .card h3 {{ color: #666; font-size: 12px; text-transform: uppercase; margin-bottom: 10px; }}
        .card .value {{ font-size: 32px; font-weight: bold; }}
        .card.errors .value {{ color: #dc3545; }}
        .card.warnings .value {{ color: #ffc107; }}
        .card.info .value {{ color: #17a2b8; }}
        .card.passed .value {{ color: #28a745; }}
        .section {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .section h2 {{ font-size: 18px; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #eee; }}
        .issue-list {{ list-style: none; }}
        .issue {{ padding: 12px; border-left: 4px solid #ddd; margin-bottom: 10px; background: #fafafa; }}
        .issue.error {{ border-color: #dc3545; background: #fff5f5; }}
        .issue.warning {{ border-color: #ffc107; background: #fffbf0; }}
        .issue.info {{ border-color: #17a2b8; background: #f0fbff; }}
        .issue .type {{ font-weight: 600; margin-bottom: 5px; }}
        .issue .detail {{ color: #666; font-size: 14px; }}
        .issue .element {{ font-family: monospace; color: #333; margin-top: 5px; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
        .badge.error {{ background: #dc3545; color: white; }}
        .badge.warning {{ background: #ffc107; color: #333; }}
        .badge.info {{ background: #17a2b8; color: white; }}
        .chart {{ height: 200px; display: flex; align-items: flex-end; gap: 10px; padding: 20px 0; }}
        .bar {{ flex: 1; background: #4a90d9; border-radius: 4px 4px 0 0; min-height: 10px; transition: height 0.3s; }}
        .bar-label {{ text-align: center; font-size: 11px; color: #666; margin-top: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>BIM Standards Compliance Report</h1>
            <div class="meta">
                <strong>{project_name}</strong> | Generated: {timestamp}
            </div>
        </div>

        <div class="summary-cards">
            <div class="card errors">
                <h3>Errors</h3>
                <div class="value">{error_count}</div>
            </div>
            <div class="card warnings">
                <h3>Warnings</h3>
                <div class="value">{warning_count}</div>
            </div>
            <div class="card info">
                <h3>Info</h3>
                <div class="value">{info_count}</div>
            </div>
            <div class="card passed">
                <h3>Score</h3>
                <div class="value">{score}%</div>
            </div>
        </div>

        {sections}
    </div>
</body>
</html>
"""

    def generate(self, results: Dict[str, Any], project_name: str) -> str:
        """Generate HTML report from checker results."""
        # Count totals
        error_count = 0
        warning_count = 0
        info_count = 0

        for checker_name, data in results.items():
            if isinstance(data, dict) and "by_severity" in data:
                error_count += data["by_severity"].get("error", 0)
                warning_count += data["by_severity"].get("warning", 0)
                info_count += data["by_severity"].get("info", 0)

        total_issues = error_count + warning_count + info_count
        max_issues = 100  # Baseline
        score = max(0, 100 - int((error_count * 5 + warning_count * 2 + info_count) / max_issues * 100))

        # Generate sections
        sections_html = ""
        for checker_name, data in results.items():
            if isinstance(data, dict) and "issues" in data:
                sections_html += self._generate_section(checker_name, data)

        return self.template.format(
            project_name=project_name,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            score=score,
            sections=sections_html
        )

    def _generate_section(self, name: str, data: Dict[str, Any]) -> str:
        """Generate a section for one checker."""
        issues = data.get("issues", [])
        if not issues:
            return ""

        # Friendly names
        name_map = {
            "naming": "Naming Conventions",
            "views": "View Organization",
            "worksets": "Workset Management",
            "links": "Linked Files"
        }
        display_name = name_map.get(name.lower(), name.title())

        issues_html = ""
        for issue in issues[:50]:  # Limit display
            severity = issue.get("severity", "info")
            issue_type = issue.get("type", "Issue")
            detail = issue.get("detail", "")
            element = issue.get("name", issue.get("view", issue.get("link", "")))

            issues_html += f"""
            <li class="issue {severity}">
                <div class="type">
                    <span class="badge {severity}">{severity.upper()}</span>
                    {issue_type}
                </div>
                <div class="detail">{detail}</div>
                <div class="element">{element}</div>
            </li>
            """

        return f"""
        <div class="section">
            <h2>{display_name} ({len(issues)} issues)</h2>
            <ul class="issue-list">
                {issues_html}
            </ul>
        </div>
        """

    def save(self, html: str, filepath: str):
        """Save HTML to file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
