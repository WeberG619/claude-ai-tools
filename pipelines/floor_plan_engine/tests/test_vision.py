"""Tests for the v3 vision/image extraction pipeline."""

import pytest
import sys
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/pipelines")

from floor_plan_engine.vision import parse_response, generate_prompt, _parse_json_response
from floor_plan_engine.builder import FloorPlanBuilder


class TestJsonParsing:

    def test_parse_code_block(self):
        text = '```json\n{"name": "Test", "rooms": []}\n```'
        result = _parse_json_response(text)
        assert result["name"] == "Test"

    def test_parse_raw_json(self):
        text = '{"name": "Raw", "rooms": []}'
        result = _parse_json_response(text)
        assert result["name"] == "Raw"

    def test_parse_with_surrounding_text(self):
        text = 'Here is the plan:\n```json\n{"name": "Plan", "rooms": []}\n```\nDone.'
        result = _parse_json_response(text)
        assert result["name"] == "Plan"

    def test_invalid_json_raises(self):
        with pytest.raises((ValueError, Exception)):
            _parse_json_response("not json at all")


class TestParseResponse:

    def test_full_response(self):
        response = '''```json
{
    "name": "Test House",
    "footprint": {"width": 30, "height": 20},
    "rooms": [
        {"name": "Living", "type": "living_room", "x": 0, "y": 0, "w": 15, "h": 12},
        {"name": "Kitchen", "type": "kitchen", "x": 15, "y": 0, "w": 10, "h": 12}
    ],
    "doors": [
        {"x": 15, "y": 6, "room_a": "Living", "room_b": "Kitchen"}
    ],
    "windows": [
        {"x": 7, "y": 0, "room_name": "Living"}
    ],
    "open_connections": []
}
```'''
        builder = parse_response(response)
        assert isinstance(builder, FloorPlanBuilder)
        plan = builder.build()
        assert len(plan.rooms) == 2
        assert len(plan.doors) == 1
        assert len(plan.windows) == 1


class TestPromptGeneration:

    def test_prompt_has_instructions(self):
        prompt = generate_prompt("test.png")
        assert "coordinate system" in prompt
        assert "living_room" in prompt
        assert "JSON" in prompt

    def test_prompt_has_room_types(self):
        prompt = generate_prompt("test.png")
        for rt in ["kitchen", "bedroom", "bathroom", "hallway", "garage"]:
            assert rt in prompt
