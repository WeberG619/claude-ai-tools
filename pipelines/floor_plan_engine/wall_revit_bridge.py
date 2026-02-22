"""
WallPlan → Revit execution bridge.

Direct port of the proven replicate_edrawmax_plan.py pattern,
accepting a WallPlan as input instead of hardcoded constants.

Execution steps:
1. batchCreateWalls for exterior walls → wall registry
2. batchCreateWalls for interior walls → add to wall registry
3. zoomToFit
4. For each door: resolve position → find wall ID → placeDoor
5. For each window: resolve position → find wall ID → placeWindow
6. For each room: createRoom at center
7. create3DView + setActiveView + zoomToFit
8. Optional verification

Uses coordinate-based wall lookup (_find_wall_id_at) from revit_bridge.py.
"""

import sys
from typing import Dict, Any, Optional, List

# Import RevitClient
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/pipelines")
from revit_client import RevitClient, get_active_client

from .wall_model import WallPlan, Wall, Opening


# Default door type IDs from Residential-Default.rte template
DEFAULT_FRONT_DOOR_TYPE = 50865     # Single-Flush 36" x 84"
DEFAULT_INTERIOR_DOOR_TYPE = 50873  # Single-Flush 30" x 80"


def _revit_call(client: RevitClient, method: str, params: dict,
                label: str = "", verbose: bool = True) -> Optional[dict]:
    """Call Revit MCP method with logging."""
    tag = label or method
    if verbose:
        print(f"  [REVIT] {tag}...")
    result = client.call(method, params)
    if result.success:
        if verbose:
            print(f"  [REVIT] {tag} OK")
        return result.data
    else:
        if verbose:
            print(f"  [REVIT] {tag} FAILED: {result.error}")
        return None


def _find_wall_id_at(registry: List[dict], x: float, y: float,
                     tol: float = 2.0) -> Optional[int]:
    """Find the wall ID that passes through or near point (x, y).

    Uses point-to-segment distance against all registry entries.
    Direct port of replicate_edrawmax_plan.py's find_wall_id_at().
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


def _find_level_id(client: RevitClient, verbose: bool = True) -> Optional[int]:
    """Find ground floor level ID."""
    levels = _revit_call(client, "getLevels", {}, "Get levels", verbose)
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


def _find_wall_type_ids(client: RevitClient, verbose: bool = True) -> Dict[str, Optional[int]]:
    """Find exterior (8") and interior (4") wall type IDs."""
    result = {"exterior": None, "interior": None}

    types_data = _revit_call(client, "getWallTypes", {}, "Get wall types", verbose)
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

        if result["exterior"] is None:
            if "exterior" in name or '8"' in name or "8 inch" in name:
                result["exterior"] = type_id

        if result["interior"] is None:
            if "interior" in name or '4"' in name or "4 inch" in name or '5"' in name:
                result["interior"] = type_id

    return result


def _find_door_types(client: RevitClient, verbose: bool = True) -> Dict[str, Optional[int]]:
    """Find available door type IDs dynamically."""
    result = {"entry": DEFAULT_FRONT_DOOR_TYPE, "interior": DEFAULT_INTERIOR_DOOR_TYPE}

    types_data = _revit_call(client, "getDoorTypes", {}, "Get door types", verbose)
    if not types_data:
        return result

    type_list = []
    if isinstance(types_data, list):
        type_list = types_data
    elif "doorTypes" in types_data:
        type_list = types_data["doorTypes"]
    elif "data" in types_data:
        type_list = types_data["data"] if isinstance(types_data["data"], list) else []

    for dt in type_list:
        name = str(dt.get("name", "")).lower()
        type_id = dt.get("id") or dt.get("typeId")
        if type_id is None:
            continue

        if "36" in name or "entry" in name or "exterior" in name:
            result["entry"] = type_id
        elif "30" in name or "interior" in name:
            result["interior"] = type_id

    return result


def build_wall_registry(walls: List[Wall], batch_result: dict,
                        is_exterior: bool) -> List[dict]:
    """Build wall ID registry from batch create result.

    Maps each Revit wall ID back to its coordinate pair for
    subsequent door/window placement via _find_wall_id_at.
    """
    registry = []
    created = batch_result.get("createdWalls", [])
    for i, wid_data in enumerate(created):
        if i >= len(walls):
            break
        w = walls[i]
        wid = wid_data.get("wallId") or wid_data.get("elementId") if isinstance(wid_data, dict) else wid_data
        registry.append({
            "wallId": wid,
            "x1": w.x1, "y1": w.y1, "x2": w.x2, "y2": w.y2,
            "is_exterior": is_exterior,
        })
    return registry


def execute_wall_plan(
    plan: WallPlan,
    client: Optional[RevitClient] = None,
    level_id: Optional[int] = None,
    verify: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Execute a WallPlan in Revit via MCP.

    This is the primary execution function for the wall-first engine.
    Follows the proven pattern from replicate_edrawmax_plan.py.

    Args:
        plan: The WallPlan to build
        client: RevitClient instance (auto-detects if None)
        level_id: Level ID to build on (auto-detects if None)
        verify: After creation, query Revit to verify counts
        verbose: Print progress

    Returns:
        Dict with created element IDs, wall registry, and status
    """
    # Auto-detect client
    if client is None:
        client = get_active_client(verbose=verbose)
        if client is None:
            return {"success": False, "error": "No Revit MCP connection available"}

    # Auto-detect level
    if level_id is None:
        level_id = _find_level_id(client, verbose)
        if level_id is None:
            return {"success": False, "error": "Could not find Level 1"}

    wall_height = plan.wall_height_ft

    if verbose:
        n_ext = len(plan.exterior_walls)
        n_int = len(plan.interior_walls)
        print(f"\n{'='*50}")
        print(f"WALL PLAN → REVIT")
        if plan.overall_width_ft and plan.overall_depth_ft:
            print(f"  {plan.overall_width_ft}' x {plan.overall_depth_ft}'")
        print(f"  {n_ext} exterior + {n_int} interior walls")
        print(f"  {len(plan.doors)} doors, {len(plan.windows)} windows")
        print(f"  {len(plan.rooms)} rooms")
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
        "skipped_doors": [],
        "skipped_windows": [],
    }

    # Try to find wall type IDs
    wall_type_ids = _find_wall_type_ids(client, verbose)

    # ── Step 1: Create Exterior Walls ──
    ext_walls = plan.exterior_walls
    if ext_walls:
        ext_walls_data = []
        for w in ext_walls:
            h = w.height_ft if w.height_ft else wall_height
            wall_data = {
                "startPoint": [w.x1, w.y1, 0],
                "endPoint": [w.x2, w.y2, 0],
                "levelId": level_id,
                "height": h,
            }
            if wall_type_ids["exterior"]:
                wall_data["wallTypeId"] = wall_type_ids["exterior"]
            ext_walls_data.append(wall_data)

        ext_result = _revit_call(client, "batchCreateWalls", {
            "walls": ext_walls_data
        }, f"Exterior walls ({len(ext_walls_data)})", verbose)

        if ext_result:
            registry = build_wall_registry(ext_walls, ext_result, True)
            result["exterior_walls"] = ext_result.get("createdWalls", [])
            result["wall_id_registry"].extend(registry)
            if verbose:
                print(f"  Created {len(registry)} exterior walls")

    # ── Step 2: Create Interior Walls ──
    int_walls = plan.interior_walls
    if int_walls:
        int_walls_data = []
        for w in int_walls:
            h = w.height_ft if w.height_ft else wall_height
            wall_data = {
                "startPoint": [w.x1, w.y1, 0],
                "endPoint": [w.x2, w.y2, 0],
                "levelId": level_id,
                "height": h,
            }
            if wall_type_ids["interior"]:
                wall_data["wallTypeId"] = wall_type_ids["interior"]
            int_walls_data.append(wall_data)

        int_result = _revit_call(client, "batchCreateWalls", {
            "walls": int_walls_data
        }, f"Interior walls ({len(int_walls_data)})", verbose)

        if int_result:
            registry = build_wall_registry(int_walls, int_result, False)
            result["interior_walls"] = int_result.get("createdWalls", [])
            result["wall_id_registry"].extend(registry)
            if verbose:
                print(f"  Created {len(registry)} interior walls")

    # Zoom to fit after walls
    _revit_call(client, "zoomToFit", {}, "Zoom to fit", verbose)

    # ── Step 3: Place Doors ──
    wall_registry = result["wall_id_registry"]

    # Try to find door types dynamically
    door_types = _find_door_types(client, verbose)

    for door in plan.doors:
        wall = plan.wall_by_id(door.wall_id)
        if wall is None:
            if verbose:
                print(f"  [SKIP] Door {door.id}: wall {door.wall_id} not found in plan")
            result["skipped_doors"].append(door.id)
            continue

        # Resolve absolute position
        x, y = door.resolve_position(wall)

        # Find the Revit wall ID at this position
        revit_wall_id = _find_wall_id_at(wall_registry, x, y)
        if revit_wall_id is None:
            if verbose:
                print(f"  [SKIP] Door {door.id}: no Revit wall at ({x:.1f}, {y:.1f})")
            result["skipped_doors"].append(door.id)
            continue

        type_id = door_types["entry"] if door.is_entry else door_types["interior"]

        door_result = _revit_call(client, "placeDoor", {
            "wallId": revit_wall_id,
            "typeId": type_id,
            "location": [x, y, 0],
        }, f"Door {door.id} at ({x:.1f},{y:.1f})", verbose)

        if door_result:
            did = door_result.get("doorId") or door_result.get("elementId")
            if did:
                result["doors"].append(did)

    # ── Step 4: Place Windows ──
    for win in plan.windows:
        wall = plan.wall_by_id(win.wall_id)
        if wall is None:
            if verbose:
                print(f"  [SKIP] Window {win.id}: wall {win.wall_id} not found in plan")
            result["skipped_windows"].append(win.id)
            continue

        x, y = win.resolve_position(wall)

        revit_wall_id = _find_wall_id_at(wall_registry, x, y, tol=1.0)
        if revit_wall_id is None:
            if verbose:
                print(f"  [SKIP] Window {win.id}: no Revit wall at ({x:.1f}, {y:.1f})")
            result["skipped_windows"].append(win.id)
            continue

        win_result = _revit_call(client, "placeWindow", {
            "wallId": revit_wall_id,
            "location": [x, y, 0],
        }, f"Window {win.id} at ({x:.1f},{y:.1f})", verbose)

        if win_result:
            wid = win_result.get("windowId") or win_result.get("elementId")
            if wid:
                result["windows"].append(wid)

    # ── Step 5: Create Rooms ──
    for room in plan.rooms:
        room_result = _revit_call(client, "createRoom", {
            "levelId": level_id,
            "location": [room.center[0], room.center[1]],
            "name": room.name,
        }, f"Room: {room.name}", verbose)

        if room_result:
            rid = room_result.get("roomId") or room_result.get("elementId")
            if rid:
                result["rooms"].append(rid)

    # ── Step 6: 3D View ──
    view_3d = _revit_call(client, "create3DView", {
        "viewName": "WallPlan Engine 3D"
    }, "Create 3D view", verbose)

    if view_3d:
        vid = None
        if "result" in view_3d and isinstance(view_3d["result"], dict):
            vid = view_3d["result"].get("viewId")
        elif "viewId" in view_3d:
            vid = view_3d["viewId"]

        if vid is not None:
            result["view_3d"] = vid
            _revit_call(client, "setActiveView", {"viewId": int(vid)}, "Switch to 3D", verbose)
            _revit_call(client, "zoomToFit", {}, "Zoom 3D to fit", verbose)

    # ── Step 7: Verification ──
    if verify:
        result["verification"] = _verify(client, plan, result, verbose)

    # Summary
    if verbose:
        print(f"\n{'='*50}")
        print(f"REVIT EXECUTION COMPLETE")
        print(f"  Exterior walls: {len(result['exterior_walls'])}")
        print(f"  Interior walls: {len(result['interior_walls'])}")
        print(f"  Doors: {len(result['doors'])}")
        print(f"  Windows: {len(result['windows'])}")
        print(f"  Rooms: {len(result['rooms'])}")
        if result["skipped_doors"]:
            print(f"  Skipped doors: {result['skipped_doors']}")
        if result["skipped_windows"]:
            print(f"  Skipped windows: {result['skipped_windows']}")
        total = (len(result['exterior_walls']) + len(result['interior_walls']) +
                 len(result['doors']) + len(result['windows']) + len(result['rooms']))
        print(f"  Total elements: {total}")
        print(f"{'='*50}")

    return result


def _verify(client, plan, result, verbose):
    """Verify Revit element counts match expected counts."""
    verification = {"passed": True, "discrepancies": []}

    walls_data = _revit_call(client, "getWalls", {}, "Verify walls", verbose)
    if walls_data:
        wall_list = []
        if isinstance(walls_data, list):
            wall_list = walls_data
        elif "walls" in walls_data:
            wall_list = walls_data["walls"]
        elif "data" in walls_data:
            wall_list = walls_data["data"] if isinstance(walls_data["data"], list) else []

        expected = len(plan.walls)
        actual = len(wall_list)
        if actual != expected:
            verification["passed"] = False
            verification["discrepancies"].append(
                f"Walls: expected {expected}, got {actual}")

    expected_doors = len(plan.doors)
    actual_doors = len(result["doors"])
    if actual_doors != expected_doors:
        verification["passed"] = False
        verification["discrepancies"].append(
            f"Doors: expected {expected_doors}, placed {actual_doors}")

    expected_win = len(plan.windows)
    actual_win = len(result["windows"])
    if actual_win != expected_win:
        verification["passed"] = False
        verification["discrepancies"].append(
            f"Windows: expected {expected_win}, placed {actual_win}")

    return verification
