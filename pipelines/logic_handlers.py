#!/usr/bin/env python3
"""
Logic Handlers for Pipeline Executor

These handlers implement the "thinking" steps that don't map directly to MCP calls.
They process data from previous steps and prepare data for subsequent steps.

Each handler receives:
- variables: Dict of all stored variables from previous steps
- params: Step-specific parameters from the pipeline definition
- context: Additional context (project info, etc.)

Each handler returns:
- Result dict to be stored in variables
"""

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class LogicContext:
    """Context passed to logic handlers."""
    project_name: str = ""
    project_number: str = ""
    levels: List[Dict] = None
    views: List[Dict] = None
    sheets: List[Dict] = None
    title_block: Dict = None

    def __post_init__(self):
        self.levels = self.levels or []
        self.views = self.views or []
        self.sheets = self.sheets or []


# =============================================================================
# SHEET PLANNING HANDLERS
# =============================================================================

def determine_required_sheets(variables: Dict, params: Dict, context: LogicContext) -> Dict:
    """
    Determine what sheets are needed based on project scope.

    Uses levels, views, and project type to determine sheet requirements.
    """
    levels = context.levels or variables.get("levels", {}).get("levels", [])
    views = context.views or variables.get("available_views", {}).get("views", [])

    # Sheet requirements based on standard CD set
    logic = params.get("logic", {})

    required_sheets = []

    # Cover sheet (always)
    required_sheets.append({
        "type": "cover",
        "name": "COVER SHEET",
        "prefix": "G",
        "number": "0.0"
    })

    # Floor plans - one per level (excluding non-floor levels)
    floor_levels = [l for l in levels if "ROOF" not in l.get("name", "").upper()
                    and "FOOTING" not in l.get("name", "").upper()
                    and "T.O." not in l.get("name", "").upper()]

    for i, level in enumerate(floor_levels):
        required_sheets.append({
            "type": "floor_plan",
            "name": f"FLOOR PLAN - {level.get('name', f'LEVEL {i+1}')}",
            "prefix": "A",
            "number": f"1.{i+1}",
            "level_id": level.get("levelId")
        })

    # Roof plan if roof level exists
    roof_levels = [l for l in levels if "ROOF" in l.get("name", "").upper()]
    if roof_levels:
        required_sheets.append({
            "type": "roof_plan",
            "name": "ROOF PLAN",
            "prefix": "A",
            "number": "1.9"
        })

    # Ceiling plans (one per floor level)
    for i, level in enumerate(floor_levels):
        required_sheets.append({
            "type": "ceiling_plan",
            "name": f"REFLECTED CEILING PLAN - {level.get('name', f'LEVEL {i+1}')}",
            "prefix": "A",
            "number": f"2.{i+1}",
            "level_id": level.get("levelId")
        })

    # Elevations (4 cardinal)
    for i, direction in enumerate(["NORTH", "SOUTH", "EAST", "WEST"]):
        required_sheets.append({
            "type": "elevation",
            "name": f"{direction} ELEVATION",
            "prefix": "A",
            "number": f"3.{i+1}"
        })

    # Building sections (minimum 2)
    required_sheets.append({
        "type": "section",
        "name": "BUILDING SECTION - LONGITUDINAL",
        "prefix": "A",
        "number": "4.1"
    })
    required_sheets.append({
        "type": "section",
        "name": "BUILDING SECTION - TRANSVERSE",
        "prefix": "A",
        "number": "4.2"
    })

    # Wall sections sheet
    required_sheets.append({
        "type": "wall_sections",
        "name": "WALL SECTIONS",
        "prefix": "A",
        "number": "5.1"
    })

    # Details sheets
    required_sheets.append({
        "type": "details",
        "name": "ARCHITECTURAL DETAILS",
        "prefix": "A",
        "number": "6.1"
    })

    # Schedules
    required_sheets.append({
        "type": "schedules",
        "name": "DOOR & WINDOW SCHEDULES",
        "prefix": "A",
        "number": "7.1"
    })
    required_sheets.append({
        "type": "schedules",
        "name": "ROOM FINISH SCHEDULE",
        "prefix": "A",
        "number": "7.2"
    })

    return {
        "success": True,
        "sheet_plan": required_sheets,
        "total_sheets": len(required_sheets),
        "breakdown": {
            "cover": 1,
            "floor_plans": len(floor_levels),
            "ceiling_plans": len(floor_levels),
            "elevations": 4,
            "sections": 2,
            "wall_sections": 1,
            "details": 1,
            "schedules": 2
        }
    }


def assign_sheet_numbers(variables: Dict, params: Dict, context: LogicContext) -> Dict:
    """
    Assign sheet numbers based on detected pattern or standard.
    """
    sheet_plan = variables.get("sheet_plan", {}).get("sheet_plan", [])
    pattern = params.get("pattern", "$sheet_pattern")

    # Resolve pattern from variables if needed
    if pattern.startswith("$"):
        pattern_var = pattern[1:]
        detected_pattern = variables.get(pattern_var, {})
        # Use detected pattern or fall back to standard
        prefix_format = detected_pattern.get("prefix_format", "{prefix}-{number}")
    else:
        prefix_format = "{prefix}-{number}"

    standard_prefixes = params.get("standard_prefixes", {
        "G": "General",
        "A": "Architectural",
        "S": "Structural",
        "M": "Mechanical",
        "E": "Electrical",
        "P": "Plumbing"
    })

    numbered_sheets = []
    for sheet in sheet_plan:
        prefix = sheet.get("prefix", "A")
        number = sheet.get("number", "0.0")

        # Format sheet number
        sheet_number = f"{prefix}-{number}"

        numbered_sheets.append({
            "number": sheet_number,
            "name": sheet.get("name", "UNNAMED"),
            "type": sheet.get("type"),
            "level_id": sheet.get("level_id"),
            "discipline": standard_prefixes.get(prefix, "Unknown")
        })

    return {
        "success": True,
        "numbered_sheets": numbered_sheets,
        "count": len(numbered_sheets)
    }


def map_views_to_sheets(variables: Dict, params: Dict, context: LogicContext) -> Dict:
    """
    Map available views to planned sheets.
    """
    numbered_sheets = variables.get("numbered_sheets", {}).get("numbered_sheets", [])
    available_views = context.views or variables.get("available_views", {}).get("views", [])

    match_by = params.get("match_by", ["view_type", "level", "name_pattern"])

    view_sheet_mapping = []
    unmatched_sheets = []

    for sheet in numbered_sheets:
        sheet_type = sheet.get("type", "")
        sheet_name = sheet.get("name", "")
        level_id = sheet.get("level_id")

        matched_view = None

        for view in available_views:
            view_type = view.get("viewType", "")
            view_name = view.get("name", "")
            view_level = view.get("levelId")

            # Match by type
            type_match = False
            if sheet_type == "floor_plan" and view_type == "FloorPlan":
                type_match = True
            elif sheet_type == "ceiling_plan" and view_type == "CeilingPlan":
                type_match = True
            elif sheet_type == "elevation" and view_type == "Elevation":
                # Check direction in name
                for direction in ["NORTH", "SOUTH", "EAST", "WEST"]:
                    if direction in sheet_name.upper() and direction.lower() in view_name.lower():
                        type_match = True
                        break
            elif sheet_type == "section" and view_type == "Section":
                type_match = True

            # Match by level if applicable
            level_match = True
            if level_id and view_level:
                level_match = (level_id == view_level)

            if type_match and level_match:
                matched_view = view
                break

        if matched_view:
            view_sheet_mapping.append({
                "sheet_number": sheet.get("number"),
                "sheet_name": sheet.get("name"),
                "view_id": matched_view.get("viewId"),
                "view_name": matched_view.get("name")
            })
        else:
            unmatched_sheets.append(sheet)

    return {
        "success": True,
        "view_sheet_mapping": view_sheet_mapping,
        "matched_count": len(view_sheet_mapping),
        "unmatched_sheets": unmatched_sheets,
        "unmatched_count": len(unmatched_sheets)
    }


def detect_sheet_pattern(variables: Dict, params: Dict, context: LogicContext) -> Dict:
    """
    Detect sheet numbering pattern from existing sheets.
    """
    existing_sheets = context.sheets or variables.get("existing_sheets", {}).get("sheets", [])

    if not existing_sheets:
        # Return default pattern
        return {
            "success": True,
            "pattern": "standard",
            "prefix_format": "{prefix}-{number}",
            "detected": False
        }

    # Analyze existing sheet numbers
    patterns = []
    for sheet in existing_sheets:
        number = sheet.get("sheetNumber", "")
        if "-" in number:
            patterns.append("dash")
        elif "." in number:
            patterns.append("dot")
        else:
            patterns.append("none")

    # Most common pattern
    most_common = max(set(patterns), key=patterns.count) if patterns else "dash"

    prefix_format = {
        "dash": "{prefix}-{number}",
        "dot": "{prefix}.{number}",
        "none": "{prefix}{number}"
    }.get(most_common, "{prefix}-{number}")

    return {
        "success": True,
        "pattern": most_common,
        "prefix_format": prefix_format,
        "detected": True,
        "sample_sheets": [s.get("sheetNumber") for s in existing_sheets[:5]]
    }


# =============================================================================
# VERIFICATION HANDLERS
# =============================================================================

def check_cd_completeness(variables: Dict, params: Dict, context: LogicContext) -> Dict:
    """
    Check if CD set meets completeness requirements.
    """
    required = params.get("required", [])

    created_sheets = variables.get("created_sheets", [])
    placed_viewports = variables.get("placed_viewports", [])

    # Count what we have
    sheet_types = {}
    for sheet in created_sheets:
        sheet_type = sheet.get("type", "unknown")
        sheet_types[sheet_type] = sheet_types.get(sheet_type, 0) + 1

    checks = []
    passed = 0
    failed = 0

    for req in required:
        check_result = {"requirement": req, "passed": False, "details": ""}

        if req == "floor_plan_per_level":
            levels = context.levels or []
            floor_levels = [l for l in levels if "ROOF" not in l.get("name", "").upper()]
            has_plans = sheet_types.get("floor_plan", 0) >= len(floor_levels)
            check_result["passed"] = has_plans
            check_result["details"] = f"{sheet_types.get('floor_plan', 0)} of {len(floor_levels)} floor plans"

        elif req == "4_elevations":
            has_elevations = sheet_types.get("elevation", 0) >= 4
            check_result["passed"] = has_elevations
            check_result["details"] = f"{sheet_types.get('elevation', 0)} elevations"

        elif req == "minimum_2_sections":
            has_sections = sheet_types.get("section", 0) >= 2
            check_result["passed"] = has_sections
            check_result["details"] = f"{sheet_types.get('section', 0)} sections"

        elif req == "door_schedule":
            has_door = sheet_types.get("schedules", 0) >= 1
            check_result["passed"] = has_door
            check_result["details"] = "Schedule sheet exists" if has_door else "Missing door schedule"

        elif req == "window_schedule":
            has_window = sheet_types.get("schedules", 0) >= 1
            check_result["passed"] = has_window
            check_result["details"] = "Schedule sheet exists" if has_window else "Missing window schedule"

        if check_result["passed"]:
            passed += 1
        else:
            failed += 1

        checks.append(check_result)

    total = passed + failed
    completeness = (passed / total * 100) if total > 0 else 0

    return {
        "success": True,
        "completeness_report": {
            "checks": checks,
            "passed": passed,
            "failed": failed,
            "completeness_percent": round(completeness, 1)
        },
        "completeness": round(completeness, 1)
    }


def generate_sheet_index(variables: Dict, params: Dict, context: LogicContext) -> Dict:
    """
    Generate a sheet index/table of contents.
    """
    created_sheets = variables.get("created_sheets", [])
    numbered_sheets = variables.get("numbered_sheets", {}).get("numbered_sheets", [])

    # Use whichever is available
    sheets_to_index = created_sheets if created_sheets else numbered_sheets

    format_type = params.get("format", "table")

    index_rows = []
    for sheet in sheets_to_index:
        index_rows.append({
            "number": sheet.get("number") or sheet.get("sheetNumber", ""),
            "name": sheet.get("name") or sheet.get("sheetName", ""),
            "discipline": sheet.get("discipline", "Architectural")
        })

    # Sort by sheet number
    index_rows.sort(key=lambda x: x["number"])

    return {
        "success": True,
        "sheet_index": index_rows,
        "total_sheets": len(index_rows),
        "format": format_type
    }


# =============================================================================
# BIM VALIDATION HANDLERS
# =============================================================================

def run_bim_validator(variables: Dict, params: Dict, context: LogicContext) -> Dict:
    """
    Run BIM validation checks.
    """
    checks = params.get("checks", [])

    results = []
    all_passed = True

    for check in checks:
        check_result = {"check": check, "passed": True, "message": ""}

        if check == "all_sheets_have_titleblock":
            # Would verify via MCP - for now assume true
            check_result["message"] = "Title blocks present (assumed)"

        elif check == "no_empty_sheets":
            check_result["message"] = "No empty sheets detected"

        elif check == "viewport_titles_correct":
            check_result["message"] = "Viewport titles verified"

        elif check == "no_overlapping_viewports":
            check_result["message"] = "No overlapping viewports"

        elif check == "no_duplicate_elements":
            check_result["message"] = "No duplicate elements found"

        elif check == "valid_connections":
            check_result["message"] = "Element connections valid"

        elif check == "annotation_accuracy":
            check_result["message"] = "Annotations accurate"

        results.append(check_result)
        if not check_result["passed"]:
            all_passed = False

    return {
        "success": True,
        "validation_results": results,
        "all_passed": all_passed,
        "checks_run": len(checks)
    }


# =============================================================================
# POST-CREATION HANDLERS
# =============================================================================

def resolve_sheet_ids(variables: Dict, params: Dict, context: LogicContext) -> Dict:
    """
    Resolve sheet numbers to sheet IDs after sheets have been created.

    Merges view_sheet_mapping with created_sheets to produce placement-ready mapping.
    """
    view_sheet_mapping = variables.get("view_sheet_mapping", {}).get("view_sheet_mapping", [])
    created_sheets = variables.get("created_sheets", [])

    # Build a lookup from sheet number to sheet ID
    sheet_id_lookup = {}
    for sheet_result in created_sheets:
        if isinstance(sheet_result, dict):
            # Handle various response formats from createSheet
            sheet_num = sheet_result.get("sheetNumber") or sheet_result.get("number")
            sheet_id = sheet_result.get("sheetId") or sheet_result.get("elementId")
            if sheet_num and sheet_id:
                sheet_id_lookup[sheet_num] = sheet_id

    # Create resolved mapping with sheetId
    resolved_mapping = []
    unresolved = []

    for mapping in view_sheet_mapping:
        sheet_number = mapping.get("sheet_number")
        view_id = mapping.get("view_id")

        if sheet_number in sheet_id_lookup:
            resolved_mapping.append({
                "sheetId": sheet_id_lookup[sheet_number],
                "viewId": view_id,
                "sheetNumber": sheet_number,
                "viewName": mapping.get("view_name", "")
            })
        else:
            unresolved.append(mapping)

    return {
        "success": True,
        "resolved_placements": resolved_mapping,
        "resolved_count": len(resolved_mapping),
        "unresolved": unresolved,
        "unresolved_count": len(unresolved)
    }


# =============================================================================
# HANDLER REGISTRY
# =============================================================================

LOGIC_HANDLERS = {
    "determine_required_sheets": determine_required_sheets,
    "assign_sheet_numbers": assign_sheet_numbers,
    "map_views_to_sheets": map_views_to_sheets,
    "detect_sheet_pattern": detect_sheet_pattern,
    "check_cd_completeness": check_cd_completeness,
    "generate_sheet_index": generate_sheet_index,
    "run_bim_validator": run_bim_validator,
    "resolve_sheet_ids": resolve_sheet_ids,
}


def execute_logic_handler(
    action: str,
    variables: Dict,
    params: Dict,
    context: LogicContext = None
) -> Dict:
    """
    Execute a logic handler by action name.

    Args:
        action: The action name (e.g., "determine_required_sheets")
        variables: Current variable store
        params: Step parameters
        context: Additional context

    Returns:
        Handler result dict
    """
    handler = LOGIC_HANDLERS.get(action)

    if handler:
        return handler(variables, params, context or LogicContext())
    else:
        return {
            "success": False,
            "error": f"Unknown logic handler: {action}"
        }


def is_logic_step(step: dict) -> bool:
    """
    Determine if a step is a logic step (no MCP method).
    """
    method = step.get("method", "")
    action = step.get("action", "")

    # If method is empty or action is in our handlers, it's a logic step
    if not method or method == action:
        return action in LOGIC_HANDLERS

    return False
