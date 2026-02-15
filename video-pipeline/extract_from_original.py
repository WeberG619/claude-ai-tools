#!/usr/bin/env python3
"""
Extract all element data from the original 1700 West Sheffield Road project.

Connects to Revit via RevitMCPBridge2026, switches to the original project,
and extracts walls, doors, windows, rooms, sheets, and all available family types.

Saves to full_extraction.json for use by demo_revit_video.py (Take 2).

Usage:
    python3 extract_from_original.py [--verbose]
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "pipelines"))
from revit_client import RevitClient

PIPE_NAME = "RevitMCPBridge2026"
OUTPUT_FILE = Path(__file__).parent / "full_extraction.json"
ORIGINAL_PROJECT = "1700 West Sheffield Road"


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    client = RevitClient(PIPE_NAME, timeout_ms=15000, verbose=verbose)

    print("Testing connection to Revit MCP...")
    if not client.ping():
        print("ERROR: Cannot reach RevitMCPBridge2026. Is Revit running?")
        sys.exit(1)
    print("Connected.\n")

    # Switch to original project
    print(f"Switching to '{ORIGINAL_PROJECT}'...")
    switch = client.call("setActiveDocument", {"documentName": ORIGINAL_PROJECT})
    if not switch.success:
        print(f"ERROR: Could not switch to '{ORIGINAL_PROJECT}': {switch.error}")
        print("Make sure the project is open in Revit.")
        sys.exit(1)
    print(f"Active document: {ORIGINAL_PROJECT}\n")

    extraction = {
        "project_name": ORIGINAL_PROJECT,
        "extraction_date": datetime.now().isoformat(),
        "source": "RevitMCPBridge2026 live extraction",
    }

    # --- Extract Walls ---
    print("Extracting walls...")
    walls_result = client.call("getWalls", {})
    if walls_result.success:
        walls = walls_result.data.get("walls", [])
        extraction["walls"] = walls
        print(f"  {len(walls)} walls extracted")
    else:
        print(f"  FAILED: {walls_result.error}")
        extraction["walls"] = []

    # --- Extract Wall Types ---
    print("Extracting wall types...")
    wt_result = client.call("getWallTypes", {})
    if wt_result.success:
        wall_types = wt_result.data.get("wallTypes", [])
        extraction["wallTypes"] = wall_types
        print(f"  {len(wall_types)} wall types")
    else:
        extraction["wallTypes"] = []

    # --- Extract Doors ---
    print("Extracting doors...")
    doors_result = client.call("getDoors", {})
    if doors_result.success:
        doors = doors_result.data.get("doors", [])
        extraction["doors"] = doors
        print(f"  {len(doors)} doors extracted")
    else:
        print(f"  FAILED: {doors_result.error}")
        extraction["doors"] = []

    # --- Extract Door Types ---
    print("Extracting door types...")
    dt_result = client.call("getDoorTypes", {})
    if dt_result.success:
        door_types = dt_result.data.get("doorTypes", [])
        extraction["doorTypes"] = door_types
        print(f"  {len(door_types)} door types")
    else:
        extraction["doorTypes"] = []

    # --- Extract Windows ---
    print("Extracting windows...")
    windows_result = client.call("getWindows", {})
    if windows_result.success:
        windows = windows_result.data.get("windows", [])
        extraction["windows"] = windows
        print(f"  {len(windows)} windows extracted")
    else:
        print(f"  FAILED: {windows_result.error}")
        extraction["windows"] = []

    # --- Extract Window Types ---
    print("Extracting window types...")
    wwt_result = client.call("getWindowTypes", {})
    if wwt_result.success:
        window_types = wwt_result.data.get("windowTypes", [])
        extraction["windowTypes"] = window_types
        print(f"  {len(window_types)} window types")
    else:
        extraction["windowTypes"] = []

    # --- Extract Rooms ---
    print("Extracting rooms...")
    rooms_result = client.call("getRooms", {})
    if rooms_result.success:
        rooms = rooms_result.data.get("rooms", [])
        extraction["rooms"] = rooms
        print(f"  {len(rooms)} rooms extracted")
    else:
        extraction["rooms"] = []

    # --- Extract Sheets (for titleblock IDs) ---
    print("Extracting sheets...")
    sheets_result = client.call("getSheets", {})
    if sheets_result.success:
        sheets_data = sheets_result.data
        # Could be under "result" or directly
        if "result" in sheets_data:
            sheets = sheets_data["result"].get("sheets", [])
        else:
            sheets = sheets_data.get("sheets", [])
        extraction["sheets"] = sheets
        print(f"  {len(sheets)} sheets extracted")
        # Extract titleblock ID from first sheet
        if sheets:
            tb_id = sheets[0].get("titleblockId") or sheets[0].get("titleBlockId")
            tb_name = sheets[0].get("titleblockName") or sheets[0].get("titleBlockName", "")
            extraction["titleblockId"] = tb_id
            extraction["titleblockName"] = tb_name
            print(f"  Titleblock: {tb_name} (ID: {tb_id})")
    else:
        extraction["sheets"] = []

    # --- Extract Levels ---
    print("Extracting levels...")
    levels_result = client.call("getLevels", {})
    if levels_result.success:
        levels = levels_result.data.get("levels", [])
        extraction["levels"] = levels
        print(f"  {len(levels)} levels extracted")
    else:
        extraction["levels"] = []

    # --- Save ---
    print(f"\nSaving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(extraction, f, indent=2)

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"Saved ({size_kb:.1f} KB)")

    # --- Summary ---
    print("\n" + "=" * 50)
    print("EXTRACTION SUMMARY")
    print("=" * 50)
    print(f"  Walls:        {len(extraction.get('walls', []))}")
    print(f"  Wall Types:   {len(extraction.get('wallTypes', []))}")
    print(f"  Doors:        {len(extraction.get('doors', []))}")
    print(f"  Door Types:   {len(extraction.get('doorTypes', []))}")
    print(f"  Windows:      {len(extraction.get('windows', []))}")
    print(f"  Window Types: {len(extraction.get('windowTypes', []))}")
    print(f"  Rooms:        {len(extraction.get('rooms', []))}")
    print(f"  Sheets:       {len(extraction.get('sheets', []))}")
    print(f"  Levels:       {len(extraction.get('levels', []))}")
    if extraction.get("titleblockId"):
        print(f"  Titleblock:   {extraction['titleblockName']} (ID: {extraction['titleblockId']})")


if __name__ == "__main__":
    main()
