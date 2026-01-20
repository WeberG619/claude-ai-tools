#!/usr/bin/env python3
"""
Correction-Compiled Rule Engine
Deterministic validation rules extracted from past corrections.
These rules catch errors BEFORE they happen.

Bootstrap set: Rules 1-4 (API/Parameter Checks)
- Source: Memory IDs 459, 234, 190, 407
"""

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable


class Severity(Enum):
    ERROR = "error"      # Block the operation
    WARN = "warn"        # Allow but warn
    INFO = "info"        # Just log


@dataclass
class Rule:
    """A compiled correction rule."""
    id: str
    source_memory_id: int
    name: str
    description: str
    severity: Severity
    trigger: Callable[[str, dict], bool]  # (tool_name, params) -> should_check
    check: Callable[[str, dict], tuple[bool, str]]  # (tool_name, params) -> (passed, message)


@dataclass
class RuleResult:
    """Result of running a rule check."""
    rule_id: str
    rule_name: str
    passed: bool
    severity: Severity
    message: str
    source_memory_id: int


# =============================================================================
# RULE DEFINITIONS (Compiled from Corrections)
# =============================================================================

def rule_001_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: Any tool name containing 'revit' (case-insensitive)."""
    return "revit" in tool_name.lower()


def rule_001_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 001: Pipe name must include "Bridge"
    Source: Memory ID 459

    The actual pipe names are `RevitMCPBridge2026` and `RevitMCPBridge2025`.
    Using abbreviated names like `RevitMCP2026` will fail to connect.
    """
    # Check if the tool name has the correct format
    if "revit" in tool_name.lower():
        # Must contain "bridge" (case insensitive)
        if "bridge" not in tool_name.lower():
            return False, f"Tool name '{tool_name}' missing 'Bridge'. Use 'RevitMCPBridge2025' or 'RevitMCPBridge2026', not 'RevitMCP20XX'"
    return True, ""


def rule_002_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: Any MCP call (tool name starts with mcp__)."""
    return tool_name.startswith("mcp__")


def rule_002_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 002: Use 'params' not 'parameters' in MCP calls
    Source: Memory ID 234

    The MCPServer.cs code parses: var parameters = request["params"] as JObject
    Using "parameters" instead of "params" causes null reference errors.
    """
    # Check if the raw JSON has "parameters" key instead of "params"
    # This check happens at the params level - if someone constructs bad JSON
    # The params dict we receive should already be parsed correctly,
    # but we can check if there's a nested "parameters" that looks like it should be "params"

    if "parameters" in params and isinstance(params["parameters"], dict):
        # Someone may have wrapped params incorrectly
        inner = params["parameters"]
        # Check if inner looks like actual MCP params (has method-specific keys)
        mcp_param_keys = ["viewId", "elementId", "startPoint", "endPoint", "sheetId", "levelId"]
        if any(key in inner for key in mcp_param_keys):
            return False, "Detected 'parameters' key that should be 'params'. MCP expects {\"method\":\"...\", \"params\":{...}}, not 'parameters'"

    return True, ""


def rule_003_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: createWall or batchCreateWalls method."""
    tool_lower = tool_name.lower()
    return "createwall" in tool_lower or "wall" in tool_lower


def rule_003_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 003: createWall startPoint/endPoint must be [x,y,z] arrays
    Source: Memory ID 190, 174

    CORRECT: {"startPoint": [10, 20, 0], "endPoint": [50, 20, 0]}
    WRONG: {"startX": 0, "startY": 0, "endX": 35, "endY": 0}
    """
    errors = []

    # Check startPoint format
    if "startPoint" in params:
        sp = params["startPoint"]
        if not isinstance(sp, list) or len(sp) != 3:
            errors.append(f"startPoint must be [x,y,z] array, got: {type(sp).__name__}")
    elif any(k in params for k in ["startX", "startY"]):
        errors.append("Use 'startPoint': [x,y,z] array, not separate startX/startY params")

    # Check endPoint format
    if "endPoint" in params:
        ep = params["endPoint"]
        if not isinstance(ep, list) or len(ep) != 3:
            errors.append(f"endPoint must be [x,y,z] array, got: {type(ep).__name__}")
    elif any(k in params for k in ["endX", "endY"]):
        errors.append("Use 'endPoint': [x,y,z] array, not separate endX/endY params")

    # Check levelId is integer, not string
    if "level" in params and isinstance(params["level"], str):
        errors.append("Use 'levelId' (integer) not 'level' (string). Get ID from getLevels response")

    if errors:
        return False, "; ".join(errors)
    return True, ""


def rule_004_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: moveViewport or viewport positioning."""
    tool_lower = tool_name.lower()
    return "viewport" in tool_lower and ("move" in tool_lower or "position" in tool_lower or "location" in tool_lower)


def rule_004_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 004: moveViewport newLocation must be [x, y] array
    Source: Memory ID 407

    CORRECT: {"viewportId": 123, "newLocation": [1.5, 0.8]}
    WRONG: {"viewportId": 123, "x": 1.5, "y": 0.8}

    Also: Use removeViewport, not removeViewportFromSheet
    """
    errors = []

    # Check newLocation format
    if "newLocation" in params:
        loc = params["newLocation"]
        if not isinstance(loc, list) or len(loc) < 2:
            errors.append(f"newLocation must be [x,y] array, got: {type(loc).__name__}")
    elif "x" in params and "y" in params and "viewportId" in params:
        errors.append("Use 'newLocation': [x,y] array, not separate x/y params")

    if errors:
        return False, "; ".join(errors)
    return True, ""


# -----------------------------------------------------------------------------
# RULES 005-009: Wall Geometry Checks
# -----------------------------------------------------------------------------

def rule_005_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: CAD to wall operations."""
    tool_lower = tool_name.lower()
    return "cad" in tool_lower and "wall" in tool_lower


def rule_005_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 005: CAD walls must come from parallel line pairs
    Source: Memory ID 448, 427

    Walls in CAD are represented by TWO parallel lines (inner/outer face).
    Single lines are NOT walls. Must detect pairs first.
    """
    # Check if processing single lines vs line pairs
    if "lines" in params and isinstance(params["lines"], list):
        # If we have lines but no indication of pairing
        if "paired" not in params and "pairs" not in params:
            return False, "CAD walls must be from parallel line PAIRS (inner/outer face), not single lines. Detect pairs first with 4-12 inch spacing."
    return True, ""


def rule_006_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: Wall creation from CAD/DXF."""
    tool_lower = tool_name.lower()
    return ("cad" in tool_lower or "dxf" in tool_lower) and "wall" in tool_lower


def rule_006_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 006: Only place walls where actual CAD lines exist
    Source: Memory ID 449, 422

    NEVER invent or assume walls. No line = no wall.
    """
    # Check for flags indicating assumed/invented walls
    if params.get("assumeConnections") or params.get("fillGaps"):
        return False, "Don't assume or invent walls. Only place where actual CAD lines exist. No line = no wall."
    return True, ""


def rule_007_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: Wall creation with door-related context."""
    tool_lower = tool_name.lower()
    return "wall" in tool_lower and ("door" in tool_lower or "opening" in str(params).lower())


def rule_007_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 007: Walls must extend past door openings
    Source: Memory ID 421

    Wall endpoints should be at wall-to-wall intersections, NOT at door openings.
    Doors are inserted INTO walls, so walls must be continuous through door locations.
    """
    # This is a WARN - we can't fully validate without geometry context
    return True, ""  # Pass but rely on fuzzy check for this pattern


def rule_008_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: Wall placement."""
    return "wall" in tool_name.lower() and "create" in tool_name.lower()


def rule_008_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 008: Wall endpoints at actual boundaries, not distant features
    Source: Memory ID 420, 450

    Stop walls at actual room edge/column, not at distant reference points.
    """
    # Check for suspiciously long walls (might be extending to distant features)
    if "startPoint" in params and "endPoint" in params:
        sp = params["startPoint"]
        ep = params["endPoint"]
        if isinstance(sp, list) and isinstance(ep, list) and len(sp) >= 2 and len(ep) >= 2:
            # Calculate length
            dx = abs(ep[0] - sp[0])
            dy = abs(ep[1] - sp[1])
            length = (dx**2 + dy**2) ** 0.5
            # Warn if wall is extremely long (> 200 feet)
            if length > 200:
                return False, f"Wall length {length:.1f}ft is unusually long. Verify endpoints are at actual room boundaries, not distant features."
    return True, ""


def rule_009_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: Wall with locationLine or exterior face specification."""
    return "wall" in tool_name.lower() and ("locationLine" in params or "exteriorFace" in str(params).lower())


def rule_009_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 009: Exterior face on grid requires centerline offset
    Source: Memory ID 187, 188

    locationLine=2 (FinishFaceExterior) alone is NOT sufficient.
    Must pre-calculate centerline offset = half wall thickness inward.
    """
    if params.get("locationLine") == 2:
        # Check if wallTypeId is provided to look up thickness
        if "wallTypeId" not in params and "wallThickness" not in params:
            return False, "When using locationLine=2 (exterior face on grid), must also account for wall thickness. Pre-calculate centerline offset = half wall thickness inward from grid."
    return True, ""


# -----------------------------------------------------------------------------
# RULES 010-012: Detail Component Checks
# -----------------------------------------------------------------------------

def rule_010_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: CMU or masonry component placement."""
    tool_lower = tool_name.lower()
    params_str = str(params).lower()
    return "placefamily" in tool_lower and ("cmu" in params_str or "masonry" in params_str or "block" in params_str)


def rule_010_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 010: CMU insertion point is BOTTOM-LEFT, not center
    Source: Memory ID 356, 355, 357

    First CMU course must be at Y=0 (grade level).
    Stacking: Y = courseNumber * 0.667 (8" courses)
    """
    if "location" in params:
        loc = params["location"]
        if isinstance(loc, list) and len(loc) >= 2:
            y = loc[1]
            # Check if Y looks like center placement instead of bottom
            # CMU course height is ~0.667 ft (8 inches)
            if 0.2 < y < 0.5:  # Suspiciously close to half course height
                return False, f"CMU Y={y:.3f}ft looks like center insertion. CMU insertion is BOTTOM-LEFT. First course at Y=0, subsequent at Y=course*0.667"
    return True, ""


def rule_011_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: Leader or text with leader creation."""
    tool_lower = tool_name.lower()
    return "leader" in tool_lower or "textnote" in tool_lower


def rule_011_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 011: Leaders must point at actual elements
    Source: Memory ID 346

    Leader endpoints should point DIRECTLY at the element they describe,
    not at calculated coordinates in empty space.
    """
    # WARN only - can't fully validate without visual context
    if "leaderEnd" in params and "elementId" not in params:
        return False, "Leaders should point at actual elements. Provide elementId or verify leaderEnd touches the target element."
    return True, ""


def rule_012_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: Keynote placement."""
    tool_lower = tool_name.lower()
    return "keynote" in tool_lower


def rule_012_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 012: Keynotes need leaders pointing to specific elements
    Source: Memory ID 301

    Don't place keynotes floating in approximate areas.
    Must have leader line from keynote to specific element.
    """
    if "hasLeader" in params and not params["hasLeader"]:
        return False, "Keynotes should have leaders pointing to specific elements, not float in approximate areas."
    if "elementId" not in params and "targetElement" not in params:
        return False, "Keynote needs target element. Identify specific element to keynote, not just approximate location."
    return True, ""


# -----------------------------------------------------------------------------
# RULES 013-015: Sheet/View Checks
# -----------------------------------------------------------------------------

def rule_013_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: Copy elements between documents (especially views)."""
    tool_lower = tool_name.lower()
    return "copy" in tool_lower and "between" in tool_lower and "document" in tool_lower


def rule_013_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 013: DraftingView copy requires create-new-then-copy-content workflow
    Source: Memory ID 451, 373, 371

    Views copied via copyElementsBetweenDocuments CANNOT be placed on sheets.

    CORRECT WORKFLOW:
    1. Create NEW DraftingView in destination (same name + scale)
    2. Use copyViewContentBetweenDocuments to copy content
    3. Then place the new view on sheet
    """
    params_str = str(params).lower()
    if "draftingview" in params_str or "legend" in params_str:
        if "createNew" not in params and "copyContent" not in params:
            return False, "DraftingView/Legend copy between documents requires: 1) Create NEW view with same name/scale, 2) copyViewContentBetweenDocuments, 3) Then place on sheet. Direct copy won't be placeable."
    return True, ""


def rule_014_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: Sheet creation."""
    tool_lower = tool_name.lower()
    return "createsheet" in tool_lower or ("sheet" in tool_lower and "create" in tool_lower)


def rule_014_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 014: createSheet must use project's standard titleblock
    Source: Memory ID 287, 280

    NEVER use default titleblock. Always:
    1. Query existing sheets for most-used titleblock
    2. Pass that titleblockId to createSheet
    """
    if "titleblockId" not in params and "titleBlockId" not in params:
        return False, "createSheet missing titleblockId. Query existing sheets to find project's standard titleblock, then pass its ID. Never use default."
    return True, ""


def rule_015_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: Viewport placement on sheet."""
    tool_lower = tool_name.lower()
    return "viewport" in tool_lower and ("place" in tool_lower or "create" in tool_lower)


def rule_015_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 015: Viewport coordinates must be within sheet bounds
    Source: Memory ID 395

    Typical ARCH D bounds: X < 2.8ft, Y < 1.8ft
    Negative or near-zero values likely wrong.
    """
    location = params.get("location") or params.get("position")
    if isinstance(location, list) and len(location) >= 2:
        x, y = location[0], location[1]
        errors = []

        # Check for obviously wrong values
        if x < 0:
            errors.append(f"X={x:.2f}ft is negative (off-sheet)")
        if y < 0:
            errors.append(f"Y={y:.2f}ft is negative (off-sheet)")
        if x > 3.0:  # Wider than ARCH D
            errors.append(f"X={x:.2f}ft exceeds typical sheet width")
        if y > 2.5:  # Taller than ARCH D
            errors.append(f"Y={y:.2f}ft exceeds typical sheet height")
        if x < 0.1 and y < 0.1:
            errors.append("Location near origin (0,0) - likely wrong, should be offset into printable area")

        if errors:
            return False, f"Viewport placement issue: {'; '.join(errors)}. Validate against sheet bounds first."
    return True, ""


# -----------------------------------------------------------------------------
# RULE 016: System State Check
# -----------------------------------------------------------------------------

def rule_016_trigger(tool_name: str, params: dict) -> bool:
    """Trigger: Any Revit MCP call that modifies the model."""
    tool_lower = tool_name.lower()
    # Trigger on modification operations
    modify_keywords = ["create", "place", "delete", "modify", "move", "set", "update", "batch"]
    return "revit" in tool_lower and any(kw in tool_lower for kw in modify_keywords)


def rule_016_check(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Rule 016: Revit must be active before model modifications
    Source: Memory ID 109

    Check system-bridge live_state.json to verify:
    1. Revit is running
    2. Revit is the active window (no dialogs blocking)
    """
    import os
    from pathlib import Path

    live_state_path = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")

    if not live_state_path.exists():
        # Can't check - allow but warn
        return True, ""

    try:
        with open(live_state_path) as f:
            state = json.load(f)

        # Check if Revit is in the applications list
        apps = state.get("applications", [])
        revit_apps = [a for a in apps if "revit" in a.get("ProcessName", "").lower()]

        if not revit_apps:
            return False, "Revit is not running. Start Revit and open a project before MCP operations."

        # Check if Revit is the active window
        active_window = state.get("active_window", "")
        if "revit" not in active_window.lower():
            return False, f"Revit is not the active window. Active: '{active_window[:50]}...'. Click into Revit before MCP operations."

        # Check for dialog indicators in window title
        dialog_indicators = ["dialog", "warning", "error", "message", "alert"]
        if any(ind in active_window.lower() for ind in dialog_indicators):
            return False, f"Revit appears to have a dialog open: '{active_window[:60]}'. Dismiss it before MCP operations."

        return True, ""

    except Exception as e:
        # Can't read state - allow operation
        return True, ""


# =============================================================================
# RULE REGISTRY
# =============================================================================

RULES = [
    # -------------------------------------------------------------------------
    # R001-R004: API/Parameter Checks (Bootstrap set)
    # -------------------------------------------------------------------------
    Rule(
        id="R001",
        source_memory_id=459,
        name="MCP Pipe Name Format",
        description="Pipe name must include 'Bridge' (RevitMCPBridge20XX)",
        severity=Severity.ERROR,
        trigger=rule_001_trigger,
        check=rule_001_check,
    ),
    Rule(
        id="R002",
        source_memory_id=234,
        name="MCP Parameter Key",
        description="Use 'params' not 'parameters' in MCP JSON",
        severity=Severity.ERROR,
        trigger=rule_002_trigger,
        check=rule_002_check,
    ),
    Rule(
        id="R003",
        source_memory_id=190,
        name="Wall Coordinate Format",
        description="startPoint/endPoint must be [x,y,z] arrays",
        severity=Severity.ERROR,
        trigger=rule_003_trigger,
        check=rule_003_check,
    ),
    Rule(
        id="R004",
        source_memory_id=407,
        name="Viewport Location Format",
        description="newLocation must be [x,y] array",
        severity=Severity.ERROR,
        trigger=rule_004_trigger,
        check=rule_004_check,
    ),
    # -------------------------------------------------------------------------
    # R005-R009: Wall Geometry Checks
    # -------------------------------------------------------------------------
    Rule(
        id="R005",
        source_memory_id=448,
        name="CAD Wall Parallel Pairs",
        description="CAD walls must come from parallel line pairs, not single lines",
        severity=Severity.ERROR,
        trigger=rule_005_trigger,
        check=rule_005_check,
    ),
    Rule(
        id="R006",
        source_memory_id=449,
        name="No Invented Walls",
        description="Only place walls where actual CAD lines exist",
        severity=Severity.ERROR,
        trigger=rule_006_trigger,
        check=rule_006_check,
    ),
    Rule(
        id="R007",
        source_memory_id=421,
        name="Walls Through Door Openings",
        description="Walls must extend past door openings to next intersection",
        severity=Severity.WARN,
        trigger=rule_007_trigger,
        check=rule_007_check,
    ),
    Rule(
        id="R008",
        source_memory_id=420,
        name="Wall Length Sanity Check",
        description="Walls >200ft likely extend to distant features incorrectly",
        severity=Severity.ERROR,
        trigger=rule_008_trigger,
        check=rule_008_check,
    ),
    Rule(
        id="R009",
        source_memory_id=187,
        name="Exterior Face Grid Offset",
        description="locationLine=2 requires wall thickness for centerline offset",
        severity=Severity.WARN,
        trigger=rule_009_trigger,
        check=rule_009_check,
    ),
    # -------------------------------------------------------------------------
    # R010-R012: Detail Component Checks
    # -------------------------------------------------------------------------
    Rule(
        id="R010",
        source_memory_id=356,
        name="CMU Insertion Point",
        description="CMU insertion is BOTTOM-LEFT, first course at Y=0",
        severity=Severity.ERROR,
        trigger=rule_010_trigger,
        check=rule_010_check,
    ),
    Rule(
        id="R011",
        source_memory_id=346,
        name="Leader Target Element",
        description="Leaders must point at actual elements, not empty space",
        severity=Severity.WARN,
        trigger=rule_011_trigger,
        check=rule_011_check,
    ),
    Rule(
        id="R012",
        source_memory_id=301,
        name="Keynote Element Target",
        description="Keynotes need leaders pointing to specific elements",
        severity=Severity.ERROR,
        trigger=rule_012_trigger,
        check=rule_012_check,
    ),
    # -------------------------------------------------------------------------
    # R013-R015: Sheet/View Checks
    # -------------------------------------------------------------------------
    Rule(
        id="R013",
        source_memory_id=451,
        name="DraftingView Copy Workflow",
        description="Create new view + copy content, don't direct-copy views",
        severity=Severity.ERROR,
        trigger=rule_013_trigger,
        check=rule_013_check,
    ),
    Rule(
        id="R014",
        source_memory_id=287,
        name="Sheet Titleblock Required",
        description="createSheet must specify titleblockId from project standard",
        severity=Severity.ERROR,
        trigger=rule_014_trigger,
        check=rule_014_check,
    ),
    Rule(
        id="R015",
        source_memory_id=395,
        name="Viewport Sheet Bounds",
        description="Viewport coordinates must be within sheet bounds",
        severity=Severity.ERROR,
        trigger=rule_015_trigger,
        check=rule_015_check,
    ),
    # -------------------------------------------------------------------------
    # R016: System State Check
    # -------------------------------------------------------------------------
    Rule(
        id="R016",
        source_memory_id=109,
        name="Revit Active State",
        description="Revit must be running and active before model modifications",
        severity=Severity.ERROR,
        trigger=rule_016_trigger,
        check=rule_016_check,
    ),
]


# =============================================================================
# RULE ENGINE
# =============================================================================

class RuleEngine:
    """Executes compiled correction rules against operations."""

    def __init__(self, rules: list[Rule] = None):
        self.rules = rules or RULES
        self.stats = {
            "checks_run": 0,
            "violations_caught": 0,
            "errors_blocked": 0,
        }

    def check(self, tool_name: str, params: dict) -> list[RuleResult]:
        """
        Run all applicable rules against an operation.

        Args:
            tool_name: Name of the tool being called
            params: Tool parameters

        Returns:
            List of RuleResults (only for rules that were triggered)
        """
        results = []

        for rule in self.rules:
            # Check if rule applies to this operation
            if not rule.trigger(tool_name, params):
                continue

            self.stats["checks_run"] += 1

            # Run the check
            passed, message = rule.check(tool_name, params)

            result = RuleResult(
                rule_id=rule.id,
                rule_name=rule.name,
                passed=passed,
                severity=rule.severity,
                message=message if not passed else "",
                source_memory_id=rule.source_memory_id,
            )

            if not passed:
                self.stats["violations_caught"] += 1
                if rule.severity == Severity.ERROR:
                    self.stats["errors_blocked"] += 1

            results.append(result)

        return results

    def should_block(self, results: list[RuleResult]) -> bool:
        """Check if any results require blocking the operation."""
        return any(
            not r.passed and r.severity == Severity.ERROR
            for r in results
        )

    def format_results(self, results: list[RuleResult]) -> str:
        """Format results for display."""
        if not results:
            return ""

        failures = [r for r in results if not r.passed]
        if not failures:
            return ""

        lines = [
            "",
            "=" * 60,
            "RULE ENGINE: VALIDATION FAILED",
            "=" * 60,
        ]

        for r in failures:
            severity_icon = "BLOCK" if r.severity == Severity.ERROR else "WARN"
            lines.append(f"[{severity_icon}] {r.rule_id}: {r.rule_name}")
            lines.append(f"       {r.message}")
            lines.append(f"       (Source: Memory #{r.source_memory_id})")
            lines.append("")

        if self.should_block(results):
            lines.extend([
                "=" * 60,
                "OPERATION BLOCKED - Fix the above issues first.",
                "=" * 60,
            ])

        return "\n".join(lines)


# Global instance
_engine = RuleEngine()


def check_operation(tool_name: str, params: dict) -> tuple[bool, str]:
    """
    Main entry point for rule checking.

    Args:
        tool_name: Name of the tool
        params: Tool parameters (dict)

    Returns:
        (allowed, message) - allowed=False means block the operation
    """
    results = _engine.check(tool_name, params)

    if not results:
        return True, ""

    should_block = _engine.should_block(results)
    message = _engine.format_results(results)

    return not should_block, message


def get_stats() -> dict:
    """Get rule engine statistics."""
    return _engine.stats.copy()


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import sys

    print("Rule Engine Test Suite - All 15 Rules")
    print("=" * 60)

    test_cases = [
        # R001-R004: API/Parameter Checks
        ("R001 FAIL", "mcp__revitmcp2026__createWall", {"startPoint": [0,0,0], "endPoint": [10,0,0]}, False),
        ("R001 PASS", "mcp__revitmcpbridge2026__createWall", {"startPoint": [0,0,0], "endPoint": [10,0,0]}, True),
        ("R003 FAIL", "mcp__revitmcpbridge2026__createWall", {"startX": 0, "startY": 0}, False),
        ("R004 FAIL", "mcp__revitmcpbridge2026__moveViewport", {"viewportId": 123, "x": 1.5, "y": 0.8}, False),
        ("R004 PASS", "mcp__revitmcpbridge2026__moveViewport", {"viewportId": 123, "newLocation": [1.5, 0.8]}, True),

        # R005-R009: Wall Geometry Checks
        ("R005 FAIL", "mcp__revitmcpbridge2026__createWallsFromCAD", {"lines": [[0,0], [10,0]]}, False),
        ("R005 PASS", "mcp__revitmcpbridge2026__createWallsFromCAD", {"pairs": [[0,0], [10,0]]}, True),
        ("R006 FAIL", "mcp__revitmcpbridge2026__createWallsFromDXF", {"fillGaps": True}, False),
        ("R008 FAIL", "mcp__revitmcpbridge2026__createWall", {"startPoint": [0,0,0], "endPoint": [500,0,0]}, False),
        ("R009 WARN", "mcp__revitmcpbridge2026__createWall", {"locationLine": 2, "startPoint": [0,0,0], "endPoint": [10,0,0]}, True),  # WARN allows

        # R010-R012: Detail Component Checks
        ("R010 FAIL", "mcp__revitmcpbridge2026__placeFamilyInstance", {"familyName": "CMU-8x8x16", "location": [0, 0.333, 0]}, False),
        ("R010 PASS", "mcp__revitmcpbridge2026__placeFamilyInstance", {"familyName": "CMU-8x8x16", "location": [0, 0, 0]}, True),
        ("R012 FAIL", "mcp__revitmcpbridge2026__placeKeynote", {"location": [5, 5]}, False),
        ("R012 PASS", "mcp__revitmcpbridge2026__placeKeynote", {"location": [5, 5], "elementId": 12345}, True),

        # R013-R015: Sheet/View Checks
        ("R013 FAIL", "mcp__revitmcpbridge2026__copyElementsBetweenDocuments", {"viewType": "DraftingView"}, False),
        ("R014 FAIL", "mcp__revitmcpbridge2026__createSheet", {"number": "A101", "name": "FLOOR PLAN"}, False),
        ("R014 PASS", "mcp__revitmcpbridge2026__createSheet", {"number": "A101", "titleblockId": 12345}, True),
        ("R015 FAIL", "mcp__revitmcpbridge2026__placeViewport", {"viewId": 1, "sheetId": 2, "location": [-0.5, 0.5]}, False),
        ("R015 PASS", "mcp__revitmcpbridge2026__placeViewport", {"viewId": 1, "sheetId": 2, "location": [1.5, 1.0]}, True),
    ]

    passed = 0
    failed = 0

    for name, tool, params, expected_allowed in test_cases:
        allowed, message = check_operation(tool, params)
        test_passed = (allowed == expected_allowed)

        if test_passed:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"

        print(f"\n{status}: {name}")
        print(f"  Tool: {tool}")
        print(f"  Expected: {'ALLOWED' if expected_allowed else 'BLOCKED'}, Got: {'ALLOWED' if allowed else 'BLOCKED'}")
        if message and not allowed:
            # Show first line of message only
            first_line = message.split('\n')[4] if '\n' in message else message
            print(f"  Message: {first_line[:80]}")

    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed}/{len(test_cases)} passed, {failed} failed")
    print(f"Rule Stats: {get_stats()}")
    print(f"Total rules registered: {len(RULES)}")
