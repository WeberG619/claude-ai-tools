"""
HTML Dashboard - Web-based project status visualization.
"""
from typing import Dict, List
from datetime import datetime


class HTMLDashboard:
    """Generate HTML dashboard for project status."""

    def __init__(self):
        self.template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Status Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e6edf3;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header .updated {{ color: #8b949e; font-size: 14px; }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .summary-card .value {{
            font-size: 36px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .summary-card .label {{ color: #8b949e; font-size: 12px; text-transform: uppercase; }}
        .summary-card.green .value {{ color: #3fb950; }}
        .summary-card.yellow .value {{ color: #d29922; }}
        .summary-card.red .value {{ color: #f85149; }}
        .summary-card.blue .value {{ color: #58a6ff; }}

        .section {{ margin-bottom: 30px; }}
        .section-title {{
            font-size: 18px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}

        .project-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }}
        .project-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #58a6ff;
            transition: transform 0.2s;
        }}
        .project-card:hover {{ transform: translateY(-2px); }}
        .project-card.on_track {{ border-color: #3fb950; }}
        .project-card.at_risk {{ border-color: #d29922; }}
        .project-card.behind {{ border-color: #f85149; }}
        .project-card.on_hold {{ border-color: #8b949e; }}

        .project-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }}
        .project-number {{ color: #8b949e; font-size: 12px; }}
        .project-name {{ font-size: 16px; font-weight: 600; margin-top: 4px; }}
        .project-client {{ color: #8b949e; font-size: 13px; }}

        .status-badge {{
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .status-badge.on_track {{ background: rgba(63,185,80,0.2); color: #3fb950; }}
        .status-badge.at_risk {{ background: rgba(210,153,34,0.2); color: #d29922; }}
        .status-badge.behind {{ background: rgba(248,81,73,0.2); color: #f85149; }}
        .status-badge.on_hold {{ background: rgba(139,148,158,0.2); color: #8b949e; }}

        .health-bar {{
            height: 6px;
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
            margin: 15px 0;
            overflow: hidden;
        }}
        .health-bar .fill {{
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s;
        }}
        .health-bar .fill.good {{ background: #3fb950; }}
        .health-bar .fill.warning {{ background: #d29922; }}
        .health-bar .fill.danger {{ background: #f85149; }}

        .project-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 15px;
        }}
        .stat {{ text-align: center; }}
        .stat .value {{ font-size: 18px; font-weight: 600; }}
        .stat .label {{ font-size: 10px; color: #8b949e; text-transform: uppercase; }}

        .milestone-list {{ margin-top: 15px; }}
        .milestone {{
            display: flex;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            font-size: 13px;
        }}
        .milestone:last-child {{ border-bottom: none; }}
        .milestone .icon {{ margin-right: 10px; }}
        .milestone.overdue {{ color: #f85149; }}
        .milestone.upcoming {{ color: #d29922; }}
        .milestone .date {{ margin-left: auto; color: #8b949e; }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>Project Status Dashboard</h1>
            <div class="updated">Last updated: {timestamp}</div>
        </header>

        <div class="summary-grid">
            <div class="summary-card blue">
                <div class="label">Active Projects</div>
                <div class="value">{active_projects}</div>
            </div>
            <div class="summary-card green">
                <div class="label">On Track</div>
                <div class="value">{on_track}</div>
            </div>
            <div class="summary-card yellow">
                <div class="label">At Risk</div>
                <div class="value">{at_risk}</div>
            </div>
            <div class="summary-card {health_class}">
                <div class="label">Avg Health</div>
                <div class="value">{avg_health}%</div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">Upcoming Milestones</h2>
            <div class="milestone-list">
                {milestones_html}
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">All Projects</h2>
            <div class="project-grid">
                {projects_html}
            </div>
        </div>
    </div>
</body>
</html>
'''

    def render(self, metrics: Dict) -> str:
        """Render the dashboard HTML."""
        summary = metrics.get("summary", {})

        # Calculate status counts
        by_status = metrics.get("by_status", {})
        on_track = by_status.get("on_track", 0) + by_status.get("ahead", 0)
        at_risk = by_status.get("at_risk", 0) + by_status.get("behind", 0)

        # Health class
        avg_health = summary.get("average_health", 0)
        if avg_health >= 80:
            health_class = "green"
        elif avg_health >= 60:
            health_class = "yellow"
        else:
            health_class = "red"

        # Render milestones
        milestones_html = ""
        for m in metrics.get("upcoming_milestones", [])[:10]:
            icon = "⚠️" if m.get("is_overdue") else "📅"
            css_class = "overdue" if m.get("is_overdue") else "upcoming" if m.get("days_until_due", 99) <= 7 else ""
            milestones_html += f'''
            <div class="milestone {css_class}">
                <span class="icon">{icon}</span>
                <span>{m.get("project_name", "")} - {m.get("milestone", "")}</span>
                <span class="date">{m.get("due_date", "")}</span>
            </div>
            '''

        # Render project cards
        projects_html = ""
        for p in metrics.get("projects", []):
            status = p.get("status", "on_track")
            health = p.get("health_score", 0)

            if health >= 80:
                fill_class = "good"
            elif health >= 60:
                fill_class = "warning"
            else:
                fill_class = "danger"

            projects_html += f'''
            <div class="project-card {status}">
                <div class="project-header">
                    <div>
                        <div class="project-number">{p.get("project_id", "")}</div>
                        <div class="project-name">{p.get("project_id", "Project")}</div>
                    </div>
                    <span class="status-badge {status}">{status.replace("_", " ")}</span>
                </div>
                <div class="health-bar">
                    <div class="fill {fill_class}" style="width: {health}%"></div>
                </div>
                <div class="project-stats">
                    <div class="stat">
                        <div class="value">{health}</div>
                        <div class="label">Health</div>
                    </div>
                    <div class="stat">
                        <div class="value">{p.get("budget_percent_used", 0):.0f}%</div>
                        <div class="label">Budget</div>
                    </div>
                    <div class="stat">
                        <div class="value">{p.get("burn_rate_weekly", 0):.0f}h</div>
                        <div class="label">Weekly</div>
                    </div>
                </div>
            </div>
            '''

        return self.template.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            active_projects=summary.get("active_projects", 0),
            on_track=on_track,
            at_risk=at_risk,
            avg_health=int(avg_health),
            health_class=health_class,
            milestones_html=milestones_html or "<div>No upcoming milestones</div>",
            projects_html=projects_html or "<div>No projects</div>"
        )

    def save(self, metrics: Dict, filepath: str):
        """Save dashboard to HTML file."""
        html = self.render(metrics)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
