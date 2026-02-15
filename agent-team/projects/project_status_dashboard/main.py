"""
Project Status Dashboard - Main entry point.

Track and visualize project status across your portfolio.

Usage:
    # Console dashboard
    python main.py show --data projects.json

    # HTML dashboard
    python main.py html --data projects.json --output dashboard.html

    # Demo with sample data
    python main.py demo
"""

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from models import Project, ProjectPhase, Milestone, TeamMember, Role
from models.metrics import ProjectMetrics, DashboardMetrics
from views import HTMLDashboard, ConsoleView


def load_projects(filepath: str) -> list:
    """Load projects from JSON file."""
    with open(filepath) as f:
        data = json.load(f)

    projects = []
    for p in data.get("projects", []):
        project = Project(
            id=p.get("id", ""),
            number=p.get("number", ""),
            name=p.get("name", ""),
            client=p.get("client", ""),
            phase=ProjectPhase(p.get("phase", "Programming")),
            start_date=date.fromisoformat(p.get("start_date", str(date.today()))),
            target_completion=date.fromisoformat(p["target_completion"]) if p.get("target_completion") else None,
            budget_hours=p.get("budget_hours", 0),
            spent_hours=p.get("spent_hours", 0),
            fee=p.get("fee", 0),
            billed=p.get("billed", 0),
            team_members=p.get("team_members", [])
        )

        # Add milestones
        for m in p.get("milestones", []):
            project.add_milestone(
                name=m.get("name", ""),
                due_date=date.fromisoformat(m.get("due_date", str(date.today()))),
                description=m.get("description", "")
            )
            if m.get("completed"):
                project.complete_milestone(m["name"])

        projects.append(project)

    return projects


def create_demo_data() -> list:
    """Create sample project data for demonstration."""
    projects = []

    # Project 1: On track
    p1 = Project(
        id="2024-001",
        number="2024-001",
        name="Downtown Office Tower",
        client="Metro Development",
        phase=ProjectPhase.CONSTRUCTION_DOCUMENTS,
        start_date=date.today() - timedelta(days=120),
        target_completion=date.today() + timedelta(days=60),
        budget_hours=2000,
        spent_hours=1400,
        fee=250000,
        billed=175000
    )
    p1.add_milestone("CD 50%", date.today() - timedelta(days=10))
    p1.complete_milestone("CD 50%")
    p1.add_milestone("CD 100%", date.today() + timedelta(days=20))
    p1.add_milestone("Permit Submission", date.today() + timedelta(days=45))
    projects.append(p1)

    # Project 2: At risk
    p2 = Project(
        id="2024-005",
        number="2024-005",
        name="Riverside Apartments",
        client="Waterfront LLC",
        phase=ProjectPhase.DESIGN_DEVELOPMENT,
        start_date=date.today() - timedelta(days=90),
        target_completion=date.today() + timedelta(days=90),
        budget_hours=1500,
        spent_hours=1350,  # Over budget
        fee=180000,
        billed=140000
    )
    p2.add_milestone("DD Review", date.today() - timedelta(days=5))  # Overdue
    p2.add_milestone("DD Completion", date.today() + timedelta(days=14))
    projects.append(p2)

    # Project 3: Behind
    p3 = Project(
        id="2024-008",
        number="2024-008",
        name="City Library Renovation",
        client="City of Springfield",
        phase=ProjectPhase.SCHEMATIC_DESIGN,
        start_date=date.today() - timedelta(days=60),
        target_completion=date.today() + timedelta(days=30),
        budget_hours=800,
        spent_hours=700,
        fee=95000,
        billed=70000
    )
    p3.add_milestone("SD Presentation", date.today() - timedelta(days=14))  # Overdue
    p3.add_milestone("SD Approval", date.today() - timedelta(days=7))  # Overdue
    projects.append(p3)

    # Project 4: Ahead
    p4 = Project(
        id="2024-012",
        number="2024-012",
        name="Tech Campus Phase 2",
        client="Innovation Corp",
        phase=ProjectPhase.DESIGN_DEVELOPMENT,
        start_date=date.today() - timedelta(days=45),
        target_completion=date.today() + timedelta(days=120),
        budget_hours=3000,
        spent_hours=900,
        fee=400000,
        billed=120000
    )
    p4.add_milestone("DD Kickoff", date.today() - timedelta(days=30))
    p4.complete_milestone("DD Kickoff")
    p4.add_milestone("DD 50%", date.today() + timedelta(days=30))
    projects.append(p4)

    # Project 5: On hold
    p5 = Project(
        id="2023-042",
        number="2023-042",
        name="Historic Theater Restoration",
        client="Heritage Foundation",
        phase=ProjectPhase.ON_HOLD,
        start_date=date.today() - timedelta(days=180),
        budget_hours=1200,
        spent_hours=600,
        fee=150000,
        billed=75000
    )
    projects.append(p5)

    return projects


def main():
    parser = argparse.ArgumentParser(description="Project Status Dashboard")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Show command
    show_parser = subparsers.add_parser("show", help="Show dashboard in console")
    show_parser.add_argument("--data", help="Project data JSON file")

    # HTML command
    html_parser = subparsers.add_parser("html", help="Generate HTML dashboard")
    html_parser.add_argument("--data", help="Project data JSON file")
    html_parser.add_argument("--output", default="dashboard.html", help="Output HTML file")

    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run demo with sample data")
    demo_parser.add_argument("--html", help="Also generate HTML to file")

    args = parser.parse_args()

    # Load or create projects
    if args.command == "demo":
        projects = create_demo_data()
    else:
        if not args.data:
            print("Error: --data required for non-demo mode")
            return
        projects = load_projects(args.data)

    # Calculate metrics
    dashboard = DashboardMetrics(projects)
    metrics = dashboard.to_dict()

    # Render output
    if args.command == "show":
        view = ConsoleView()
        view.render_full(metrics)

    elif args.command == "html":
        html = HTMLDashboard()
        html.save(metrics, args.output)
        print(f"Dashboard saved to: {args.output}")

    elif args.command == "demo":
        view = ConsoleView()
        view.render_full(metrics)

        if args.html:
            html = HTMLDashboard()
            html.save(metrics, args.html)
            print(f"\nHTML dashboard saved to: {args.html}")


if __name__ == "__main__":
    main()
