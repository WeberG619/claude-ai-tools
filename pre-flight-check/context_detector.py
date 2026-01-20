#!/usr/bin/env python3
"""
Context Detector
Analyzes tool calls and commands to determine operation context.
Used by pre-flight check to know what to search for.
"""

import re
import json
from typing import Optional

# Operation patterns and their associated keywords
OPERATION_PATTERNS = {
    "wall_creation": {
        "triggers": [
            r"createWall",
            r"create.*wall",
            r"place.*wall",
            r"wall.*placement",
            r"build.*wall",
        ],
        "keywords": ["wall", "walls", "DXF", "CAD", "coordinates", "placement", "create"],
        "risk_level": "high",  # Has 20+ corrections
    },
    "viewport_layout": {
        "triggers": [
            r"moveViewport",
            r"placeViewport",
            r"viewport.*layout",
            r"sheet.*layout",
            r"arrange.*viewport",
        ],
        "keywords": ["viewport", "sheet", "layout", "placement", "bounds", "position"],
        "risk_level": "medium",
    },
    "floor_plan_extraction": {
        "triggers": [
            r"extract.*floor.*plan",
            r"trace.*floor.*plan",
            r"pdf.*floor.*plan",
            r"analyze.*floor.*plan",
        ],
        "keywords": ["floor plan", "extraction", "trace", "PDF", "walls", "rooms"],
        "risk_level": "medium",
    },
    "cad_import": {
        "triggers": [
            r"import.*cad",
            r"import.*dxf",
            r"cad.*import",
            r"dxf.*import",
            r"getImportedLines",
        ],
        "keywords": ["CAD", "DXF", "import", "lines", "geometry", "layers"],
        "risk_level": "high",
    },
    "element_copy": {
        "triggers": [
            r"copy.*element",
            r"copyElementsBetweenDocuments",
            r"duplicate.*view",
            r"transfer.*view",
        ],
        "keywords": ["copy", "transfer", "duplicate", "between documents", "view"],
        "risk_level": "medium",
    },
    "door_placement": {
        "triggers": [
            r"placeDoor",
            r"create.*door",
            r"insert.*door",
            r"door.*opening",
        ],
        "keywords": ["door", "doors", "opening", "insert", "host wall"],
        "risk_level": "low",
    },
    "schedule_update": {
        "triggers": [
            r"updateSchedule",
            r"schedule.*field",
            r"parameter.*update",
        ],
        "keywords": ["schedule", "parameter", "field", "update", "value"],
        "risk_level": "low",
    },
}


def detect_operation(text: str) -> Optional[dict]:
    """
    Detect what operation is being performed from text.

    Args:
        text: Command, tool call, or description

    Returns:
        dict with operation type, keywords, and risk level
    """
    text_lower = text.lower()

    for op_name, config in OPERATION_PATTERNS.items():
        for trigger in config["triggers"]:
            if re.search(trigger, text, re.IGNORECASE):
                return {
                    "operation": op_name,
                    "keywords": config["keywords"],
                    "risk_level": config["risk_level"],
                    "matched_trigger": trigger,
                }

    return None


def should_check(text: str) -> tuple[bool, list[str]]:
    """
    Determine if pre-flight check should run and what keywords to use.

    Returns:
        (should_check, keywords)
    """
    detection = detect_operation(text)

    if detection is None:
        return False, []

    # Always check high-risk operations
    if detection["risk_level"] == "high":
        return True, detection["keywords"]

    # Check medium-risk if they match specific patterns
    if detection["risk_level"] == "medium":
        return True, detection["keywords"]

    return False, []


def get_operation_context(tool_name: str, parameters: dict) -> dict:
    """
    Build context from a tool call.

    Args:
        tool_name: Name of the MCP tool being called
        parameters: Tool parameters

    Returns:
        Context dict for pre-flight check
    """
    context = {
        "tool": tool_name,
        "parameters": parameters,
        "text": f"{tool_name} {json.dumps(parameters)}",
    }

    detection = detect_operation(context["text"])
    if detection:
        context.update(detection)

    return context


# Quick test
if __name__ == "__main__":
    test_cases = [
        "createWall with coordinates from DXF",
        "moveViewport to new position on sheet",
        "analyze floor plan from PDF",
        "just reading a file",
        "getImportedLines from CAD import",
    ]

    for test in test_cases:
        result = detect_operation(test)
        should, keywords = should_check(test)
        print(f"\n'{test}'")
        print(f"  Operation: {result}")
        print(f"  Should check: {should}, Keywords: {keywords}")
