#!/usr/bin/env python3
"""
Analysis Rules - Determine what changes trigger announcements.
Start conservative: voice for unjoined walls >= 2, queue everything else.
"""

from dataclasses import dataclass, field
from typing import List
from enum import Enum

from state_differ import StateChanges, RevitState


class FindingTier(Enum):
    """Output tier for findings."""
    VOICE = "voice"       # Actionable, announce now
    QUEUE = "queue"       # Log for later review
    CRITICAL = "critical" # Blocks work, must alert


@dataclass
class Finding:
    """A finding from analysis."""
    tier: FindingTier
    category: str
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """Results of analyzing changes."""
    voice_findings: List[Finding] = field(default_factory=list)
    queue_findings: List[Finding] = field(default_factory=list)
    critical_findings: List[Finding] = field(default_factory=list)


# =============================================================================
# TRIGGER THRESHOLDS
# =============================================================================

VOICE_TRIGGERS = {
    # Trigger voice when these conditions are met
    "unjoined_walls": lambda count: count >= 2,
    "overlapping_elements": lambda count: count >= 1,  # Always announce
    "room_without_door": lambda count: count >= 1,     # Always announce
    "egress_blocked": lambda count: count >= 1,        # Always announce
}

QUEUE_ONLY = {
    # These just get logged, never announced
    "elements_added": True,
    "elements_removed": True,
    "view_changed": True,
}

IGNORE = {
    # Don't even log these
    "selection_changed": True,
}

CRITICAL_TRIGGERS = {
    # These require immediate attention
    "egress_blocked": lambda count: count >= 1,
    "structural_conflict": lambda count: count >= 1,
}


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def analyze_changes(changes: StateChanges, current_state: RevitState) -> AnalysisResult:
    """
    Analyze changes and produce findings categorized by tier.
    """
    result = AnalysisResult()

    # --- UNJOINED WALLS (Primary focus) ---
    if changes.new_unjoined_walls:
        unjoined_count = len(changes.new_unjoined_walls)

        if VOICE_TRIGGERS["unjoined_walls"](unjoined_count):
            # Voice announcement
            result.voice_findings.append(Finding(
                tier=FindingTier.VOICE,
                category="unjoined_walls",
                message=f"{unjoined_count} walls unjoined" if unjoined_count > 1 else "1 wall unjoined",
                details={
                    "wall_ids": changes.new_unjoined_walls,
                    "total_unjoined": changes.total_unjoined
                }
            ))
        else:
            # Just queue it
            result.queue_findings.append(Finding(
                tier=FindingTier.QUEUE,
                category="unjoined_walls",
                message=f"{unjoined_count} wall unjoined (below voice threshold)",
                details={"wall_ids": changes.new_unjoined_walls}
            ))

    # Log when walls get joined (positive feedback)
    if changes.fixed_unjoined_walls:
        fixed_count = len(changes.fixed_unjoined_walls)
        result.queue_findings.append(Finding(
            tier=FindingTier.QUEUE,
            category="walls_joined",
            message=f"{fixed_count} wall{'s' if fixed_count > 1 else ''} joined",
            details={"wall_ids": changes.fixed_unjoined_walls}
        ))

    # --- WALL ADDITIONS/REMOVALS (Queue only) ---
    if changes.walls_added and QUEUE_ONLY.get("elements_added"):
        result.queue_findings.append(Finding(
            tier=FindingTier.QUEUE,
            category="walls_added",
            message=f"+{changes.walls_added} walls",
            details={"count": changes.walls_added}
        ))

    if changes.walls_removed and QUEUE_ONLY.get("elements_removed"):
        result.queue_findings.append(Finding(
            tier=FindingTier.QUEUE,
            category="walls_removed",
            message=f"-{changes.walls_removed} walls",
            details={"count": changes.walls_removed}
        ))

    # --- VIEW CHANGES (Queue only) ---
    if changes.view_changed and QUEUE_ONLY.get("view_changed"):
        result.queue_findings.append(Finding(
            tier=FindingTier.QUEUE,
            category="view_changed",
            message=f"View changed: {changes.new_view_name}",
            details={
                "old_view": changes.old_view_name,
                "new_view": changes.new_view_name
            }
        ))

    # --- TOTAL UNJOINED CHECK (every poll, not just on change) ---
    # If total unjoined is high, remind periodically
    if current_state and changes.total_unjoined >= 5:
        # This will be controlled by cooldown in daemon
        result.queue_findings.append(Finding(
            tier=FindingTier.QUEUE,
            category="unjoined_summary",
            message=f"Total unjoined walls: {changes.total_unjoined}",
            details={"total": changes.total_unjoined}
        ))

    return result


def analyze_for_critical(current_state: RevitState) -> List[Finding]:
    """
    Check for critical issues that block downstream work.
    These run separately from change detection.

    TODO: Implement when we add room/egress analysis
    """
    findings = []

    # Future: Check for egress issues
    # Future: Check for structural conflicts
    # Future: Check for code violations

    return findings
