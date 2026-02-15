"""
Link Checker - Validates linked file management.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LinkIssue:
    link_name: str
    issue_type: str
    detail: str
    file_path: str
    severity: str = "warning"


class LinkChecker:
    """Checks linked file status, paths, and management."""

    def __init__(self):
        self.issues: List[LinkIssue] = []

    def check_link_status(self, links: List[Dict[str, Any]]) -> List[LinkIssue]:
        """Check status of all linked files."""
        issues = []

        for link in links:
            name = link.get("name", "")
            status = link.get("status", "")
            path = link.get("path", "")

            if status == "Not Found":
                issues.append(LinkIssue(
                    link_name=name,
                    issue_type="Missing Link",
                    detail="Linked file cannot be found",
                    file_path=path,
                    severity="error"
                ))
            elif status == "Unloaded":
                issues.append(LinkIssue(
                    link_name=name,
                    issue_type="Unloaded Link",
                    detail="Link is present but unloaded",
                    file_path=path,
                    severity="info"
                ))
            elif status == "Not Loaded":
                issues.append(LinkIssue(
                    link_name=name,
                    issue_type="Not Loaded",
                    detail="Link exists but is not loaded",
                    file_path=path,
                    severity="warning"
                ))

        self.issues.extend(issues)
        return issues

    def check_link_paths(self, links: List[Dict[str, Any]],
                         project_path: str) -> List[LinkIssue]:
        """Check link paths for best practices."""
        issues = []
        project_dir = Path(project_path).parent if project_path else None

        for link in links:
            name = link.get("name", "")
            path = link.get("path", "")
            path_type = link.get("path_type", "")  # Absolute, Relative

            # Check for absolute paths (problematic for sharing)
            if path_type == "Absolute" or (path and ":" in path and "\\" in path):
                issues.append(LinkIssue(
                    link_name=name,
                    issue_type="Absolute Path",
                    detail="Link uses absolute path which may break on other machines",
                    file_path=path,
                    severity="warning"
                ))

            # Check for paths outside project folder
            if project_dir and path:
                try:
                    link_path = Path(path)
                    if not str(link_path).startswith(str(project_dir)):
                        issues.append(LinkIssue(
                            link_name=name,
                            issue_type="External Path",
                            detail="Link is outside project folder structure",
                            file_path=path,
                            severity="info"
                        ))
                except:
                    pass

            # Check for nested too deep
            if path and path.count("\\") > 8:
                issues.append(LinkIssue(
                    link_name=name,
                    issue_type="Deep Nesting",
                    detail="Link path has excessive folder depth",
                    file_path=path,
                    severity="info"
                ))

        self.issues.extend(issues)
        return issues

    def check_link_versions(self, links: List[Dict[str, Any]],
                            current_version: str) -> List[LinkIssue]:
        """Check linked file Revit versions."""
        issues = []

        for link in links:
            name = link.get("name", "")
            path = link.get("path", "")
            version = link.get("revit_version", "")

            if version and version != current_version:
                issues.append(LinkIssue(
                    link_name=name,
                    issue_type="Version Mismatch",
                    detail=f"Link is version {version}, project is {current_version}",
                    file_path=path,
                    severity="warning"
                ))

        self.issues.extend(issues)
        return issues

    def check_duplicate_links(self, links: List[Dict[str, Any]]) -> List[LinkIssue]:
        """Check for duplicate link instances."""
        issues = []

        # Group by file path
        path_groups: Dict[str, List[Dict]] = {}
        for link in links:
            path = link.get("path", "").lower()
            if path not in path_groups:
                path_groups[path] = []
            path_groups[path].append(link)

        for path, group in path_groups.items():
            if len(group) > 1:
                # Multiple instances might be intentional, but flag if same location
                locations = [l.get("location", "") for l in group]
                if len(locations) != len(set(locations)):
                    issues.append(LinkIssue(
                        link_name=group[0].get("name", ""),
                        issue_type="Duplicate Links",
                        detail=f"Found {len(group)} instances, some at same location",
                        file_path=path,
                        severity="warning"
                    ))

        self.issues.extend(issues)
        return issues

    def check_cad_links(self, cad_links: List[Dict[str, Any]]) -> List[LinkIssue]:
        """Check CAD link management."""
        issues = []

        for link in cad_links:
            name = link.get("name", "")
            path = link.get("path", "")
            import_type = link.get("import_type", "")  # Link vs Import

            # Imported CAD (not linked) can bloat model
            if import_type == "Import":
                issues.append(LinkIssue(
                    link_name=name,
                    issue_type="Imported CAD",
                    detail="CAD is imported instead of linked (increases file size)",
                    file_path=path,
                    severity="warning"
                ))

            # Check for DWG in views (should be in drafting views only)
            current_view = link.get("current_view_only", False)
            view_type = link.get("view_type", "")

            if not current_view and view_type not in ["Drafting", "Legend"]:
                issues.append(LinkIssue(
                    link_name=name,
                    issue_type="CAD Visibility",
                    detail="CAD link visible in all views (consider current view only)",
                    file_path=path,
                    severity="info"
                ))

        self.issues.extend(issues)
        return issues

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all link issues."""
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
                    "link": i.link_name,
                    "type": i.issue_type,
                    "detail": i.detail,
                    "path": i.file_path,
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
