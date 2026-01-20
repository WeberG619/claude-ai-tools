#!/usr/bin/env python3
"""
Schedule Mapper - Data Transformation for Revit Schedule Integration
=====================================================================
Maps Revit schedule column names to standardized validator fields.
Preserves element IDs for write-back operations.

Handles variations in schedule column naming across different projects
and Revit templates.

Author: BIM Ops Studio
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class FieldMapping:
    """Defines a mapping from standard field name to possible Revit column names."""
    standard_name: str
    revit_names: List[str]
    required: bool = False
    default_value: Any = None
    transform: Optional[str] = None  # 'dimension', 'boolean', 'number', 'rating'


class ScheduleFieldMapper:
    """
    Maps Revit schedule columns to validator expected fields.

    Handles:
    - Column name variations (e.g., "Mark" vs "Door Number" vs "Number")
    - Unit conversions (feet to inches)
    - Data type normalization
    - Missing/optional fields

    Example:
        mapper = ScheduleFieldMapper()
        normalized_doors = mapper.map_door_schedule(revit_door_data)
    """

    # Door schedule field mappings
    DOOR_FIELD_MAP = [
        FieldMapping("Mark", ["Mark", "Door Number", "Number", "Door Mark", "Door #", "ID", "mark"], required=True),
        FieldMapping("ElementId", ["ElementId", "Element Id", "Id", "Revit ID", "doorId", "elementId"], required=False),
        FieldMapping("Width", ["Width", "Door Width", "Rough Width", "Clear Width", "Opening Width", "width"], transform="dimension"),
        FieldMapping("Height", ["Height", "Door Height", "Rough Height", "Clear Height", "Opening Height", "height"], transform="dimension"),
        FieldMapping("Type", ["Type", "Type Name", "Door Type", "Family and Type", "Family: Type", "typeName", "familyName"]),
        FieldMapping("Fire_Rating", ["Fire Rating", "Fire_Rating", "FireRating", "Rating", "Fire Resistance"]),
        FieldMapping("Hardware", ["Hardware", "Hardware Set", "Hardware Group", "Hdwr", "HW"]),
        FieldMapping("Frame", ["Frame", "Frame Type", "Frame Material", "Door Frame"]),
        FieldMapping("Location", ["Location", "Room", "From Room", "To Room", "Room Name", "fromRoom", "toRoom"]),
        FieldMapping("Level", ["Level", "Floor", "Story", "level"]),
        FieldMapping("NOA", ["NOA", "NOA Number", "Product Approval", "Miami-Dade NOA", "NOA #"]),
        FieldMapping("Closer", ["Closer", "Door Closer", "Self-Closing", "Has Closer"], transform="boolean"),
        FieldMapping("Label", ["Label", "Fire Label", "Labeled", "UL Label"], transform="boolean"),
        FieldMapping("Comments", ["Comments", "Notes", "Description", "Remarks"]),
        FieldMapping("Material", ["Material", "Door Material", "Finish", "Face Material"]),
        FieldMapping("Glazing", ["Glazing", "Glass", "Lite", "Vision Panel"]),
        FieldMapping("Threshold", ["Threshold", "Threshold Height", "Saddle"], transform="dimension"),
        FieldMapping("Hardware_Height", ["Hardware Height", "Lever Height", "Handle Height"], transform="dimension"),
    ]

    # Window schedule field mappings
    WINDOW_FIELD_MAP = [
        FieldMapping("Mark", ["Mark", "Window Number", "Number", "Window Mark", "Window #", "ID", "mark"], required=True),
        FieldMapping("ElementId", ["ElementId", "Element Id", "Id", "Revit ID", "windowId", "elementId"], required=False),
        FieldMapping("Width", ["Width", "Window Width", "Rough Width", "Frame Width"], transform="dimension"),
        FieldMapping("Height", ["Height", "Window Height", "Rough Height", "Frame Height"], transform="dimension"),
        FieldMapping("Type", ["Type", "Type Name", "Window Type", "Family and Type", "Family: Type"]),
        FieldMapping("Sill_Height", ["Sill Height", "Sill_Height", "SillHeight", "Sill", "Head Height"], transform="dimension"),
        FieldMapping("Location", ["Location", "Room", "Room Name"]),
        FieldMapping("Level", ["Level", "Floor", "Story"]),
        FieldMapping("NOA", ["NOA", "NOA Number", "Product Approval", "Miami-Dade NOA", "NOA #"]),
        FieldMapping("Design_Pressure", ["Design Pressure", "DP", "Design_Pressure", "Wind Pressure"], transform="number"),
        FieldMapping("Impact_Rating", ["Impact Rating", "Impact_Rating", "Missile Impact", "Impact Level"]),
        FieldMapping("Egress", ["Egress", "Emergency Egress", "EERO", "Is Egress"], transform="boolean"),
        FieldMapping("U_Factor", ["U-Factor", "U Factor", "U_Factor", "Thermal"], transform="number"),
        FieldMapping("SHGC", ["SHGC", "Solar Heat Gain", "Solar Heat Gain Coefficient"], transform="number"),
        FieldMapping("Glass_Type", ["Glass Type", "Glazing Type", "Glass", "Glazing"]),
        FieldMapping("Frame_Material", ["Frame Material", "Frame", "Frame Type"]),
        FieldMapping("Comments", ["Comments", "Notes", "Description", "Remarks"]),
    ]

    # Wall schedule field mappings
    WALL_FIELD_MAP = [
        FieldMapping("Type", ["Type", "Type Name", "Wall Type", "Name", "Family and Type"], required=True),
        FieldMapping("ElementId", ["ElementId", "Element Id", "Id", "Type Id"], required=False),
        FieldMapping("Width", ["Width", "Wall Width", "Thickness", "Total Thickness"], transform="dimension"),
        FieldMapping("Fire_Rating", ["Fire Rating", "Fire_Rating", "FireRating", "Rating", "Fire Resistance"]),
        FieldMapping("Function", ["Function", "Wall Function", "Category"]),
        FieldMapping("Structure", ["Structure", "Structural Usage", "Is Structural"], transform="boolean"),
        FieldMapping("STC", ["STC", "STC Rating", "Sound Transmission", "STC_Rating"], transform="number"),
        FieldMapping("Exterior", ["Exterior", "Is Exterior", "Ext"], transform="boolean"),
        FieldMapping("Description", ["Description", "Assembly Description", "Assembly"]),
        FieldMapping("Core_Material", ["Core Material", "Core", "Primary Material"]),
        FieldMapping("Comments", ["Comments", "Notes", "Remarks"]),
    ]

    # Room schedule field mappings
    ROOM_FIELD_MAP = [
        FieldMapping("Number", ["Number", "Room Number", "Room #", "Rm#", "No.", "number"], required=True),
        FieldMapping("Name", ["Name", "Room Name", "Room", "Space Name", "name"]),
        FieldMapping("ElementId", ["ElementId", "Element Id", "Id", "Revit ID", "roomId", "elementId"], required=False),
        FieldMapping("Area", ["Area", "Room Area", "Net Area", "Gross Area"], transform="number"),
        FieldMapping("Perimeter", ["Perimeter", "Room Perimeter"], transform="number"),
        FieldMapping("Level", ["Level", "Floor", "Story"]),
        FieldMapping("Occupancy", ["Occupancy", "Occupancy Type", "Use", "Room Use"]),
        FieldMapping("Occupant_Load", ["Occupant Load", "Occupant_Load", "Occupants", "Max Occupancy"], transform="number"),
        FieldMapping("Department", ["Department", "Dept", "Zone"]),
        FieldMapping("Ceiling_Height", ["Ceiling Height", "Ceiling_Height", "Height"], transform="dimension"),
        FieldMapping("Finish_Floor", ["Floor Finish", "Finish_Floor", "Flooring"]),
        FieldMapping("Finish_Wall", ["Wall Finish", "Finish_Wall", "Wall Covering"]),
        FieldMapping("Finish_Ceiling", ["Ceiling Finish", "Finish_Ceiling", "Ceiling"]),
        FieldMapping("Comments", ["Comments", "Notes", "Description", "Remarks"]),
    ]

    def __init__(self, custom_mappings: Dict[str, List[FieldMapping]] = None):
        """
        Initialize the mapper with optional custom mappings.

        Args:
            custom_mappings: Dict with schedule type as key and list of FieldMappings
        """
        self.custom_mappings = custom_mappings or {}

    def _find_matching_field(self, column_name: str,
                              field_mappings: List[FieldMapping]) -> Optional[FieldMapping]:
        """
        Find a field mapping that matches the given column name.

        Uses fuzzy matching to handle variations in naming.
        Priority:
        1. Exact match (case-insensitive)
        2. Normalized match (ignoring special chars)
        3. Partial match for longer strings only (min 4 chars to avoid false positives)
        """
        column_lower = column_name.lower().strip()
        column_normalized = re.sub(r'[^a-z0-9]', '', column_lower)

        # First pass: exact and normalized matches only (higher confidence)
        for mapping in field_mappings:
            for revit_name in mapping.revit_names:
                revit_lower = revit_name.lower()
                revit_normalized = re.sub(r'[^a-z0-9]', '', revit_lower)

                # Exact match
                if column_lower == revit_lower:
                    return mapping

                # Normalized match (ignore special chars)
                if column_normalized == revit_normalized:
                    return mapping

        # Second pass: partial matches (lower confidence, require longer strings)
        MIN_PARTIAL_LENGTH = 4  # Require at least 4 chars to avoid "id" in "width" type matches

        for mapping in field_mappings:
            for revit_name in mapping.revit_names:
                revit_normalized = re.sub(r'[^a-z0-9]', '', revit_name.lower())

                # Only do partial matching for sufficiently long strings
                if len(revit_normalized) >= MIN_PARTIAL_LENGTH:
                    if revit_normalized in column_normalized:
                        return mapping
                if len(column_normalized) >= MIN_PARTIAL_LENGTH:
                    if column_normalized in revit_normalized:
                        return mapping

        return None

    def _transform_value(self, value: Any, transform: Optional[str]) -> Any:
        """
        Transform a value based on the specified transform type.
        """
        if value is None or value == "":
            return None

        if transform == "dimension":
            return self._parse_dimension(value)
        elif transform == "boolean":
            return self._parse_boolean(value)
        elif transform == "number":
            return self._parse_number(value)
        elif transform == "rating":
            return self._parse_fire_rating(value)

        return value

    def _parse_dimension(self, value: Any) -> Optional[float]:
        """
        Parse dimension value to inches.

        Handles formats:
        - "36" (inches)
        - "3'-0\"" (feet-inches)
        - "36 in" (with units)
        - "3 ft" (feet)
        """
        if value is None:
            return None

        value_str = str(value).strip().lower()

        # Remove units
        value_str = re.sub(r'(inches|inch|in|"|″)', '', value_str)
        value_str = re.sub(r"(feet|foot|ft|'|′)", ' ', value_str)

        # Handle feet-inches format (3 6, 3-6, etc.)
        feet_match = re.match(r'(\d+(?:\.\d+)?)\s*[-\s]?\s*(\d+(?:\.\d+)?)?', value_str.strip())
        if feet_match:
            feet = float(feet_match.group(1) or 0)
            inches = float(feet_match.group(2) or 0) if feet_match.group(2) else 0

            # If first number is small (< 10) and second exists, assume feet-inches
            if feet < 10 and inches > 0:
                return feet * 12 + inches
            # If just one number, try to determine if feet or inches
            elif inches == 0:
                # Check if original had feet indicator
                if "'" in str(value) or "ft" in str(value).lower():
                    return feet * 12
                return feet  # Assume inches

        # Try direct number
        try:
            return float(re.sub(r'[^0-9.\-]', '', value_str))
        except (ValueError, TypeError):
            return None

    def _parse_boolean(self, value: Any) -> bool:
        """Parse boolean value."""
        if value is None:
            return False

        value_str = str(value).strip().lower()
        return value_str in ('yes', 'true', '1', 'y', 'x', 'checked', '✓', '✔')

    def _parse_number(self, value: Any) -> Optional[float]:
        """Parse numeric value."""
        if value is None or value == "":
            return None

        try:
            # Remove everything except digits, decimal, minus
            cleaned = re.sub(r'[^0-9.\-]', '', str(value))
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None

    def _parse_fire_rating(self, value: Any) -> int:
        """Parse fire rating to minutes."""
        if value is None or value == "":
            return 0

        value_str = str(value).lower().strip()

        # Handle hour format
        hour_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:hour|hr|h)', value_str)
        if hour_match:
            return int(float(hour_match.group(1)) * 60)

        # Handle minute format
        min_match = re.search(r'(\d+)\s*(?:min|m)', value_str)
        if min_match:
            return int(min_match.group(1))

        # Handle just number
        num_match = re.search(r'(\d+)', value_str)
        if num_match:
            num = int(num_match.group(1))
            # If small number, assume hours
            if num <= 4:
                return num * 60
            return num

        return 0

    def map_schedule(self, revit_data: List[Dict], field_mappings: List[FieldMapping],
                     schedule_type: str = "generic") -> List[Dict]:
        """
        Map raw Revit schedule data to normalized format.

        Args:
            revit_data: List of dicts from Revit schedule
            field_mappings: Field mappings to use
            schedule_type: Type for logging

        Returns:
            List of dicts with normalized field names
        """
        if not revit_data:
            return []

        # Build column to field mapping
        sample = revit_data[0]
        column_map = {}

        for column_name in sample.keys():
            mapping = self._find_matching_field(column_name, field_mappings)
            if mapping:
                column_map[column_name] = mapping

        logger.debug(f"Mapped {len(column_map)} columns for {schedule_type} schedule")

        # Transform data
        result = []
        for row in revit_data:
            mapped_row = {}

            for column_name, value in row.items():
                if column_name in column_map:
                    mapping = column_map[column_name]
                    transformed = self._transform_value(value, mapping.transform)
                    mapped_row[mapping.standard_name] = transformed
                else:
                    # Keep unmapped columns with original names
                    mapped_row[column_name] = value

            # Add defaults for missing required fields
            for mapping in field_mappings:
                if mapping.standard_name not in mapped_row:
                    if mapping.default_value is not None:
                        mapped_row[mapping.standard_name] = mapping.default_value

            result.append(mapped_row)

        return result

    def map_door_schedule(self, revit_data: List[Dict]) -> List[Dict]:
        """Map door schedule data to normalized format."""
        mappings = self.custom_mappings.get("door", self.DOOR_FIELD_MAP)
        return self.map_schedule(revit_data, mappings, "door")

    def map_window_schedule(self, revit_data: List[Dict]) -> List[Dict]:
        """Map window schedule data to normalized format."""
        mappings = self.custom_mappings.get("window", self.WINDOW_FIELD_MAP)
        return self.map_schedule(revit_data, mappings, "window")

    def map_wall_schedule(self, revit_data: List[Dict]) -> List[Dict]:
        """Map wall schedule data to normalized format."""
        mappings = self.custom_mappings.get("wall", self.WALL_FIELD_MAP)
        return self.map_schedule(revit_data, mappings, "wall")

    def map_room_schedule(self, revit_data: List[Dict]) -> List[Dict]:
        """Map room schedule data to normalized format."""
        mappings = self.custom_mappings.get("room", self.ROOM_FIELD_MAP)
        return self.map_schedule(revit_data, mappings, "room")


class ElementIdPreserver:
    """
    Maintains element ID mapping for write-back operations.

    When extracting schedule data, stores the mapping between element marks
    and Revit element IDs so that compliance results can be written back
    to the correct elements.

    Example:
        preserver = ElementIdPreserver()
        preserver.store_mapping("door", "D-101", 12345)
        element_id = preserver.get_element_id("door", "D-101")  # Returns 12345
    """

    def __init__(self):
        """Initialize the ID preserver."""
        self._mappings: Dict[str, Dict[str, int]] = {}
        self._reverse_mappings: Dict[str, Dict[int, str]] = {}
        self._extraction_timestamp = None

    def store_mapping(self, schedule_type: str, mark: str, element_id: int):
        """
        Store a mapping between element mark and Revit element ID.

        Args:
            schedule_type: Type of schedule (door, window, wall, room)
            mark: Element mark/number
            element_id: Revit element ID
        """
        if schedule_type not in self._mappings:
            self._mappings[schedule_type] = {}
            self._reverse_mappings[schedule_type] = {}

        self._mappings[schedule_type][mark] = element_id
        self._reverse_mappings[schedule_type][element_id] = mark
        self._extraction_timestamp = datetime.now()

    def store_mappings_from_schedule(self, schedule_type: str,
                                      schedule_data: List[Dict],
                                      mark_field: str = "Mark",
                                      id_field: str = "ElementId"):
        """
        Store all mappings from schedule data.

        Args:
            schedule_type: Type of schedule
            schedule_data: List of element dicts
            mark_field: Field name containing the element mark
            id_field: Field name containing the element ID
        """
        for element in schedule_data:
            mark = element.get(mark_field)
            element_id = element.get(id_field)

            if mark and element_id:
                try:
                    self.store_mapping(schedule_type, str(mark), int(element_id))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid element ID for {mark}: {element_id}")

    def get_element_id(self, schedule_type: str, mark: str) -> Optional[int]:
        """
        Get the Revit element ID for a given mark.

        Args:
            schedule_type: Type of schedule
            mark: Element mark/number

        Returns:
            Element ID or None if not found
        """
        return self._mappings.get(schedule_type, {}).get(mark)

    def get_mark(self, schedule_type: str, element_id: int) -> Optional[str]:
        """
        Get the mark for a given element ID.

        Args:
            schedule_type: Type of schedule
            element_id: Revit element ID

        Returns:
            Element mark or None if not found
        """
        return self._reverse_mappings.get(schedule_type, {}).get(element_id)

    def get_all_mappings(self, schedule_type: str) -> Dict[str, int]:
        """
        Get all mappings for a schedule type.

        Args:
            schedule_type: Type of schedule

        Returns:
            Dict of mark -> element_id
        """
        return self._mappings.get(schedule_type, {}).copy()

    def get_all_element_ids(self, schedule_type: str) -> List[int]:
        """
        Get all element IDs for a schedule type.

        Args:
            schedule_type: Type of schedule

        Returns:
            List of element IDs
        """
        return list(self._reverse_mappings.get(schedule_type, {}).keys())

    def clear(self, schedule_type: str = None):
        """
        Clear stored mappings.

        Args:
            schedule_type: Type to clear, or None to clear all
        """
        if schedule_type:
            self._mappings.pop(schedule_type, None)
            self._reverse_mappings.pop(schedule_type, None)
        else:
            self._mappings.clear()
            self._reverse_mappings.clear()
            self._extraction_timestamp = None

    @property
    def extraction_age_seconds(self) -> Optional[float]:
        """Get the age of the extraction in seconds."""
        if self._extraction_timestamp:
            return (datetime.now() - self._extraction_timestamp).total_seconds()
        return None

    def to_dict(self) -> Dict:
        """Export mappings to dictionary for persistence."""
        return {
            "mappings": self._mappings,
            "timestamp": self._extraction_timestamp.isoformat() if self._extraction_timestamp else None
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ElementIdPreserver":
        """Create from dictionary."""
        preserver = cls()
        preserver._mappings = data.get("mappings", {})

        # Rebuild reverse mappings
        for schedule_type, mappings in preserver._mappings.items():
            preserver._reverse_mappings[schedule_type] = {v: k for k, v in mappings.items()}

        timestamp_str = data.get("timestamp")
        if timestamp_str:
            preserver._extraction_timestamp = datetime.fromisoformat(timestamp_str)

        return preserver


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("SCHEDULE MAPPER TEST")
    print("=" * 70)

    mapper = ScheduleFieldMapper()

    # Test door schedule mapping
    print("\nTesting Door Schedule Mapping:")
    print("-" * 50)

    test_doors = [
        {
            "Door Number": "D-101",
            "ElementId": "12345",
            "Door Width": "3'-0\"",
            "Door Height": "7'-0\"",
            "Type Name": "Single Flush 36x84",
            "Fire Rating": "90 min",
            "Hdwr": "HW-A",
            "Room": "Lobby",
            "NOA Number": "NOA 21-0505.05"
        },
        {
            "Door Number": "D-102",
            "ElementId": "12346",
            "Door Width": "30",
            "Door Height": "80",
            "Type Name": "Single Panel",
            "Fire Rating": "",
            "Hdwr": "HW-B",
            "Room": "Office"
        }
    ]

    mapped_doors = mapper.map_door_schedule(test_doors)

    for door in mapped_doors:
        print(f"\n  Mark: {door.get('Mark')}")
        print(f"  Width: {door.get('Width')} inches")
        print(f"  Height: {door.get('Height')} inches")
        print(f"  Type: {door.get('Type')}")
        print(f"  Fire Rating: {door.get('Fire_Rating')}")
        print(f"  NOA: {door.get('NOA')}")

    # Test element ID preserver
    print("\n" + "-" * 50)
    print("Testing Element ID Preserver:")
    print("-" * 50)

    preserver = ElementIdPreserver()
    preserver.store_mappings_from_schedule("door", mapped_doors, "Mark", "ElementId")

    print(f"\n  Stored mappings: {preserver.get_all_mappings('door')}")
    print(f"  D-101 element ID: {preserver.get_element_id('door', 'D-101')}")
    print(f"  Element 12345 mark: {preserver.get_mark('door', 12345)}")

    # Test dimension parsing
    print("\n" + "-" * 50)
    print("Testing Dimension Parsing:")
    print("-" * 50)

    test_dims = ["36", "3'-0\"", "3 ft", "36 in", "3'-6\"", "42", "3'6\""]
    for dim in test_dims:
        result = mapper._parse_dimension(dim)
        print(f"  '{dim}' -> {result} inches")

    print("\n" + "=" * 70)
    print("Test complete")
    print("=" * 70)
