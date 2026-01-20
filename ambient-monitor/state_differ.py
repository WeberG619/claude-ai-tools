#!/usr/bin/env python3
"""
State Differ - Detect changes between Revit model snapshots.
Lightweight comparison for fast polling.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RevitState:
    """Lightweight snapshot of Revit model state."""
    timestamp: datetime
    view_id: Optional[int] = None
    view_name: str = ""
    view_type: str = ""
    element_counts: dict = field(default_factory=dict)
    unjoined_wall_ids: list = field(default_factory=list)
    wall_count: int = 0


@dataclass
class StateChanges:
    """Changes detected between two states."""
    has_changes: bool = False
    view_changed: bool = False
    old_view_name: str = ""
    new_view_name: str = ""

    walls_added: int = 0
    walls_removed: int = 0

    new_unjoined_walls: list = field(default_factory=list)
    fixed_unjoined_walls: list = field(default_factory=list)
    total_unjoined: int = 0

    element_changes: dict = field(default_factory=dict)

    def __str__(self) -> str:
        parts = []
        if self.view_changed:
            parts.append(f"view: {self.old_view_name} → {self.new_view_name}")
        if self.walls_added:
            parts.append(f"+{self.walls_added} walls")
        if self.walls_removed:
            parts.append(f"-{self.walls_removed} walls")
        if self.new_unjoined_walls:
            parts.append(f"{len(self.new_unjoined_walls)} new unjoined")
        if self.fixed_unjoined_walls:
            parts.append(f"{len(self.fixed_unjoined_walls)} walls joined")
        return ", ".join(parts) if parts else "no changes"


def diff_states(old_state: Optional[RevitState], new_state: RevitState) -> StateChanges:
    """
    Compare two states and return changes.
    First state can be None (initial snapshot).
    """
    changes = StateChanges()

    # First run - no comparison possible
    if old_state is None:
        changes.total_unjoined = len(new_state.unjoined_wall_ids)
        return changes

    # View changed?
    if old_state.view_id != new_state.view_id:
        changes.has_changes = True
        changes.view_changed = True
        changes.old_view_name = old_state.view_name
        changes.new_view_name = new_state.view_name

    # Wall count changes
    wall_diff = new_state.wall_count - old_state.wall_count
    if wall_diff > 0:
        changes.has_changes = True
        changes.walls_added = wall_diff
    elif wall_diff < 0:
        changes.has_changes = True
        changes.walls_removed = abs(wall_diff)

    # Unjoined wall changes
    old_unjoined = set(old_state.unjoined_wall_ids)
    new_unjoined = set(new_state.unjoined_wall_ids)

    newly_unjoined = new_unjoined - old_unjoined
    now_joined = old_unjoined - new_unjoined

    if newly_unjoined:
        changes.has_changes = True
        changes.new_unjoined_walls = list(newly_unjoined)

    if now_joined:
        changes.has_changes = True
        changes.fixed_unjoined_walls = list(now_joined)

    changes.total_unjoined = len(new_unjoined)

    # Element count changes by category
    all_categories = set(old_state.element_counts.keys()) | set(new_state.element_counts.keys())
    for cat in all_categories:
        old_count = old_state.element_counts.get(cat, 0)
        new_count = new_state.element_counts.get(cat, 0)
        if old_count != new_count:
            changes.has_changes = True
            changes.element_changes[cat] = {
                "old": old_count,
                "new": new_count,
                "diff": new_count - old_count
            }

    return changes
