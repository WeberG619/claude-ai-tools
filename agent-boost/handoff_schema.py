#!/usr/bin/env python3
"""
Handoff Schema — Structured data contracts between pipeline stages.

Each stage receives a compact JSON handoff from the previous stage.
No raw conversation dumps. No exploration tokens. Clean context only.

Usage:
    from handoff_schema import SpecOutput, DesignOutput, ImplementOutput, ReviewOutput
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Stage 1 output: SPEC
# ---------------------------------------------------------------------------

@dataclass
class FileRef:
    """A file involved in the task."""
    path: str
    reason: str          # why this file matters
    action: str          # "read", "modify", "create", "delete"


@dataclass
class Change:
    """A discrete change to be made."""
    file_path: str
    description: str     # what changes, not how — that's for ARCHITECT
    why: str             # rationale tied back to objective


@dataclass
class AcceptanceCriterion:
    description: str
    verifiable: bool     # can this be checked programmatically?
    check_command: Optional[str] = None   # e.g. "pytest tests/test_retry.py"


@dataclass
class SpecOutput:
    """
    Output of Stage 1 (SPEC).
    Read-only stage: no code written, no files modified.
    """
    objective: str                                     # one-sentence goal
    files_involved: list[FileRef] = field(default_factory=list)
    changes_needed: list[Change] = field(default_factory=list)
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    scope_estimate: str = "medium"                    # "trivial" | "small" | "medium" | "large"
    notes: str = ""                                   # anything the ARCHITECT should know
    task_raw: str = ""                                # original user request, verbatim
    created_at: str = field(default_factory=lambda: _now())

    # --- serialization ---

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def to_file(self, path: str | Path) -> Path:
        p = Path(path)
        p.write_text(self.to_json())
        return p

    @classmethod
    def from_json(cls, raw: str) -> "SpecOutput":
        data = json.loads(raw)
        data["files_involved"] = [FileRef(**f) for f in data.get("files_involved", [])]
        data["changes_needed"] = [Change(**c) for c in data.get("changes_needed", [])]
        data["acceptance_criteria"] = [AcceptanceCriterion(**a) for a in data.get("acceptance_criteria", [])]
        return cls(**data)

    @classmethod
    def from_file(cls, path: str | Path) -> "SpecOutput":
        return cls.from_json(Path(path).read_text())

    def validate(self) -> list[str]:
        """Return a list of validation errors. Empty means OK."""
        errors = []
        if not self.objective:
            errors.append("objective is required")
        if not self.files_involved:
            errors.append("files_involved must name at least one file")
        if not self.changes_needed:
            errors.append("changes_needed must describe at least one change")
        if not self.acceptance_criteria:
            errors.append("acceptance_criteria must have at least one criterion")
        return errors


# ---------------------------------------------------------------------------
# Stage 2 output: DESIGN
# ---------------------------------------------------------------------------

@dataclass
class Risk:
    description: str
    severity: str        # "low" | "medium" | "high"
    mitigation: str


@dataclass
class DesignOutput:
    """
    Output of Stage 2 (ARCHITECT).
    Read-only stage: validates spec, produces an implementation plan.
    Can REJECT with feedback → back to Stage 1.
    """
    approved: bool                                     # False = rejection
    rejection_reason: str = ""                        # populated when approved=False
    rejection_feedback: str = ""                      # specific guidance for Stage 1 retry

    approach: str = ""                                # implementation strategy, high-level
    affected_files: list[str] = field(default_factory=list)
    implementation_steps: list[str] = field(default_factory=list)
    risks: list[Risk] = field(default_factory=list)
    test_strategy: str = ""
    worktree_recommended: bool = False                # True if 3+ files or risky refactor
    notes: str = ""
    created_at: str = field(default_factory=lambda: _now())

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def to_file(self, path: str | Path) -> Path:
        p = Path(path)
        p.write_text(self.to_json())
        return p

    @classmethod
    def from_json(cls, raw: str) -> "DesignOutput":
        data = json.loads(raw)
        data["risks"] = [Risk(**r) for r in data.get("risks", [])]
        return cls(**data)

    @classmethod
    def from_file(cls, path: str | Path) -> "DesignOutput":
        return cls.from_json(Path(path).read_text())

    def validate(self) -> list[str]:
        errors = []
        if self.approved and not self.approach:
            errors.append("approach is required when approved=True")
        if self.approved and not self.implementation_steps:
            errors.append("implementation_steps required when approved=True")
        if not self.approved and not self.rejection_reason:
            errors.append("rejection_reason required when approved=False")
        return errors


# ---------------------------------------------------------------------------
# Stage 3 output: IMPLEMENT
# ---------------------------------------------------------------------------

@dataclass
class FileChange:
    path: str
    action: str          # "modified" | "created" | "deleted"
    summary: str         # one-line description of what changed


@dataclass
class ImplementOutput:
    """
    Output of Stage 3 (IMPLEMENT).
    Editor stage: makes the actual code changes.
    """
    success: bool
    files_changed: list[FileChange] = field(default_factory=list)
    summary: str = ""                                  # 2-3 sentence description
    deviations: list[str] = field(default_factory=list)  # if implementation differed from design
    error: str = ""                                    # populated if success=False
    created_at: str = field(default_factory=lambda: _now())

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def to_file(self, path: str | Path) -> Path:
        p = Path(path)
        p.write_text(self.to_json())
        return p

    @classmethod
    def from_json(cls, raw: str) -> "ImplementOutput":
        data = json.loads(raw)
        data["files_changed"] = [FileChange(**f) for f in data.get("files_changed", [])]
        return cls(**data)

    @classmethod
    def from_file(cls, path: str | Path) -> "ImplementOutput":
        return cls.from_json(Path(path).read_text())

    def validate(self) -> list[str]:
        errors = []
        if self.success and not self.files_changed:
            errors.append("files_changed must list at least one file when success=True")
        if self.success and not self.summary:
            errors.append("summary required when success=True")
        return errors


# ---------------------------------------------------------------------------
# Stage 4 output: REVIEW
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    file_path: str
    description: str
    severity: str        # "blocker" | "warning" | "suggestion"
    criterion_violated: str = ""   # which acceptance criterion this relates to


@dataclass
class ReviewOutput:
    """
    Output of Stage 4 (REVIEW).
    Read-only stage: checks implementation against spec acceptance criteria.
    Can REJECT with specific fixes → back to Stage 3.
    """
    passed: bool
    rejection_reason: str = ""                        # summary of why it failed
    issues: list[Issue] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    tests_run: list[str] = field(default_factory=list)
    tests_passed: bool = True
    criteria_results: dict = field(default_factory=dict)  # criterion -> "pass" | "fail" | "skip"
    notes: str = ""
    created_at: str = field(default_factory=lambda: _now())

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def to_file(self, path: str | Path) -> Path:
        p = Path(path)
        p.write_text(self.to_json())
        return p

    @classmethod
    def from_json(cls, raw: str) -> "ReviewOutput":
        data = json.loads(raw)
        data["issues"] = [Issue(**i) for i in data.get("issues", [])]
        return cls(**data)

    @classmethod
    def from_file(cls, path: str | Path) -> "ReviewOutput":
        return cls.from_json(Path(path).read_text())

    def validate(self) -> list[str]:
        errors = []
        if not self.passed and not self.rejection_reason:
            errors.append("rejection_reason required when passed=False")
        if not self.passed and not self.issues:
            errors.append("issues required when passed=False — be specific about what to fix")
        return errors

    def blockers(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "blocker"]


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_handoff(path: str | Path, stage: str):
    """
    Load a handoff file by stage name.
    stage: "spec" | "design" | "implement" | "review"
    """
    mapping = {
        "spec": SpecOutput,
        "design": DesignOutput,
        "implement": ImplementOutput,
        "review": ReviewOutput,
    }
    cls = mapping.get(stage)
    if cls is None:
        raise ValueError(f"Unknown stage: {stage}. Must be one of {list(mapping)}")
    return cls.from_file(path)


if __name__ == "__main__":
    # Quick smoke test
    spec = SpecOutput(
        objective="Add retry logic to RevitMCPBridge API calls",
        task_raw="Add retry logic to RevitMCPBridge API calls with exponential backoff",
        files_involved=[
            FileRef(path="/mnt/d/RevitMCPBridge/client.py", reason="makes API calls", action="modify"),
        ],
        changes_needed=[
            Change(
                file_path="/mnt/d/RevitMCPBridge/client.py",
                description="Wrap API call methods with retry decorator using exponential backoff",
                why="Named pipe calls can fail transiently when Revit is loading",
            ),
        ],
        acceptance_criteria=[
            AcceptanceCriterion(
                description="API calls retry up to 3 times on connection error",
                verifiable=True,
                check_command="pytest tests/test_retry.py",
            ),
        ],
        scope_estimate="small",
    )

    errors = spec.validate()
    assert not errors, f"Validation failed: {errors}"

    roundtrip = SpecOutput.from_json(spec.to_json())
    assert roundtrip.objective == spec.objective

    print("handoff_schema.py: smoke test passed")
    print(spec.to_json())
