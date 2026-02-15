"""
Project Metrics - Calculated metrics and KPIs for projects.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Dict, Optional
from .project import Project, ProjectStatus, ProjectPhase


@dataclass
class ProjectMetrics:
    """Calculated metrics for a project."""
    project: Project

    @property
    def health_score(self) -> int:
        """Calculate overall project health (0-100)."""
        score = 100

        # Budget impact (-30 max)
        if self.project.budget_hours > 0:
            budget_ratio = self.project.spent_hours / self.project.budget_hours
            if budget_ratio > 1.0:
                score -= 30
            elif budget_ratio > 0.9:
                score -= 15
            elif budget_ratio > 0.8:
                score -= 5

        # Milestone impact (-30 max)
        overdue = len([m for m in self.project.milestones if m.is_overdue])
        if overdue > 2:
            score -= 30
        elif overdue > 0:
            score -= 15 * overdue

        # Schedule impact (-20 max)
        if self.project.target_completion:
            days_remaining = (self.project.target_completion - date.today()).days
            if days_remaining < 0:
                score -= 20
            elif days_remaining < 14:
                score -= 10

        # Status impact (-20 max)
        status = self.project.status
        if status == ProjectStatus.BEHIND:
            score -= 20
        elif status == ProjectStatus.AT_RISK:
            score -= 10
        elif status == ProjectStatus.AHEAD:
            score += 5  # Bonus

        return max(0, min(100, score))

    @property
    def burn_rate(self) -> float:
        """Hours burned per week (average)."""
        if not self.project.start_date:
            return 0.0

        weeks_elapsed = max(1, (date.today() - self.project.start_date).days / 7)
        return self.project.spent_hours / weeks_elapsed

    @property
    def estimated_completion_date(self) -> Optional[date]:
        """Estimate completion based on burn rate."""
        if self.burn_rate == 0 or self.project.hours_remaining == 0:
            return None

        weeks_remaining = self.project.hours_remaining / self.burn_rate
        return date.today() + timedelta(weeks=weeks_remaining)

    @property
    def is_on_budget(self) -> bool:
        """Check if project is within budget tolerance."""
        return self.project.budget_percent_used <= 100

    @property
    def schedule_variance(self) -> int:
        """Days ahead (+) or behind (-) schedule."""
        if not self.project.target_completion:
            return 0

        if estimated := self.estimated_completion_date:
            return (self.project.target_completion - estimated).days
        return 0

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            "project_id": self.project.id,
            "health_score": self.health_score,
            "burn_rate_weekly": round(self.burn_rate, 1),
            "estimated_completion": (
                self.estimated_completion_date.isoformat()
                if self.estimated_completion_date else None
            ),
            "schedule_variance_days": self.schedule_variance,
            "is_on_budget": self.is_on_budget,
            "budget_percent_used": round(self.project.budget_percent_used, 1),
            "status": self.project.status.value
        }


class DashboardMetrics:
    """Aggregate metrics across all projects."""

    def __init__(self, projects: List[Project]):
        self.projects = projects
        self.project_metrics = [ProjectMetrics(p) for p in projects]

    @property
    def total_projects(self) -> int:
        return len(self.projects)

    @property
    def active_projects(self) -> int:
        return len([p for p in self.projects
                   if p.phase not in [ProjectPhase.COMPLETE, ProjectPhase.ON_HOLD]])

    @property
    def projects_at_risk(self) -> int:
        return len([p for p in self.projects
                   if p.status in [ProjectStatus.AT_RISK, ProjectStatus.BEHIND]])

    @property
    def average_health(self) -> float:
        if not self.project_metrics:
            return 0.0
        return sum(m.health_score for m in self.project_metrics) / len(self.project_metrics)

    @property
    def total_budget_hours(self) -> float:
        return sum(p.budget_hours for p in self.projects)

    @property
    def total_spent_hours(self) -> float:
        return sum(p.spent_hours for p in self.projects)

    @property
    def overall_utilization(self) -> float:
        if self.total_budget_hours == 0:
            return 0.0
        return (self.total_spent_hours / self.total_budget_hours) * 100

    def projects_by_phase(self) -> Dict[str, int]:
        """Count projects by phase."""
        counts = {}
        for p in self.projects:
            phase = p.phase.value
            counts[phase] = counts.get(phase, 0) + 1
        return counts

    def projects_by_status(self) -> Dict[str, int]:
        """Count projects by status."""
        counts = {}
        for p in self.projects:
            status = p.status.value
            counts[status] = counts.get(status, 0) + 1
        return counts

    def upcoming_milestones(self, days: int = 14) -> List[Dict]:
        """Get milestones due within specified days."""
        milestones = []
        cutoff = date.today() + timedelta(days=days)

        for p in self.projects:
            for m in p.milestones:
                if not m.is_complete and m.due_date <= cutoff:
                    milestones.append({
                        "project_id": p.id,
                        "project_name": p.name,
                        "milestone": m.name,
                        "due_date": m.due_date.isoformat(),
                        "days_until_due": m.days_until_due,
                        "is_overdue": m.is_overdue
                    })

        return sorted(milestones, key=lambda m: m["due_date"])

    def to_dict(self) -> Dict:
        """Convert all metrics to dictionary."""
        return {
            "summary": {
                "total_projects": self.total_projects,
                "active_projects": self.active_projects,
                "at_risk": self.projects_at_risk,
                "average_health": round(self.average_health, 1),
                "total_budget_hours": self.total_budget_hours,
                "total_spent_hours": self.total_spent_hours,
                "overall_utilization": round(self.overall_utilization, 1)
            },
            "by_phase": self.projects_by_phase(),
            "by_status": self.projects_by_status(),
            "upcoming_milestones": self.upcoming_milestones(),
            "projects": [m.to_dict() for m in self.project_metrics]
        }
