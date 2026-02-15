"""Data models for OpportunityEngine."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional


class OpportunityStatus(str, Enum):
    DISCOVERED = "discovered"
    QUALIFIED = "qualified"
    PROPOSAL_DRAFTED = "proposal_drafted"
    SUBMITTED = "submitted"
    WON = "won"
    LOST = "lost"
    EXPIRED = "expired"
    DISMISSED = "dismissed"


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class CompetitionLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass
class Opportunity:
    id: Optional[int] = None
    source: str = ""
    source_id: str = ""
    title: str = ""
    description: str = ""
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    currency: str = "USD"
    deadline: Optional[str] = None
    skills_required: list[str] = field(default_factory=list)
    competition_level: str = CompetitionLevel.UNKNOWN
    client_info: dict = field(default_factory=dict)
    score: int = 0
    status: str = OpportunityStatus.DISCOVERED
    discovered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    qualified_at: Optional[str] = None
    submitted_at: Optional[str] = None
    resolved_at: Optional[str] = None
    notes: str = ""
    raw_data: dict = field(default_factory=dict)

    # Score breakdown (persisted as JSON)
    score_breakdown: dict = field(default_factory=dict, repr=False)

    def to_row(self) -> dict:
        """Convert to a dict suitable for SQLite insertion."""
        return {
            "source": self.source,
            "source_id": self.source_id,
            "title": self.title,
            "description": self.description,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "currency": self.currency,
            "deadline": self.deadline,
            "skills_required": json.dumps(self.skills_required),
            "competition_level": self.competition_level,
            "client_info": json.dumps(self.client_info),
            "score": self.score,
            "status": self.status,
            "discovered_at": self.discovered_at,
            "qualified_at": self.qualified_at,
            "submitted_at": self.submitted_at,
            "resolved_at": self.resolved_at,
            "notes": self.notes,
            "raw_data": json.dumps(self.raw_data),
            "score_breakdown": json.dumps(self.score_breakdown) if self.score_breakdown else None,
        }

    @classmethod
    def from_row(cls, row: dict) -> Opportunity:
        """Create from a SQLite row dict."""
        return cls(
            id=row["id"],
            source=row["source"],
            source_id=row.get("source_id", ""),
            title=row["title"],
            description=row.get("description", ""),
            budget_min=row.get("budget_min"),
            budget_max=row.get("budget_max"),
            currency=row.get("currency", "USD"),
            deadline=row.get("deadline"),
            skills_required=json.loads(row.get("skills_required") or "[]"),
            competition_level=row.get("competition_level", CompetitionLevel.UNKNOWN),
            client_info=json.loads(row.get("client_info") or "{}"),
            score=row.get("score", 0),
            status=row.get("status", OpportunityStatus.DISCOVERED),
            discovered_at=row["discovered_at"],
            qualified_at=row.get("qualified_at"),
            submitted_at=row.get("submitted_at"),
            resolved_at=row.get("resolved_at"),
            notes=row.get("notes", ""),
            raw_data=json.loads(row.get("raw_data") or "{}"),
            score_breakdown=json.loads(row.get("score_breakdown") or "{}"),
        )

    @property
    def budget_display(self) -> str:
        if self.budget_min and self.budget_max:
            return f"${self.budget_min:,.0f} - ${self.budget_max:,.0f}"
        elif self.budget_max:
            return f"Up to ${self.budget_max:,.0f}"
        elif self.budget_min:
            return f"From ${self.budget_min:,.0f}"
        return "Not specified"

    @property
    def age_hours(self) -> float:
        discovered = datetime.fromisoformat(self.discovered_at)
        return (datetime.utcnow() - discovered).total_seconds() / 3600


@dataclass
class Proposal:
    id: Optional[int] = None
    opportunity_id: int = 0
    content: str = ""
    pricing: str = ""
    template_used: str = ""
    status: str = ProposalStatus.DRAFT
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    approved_at: Optional[str] = None
    submitted_at: Optional[str] = None
    client_response: str = ""
    lessons_learned: str = ""

    def to_row(self) -> dict:
        return {
            "opportunity_id": self.opportunity_id,
            "content": self.content,
            "pricing": self.pricing,
            "template_used": self.template_used,
            "status": self.status,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "submitted_at": self.submitted_at,
            "client_response": self.client_response,
            "lessons_learned": self.lessons_learned,
        }

    @classmethod
    def from_row(cls, row: dict) -> Proposal:
        return cls(
            id=row["id"],
            opportunity_id=row["opportunity_id"],
            content=row["content"],
            pricing=row.get("pricing", ""),
            template_used=row.get("template_used", ""),
            status=row.get("status", ProposalStatus.DRAFT),
            created_at=row["created_at"],
            approved_at=row.get("approved_at"),
            submitted_at=row.get("submitted_at"),
            client_response=row.get("client_response", ""),
            lessons_learned=row.get("lessons_learned", ""),
        )


@dataclass
class Template:
    id: Optional[int] = None
    name: str = ""
    category: str = ""
    content: str = ""
    times_used: int = 0
    wins: int = 0
    losses: int = 0
    last_used: Optional[str] = None

    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        return (self.wins / total * 100) if total > 0 else 0.0

    def to_row(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "content": self.content,
            "times_used": self.times_used,
            "wins": self.wins,
            "losses": self.losses,
            "last_used": self.last_used,
        }

    @classmethod
    def from_row(cls, row: dict) -> Template:
        return cls(
            id=row["id"],
            name=row["name"],
            category=row.get("category", ""),
            content=row["content"],
            times_used=row.get("times_used", 0),
            wins=row.get("wins", 0),
            losses=row.get("losses", 0),
            last_used=row.get("last_used"),
        )


@dataclass
class ScanLog:
    id: Optional[int] = None
    source: str = ""
    scanned_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    opportunities_found: int = 0
    new_opportunities: int = 0
    errors: str = ""
    duration_ms: int = 0

    def to_row(self) -> dict:
        return {
            "source": self.source,
            "scanned_at": self.scanned_at,
            "opportunities_found": self.opportunities_found,
            "new_opportunities": self.new_opportunities,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_row(cls, row: dict) -> ScanLog:
        return cls(
            id=row["id"],
            source=row["source"],
            scanned_at=row["scanned_at"],
            opportunities_found=row.get("opportunities_found", 0),
            new_opportunities=row.get("new_opportunities", 0),
            errors=row.get("errors", ""),
            duration_ms=row.get("duration_ms", 0),
        )
