"""
Stage 3: Revit Execution

Converts a FloorPlan into Revit MCP calls to build the actual model.
Uses coordinate-based wall registry for reliable door/window placement
(ported from replicate_edrawmax_plan.py's proven approach).

Requires:
- RevitClient from pipelines/revit_client.py
- Active Revit project with a Level 1
"""

import sys
from typing import Dict, Any, Optional, List

# Import RevitClient
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/pipelines")
from revit_client import RevitClient, get_active_client

from .models import FloorPlan, WallSegment, DoorPlacement, WindowPlacement, RoomRect


# Default door/window type IDs from Residential-Default.rte template
DEFAULT_FRONT_DOOR_TYPE = 50865     # Single-Flush 36" x 84"
DEFAULT_INTERIOR_DOOR_TYPE = 50873  # Single-Flush 30" x 80"


def _revit_call(client: RevitClient, method: str, params: dict, label: str = "") -> Optional[dict]:
    """Call Revit MCP method with logging."""
    tag = label or method
    print(f"  [REVIT] {tag}...")
    result = client.call(method, params)
    if result.success:
        print(f"  [REVIT] {tag} OK")
        return result.data
    else:
        print(f"  [REVIT] {tag} FAILED: {result.error}")
        return None


def find_level_id(client: RevitClient) -> Optional[int]:
    """Find ground floor level ID."""
    levels = _revit_call(client, "getLevels", {}, "Get levels")
    if not levels:
        return None

    level_list = []
    if isinstance(levels, list):
        level_list = levels
    elif "levels" in levels:
        level_list = levels["levels"]
    elif "data" in levels:
        level_list = levels["data"] if isinstance(levels["data"], list) else []

    ground_names = ["Level 1", "Level1", "First Floor", "Ground"]
    for lv in level_list:
        name = str(lv.get("name", ""))
        lid = lv.get("id") or lv.get("levelId")
        if any(gn in name for gn in ground_names):
            return lid

    if level_list:
        level_list.sort(key=lambda x: x.get("elevation", 999))
        return level_list[0].get("id") or level_list[0].get("levelId")

    return None


def _find_wall_id_at(registry: List[dict], x: float, y: float,
                     tol: float = 2.0) -> Optional[int]:
    """Find the wall ID that passes through or near point (x, y).

    Uses point-to-segment distance against all registry entries.
    Direct port of replicate_edrawmax_plan.py's find_wall_id_at().

    Args:
        registry: List of dicts with wallId, x1, y1, x2, y2, is_exterior
        x, y: Point to find wall at
        tol: Maximum distance tolerance

    Returns:
        Wall ID or None
    """
    best = None
    best_dist = float('inf')

    for wd in registry:
        x1, y1, x2, y2 = wd["x1"], wd["y1"], wd["x2"], wd["y2"]

        # Point-to-segment distance
        dx, dy = x2 - x1, y2 - y1
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq < 0.01:
            dist = ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
        else:
            t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / seg_len_sq))
            px, py = x1 + t * dx, y1 + t * dy
            dist = ((x - px) ** 2 + (y - py) ** 2) ** 0.5

        if dist < best_dist:
            best_dist = dist
            best = wd

    if best and best_dist <= tol:
        return best["wallId"]
    return None


def _find_wall_type_ids(client: RevitClient) -> Dict[str, Optional[int]]:
    """Find exterior (8") and interior (4") wall type IDs.

    Returns dict with 'exterior' and 'interior' keys.
    Falls back to None if types can't be found.
    """
    result = {"exterior": None, "interior": None}

    types_data = _revit_call(client, "getWallTypes", {}, "Get wall types")
    if not types_data:
        return result

    type_list = []
    if isinstance(types_data, list):
        type_list = types_data
    elif "wallTypes" in types_data:
        type_list = types_data["wallTypes"]
    elif "data" in types_data:
        type_list = types_data["data"] if isinstance(types_data["data"], list) else []

    for wt in type_list:
        name = str(wt.get("name", "")).lower()
        type_id = wt.get("id") or wt.get("typeId") or wt.get("wallTypeId")
        if type_id is None:
            continue

        # Look for exterior wall types (typically 8" or "exterior")
        if result["exterior"] is None:
            if "exterior" in name or '8"' in name or "8 inch" in name:
                result["exterior"] = type_id

        # Look for interior wall types (typically 4" or 5" or "interior")
        if result["interior"] is None:
            if "interior" in name or '4"' in name or "4 inch" in name or '5"' in name:
                result["interior"] = type_id

    return result


def execute_in_revit(
    plan: FloorPlan,
    client: Optional[RevitClient] = None,
    level_id: Optional[int] = None,
    wall_height: float = 10.0,
    create_3d_view: bool = True,
    verbose: bool = True,
    verify: bool = False,
) -> Dict[str, Any]:
    """Execute a FloorPlan in Revit via MCP.

    Args:
        plan: The FloorPlan to build
        client: RevitClient instance (auto-detects if None)
        level_id: Level ID to build on (auto-detects if None)
        wall_height: Wall height in feet
        create_3d_view: Whether to create and switch to 3D view at end
        verbose: Print progress
        verify: After creation, call getWalls to verify counts match

    Returns:
        Dict with created element IDs and status
    """
    # Auto-detect client
    if client is None:
        client = get_active_client(verbose=verbose)
        if client is None:
            return {"success": False, "error": "No Revit MCP connection available"}

    # Auto-detect level
    if level_id is None:
        level_id = find_level_id(client)
        if level_id is None:
            return {"success": False, "error": "Could not find Level 1"}

    if verbose:
        print(f"\n{'='*50}")
        print(f"FLOOR PLAN ENGINE → REVIT")
        print(f"  {plan.footprint_width}' x {plan.footprint_height}' = {plan.total_area:.0f} SF")
        print(f"  {len(plan.rooms)} rooms, {len(plan.walls)} walls")
        print(f"  {len(plan.doors)} doors, {len(plan.windows)} windows")
        print(f"  Level ID: {level_id}")
        print(f"{'='*50}\n")

    result = {
        "success": True,
        "level_id": level_id,
        "exterior_walls": [],
        "interior_walls": [],
        "wall_id_registry": [],
        "doors": [],
        "windows": [],
        "rooms": [],
        "view_3d": None,
        "verification": None,
    }

    # Try to find wall type IDs for exterior vs interior
    wall_type_ids = _find_wall_type_ids(client)

    # ── Step 1: Exterior Walls ──
    ext_walls = [w for w in plan.walls if w.is_exterior]
    ext_walls_data = []
    for w in ext_walls:
        wall_data = {
            "startPoint": [w.x1, w.y1, 0],
            "endPoint": [w.x2, w.y2, 0],
            "levelId": level_id,
            "height": wall_height,
        }
        if wall_type_ids["exterior"]:
            wall_data["wallTypeId"] = wall_type_ids["exterior"]
        ext_walls_data.append(wall_data)

    if ext_walls_data:
        ext_result = _revit_call(client, "batchCreateWalls", {
            "walls": ext_walls_data
        }, f"Exterior walls ({len(ext_walls_data)})")

        if ext_result and "createdWalls" in ext_result:
            result["exterior_walls"] = ext_result["createdWalls"]
            # Build wall ID registry with coordinates
            for i, wid_data in enumerate(ext_result["createdWalls"]):
                if i >= len(ext_walls):
                    break
                w = ext_walls[i]
                wid = wid_data.get("wallId") or wid_data.get("elementId") if isinstance(wid_data, dict) else wid_data
                result["wall_id_registry"].append({
                    "wallId": wid,
                    "x1": w.x1, "y1": w.y1, "x2": w.x2, "y2": w.y2,
                    "is_exterior": True,
                })
            if verbose:
                print(f"  Created {len(result['exterior_walls'])} exterior walls")

    # ── Step 2: Interior Walls ──
    int_walls = [w for w in plan.walls if not w.is_exterior]
    int_walls_data = []
    for w in int_walls:
        wall_data = {
            "startPoint": [w.x1, w.y1, 0],
            "endPoint": [w.x2, w.y2, 0],
            "levelId": level_id,
            "height": wall_height,
        }
        if wall_type_ids["interior"]:
            wall_data["wallTypeId"] = wall_type_ids["interior"]
        int_walls_data.append(wall_data)

    if int_walls_data:
        int_result = _revit_call(client, "batchCreateWalls", {
            "walls": int_walls_data
        }, f"Interior walls ({len(int_walls_data)})")

        if int_result and "createdWalls" in int_result:
            result["interior_walls"] = int_result["createdWalls"]
            # Add to wall ID registry with coordinates
            for i, wid_data in enumerate(int_result["createdWalls"]):
                if i >= len(int_walls):
                    break
                w = int_walls[i]
                wid = wid_data.get("wallId") or wid_data.get("elementId") if isinstance(wid_data, dict) else wid_data
                result["wall_id_registry"].append({
                    "wallId": wid,
                    "x1": w.x1, "y1": w.y1, "x2": w.x2, "y2": w.y2,
                    "is_exterior": False,
                })
            if verbose:
                print(f"  Created {len(result['interior_walls'])} interior walls")

    # Zoom to fit after walls
    _revit_call(client, "zoomToFit", {}, "Zoom to fit")

    # ── Step 3: Doors ──
    wall_registry = result["wall_id_registry"]

    for door in plan.doors:
        # Find wall by coordinate proximity (proven approach from reference script)
        wall_id = _find_wall_id_at(
            wall_registry, door.location[0], door.location[1])
        if wall_id is None:
            if verbose:
                print(f"  [SKIP] No wall found for door at ({door.location[0]}, {door.location[1]})")
            continue

        # Select door type
        is_entry = door.room_b == "exterior"
        type_id = DEFAULT_FRONT_DOOR_TYPE if is_entry else DEFAULT_INTERIOR_DOOR_TYPE

        door_result = _revit_call(client, "placeDoor", {
            "wallId": wall_id,
            "typeId": type_id,
            "location": [door.location[0], door.location[1], 0],
        }, f"Door: {door.room_a} → {door.room_b}")

        if door_result:
            door_id = door_result.get("doorId") or door_result.get("elementId")
            if door_id:
                result["doors"].append(door_id)

    # ── Step 4: Windows ──
    for window in plan.windows:
        wall_id = _find_wall_id_at(
            wall_registry, window.location[0], window.location[1], tol=1.0)
        if wall_id is None:
            if verbose:
                print(f"  [SKIP] No wall found for window at ({window.location[0]}, {window.location[1]})")
            continue

        win_result = _revit_call(client, "placeWindow", {
            "wallId": wall_id,
            "location": [window.location[0], window.location[1], 0],
        }, f"Window: {window.room_name}")

        if win_result:
            win_id = win_result.get("windowId") or win_result.get("elementId")
            if win_id:
                result["windows"].append(win_id)

    # ── Step 5: Rooms ──
    for room in plan.rooms:
        room_result = _revit_call(client, "createRoom", {
            "levelId": level_id,
            "location": [room.cx, room.cy],
            "name": room.name,
        }, f"Room: {room.name}")

        if room_result:
            room_id = room_result.get("roomId") or room_result.get("elementId")
            if room_id:
                result["rooms"].append(room_id)

    # ── Step 6: 3D View ──
    if create_3d_view:
        view_3d = _revit_call(client, "create3DView", {
            "viewName": "Floor Plan Engine 3D"
        }, "Create 3D view")

        if view_3d:
            vid = None
            if "result" in view_3d and isinstance(view_3d["result"], dict):
                vid = view_3d["result"].get("viewId")
            elif "viewId" in view_3d:
                vid = view_3d["viewId"]

            if vid is not None:
                result["view_3d"] = vid
                _revit_call(client, "setActiveView", {"viewId": int(vid)}, "Switch to 3D")
                _revit_call(client, "zoomToFit", {}, "Zoom 3D to fit")

    # ── Step 7: Verification ──
    if verify:
        result["verification"] = _verify_creation(
            client, plan, result, verbose)

    # Summary
    if verbose:
        print(f"\n{'='*50}")
        print(f"REVIT EXECUTION COMPLETE")
        print(f"  Exterior walls: {len(result['exterior_walls'])}")
        print(f"  Interior walls: {len(result['interior_walls'])}")
        print(f"  Doors: {len(result['doors'])}")
        print(f"  Windows: {len(result['windows'])}")
        print(f"  Rooms: {len(result['rooms'])}")
        total = (len(result['exterior_walls']) + len(result['interior_walls']) +
                 len(result['doors']) + len(result['windows']) + len(result['rooms']))
        print(f"  Total elements: {total}")
        if result["verification"]:
            v = result["verification"]
            if v.get("discrepancies"):
                print(f"  VERIFICATION ISSUES:")
                for d in v["discrepancies"]:
                    print(f"    - {d}")
            else:
                print(f"  Verification: PASSED")
        print(f"{'='*50}")

    return result


def _verify_creation(
    client: RevitClient, plan: FloorPlan,
    result: Dict[str, Any], verbose: bool
) -> Dict[str, Any]:
    """Verify that Revit element counts match expected counts."""
    verification = {"passed": True, "discrepancies": []}

    walls_data = _revit_call(client, "getWalls", {}, "Verify walls")
    if walls_data:
        wall_list = []
        if isinstance(walls_data, list):
            wall_list = walls_data
        elif "walls" in walls_data:
            wall_list = walls_data["walls"]
        elif "data" in walls_data:
            wall_list = walls_data["data"] if isinstance(walls_data["data"], list) else []

        expected_walls = len(plan.walls)
        actual_walls = len(wall_list)
        if actual_walls != expected_walls:
            verification["passed"] = False
            verification["discrepancies"].append(
                f"Walls: expected {expected_walls}, got {actual_walls}"
            )

    expected_doors = len(plan.doors)
    actual_doors = len(result["doors"])
    if actual_doors != expected_doors:
        verification["passed"] = False
        verification["discrepancies"].append(
            f"Doors: expected {expected_doors}, placed {actual_doors}"
        )

    expected_windows = len(plan.windows)
    actual_windows = len(result["windows"])
    if actual_windows != expected_windows:
        verification["passed"] = False
        verification["discrepancies"].append(
            f"Windows: expected {expected_windows}, placed {actual_windows}"
        )

    return verification
