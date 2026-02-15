"""
Reference Validator - Checks for broken section/detail/callout references.

Uses RevitMCPBridge methods:
- getAllViews: Get all views in the project
- getViewInfo: Get details about a view
- getViewsOnSheet: Check if views are placed
- getAllSheets: Get sheet information for reference matching
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from cd_validator.core.base_validator import (
    BaseValidator,
    ValidationResult,
    ValidationSeverity,
    RevitMCPConnection,
)


class ReferenceValidator(BaseValidator):
    """
    Validates cross-references between views and sheets.

    Checks:
    - Section markers point to valid sheets
    - Detail callouts reference existing details
    - Elevation markers are properly linked
    - Plan references match actual sheet placements
    - Interior elevation markers are complete
    """

    # View types that create references
    REFERENCE_VIEW_TYPES = [
        "Section",
        "Detail",
        "Callout",
        "Elevation",
        "BuildingSection",
        "WallSection",
        "DetailSection",
    ]

    def __init__(self, connection: Optional[RevitMCPConnection] = None):
        super().__init__(connection)
        self._views: List[Dict[str, Any]] = []
        self._sheets: List[Dict[str, Any]] = []
        self._view_to_sheet_map: Dict[int, Dict[str, Any]] = {}  # viewId -> sheet info

    @property
    def name(self) -> str:
        return "Reference Validator"

    @property
    def description(self) -> str:
        return "Validates section markers, detail callouts, and cross-references"

    def _fetch_views(self) -> bool:
        """Fetch all views from Revit."""
        response = self.connection.send_request("getAllViews", {})
        if not response.get("success"):
            self.add_result(
                rule_id="REF-001",
                message=f"Failed to fetch views: {response.get('error', 'Unknown error')}",
                severity=ValidationSeverity.CRITICAL,
                suggestion="Ensure Revit is open and MCP server is running"
            )
            return False

        self._views = response.get("views", [])
        return True

    def _fetch_sheets(self) -> bool:
        """Fetch all sheets from Revit."""
        response = self.connection.send_request("getAllSheets", {})
        if not response.get("success"):
            self.add_result(
                rule_id="REF-002",
                message=f"Failed to fetch sheets: {response.get('error', 'Unknown error')}",
                severity=ValidationSeverity.CRITICAL,
                suggestion="Ensure Revit is open and MCP server is running"
            )
            return False

        self._sheets = response.get("sheets", [])
        return True

    def _build_view_sheet_map(self) -> None:
        """Build mapping of views to their sheet placements."""
        for sheet in self._sheets:
            sheet_id = sheet.get("sheetId")
            sheet_number = sheet.get("sheetNumber", "")
            sheet_name = sheet.get("sheetName", "")

            # Get viewports on this sheet
            response = self.connection.send_request("getViewsOnSheet", {"sheetId": sheet_id})
            if not response.get("success"):
                continue

            for viewport in response.get("viewports", []):
                view_id = viewport.get("viewId")
                if view_id:
                    self._view_to_sheet_map[view_id] = {
                        "sheetId": sheet_id,
                        "sheetNumber": sheet_number,
                        "sheetName": sheet_name,
                        "detailNumber": viewport.get("detailNumber", ""),
                    }

    def _check_unplaced_reference_views(self) -> None:
        """Check for section/detail views not placed on sheets."""
        for view in self._views:
            view_id = view.get("viewId")
            view_name = view.get("name", "")
            view_type = view.get("viewType", "")

            # Skip non-reference view types
            if view_type not in self.REFERENCE_VIEW_TYPES:
                continue

            # Check if view is placed on a sheet
            if view_id not in self._view_to_sheet_map:
                severity = ValidationSeverity.ERROR
                if "working" in view_name.lower() or "draft" in view_name.lower():
                    severity = ValidationSeverity.INFO

                self.add_result(
                    rule_id="REF-100",
                    message=f"{view_type} view '{view_name}' is not placed on any sheet",
                    severity=severity,
                    element_id=view_id,
                    element_type=view_type,
                    location=view_name,
                    suggestion=f"Place this {view_type.lower()} on a sheet or delete if not needed",
                    view_type=view_type
                )

    def _check_section_references(self) -> None:
        """
        Check section markers for proper sheet/detail references.

        A section marker shows where it's cut (in the parent view) and
        where to find it (sheet number/detail number). This validates
        the reference is correct.
        """
        for view in self._views:
            view_type = view.get("viewType", "")
            if view_type not in ["Section", "BuildingSection", "WallSection", "DetailSection"]:
                continue

            view_id = view.get("viewId")
            view_name = view.get("name", "")

            # Get view info for reference parameters
            response = self.connection.send_request("getViewInfo", {"viewId": view_id})
            if not response.get("success"):
                continue

            view_info = response

            # Check referencing sheet parameter
            ref_sheet = view_info.get("referencingSheet", "")
            ref_detail = view_info.get("referencingDetail", "")

            if view_id in self._view_to_sheet_map:
                placed = self._view_to_sheet_map[view_id]
                actual_sheet = placed.get("sheetNumber", "")
                actual_detail = placed.get("detailNumber", "")

                # Verify reference matches placement
                if ref_sheet and ref_sheet != actual_sheet:
                    self.add_result(
                        rule_id="REF-200",
                        message=f"Section '{view_name}' reference ({ref_sheet}) doesn't match placement ({actual_sheet})",
                        severity=ValidationSeverity.ERROR,
                        element_id=view_id,
                        element_type="Section",
                        location=view_name,
                        suggestion="Update section reference or move to correct sheet",
                        expected_sheet=ref_sheet,
                        actual_sheet=actual_sheet
                    )

    def _check_detail_callouts(self) -> None:
        """Check detail callout references."""
        for view in self._views:
            view_type = view.get("viewType", "")
            if view_type not in ["Detail", "Callout"]:
                continue

            view_id = view.get("viewId")
            view_name = view.get("name", "")

            # Get view info
            response = self.connection.send_request("getViewInfo", {"viewId": view_id})
            if not response.get("success"):
                continue

            view_info = response

            # Check if detail is placed and has proper reference
            if view_id in self._view_to_sheet_map:
                placed = self._view_to_sheet_map[view_id]

                # Check detail number
                detail_num = placed.get("detailNumber", "")
                if not detail_num or detail_num == "0":
                    self.add_result(
                        rule_id="REF-300",
                        message=f"Detail '{view_name}' on sheet {placed['sheetNumber']} has no detail number",
                        severity=ValidationSeverity.WARNING,
                        element_id=view_id,
                        element_type="Detail",
                        location=f"{placed['sheetNumber']}/{view_name}",
                        suggestion="Assign a detail number in the viewport properties"
                    )

    def _check_elevation_completeness(self) -> None:
        """
        Check that elevation sets are complete.

        Interior elevations typically come in sets (N, S, E, W or 1, 2, 3, 4).
        This checks for incomplete sets.
        """
        elevation_groups: Dict[str, List[Dict[str, Any]]] = {}

        for view in self._views:
            view_type = view.get("viewType", "")
            if view_type != "Elevation":
                continue

            view_name = view.get("name", "")

            # Try to identify elevation grouping
            # Common patterns: "Room Name - North", "123 - A", etc.
            base_match = re.match(r'^(.+?)[\s\-]+([NSEW]|North|South|East|West|\d+|[A-D])$', view_name, re.IGNORECASE)
            if base_match:
                base_name = base_match.group(1).strip()
                direction = base_match.group(2).upper()

                if base_name not in elevation_groups:
                    elevation_groups[base_name] = []
                elevation_groups[base_name].append({
                    "view": view,
                    "direction": direction
                })

        # Check for incomplete groups
        for base_name, elevations in elevation_groups.items():
            directions = {e["direction"] for e in elevations}

            # Check cardinal directions
            cardinal = {"N", "S", "E", "W", "NORTH", "SOUTH", "EAST", "WEST"}
            cardinal_found = directions & cardinal

            if cardinal_found and len(cardinal_found) < 4:
                # Normalize to simple NSEW
                simple_dirs = {d[0] if len(d) > 1 else d for d in cardinal_found}
                missing = {"N", "S", "E", "W"} - simple_dirs

                if missing:
                    self.add_result(
                        rule_id="REF-400",
                        message=f"Elevation set '{base_name}' may be incomplete (missing {', '.join(missing)})",
                        severity=ValidationSeverity.INFO,
                        location=base_name,
                        suggestion="Verify all required elevations are created",
                        found_directions=list(cardinal_found),
                        missing_directions=list(missing)
                    )

    def _check_orphaned_references(self) -> None:
        """
        Check for callout/section markers that point to deleted or renamed views.

        This is detected when a marker's target view ID doesn't exist in the project.
        """
        view_ids = {v.get("viewId") for v in self._views if v.get("viewId")}

        # Get all section/callout markers in the project
        # Note: This would require a method like "getAllSectionMarkers" or
        # checking annotations in each view. For now, we validate views exist.
        #
        # TODO: Full orphan detection requires getAllSectionMarkers method from RevitMCPBridge.
        # Currently we can only check parent view references, not section markers in views
        # pointing to deleted sections. This needs RevitMCPBridge enhancement to expose
        # section marker annotations and their target view IDs.
        for view in self._views:
            view_type = view.get("viewType", "")
            if view_type not in self.REFERENCE_VIEW_TYPES:
                continue

            view_id = view.get("viewId")
            view_name = view.get("name", "")

            # Get parent view info
            response = self.connection.send_request("getViewInfo", {"viewId": view_id})
            if not response.get("success"):
                continue

            parent_id = response.get("parentViewId")

            # Check if parent view exists (for callouts/sections)
            if parent_id and parent_id not in view_ids and parent_id != -1:
                self.add_result(
                    rule_id="REF-500",
                    message=f"View '{view_name}' references non-existent parent view (ID: {parent_id})",
                    severity=ValidationSeverity.ERROR,
                    element_id=view_id,
                    element_type=view_type,
                    location=view_name,
                    suggestion="View may need to be recreated or relinked",
                    orphan_parent_id=parent_id
                )

    def _check_similar_names(self) -> None:
        """Check for views with similar names that might cause reference confusion."""
        view_names: Dict[str, List[Dict[str, Any]]] = {}

        for view in self._views:
            view_name = view.get("name", "").lower().strip()
            if not view_name:
                continue

            # Normalize name for comparison
            normalized = re.sub(r'\s+', ' ', view_name)
            normalized = re.sub(r'[_\-]', ' ', normalized)

            if normalized not in view_names:
                view_names[normalized] = []
            view_names[normalized].append(view)

        for name, views in view_names.items():
            if len(views) > 1:
                # Check if they're different types (which is OK) or same type (potential issue)
                types = {v.get("viewType") for v in views}
                if len(types) == 1:  # All same type
                    view_type = list(types)[0]
                    actual_names = [v.get("name") for v in views]
                    ids = [v.get("viewId") for v in views]

                    self.add_result(
                        rule_id="REF-600",
                        message=f"Multiple {view_type} views with similar names: {actual_names}",
                        severity=ValidationSeverity.WARNING,
                        location=name,
                        suggestion="Rename views to be more distinct to avoid reference confusion",
                        view_ids=ids,
                        view_names=actual_names
                    )

    def validate(self) -> List[ValidationResult]:
        """Run all reference validations."""
        self.clear_results()

        # Fetch data
        if not self._fetch_views():
            return self.results

        if not self._fetch_sheets():
            return self.results

        # Build lookup map
        self._build_view_sheet_map()

        # Run validations
        self._check_unplaced_reference_views()
        self._check_section_references()
        self._check_detail_callouts()
        self._check_elevation_completeness()
        self._check_orphaned_references()
        self._check_similar_names()

        return self.results
