#!/usr/bin/env python3
"""
Replicate the EdrawMax 1200 sqft floor plan in Revit.

This script creates an exact copy of the floor plan found at:
https://edrawmax.wondershare.com/templates/1200-sq-ft-floor-plan.html

The house is L-shaped with:
- Right wing (25' x 30'): Great Room, Dining, Kitchen, Bedroom 1, Bath 3
- Left wing (19' x 24'): Master Bedroom, Bedroom 2, Bath 1, Bath 2, Wardrobe

Origin (0,0) is at the bottom-right of the L's inner corner.
"""

import sys
import time
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/pipelines")
from revit_client import RevitClient

# ─── Configuration ───────────────────────────────────────────────────────────

WALL_HEIGHT = 10.0  # feet

# Door type IDs from Residential-Default.rte template
FRONT_DOOR_TYPE = 50865     # Single-Flush 36" x 84"
INTERIOR_DOOR_TYPE = 50873  # Single-Flush 30" x 80"

# ─── Room Definitions ────────────────────────────────────────────────────────
# Format: (name, x, y, width, height)
# Origin (0,0) at bottom-left of the full bounding box
# x goes right (east), y goes up (north)

# The L-shaped house:
# - Right wing: x=19 to x=44, y=0 to y=30
# - Left wing: x=0 to x=19, y=6 to y=30
# - Bottom-left (x=0-19, y=0-6) is covered porch (outside)

ROOMS = [
    # Right wing
    ("Great Room",      19,  0, 15, 19),
    ("Dining",          19, 19, 15, 11),
    ("Kitchen",         34, 19, 10, 11),
    ("Bedroom 1",       34,  7, 10, 12),
    ("Bath 3",          34,  0, 10,  7),

    # Left wing
    ("Bath 1",           0, 23,  8,  7),
    ("Bedroom 2",        8, 20, 11, 10),
    ("Bath 2",           0, 13,  8, 10),
    ("Master Bedroom",   8,  7, 11, 13),
    ("Wardrobe",         0,  6,  8,  7),
]

# ─── Wall Definitions ────────────────────────────────────────────────────────
# (x1, y1, x2, y2, is_exterior)

# Exterior walls — L-shaped perimeter (clockwise from bottom-right of right wing)
EXTERIOR_WALLS = [
    # Right wing south wall
    (19,  0, 44,  0),
    # East wall (full height)
    (44,  0, 44, 30),
    # North wall (full width)
    (44, 30,  0, 30),
    # West wall (left wing only — from top down to y=6)
    ( 0, 30,  0,  6),
    # Left wing south wall
    ( 0,  6, 19,  6),
    # Inner corner step-down (L notch)
    (19,  6, 19,  0),
]

# Interior walls
INTERIOR_WALLS = [
    # Wing divider: separates left wing from right wing (x=19, from y=6 to y=30)
    (19,  6, 19, 30),

    # RIGHT WING interior walls
    # Horizontal: Dining/Kitchen row above Great Room/Bedroom1 row
    (19, 19, 44, 19),
    # Vertical: Great Room/Dining (left) | Bedroom1/Kitchen/Bath3 (right)
    (34,  0, 34, 30),
    # Horizontal: Bath3 below Bedroom1
    (34,  7, 44,  7),

    # LEFT WING interior walls
    # Vertical: Bath column (x=0-8) | Bedroom column (x=8-19)
    ( 8,  6,  8, 30),
    # Horizontal: Bath1 / Bath2 divider
    ( 0, 23,  8, 23),
    # Horizontal: Bedroom2 / Master Bedroom divider
    ( 8, 20, 19, 20),
    # Horizontal: Bath2 / Wardrobe divider
    ( 0, 13,  8, 13),
    # Horizontal: Master Bedroom bottom (Master | entry area)
    ( 8,  7, 19,  7),
]

# ─── Door Definitions ────────────────────────────────────────────────────────
# (x, y, is_entry)
# Doors are placed at these coordinates on the nearest wall

DOORS = [
    # Entry door — south wall of left wing, centered on entry area
    (14,  6, True),

    # Master Bedroom — door from entry/hallway area (bottom of master)
    (14,  7, False),

    # Wardrobe — door from master bedroom side (east wall of wardrobe)
    ( 8, 10, False),

    # Bath 2 — door from master bedroom (east wall of bath 2)
    ( 8, 18, False),

    # Bath 1 — door from bedroom 2 (east wall of bath 1, near south end)
    ( 8, 24, False),

    # Bedroom 2 — door from hallway or from master bedroom area
    (14, 20, False),

    # Great Room to left wing — door through wing divider
    (19, 12, False),

    # Dining — opening from Great Room (might be open, but add a door)
    (26, 19, False),

    # Kitchen — from dining area
    (34, 24, False),

    # Bedroom 1 — from great room / hallway
    (34, 13, False),

    # Bath 3 — from bedroom 1 or great room
    (34,  3, False),
]

# ─── Window Definitions ──────────────────────────────────────────────────────
# (x, y) — placed on nearest exterior wall

WINDOWS = [
    # North wall windows
    ( 4, 30),   # Bath 1 window
    (14, 30),   # Bedroom 2 window
    (26, 30),   # Dining window
    (39, 30),   # Kitchen window

    # East wall windows
    (44, 24),   # Kitchen east window
    (44, 13),   # Bedroom 1 window
    (44,  3),   # Bath 3 window

    # South wall windows (right wing)
    (26,  0),   # Great Room south window
    (34,  0),   # Great Room south window (near corner)

    # West wall windows (left wing)
    ( 0, 26),   # Bath 1 west window
    ( 0, 18),   # Bath 2 west window
    ( 0,  9),   # Wardrobe west window
]


# ─── Helper Functions ─────────────────────────────────────────────────────────

def call_revit(client, method, params, label=""):
    """Call Revit MCP method with logging."""
    tag = label or method
    print(f"  [{tag}]...", end=" ", flush=True)
    result = client.call(method, params)
    if result.success:
        print("OK")
        return result.data
    else:
        print(f"FAILED: {result.error}")
        return None


def find_level_id(client):
    """Find ground floor level ID."""
    levels = call_revit(client, "getLevels", {}, "Get levels")
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


def find_wall_id_at(wall_ids_data, x, y, tol=2.0):
    """Find a wall ID that passes through or near point (x, y).

    wall_ids_data is list of dicts with wallId plus the wall coords we stored.
    """
    best = None
    best_dist = float('inf')

    for wd in wall_ids_data:
        x1, y1, x2, y2 = wd["x1"], wd["y1"], wd["x2"], wd["y2"]

        # Point-to-segment distance
        dx, dy = x2 - x1, y2 - y1
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq < 0.01:
            dist = ((x - x1)**2 + (y - y1)**2) ** 0.5
        else:
            t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / seg_len_sq))
            px, py = x1 + t * dx, y1 + t * dy
            dist = ((x - px)**2 + (y - py)**2) ** 0.5

        if dist < best_dist:
            best_dist = dist
            best = wd

    if best and best_dist <= tol:
        return best["wallId"]
    return None


# ─── Main Execution ──────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("REPLICATING EDRAWMAX 1200 SQFT FLOOR PLAN IN REVIT")
    print("=" * 60)

    # Connect
    client = RevitClient("RevitMCPBridge2026", timeout_ms=10000)
    if not client.ping():
        print("ERROR: Cannot connect to Revit MCP Bridge")
        return

    print("Connected to Revit 2026 MCP Bridge")

    # Get level
    level_id = find_level_id(client)
    if not level_id:
        print("ERROR: Cannot find Level 1")
        return
    print(f"Level ID: {level_id}")

    # ── Step 1: Create Exterior Walls ──
    print(f"\n--- EXTERIOR WALLS ({len(EXTERIOR_WALLS)}) ---")
    ext_walls_data = []
    for x1, y1, x2, y2 in EXTERIOR_WALLS:
        ext_walls_data.append({
            "startPoint": [x1, y1, 0],
            "endPoint": [x2, y2, 0],
            "levelId": level_id,
            "height": WALL_HEIGHT,
        })

    ext_result = call_revit(client, "batchCreateWalls", {
        "walls": ext_walls_data
    }, f"Exterior walls ({len(ext_walls_data)})")

    ext_wall_ids = []
    if ext_result and "createdWalls" in ext_result:
        for i, wid_data in enumerate(ext_result["createdWalls"]):
            wid = wid_data.get("wallId") or wid_data.get("elementId") if isinstance(wid_data, dict) else wid_data
            x1, y1, x2, y2 = EXTERIOR_WALLS[i]
            ext_wall_ids.append({
                "wallId": wid,
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "is_exterior": True,
            })
        print(f"  Created {len(ext_wall_ids)} exterior walls")

    # ── Step 2: Create Interior Walls ──
    print(f"\n--- INTERIOR WALLS ({len(INTERIOR_WALLS)}) ---")
    int_walls_data = []
    for x1, y1, x2, y2 in INTERIOR_WALLS:
        int_walls_data.append({
            "startPoint": [x1, y1, 0],
            "endPoint": [x2, y2, 0],
            "levelId": level_id,
            "height": WALL_HEIGHT,
        })

    int_result = call_revit(client, "batchCreateWalls", {
        "walls": int_walls_data
    }, f"Interior walls ({len(int_walls_data)})")

    int_wall_ids = []
    if int_result and "createdWalls" in int_result:
        for i, wid_data in enumerate(int_result["createdWalls"]):
            wid = wid_data.get("wallId") or wid_data.get("elementId") if isinstance(wid_data, dict) else wid_data
            x1, y1, x2, y2 = INTERIOR_WALLS[i]
            int_wall_ids.append({
                "wallId": wid,
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "is_exterior": False,
            })
        print(f"  Created {len(int_wall_ids)} interior walls")

    # All walls combined
    all_wall_ids = ext_wall_ids + int_wall_ids

    # Zoom to fit
    call_revit(client, "zoomToFit", {}, "Zoom to fit")

    # ── Step 3: Place Doors ──
    print(f"\n--- DOORS ({len(DOORS)}) ---")
    door_ids = []
    for dx, dy, is_entry in DOORS:
        wall_id = find_wall_id_at(all_wall_ids, dx, dy)
        if wall_id is None:
            print(f"  [SKIP] No wall found for door at ({dx}, {dy})")
            continue

        type_id = FRONT_DOOR_TYPE if is_entry else INTERIOR_DOOR_TYPE
        door_result = call_revit(client, "placeDoor", {
            "wallId": wall_id,
            "typeId": type_id,
            "location": [dx, dy, 0],
        }, f"Door at ({dx},{dy})")

        if door_result:
            did = door_result.get("doorId") or door_result.get("elementId")
            if did:
                door_ids.append(did)

    print(f"  Placed {len(door_ids)} doors")

    # ── Step 4: Place Windows ──
    print(f"\n--- WINDOWS ({len(WINDOWS)}) ---")
    window_ids = []
    for wx, wy in WINDOWS:
        wall_id = find_wall_id_at(all_wall_ids, wx, wy, tol=1.0)
        if wall_id is None:
            print(f"  [SKIP] No wall found for window at ({wx}, {wy})")
            continue

        win_result = call_revit(client, "placeWindow", {
            "wallId": wall_id,
            "location": [wx, wy, 0],
        }, f"Window at ({wx},{wy})")

        if win_result:
            wid = win_result.get("windowId") or win_result.get("elementId")
            if wid:
                window_ids.append(wid)

    print(f"  Placed {len(window_ids)} windows")

    # ── Step 5: Create Rooms ──
    print(f"\n--- ROOMS ({len(ROOMS)}) ---")
    room_ids = []
    for name, x, y, w, h in ROOMS:
        cx = x + w / 2
        cy = y + h / 2
        room_result = call_revit(client, "createRoom", {
            "levelId": level_id,
            "location": [cx, cy],
            "name": name,
        }, f"Room: {name}")

        if room_result:
            rid = room_result.get("roomId") or room_result.get("elementId")
            if rid:
                room_ids.append(rid)

    print(f"  Created {len(room_ids)} rooms")

    # ── Step 6: 3D View ──
    print(f"\n--- 3D VIEW ---")
    view_3d = call_revit(client, "create3DView", {
        "viewName": "EdrawMax Replication 3D"
    }, "Create 3D view")

    if view_3d:
        vid = None
        if "result" in view_3d and isinstance(view_3d["result"], dict):
            vid = view_3d["result"].get("viewId")
        elif "viewId" in view_3d:
            vid = view_3d["viewId"]

        if vid:
            call_revit(client, "setActiveView", {"viewId": int(vid)}, "Switch to 3D")
            call_revit(client, "zoomToFit", {}, "Zoom 3D to fit")

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"REPLICATION COMPLETE")
    print(f"  Exterior walls: {len(ext_wall_ids)}")
    print(f"  Interior walls: {len(int_wall_ids)}")
    print(f"  Doors: {len(door_ids)}")
    print(f"  Windows: {len(window_ids)}")
    print(f"  Rooms: {len(room_ids)}")
    total = len(ext_wall_ids) + len(int_wall_ids) + len(door_ids) + len(window_ids) + len(room_ids)
    print(f"  Total elements: {total}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
