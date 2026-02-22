#!/usr/bin/env python3
"""
Voice-to-Revit Demo — Autonomous House Builder
================================================
Claude speaks a house design request aloud, then builds the entire
Revit model live — walls, rooms, doors, windows — all autonomous,
zero human intervention.

Target: 60-90 second video for X (@BIMOpsStudio)

Acts:
 1. Cold Open — voice command
 2. New Project + Levels
 3. Exterior Walls (40x30 ft rectangle)
 4. Interior Partitions (5 rooms)
 5. Doors (5 doors)
 6. Windows (5 windows on exterior)
 7. Rooms + 3D View + Closing

House Layout (40ft x 30ft = 1200 sqft):
    (0,30)────────(22,30)────────(40,30)
    │              │                   │
    │ Living Room  │  Master Bedroom   │
    │ (22x15)      │  (18x15)          │
    │              │                   │
    (0,15)────────(22,15)──────(40,15) │
    │              │                   │
    │ Kitchen      │  Bedroom 2        │
    │ (22x15)      │  (18x7)           │
    │              (22,8)──────(40,8)   │
    │              │  Bathroom (18x8)  │
    (0,0)─────────(22,0)──────(40,0)

Usage:  python3 demo_voice_to_revit.py
"""

import json
import subprocess
import sys
import time

# Add revit client path
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/pipelines")
from revit_client import RevitClient

# ═══════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════

OBS_HOST = "172.24.224.1"
OBS_PORT = 4455
OBS_PASSWORD = "2GwO1bvUqSIy3V2X"

# Center monitor (DISPLAY2) — DPI-aware virtual coordinates
CENTER_X = -2560
CENTER_Y = 0
CENTER_W = 2560
CENTER_H = 1440

PIPE_NAME = "RevitMCPBridge2026"

# Residential template — includes door/window families needed for demo
TEMPLATE_PATH = r"C:\ProgramData\Autodesk\RVT 2026\Templates\English-Imperial\Residential-Default.rte"

# Door type IDs from Residential template
FRONT_DOOR_TYPE = 50865   # Single-Flush 36" x 84"
INTERIOR_DOOR_TYPE = 50873  # Single-Flush 30" x 80"

_obs_cl = None
_class_counter = 0


# ═══════════════════════════════════════════
# CORE HELPERS
# ═══════════════════════════════════════════

def speak(text):
    """Narrate via TTS (Edge TTS -> Google TTS -> SAPI fallback)."""
    print(f"  [VOICE] {text[:90]}...")
    try:
        subprocess.run(
            ["python3", "/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py", text],
            timeout=120, capture_output=True
        )
    except Exception as e:
        print(f"  Voice error: {e}")


def pause(s=1.0):
    """Sleep for s seconds."""
    time.sleep(s)


def ps(cmd, timeout=30):
    """Run PowerShell command and return stdout."""
    try:
        r = subprocess.run(["powershell.exe", "-Command", cmd],
                           capture_output=True, text=True, timeout=timeout)
        if r.stderr.strip():
            print(f"  PS stderr: {r.stderr.strip()[:200]}")
        return r.stdout.strip()
    except Exception as e:
        print(f"  PS error: {e}")
        return ""


def unique_class():
    """Generate unique C# class name for Add-Type (avoids conflicts)."""
    global _class_counter
    _class_counter += 1
    return f"VR{_class_counter}"


# ═══════════════════════════════════════════
# REVIT CLIENT
# ═══════════════════════════════════════════

revit = RevitClient(PIPE_NAME, timeout_ms=30000, verbose=False)


def revit_call(method, params, label=""):
    """Call Revit MCP method. Logs result. Returns data dict or None on failure."""
    tag = label or method
    print(f"  [REVIT] {tag}...")
    result = revit.call(method, params)
    if result.success:
        print(f"  [REVIT] {tag} OK")
        return result.data
    else:
        print(f"  [REVIT] {tag} FAILED: {result.error}")
        return None


# ═══════════════════════════════════════════
# WINDOW MANAGEMENT
# ═══════════════════════════════════════════

def move_revit_to_center():
    """Move Revit window to center monitor using DPI-aware SetWindowPos."""
    cn = unique_class()
    result = ps(f"""
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class {cn} {{
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll", SetLastError=true)]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr after, int X, int Y, int cx, int cy, uint flags);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}}
'@
[{cn}]::SetProcessDPIAware()
$p = Get-Process -Name 'Revit' -EA SilentlyContinue | Where-Object {{$_.MainWindowTitle -ne ''}} | Select-Object -First 1
if($p) {{
    [{cn}]::ShowWindow($p.MainWindowHandle, 1)
    Start-Sleep -Milliseconds 200
    [{cn}]::SetWindowPos($p.MainWindowHandle, [IntPtr]::Zero, {CENTER_X}, {CENTER_Y}, {CENTER_W}, {CENTER_H}, 0x0004)
    Start-Sleep -Milliseconds 200
    [{cn}]::SetForegroundWindow($p.MainWindowHandle)
    Write-Output "MOVED"
}} else {{
    Write-Output "NOT_FOUND"
}}
""")
    if "MOVED" in result:
        print("  [WINDOW] Revit -> center monitor")
    else:
        print("  [WINDOW] WARNING: Could not find Revit window")


def minimize_others():
    """Minimize non-Revit windows to clean up desktop."""
    cn = unique_class()
    ps(f"""
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class {cn} {{ [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c); }}
'@
foreach ($name in @('POWERPNT','EXCEL','WINWORD','notepad','chrome','msedge','explorer','Telegram','Code')) {{
    Get-Process -Name $name -EA SilentlyContinue | ForEach-Object {{ [{cn}]::ShowWindow($_.MainWindowHandle, 6) | Out-Null }}
}}
""")


# ═══════════════════════════════════════════
# DATA EXTRACTION HELPERS
# ═══════════════════════════════════════════

def find_level_id(project_data, levels_data):
    """Extract ground floor level ID from createNewProject or getLevels response."""
    # Try from createNewProject response
    level_list = []
    if project_data and "levels" in project_data:
        level_list = project_data["levels"]

    # Try from getLevels response
    if not level_list and levels_data:
        if isinstance(levels_data, list):
            level_list = levels_data
        elif "levels" in levels_data:
            level_list = levels_data["levels"]
        elif "data" in levels_data:
            level_list = levels_data["data"] if isinstance(levels_data["data"], list) else []

    # Find ground floor by name or elevation
    ground_names = ["Level 1", "Level1", "First Floor", "Ground"]
    for lv in level_list:
        name = str(lv.get("name", ""))
        lid = lv.get("id") or lv.get("levelId")
        if any(gn in name for gn in ground_names):
            return lid

    # Fallback: lowest elevation
    if level_list:
        level_list.sort(key=lambda x: x.get("elevation", 999))
        return level_list[0].get("id") or level_list[0].get("levelId")

    return None


def find_floor_plan_view(views_data):
    """Find ground floor plan view ID from getViews response."""
    if not views_data:
        return None

    # Handle nested result.views format
    view_list = []
    if isinstance(views_data, list):
        view_list = views_data
    elif "result" in views_data and isinstance(views_data["result"], dict):
        view_list = views_data["result"].get("views", [])
    elif "views" in views_data:
        view_list = views_data["views"]
    elif "data" in views_data:
        view_list = views_data["data"] if isinstance(views_data["data"], list) else []

    ground_names = ["Level 1", "First Floor"]
    for v in view_list:
        name = str(v.get("name", ""))
        vtype = str(v.get("viewType", ""))
        if any(gn in name for gn in ground_names) and "Ceiling" not in name and vtype == "FloorPlan":
            return v.get("id") or v.get("viewId")

    # Fallback: first FloorPlan view
    for v in view_list:
        if str(v.get("viewType", "")) == "FloorPlan":
            return v.get("id") or v.get("viewId")

    return None


def get_wall_ids(batch_result):
    """Extract wall IDs list from batchCreateWalls response."""
    if not batch_result or "createdWalls" not in batch_result:
        return []
    return batch_result["createdWalls"]


# ════════════════════════════════════════════════════════════
# MAIN DEMO
# ════════════════════════════════════════════════════════════

def run_demo():
    global _obs_cl

    print("=" * 60)
    print("VOICE-TO-REVIT — AUTONOMOUS HOUSE BUILDER")
    print("  40x30 ft house | 5 rooms | ~90 seconds")
    print("=" * 60)

    # ── PRE-FLIGHT: Test Revit connection ──
    print("\n[PRE-FLIGHT] Testing Revit MCP connection...")
    if not revit.ping():
        print("  FATAL: Cannot reach RevitMCPBridge2026.")
        print("  Check: Revit running? MCP bridge loaded? Named pipe active?")
        return None
    print("  Revit MCP connected OK")

    # ── CONNECT OBS ──
    print("\n[OBS] Connecting to OBS WebSocket...")
    import obsws_python as obs
    cl = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD, timeout=5)
    _obs_cl = cl
    cl.set_current_program_scene("Screen 2")
    pause(1)
    print("  OBS connected — scene: Screen 2")

    # ── PREPARE DESKTOP ──
    print("\n[DESKTOP] Preparing clean desktop...")
    minimize_others()
    pause(1)
    move_revit_to_center()
    pause(2)

    # ── START RECORDING ──
    print("\n[OBS] Starting recording...")
    cl.start_record()
    pause(3)
    t0 = time.time()
    ts = lambda: f"[{int(time.time()-t0):3d}s]"

    # ══════════════════════════════════════════════════════════
    # ACT 1: COLD OPEN (~10s)
    # ══════════════════════════════════════════════════════════
    print(f"\n{ts()} >> ACT 1: Cold Open")
    speak(
        "Build me a twelve hundred square foot house. "
        "Two bedrooms, open kitchen, single story. Let's go."
    )
    pause(2)

    # ══════════════════════════════════════════════════════════
    # ACT 2: NEW PROJECT + LEVELS (~10s)
    # ══════════════════════════════════════════════════════════
    print(f"\n{ts()} >> ACT 2: New Project")

    # Create new project (try template first, falls back to blank)
    project = revit_call("createNewProject", {
        "templatePath": TEMPLATE_PATH,
        "projectName": "Demo House"
    }, "Create new project")
    pause(2)

    # Get levels (from project response or separate call)
    levels = revit_call("getLevels", {}, "Get levels")
    level_id = find_level_id(project, levels)
    if level_id is None:
        print("  FATAL: Could not find Level 1. Aborting.")
        cl.stop_record()
        cl.disconnect()
        return None
    print(f"  Level 1 ID: {level_id}")

    # Set active view to Level 1 floor plan
    views = revit_call("getViews", {"viewType": "FloorPlan"}, "Get floor plans")
    fp_view_id = find_floor_plan_view(views)
    if fp_view_id:
        revit_call("setActiveView", {"viewId": fp_view_id}, "Set Level 1 view")
    pause(1)

    speak("New project created. Level 1 floor plan. Starting with the exterior.")
    pause(1)

    # ══════════════════════════════════════════════════════════
    # ACT 3: EXTERIOR WALLS (~15s)
    # ══════════════════════════════════════════════════════════
    print(f"\n{ts()} >> ACT 3: Exterior Walls")

    ext_result = revit_call("batchCreateWalls", {
        "walls": [
            {"startPoint": [0,0,0], "endPoint": [40,0,0],  "levelId": level_id, "height": 10},  # South
            {"startPoint": [40,0,0], "endPoint": [40,30,0], "levelId": level_id, "height": 10},  # East
            {"startPoint": [40,30,0], "endPoint": [0,30,0], "levelId": level_id, "height": 10},  # North
            {"startPoint": [0,30,0], "endPoint": [0,0,0],   "levelId": level_id, "height": 10},  # West
        ]
    }, "Exterior walls (40x30)")

    ext_walls = get_wall_ids(ext_result)
    print(f"  Exterior walls created: {len(ext_walls)}")

    pause(1)
    revit_call("zoomToFit", {}, "Zoom to fit")
    pause(1)

    speak("Forty by thirty exterior. Twelve hundred square feet.")
    pause(2)

    # ══════════════════════════════════════════════════════════
    # ACT 4: INTERIOR PARTITIONS (~15s)
    # ══════════════════════════════════════════════════════════
    print(f"\n{ts()} >> ACT 4: Interior Partitions")

    int_result = revit_call("batchCreateWalls", {
        "walls": [
            # Vertical — splits house left/right
            {"startPoint": [22,0,0], "endPoint": [22,30,0],  "levelId": level_id, "height": 10},
            # Left horizontal — splits left into Living/Kitchen
            {"startPoint": [0,15,0], "endPoint": [22,15,0],  "levelId": level_id, "height": 10},
            # Right horizontal — splits right into Master/BR2
            {"startPoint": [22,15,0], "endPoint": [40,15,0], "levelId": level_id, "height": 10},
            # Bottom horizontal — splits right bottom into BR2/Bath
            {"startPoint": [22,8,0], "endPoint": [40,8,0],   "levelId": level_id, "height": 10},
        ]
    }, "Interior partitions")

    int_walls = get_wall_ids(int_result)
    print(f"  Interior walls created: {len(int_walls)}")

    pause(1)
    revit_call("zoomToFit", {}, "Zoom to fit")
    pause(1)

    speak(
        "Interior partitions. Open living and kitchen on the left. "
        "Two bedrooms and a bathroom on the right."
    )
    pause(2)

    # ══════════════════════════════════════════════════════════
    # ACT 5: DOORS (~15s)
    # ══════════════════════════════════════════════════════════
    print(f"\n{ts()} >> ACT 5: Doors")

    # Wall index map:
    #   ext: 0=South, 1=East, 2=North, 3=West
    #   int: 0=Vertical(x=22), 1=Left_H(y=15), 2=Right_H(y=15), 3=Bottom_H(y=8)
    door_specs = [
        # (wall_list, wall_index, location, typeId, label)
        (ext_walls,  0, [20, 0, 0],  FRONT_DOOR_TYPE,    "Front door"),
        (int_walls,  1, [11, 15, 0], INTERIOR_DOOR_TYPE,  "Kitchen to Living"),
        (int_walls,  0, [22, 22, 0], INTERIOR_DOOR_TYPE,  "Living to Master BR"),
        (int_walls,  0, [22, 11, 0], INTERIOR_DOOR_TYPE,  "Hall to Bedroom 2"),
        (int_walls,  3, [31, 8, 0],  INTERIOR_DOOR_TYPE,  "Hall to Bathroom"),
    ]

    placed_doors = 0
    for wall_list, idx, loc, type_id, label in door_specs:
        if idx < len(wall_list):
            wall_id = wall_list[idx].get("wallId")
            if wall_id is not None:
                r = revit_call("placeDoor", {
                    "wallId": wall_id,
                    "typeId": type_id,
                    "location": loc
                }, f"Door: {label}")
                if r and r.get("success", False) is not False:
                    placed_doors += 1
            else:
                print(f"  [SKIP] No wallId for {label}")
        else:
            print(f"  [SKIP] Wall index {idx} out of range for {label}")

    print(f"  Doors placed: {placed_doors}")
    revit_call("zoomToFit", {}, "Zoom to fit")
    pause(1)

    speak(
        "Five doors. Front entry, kitchen pass-through, "
        "master bedroom, second bedroom, bathroom."
    )
    pause(2)

    # ══════════════════════════════════════════════════════════
    # ACT 6: WINDOWS (~10s)
    # ══════════════════════════════════════════════════════════
    print(f"\n{ts()} >> ACT 6: Windows")

    window_specs = [
        # (wall_list, wall_index, location, label)
        (ext_walls, 0, [10, 0, 0],   "South - Kitchen"),
        (ext_walls, 0, [35, 0, 0],   "South - Entry"),
        (ext_walls, 2, [11, 30, 0],  "North - Living"),
        (ext_walls, 1, [40, 22, 0],  "East - Master BR"),
        (ext_walls, 3, [0, 7, 0],    "West - Kitchen"),
    ]

    placed_windows = 0
    for wall_list, idx, loc, label in window_specs:
        if idx < len(wall_list):
            wall_id = wall_list[idx].get("wallId")
            if wall_id is not None:
                r = revit_call("placeWindow", {
                    "wallId": wall_id,
                    "location": loc
                }, f"Window: {label}")
                if r and r.get("success", False) is not False:
                    placed_windows += 1
            else:
                print(f"  [SKIP] No wallId for {label}")
        else:
            print(f"  [SKIP] Wall index {idx} out of range for {label}")

    print(f"  Windows placed: {placed_windows}")
    revit_call("zoomToFit", {}, "Zoom to fit")
    pause(1)

    speak("Windows on every exterior wall. Natural light throughout.")
    pause(2)

    # ══════════════════════════════════════════════════════════
    # ACT 7: ROOMS + 3D VIEW + CLOSING (~25s)
    # ══════════════════════════════════════════════════════════
    print(f"\n{ts()} >> ACT 7: Rooms + 3D View")

    room_specs = [
        # (location [x,y], name)
        ([11, 22], "Living Room"),
        ([11, 7],  "Kitchen"),
        ([31, 22], "Master Bedroom"),
        ([31, 11], "Bedroom 2"),
        ([31, 4],  "Bathroom"),
    ]

    placed_rooms = 0
    for loc, name in room_specs:
        r = revit_call("createRoom", {
            "levelId": level_id,
            "location": loc,
            "name": name
        }, f"Room: {name}")
        if r:
            placed_rooms += 1

    print(f"  Rooms created: {placed_rooms}")
    pause(1)

    speak("Five rooms labeled. Now let's see it in 3D.")
    pause(2)

    # ── Create + switch to 3D view ──
    view_3d = revit_call("create3DView", {"viewName": "Demo 3D"}, "Create 3D view")
    if view_3d:
        # Handle both response formats: {result: {viewId}} and {viewId}
        vid = None
        if "result" in view_3d and isinstance(view_3d["result"], dict):
            vid = view_3d["result"].get("viewId")
        elif "viewId" in view_3d:
            vid = view_3d["viewId"]

        if vid is not None:
            revit_call("setActiveView", {"viewId": int(vid)}, "Switch to 3D")
            pause(2)
            revit_call("zoomToFit", {}, "Zoom 3D to fit")

    pause(4)  # Hold on 3D view — dramatic pause

    speak(
        "Voice command to finished model. Twelve hundred square feet. "
        "No human touched the keyboard. This is Cadre AI."
    )
    pause(5)

    # ══════════════════════════════════════════════════════════
    # WRAP UP
    # ══════════════════════════════════════════════════════════
    total = int(time.time() - t0)
    mins, secs = divmod(total, 60)
    print(f"\n\nDemo complete. Total time: {mins}:{secs:02d}")

    pause(3)

    print("Stopping OBS recording...")
    result = cl.stop_record()
    output_path = getattr(result, "output_path", "unknown")
    cl.disconnect()

    print(f"\nRecording saved: {output_path}")
    print("=" * 60)
    print("VOICE-TO-REVIT DEMO COMPLETE")
    print("=" * 60)
    return output_path


# ════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        path = run_demo()
        if path:
            print(f"\nVideo: {path}")
        else:
            print("\nDemo did not complete successfully.")
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        try:
            if _obs_cl:
                _obs_cl.stop_record()
                _obs_cl.disconnect()
                print("OBS recording stopped.")
        except Exception:
            pass
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        try:
            if _obs_cl:
                _obs_cl.stop_record()
                _obs_cl.disconnect()
                print("OBS recording stopped.")
        except Exception:
            pass
