"""
Tests for vision_v2.py — Image/PDF → WallPlan extraction.

Tests:
- JSON parsing from code block, raw, surrounding text
- Validation: missing walls, bad offsets, unclosed exterior
- Scale detection from dimension strings
- WallPlan geometry from mock Claude response
"""

import pytest
from floor_plan_engine.vision_v2 import (
    parse_json_response,
    validate_wall_plan,
    detect_scale,
    _check_exterior_closure,
    _check_opening_references,
    _check_opening_offsets,
)
from floor_plan_engine.wall_model import Wall, Opening, RoomLabel, WallPlan


# ── parse_json_response Tests ──

class TestParseJsonResponse:
    def test_json_in_code_block(self):
        text = '''Here is the floor plan:
```json
{"metadata": {"units": "feet"}, "walls": []}
```
'''
        d = parse_json_response(text)
        assert d["metadata"]["units"] == "feet"

    def test_raw_json(self):
        text = '{"metadata": {"units": "feet"}, "walls": []}'
        d = parse_json_response(text)
        assert d["metadata"]["units"] == "feet"

    def test_json_surrounded_by_text(self):
        text = 'The floor plan data is: {"metadata": {"units": "feet"}, "walls": []} which represents the layout.'
        d = parse_json_response(text)
        assert "metadata" in d

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError):
            parse_json_response("No JSON here at all")

    def test_code_block_no_lang_tag(self):
        text = '''```
{"metadata": {"units": "feet"}, "walls": [{"id": "W1", "start": {"x": 0, "y": 0}, "end": {"x": 10, "y": 0}}]}
```'''
        d = parse_json_response(text)
        assert len(d["walls"]) == 1

    def test_full_response_with_walls(self):
        text = '''```json
{
  "metadata": {"units": "feet", "overall_width_ft": 30, "overall_depth_ft": 20},
  "walls": [
    {"id": "W1", "start": {"x": 0, "y": 0}, "end": {"x": 30, "y": 0}, "type": "exterior", "thickness_in": 8},
    {"id": "W2", "start": {"x": 30, "y": 0}, "end": {"x": 30, "y": 20}, "type": "exterior", "thickness_in": 8},
    {"id": "W3", "start": {"x": 30, "y": 20}, "end": {"x": 0, "y": 20}, "type": "exterior", "thickness_in": 8},
    {"id": "W4", "start": {"x": 0, "y": 20}, "end": {"x": 0, "y": 0}, "type": "exterior", "thickness_in": 8}
  ],
  "doors": [
    {"id": "D1", "wall_id": "W1", "offset_ft": 12.0, "width_ft": 3.0, "swing": "left", "is_entry": true}
  ],
  "rooms": [
    {"name": "Living Room", "label_position": {"x": 15, "y": 10}}
  ]
}
```'''
        d = parse_json_response(text)
        plan = WallPlan.from_dict(d)
        assert len(plan.walls) == 4
        assert len(plan.doors) == 1
        assert plan.doors[0].is_entry
        assert len(plan.rooms) == 1


# ── Validation Tests ──

class TestValidation:
    def test_valid_rectangle(self):
        """Simple rectangle passes validation."""
        plan = WallPlan(walls=[
            Wall("W1", (0, 0), (20, 0), "exterior"),
            Wall("W2", (20, 0), (20, 15), "exterior"),
            Wall("W3", (20, 15), (0, 15), "exterior"),
            Wall("W4", (0, 15), (0, 0), "exterior"),
            Wall("W5", (10, 0), (10, 15), "interior"),
        ])
        issues = validate_wall_plan(plan)
        assert len(issues) == 0

    def test_no_walls(self):
        plan = WallPlan()
        issues = validate_wall_plan(plan)
        assert any("No walls" in i for i in issues)

    def test_unclosed_exterior(self):
        """Gap in exterior walls detected."""
        plan = WallPlan(walls=[
            Wall("W1", (0, 0), (20, 0), "exterior"),
            Wall("W2", (20, 0), (20, 15), "exterior"),
            Wall("W3", (20, 15), (0, 15), "exterior"),
            # Missing W4: (0, 15) → (0, 0) — gap!
        ])
        issues = validate_wall_plan(plan)
        assert any("gap" in i.lower() for i in issues)

    def test_bad_opening_reference(self):
        """Door referencing non-existent wall caught."""
        plan = WallPlan(
            walls=[Wall("W1", (0, 0), (20, 0), "exterior")],
            doors=[Opening("D1", "W99", 5.0, 3.0, "door")],
        )
        issues = validate_wall_plan(plan)
        assert any("non-existent" in i for i in issues)

    def test_bad_offset(self):
        """Door offset exceeding wall length caught."""
        plan = WallPlan(
            walls=[
                Wall("W1", (0, 0), (10, 0), "exterior"),
                Wall("W2", (10, 0), (10, 10), "exterior"),
                Wall("W3", (10, 10), (0, 10), "exterior"),
                Wall("W4", (0, 10), (0, 0), "exterior"),
            ],
            doors=[Opening("D1", "W1", 9.0, 3.0, "door")],  # 9 + 3 = 12 > wall length 10
        )
        issues = validate_wall_plan(plan)
        assert any("exceeds" in i for i in issues)

    def test_negative_offset(self):
        plan = WallPlan(
            walls=[
                Wall("W1", (0, 0), (10, 0), "exterior"),
                Wall("W2", (10, 0), (10, 10), "exterior"),
                Wall("W3", (10, 10), (0, 10), "exterior"),
                Wall("W4", (0, 10), (0, 0), "exterior"),
            ],
            doors=[Opening("D1", "W1", -2.0, 3.0, "door")],
        )
        issues = validate_wall_plan(plan)
        assert any("negative" in i for i in issues)

    def test_interior_wall_connection(self):
        """Interior wall that doesn't connect flags a warning."""
        plan = WallPlan(walls=[
            Wall("W1", (0, 0), (20, 0), "exterior"),
            Wall("W2", (20, 0), (20, 15), "exterior"),
            Wall("W3", (20, 15), (0, 15), "exterior"),
            Wall("W4", (0, 15), (0, 0), "exterior"),
            Wall("W5", (5, 5), (5, 10), "interior"),  # floating — not connected
        ])
        issues = validate_wall_plan(plan)
        assert any("doesn't connect" in i for i in issues)


# ── Scale Detection Tests ──

class TestScaleDetection:
    def test_known_dimensions(self):
        plan = WallPlan(overall_width_ft=30, overall_depth_ft=20)
        assert detect_scale(plan) == 1.0

    def test_standard_door_width(self):
        plan = WallPlan(
            walls=[Wall("W1", (0, 0), (20, 0), "exterior")],
            doors=[Opening("D1", "W1", 5.0, 3.0, "door")],
        )
        scale = detect_scale(plan)
        assert abs(scale - 1.0) < 0.01  # 3.0 / 3.0 = 1.0

    def test_scaled_door_width(self):
        plan = WallPlan(
            walls=[Wall("W1", (0, 0), (20, 0), "exterior")],
            doors=[Opening("D1", "W1", 5.0, 1.5, "door")],  # half-size
        )
        scale = detect_scale(plan)
        assert abs(scale - 2.0) < 0.01  # 3.0 / 1.5 = 2.0
