#!/usr/bin/env python3
"""
Tests for ScheduleMapper
========================
Unit tests for schedule field mapping and data transformation.

Author: BIM Ops Studio
"""

import pytest
from typing import Dict, List, Any

import sys
sys.path.insert(0, '/mnt/d/_CLAUDE-TOOLS/site-data-api')

from schedule_mapper import (
    FieldMapping,
    ScheduleFieldMapper,
    ElementIdPreserver
)


class TestFieldMapping:
    """Tests for FieldMapping dataclass."""

    def test_basic_field_mapping(self):
        """Test basic field mapping creation."""
        mapping = FieldMapping(
            standard_name="Mark",
            revit_names=["Mark", "Door Number", "Number"],
            required=True
        )
        assert mapping.standard_name == "Mark"
        assert "Door Number" in mapping.revit_names
        assert mapping.required is True

    def test_field_mapping_with_transform(self):
        """Test field mapping with transform."""
        mapping = FieldMapping(
            standard_name="Width",
            revit_names=["Width"],
            transform="dimension"
        )
        assert mapping.transform == "dimension"

    def test_field_mapping_defaults(self):
        """Test field mapping defaults."""
        mapping = FieldMapping(
            standard_name="Test",
            revit_names=["Test"]
        )
        assert mapping.required is False
        assert mapping.default_value is None
        assert mapping.transform is None


class TestScheduleFieldMapper:
    """Tests for ScheduleFieldMapper class."""

    def test_init_default(self):
        """Test mapper initializes without custom mappings."""
        mapper = ScheduleFieldMapper()
        assert mapper.custom_mappings == {}

    def test_init_custom_mappings(self):
        """Test mapper with custom mappings."""
        custom = {
            "custom": [
                FieldMapping("Field1", ["F1", "Field 1"]),
                FieldMapping("Field2", ["F2", "Field 2"])
            ]
        }
        mapper = ScheduleFieldMapper(custom_mappings=custom)
        assert "custom" in mapper.custom_mappings

    def test_class_has_field_maps(self):
        """Test mapper class has field map constants."""
        assert hasattr(ScheduleFieldMapper, 'DOOR_FIELD_MAP')
        assert hasattr(ScheduleFieldMapper, 'WINDOW_FIELD_MAP')
        assert hasattr(ScheduleFieldMapper, 'WALL_FIELD_MAP')
        assert hasattr(ScheduleFieldMapper, 'ROOM_FIELD_MAP')


class TestScheduleFieldMapperDoorMapping:
    """Tests for door schedule mapping."""

    def test_map_door_schedule_preserves_data(self):
        """Test that mapping preserves all data."""
        mapper = ScheduleFieldMapper()

        raw_data = [
            {"Mark": "D1", "Width": "36"},
            {"Mark": "D2", "Width": "32"}
        ]

        result = mapper.map_door_schedule(raw_data)

        assert len(result) == 2
        # Check that all data is preserved in some form
        assert "D1" in str(result[0].values())
        assert "D2" in str(result[1].values())

    def test_map_door_schedule_transforms_dimensions(self):
        """Test that dimensions are transformed to numbers."""
        mapper = ScheduleFieldMapper()

        raw_data = [
            {"Mark": "D1", "Width": "36"}
        ]

        result = mapper.map_door_schedule(raw_data)

        # Width should be transformed to float
        assert result[0]["Width"] == 36.0

    def test_map_door_schedule_empty(self):
        """Test mapping empty schedule."""
        mapper = ScheduleFieldMapper()

        result = mapper.map_door_schedule([])

        assert result == []

    def test_map_door_schedule_feet_inches(self):
        """Test mapping with feet-inches format."""
        mapper = ScheduleFieldMapper()

        raw_data = [
            {"Width": "3'-0\"", "Height": "7'-0\""}
        ]

        result = mapper.map_door_schedule(raw_data)

        assert result[0]["Width"] == 36.0  # 3 feet = 36 inches
        assert result[0]["Height"] == 84.0  # 7 feet = 84 inches


class TestScheduleFieldMapperWindowMapping:
    """Tests for window schedule mapping."""

    def test_map_window_schedule_standard(self):
        """Test window schedule mapping."""
        mapper = ScheduleFieldMapper()

        raw_data = [
            {"Width": "48", "Height": "60", "Type": "Casement"},
            {"Width": "36", "Height": "48", "Type": "Awning"}
        ]

        result = mapper.map_window_schedule(raw_data)

        assert len(result) == 2
        assert result[0]["Width"] == 48.0
        assert result[1]["Width"] == 36.0


class TestScheduleFieldMapperWallMapping:
    """Tests for wall schedule mapping."""

    def test_map_wall_schedule(self):
        """Test wall schedule mapping."""
        mapper = ScheduleFieldMapper()

        raw_data = [
            {"Type Name": "Exterior - 8\" CMU", "Width": "8", "Fire Rating": "2 Hour"},
        ]

        result = mapper.map_wall_schedule(raw_data)

        assert len(result) == 1
        assert result[0]["Type"] == "Exterior - 8\" CMU"


class TestScheduleFieldMapperRoomMapping:
    """Tests for room schedule mapping."""

    def test_map_room_schedule(self):
        """Test room schedule mapping."""
        mapper = ScheduleFieldMapper()

        raw_data = [
            {"Number": "101", "Name": "Living Room", "Area": "250"},
            {"Number": "102", "Name": "Kitchen", "Area": "150"}
        ]

        result = mapper.map_room_schedule(raw_data)

        assert len(result) == 2
        assert result[0]["Number"] == "101"
        assert result[0]["Name"] == "Living Room"


class TestScheduleFieldMapperDimensionParsing:
    """Tests for dimension parsing."""

    def test_parse_dimension_inches(self):
        """Test parsing inch values."""
        mapper = ScheduleFieldMapper()

        result = mapper._parse_dimension("36")
        assert result == 36.0

    def test_parse_dimension_with_quote(self):
        """Test parsing with inch mark."""
        mapper = ScheduleFieldMapper()

        result = mapper._parse_dimension("36\"")
        assert result == 36.0

    def test_parse_dimension_feet_inches(self):
        """Test parsing feet-inches format."""
        mapper = ScheduleFieldMapper()

        result = mapper._parse_dimension("3'-0\"")
        assert result == 36.0  # 3 feet = 36 inches

    def test_parse_dimension_feet_only(self):
        """Test parsing feet-only format."""
        mapper = ScheduleFieldMapper()

        result = mapper._parse_dimension("3'")
        assert result == 36.0  # 3 feet = 36 inches

    def test_parse_dimension_none(self):
        """Test parsing None value."""
        mapper = ScheduleFieldMapper()

        result = mapper._parse_dimension(None)
        assert result is None


class TestScheduleFieldMapperBooleanParsing:
    """Tests for boolean parsing."""

    def test_parse_boolean_yes(self):
        """Test parsing 'yes' value."""
        mapper = ScheduleFieldMapper()

        assert mapper._parse_boolean("yes") is True
        assert mapper._parse_boolean("Yes") is True
        assert mapper._parse_boolean("YES") is True

    def test_parse_boolean_no(self):
        """Test parsing 'no' value."""
        mapper = ScheduleFieldMapper()

        assert mapper._parse_boolean("no") is False
        assert mapper._parse_boolean("No") is False

    def test_parse_boolean_true(self):
        """Test parsing 'true' value."""
        mapper = ScheduleFieldMapper()

        assert mapper._parse_boolean("true") is True
        assert mapper._parse_boolean("True") is True

    def test_parse_boolean_none(self):
        """Test parsing None value."""
        mapper = ScheduleFieldMapper()

        assert mapper._parse_boolean(None) is False


class TestScheduleFieldMapperFireRating:
    """Tests for fire rating parsing."""

    def test_parse_fire_rating_hour(self):
        """Test parsing hour format."""
        mapper = ScheduleFieldMapper()

        assert mapper._parse_fire_rating("1 hour") == 60
        assert mapper._parse_fire_rating("2 hr") == 120

    def test_parse_fire_rating_minute(self):
        """Test parsing minute format."""
        mapper = ScheduleFieldMapper()

        assert mapper._parse_fire_rating("20 min") == 20
        assert mapper._parse_fire_rating("45 minutes") == 45

    def test_parse_fire_rating_none(self):
        """Test parsing empty/none value."""
        mapper = ScheduleFieldMapper()

        assert mapper._parse_fire_rating(None) == 0
        assert mapper._parse_fire_rating("") == 0


class TestScheduleFieldMapperFieldMatching:
    """Tests for field matching."""

    def test_find_matching_field_exact(self):
        """Test exact field match."""
        mapper = ScheduleFieldMapper()
        mapping = FieldMapping("Mark", ["Mark", "Door Number"])

        result = mapper._find_matching_field("Mark", [mapping])
        assert result is not None
        assert result.standard_name == "Mark"

    def test_find_matching_field_alias(self):
        """Test alias field match."""
        mapper = ScheduleFieldMapper()
        mapping = FieldMapping("Mark", ["Mark", "Door Number"])

        result = mapper._find_matching_field("Door Number", [mapping])
        assert result is not None
        assert result.standard_name == "Mark"

    def test_find_matching_field_case_insensitive(self):
        """Test case-insensitive match."""
        mapper = ScheduleFieldMapper()
        mapping = FieldMapping("Mark", ["Mark", "Door Number"])

        result = mapper._find_matching_field("MARK", [mapping])
        assert result is not None

    def test_find_matching_field_not_found(self):
        """Test no match found."""
        mapper = ScheduleFieldMapper()
        mapping = FieldMapping("Mark", ["Mark", "Door Number"])

        result = mapper._find_matching_field("Width", [mapping])
        assert result is None


class TestElementIdPreserver:
    """Tests for ElementIdPreserver class."""

    def test_store_mapping(self):
        """Test storing element ID mapping."""
        preserver = ElementIdPreserver()

        preserver.store_mapping("door", "D1", 12345)
        preserver.store_mapping("door", "D2", 12346)

        assert preserver.get_element_id("door", "D1") == 12345
        assert preserver.get_element_id("door", "D2") == 12346

    def test_get_element_id_not_found(self):
        """Test getting non-existent mapping."""
        preserver = ElementIdPreserver()

        result = preserver.get_element_id("door", "D99")

        assert result is None

    def test_get_mark(self):
        """Test reverse lookup - ID to mark."""
        preserver = ElementIdPreserver()

        preserver.store_mapping("door", "D1", 12345)

        assert preserver.get_mark("door", 12345) == "D1"

    def test_get_all_mappings(self):
        """Test getting all mappings for a type."""
        preserver = ElementIdPreserver()

        preserver.store_mapping("door", "D1", 12345)
        preserver.store_mapping("door", "D2", 12346)
        preserver.store_mapping("window", "W1", 22222)

        door_mappings = preserver.get_all_mappings("door")

        assert len(door_mappings) == 2
        assert door_mappings["D1"] == 12345

    def test_clear_specific_type(self):
        """Test clearing mappings for specific type."""
        preserver = ElementIdPreserver()

        preserver.store_mapping("door", "D1", 12345)
        preserver.store_mapping("window", "W1", 22222)
        preserver.clear("door")

        assert preserver.get_element_id("door", "D1") is None
        assert preserver.get_element_id("window", "W1") == 22222

    def test_clear_all_mappings(self):
        """Test clearing all mappings."""
        preserver = ElementIdPreserver()

        preserver.store_mapping("door", "D1", 12345)
        preserver.store_mapping("window", "W1", 22222)
        preserver.clear()  # No argument clears all

        assert preserver.get_element_id("door", "D1") is None
        assert preserver.get_element_id("window", "W1") is None

    def test_update_existing_mapping(self):
        """Test updating existing mapping."""
        preserver = ElementIdPreserver()

        preserver.store_mapping("door", "D1", 12345)
        preserver.store_mapping("door", "D1", 99999)

        assert preserver.get_element_id("door", "D1") == 99999

    def test_multiple_schedule_types(self):
        """Test mappings for multiple schedule types."""
        preserver = ElementIdPreserver()

        preserver.store_mapping("door", "D1", 11111)
        preserver.store_mapping("window", "W1", 22222)
        preserver.store_mapping("wall", "WALL-1", 33333)
        preserver.store_mapping("room", "101", 44444)

        assert preserver.get_element_id("door", "D1") == 11111
        assert preserver.get_element_id("window", "W1") == 22222
        assert preserver.get_element_id("wall", "WALL-1") == 33333
        assert preserver.get_element_id("room", "101") == 44444

    def test_store_mappings_from_schedule(self):
        """Test bulk storing from schedule data."""
        preserver = ElementIdPreserver()

        schedule_data = [
            {"Mark": "D1", "ElementId": "12345"},
            {"Mark": "D2", "ElementId": "12346"}
        ]

        preserver.store_mappings_from_schedule("door", schedule_data)

        assert preserver.get_element_id("door", "D1") == 12345
        assert preserver.get_element_id("door", "D2") == 12346

    def test_to_dict_from_dict(self):
        """Test serialization and deserialization."""
        preserver = ElementIdPreserver()
        preserver.store_mapping("door", "D1", 12345)

        exported = preserver.to_dict()
        restored = ElementIdPreserver.from_dict(exported)

        assert restored.get_element_id("door", "D1") == 12345


class TestFieldMappingConstants:
    """Tests for predefined field mapping constants."""

    def test_door_field_map_has_required_fields(self):
        """Test door field map has required fields."""
        field_names = [m.standard_name for m in ScheduleFieldMapper.DOOR_FIELD_MAP]

        assert "Mark" in field_names
        assert "Width" in field_names
        assert "Height" in field_names

    def test_door_field_map_mark_is_required(self):
        """Test Mark field is marked as required."""
        mark_mapping = next(m for m in ScheduleFieldMapper.DOOR_FIELD_MAP if m.standard_name == "Mark")
        assert mark_mapping.required is True

    def test_window_field_map_exists(self):
        """Test window field map exists and has fields."""
        assert len(ScheduleFieldMapper.WINDOW_FIELD_MAP) > 0

    def test_wall_field_map_exists(self):
        """Test wall field map exists and has fields."""
        assert len(ScheduleFieldMapper.WALL_FIELD_MAP) > 0

    def test_room_field_map_exists(self):
        """Test room field map exists and has fields."""
        assert len(ScheduleFieldMapper.ROOM_FIELD_MAP) > 0


# =============================================================================
# RUN TESTS
# =============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
