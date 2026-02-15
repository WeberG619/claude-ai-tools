"""
Naming Convention Checker - Validates element naming against BIM standards.
"""
import re
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class NamingViolation:
    element_type: str
    element_name: str
    expected_pattern: str
    violation_detail: str
    severity: str = "warning"


class NamingChecker:
    """Checks naming conventions for views, sheets, families, and levels."""

    # Standard naming patterns (customizable)
    DEFAULT_PATTERNS = {
        "sheet": r"^[A-Z]\d{1,3}(\.\d{1,2})?$",  # A101, A1.01
        "view_floor_plan": r"^(Level \d+|L\d+|Floor \d+).*$",
        "view_section": r"^Section.*\d+$",
        "view_elevation": r"^(North|South|East|West|Interior).*$",
        "view_3d": r"^(\{3D\}|3D.*)$",
        "level": r"^(Level \d+|L\d+|T\.O\..*)$",
        "family_door": r"^Door_.*$",
        "family_window": r"^Window_.*$",
        "family_furniture": r"^Furn_.*$",
    }

    def __init__(self, custom_patterns: Dict[str, str] = None):
        self.patterns = {**self.DEFAULT_PATTERNS}
        if custom_patterns:
            self.patterns.update(custom_patterns)
        self.violations: List[NamingViolation] = []

    def check_sheet_names(self, sheets: List[Dict[str, Any]]) -> List[NamingViolation]:
        """Check sheet number naming conventions."""
        violations = []
        pattern = re.compile(self.patterns["sheet"])

        for sheet in sheets:
            number = sheet.get("number", "")
            if not pattern.match(number):
                violations.append(NamingViolation(
                    element_type="Sheet",
                    element_name=f"{number} - {sheet.get('name', '')}",
                    expected_pattern=self.patterns["sheet"],
                    violation_detail=f"Sheet number '{number}' doesn't match standard pattern",
                    severity="warning"
                ))

        self.violations.extend(violations)
        return violations

    def check_view_names(self, views: List[Dict[str, Any]]) -> List[NamingViolation]:
        """Check view naming conventions based on view type."""
        violations = []

        type_patterns = {
            "FloorPlan": self.patterns["view_floor_plan"],
            "CeilingPlan": self.patterns["view_floor_plan"],
            "Section": self.patterns["view_section"],
            "Elevation": self.patterns["view_elevation"],
            "ThreeD": self.patterns["view_3d"],
        }

        for view in views:
            view_type = view.get("type", "")
            view_name = view.get("name", "")

            if view_type in type_patterns:
                pattern = re.compile(type_patterns[view_type])
                if not pattern.match(view_name):
                    violations.append(NamingViolation(
                        element_type=f"View ({view_type})",
                        element_name=view_name,
                        expected_pattern=type_patterns[view_type],
                        violation_detail=f"View name doesn't follow {view_type} naming convention"
                    ))

        self.violations.extend(violations)
        return violations

    def check_level_names(self, levels: List[Dict[str, Any]]) -> List[NamingViolation]:
        """Check level naming conventions."""
        violations = []
        pattern = re.compile(self.patterns["level"])

        for level in levels:
            name = level.get("name", "")
            if not pattern.match(name):
                violations.append(NamingViolation(
                    element_type="Level",
                    element_name=name,
                    expected_pattern=self.patterns["level"],
                    violation_detail=f"Level name '{name}' doesn't match standard pattern",
                    severity="error"  # Level naming is critical
                ))

        self.violations.extend(violations)
        return violations

    def check_family_names(self, families: List[Dict[str, Any]]) -> List[NamingViolation]:
        """Check family naming conventions by category."""
        violations = []

        category_patterns = {
            "Doors": self.patterns["family_door"],
            "Windows": self.patterns["family_window"],
            "Furniture": self.patterns["family_furniture"],
        }

        for family in families:
            category = family.get("category", "")
            name = family.get("name", "")

            if category in category_patterns:
                pattern = re.compile(category_patterns[category])
                if not pattern.match(name):
                    violations.append(NamingViolation(
                        element_type=f"Family ({category})",
                        element_name=name,
                        expected_pattern=category_patterns[category],
                        violation_detail=f"Family name doesn't follow {category} naming convention"
                    ))

        self.violations.extend(violations)
        return violations

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all naming violations."""
        return {
            "total_violations": len(self.violations),
            "by_severity": {
                "error": len([v for v in self.violations if v.severity == "error"]),
                "warning": len([v for v in self.violations if v.severity == "warning"]),
            },
            "by_type": self._group_by_type(),
            "violations": [
                {
                    "type": v.element_type,
                    "name": v.element_name,
                    "issue": v.violation_detail,
                    "severity": v.severity
                }
                for v in self.violations
            ]
        }

    def _group_by_type(self) -> Dict[str, int]:
        """Group violations by element type."""
        groups = {}
        for v in self.violations:
            base_type = v.element_type.split(" (")[0]
            groups[base_type] = groups.get(base_type, 0) + 1
        return groups
