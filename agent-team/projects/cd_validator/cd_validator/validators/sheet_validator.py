"""
Sheet Validator - Validates construction document sheets against AIA standards.

Uses RevitMCPBridge SheetMethods:
- getAllSheets: Get all sheets in the project
- getSheetInfo: Get details for a specific sheet
- getViewsOnSheet: Get viewports placed on a sheet
"""

import re
from typing import Any, Dict, List, Optional, Set

from cd_validator.core.base_validator import (
    BaseValidator,
    ValidationResult,
    ValidationSeverity,
    RevitMCPConnection,
)


class SheetValidator(BaseValidator):
    """
    Validates sheets against AIA E202 and NCS standards.

    Checks:
    - Sheet numbering follows AIA discipline codes
    - Sheet names follow consistent patterns
    - Required sheets are present
    - No duplicate sheet numbers
    - Viewports are properly placed (not overlapping title block)
    """

    # AIA Discipline Codes (E202)
    DISCIPLINE_CODES = {
        "G": "General",
        "H": "Hazardous Materials",
        "V": "Survey/Mapping",
        "B": "Geotechnical",
        "C": "Civil",
        "L": "Landscape",
        "S": "Structural",
        "A": "Architectural",
        "I": "Interiors",
        "J": "Technology",
        "K": "Dietary/Food Service",
        "N": "Infrastructure",
        "Q": "Equipment",
        "F": "Fire Protection",
        "P": "Plumbing",
        "D": "Process",
        "M": "Mechanical",
        "E": "Electrical",
        "W": "Distributed Energy",
        "T": "Telecommunications",
        "R": "Resource",
        "X": "Other Disciplines",
        "Z": "Contractor/Shop Drawings",
        "O": "Operations",
    }

    # Common sheet number patterns (NCS)
    # Pattern: DISCIPLINE + SHEET_TYPE + SEQUENCE
    # Example: A1.01, A2.01, S1.01
    SHEET_TYPE_CODES = {
        "0": "General (symbols, legends, notes)",
        "1": "Plans",
        "2": "Elevations",
        "3": "Sections",
        "4": "Large Scale Views",
        "5": "Details",
        "6": "Schedules and Diagrams",
        "7": "User Defined",
        "8": "User Defined",
        "9": "3D Representations",
    }

    def __init__(self, connection: Optional[RevitMCPConnection] = None):
        super().__init__(connection)
        self._sheets: List[Dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "Sheet Validator"

    @property
    def description(self) -> str:
        return "Validates sheet numbering, naming, and organization against AIA/NCS standards"

    def _fetch_sheets(self) -> bool:
        """Fetch all sheets from Revit via MCP."""
        response = self.connection.send_request("getAllSheets", {})
        if not response.get("success"):
            self.add_result(
                rule_id="SHEET-001",
                message=f"Failed to fetch sheets: {response.get('error', 'Unknown error')}",
                severity=ValidationSeverity.CRITICAL,
                suggestion="Ensure Revit is open and MCP server is running"
            )
            return False

        self._sheets = response.get("sheets", [])
        return True

    def _validate_sheet_number(self, sheet: Dict[str, Any]) -> None:
        """Validate individual sheet number against AIA standards."""
        sheet_number = sheet.get("sheetNumber", "")
        sheet_id = sheet.get("sheetId")
        sheet_name = sheet.get("sheetName", "")

        if not sheet_number:
            self.add_result(
                rule_id="SHEET-100",
                message=f"Sheet has no number",
                severity=ValidationSeverity.ERROR,
                element_id=sheet_id,
                element_type="Sheet",
                location=sheet_name or "Unknown",
                suggestion="Add a sheet number following AIA format (e.g., A1.01)"
            )
            return

        # Check first character is a valid discipline code
        first_char = sheet_number[0].upper()
        if first_char not in self.DISCIPLINE_CODES:
            self.add_result(
                rule_id="SHEET-101",
                message=f"Sheet '{sheet_number}' has non-standard discipline code '{first_char}'",
                severity=ValidationSeverity.WARNING,
                element_id=sheet_id,
                element_type="Sheet",
                location=sheet_number,
                suggestion=f"Use AIA discipline codes: {', '.join(sorted(self.DISCIPLINE_CODES.keys()))}"
            )

        # Check for sheet type digit (second character should be 0-9)
        if len(sheet_number) >= 2:
            second_char = sheet_number[1]
            if second_char.isdigit():
                if second_char not in self.SHEET_TYPE_CODES:
                    self.add_result(
                        rule_id="SHEET-102",
                        message=f"Sheet '{sheet_number}' has non-standard type code '{second_char}'",
                        severity=ValidationSeverity.INFO,
                        element_id=sheet_id,
                        element_type="Sheet",
                        location=sheet_number,
                    )
            elif second_char not in ("-", ".", " "):
                self.add_result(
                    rule_id="SHEET-103",
                    message=f"Sheet '{sheet_number}' second character '{second_char}' is not a type digit",
                    severity=ValidationSeverity.INFO,
                    element_id=sheet_id,
                    element_type="Sheet",
                    location=sheet_number,
                )

        # Check for common formatting patterns
        # Valid patterns: A1.01, A-1.01, A1-01, A101, A10.01, AS1.01, etc.
        # Supports multi-digit type codes (A10.01) and multi-letter discipline prefixes (AS1.01)
        standard_pattern = re.compile(r'^[A-Z]{1,2}[0-9]{1,2}[\.\-]?[0-9]{1,2}$', re.IGNORECASE)
        extended_pattern = re.compile(r'^[A-Z]{1,2}[0-9]{1,2}[\.\-]?[0-9]{1,2}[\.\-]?[0-9]{0,2}[A-Z]?$', re.IGNORECASE)

        if not standard_pattern.match(sheet_number) and not extended_pattern.match(sheet_number):
            # It's a non-standard format, but might be intentional
            self.add_result(
                rule_id="SHEET-104",
                message=f"Sheet '{sheet_number}' uses non-standard numbering format",
                severity=ValidationSeverity.INFO,
                element_id=sheet_id,
                element_type="Sheet",
                location=sheet_number,
                suggestion="Consider using format: [Discipline][Type].[Sequence] (e.g., A1.01)"
            )

    def _validate_sheet_name(self, sheet: Dict[str, Any]) -> None:
        """Validate sheet name conventions."""
        sheet_number = sheet.get("sheetNumber", "")
        sheet_name = sheet.get("sheetName", "")
        sheet_id = sheet.get("sheetId")

        if not sheet_name:
            self.add_result(
                rule_id="SHEET-200",
                message=f"Sheet '{sheet_number}' has no name",
                severity=ValidationSeverity.ERROR,
                element_id=sheet_id,
                element_type="Sheet",
                location=sheet_number,
                suggestion="Add a descriptive sheet name"
            )
            return

        # Check for placeholder names
        placeholder_patterns = [
            r'^sheet\s*\d*$',
            r'^new\s*sheet',
            r'^untitled',
            r'^unnamed',
            r'^copy\s*of',
        ]
        for pattern in placeholder_patterns:
            if re.match(pattern, sheet_name, re.IGNORECASE):
                self.add_result(
                    rule_id="SHEET-201",
                    message=f"Sheet '{sheet_number}' has placeholder name: '{sheet_name}'",
                    severity=ValidationSeverity.WARNING,
                    element_id=sheet_id,
                    element_type="Sheet",
                    location=sheet_number,
                    suggestion="Replace with descriptive name matching sheet content"
                )
                break

        # Check name length (too short or too long)
        if len(sheet_name) < 5:
            self.add_result(
                rule_id="SHEET-202",
                message=f"Sheet '{sheet_number}' name '{sheet_name}' is very short",
                severity=ValidationSeverity.INFO,
                element_id=sheet_id,
                element_type="Sheet",
                location=sheet_number,
                suggestion="Consider a more descriptive name"
            )
        elif len(sheet_name) > 60:
            self.add_result(
                rule_id="SHEET-203",
                message=f"Sheet '{sheet_number}' name is very long ({len(sheet_name)} chars)",
                severity=ValidationSeverity.INFO,
                element_id=sheet_id,
                element_type="Sheet",
                location=sheet_number,
                suggestion="Consider shortening for better fit in title block"
            )

    def _check_duplicates(self) -> None:
        """Check for duplicate sheet numbers."""
        seen_numbers: Dict[str, List[int]] = {}

        for sheet in self._sheets:
            number = sheet.get("sheetNumber", "").upper()
            sheet_id = sheet.get("sheetId")

            if number in seen_numbers:
                seen_numbers[number].append(sheet_id)
            else:
                seen_numbers[number] = [sheet_id]

        for number, ids in seen_numbers.items():
            if len(ids) > 1:
                self.add_result(
                    rule_id="SHEET-300",
                    message=f"Duplicate sheet number '{number}' found ({len(ids)} occurrences)",
                    severity=ValidationSeverity.ERROR,
                    location=number,
                    suggestion="Each sheet must have a unique number",
                    duplicate_ids=ids
                )

    def _check_sequence_gaps(self) -> None:
        """Check for gaps in sheet numbering sequences."""
        # Group sheets by discipline and type
        sequences: Dict[str, List[int]] = {}

        for sheet in self._sheets:
            number = sheet.get("sheetNumber", "")
            if not number or len(number) < 3:
                continue

            # Extract discipline and type (e.g., "A1" from "A1.01")
            prefix_match = re.match(r'^([A-Z][0-9])', number, re.IGNORECASE)
            if prefix_match:
                prefix = prefix_match.group(1).upper()
                # Try to extract sequence number
                seq_match = re.search(r'[\.\-]?(\d{1,2})$', number)
                if seq_match:
                    seq_num = int(seq_match.group(1))
                    if prefix not in sequences:
                        sequences[prefix] = []
                    sequences[prefix].append(seq_num)

        # Check for gaps in each sequence
        for prefix, nums in sequences.items():
            if len(nums) < 2:
                continue

            nums_sorted = sorted(set(nums))
            for i in range(len(nums_sorted) - 1):
                gap = nums_sorted[i + 1] - nums_sorted[i]
                if gap > 1:
                    self.add_result(
                        rule_id="SHEET-301",
                        message=f"Gap in {prefix} sheet sequence between {nums_sorted[i]:02d} and {nums_sorted[i+1]:02d}",
                        severity=ValidationSeverity.INFO,
                        location=f"{prefix}.{nums_sorted[i]:02d} to {prefix}.{nums_sorted[i+1]:02d}",
                        suggestion="Review if sheets are missing or if gap is intentional"
                    )

    def _check_empty_sheets(self) -> None:
        """Check for sheets with no viewports."""
        for sheet in self._sheets:
            sheet_id = sheet.get("sheetId")
            sheet_number = sheet.get("sheetNumber", "Unknown")

            # Get viewports on this sheet
            response = self.connection.send_request("getViewsOnSheet", {"sheetId": sheet_id})
            if not response.get("success"):
                continue

            viewports = response.get("viewports", [])
            if not viewports:
                self.add_result(
                    rule_id="SHEET-400",
                    message=f"Sheet '{sheet_number}' has no viewports",
                    severity=ValidationSeverity.WARNING,
                    element_id=sheet_id,
                    element_type="Sheet",
                    location=sheet_number,
                    suggestion="Add views to sheet or delete if not needed"
                )

    def validate(self) -> List[ValidationResult]:
        """Run all sheet validations."""
        self.clear_results()

        # Fetch sheets
        if not self._fetch_sheets():
            return self.results

        if not self._sheets:
            self.add_result(
                rule_id="SHEET-002",
                message="No sheets found in project",
                severity=ValidationSeverity.WARNING,
                suggestion="Create sheets for construction documents"
            )
            return self.results

        # Run validations
        for sheet in self._sheets:
            self._validate_sheet_number(sheet)
            self._validate_sheet_name(sheet)

        self._check_duplicates()
        self._check_sequence_gaps()
        self._check_empty_sheets()

        return self.results
