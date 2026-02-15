"""
View Checker - Validates view organization and properties.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ViewIssue:
    view_name: str
    issue_type: str
    detail: str
    recommendation: str
    severity: str = "warning"


class ViewChecker:
    """Checks view organization, templates, and best practices."""

    def __init__(self):
        self.issues: List[ViewIssue] = []

    def check_view_templates(self, views: List[Dict[str, Any]]) -> List[ViewIssue]:
        """Check that views have appropriate templates applied."""
        issues = []

        # Views that should have templates
        template_required_types = ["FloorPlan", "CeilingPlan", "Section", "Elevation"]

        for view in views:
            view_type = view.get("type", "")
            view_name = view.get("name", "")
            template = view.get("template", None)

            if view_type in template_required_types and not template:
                issues.append(ViewIssue(
                    view_name=view_name,
                    issue_type="Missing Template",
                    detail=f"{view_type} view has no template assigned",
                    recommendation="Apply appropriate view template for consistency",
                    severity="warning"
                ))

        self.issues.extend(issues)
        return issues

    def check_view_on_sheets(self, views: List[Dict[str, Any]],
                             placed_views: List[str]) -> List[ViewIssue]:
        """Check for orphan views not placed on sheets."""
        issues = []

        # View types that should be on sheets
        sheet_types = ["FloorPlan", "CeilingPlan", "Section", "Elevation", "Detail"]

        for view in views:
            view_type = view.get("type", "")
            view_name = view.get("name", "")
            view_id = view.get("id", "")

            if view_type in sheet_types and view_id not in placed_views:
                # Skip working views (often have "Working" in name)
                if "Working" not in view_name and "WORKING" not in view_name:
                    issues.append(ViewIssue(
                        view_name=view_name,
                        issue_type="Not On Sheet",
                        detail=f"View is not placed on any sheet",
                        recommendation="Place on appropriate sheet or mark as working view"
                    ))

        self.issues.extend(issues)
        return issues

    def check_duplicate_views(self, views: List[Dict[str, Any]]) -> List[ViewIssue]:
        """Check for potentially duplicate views."""
        issues = []

        # Group by similar names
        name_groups: Dict[str, List[Dict]] = {}
        for view in views:
            base_name = view.get("name", "").rstrip("0123456789 ").strip()
            if base_name not in name_groups:
                name_groups[base_name] = []
            name_groups[base_name].append(view)

        for base_name, group in name_groups.items():
            if len(group) > 3:  # More than 3 similar views
                issues.append(ViewIssue(
                    view_name=base_name,
                    issue_type="Potential Duplicates",
                    detail=f"Found {len(group)} views with similar names",
                    recommendation="Review and consolidate duplicate views",
                    severity="info"
                ))

        self.issues.extend(issues)
        return issues

    def check_crop_regions(self, views: List[Dict[str, Any]]) -> List[ViewIssue]:
        """Check crop region settings for views."""
        issues = []

        for view in views:
            view_name = view.get("name", "")
            crop_active = view.get("crop_box_active", True)
            crop_visible = view.get("crop_box_visible", False)

            # For sheet views, crop should be active but not visible
            if view.get("on_sheet", False):
                if not crop_active:
                    issues.append(ViewIssue(
                        view_name=view_name,
                        issue_type="Crop Not Active",
                        detail="View on sheet should have crop region active",
                        recommendation="Activate crop region for proper sheet presentation"
                    ))
                if crop_visible:
                    issues.append(ViewIssue(
                        view_name=view_name,
                        issue_type="Crop Visible",
                        detail="View on sheet has visible crop region",
                        recommendation="Hide crop region for clean sheet appearance"
                    ))

        self.issues.extend(issues)
        return issues

    def check_detail_level(self, views: List[Dict[str, Any]]) -> List[ViewIssue]:
        """Check appropriate detail levels for view scales."""
        issues = []

        scale_detail_map = {
            "1/8\" = 1'-0\"": "Coarse",
            "1/4\" = 1'-0\"": "Medium",
            "1/2\" = 1'-0\"": "Fine",
            "1\" = 1'-0\"": "Fine",
            "3\" = 1'-0\"": "Fine",
        }

        for view in views:
            view_name = view.get("name", "")
            scale = view.get("scale", "")
            detail_level = view.get("detail_level", "")

            if scale in scale_detail_map:
                expected = scale_detail_map[scale]
                if detail_level != expected:
                    issues.append(ViewIssue(
                        view_name=view_name,
                        issue_type="Detail Level Mismatch",
                        detail=f"Scale {scale} typically uses {expected} detail, found {detail_level}",
                        recommendation=f"Consider changing detail level to {expected}",
                        severity="info"
                    ))

        self.issues.extend(issues)
        return issues

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all view issues."""
        return {
            "total_issues": len(self.issues),
            "by_severity": {
                "error": len([i for i in self.issues if i.severity == "error"]),
                "warning": len([i for i in self.issues if i.severity == "warning"]),
                "info": len([i for i in self.issues if i.severity == "info"]),
            },
            "by_type": self._group_by_type(),
            "issues": [
                {
                    "view": i.view_name,
                    "type": i.issue_type,
                    "detail": i.detail,
                    "recommendation": i.recommendation,
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
