"""
Workset Checker - Validates workset organization and element placement.
"""
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class WorksetIssue:
    workset_name: str
    issue_type: str
    detail: str
    affected_elements: int
    severity: str = "warning"


class WorksetChecker:
    """Checks workset organization and proper element assignment."""

    # Standard workset naming and content rules
    STANDARD_WORKSETS = {
        "Shared Levels and Grids": ["Grids", "Levels"],
        "Core and Shell": ["Walls", "Floors", "Roofs", "Ceilings"],
        "Interior": ["Walls", "Doors", "Furniture"],
        "MEP": ["Mechanical Equipment", "Electrical", "Plumbing"],
        "Site": ["Topography", "Site Components"],
        "Linked Files": [],  # For linked models
    }

    def __init__(self):
        self.issues: List[WorksetIssue] = []

    def check_workset_naming(self, worksets: List[Dict[str, Any]]) -> List[WorksetIssue]:
        """Check workset naming follows standards."""
        issues = []
        workset_names = [w.get("name", "") for w in worksets]

        # Check for required worksets
        for required in ["Shared Levels and Grids"]:
            if required not in workset_names:
                issues.append(WorksetIssue(
                    workset_name=required,
                    issue_type="Missing Required Workset",
                    detail=f"Standard workset '{required}' not found",
                    affected_elements=0,
                    severity="error"
                ))

        # Check for default "Workset1" still present
        if "Workset1" in workset_names:
            issues.append(WorksetIssue(
                workset_name="Workset1",
                issue_type="Default Workset",
                detail="Default 'Workset1' should be renamed or removed",
                affected_elements=0,
                severity="warning"
            ))

        self.issues.extend(issues)
        return issues

    def check_element_placement(self, worksets: List[Dict[str, Any]],
                                elements: List[Dict[str, Any]]) -> List[WorksetIssue]:
        """Check elements are on appropriate worksets."""
        issues = []

        # Build workset lookup
        workset_map = {w.get("id"): w.get("name", "") for w in worksets}

        # Check grids and levels
        grid_level_issues = []
        for elem in elements:
            category = elem.get("category", "")
            workset_id = elem.get("workset_id")
            workset_name = workset_map.get(workset_id, "Unknown")

            if category in ["Grids", "Levels"]:
                if "Shared" not in workset_name and "Grid" not in workset_name:
                    grid_level_issues.append(elem)

        if grid_level_issues:
            issues.append(WorksetIssue(
                workset_name="Various",
                issue_type="Grids/Levels Misplaced",
                detail="Grids and Levels should be on 'Shared Levels and Grids' workset",
                affected_elements=len(grid_level_issues),
                severity="error"
            ))

        # Check linked files
        link_issues = []
        for elem in elements:
            category = elem.get("category", "")
            workset_id = elem.get("workset_id")
            workset_name = workset_map.get(workset_id, "Unknown")

            if "Link" in category or "RVT" in category:
                if "Link" not in workset_name:
                    link_issues.append(elem)

        if link_issues:
            issues.append(WorksetIssue(
                workset_name="Various",
                issue_type="Links Misplaced",
                detail="Linked files should be on dedicated 'Linked Files' workset",
                affected_elements=len(link_issues),
                severity="warning"
            ))

        self.issues.extend(issues)
        return issues

    def check_workset_visibility(self, worksets: List[Dict[str, Any]]) -> List[WorksetIssue]:
        """Check workset default visibility settings."""
        issues = []

        for workset in worksets:
            name = workset.get("name", "")
            default_visible = workset.get("default_visible", True)

            # Linked files workset should be off by default
            if "Link" in name and default_visible:
                issues.append(WorksetIssue(
                    workset_name=name,
                    issue_type="Visibility Setting",
                    detail="Linked files workset should be off by default",
                    affected_elements=0,
                    severity="info"
                ))

        self.issues.extend(issues)
        return issues

    def check_workset_borrowing(self, worksets: List[Dict[str, Any]],
                                 user_borrowing: Dict[str, List[str]]) -> List[WorksetIssue]:
        """Check for workset borrowing conflicts."""
        issues = []

        for workset in worksets:
            name = workset.get("name", "")
            owner = workset.get("owner", None)

            if owner and owner != "Not Owned":
                # Shared worksets shouldn't be owned
                if "Shared" in name:
                    issues.append(WorksetIssue(
                        workset_name=name,
                        issue_type="Ownership Conflict",
                        detail=f"Shared workset is owned by {owner}",
                        affected_elements=0,
                        severity="warning"
                    ))

        self.issues.extend(issues)
        return issues

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all workset issues."""
        total_affected = sum(i.affected_elements for i in self.issues)

        return {
            "total_issues": len(self.issues),
            "total_affected_elements": total_affected,
            "by_severity": {
                "error": len([i for i in self.issues if i.severity == "error"]),
                "warning": len([i for i in self.issues if i.severity == "warning"]),
                "info": len([i for i in self.issues if i.severity == "info"]),
            },
            "by_type": self._group_by_type(),
            "issues": [
                {
                    "workset": i.workset_name,
                    "type": i.issue_type,
                    "detail": i.detail,
                    "affected_count": i.affected_elements,
                    "severity": i.severity
                }
                for i in self.issues
            ]
        }

    def _group_by_type(self) -> Dict[str, int]:
        """Group issues by type."""
        groups = {}
        for i in self.issues:
            groups[i.issue_type] = groups.get(i.issue_type, 0) + 1
        return groups
