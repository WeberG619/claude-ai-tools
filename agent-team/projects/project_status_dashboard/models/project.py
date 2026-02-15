"""
Project Model - Core project tracking data structures.
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional, Dict
from enum import Enum


class ProjectPhase(Enum):
    """Standard architecture project phases."""
    PROGRAMMING = "Programming"
    SCHEMATIC_DESIGN = "Schematic Design"
    DESIGN_DEVELOPMENT = "Design Development"
    CONSTRUCTION_DOCUMENTS = "Construction Documents"
    BIDDING = "Bidding & Negotiation"
    CONSTRUCTION_ADMIN = "Construction Administration"
    CLOSEOUT = "Closeout"
    COMPLETE = "Complete"
    ON_HOLD = "On Hold"


class ProjectStatus(Enum):
    """Project status indicators."""
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BEHIND = "behind"
    AHEAD = "ahead"
    ON_HOLD = "on_hold"


@dataclass
class Milestone:
    """Project milestone."""
    name: str
    due_date: date
    completed_date: Optional[date] = None
    description: str = ""
    phase: Optional[ProjectPhase] = None

    @property
    def is_complete(self) -> bool:
        return self.completed_date is not None

    @property
    def is_overdue(self) -> bool:
        if self.is_complete:
            return False
        return date.today() > self.due_date

    @property
    def days_until_due(self) -> int:
        if self.is_complete:
            return 0
        return (self.due_date - date.today()).days


@dataclass
class Project:
    """Architecture project."""
    id: str
    number: str
    name: str
    client: str
    phase: ProjectPhase = ProjectPhase.PROGRAMMING
    start_date: date = field(default_factory=date.today)
    target_completion: Optional[date] = None
    milestones: List[Milestone] = field(default_factory=list)
    budget_hours: float = 0.0
    spent_hours: float = 0.0
    fee: float = 0.0
    billed: float = 0.0
    team_members: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def status(self) -> ProjectStatus:
        """Calculate project status based on metrics."""
        if self.phase == ProjectPhase.ON_HOLD:
            return ProjectStatus.ON_HOLD

        # Check milestone status
        overdue_milestones = [m for m in self.milestones if m.is_overdue]
        if overdue_milestones:
            return ProjectStatus.BEHIND

        # Check hours
        if self.budget_hours > 0:
            hours_ratio = self.spent_hours / self.budget_hours
            if hours_ratio > 0.9:
                return ProjectStatus.AT_RISK
            if hours_ratio < 0.5 and self.phase_progress > 0.6:
                return ProjectStatus.AHEAD

        # Check upcoming milestones
        urgent_milestones = [m for m in self.milestones
                           if not m.is_complete and m.days_until_due <= 7]
        if urgent_milestones:
            return ProjectStatus.AT_RISK

        return ProjectStatus.ON_TRACK

    @property
    def phase_progress(self) -> float:
        """Estimate overall phase progress (0.0 - 1.0)."""
        phase_order = list(ProjectPhase)
        try:
            current_idx = phase_order.index(self.phase)
            return current_idx / (len(phase_order) - 1)
        except ValueError:
            return 0.0

    @property
    def hours_remaining(self) -> float:
        """Hours remaining in budget."""
        return max(0, self.budget_hours - self.spent_hours)

    @property
    def budget_percent_used(self) -> float:
        """Percentage of budget hours used."""
        if self.budget_hours == 0:
            return 0.0
        return (self.spent_hours / self.budget_hours) * 100

    @property
    def next_milestone(self) -> Optional[Milestone]:
        """Get next upcoming milestone."""
        upcoming = [m for m in self.milestones if not m.is_complete]
        if not upcoming:
            return None
        return min(upcoming, key=lambda m: m.due_date)

    def add_milestone(self, name: str, due_date: date,
                      description: str = "", phase: ProjectPhase = None):
        """Add a milestone to the project."""
        self.milestones.append(Milestone(
            name=name,
            due_date=due_date,
            description=description,
            phase=phase or self.phase
        ))
        self.updated_at = datetime.now()

    def complete_milestone(self, name: str, completed_date: date = None):
        """Mark a milestone as complete."""
        for m in self.milestones:
            if m.name == name:
                m.completed_date = completed_date or date.today()
                self.updated_at = datetime.now()
                return True
        return False

    def advance_phase(self):
        """Advance to the next project phase."""
        phases = list(ProjectPhase)
        try:
            current_idx = phases.index(self.phase)
            if current_idx < len(phases) - 1:
                self.phase = phases[current_idx + 1]
                self.updated_at = datetime.now()
        except ValueError:
            pass

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "number": self.number,
            "name": self.name,
            "client": self.client,
            "phase": self.phase.value,
            "status": self.status.value,
            "start_date": self.start_date.isoformat(),
            "target_completion": self.target_completion.isoformat() if self.target_completion else None,
            "budget_hours": self.budget_hours,
            "spent_hours": self.spent_hours,
            "hours_remaining": self.hours_remaining,
            "budget_percent": self.budget_percent_used,
            "fee": self.fee,
            "billed": self.billed,
            "team_members": self.team_members,
            "tags": self.tags,
            "milestones": [
                {
                    "name": m.name,
                    "due_date": m.due_date.isoformat(),
                    "completed": m.is_complete,
                    "overdue": m.is_overdue,
                    "days_until_due": m.days_until_due
                }
                for m in self.milestones
            ],
            "next_milestone": self.next_milestone.name if self.next_milestone else None
        }
