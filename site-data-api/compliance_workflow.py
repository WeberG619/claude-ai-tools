#!/usr/bin/env python3
"""
Compliance Workflow - Orchestration Engine for Revit Compliance Checking
=========================================================================
Orchestrates the full compliance checking workflow:
1. Extract schedules from Revit
2. Map and transform data
3. Validate against code requirements
4. Match NOA products
5. Generate reports
6. Write results back to Revit

Author: BIM Ops Studio
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

# Import local modules
try:
    from revit_mcp_client import RevitMCPClient, MCPResponse
    from schedule_mapper import ScheduleFieldMapper, ElementIdPreserver
    from revit_schedule_integration import RevitScheduleValidator, ScheduleValidationResult, ComplianceIssue, ComplianceStatus
    from noa_database import NOADatabase
except ImportError as e:
    logging.warning(f"Import error: {e}. Some features may not be available.")

# Configure logging
logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Status of the compliance workflow."""
    NOT_STARTED = "not_started"
    EXTRACTING = "extracting"
    MAPPING = "mapping"
    VALIDATING = "validating"
    GENERATING_REPORT = "generating_report"
    WRITING_BACK = "writing_back"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExtractedSchedules:
    """Container for extracted schedule data."""
    doors: List[Dict] = field(default_factory=list)
    windows: List[Dict] = field(default_factory=list)
    walls: List[Dict] = field(default_factory=list)
    rooms: List[Dict] = field(default_factory=list)
    extraction_time: str = ""
    project_name: str = ""
    project_address: str = ""


@dataclass
class ValidationResults:
    """Container for validation results."""
    door_result: Optional[ScheduleValidationResult] = None
    window_result: Optional[ScheduleValidationResult] = None
    wall_result: Optional[ScheduleValidationResult] = None
    room_result: Optional[ScheduleValidationResult] = None
    validation_time: str = ""


@dataclass
class WriteBackSummary:
    """Summary of parameter write-back operations."""
    total_elements: int = 0
    successful_writes: int = 0
    failed_writes: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class ComplianceReport:
    """Complete compliance report."""
    project_name: str
    project_address: str
    hvhz: bool
    schedules: ExtractedSchedules
    results: ValidationResults
    write_back: Optional[WriteBackSummary]
    report_text: str
    generated_at: str
    total_elements: int = 0
    total_passed: int = 0
    total_failed: int = 0
    total_warnings: int = 0
    pass_rate: float = 0.0


class RevitComplianceWorkflow:
    """
    Orchestrates the full compliance checking workflow.

    Connects RevitMCPBridge with the Python compliance validation system
    to provide one-click compliance checking from live Revit models.

    Example:
        workflow = RevitComplianceWorkflow()
        report = workflow.run_full_compliance_check(
            project_info={"name": "Goulds Tower", "hvhz": True},
            check_doors=True,
            check_windows=True,
            write_back_results=True
        )
    """

    # Default schedule names in Revit
    DEFAULT_SCHEDULE_NAMES = {
        "door": ["Door Schedule", "Doors", "DOOR SCHEDULE"],
        "window": ["Window Schedule", "Windows", "WINDOW SCHEDULE"],
        "wall": ["Wall Schedule", "Wall Types", "WALL SCHEDULE", "Wall Type Schedule"],
        "room": ["Room Schedule", "Rooms", "ROOM SCHEDULE", "Room Finish Schedule"]
    }

    def __init__(
        self,
        mcp_client: RevitMCPClient = None,
        validator: RevitScheduleValidator = None,
        noa_db: NOADatabase = None,
        hvhz: bool = True
    ):
        """
        Initialize the workflow.

        Args:
            mcp_client: RevitMCPClient instance (creates new if None)
            validator: RevitScheduleValidator instance (creates new if None)
            noa_db: NOADatabase instance (creates new if None)
            hvhz: Whether to apply HVHZ requirements
        """
        self.mcp_client = mcp_client or RevitMCPClient()
        self.validator = validator or RevitScheduleValidator(hvhz=hvhz)
        self.noa_db = noa_db or NOADatabase()
        self.hvhz = hvhz

        self.mapper = ScheduleFieldMapper()
        self.id_preserver = ElementIdPreserver()

        self.status = WorkflowStatus.NOT_STARTED
        self._progress_callback = None

    def set_progress_callback(self, callback):
        """
        Set a callback for progress updates.

        Args:
            callback: Function(status: str, progress: float, message: str)
        """
        self._progress_callback = callback

    def _report_progress(self, status: str, progress: float, message: str):
        """Report progress to callback if set."""
        self.status = WorkflowStatus(status) if status in [s.value for s in WorkflowStatus] else WorkflowStatus.NOT_STARTED
        if self._progress_callback:
            self._progress_callback(status, progress, message)
        logger.info(f"[{status}] {progress:.0%}: {message}")

    def run_full_compliance_check(
        self,
        project_info: Dict[str, Any] = None,
        check_doors: bool = True,
        check_windows: bool = True,
        check_walls: bool = True,
        check_rooms: bool = True,
        write_back_results: bool = False,
        schedule_names: Dict[str, str] = None
    ) -> ComplianceReport:
        """
        Run the full compliance checking workflow.

        Args:
            project_info: Dict with project name, address, hvhz flag
            check_doors: Whether to check door schedule
            check_windows: Whether to check window schedule
            check_walls: Whether to check wall schedule
            check_rooms: Whether to check room schedule
            write_back_results: Whether to write compliance status back to Revit
            schedule_names: Custom schedule names (dict with door, window, wall, room keys)

        Returns:
            ComplianceReport with all results
        """
        project_info = project_info or {}
        schedule_names = schedule_names or {}

        try:
            # 1. Connect to Revit
            self._report_progress("extracting", 0.0, "Connecting to Revit...")
            if not self.mcp_client.is_connected:
                if not self.mcp_client.connect():
                    raise ConnectionError(f"Failed to connect to Revit: {self.mcp_client.last_error}")

            # Get project info from Revit if not provided
            if not project_info.get("name"):
                revit_info = self.mcp_client.get_project_info()
                if revit_info.success:
                    # Handle nested response format: data.result contains actual project info
                    info_data = revit_info.data.get("result", revit_info.data)
                    project_info["name"] = info_data.get("name", info_data.get("title", "Unknown Project"))
                    project_info["address"] = info_data.get("address", "")

            # 2. Extract schedules
            self._report_progress("extracting", 0.1, "Extracting schedules from Revit...")
            schedules = self.extract_schedules(
                check_doors=check_doors,
                check_windows=check_windows,
                check_walls=check_walls,
                check_rooms=check_rooms,
                schedule_names=schedule_names
            )
            schedules.project_name = project_info.get("name", "")
            schedules.project_address = project_info.get("address", "")

            # 3. Validate schedules
            self._report_progress("validating", 0.4, "Validating against code requirements...")
            results = self.validate_all(schedules)

            # 4. Generate report
            self._report_progress("generating_report", 0.7, "Generating compliance report...")
            report_text = self.validator.generate_compliance_report(
                [r for r in [results.door_result, results.window_result,
                           results.wall_result, results.room_result] if r],
                project_name=schedules.project_name,
                project_address=schedules.project_address
            )

            # 5. Write back results (optional)
            write_back = None
            if write_back_results:
                self._report_progress("writing_back", 0.85, "Writing results back to Revit...")
                write_back = self.write_back_results(results)

            # 6. Build final report
            self._report_progress("completed", 1.0, "Compliance check complete")

            # Calculate totals
            all_results = [results.door_result, results.window_result,
                          results.wall_result, results.room_result]
            all_results = [r for r in all_results if r]

            total_elements = sum(r.total_elements for r in all_results)
            total_passed = sum(r.passed for r in all_results)
            total_failed = sum(r.failed for r in all_results)
            total_warnings = sum(r.warnings for r in all_results)
            pass_rate = (total_passed / total_elements * 100) if total_elements > 0 else 100.0

            return ComplianceReport(
                project_name=schedules.project_name,
                project_address=schedules.project_address,
                hvhz=self.hvhz,
                schedules=schedules,
                results=results,
                write_back=write_back,
                report_text=report_text,
                generated_at=datetime.now().isoformat(),
                total_elements=total_elements,
                total_passed=total_passed,
                total_failed=total_failed,
                total_warnings=total_warnings,
                pass_rate=pass_rate
            )

        except Exception as e:
            self._report_progress("failed", 0.0, f"Workflow failed: {e}")
            raise

    def extract_schedules(
        self,
        check_doors: bool = True,
        check_windows: bool = True,
        check_walls: bool = True,
        check_rooms: bool = True,
        schedule_names: Dict[str, str] = None
    ) -> ExtractedSchedules:
        """
        Extract schedules from Revit.

        Args:
            check_doors: Extract door schedule
            check_windows: Extract window schedule
            check_walls: Extract wall schedule
            check_rooms: Extract room schedule
            schedule_names: Custom schedule names

        Returns:
            ExtractedSchedules with all data
        """
        schedule_names = schedule_names or {}
        schedules = ExtractedSchedules(extraction_time=datetime.now().isoformat())

        # Extract doors
        if check_doors:
            door_names = [schedule_names.get("door")] if schedule_names.get("door") else self.DEFAULT_SCHEDULE_NAMES["door"]
            schedules.doors = self._extract_schedule("door", door_names)
            self.id_preserver.store_mappings_from_schedule("door", schedules.doors)

        # Extract windows
        if check_windows:
            window_names = [schedule_names.get("window")] if schedule_names.get("window") else self.DEFAULT_SCHEDULE_NAMES["window"]
            schedules.windows = self._extract_schedule("window", window_names)
            self.id_preserver.store_mappings_from_schedule("window", schedules.windows)

        # Extract walls
        if check_walls:
            wall_names = [schedule_names.get("wall")] if schedule_names.get("wall") else self.DEFAULT_SCHEDULE_NAMES["wall"]
            schedules.walls = self._extract_schedule("wall", wall_names)
            self.id_preserver.store_mappings_from_schedule("wall", schedules.walls, mark_field="Type")

        # Extract rooms
        if check_rooms:
            room_names = [schedule_names.get("room")] if schedule_names.get("room") else self.DEFAULT_SCHEDULE_NAMES["room"]
            schedules.rooms = self._extract_schedule("room", room_names)
            self.id_preserver.store_mappings_from_schedule("room", schedules.rooms, mark_field="Number")

        return schedules

    def _extract_schedule(self, schedule_type: str, possible_names: List[str]) -> List[Dict]:
        """
        Extract element data using direct API methods (preferred) or schedule parsing (fallback).

        Args:
            schedule_type: Type of schedule (door, window, wall, room)
            possible_names: List of possible schedule names to try (for fallback)

        Returns:
            List of mapped schedule data
        """
        raw_data = []

        # Try direct API methods first (more reliable than parsing schedules)
        try:
            if schedule_type == "door":
                response = self.mcp_client.get_all_doors()
                if response.success:
                    raw_data = response.data.get("doors", [])
                    logger.info(f"Extracted {len(raw_data)} doors via getDoors API")
            elif schedule_type == "window":
                response = self.mcp_client.get_all_windows()
                if response.success:
                    raw_data = response.data.get("windows", [])
                    logger.info(f"Extracted {len(raw_data)} windows via getWindows API")
            elif schedule_type == "room":
                response = self.mcp_client.get_all_rooms()
                if response.success:
                    raw_data = response.data.get("rooms", [])
                    logger.info(f"Extracted {len(raw_data)} rooms via getRooms API")
        except Exception as e:
            logger.debug(f"Direct API extraction failed for {schedule_type}: {e}")

        # Fallback to schedule parsing if direct API failed
        if not raw_data:
            for name in possible_names:
                if name is None:
                    continue

                try:
                    if schedule_type == "door":
                        raw_data = self.mcp_client.get_door_schedule(name)
                    elif schedule_type == "window":
                        raw_data = self.mcp_client.get_window_schedule(name)
                    elif schedule_type == "wall":
                        raw_data = self.mcp_client.get_wall_schedule(name)
                    elif schedule_type == "room":
                        raw_data = self.mcp_client.get_room_schedule(name)
                    else:
                        response = self.mcp_client.get_schedule_data(name)
                        raw_data = self.mcp_client._parse_schedule_to_dicts(response.data) if response.success else []

                    if raw_data:
                        logger.info(f"Extracted {len(raw_data)} {schedule_type}s from schedule '{name}'")
                        break

                except Exception as e:
                    logger.debug(f"Failed to extract {schedule_type} schedule '{name}': {e}")
                    continue

        if not raw_data:
            logger.warning(f"No {schedule_type} data found")
            return []

        # Map to normalized format
        if schedule_type == "door":
            return self.mapper.map_door_schedule(raw_data)
        elif schedule_type == "window":
            return self.mapper.map_window_schedule(raw_data)
        elif schedule_type == "wall":
            return self.mapper.map_wall_schedule(raw_data)
        elif schedule_type == "room":
            return self.mapper.map_room_schedule(raw_data)
        else:
            return raw_data

    def validate_all(self, schedules: ExtractedSchedules) -> ValidationResults:
        """
        Validate all extracted schedules.

        Args:
            schedules: ExtractedSchedules to validate

        Returns:
            ValidationResults with all results
        """
        results = ValidationResults(validation_time=datetime.now().isoformat())

        if schedules.doors:
            logger.info(f"Validating {len(schedules.doors)} doors...")
            results.door_result = self.validator.validate_door_schedule(schedules.doors)

        if schedules.windows:
            logger.info(f"Validating {len(schedules.windows)} windows...")
            results.window_result = self.validator.validate_window_schedule(schedules.windows)

        if schedules.walls:
            logger.info(f"Validating {len(schedules.walls)} wall types...")
            results.wall_result = self.validator.validate_wall_schedule(schedules.walls)

        if schedules.rooms:
            logger.info(f"Validating {len(schedules.rooms)} rooms...")
            results.room_result = self.validator.validate_room_schedule(schedules.rooms)

        return results

    def write_back_results(self, results: ValidationResults) -> WriteBackSummary:
        """
        Write compliance results back to Revit elements.

        Args:
            results: ValidationResults to write back

        Returns:
            WriteBackSummary with write-back statistics
        """
        summary = WriteBackSummary()

        all_results = [
            ("door", results.door_result),
            ("window", results.window_result),
            ("wall", results.wall_result),
            ("room", results.room_result)
        ]

        for schedule_type, validation_result in all_results:
            if validation_result is None:
                continue

            # Build updates for each element
            updates = []
            mark_field = "Type" if schedule_type == "wall" else ("Number" if schedule_type == "room" else "Mark")

            # Group issues by element
            issues_by_element = {}
            for issue in validation_result.issues:
                mark = issue.element_mark
                if mark not in issues_by_element:
                    issues_by_element[mark] = []
                issues_by_element[mark].append(issue)

            # Create update for each element
            for mark, issues in issues_by_element.items():
                element_id = self.id_preserver.get_element_id(schedule_type, mark)
                if element_id is None:
                    summary.skipped += 1
                    continue

                summary.total_elements += 1

                # Determine overall status for element
                has_fail = any(i.severity == ComplianceStatus.FAIL for i in issues)
                has_warning = any(i.severity == ComplianceStatus.WARNING for i in issues)

                status = "FAIL" if has_fail else ("WARNING" if has_warning else "NEEDS REVIEW")

                # Combine issue descriptions
                notes = "; ".join(f"{i.issue_type}: {i.description}" for i in issues[:3])
                if len(issues) > 3:
                    notes += f"; +{len(issues) - 3} more issues"

                # Write compliance info to Comments parameter (built-in, always available)
                # Format: "COMPLIANCE: [STATUS] - [NOTES] - [DATE]"
                comment_value = f"COMPLIANCE: {status} - {notes[:400]} - {datetime.now().strftime('%Y-%m-%d')}"

                response = self.mcp_client.set_parameter_value(element_id, "Comments", comment_value)
                if response.success:
                    summary.successful_writes += 1
                else:
                    summary.failed_writes += 1
                    if len(summary.errors) < 5:  # Limit error messages
                        summary.errors.append(f"{schedule_type} {mark}: {response.error}")

        # Also mark passed elements
        # (Optional: could add "PASS" status to elements without issues)

        return summary


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def run_compliance_check(
    project_name: str = "",
    hvhz: bool = True,
    check_doors: bool = True,
    check_windows: bool = True,
    check_walls: bool = True,
    check_rooms: bool = True,
    write_back: bool = False
) -> ComplianceReport:
    """
    Convenience function to run compliance check.

    Args:
        project_name: Project name (auto-detected if empty)
        hvhz: Whether to apply HVHZ requirements
        check_doors: Check door schedule
        check_windows: Check window schedule
        check_walls: Check wall schedule
        check_rooms: Check room schedule
        write_back: Write results back to Revit

    Returns:
        ComplianceReport
    """
    workflow = RevitComplianceWorkflow(hvhz=hvhz)
    return workflow.run_full_compliance_check(
        project_info={"name": project_name, "hvhz": hvhz},
        check_doors=check_doors,
        check_windows=check_windows,
        check_walls=check_walls,
        check_rooms=check_rooms,
        write_back_results=write_back
    )


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("COMPLIANCE WORKFLOW TEST")
    print("=" * 70)

    # Test with mock data (no Revit connection)
    print("\nTesting workflow with mock data...")

    # Create mock schedules
    mock_schedules = ExtractedSchedules(
        project_name="Goulds Tower",
        project_address="11900 SW 216th St, Goulds, FL",
        extraction_time=datetime.now().isoformat(),
        doors=[
            {"Mark": "D-101", "Width": 36, "Height": 84, "Location": "Interior"},
            {"Mark": "D-102", "Width": 30, "Height": 80, "Location": "Interior"},  # Too narrow
            {"Mark": "D-103", "Width": 36, "Height": 84, "Fire_Rating": "90 min", "Closer": False, "Location": "Stair"},
            {"Mark": "D-104", "Width": 36, "Height": 84, "Location": "Exterior Entry"},  # Missing NOA
        ],
        windows=[
            {"Mark": "W-101", "Width": 48, "Height": 60, "NOA": "NOA 21-0505.05", "Design_Pressure": 65, "Impact_Rating": "Large Missile"},
            {"Mark": "W-102", "Width": 36, "Height": 48},  # Missing NOA
        ]
    )

    # Create validator and run validation
    validator = RevitScheduleValidator(hvhz=True)

    print("\n" + "-" * 50)
    print("Validating Door Schedule")
    print("-" * 50)

    door_result = validator.validate_door_schedule(mock_schedules.doors)
    print(f"  Total: {door_result.total_elements}")
    print(f"  Passed: {door_result.passed}")
    print(f"  Failed: {door_result.failed}")
    print(f"  Warnings: {door_result.warnings}")
    print(f"  Pass Rate: {door_result.pass_rate:.1f}%")

    print("\n  Issues:")
    for issue in door_result.issues:
        print(f"    [{issue.severity.value.upper():8}] {issue.element_mark}: {issue.issue_type}")
        print(f"              {issue.description}")

    print("\n" + "-" * 50)
    print("Validating Window Schedule")
    print("-" * 50)

    window_result = validator.validate_window_schedule(mock_schedules.windows)
    print(f"  Total: {window_result.total_elements}")
    print(f"  Passed: {window_result.passed}")
    print(f"  Failed: {window_result.failed}")

    print("\n  Issues:")
    for issue in window_result.issues:
        print(f"    [{issue.severity.value.upper():8}] {issue.element_mark}: {issue.issue_type}")

    # Generate report
    print("\n" + "-" * 50)
    print("Generating Compliance Report")
    print("-" * 50)

    report_text = validator.generate_compliance_report(
        [door_result, window_result],
        project_name=mock_schedules.project_name,
        project_address=mock_schedules.project_address
    )

    print(report_text)

    print("\n" + "=" * 70)
    print("Test complete")
    print("=" * 70)
