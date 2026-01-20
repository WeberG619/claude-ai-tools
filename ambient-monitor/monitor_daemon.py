#!/usr/bin/env python3
"""
Ambient Revit Monitor Daemon
Polls Revit state, detects changes, surfaces insights via voice/queue.

Start conservative: 30-second polling, voice for unjoined walls only.
"""

import json
import time
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
import argparse

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))

from state_differ import RevitState, diff_states
from analysis_rules import analyze_changes, AnalysisResult
from output_handlers import speak_finding, queue_finding, alert_critical

# Configuration
DEFAULT_POLL_INTERVAL = 30  # seconds
LIVE_STATE_PATH = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")
PIPE_NAME_2026 = "RevitMCPBridge2026"
PIPE_NAME_2025 = "RevitMCPBridge2025"


def is_revit_active() -> tuple[bool, str]:
    """
    Check if Revit is the active window.
    Returns (is_active, pipe_name_to_use).
    """
    try:
        if not LIVE_STATE_PATH.exists():
            return False, ""

        with open(LIVE_STATE_PATH) as f:
            state = json.load(f)

        active_window = state.get("active_window", "")
        applications = state.get("applications", [])

        # Find Revit instances
        revit_apps = [app for app in applications if "Revit" in app.get("ProcessName", "")]

        if not revit_apps:
            return False, ""

        # Check which Revit is active
        for app in revit_apps:
            title = app.get("MainWindowTitle", "")
            if "2026" in title:
                # Check if Revit 2026 is in active window
                if "Revit" in active_window and "2026" in active_window:
                    return True, PIPE_NAME_2026
            elif "2025" in title:
                if "Revit" in active_window and "2025" in active_window:
                    return True, PIPE_NAME_2025

        # Revit is running but not active window
        return False, ""

    except Exception as e:
        print(f"[Monitor] Error checking Revit status: {e}", file=sys.stderr)
        return False, ""


def query_revit_state(pipe_name: str) -> Optional[RevitState]:
    """
    Query current Revit model state via MCP.
    Uses lightweight queries for fast polling.
    """
    try:
        # Query 1: Get active view info
        view_response = call_mcp(pipe_name, "getActiveView", {})
        if not view_response.get("success"):
            print(f"[Monitor] getActiveView failed: {view_response.get('error')}", file=sys.stderr)
            return None

        view_info = view_response.get("result", {})
        view_id = view_info.get("viewId") or view_info.get("id")
        view_name = view_info.get("viewName") or view_info.get("name", "")
        view_type = view_info.get("viewType", "")

        # Query 2: Get walls in current view
        walls_response = call_mcp(pipe_name, "getWallsInView", {"viewId": view_id})
        walls = []
        if walls_response.get("success"):
            result = walls_response.get("result", {})
            walls = result.get("walls", []) if isinstance(result, dict) else result

        # Query 3: Check for unjoined walls by examining wall info
        # Sample a few walls to check for gaps/unjoined ends
        unjoined_walls = []
        if walls and len(walls) <= 50:  # Only check if reasonable count
            for wall in walls[:10]:  # Sample first 10
                wall_id = wall.get("id") or wall.get("elementId")
                if wall_id:
                    info_response = call_mcp(pipe_name, "getWallInfo", {"wallId": wall_id})
                    if info_response.get("success"):
                        info = info_response.get("result", {})
                        # Check if wall has join issues (implementation depends on API response)
                        # For now, mark as unjoined if either end reports no connection
                        joins = info.get("joins", {})
                        if joins:
                            if not joins.get("startJoined", True) or not joins.get("endJoined", True):
                                unjoined_walls.append(wall_id)

        # Element counts
        element_counts = {
            "walls": len(walls),
        }

        return RevitState(
            timestamp=datetime.now(),
            view_id=view_id,
            view_name=view_name,
            view_type=view_type,
            element_counts=element_counts,
            unjoined_wall_ids=unjoined_walls,
            wall_count=len(walls)
        )

    except Exception as e:
        print(f"[Monitor] Error querying Revit state: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def call_mcp(pipe_name: str, method: str, params: dict) -> dict:
    """Call RevitMCPBridge via named pipe."""
    request = json.dumps({"method": method, "params": params})

    ps_script = f'''
$pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", "{pipe_name}", [System.IO.Pipes.PipeDirection]::InOut)
try {{
    $pipe.Connect(3000)
    $writer = New-Object System.IO.StreamWriter($pipe)
    $reader = New-Object System.IO.StreamReader($pipe)
    $writer.WriteLine('{request.replace("'", "''")}')
    $writer.Flush()
    $response = $reader.ReadLine()
    Write-Output $response
}} finally {{
    $pipe.Close()
}}
'''

    try:
        result = subprocess.run(
            ["powershell.exe", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0 and result.stdout.strip():
            # Filter out non-JSON lines (PowerShell profile messages, etc.)
            lines = result.stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('{'):
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue
            return {"success": False, "error": "No valid JSON in response"}
        return {"success": False, "error": result.stderr}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "MCP call timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_monitor(poll_interval: int = DEFAULT_POLL_INTERVAL, verbose: bool = False):
    """Main monitoring loop."""
    print(f"[Monitor] Starting ambient Revit monitor (polling every {poll_interval}s)")
    print(f"[Monitor] Voice triggers: unjoined walls >= 2")
    print(f"[Monitor] Press Ctrl+C to stop")

    last_state: Optional[RevitState] = None
    last_voice_time = 0
    voice_cooldown = 60  # Don't repeat same voice announcement within 60s

    while True:
        try:
            is_active, pipe_name = is_revit_active()

            if is_active:
                if verbose:
                    print(f"[Monitor] Revit active, querying state via {pipe_name}...")

                current_state = query_revit_state(pipe_name)

                if current_state:
                    # Diff against last state
                    changes = diff_states(last_state, current_state)

                    if changes.has_changes:
                        if verbose:
                            print(f"[Monitor] Changes detected: {changes}")

                        # Analyze changes against rules
                        analysis = analyze_changes(changes, current_state)

                        # Handle outputs based on tier
                        current_time = time.time()

                        for finding in analysis.voice_findings:
                            if current_time - last_voice_time > voice_cooldown:
                                speak_finding(finding)
                                last_voice_time = current_time

                        for finding in analysis.queue_findings:
                            queue_finding(finding)

                        for finding in analysis.critical_findings:
                            alert_critical(finding)
                            last_voice_time = current_time  # Critical always speaks

                    last_state = current_state
            else:
                if verbose:
                    print("[Monitor] Revit not active, sleeping...")

            time.sleep(poll_interval)

        except KeyboardInterrupt:
            print("\n[Monitor] Shutting down...")
            break
        except Exception as e:
            print(f"[Monitor] Error in main loop: {e}", file=sys.stderr)
            time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description="Ambient Revit Monitor")
    parser.add_argument("--interval", "-i", type=int, default=DEFAULT_POLL_INTERVAL,
                       help=f"Poll interval in seconds (default: {DEFAULT_POLL_INTERVAL})")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--test", "-t", action="store_true",
                       help="Run single test query and exit")

    args = parser.parse_args()

    if args.test:
        print("[Monitor] Running test query...")
        is_active, pipe_name = is_revit_active()
        print(f"  Revit active: {is_active}")
        print(f"  Pipe: {pipe_name}")

        if is_active:
            state = query_revit_state(pipe_name)
            if state:
                print(f"  View: {state.view_name}")
                print(f"  Walls: {state.wall_count}")
                print(f"  Unjoined: {len(state.unjoined_wall_ids)}")
            else:
                print("  Failed to query state")
        return 0

    run_monitor(args.interval, args.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())
