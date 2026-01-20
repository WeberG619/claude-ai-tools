#!/usr/bin/env python3
"""
Revit Schedule Integration for Compliance Checking
===================================================
Validates Revit schedules (doors, windows, walls) against code requirements.
Integrates with RevitMCPBridge to extract schedule data and verify:
- Product approvals (NOA validation for HVHZ)
- Fire ratings
- Accessibility compliance
- Energy code compliance
- Material specifications

Works with:
- Door schedules
- Window schedules
- Wall type schedules
- Room/Area schedules
- Equipment schedules
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
import re

# Try to import NOA database for product validation
try:
    from noa_database import NOADatabase
    HAS_NOA_DB = True
except ImportError:
    HAS_NOA_DB = False


class ScheduleType(Enum):
    """Types of Revit schedules"""
    DOOR = "door"
    WINDOW = "window"
    WALL = "wall"
    ROOM = "room"
    EQUIPMENT = "equipment"
    FIXTURE = "fixture"


class ComplianceStatus(Enum):
    """Compliance check status"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "n/a"


@dataclass
class ComplianceIssue:
    """A compliance issue found during validation"""
    element_id: str
    element_mark: str
    issue_type: str
    severity: ComplianceStatus
    description: str
    code_reference: str
    recommendation: str
    sheet_reference: str = ""


@dataclass
class ScheduleValidationResult:
    """Results of schedule validation"""
    schedule_type: ScheduleType
    total_elements: int
    passed: int
    failed: int
    warnings: int
    needs_review: int
    issues: List[ComplianceIssue] = field(default_factory=list)
    validation_date: str = ""

    def __post_init__(self):
        if not self.validation_date:
            self.validation_date = datetime.now().isoformat()

    @property
    def pass_rate(self) -> float:
        if self.total_elements == 0:
            return 100.0
        return (self.passed / self.total_elements) * 100


class RevitScheduleValidator:
    """Validates Revit schedule data against code requirements"""

    def __init__(self, db_path: str = "site_intelligence.db", hvhz: bool = True):
        self.db_path = db_path
        self.hvhz = hvhz
        self.noa_db = NOADatabase() if HAS_NOA_DB else None

        # Door fire rating requirements by occupancy separation
        self.door_fire_ratings = {
            "1-hour": {"min_rating": 45, "closer_required": True, "label_required": True},
            "2-hour": {"min_rating": 90, "closer_required": True, "label_required": True},
            "3-hour": {"min_rating": 180, "closer_required": True, "label_required": True},
            "exit_enclosure": {"min_rating": 60, "closer_required": True, "self_closing": True},
            "corridor": {"min_rating": 20, "closer_required": True},
            "smoke_barrier": {"min_rating": 20, "smoke_seal": True},
        }

        # ADA door requirements
        self.ada_door_requirements = {
            "min_clear_width": 32,  # inches
            "max_force_interior": 5,  # lbs
            "max_force_fire": 15,  # lbs for fire doors
            "max_threshold": 0.5,  # inches
            "min_maneuvering_clearance": 18,  # inches on pull side
            "min_door_height": 80,  # inches
            "hardware_height_min": 34,  # inches
            "hardware_height_max": 48,  # inches
        }

        # Window requirements (HVHZ)
        self.hvhz_window_requirements = {
            "large_missile": {
                "min_design_pressure": 50,  # psf for most zones
                "impact_required": True,
                "noa_required": True,
            },
            "small_missile": {
                "min_design_pressure": 30,
                "impact_required": True,
                "noa_required": True,
            }
        }

        # Wall fire rating requirements
        self.wall_fire_ratings = {
            "occupancy_separation": {
                "A_to_B": 2,
                "A_to_M": 2,
                "A_to_R": 2,
                "B_to_M": 1,
                "B_to_S": 2,
                "H_to_any": 4,
            },
            "shaft_enclosure": 2,
            "exit_enclosure": 1,  # 2 for 4+ stories
            "corridor": 1,
            "dwelling_separation": 1,
        }

        # Room area limits by occupancy
        self.room_area_limits = {
            "A-1": {"sprinklered": 15000, "non_sprinklered": 5000},
            "A-2": {"sprinklered": 15000, "non_sprinklered": 5000},
            "A-3": {"sprinklered": 15000, "non_sprinklered": 5000},
            "B": {"sprinklered": 37500, "non_sprinklered": 12500},
            "M": {"sprinklered": 21000, "non_sprinklered": 7000},
            "S-1": {"sprinklered": 26000, "non_sprinklered": 8500},
        }

    def validate_door_schedule(
        self,
        doors: List[Dict[str, Any]],
        project_requirements: Optional[Dict[str, Any]] = None
    ) -> ScheduleValidationResult:
        """
        Validate a door schedule against code requirements.

        Args:
            doors: List of door data from Revit schedule
                   Expected keys: Mark, Width, Height, Type, Fire_Rating, Hardware, Frame, etc.
            project_requirements: Optional project-specific requirements

        Returns:
            ScheduleValidationResult with all issues found
        """
        issues = []
        passed = 0
        failed = 0
        warnings = 0
        needs_review = 0

        for door in doors:
            door_issues = self._check_door_compliance(door, project_requirements)

            if not door_issues:
                passed += 1
            else:
                for issue in door_issues:
                    issues.append(issue)
                    if issue.severity == ComplianceStatus.FAIL:
                        failed += 1
                    elif issue.severity == ComplianceStatus.WARNING:
                        warnings += 1
                    elif issue.severity == ComplianceStatus.NEEDS_REVIEW:
                        needs_review += 1

        return ScheduleValidationResult(
            schedule_type=ScheduleType.DOOR,
            total_elements=len(doors),
            passed=passed,
            failed=failed,
            warnings=warnings,
            needs_review=needs_review,
            issues=issues
        )

    def _check_door_compliance(
        self,
        door: Dict[str, Any],
        requirements: Optional[Dict[str, Any]] = None
    ) -> List[ComplianceIssue]:
        """Check a single door for compliance issues."""
        issues = []
        mark = door.get('Mark', door.get('mark', 'Unknown'))
        element_id = door.get('ElementId', door.get('id', ''))

        # Get door dimensions
        width = self._parse_dimension(door.get('Width', door.get('width', '')))
        height = self._parse_dimension(door.get('Height', door.get('height', '')))

        # Check clear width (ADA)
        if width and width < self.ada_door_requirements['min_clear_width']:
            issues.append(ComplianceIssue(
                element_id=str(element_id),
                element_mark=mark,
                issue_type="ADA Clear Width",
                severity=ComplianceStatus.FAIL,
                description=f"Door clear width {width}\" is less than required {self.ada_door_requirements['min_clear_width']}\"",
                code_reference="ADA 404.2.3 / FBC 1010.1.1",
                recommendation=f"Increase door width to minimum 36\" nominal (32\" clear)"
            ))

        # Check door height
        if height and height < self.ada_door_requirements['min_door_height']:
            issues.append(ComplianceIssue(
                element_id=str(element_id),
                element_mark=mark,
                issue_type="Door Height",
                severity=ComplianceStatus.FAIL,
                description=f"Door height {height}\" is less than required {self.ada_door_requirements['min_door_height']}\"",
                code_reference="FBC 1010.1.1",
                recommendation="Increase door height to minimum 80\""
            ))

        # Check fire rating
        fire_rating = door.get('Fire_Rating', door.get('fire_rating', door.get('FireRating', '')))
        if fire_rating:
            rating_issues = self._check_door_fire_rating(door, fire_rating)
            issues.extend(rating_issues)

        # Check hardware mounting height
        hardware_height = self._parse_dimension(
            door.get('Hardware_Height', door.get('hardware_height', ''))
        )
        if hardware_height:
            if hardware_height < self.ada_door_requirements['hardware_height_min']:
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=mark,
                    issue_type="Hardware Height",
                    severity=ComplianceStatus.FAIL,
                    description=f"Hardware height {hardware_height}\" is below ADA minimum",
                    code_reference="ADA 404.2.7",
                    recommendation=f"Mount hardware between {self.ada_door_requirements['hardware_height_min']}\" and {self.ada_door_requirements['hardware_height_max']}\" AFF"
                ))
            elif hardware_height > self.ada_door_requirements['hardware_height_max']:
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=mark,
                    issue_type="Hardware Height",
                    severity=ComplianceStatus.FAIL,
                    description=f"Hardware height {hardware_height}\" exceeds ADA maximum",
                    code_reference="ADA 404.2.7",
                    recommendation=f"Mount hardware between {self.ada_door_requirements['hardware_height_min']}\" and {self.ada_door_requirements['hardware_height_max']}\" AFF"
                ))

        # Check NOA for HVHZ exterior doors
        if self.hvhz:
            location = door.get('Location', door.get('location', ''))
            if 'exterior' in str(location).lower() or 'entry' in str(location).lower():
                noa_issues = self._check_door_noa(door)
                issues.extend(noa_issues)

        return issues

    def _check_door_fire_rating(
        self,
        door: Dict[str, Any],
        fire_rating: str
    ) -> List[ComplianceIssue]:
        """Check door fire rating requirements."""
        issues = []
        mark = door.get('Mark', door.get('mark', 'Unknown'))
        element_id = door.get('ElementId', door.get('id', ''))

        # Parse rating
        rating_minutes = self._parse_fire_rating(fire_rating)

        if rating_minutes > 0:
            # Fire-rated doors need specific features
            has_closer = door.get('Closer', door.get('closer', False))
            has_label = door.get('Label', door.get('label', False))

            if not has_closer and door.get('Type', '').lower() != 'slider':
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=mark,
                    issue_type="Fire Door Closer",
                    severity=ComplianceStatus.FAIL,
                    description=f"Fire-rated door ({fire_rating}) requires self-closing device",
                    code_reference="FBC 716.2.6.3",
                    recommendation="Add listed door closer or provide positive latching"
                ))

            if not has_label:
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=mark,
                    issue_type="Fire Door Label",
                    severity=ComplianceStatus.NEEDS_REVIEW,
                    description=f"Fire-rated door ({fire_rating}) should have fire door label",
                    code_reference="FBC 716.2.6.1",
                    recommendation="Verify door assembly has required fire test label"
                ))

            # Check frame type
            frame_type = door.get('Frame', door.get('frame', ''))
            if 'hollow' in str(frame_type).lower() and rating_minutes >= 60:
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=mark,
                    issue_type="Fire Door Frame",
                    severity=ComplianceStatus.WARNING,
                    description=f"Hollow metal frame may not meet {fire_rating} requirements",
                    code_reference="FBC 716.2",
                    recommendation="Verify frame is listed for required fire rating"
                ))

        return issues

    def _check_door_noa(self, door: Dict[str, Any]) -> List[ComplianceIssue]:
        """Check door has valid NOA for HVHZ."""
        issues = []
        mark = door.get('Mark', door.get('mark', 'Unknown'))
        element_id = door.get('ElementId', door.get('id', ''))

        noa_number = door.get('NOA', door.get('noa', door.get('Product_Approval', '')))

        if not noa_number:
            issues.append(ComplianceIssue(
                element_id=str(element_id),
                element_mark=mark,
                issue_type="HVHZ Product Approval",
                severity=ComplianceStatus.FAIL,
                description="Exterior door requires Miami-Dade NOA for HVHZ",
                code_reference="FBC 1609.1.2 / ASCE 7-22",
                recommendation="Provide NOA number or specify impact-rated assembly"
            ))
        elif self.noa_db:
            # Validate NOA
            products = self.noa_db.search_products(approval_number=str(noa_number))
            if not products:
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=mark,
                    issue_type="NOA Verification",
                    severity=ComplianceStatus.WARNING,
                    description=f"NOA {noa_number} could not be verified in database",
                    code_reference="FBC 1609.1.2",
                    recommendation="Verify NOA is valid and current with Miami-Dade BCCO"
                ))
            else:
                # Check expiration
                product = products[0]
                if product.get('expiration_date'):
                    exp_date = datetime.strptime(product['expiration_date'], '%Y-%m-%d')
                    if exp_date < datetime.now():
                        issues.append(ComplianceIssue(
                            element_id=str(element_id),
                            element_mark=mark,
                            issue_type="NOA Expired",
                            severity=ComplianceStatus.FAIL,
                            description=f"NOA {noa_number} expired on {product['expiration_date']}",
                            code_reference="FBC 1609.1.2",
                            recommendation="Update to current NOA from manufacturer"
                        ))

        return issues

    def validate_window_schedule(
        self,
        windows: List[Dict[str, Any]],
        wind_speed: int = 195,
        exposure: str = "C"
    ) -> ScheduleValidationResult:
        """
        Validate a window schedule against code requirements.

        Args:
            windows: List of window data from Revit schedule
            wind_speed: Basic wind speed (mph)
            exposure: Wind exposure category (B, C, or D)

        Returns:
            ScheduleValidationResult with all issues found
        """
        issues = []
        passed = 0
        failed = 0
        warnings = 0
        needs_review = 0

        for window in windows:
            window_issues = self._check_window_compliance(window, wind_speed, exposure)

            if not window_issues:
                passed += 1
            else:
                for issue in window_issues:
                    issues.append(issue)
                    if issue.severity == ComplianceStatus.FAIL:
                        failed += 1
                    elif issue.severity == ComplianceStatus.WARNING:
                        warnings += 1
                    elif issue.severity == ComplianceStatus.NEEDS_REVIEW:
                        needs_review += 1

        return ScheduleValidationResult(
            schedule_type=ScheduleType.WINDOW,
            total_elements=len(windows),
            passed=passed,
            failed=failed,
            warnings=warnings,
            needs_review=needs_review,
            issues=issues
        )

    def _check_window_compliance(
        self,
        window: Dict[str, Any],
        wind_speed: int,
        exposure: str
    ) -> List[ComplianceIssue]:
        """Check a single window for compliance issues."""
        issues = []
        mark = window.get('Mark', window.get('mark', 'Unknown'))
        element_id = window.get('ElementId', window.get('id', ''))

        if self.hvhz:
            # Check NOA
            noa_number = window.get('NOA', window.get('noa', window.get('Product_Approval', '')))

            if not noa_number:
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=mark,
                    issue_type="HVHZ Product Approval",
                    severity=ComplianceStatus.FAIL,
                    description="Window requires Miami-Dade NOA for HVHZ",
                    code_reference="FBC 1609.1.2",
                    recommendation="Specify impact-rated window with valid NOA"
                ))

            # Check design pressure
            design_pressure = window.get('Design_Pressure', window.get('design_pressure', 0))
            if design_pressure:
                dp = float(design_pressure) if isinstance(design_pressure, str) else design_pressure

                # Simplified DP check - real check would use building height, zone, etc.
                min_dp = self.hvhz_window_requirements['large_missile']['min_design_pressure']
                if dp < min_dp:
                    issues.append(ComplianceIssue(
                        element_id=str(element_id),
                        element_mark=mark,
                        issue_type="Design Pressure",
                        severity=ComplianceStatus.WARNING,
                        description=f"Window DP {dp} psf may be insufficient for {wind_speed} mph wind zone",
                        code_reference="FBC 1609 / ASCE 7-22",
                        recommendation=f"Verify design pressure meets calculated requirements (typical min {min_dp} psf)"
                    ))

            # Check impact rating
            impact_rating = window.get('Impact_Rating', window.get('impact_rating', ''))
            if not impact_rating or 'large' not in str(impact_rating).lower():
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=mark,
                    issue_type="Impact Protection",
                    severity=ComplianceStatus.NEEDS_REVIEW,
                    description="HVHZ requires Large Missile Impact protection within 30 ft of grade",
                    code_reference="FBC 1609.1.2.1",
                    recommendation="Verify window meets Large Missile (Zone 4) or specify approved protection"
                ))

        # Check glazing for egress windows
        is_egress = window.get('Egress', window.get('egress', False))
        if is_egress:
            width = self._parse_dimension(window.get('Width', window.get('width', '')))
            height = self._parse_dimension(window.get('Height', window.get('height', '')))
            sill_height = self._parse_dimension(window.get('Sill_Height', window.get('sill_height', '')))

            # FBC 1030.2 - Emergency Escape Requirements
            if width and width < 20:
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=mark,
                    issue_type="Egress Window Width",
                    severity=ComplianceStatus.FAIL,
                    description=f"Egress window clear width {width}\" is less than minimum 20\"",
                    code_reference="FBC 1030.2",
                    recommendation="Increase window width to provide minimum 20\" clear opening"
                ))

            if height and height < 24:
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=mark,
                    issue_type="Egress Window Height",
                    severity=ComplianceStatus.FAIL,
                    description=f"Egress window clear height {height}\" is less than minimum 24\"",
                    code_reference="FBC 1030.2",
                    recommendation="Increase window height to provide minimum 24\" clear opening"
                ))

            if sill_height and sill_height > 44:
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=mark,
                    issue_type="Egress Window Sill",
                    severity=ComplianceStatus.FAIL,
                    description=f"Egress window sill height {sill_height}\" exceeds maximum 44\" AFF",
                    code_reference="FBC 1030.2",
                    recommendation="Lower window sill to maximum 44\" above floor"
                ))

        return issues

    def validate_wall_schedule(
        self,
        walls: List[Dict[str, Any]],
        occupancy_separations: Optional[Dict[str, int]] = None
    ) -> ScheduleValidationResult:
        """
        Validate a wall type schedule against code requirements.

        Args:
            walls: List of wall type data from Revit
            occupancy_separations: Required fire ratings by wall location

        Returns:
            ScheduleValidationResult with all issues found
        """
        issues = []
        passed = 0
        failed = 0
        warnings = 0
        needs_review = 0

        for wall in walls:
            wall_issues = self._check_wall_compliance(wall, occupancy_separations)

            if not wall_issues:
                passed += 1
            else:
                for issue in wall_issues:
                    issues.append(issue)
                    if issue.severity == ComplianceStatus.FAIL:
                        failed += 1
                    elif issue.severity == ComplianceStatus.WARNING:
                        warnings += 1
                    elif issue.severity == ComplianceStatus.NEEDS_REVIEW:
                        needs_review += 1

        return ScheduleValidationResult(
            schedule_type=ScheduleType.WALL,
            total_elements=len(walls),
            passed=passed,
            failed=failed,
            warnings=warnings,
            needs_review=needs_review,
            issues=issues
        )

    def _check_wall_compliance(
        self,
        wall: Dict[str, Any],
        occupancy_separations: Optional[Dict[str, int]] = None
    ) -> List[ComplianceIssue]:
        """Check a single wall type for compliance issues."""
        issues = []
        wall_type = wall.get('Type', wall.get('type', wall.get('Name', 'Unknown')))
        element_id = wall.get('ElementId', wall.get('id', ''))

        # Check fire rating
        fire_rating = wall.get('Fire_Rating', wall.get('fire_rating', wall.get('FireRating', '')))
        function = wall.get('Function', wall.get('function', ''))

        # Check if wall function requires fire rating
        function_lower = str(function).lower()

        if 'shaft' in function_lower and not fire_rating:
            issues.append(ComplianceIssue(
                element_id=str(element_id),
                element_mark=wall_type,
                issue_type="Shaft Wall Rating",
                severity=ComplianceStatus.FAIL,
                description="Shaft wall requires fire rating",
                code_reference="FBC 713.4",
                recommendation="Specify 2-hour fire-rated shaft wall assembly"
            ))

        if 'corridor' in function_lower:
            rating_hours = self._parse_fire_rating(str(fire_rating)) / 60 if fire_rating else 0
            if rating_hours < 1:
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=wall_type,
                    issue_type="Corridor Wall Rating",
                    severity=ComplianceStatus.WARNING,
                    description="Corridor walls typically require 1-hour fire rating",
                    code_reference="FBC Table 1020.1",
                    recommendation="Verify corridor rating requirement based on occupancy"
                ))

        if 'exit' in function_lower or 'stair' in function_lower:
            rating_hours = self._parse_fire_rating(str(fire_rating)) / 60 if fire_rating else 0
            if rating_hours < 1:
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=wall_type,
                    issue_type="Exit Enclosure Rating",
                    severity=ComplianceStatus.FAIL,
                    description="Exit enclosure requires minimum 1-hour fire rating (2-hour for 4+ stories)",
                    code_reference="FBC 1023.2",
                    recommendation="Specify fire-rated exit enclosure wall assembly"
                ))

        # Check occupancy separation if provided
        if occupancy_separations:
            for separation_type, required_hours in occupancy_separations.items():
                if separation_type.lower() in function_lower:
                    rating_hours = self._parse_fire_rating(str(fire_rating)) / 60 if fire_rating else 0
                    if rating_hours < required_hours:
                        issues.append(ComplianceIssue(
                            element_id=str(element_id),
                            element_mark=wall_type,
                            issue_type="Occupancy Separation",
                            severity=ComplianceStatus.FAIL,
                            description=f"{separation_type} requires {required_hours}-hour fire rating, found {rating_hours}-hour",
                            code_reference="FBC Table 508.4",
                            recommendation=f"Upgrade wall assembly to {required_hours}-hour fire rating"
                        ))

        # Check STC rating for dwelling units
        if 'dwelling' in function_lower or 'residential' in function_lower:
            stc_rating = wall.get('STC', wall.get('stc', wall.get('STC_Rating', 0)))
            if stc_rating:
                stc = int(stc_rating) if str(stc_rating).isdigit() else 0
                if stc < 50:
                    issues.append(ComplianceIssue(
                        element_id=str(element_id),
                        element_mark=wall_type,
                        issue_type="Sound Transmission",
                        severity=ComplianceStatus.WARNING,
                        description=f"Wall STC {stc} may not meet dwelling unit separation requirement (STC 50)",
                        code_reference="FBC 1207.2",
                        recommendation="Verify wall assembly achieves minimum STC 50 for dwelling separations"
                    ))

        return issues

    def validate_room_schedule(
        self,
        rooms: List[Dict[str, Any]],
        sprinklered: bool = True,
        occupancy_group: str = "B"
    ) -> ScheduleValidationResult:
        """
        Validate room schedule for area limits and occupant loads.

        Args:
            rooms: List of room data from Revit
            sprinklered: Whether building is sprinklered
            occupancy_group: Default occupancy group

        Returns:
            ScheduleValidationResult
        """
        issues = []
        passed = 0
        failed = 0
        warnings = 0
        needs_review = 0

        for room in rooms:
            room_issues = self._check_room_compliance(room, sprinklered, occupancy_group)

            if not room_issues:
                passed += 1
            else:
                for issue in room_issues:
                    issues.append(issue)
                    if issue.severity == ComplianceStatus.FAIL:
                        failed += 1
                    elif issue.severity == ComplianceStatus.WARNING:
                        warnings += 1
                    elif issue.severity == ComplianceStatus.NEEDS_REVIEW:
                        needs_review += 1

        return ScheduleValidationResult(
            schedule_type=ScheduleType.ROOM,
            total_elements=len(rooms),
            passed=passed,
            failed=failed,
            warnings=warnings,
            needs_review=needs_review,
            issues=issues
        )

    def _check_room_compliance(
        self,
        room: Dict[str, Any],
        sprinklered: bool,
        default_occupancy: str
    ) -> List[ComplianceIssue]:
        """Check a single room for compliance issues."""
        issues = []
        room_name = room.get('Name', room.get('name', 'Unknown'))
        room_number = room.get('Number', room.get('number', room.get('Mark', '')))
        element_id = room.get('ElementId', room.get('id', ''))

        # Get room area
        area = room.get('Area', room.get('area', 0))
        if isinstance(area, str):
            # Parse area value (may include "SF" suffix)
            area_match = re.search(r'[\d.]+', area)
            area = float(area_match.group()) if area_match else 0

        # Get occupancy
        occupancy = room.get('Occupancy', room.get('occupancy', default_occupancy))

        # Check area limits for certain occupancies
        if occupancy in self.room_area_limits:
            limits = self.room_area_limits[occupancy]
            max_area = limits['sprinklered'] if sprinklered else limits['non_sprinklered']

            if area > max_area:
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=room_number,
                    issue_type="Allowable Area",
                    severity=ComplianceStatus.FAIL,
                    description=f"Room area {area:,.0f} SF exceeds allowable {max_area:,.0f} SF for {occupancy}",
                    code_reference="FBC Table 506.2",
                    recommendation="Reduce area or provide rated separations"
                ))

        # Check occupant load
        occupant_load = room.get('Occupant_Load', room.get('occupant_load', 0))
        if occupant_load:
            load = int(occupant_load) if str(occupant_load).isdigit() else 0

            # Check if multiple exits required
            if load > 49:
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=room_number,
                    issue_type="Means of Egress",
                    severity=ComplianceStatus.NEEDS_REVIEW,
                    description=f"Room with {load} occupants requires minimum 2 exits",
                    code_reference="FBC 1006.2.1",
                    recommendation="Verify room has required number of exits"
                ))

            if load > 500:
                issues.append(ComplianceIssue(
                    element_id=str(element_id),
                    element_mark=room_number,
                    issue_type="Means of Egress",
                    severity=ComplianceStatus.NEEDS_REVIEW,
                    description=f"Room with {load} occupants requires minimum 3 exits",
                    code_reference="FBC 1006.2.1",
                    recommendation="Verify room has 3 or more exits"
                ))

        return issues

    def _parse_dimension(self, dim_str: str) -> Optional[float]:
        """Parse dimension string to inches."""
        if not dim_str:
            return None

        dim_str = str(dim_str).strip()

        # Handle feet-inches format (3'-0")
        feet_match = re.search(r"(\d+)[']\s*-?\s*(\d+(?:\.\d+)?)", dim_str)
        if feet_match:
            feet = float(feet_match.group(1))
            inches = float(feet_match.group(2))
            return feet * 12 + inches

        # Handle inches only
        inch_match = re.search(r"(\d+(?:\.\d+)?)", dim_str)
        if inch_match:
            return float(inch_match.group(1))

        # Try direct number
        try:
            return float(dim_str)
        except ValueError:
            return None

    def _parse_fire_rating(self, rating_str: str) -> int:
        """Parse fire rating string to minutes."""
        if not rating_str:
            return 0

        rating_str = str(rating_str).lower().strip()

        # Handle hour format
        hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hour|hr|h)", rating_str)
        if hour_match:
            return int(float(hour_match.group(1)) * 60)

        # Handle minute format
        min_match = re.search(r"(\d+)\s*(?:min|m)", rating_str)
        if min_match:
            return int(min_match.group(1))

        # Handle just number (assume hours if >= 1, minutes if < 60)
        num_match = re.search(r"(\d+)", rating_str)
        if num_match:
            num = int(num_match.group(1))
            if num <= 4:  # Likely hours (0, 1, 2, 3, 4 hour ratings common)
                return num * 60
            return num  # Assume minutes

        return 0

    def generate_compliance_report(
        self,
        results: List[ScheduleValidationResult],
        project_name: str = "",
        project_address: str = ""
    ) -> str:
        """
        Generate a compliance report from validation results.

        Args:
            results: List of validation results
            project_name: Project name
            project_address: Project address

        Returns:
            Formatted compliance report string
        """
        report = []
        report.append("=" * 70)
        report.append("REVIT SCHEDULE COMPLIANCE REPORT")
        report.append("=" * 70)

        if project_name:
            report.append(f"Project: {project_name}")
        if project_address:
            report.append(f"Address: {project_address}")

        report.append(f"Report Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        report.append(f"HVHZ Zone: {'Yes' if self.hvhz else 'No'}")
        report.append("")

        # Summary
        total_elements = sum(r.total_elements for r in results)
        total_passed = sum(r.passed for r in results)
        total_failed = sum(r.failed for r in results)
        total_warnings = sum(r.warnings for r in results)
        total_review = sum(r.needs_review for r in results)

        report.append("-" * 50)
        report.append("SUMMARY")
        report.append("-" * 50)
        report.append(f"Total Elements Checked: {total_elements}")
        report.append(f"Passed: {total_passed}")
        report.append(f"Failed: {total_failed}")
        report.append(f"Warnings: {total_warnings}")
        report.append(f"Needs Review: {total_review}")

        if total_elements > 0:
            pass_rate = (total_passed / total_elements) * 100
            report.append(f"Pass Rate: {pass_rate:.1f}%")
        report.append("")

        # Details by schedule
        for result in results:
            if result.issues:
                report.append("-" * 50)
                report.append(f"{result.schedule_type.value.upper()} SCHEDULE ISSUES")
                report.append("-" * 50)

                for issue in result.issues:
                    severity_icon = {
                        ComplianceStatus.FAIL: "✗",
                        ComplianceStatus.WARNING: "⚠",
                        ComplianceStatus.NEEDS_REVIEW: "?"
                    }.get(issue.severity, " ")

                    report.append(f"\n[{severity_icon}] {issue.element_mark}: {issue.issue_type}")
                    report.append(f"    {issue.description}")
                    report.append(f"    Code: {issue.code_reference}")
                    report.append(f"    Fix: {issue.recommendation}")

        report.append("")
        report.append("=" * 70)
        report.append("END OF REPORT")
        report.append("=" * 70)

        return "\n".join(report)


# =============================================================================
# INTEGRATION WITH REVIT MCP
# =============================================================================

def validate_revit_schedules(
    project_name: str = "",
    hvhz: bool = True,
    doors: Optional[List[Dict]] = None,
    windows: Optional[List[Dict]] = None,
    walls: Optional[List[Dict]] = None,
    rooms: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Validate Revit schedule data and return compliance report.

    This function is designed to be called with data extracted from
    Revit via RevitMCPBridge.

    Args:
        project_name: Name of the project
        hvhz: Whether project is in HVHZ
        doors: Door schedule data
        windows: Window schedule data
        walls: Wall type schedule data
        rooms: Room schedule data

    Returns:
        Dictionary with validation results and report
    """
    validator = RevitScheduleValidator(hvhz=hvhz)
    results = []

    if doors:
        results.append(validator.validate_door_schedule(doors))

    if windows:
        results.append(validator.validate_window_schedule(windows))

    if walls:
        results.append(validator.validate_wall_schedule(walls))

    if rooms:
        results.append(validator.validate_room_schedule(rooms))

    report = validator.generate_compliance_report(results, project_name)

    return {
        "results": [
            {
                "schedule_type": r.schedule_type.value,
                "total": r.total_elements,
                "passed": r.passed,
                "failed": r.failed,
                "warnings": r.warnings,
                "needs_review": r.needs_review,
                "pass_rate": r.pass_rate
            }
            for r in results
        ],
        "total_issues": sum(len(r.issues) for r in results),
        "report": report
    }


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("REVIT SCHEDULE COMPLIANCE VALIDATOR - TEST")
    print("=" * 70)

    validator = RevitScheduleValidator(hvhz=True)

    # Test door schedule validation
    print("\n" + "-" * 50)
    print("Testing Door Schedule Validation")
    print("-" * 50)

    test_doors = [
        {
            "Mark": "D-101",
            "Width": "36",
            "Height": "84",
            "Type": "Single Flush",
            "Fire_Rating": "",
            "Location": "Interior"
        },
        {
            "Mark": "D-102",
            "Width": "30",  # Too narrow for ADA
            "Height": "80",
            "Type": "Single Panel",
            "Fire_Rating": "",
            "Location": "Interior"
        },
        {
            "Mark": "D-103",
            "Width": "36",
            "Height": "84",
            "Type": "Fire Door",
            "Fire_Rating": "90 min",
            "Closer": False,  # Missing closer
            "Location": "Stair"
        },
        {
            "Mark": "D-104",
            "Width": "36",
            "Height": "84",
            "Type": "Entry Door",
            "Fire_Rating": "",
            "Location": "Exterior Entry",
            "NOA": ""  # Missing NOA for HVHZ
        },
        {
            "Mark": "D-105",
            "Width": "36",
            "Height": "84",
            "Type": "Entry Door",
            "Fire_Rating": "",
            "Location": "Exterior Entry",
            "NOA": "NOA 21-0101.01"  # Has NOA
        }
    ]

    door_result = validator.validate_door_schedule(test_doors)

    print(f"\nDoor Schedule Results:")
    print(f"  Total Doors: {door_result.total_elements}")
    print(f"  Passed: {door_result.passed}")
    print(f"  Failed: {door_result.failed}")
    print(f"  Warnings: {door_result.warnings}")
    print(f"  Pass Rate: {door_result.pass_rate:.1f}%")

    print("\n  Issues Found:")
    for issue in door_result.issues:
        print(f"    [{issue.severity.value.upper():8}] {issue.element_mark}: {issue.issue_type}")
        print(f"              {issue.description}")

    # Test window schedule validation
    print("\n" + "-" * 50)
    print("Testing Window Schedule Validation")
    print("-" * 50)

    test_windows = [
        {
            "Mark": "W-101",
            "Width": "48",
            "Height": "60",
            "Type": "Fixed",
            "NOA": "NOA 21-0505.05",
            "Design_Pressure": "65",
            "Impact_Rating": "Large Missile"
        },
        {
            "Mark": "W-102",
            "Width": "36",
            "Height": "48",
            "Type": "Casement",
            "NOA": "",  # Missing NOA
            "Design_Pressure": "40",
            "Impact_Rating": ""
        },
        {
            "Mark": "W-103",
            "Width": "18",  # Too small for egress
            "Height": "20",  # Too small for egress
            "Type": "Egress Window",
            "Egress": True,
            "Sill_Height": "48",  # Too high
            "NOA": "NOA 21-0505.05"
        }
    ]

    window_result = validator.validate_window_schedule(test_windows, wind_speed=195)

    print(f"\nWindow Schedule Results:")
    print(f"  Total Windows: {window_result.total_elements}")
    print(f"  Passed: {window_result.passed}")
    print(f"  Failed: {window_result.failed}")
    print(f"  Pass Rate: {window_result.pass_rate:.1f}%")

    print("\n  Issues Found:")
    for issue in window_result.issues:
        print(f"    [{issue.severity.value.upper():8}] {issue.element_mark}: {issue.issue_type}")

    # Test wall schedule validation
    print("\n" + "-" * 50)
    print("Testing Wall Type Validation")
    print("-" * 50)

    test_walls = [
        {
            "Type": "Interior Partition",
            "Fire_Rating": "",
            "Function": "Interior"
        },
        {
            "Type": "Corridor Wall",
            "Fire_Rating": "20 min",  # Insufficient
            "Function": "Corridor"
        },
        {
            "Type": "Shaft Wall",
            "Fire_Rating": "",  # Missing rating
            "Function": "Shaft Enclosure"
        },
        {
            "Type": "Exit Stair Wall",
            "Fire_Rating": "2 hour",
            "Function": "Exit Enclosure"
        }
    ]

    wall_result = validator.validate_wall_schedule(test_walls)

    print(f"\nWall Type Results:")
    print(f"  Total Wall Types: {wall_result.total_elements}")
    print(f"  Passed: {wall_result.passed}")
    print(f"  Failed: {wall_result.failed}")
    print(f"  Pass Rate: {wall_result.pass_rate:.1f}%")

    print("\n  Issues Found:")
    for issue in wall_result.issues:
        print(f"    [{issue.severity.value.upper():8}] {issue.element_mark}: {issue.issue_type}")

    # Generate full report
    print("\n" + "=" * 70)
    print("FULL COMPLIANCE REPORT")
    print("=" * 70)

    report = validator.generate_compliance_report(
        [door_result, window_result, wall_result],
        project_name="Goulds Tower",
        project_address="11900 SW 216th St, Goulds, FL"
    )

    print(report)

    print("\n✓ All tests completed!")
