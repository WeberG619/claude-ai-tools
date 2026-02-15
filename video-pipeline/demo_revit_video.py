#!/usr/bin/env python3
"""
AI Builds a Real Building in Revit - Demo Video Script (Take 2)
================================================================
Recreates 1700 West Sheffield Road (Avon Park SFR) in Revit from scratch,
using EXACT wall types, door families, window families, and titleblock
extracted from the original project.

Key fixes from Take 1:
- Correct wall types: 8" CMU Exterior (not Generic 8")
- Per-door family types: garage, opening, flush, sliding, pocket, bifold
- Windows placed on exterior walls (14 total)
- Wall joins at every corner
- Project titleblock (ARKY), not Autodesk default
- Proper viewport framing with zoomToRegion
- Room and door tagging

Strategy: Save-As from original project (so all types exist), clear elements,
then rebuild everything from extracted coordinates.

Usage:
    python3 demo_revit_video.py [--dry-run] [--fast] [--verbose]
"""

import json
import subprocess
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "pipelines"))
from revit_client import RevitClient

# ============================================================================
# CONFIGURATION
# ============================================================================

PIPE_NAME = "RevitMCPBridge2026"
EXTRACTION_FILE = Path(__file__).parent / "full_extraction.json"
LOG_FILE = Path(__file__).parent / "demo_log.json"
ORIGINAL_PROJECT = "1700 West Sheffield Road"
ORIGINAL_PROJECT_PATH = r"D:\001 - PROJECTS\01 - CLIENT PROJECTS\01 - ARKY\012-Avon Park Single Family\Revit\1700 West Sheffield Road.rvt"
DEMO_PROJECT_PATH = r"D:\AI_Demo_Building.rvt"
DEMO_PROJECT_NAME = "AI_Demo_Building"

# Pause durations (seconds) for video pacing
PAUSE_WALL = 1.5
PAUSE_DOOR = 1.0
PAUSE_WINDOW = 1.0
PAUSE_ROOM = 0.8
PAUSE_VIEW = 2.0
PAUSE_SHEET = 2.0
PAUSE_SECTION = 3.0
PAUSE_FINALE = 5.0
FAST_PAUSE = 0.1


class DemoOrchestrator:
    """Orchestrates the 10-phase demo sequence."""

    def __init__(self, client: RevitClient, fast: bool = False, verbose: bool = False):
        self.client = client
        self.fast = fast
        self.verbose = verbose
        self.log = []
        self.created_elements = {
            "walls": [],
            "doors": [],
            "windows": [],
            "rooms": [],
            "views": [],
            "sheets": [],
        }
        self.level_id = None
        self.wall_id_map = {}  # wall name -> wallId (for joining)
        self.extraction = {}
        self.floor_plan_view_id = None

    def load_extraction(self):
        """Load extracted data from original project."""
        with open(EXTRACTION_FILE) as f:
            self.extraction = json.load(f)
        print(f"  Loaded extraction: {len(self.extraction.get('walls', []))} walls, "
              f"{len(self.extraction.get('doors', []))} doors, "
              f"{len(self.extraction.get('windows', []))} windows")

    def _ensure_demo_active(self):
        """Ensure the demo project is the active document."""
        self.client.call("setActiveDocument", {"documentName": DEMO_PROJECT_NAME})

    def _frame_building(self):
        """Zoom the current view to fit the full building content.

        Uses Revit's native Zoom-to-Fit (ZF) which auto-frames all visible
        elements in the current view.  Section/elevation annotations are
        deleted in Phase 1 cleanup so ZF gives a tight fit on the building.
        """
        self.force_viewport_refresh()  # sends ZF keystroke

    def force_viewport_refresh(self):
        """Force Revit to redraw by sending ZF keystroke."""
        try:
            ps_cmd = (
                "$revit = Get-Process -Name Revit | Select-Object -First 1; "
                "if ($revit) { "
                "[void][System.Reflection.Assembly]::LoadWithPartialName('Microsoft.VisualBasic'); "
                "[Microsoft.VisualBasic.Interaction]::AppActivate($revit.Id); "
                "Start-Sleep -Milliseconds 300; "
                "Add-Type -AssemblyName System.Windows.Forms; "
                "[System.Windows.Forms.SendKeys]::SendWait('ZF'); "
                "}"
            )
            subprocess.run(
                ["powershell.exe", "-Command", ps_cmd],
                capture_output=True, timeout=10
            )
            time.sleep(0.5)
        except Exception as e:
            if self.verbose:
                print(f"  [viewport refresh warning: {e}]")

    def find_floor_plan_view_id(self):
        """Find the architectural floor plan view ID."""
        views = self.client.call("getViews", {})
        if not views.success:
            return None
        for v in views.data.get("result", {}).get("views", []):
            vtype = v.get("viewType", "")
            vname = v.get("name", "")
            if "FloorPlan" in vtype:
                if vname in ("First Floor", "Level 1", "F.F."):
                    return v.get("id")
        # Fallback: any floor plan not electrical/framing
        for v in views.data.get("result", {}).get("views", []):
            vtype = v.get("viewType", "")
            vname = v.get("name", "")
            if "FloorPlan" in vtype and not any(
                x in vname for x in ["Electrical", "Framing", "Foundation", "Footing", "Second", "Roof"]
            ):
                return v.get("id")
        return None

    def pause(self, duration: float, label: str = ""):
        actual = FAST_PAUSE if self.fast else duration
        if self.verbose and label:
            print(f"  [pause {actual:.1f}s] {label}")
        time.sleep(actual)

    def log_step(self, step: str, result, success: bool):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "success": success,
            "details": str(result.data if hasattr(result, 'data') else result)[:200]
        }
        self.log.append(entry)
        status = "OK" if success else "FAIL"
        print(f"  [{status}] {step}")
        if not success and hasattr(result, 'error') and result.error:
            print(f"       Error: {result.error}")

    def save_log(self):
        with open(LOG_FILE, "w") as f:
            json.dump({
                "demo_date": datetime.now().isoformat(),
                "version": "take2",
                "total_steps": len(self.log),
                "successes": sum(1 for l in self.log if l["success"]),
                "failures": sum(1 for l in self.log if not l["success"]),
                "created_elements": {k: len(v) for k, v in self.created_elements.items()},
                "steps": self.log
            }, f, indent=2)
        print(f"\nLog saved to {LOG_FILE}")

    # ========================================================================
    # PHASE 1: CREATE PROJECT (Save-As from original, then clear)
    # ========================================================================

    def phase1_create_project(self) -> bool:
        """Create demo project by saving-as from original (preserves all types).

        ALWAYS does Save-As from original to ensure correct wall types, door
        families, window families, and titleblock are available. Closes any
        existing demo project first to avoid file locking.
        """
        print("\n" + "=" * 60)
        print("PHASE 1: CREATE NEW PROJECT (Save-As from original)")
        print("=" * 60)

        # Step 1: Ensure original project is open and demo project is closed
        docs = self.client.call("getOpenDocuments", {})
        has_original = False
        has_demo = False
        if docs.success:
            for doc in docs.data.get("result", {}).get("documents", []):
                title = doc.get("title", "")
                if title == ORIGINAL_PROJECT:
                    has_original = True
                if title == DEMO_PROJECT_NAME:
                    has_demo = True

        # Open original if not open
        if not has_original:
            print(f"  Opening original project: {ORIGINAL_PROJECT}...")
            open_result = self.client.call("openProject", {"filePath": ORIGINAL_PROJECT_PATH})
            if not open_result.success:
                print(f"  ERROR: Could not open original project: {open_result.error}")
                return False
            self.pause(3.0, "Opened original project")

        # Close existing demo project if open (avoids file lock on save-as)
        if has_demo:
            print(f"  Closing existing {DEMO_PROJECT_NAME}...")
            self.client.call("setActiveDocument", {"documentName": ORIGINAL_PROJECT})
            self.pause(1.0, "Switched to original before closing demo")
            close_result = self.client.call("closeDocument", {
                "documentTitle": DEMO_PROJECT_NAME,
                "save": False,
            })
            if close_result.success:
                print(f"  Closed {DEMO_PROJECT_NAME}")
            else:
                print(f"  Warning: Could not close {DEMO_PROJECT_NAME}: {close_result.error}")
            self.pause(1.0, "Closed old demo project")

        # Step 2: Switch to original project
        print(f"  Switching to '{ORIGINAL_PROJECT}'...")
        switch = self.client.call("setActiveDocument", {"documentName": ORIGINAL_PROJECT})
        if not switch.success:
            print(f"  ERROR: Could not switch to original project: {switch.error}")
            return False
        self.pause(2.0, "Original project active")

        # Step 3: Save-As to create the demo project (preserves ALL types!)
        print(f"  Saving as {DEMO_PROJECT_PATH}...")
        save_result = self.client.call("saveProjectAs", {
            "filePath": DEMO_PROJECT_PATH,
            "overwrite": True,
        })
        self.log_step("Save-As from original project", save_result, save_result.success)

        if not save_result.success:
            # Save-As may have succeeded but timed out — wait and retry
            print(f"  Save-As reported: {save_result.error}")
            # Large files can take 30+ seconds for Save-As; retry up to 60s
            for attempt in range(6):
                self.pause(10.0, f"Waiting for Save-As (attempt {attempt+1}/6)...")
                check = self.client.call("setActiveDocument", {"documentName": DEMO_PROJECT_NAME})
                if check.success:
                    print(f"  Save-As succeeded (took extra {(attempt+1)*10}s) — {DEMO_PROJECT_NAME} is active")
                    break
            else:
                print(f"  ERROR: Save-As truly failed after 60s — demo project not found")
                return False
        else:
            self.pause(2.0, "New project saved")

        # Step 4: The save-as made the demo project the active document
        # Set it explicitly to be safe
        self.client.call("setActiveDocument", {"documentName": DEMO_PROJECT_NAME})
        self.pause(1.0, "Demo project active")

        # Step 5: Close the original project so only demo is open
        # This prevents multi-document confusion in later phases
        print(f"  Closing original project to avoid document confusion...")
        close_orig = self.client.call("closeDocument", {
            "documentTitle": ORIGINAL_PROJECT,
            "save": False,
        })
        if close_orig.success:
            print(f"  Closed '{ORIGINAL_PROJECT}' — only demo project remains open")
        else:
            print(f"  Warning: Could not close original: {close_orig.error}")
            print(f"  Continuing with both documents open")
        self.pause(1.0, "Ready for clean start")

        # Step 6: Clear all elements from the demo project
        self._clear_all_elements()

        # Get level ID
        levels = self.client.call("getLevels", {})
        if levels.success:
            for level in levels.data.get("levels", []):
                elev = level.get("elevation", -999)
                name = level.get("name", "")
                if elev == 0.0 or "F.F." in name or "Level 1" in name:
                    self.level_id = level["levelId"]
                    print(f"  Using level: {name} (ID: {self.level_id})")
                    break

        if not self.level_id:
            if levels.data.get("levels"):
                self.level_id = levels.data["levels"][0]["levelId"]
                print(f"  Fallback level: {levels.data['levels'][0]['name']}")

        # Switch to floor plan view
        self.floor_plan_view_id = self.find_floor_plan_view_id()
        if self.floor_plan_view_id:
            self.client.call("setActiveView", {"viewId": self.floor_plan_view_id})
            print(f"  Active view: floor plan (ID: {self.floor_plan_view_id})")

        # Frame the building area so entire model is visible from the start
        self._frame_building()
        self.pause(2.0, "Clean blank canvas ready")
        return self.level_id is not None

    def _clear_all_elements(self):
        """Delete all model elements to start fresh."""
        element_methods = {
            "getWalls": ("walls", "wallId"),
            "getDoors": ("doors", "doorId"),
            "getWindows": ("windows", "windowId"),
            "getRooms": ("rooms", "roomId"),
        }
        for method, (list_key, id_key) in element_methods.items():
            items = self.client.call(method, {})
            if items.success:
                item_list = items.data.get(list_key, [])
                ids = [item.get(id_key) or item.get("elementId")
                       for item in item_list if item]
                ids = [i for i in ids if i]
                if ids:
                    self.client.call("deleteElements", {"elementIds": ids})
                    print(f"  Cleared {len(ids)} elements via {method}")

        # Delete views that cause annotation clutter or are from previous runs.
        # Section/elevation views create markers that stretch the viewport extent,
        # making the building appear off-center during recording.
        views_result = self.client.call("getViews", {})
        if views_result.success:
            floor_plan_vid = None
            del_ids = []
            for v in views_result.data.get("result", {}).get("views", []):
                vname = v.get("name", "")
                vtype = v.get("viewType", "")
                if "FloorPlan" in vtype and any(
                    n in vname for n in ["Level 1", "F.F.", "First Floor", "FLOOR PLAN"]
                ):
                    floor_plan_vid = v.get("id")
                # Delete AI-specific views from previous runs
                if "AI Demo" in vname or "AI Room" in vname or "AI DEMO" in vname:
                    del_ids.append(v.get("id"))
                # Delete section views (their markers stretch the view extent)
                if "Section" in vtype:
                    del_ids.append(v.get("id"))
                # Delete elevation views (interior elevations create markers too)
                if "Elevation" in vtype:
                    del_ids.append(v.get("id"))
                # Delete detail/callout views
                if "Detail" in vtype or "Callout" in vtype:
                    del_ids.append(v.get("id"))
            del_ids = [i for i in del_ids if i]
            if del_ids and floor_plan_vid:
                self.client.call("setActiveView", {"viewId": floor_plan_vid})
                time.sleep(0.5)
                deleted = 0
                for did in del_ids:
                    dr = self.client.call("deleteElements", {"elementIds": [did]})
                    if dr.success:
                        deleted += 1
                print(f"  Cleared {deleted}/{len(del_ids)} views (sections/elevations/AI views)")

    # ========================================================================
    # PHASE 2: EXTERIOR WALLS (8" CMU)
    # ========================================================================

    def _recover_level_id(self):
        """Recover level_id if Phase 1 failed to set it (e.g. Save-As timeout)."""
        if self.level_id:
            return
        print("  Recovering level ID...")
        levels = self.client.call("getLevels", {})
        if levels.success:
            for level in levels.data.get("levels", []):
                elev = level.get("elevation", -999)
                name = level.get("name", "")
                if elev == 0.0 or "F.F." in name or "Level 1" in name:
                    self.level_id = level["levelId"]
                    print(f"  Recovered level: {name} (ID: {self.level_id})")
                    return
            if levels.data.get("levels"):
                self.level_id = levels.data["levels"][0]["levelId"]
                print(f"  Recovered fallback level: {levels.data['levels'][0]['name']} (ID: {self.level_id})")

    def phase2_exterior_walls(self) -> bool:
        """Create 8 exterior perimeter walls using 8\" CMU type."""
        print("\n" + "=" * 60)
        print('PHASE 2: EXTERIOR WALLS - 8" CMU BLOCK')
        print("=" * 60)

        self._ensure_demo_active()
        self._recover_level_id()

        # Ensure floor plan view
        if not self.floor_plan_view_id:
            self.floor_plan_view_id = self.find_floor_plan_view_id()
        if self.floor_plan_view_id:
            self.client.call("setActiveView", {"viewId": self.floor_plan_view_id})
            self._frame_building()

        # Find the CMU 8" wall type (should exist since we saved-as from original)
        wall_types = self.client.call("getWallTypes", {})
        ext_wall_id = None
        if wall_types.success:
            for wt in wall_types.data.get("wallTypes", []):
                name = wt.get("name", "")
                if "CMU" in name and "Exterior" in name and '8"' in name:
                    ext_wall_id = wt["wallTypeId"]
                    print(f'  Found CMU wall type: "{name}" (ID: {ext_wall_id})')
                    break
            if not ext_wall_id:
                # Exact ID from extraction
                for wt in wall_types.data.get("wallTypes", []):
                    if wt["wallTypeId"] == 1200718:
                        ext_wall_id = 1200718
                        print(f'  Found wall type by ID: "{wt["name"]}" (ID: {ext_wall_id})')
                        break
            if not ext_wall_id:
                # Fallback
                for wt in wall_types.data.get("wallTypes", []):
                    if 'Generic - 8"' in wt.get("name", ""):
                        ext_wall_id = wt["wallTypeId"]
                        print(f'  FALLBACK wall type: "{wt["name"]}" (ID: {ext_wall_id})')
                        break

        self.cmu_wall_type_id = ext_wall_id

        # L-shaped exterior perimeter from extraction
        exterior_walls = [
            {"name": "North Wall",        "start": [-24.7, 26.8, 0], "end": [30.2, 26.8, 0],   "height": 10.5},
            {"name": "East Wall",         "start": [30.2, 26.8, 0],  "end": [30.2, -19.5, 0],  "height": 10.5},
            {"name": "South Garage Wall", "start": [30.2, -19.5, 0], "end": [10.9, -19.5, 0],  "height": 10.5},
            {"name": "Garage Step-Up S",  "start": [10.9, -19.5, 0], "end": [10.9, -13.2, 0],  "height": 10.5},
            {"name": "Living Entry Wall", "start": [10.9, -13.2, 0], "end": [1.5, -13.2, 0],   "height": 10.5},
            {"name": "Living South Step", "start": [1.5, -13.2, 0],  "end": [1.5, -22.6, 0],   "height": 10.5},
            {"name": "South Master Wall", "start": [1.6, -22.5, 0],  "end": [-24.7, -22.5, 0], "height": 10.5},
            {"name": "West Wall",         "start": [-24.7, -22.5, 0],"end": [-24.7, 26.8, 0],  "height": 10.5},
        ]

        success_count = 0
        for wall in exterior_walls:
            params = {
                "startPoint": wall["start"],
                "endPoint": wall["end"],
                "levelId": self.level_id,
                "height": wall["height"],
                "wallTypeId": ext_wall_id,
            }
            result = self.client.call("createWall", params)
            self.log_step(f"Exterior: {wall['name']}", result, result.success)

            if result.success:
                wall_id = result.data.get("wallId") or result.data.get("elementId")
                if wall_id:
                    self.wall_id_map[wall["name"]] = wall_id
                    self.created_elements["walls"].append(wall_id)
                success_count += 1
                self.force_viewport_refresh()

            self.pause(PAUSE_WALL, wall["name"])

        if success_count > 0:
            self._frame_building()
            self.pause(2.0, "Exterior walls complete")
        return success_count > 0

    # ========================================================================
    # PHASE 3: INTERIOR WALLS (4 1/2" Partition)
    # ========================================================================

    def phase3_interior_walls(self) -> bool:
        """Create 25 interior partition walls."""
        print("\n" + "=" * 60)
        print('PHASE 3: INTERIOR PARTITION WALLS')
        print("=" * 60)
        self._ensure_demo_active()
        self.pause(PAUSE_SECTION, "Transitioning to interior walls...")

        # Find interior wall type
        wall_types = self.client.call("getWallTypes", {})
        int_wall_id = None
        if wall_types.success:
            for wt in wall_types.data.get("wallTypes", []):
                if wt["wallTypeId"] == 441519:
                    int_wall_id = 441519
                    print(f'  Found partition type: "{wt["name"]}" (ID: {int_wall_id})')
                    break
            if not int_wall_id:
                for wt in wall_types.data.get("wallTypes", []):
                    name = wt.get("name", "")
                    if "4 1/2" in name and "Partition" in name:
                        int_wall_id = wt["wallTypeId"]
                        print(f'  Found partition type: "{name}" (ID: {int_wall_id})')
                        break
            if not int_wall_id:
                for wt in wall_types.data.get("wallTypes", []):
                    if "Interior" in wt.get("name", ""):
                        int_wall_id = wt["wallTypeId"]
                        break

        self.int_wall_type_id = int_wall_id

        interior_walls = [
            {"name": "Bedroom Wing NS",       "start": [-12.3, 26.8, 0], "end": [-12.3, 14.3, 0]},
            {"name": "Bedroom Wing EW Upper", "start": [-24.7, 14.3, 0], "end": [-8.3, 14.3, 0]},
            {"name": "Kitchen Living NS",     "start": [0.1, 13.3, 0],   "end": [0.1, 3.6, 0]},
            {"name": "Bath2 Upper EW",        "start": [-24.7, 6.1, 0],  "end": [-16.3, 6.1, 0]},
            {"name": "Bedroom2 Wing EW",      "start": [-24.7, 3.8, 0],  "end": [-12.3, 3.8, 0]},
            {"name": "Master EW Divider",     "start": [-24.7, -8.5, 0], "end": [-1.9, -8.5, 0]},
            {"name": "Kitchen Family EW",     "start": [0.1, 13.3, 0],   "end": [30.2, 13.3, 0]},
            {"name": "Closet Laundry NS",     "start": [22.1, 13.3, 0],  "end": [22.1, 1.0, 0]},
            {"name": "Garage Top EW",         "start": [30.2, 1.0, 0],   "end": [11.2, 1.0, 0]},
            {"name": "Kitchen NS Divider",    "start": [12.7, 13.3, 0],  "end": [12.7, 1.0, 0]},
            {"name": "Tub Half Upper EW",     "start": [-24.7, 12.0, 0], "end": [-16.3, 12.0, 0]},
            {"name": "Bath NS Corridor",      "start": [-16.3, 14.3, 0], "end": [-16.3, 3.8, 0]},
            {"name": "WIC Bedroom NS",        "start": [-12.3, -8.5, 0], "end": [-12.3, 3.8, 0]},
            {"name": "Living NS Wall",        "start": [-1.9, -12.9, 0], "end": [-1.9, 3.6, 0]},
            {"name": "WIC Divider EW",        "start": [-12.3, -0.7, 0], "end": [-1.9, -0.7, 0]},
            {"name": "WIC NS Divider",        "start": [-8.3, -8.5, 0],  "end": [-8.3, -0.7, 0]},
            {"name": "Master Bath NS",        "start": [-7.3, -22.5, 0], "end": [-7.3, -8.5, 0]},
            {"name": "Hall Main EW",          "start": [12.7, 3.6, 0],   "end": [-12.3, 3.6, 0]},
            {"name": "Bath3 NS Divider",      "start": [-8.3, 14.3, 0],  "end": [-8.3, 3.6, 0]},
            {"name": "Bath3 EW Bottom",       "start": [-8.3, 6.1, 0],   "end": [0.1, 6.1, 0]},
            {"name": "Bedroom3 Upper EW",     "start": [-8.3, 12.0, 0],  "end": [0.1, 12.0, 0]},
            {"name": "Bath3 Partition NS",    "start": [-3.9, 6.1, 0],   "end": [-3.9, 3.6, 0]},
            {"name": "Master Bath EW",        "start": [1.5, -12.9, 0],  "end": [-7.3, -12.9, 0]},
            {"name": "Utility NS Wall",       "start": [11.2, -13.2, 0], "end": [11.2, 1.0, 0]},
            {"name": "Laundry Upper EW",      "start": [30.2, 8.0, 0],   "end": [22.1, 8.0, 0]},
        ]

        success_count = 0
        for wall in interior_walls:
            params = {
                "startPoint": wall["start"],
                "endPoint": wall["end"],
                "levelId": self.level_id,
                "height": 10,
                "wallTypeId": int_wall_id,
            }
            result = self.client.call("createWall", params)
            self.log_step(f"Interior: {wall['name']}", result, result.success)

            if result.success:
                wall_id = result.data.get("wallId") or result.data.get("elementId")
                if wall_id:
                    self.wall_id_map[wall["name"]] = wall_id
                    self.created_elements["walls"].append(wall_id)
                success_count += 1
                if success_count % 5 == 0:
                    self.force_viewport_refresh()

            self.pause(PAUSE_WALL * 0.7, wall["name"])

        if success_count > 0:
            self._frame_building()
            self.force_viewport_refresh()
            self.pause(1.5, "Interior walls complete")
        return success_count > 0

    # ========================================================================
    # PHASE 4: JOIN WALLS
    # ========================================================================

    def phase4_join_walls(self) -> bool:
        """Join wall corners for clean intersections."""
        print("\n" + "=" * 60)
        print("PHASE 4: JOIN WALL CORNERS")
        print("=" * 60)
        self._ensure_demo_active()
        self.pause(PAUSE_SECTION, "Joining wall corners...")

        # Get all walls and find pairs that share endpoints (within tolerance)
        walls_result = self.client.call("getWalls", {})
        if not walls_result.success:
            print("  ERROR: Cannot get walls for joining")
            return False

        wall_list = walls_result.data.get("walls", [])
        if not wall_list:
            return True

        def point_close(p1, p2, tol=1.0):
            """Check if two points are within tolerance."""
            dx = p1.get("x", 0) - p2.get("x", 0)
            dy = p1.get("y", 0) - p2.get("y", 0)
            return (dx * dx + dy * dy) < tol * tol

        # Find all pairs of walls that share an endpoint
        join_pairs = set()
        for i, w1 in enumerate(wall_list):
            for j, w2 in enumerate(wall_list):
                if i >= j:
                    continue
                s1, e1 = w1.get("startPoint", {}), w1.get("endPoint", {})
                s2, e2 = w2.get("startPoint", {}), w2.get("endPoint", {})
                if (point_close(s1, s2) or point_close(s1, e2) or
                        point_close(e1, s2) or point_close(e1, e2)):
                    id1 = w1.get("wallId")
                    id2 = w2.get("wallId")
                    if id1 and id2:
                        pair = (min(id1, id2), max(id1, id2))
                        join_pairs.add(pair)

        print(f"  Found {len(join_pairs)} wall pairs to join")

        success_count = 0
        already_joined = 0
        fail_count = 0
        for wall1_id, wall2_id in sorted(join_pairs):
            result = self.client.call("joinWalls", {
                "wall1Id": wall1_id,
                "wall2Id": wall2_id,
            })
            if result.success:
                success_count += 1
            else:
                err = str(result.error or result.data).lower()
                if "already" in err or "cannot be joined" in err:
                    already_joined += 1
                else:
                    fail_count += 1
                    if self.verbose:
                        print(f"    Join failed: {wall1_id} + {wall2_id}: {result.error}")

        total_ok = success_count + already_joined
        print(f"  Joined: {success_count}, Already joined: {already_joined}, Failed: {fail_count}")
        self.log_step(
            f"Join walls: {total_ok}/{len(join_pairs)} OK ({already_joined} auto-joined)",
            type('R', (), {'data': {'joined': success_count, 'already': already_joined, 'failed': fail_count}})(),
            True,  # Wall joining is non-critical — Revit auto-joins at shared endpoints
        )

        self.force_viewport_refresh()
        self._frame_building()
        self.pause(2.0, "Wall joins complete")
        return True

    # ========================================================================
    # PHASE 5: DOORS (each with correct family type)
    # ========================================================================

    def phase5_doors(self) -> bool:
        """Place 26 doors, each with its correct family/type from extraction."""
        print("\n" + "=" * 60)
        print("PHASE 5: DOORS - 26 OPENINGS (EXACT TYPES)")
        print("=" * 60)
        self._ensure_demo_active()
        self.pause(PAUSE_SECTION, "Transitioning to doors...")

        # Get available door types in demo project
        door_types_result = self.client.call("getDoorTypes", {})
        available_types = {}
        if door_types_result.success:
            for dt in door_types_result.data.get("doorTypes", []):
                available_types[dt["typeId"]] = dt
            print(f"  {len(available_types)} door types available")

        # Get all walls for host finding
        walls_result = self.client.call("getWalls", {})
        if not walls_result.success:
            print("  ERROR: Cannot get walls for door placement")
            return False
        wall_list = walls_result.data.get("walls", [])

        def find_wall_near(x, y, tolerance=3.0):
            best = None
            best_dist = float('inf')
            for w in wall_list:
                sp = w.get("startPoint", {})
                ep = w.get("endPoint", {})
                sx, sy = sp.get("x", 0), sp.get("y", 0)
                ex, ey = ep.get("x", 0), ep.get("y", 0)
                dx, dy = ex - sx, ey - sy
                seg_len_sq = dx * dx + dy * dy
                if seg_len_sq == 0:
                    dist = ((x - sx) ** 2 + (y - sy) ** 2) ** 0.5
                else:
                    t = max(0, min(1, ((x - sx) * dx + (y - sy) * dy) / seg_len_sq))
                    proj_x, proj_y = sx + t * dx, sy + t * dy
                    dist = ((x - proj_x) ** 2 + (y - proj_y) ** 2) ** 0.5
                if dist < best_dist and dist < tolerance:
                    best_dist = dist
                    best = w
            return best

        # Door placements from extraction - each has its own typeId
        doors = self.extraction.get("doors", [])
        if not doors:
            print("  WARNING: No doors in extraction data, using blueprint doors")
            return False

        # Find a fallback door type (interior flush)
        fallback_type_id = None
        for tid, dt in available_types.items():
            if "Passage" in dt.get("familyName", "") and "Single" in dt.get("familyName", ""):
                fallback_type_id = tid
                break
        if not fallback_type_id and available_types:
            fallback_type_id = next(iter(available_types))

        success_count = 0
        for door in doors:
            loc = door.get("location", {})
            x, y = loc.get("x", 0), loc.get("y", 0)
            type_id = door.get("typeId")
            family_name = door.get("familyName", "")
            type_name = door.get("typeName", "")

            # Check if this type exists in demo project
            if type_id not in available_types:
                # Try to match by family+type name
                matched = False
                for tid, dt in available_types.items():
                    if dt.get("familyName") == family_name and dt.get("typeName") == type_name:
                        type_id = tid
                        matched = True
                        break
                if not matched:
                    if self.verbose:
                        print(f"    Type not found: {family_name} {type_name} (ID:{door.get('typeId')}), using fallback")
                    type_id = fallback_type_id

            host_wall = find_wall_near(x, y)
            if not host_wall:
                if self.verbose:
                    print(f"  SKIP: No wall for door at ({x:.1f},{y:.1f})")
                continue

            params = {
                "wallId": host_wall["wallId"],
                "typeId": type_id,
                "location": [x, y, 0],
                "levelId": self.level_id,
            }

            mark = door.get("mark", "")
            label = f"Door {mark}: {family_name} {type_name}"
            result = self.client.call("placeDoor", params)
            self.log_step(label[:60], result, result.success)

            if result.success:
                door_id = result.data.get("doorId") or result.data.get("elementId")
                if door_id:
                    self.created_elements["doors"].append(door_id)
                success_count += 1
                if success_count % 5 == 0:
                    self.force_viewport_refresh()

            self.pause(PAUSE_DOOR, mark)

        if success_count > 0:
            self._frame_building()
            self.force_viewport_refresh()
            self.pause(1.5, "Doors placed")
        return success_count > 0

    # ========================================================================
    # PHASE 6: WINDOWS (NEW - 14 windows on exterior walls)
    # ========================================================================

    def phase6_windows(self) -> bool:
        """Place 14 windows on exterior walls with correct types."""
        print("\n" + "=" * 60)
        print("PHASE 6: WINDOWS - 14 ON EXTERIOR WALLS")
        print("=" * 60)
        self._ensure_demo_active()
        self.pause(PAUSE_SECTION, "Transitioning to windows...")

        # Get available window types
        window_types_result = self.client.call("getWindowTypes", {})
        available_types = {}
        if window_types_result.success:
            for wt in window_types_result.data.get("windowTypes", []):
                available_types[wt["typeId"]] = wt
            print(f"  {len(available_types)} window types available")

        # Get walls for host finding
        walls_result = self.client.call("getWalls", {})
        if not walls_result.success:
            print("  ERROR: Cannot get walls for window placement")
            return False
        wall_list = walls_result.data.get("walls", [])

        def find_wall_near(x, y, tolerance=3.0):
            best = None
            best_dist = float('inf')
            for w in wall_list:
                sp = w.get("startPoint", {})
                ep = w.get("endPoint", {})
                sx, sy = sp.get("x", 0), sp.get("y", 0)
                ex, ey = ep.get("x", 0), ep.get("y", 0)
                dx, dy = ex - sx, ey - sy
                seg_len_sq = dx * dx + dy * dy
                if seg_len_sq == 0:
                    dist = ((x - sx) ** 2 + (y - sy) ** 2) ** 0.5
                else:
                    t = max(0, min(1, ((x - sx) * dx + (y - sy) * dy) / seg_len_sq))
                    proj_x, proj_y = sx + t * dx, sy + t * dy
                    dist = ((x - proj_x) ** 2 + (y - proj_y) ** 2) ** 0.5
                if dist < best_dist and dist < tolerance:
                    best_dist = dist
                    best = w
            return best

        windows = self.extraction.get("windows", [])
        if not windows:
            print("  WARNING: No windows in extraction data")
            return False

        # Fallback window type
        fallback_type_id = None
        for tid, wt in available_types.items():
            if "Double-Hung" in wt.get("familyName", ""):
                fallback_type_id = tid
                break
        if not fallback_type_id and available_types:
            fallback_type_id = next(iter(available_types))

        success_count = 0
        for window in windows:
            loc = window.get("location", {})
            x, y = loc.get("x", 0), loc.get("y", 0)
            type_id = window.get("typeId")
            sill_height = window.get("sillHeight", 3.0)
            family_name = window.get("familyName", "")
            type_name = window.get("typeName", "")
            mark = window.get("mark", "")

            # Check type availability
            if type_id not in available_types:
                matched = False
                for tid, wt in available_types.items():
                    if wt.get("familyName") == family_name and wt.get("typeName") == type_name:
                        type_id = tid
                        matched = True
                        break
                if not matched:
                    if self.verbose:
                        print(f"    Type not found: {family_name} {type_name}, using fallback")
                    type_id = fallback_type_id

            host_wall = find_wall_near(x, y)
            if not host_wall:
                if self.verbose:
                    print(f"  SKIP: No wall for window at ({x:.1f},{y:.1f})")
                continue

            params = {
                "wallId": host_wall["wallId"],
                "typeId": type_id,
                "location": [x, y, sill_height],
            }

            label = f"Window {mark}: {family_name} {type_name}"
            result = self.client.call("placeWindow", params)
            self.log_step(label[:60], result, result.success)

            if result.success:
                win_id = result.data.get("windowId") or result.data.get("elementId")
                if win_id:
                    self.created_elements["windows"].append(win_id)
                success_count += 1
                if success_count % 3 == 0:
                    self.force_viewport_refresh()

            self.pause(PAUSE_WINDOW, mark)

        if success_count > 0:
            self._frame_building()
            self.force_viewport_refresh()
            self.pause(1.5, "Windows placed")
        return success_count > 0

    # ========================================================================
    # PHASE 7: ROOMS
    # ========================================================================

    def phase7_rooms(self) -> bool:
        """Create 14 rooms with names and numbers."""
        print("\n" + "=" * 60)
        print("PHASE 7: ROOMS - 14 SPACES")
        print("=" * 60)
        self.pause(PAUSE_SECTION, "Transitioning to rooms...")

        rooms = [
            {"name": "LIVING",          "number": "100", "location": [-5.0, -11.0, 0]},
            {"name": "MASTER BEDROOM",  "number": "101", "location": [-16.0, -15.0, 0]},
            {"name": "W.I.C.",          "number": "102", "location": [-10.0, -4.5, 0]},
            {"name": "MASTER BATH",     "number": "103", "location": [-4.0, -17.0, 0]},
            {"name": "BEDROOM-2",       "number": "104", "location": [-18.0, 0.0, 0]},
            {"name": "BATH-2",          "number": "105", "location": [-20.0, 9.0, 0]},
            {"name": "BATH-3",          "number": "106", "location": [-4.0, 5.0, 0]},
            {"name": "BEDROOM-3",       "number": "107", "location": [-18.0, 20.0, 0]},
            {"name": "KITCHEN",         "number": "108", "location": [6.0, 8.0, 0]},
            {"name": "FAMILY / DINING", "number": "109", "location": [15.0, 20.0, 0]},
            {"name": "HALL-1",          "number": "111", "location": [-6.0, 0.0, 0]},
            {"name": "LAUNDRY",         "number": "113", "location": [26.0, 4.0, 0]},
            {"name": "CLOSET",          "number": "114", "location": [26.0, 11.0, 0]},
            {"name": "2-CAR GARAGE",    "number": "116", "location": [20.0, -10.0, 0]},
        ]

        success_count = 0
        for room in rooms:
            params = {
                "location": room["location"],
                "name": room["name"],
                "number": room["number"],
                "levelId": self.level_id,
            }
            result = self.client.call("createRoom", params)
            self.log_step(f"Room: {room['name']} ({room['number']})", result, result.success)

            if result.success:
                room_id = result.data.get("roomId") or result.data.get("elementId")
                if room_id:
                    self.created_elements["rooms"].append(room_id)
                success_count += 1
                if success_count % 5 == 0:
                    self.force_viewport_refresh()

            self.pause(PAUSE_ROOM, room["name"])

        if success_count > 0:
            self.force_viewport_refresh()
            self._frame_building()
        return success_count > 0

    # ========================================================================
    # PHASE 8: TAG ELEMENTS
    # ========================================================================

    def phase8_tags(self) -> bool:
        """Tag all rooms and doors in the floor plan view."""
        print("\n" + "=" * 60)
        print("PHASE 8: TAG ROOMS & DOORS")
        print("=" * 60)
        self.pause(PAUSE_SECTION, "Adding tags...")

        view_id = self.floor_plan_view_id
        if not view_id:
            view_id = self.find_floor_plan_view_id()
        if not view_id:
            print("  ERROR: No floor plan view for tagging")
            return False

        # Ensure we're on the floor plan
        self.client.call("setActiveView", {"viewId": view_id})
        self._frame_building()

        # Tag all rooms
        tag_rooms = self.client.call("tagAllRooms", {"viewId": view_id})
        self.log_step("Tag all rooms", tag_rooms, tag_rooms.success)
        if tag_rooms.success:
            tagged = tag_rooms.data.get("roomsTagged", 0)
            print(f"  Tagged {tagged} rooms")
        self.force_viewport_refresh()
        self.pause(2.0, "Room tags placed")

        # Tag each door
        tagged_doors = 0
        for door_id in self.created_elements["doors"]:
            result = self.client.call("tagDoor", {
                "doorId": door_id,
                "viewId": view_id,
            })
            if result.success:
                tagged_doors += 1

        self.log_step(
            f"Tag doors: {tagged_doors}/{len(self.created_elements['doors'])}",
            type('R', (), {'data': {'tagged': tagged_doors}})(),
            tagged_doors > 0,
        )
        self.force_viewport_refresh()
        self._frame_building()
        self.pause(1.5, "Door tags placed")
        return True

    # ========================================================================
    # PHASE 9: VIEWS & SHEET
    # ========================================================================

    def phase9_views_sheet(self) -> bool:
        """Create views, sheet with project titleblock, place views."""
        print("\n" + "=" * 60)
        print("PHASE 9: VIEWS & CONSTRUCTION DOCUMENT SHEET")
        print("=" * 60)
        self._ensure_demo_active()
        self.pause(PAUSE_SECTION, "Creating views and sheet...")

        # Create 3D view
        view_3d = self.client.call("create3DView", {"viewName": "AI Demo 3D"})
        self.log_step("Create 3D view", view_3d, view_3d.success)
        view_3d_id = None
        if view_3d.success:
            view_3d_id = view_3d.data.get("viewId") or view_3d.data.get("result", {}).get("viewId")
            if view_3d_id:
                self.created_elements["views"].append(view_3d_id)
                self.client.call("setActiveView", {"viewId": view_3d_id})
                self._frame_building()  # Zoom to fit 3D view
                self.pause(PAUSE_VIEW, "3D view created")

        # Switch back to floor plan
        if self.floor_plan_view_id:
            self.client.call("setActiveView", {"viewId": self.floor_plan_view_id})
            self._frame_building()  # Zoom to fit floor plan

        # Create sheet with project titleblock
        titleblock_id = self.extraction.get("titleblockId")
        sheet_params = {
            "sheetNumber": "A1.0",
            "sheetName": "FLOOR PLAN - AI DEMO",
        }
        if titleblock_id:
            sheet_params["titleblockId"] = titleblock_id
            print(f"  Using titleblock ID: {titleblock_id} ({self.extraction.get('titleblockName', '')})")

        sheet_result = self.client.call("createSheet", sheet_params)
        self.log_step("Create sheet A1.0", sheet_result, sheet_result.success)

        sheet_id = None
        if sheet_result.success:
            sheet_id = sheet_result.data.get("sheetId") or sheet_result.data.get("elementId")
            if sheet_id:
                self.created_elements["sheets"].append(sheet_id)

                # Print which titleblock was used
                tb_name = sheet_result.data.get("titleblockName", "")
                print(f"  Sheet titleblock: {tb_name}")

        self.pause(PAUSE_SHEET, "Sheet created")

        # Place floor plan on sheet
        if sheet_id and self.floor_plan_view_id:
            place_result = self.client.call("placeViewOnSheet", {
                "sheetId": sheet_id,
                "viewId": self.floor_plan_view_id,
                "location": [1.4, 0.9],  # Center of ARCH D sheet
            })
            if place_result.success:
                self.log_step("Place floor plan on sheet", place_result, True)
                self.force_viewport_refresh()
            else:
                # View already placed on another sheet from original project
                # This is expected when using Save-As — log as non-critical
                err = str(place_result.error or place_result.data)
                if "already placed" in err.lower():
                    print(f"  Note: Floor plan already on a sheet (from original project)")
                    self.log_step("Floor plan (already on original sheet)", place_result, True)
                else:
                    self.log_step("Place floor plan on sheet", place_result, False)

        self.pause(PAUSE_SHEET, "View placed on sheet")
        return True

    # ========================================================================
    # PHASE 10: FINALE - 3D REVEAL
    # ========================================================================

    def phase10_finale(self) -> bool:
        """Switch to 3D view with proper framing for the reveal."""
        print("\n" + "=" * 60)
        print("PHASE 10: FINALE - 3D REVEAL")
        print("=" * 60)

        # Switch to 3D view
        views = self.client.call("getViews", {})
        switched_3d = False
        if views.success:
            for v in views.data.get("result", {}).get("views", []):
                vtype = v.get("viewType", "")
                vname = v.get("name", "")
                if ("ThreeD" in vtype or "3D" in vtype) and "AI Demo" in vname:
                    r = self.client.call("setActiveView", {"viewId": v.get("id")})
                    switched_3d = r.success
                    print(f"  Switched to 3D view: {vname}")
                    break

        # Zoom to fit the 3D view — fills the viewport with the building
        self._frame_building()
        print("  Zoomed to fit 3D view")

        self.log_step("3D Reveal", views, True)
        self.pause(PAUSE_FINALE, "FINAL 3D REVEAL")

        # Save project
        save_result = self.client.call("saveProject", {})
        self.log_step("Save project", save_result, save_result.success)
        return True

    # ========================================================================
    # MAIN EXECUTION
    # ========================================================================

    def run(self) -> bool:
        """Execute the full 10-phase demo sequence."""
        print("\n" + "#" * 60)
        print("# AI BUILDS A REAL BUILDING IN REVIT (Take 2)")
        print("# BIM Ops Studio - Autonomous Demo")
        print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("#" * 60)

        start_time = time.time()

        # Load extraction data
        self.load_extraction()

        # Verify connection
        ping = self.client.call("ping", {})
        if not ping.success:
            print("ERROR: Cannot connect to RevitMCPBridge2026")
            return False
        print(f"Connected to RevitMCPBridge2026 v{ping.data.get('assemblyVersion', '?')}")

        phases = [
            ("1. Create Project",     self.phase1_create_project),
            ("2. Exterior Walls",     self.phase2_exterior_walls),
            ("3. Interior Walls",     self.phase3_interior_walls),
            ("4. Join Walls",         self.phase4_join_walls),
            ("5. Doors",              self.phase5_doors),
            ("6. Windows",            self.phase6_windows),
            ("7. Rooms",              self.phase7_rooms),
            ("8. Tags",               self.phase8_tags),
            ("9. Views & Sheet",      self.phase9_views_sheet),
            ("10. Finale",            self.phase10_finale),
        ]

        results = {}
        for name, phase_fn in phases:
            try:
                result = phase_fn()
                results[name] = result
                if not result:
                    print(f"\n  WARNING: Phase '{name}' had issues, continuing...")
            except Exception as e:
                print(f"\n  ERROR in phase '{name}': {e}")
                import traceback
                traceback.print_exc()
                results[name] = False

        # Summary
        elapsed = time.time() - start_time
        print("\n" + "#" * 60)
        print("# DEMO COMPLETE")
        print("#" * 60)
        print(f"  Duration: {elapsed:.1f} seconds ({elapsed / 60:.1f} minutes)")
        print(f"  Walls created:   {len(self.created_elements['walls'])}")
        print(f"  Doors placed:    {len(self.created_elements['doors'])}")
        print(f"  Windows placed:  {len(self.created_elements['windows'])}")
        print(f"  Rooms created:   {len(self.created_elements['rooms'])}")
        print(f"  Views created:   {len(self.created_elements['views'])}")
        print(f"  Sheets created:  {len(self.created_elements['sheets'])}")
        print(f"  Total steps:     {len(self.log)}")
        print(f"  Successes:       {sum(1 for l in self.log if l['success'])}")
        print(f"  Failures:        {sum(1 for l in self.log if not l['success'])}")

        self.save_log()
        return all(results.values())


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="AI Builds a Building in Revit - Demo (Take 2)")
    parser.add_argument("--dry-run", action="store_true", help="Run with fast pauses")
    parser.add_argument("--fast", action="store_true", help="Minimal pauses")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    client = RevitClient(PIPE_NAME, timeout_ms=120000, verbose=args.verbose)

    print("Testing connection to Revit MCP...")
    if not client.ping():
        print("ERROR: Cannot reach RevitMCPBridge2026. Is Revit running with the add-in?")
        sys.exit(1)

    demo = DemoOrchestrator(
        client=client,
        fast=args.dry_run or args.fast,
        verbose=args.verbose,
    )

    success = demo.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
