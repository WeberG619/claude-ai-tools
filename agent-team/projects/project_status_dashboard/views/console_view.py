"""
Console View - Terminal-based project status display.
"""
from typing import Dict, List


class ConsoleView:
    """Display project status in terminal."""

    STATUS_COLORS = {
        "on_track": "\033[92m",  # Green
        "at_risk": "\033[93m",   # Yellow
        "behind": "\033[91m",    # Red
        "on_hold": "\033[90m",   # Gray
        "ahead": "\033[96m",     # Cyan
    }
    RESET = "\033[0m"

    def render_summary(self, metrics: Dict):
        """Print summary to console."""
        summary = metrics.get("summary", {})

        print("\n" + "=" * 60)
        print("PROJECT STATUS DASHBOARD")
        print("=" * 60)

        print(f"\n📊 SUMMARY")
        print(f"   Active Projects: {summary.get('active_projects', 0)}")
        print(f"   At Risk: {summary.get('at_risk', 0)}")
        print(f"   Average Health: {summary.get('average_health', 0):.0f}%")
        print(f"   Total Hours Budget: {summary.get('total_budget_hours', 0):,.0f}")
        print(f"   Total Hours Spent: {summary.get('total_spent_hours', 0):,.0f}")
        print(f"   Overall Utilization: {summary.get('overall_utilization', 0):.1f}%")

    def render_by_phase(self, metrics: Dict):
        """Print projects by phase."""
        by_phase = metrics.get("by_phase", {})

        print(f"\n📈 BY PHASE")
        for phase, count in sorted(by_phase.items(), key=lambda x: -x[1]):
            bar = "█" * count + "░" * (10 - min(count, 10))
            print(f"   {phase:30} [{bar}] {count}")

    def render_by_status(self, metrics: Dict):
        """Print projects by status."""
        by_status = metrics.get("by_status", {})

        print(f"\n🚦 BY STATUS")
        for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
            color = self.STATUS_COLORS.get(status, "")
            bar = "█" * count + "░" * (10 - min(count, 10))
            print(f"   {color}{status:15}{self.RESET} [{bar}] {count}")

    def render_milestones(self, metrics: Dict):
        """Print upcoming milestones."""
        milestones = metrics.get("upcoming_milestones", [])[:10]

        print(f"\n📅 UPCOMING MILESTONES")
        if not milestones:
            print("   No upcoming milestones")
            return

        for m in milestones:
            icon = "⚠️ " if m.get("is_overdue") else "📌"
            days = m.get("days_until_due", 0)
            urgency = f"({days}d)" if days >= 0 else "(OVERDUE)"

            color = "\033[91m" if m.get("is_overdue") else "\033[93m" if days <= 7 else ""
            print(f"   {icon} {color}{m.get('project_name', '')}: {m.get('milestone', '')} {urgency}{self.RESET}")

    def render_projects(self, metrics: Dict):
        """Print project details."""
        projects = metrics.get("projects", [])

        print(f"\n📁 PROJECT DETAILS")
        print("-" * 60)

        for p in sorted(projects, key=lambda x: -x.get("health_score", 0)):
            status = p.get("status", "on_track")
            color = self.STATUS_COLORS.get(status, "")
            health = p.get("health_score", 0)

            # Health bar
            health_bar = "█" * (health // 10) + "░" * (10 - health // 10)

            print(f"\n   {p.get('project_id', 'Unknown')}")
            print(f"   {color}Status: {status.upper()}{self.RESET}")
            print(f"   Health: [{health_bar}] {health}%")
            print(f"   Budget: {p.get('budget_percent_used', 0):.0f}% used")
            print(f"   Burn Rate: {p.get('burn_rate_weekly', 0):.1f}h/week")

    def render_full(self, metrics: Dict):
        """Render complete dashboard."""
        self.render_summary(metrics)
        self.render_by_phase(metrics)
        self.render_by_status(metrics)
        self.render_milestones(metrics)
        self.render_projects(metrics)

        print("\n" + "=" * 60 + "\n")
