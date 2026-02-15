"""
Team Model - Team member and assignment tracking.
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Optional
from enum import Enum


class Role(Enum):
    """Team member roles."""
    PRINCIPAL = "Principal"
    PROJECT_MANAGER = "Project Manager"
    PROJECT_ARCHITECT = "Project Architect"
    DESIGNER = "Designer"
    DRAFTER = "Drafter"
    INTERN = "Intern"
    CONSULTANT = "Consultant"


@dataclass
class Assignment:
    """Project assignment for a team member."""
    project_id: str
    project_name: str
    role: Role
    allocated_hours: float = 0.0
    logged_hours: float = 0.0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    active: bool = True

    @property
    def utilization(self) -> float:
        """Hours used vs allocated."""
        if self.allocated_hours == 0:
            return 0.0
        return (self.logged_hours / self.allocated_hours) * 100


@dataclass
class TeamMember:
    """Team member profile."""
    id: str
    name: str
    email: str
    role: Role
    department: str = "Architecture"
    target_hours_weekly: float = 40.0
    assignments: List[Assignment] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    active: bool = True

    @property
    def total_allocated_hours(self) -> float:
        """Total hours allocated across all active projects."""
        return sum(a.allocated_hours for a in self.assignments if a.active)

    @property
    def total_logged_hours(self) -> float:
        """Total hours logged across all projects."""
        return sum(a.logged_hours for a in self.assignments)

    @property
    def current_projects(self) -> List[Assignment]:
        """List of active project assignments."""
        return [a for a in self.assignments if a.active]

    @property
    def availability(self) -> float:
        """Weekly hours available (target - allocated)."""
        weekly_allocated = self.total_allocated_hours / 4  # Rough weekly estimate
        return max(0, self.target_hours_weekly - weekly_allocated)

    @property
    def is_overallocated(self) -> bool:
        """Check if member is overallocated."""
        return self.availability < 0

    def add_assignment(self, project_id: str, project_name: str,
                       role: Role = None, hours: float = 0.0):
        """Add a project assignment."""
        self.assignments.append(Assignment(
            project_id=project_id,
            project_name=project_name,
            role=role or self.role,
            allocated_hours=hours,
            start_date=date.today()
        ))

    def log_hours(self, project_id: str, hours: float):
        """Log hours to a project assignment."""
        for a in self.assignments:
            if a.project_id == project_id and a.active:
                a.logged_hours += hours
                return True
        return False

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role.value,
            "department": self.department,
            "target_hours_weekly": self.target_hours_weekly,
            "total_allocated": self.total_allocated_hours,
            "total_logged": self.total_logged_hours,
            "availability": self.availability,
            "is_overallocated": self.is_overallocated,
            "current_projects": [
                {
                    "project_id": a.project_id,
                    "project_name": a.project_name,
                    "role": a.role.value,
                    "hours_allocated": a.allocated_hours,
                    "hours_logged": a.logged_hours,
                    "utilization": a.utilization
                }
                for a in self.current_projects
            ],
            "skills": self.skills
        }
