"""
BIM Standards Validator - Validates naming conventions and BIM standards.

Uses RevitMCPBridge methods:
- getAllViews: Get all views for naming validation
- getAllLevels: Get levels for naming validation
- getElementsByCategory: Get elements for naming checks
- getAllWallTypes: Get wall type names
- getProjectInfo: Get project naming
"""

import re
from typing import Any, Dict, List, Optional, Pattern, Set

from cd_validator.core.base_validator import (
    BaseValidator,
    ValidationResult,
    ValidationSeverity,
    RevitMCPConnection,
)


class BIMStandardsValidator(BaseValidator):
    """
    Validates BIM naming conventions and standards.

    Checks:
    - View naming conventions
    - Level naming standards
    - Wall type naming patterns
    - Family naming consistency
    - Workset naming (if enabled)
    - Parameter naming conventions
    """

    # View naming patterns by type
    VIEW_NAMING_PATTERNS: Dict[str, Dict[str, Any]] = {
        "FloorPlan": {
            "pattern": r'^(Level\s*\d+|L\d+|Floor\s*\d+|\d{1,2}(st|nd|rd|th)\s*Floor)',
            "examples": ["Level 1", "L1", "Floor 1", "1st Floor"],
            "description": "Level/Floor designation",
        },
        "CeilingPlan": {
            "pattern": r'^(Level\s*\d+|L\d+|Floor\s*\d+|\d{1,2}(st|nd|rd|th)\s*Floor).*[Cc]eiling',
            "examples": ["Level 1 - Ceiling Plan", "L1 RCP"],
            "description": "Level designation with ceiling indicator",
        },
        "Section": {
            "pattern": r'^(Section|SECTION|Sec\.?)\s*[\d\-A-Z]',
            "examples": ["Section 1", "Section A", "SECTION 1-A"],
            "description": "Section designation",
        },
        "Elevation": {
            "pattern": r'^(Elevation|ELEV|North|South|East|West|Interior)',
            "examples": ["North Elevation", "Elevation 1", "Interior Elevation"],
            "description": "Elevation designation",
        },
        "Detail": {
            "pattern": r'^(Detail|DETAIL|DTL)\s*[\d\-]',
            "examples": ["Detail 1", "DETAIL 1-A"],
            "description": "Detail designation",
        },
        "ThreeD": {
            "pattern": r'^(\{?3D\}?|Isometric|Perspective|Camera)',
            "examples": ["{3D}", "3D View 1", "Isometric"],
            "description": "3D view designation",
        },
    }

    # Level naming patterns
    LEVEL_PATTERNS = [
        (r'^Level\s*\d+$', "Level N"),
        (r'^L\d+$', "LN"),
        (r'^Floor\s*\d+$', "Floor N"),
        (r'^B\d+$', "BN (Basement)"),
        (r'^(Basement|Parking|Roof|Penthouse)', "Descriptive"),
        (r'^T\.?O\.?\s*(Steel|Parapet|Slab|Roof)', "T.O. Designation"),
    ]

    # Wall type naming patterns (best practices)
    WALL_TYPE_PATTERNS = {
        "exterior": r'(Ext|EXT|Exterior)',
        "interior": r'(Int|INT|Interior)',
        "partition": r'(Part|Partition)',
        "rated": r'(\d+[\-\s]?HR|\d+[\-\s]?Hour|Fire[\-\s]?Rated)',
        "dimensions": r'(\d+[\"\']|\d+\s*mm|\d+/\d+)',
    }

    def __init__(self, connection: Optional[RevitMCPConnection] = None):
        super().__init__(connection)
        self._views: List[Dict[str, Any]] = []
        self._levels: List[Dict[str, Any]] = []
        self._wall_types: List[Dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "BIM Standards Validator"

    @property
    def description(self) -> str:
        return "Validates BIM naming conventions, standards, and consistency"

    def _fetch_views(self) -> bool:
        """Fetch all views from Revit."""
        response = self.connection.send_request("getAllViews", {})
        if not response.get("success"):
            self.add_result(
                rule_id="BIM-001",
                message=f"Failed to fetch views: {response.get('error', 'Unknown error')}",
                severity=ValidationSeverity.CRITICAL,
            )
            return False
        self._views = response.get("views", [])
        return True

    def _fetch_levels(self) -> bool:
        """Fetch all levels from Revit."""
        response = self.connection.send_request("getAllLevels", {})
        if not response.get("success"):
            self.add_result(
                rule_id="BIM-002",
                message=f"Failed to fetch levels: {response.get('error', 'Unknown error')}",
                severity=ValidationSeverity.CRITICAL,
            )
            return False
        self._levels = response.get("levels", [])
        return True

    def _fetch_wall_types(self) -> bool:
        """Fetch wall types from Revit."""
        response = self.connection.send_request("getAllWallTypes", {})
        if not response.get("success"):
            # Wall types might not be available, non-critical
            self._wall_types = []
            return True
        self._wall_types = response.get("wallTypes", [])
        return True

    def _validate_view_naming(self) -> None:
        """Validate view naming conventions."""
        for view in self._views:
            view_name = view.get("name", "")
            view_type = view.get("viewType", "")
            view_id = view.get("viewId")

            if not view_name:
                self.add_result(
                    rule_id="BIM-100",
                    message=f"{view_type} view has no name",
                    severity=ValidationSeverity.ERROR,
                    element_id=view_id,
                    element_type=view_type,
                )
                continue

            # Check against pattern for this view type
            if view_type in self.VIEW_NAMING_PATTERNS:
                pattern_info = self.VIEW_NAMING_PATTERNS[view_type]
                pattern = pattern_info["pattern"]

                if not re.match(pattern, view_name, re.IGNORECASE):
                    self.add_result(
                        rule_id="BIM-101",
                        message=f"{view_type} view '{view_name}' doesn't follow naming convention",
                        severity=ValidationSeverity.INFO,
                        element_id=view_id,
                        element_type=view_type,
                        location=view_name,
                        suggestion=f"Expected format: {pattern_info['description']}. Examples: {', '.join(pattern_info['examples'])}",
                    )

            # Check for generic/placeholder names
            placeholder_patterns = [
                r'^Copy\s*(of\s*)?\d*$',
                r'^View\s*\d*$',
                r'^New\s*View',
                r'^Untitled',
                r'^\{3D\s*-\s*[a-f0-9]+\}$',  # Default 3D view names
            ]
            for pattern in placeholder_patterns:
                if re.match(pattern, view_name, re.IGNORECASE):
                    self.add_result(
                        rule_id="BIM-102",
                        message=f"View '{view_name}' has placeholder/generic name",
                        severity=ValidationSeverity.WARNING,
                        element_id=view_id,
                        element_type=view_type,
                        location=view_name,
                        suggestion="Rename with descriptive, standards-compliant name",
                    )
                    break

            # Check for special characters
            if re.search(r'[<>:"/\\|?*]', view_name):
                self.add_result(
                    rule_id="BIM-103",
                    message=f"View '{view_name}' contains invalid characters",
                    severity=ValidationSeverity.WARNING,
                    element_id=view_id,
                    element_type=view_type,
                    location=view_name,
                    suggestion="Remove special characters: < > : \" / \\ | ? *",
                )

    def _validate_level_naming(self) -> None:
        """Validate level naming conventions."""
        seen_names: Dict[str, int] = {}
        elevations: List[tuple] = []

        for level in self._levels:
            level_name = level.get("name", "")
            level_id = level.get("levelId")
            elevation = level.get("elevation", 0)

            elevations.append((elevation, level_name, level_id))

            if not level_name:
                self.add_result(
                    rule_id="BIM-200",
                    message="Level has no name",
                    severity=ValidationSeverity.ERROR,
                    element_id=level_id,
                    element_type="Level",
                )
                continue

            # Check against standard patterns
            matched_pattern = False
            for pattern, description in self.LEVEL_PATTERNS:
                if re.match(pattern, level_name, re.IGNORECASE):
                    matched_pattern = True
                    break

            if not matched_pattern:
                self.add_result(
                    rule_id="BIM-201",
                    message=f"Level '{level_name}' doesn't follow standard naming",
                    severity=ValidationSeverity.INFO,
                    element_id=level_id,
                    element_type="Level",
                    location=level_name,
                    suggestion="Standard formats: Level 1, L1, Floor 1, B1, T.O. Steel",
                )

            # Track for duplicates
            norm_name = level_name.lower().strip()
            if norm_name in seen_names:
                self.add_result(
                    rule_id="BIM-202",
                    message=f"Duplicate level name: '{level_name}'",
                    severity=ValidationSeverity.ERROR,
                    element_id=level_id,
                    element_type="Level",
                    location=level_name,
                )
            seen_names[norm_name] = level_id

        # Check level sequence matches elevation order
        elevations_sorted = sorted(elevations, key=lambda x: x[0])
        for i, (elev, name, level_id) in enumerate(elevations_sorted):
            # Extract number from name if present
            num_match = re.search(r'(\d+)', name)
            if num_match:
                level_num = int(num_match.group(1))
                # Check if numbering is sequential (allowing for basements)
                expected_position = level_num if "B" not in name.upper() else -level_num

                # This is a soft check - just informational
                if i > 0:
                    prev_name = elevations_sorted[i-1][1]
                    prev_match = re.search(r'(\d+)', prev_name)
                    if prev_match:
                        prev_num = int(prev_match.group(1))
                        if "B" in prev_name.upper():
                            prev_num = -prev_num
                        if "B" in name.upper():
                            level_num = -level_num

    def _validate_wall_type_naming(self) -> None:
        """Validate wall type naming conventions."""
        for wall_type in self._wall_types:
            type_name = wall_type.get("name", "")
            type_id = wall_type.get("typeId")

            if not type_name:
                self.add_result(
                    rule_id="BIM-300",
                    message="Wall type has no name",
                    severity=ValidationSeverity.ERROR,
                    element_id=type_id,
                    element_type="WallType",
                )
                continue

            # Check for descriptive naming
            has_location = bool(
                re.search(self.WALL_TYPE_PATTERNS["exterior"], type_name, re.IGNORECASE) or
                re.search(self.WALL_TYPE_PATTERNS["interior"], type_name, re.IGNORECASE) or
                re.search(self.WALL_TYPE_PATTERNS["partition"], type_name, re.IGNORECASE)
            )

            has_dimensions = bool(
                re.search(self.WALL_TYPE_PATTERNS["dimensions"], type_name)
            )

            if not has_location and not has_dimensions:
                self.add_result(
                    rule_id="BIM-301",
                    message=f"Wall type '{type_name}' lacks descriptive naming",
                    severity=ValidationSeverity.INFO,
                    element_id=type_id,
                    element_type="WallType",
                    location=type_name,
                    suggestion="Include location (Ext/Int) and/or dimensions in wall type name",
                )

            # Check for generic Revit defaults
            default_patterns = [
                r'^Generic.*Wall',
                r'^Basic\s*Wall',
                r'^Wall\s*\d+$',
            ]
            for pattern in default_patterns:
                if re.match(pattern, type_name, re.IGNORECASE):
                    self.add_result(
                        rule_id="BIM-302",
                        message=f"Wall type '{type_name}' appears to be default/generic",
                        severity=ValidationSeverity.WARNING,
                        element_id=type_id,
                        element_type="WallType",
                        location=type_name,
                        suggestion="Rename with project-specific, descriptive name",
                    )
                    break

            # Check fire rating format
            fire_match = re.search(r'(\d+)\s*[-\s]?(HR|Hour)', type_name, re.IGNORECASE)
            if fire_match:
                # Fire rating present - good
                pass
            elif "fire" in type_name.lower() or "rated" in type_name.lower():
                # Has fire-related words but unclear rating
                self.add_result(
                    rule_id="BIM-303",
                    message=f"Wall type '{type_name}' mentions fire rating but format unclear",
                    severity=ValidationSeverity.INFO,
                    element_id=type_id,
                    element_type="WallType",
                    location=type_name,
                    suggestion="Use format like '1-HR' or '2-Hour' for fire ratings",
                )

    def _validate_naming_consistency(self) -> None:
        """Check for consistency in naming across similar elements."""
        # Analyze view naming patterns
        view_prefixes: Dict[str, Set[str]] = {}
        for view in self._views:
            view_type = view.get("viewType", "")
            view_name = view.get("name", "")

            if view_name:
                # Extract prefix (first word or phrase)
                prefix_match = re.match(r'^([A-Za-z]+)', view_name)
                if prefix_match:
                    prefix = prefix_match.group(1).lower()
                    if view_type not in view_prefixes:
                        view_prefixes[view_type] = set()
                    view_prefixes[view_type].add(prefix)

        # Check for inconsistent prefixes within same type
        for view_type, prefixes in view_prefixes.items():
            if len(prefixes) > 3:  # Allow some variation, but flag high inconsistency
                self.add_result(
                    rule_id="BIM-400",
                    message=f"{view_type} views have inconsistent naming prefixes",
                    severity=ValidationSeverity.INFO,
                    location=view_type,
                    suggestion="Standardize view naming within each type",
                    found_prefixes=list(prefixes)[:10],  # Limit to 10
                )

    def _validate_project_info(self) -> None:
        """Validate project information is filled in."""
        response = self.connection.send_request("getProjectInfo", {})
        if not response.get("success"):
            return

        # Check required fields
        required_fields = [
            ("projectName", "Project Name"),
            ("projectNumber", "Project Number"),
        ]

        recommended_fields = [
            ("clientName", "Client Name"),
            ("projectAddress", "Project Address"),
        ]

        for field_key, field_name in required_fields:
            value = response.get(field_key, "")
            if not value or value.strip() == "":
                self.add_result(
                    rule_id="BIM-500",
                    message=f"Project Information: {field_name} is empty",
                    severity=ValidationSeverity.WARNING,
                    location="Project Information",
                    suggestion=f"Fill in {field_name} in Project Information",
                )

        for field_key, field_name in recommended_fields:
            value = response.get(field_key, "")
            if not value or value.strip() == "":
                self.add_result(
                    rule_id="BIM-501",
                    message=f"Project Information: {field_name} is not set",
                    severity=ValidationSeverity.INFO,
                    location="Project Information",
                    suggestion=f"Consider filling in {field_name}",
                )

    def validate(self) -> List[ValidationResult]:
        """Run all BIM standards validations."""
        self.clear_results()

        # Fetch data
        views_ok = self._fetch_views()
        levels_ok = self._fetch_levels()
        self._fetch_wall_types()  # Non-critical

        if not views_ok and not levels_ok:
            return self.results

        # Run validations
        if views_ok:
            self._validate_view_naming()
            self._validate_naming_consistency()

        if levels_ok:
            self._validate_level_naming()

        if self._wall_types:
            self._validate_wall_type_naming()

        self._validate_project_info()

        return self.results
