#!/usr/bin/env python3
"""
Visual Inspector - Autonomous Zoom Control for Revit
Gives Claude the ability to zoom in/out, inspect areas, and gather information.

Capabilities:
- Zoom to fit (overview)
- Zoom to specific element
- Zoom to region (requires MCP addition)
- Zoom to grid intersection (requires MCP addition)
- Multi-level inspection workflow
"""

import json
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple
from datetime import datetime


@dataclass
class InspectionCapture:
    """A single capture during inspection."""
    timestamp: datetime
    zoom_level: str  # "fit", "element", "region"
    target: str      # element ID, grid intersection, or "overview"
    image_path: str
    view_name: str
    notes: str = ""


@dataclass
class InspectionResult:
    """Results from a visual inspection session."""
    captures: List[InspectionCapture]
    findings: List[dict]
    summary: str


# =============================================================================
# MCP COMMUNICATION
# =============================================================================

def call_mcp(pipe_name: str, method: str, params: dict) -> dict:
    """Call RevitMCPBridge via named pipe."""
    request = json.dumps({"method": method, "params": params})

    ps_script = f'''
$pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", "{pipe_name}", [System.IO.Pipes.PipeDirection]::InOut)
try {{
    $pipe.Connect(5000)
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
            timeout=15
        )

        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('{'):
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue
        return {"success": False, "error": "No valid JSON response"}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "MCP call timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# ZOOM CONTROL
# =============================================================================

def zoom_to_fit(pipe_name: str = "RevitMCPBridge2026") -> dict:
    """Zoom to fit all elements in view."""
    return call_mcp(pipe_name, "zoomToFit", {})


def zoom_to_element(element_id: int, pipe_name: str = "RevitMCPBridge2026") -> dict:
    """Zoom to a specific element by ID."""
    return call_mcp(pipe_name, "zoomToElement", {"elementId": element_id})


def zoom_to_region(min_point: List[float], max_point: List[float],
                   pipe_name: str = "RevitMCPBridge2026") -> dict:
    """
    Zoom to a bounding box region.
    NOTE: Requires zoomToRegion method to be added to MCP.

    Args:
        min_point: [x, y, z] minimum corner in feet
        max_point: [x, y, z] maximum corner in feet
    """
    return call_mcp(pipe_name, "zoomToRegion", {
        "minPoint": min_point,
        "maxPoint": max_point
    })


def zoom_to_grid_intersection(grid_h: str, grid_v: str,
                               margin_feet: float = 30.0,
                               pipe_name: str = "RevitMCPBridge2026") -> dict:
    """
    Zoom to area around a grid intersection.
    NOTE: Requires zoomToGridIntersection method to be added to MCP.

    Args:
        grid_h: Horizontal grid name (e.g., "FFF")
        grid_v: Vertical grid name (e.g., "QQQ")
        margin_feet: How much area around intersection to show
    """
    return call_mcp(pipe_name, "zoomToGridIntersection", {
        "gridHorizontal": grid_h,
        "gridVertical": grid_v,
        "margin": margin_feet
    })


# =============================================================================
# CAPTURE
# =============================================================================

def capture_view(width: int = 1920, height: int = 1080,
                 pipe_name: str = "RevitMCPBridge2026") -> Optional[str]:
    """Capture current view and return image path."""
    response = call_mcp(pipe_name, "exportViewImage", {
        "width": width,
        "height": height
    })

    if response.get("success"):
        result = response.get("result", {})
        return result.get("outputPath")
    return None


def get_active_view(pipe_name: str = "RevitMCPBridge2026") -> dict:
    """Get current active view info."""
    return call_mcp(pipe_name, "getActiveView", {})


# =============================================================================
# INSPECTION WORKFLOWS
# =============================================================================

def inspect_overview(pipe_name: str = "RevitMCPBridge2026") -> Optional[InspectionCapture]:
    """Capture overview of entire view."""
    zoom_to_fit(pipe_name)

    view_info = get_active_view(pipe_name)
    view_name = view_info.get("viewName", "Unknown")

    image_path = capture_view(pipe_name=pipe_name)

    if image_path:
        return InspectionCapture(
            timestamp=datetime.now(),
            zoom_level="fit",
            target="overview",
            image_path=image_path,
            view_name=view_name
        )
    return None


def inspect_element(element_id: int,
                    pipe_name: str = "RevitMCPBridge2026") -> Optional[InspectionCapture]:
    """Zoom to and capture a specific element."""
    zoom_response = zoom_to_element(element_id, pipe_name)

    if not zoom_response.get("success"):
        return None

    view_info = get_active_view(pipe_name)
    view_name = view_info.get("viewName", "Unknown")

    image_path = capture_view(pipe_name=pipe_name)

    if image_path:
        return InspectionCapture(
            timestamp=datetime.now(),
            zoom_level="element",
            target=str(element_id),
            image_path=image_path,
            view_name=view_name
        )
    return None


def inspect_region(min_point: List[float], max_point: List[float],
                   name: str = "region",
                   pipe_name: str = "RevitMCPBridge2026") -> Optional[InspectionCapture]:
    """Zoom to and capture a region."""
    zoom_response = zoom_to_region(min_point, max_point, pipe_name)

    if not zoom_response.get("success"):
        print(f"[Inspector] zoomToRegion not available: {zoom_response.get('error')}")
        return None

    view_info = get_active_view(pipe_name)
    view_name = view_info.get("viewName", "Unknown")

    image_path = capture_view(pipe_name=pipe_name)

    if image_path:
        return InspectionCapture(
            timestamp=datetime.now(),
            zoom_level="region",
            target=name,
            image_path=image_path,
            view_name=view_name
        )
    return None


def inspect_grid_area(grid_h: str, grid_v: str, margin: float = 30.0,
                      pipe_name: str = "RevitMCPBridge2026") -> Optional[InspectionCapture]:
    """Zoom to and capture area around grid intersection."""
    zoom_response = zoom_to_grid_intersection(grid_h, grid_v, margin, pipe_name)

    if not zoom_response.get("success"):
        print(f"[Inspector] zoomToGridIntersection not available: {zoom_response.get('error')}")
        return None

    view_info = get_active_view(pipe_name)
    view_name = view_info.get("viewName", "Unknown")

    image_path = capture_view(pipe_name=pipe_name)

    if image_path:
        return InspectionCapture(
            timestamp=datetime.now(),
            zoom_level="grid",
            target=f"{grid_h}/{grid_v}",
            image_path=image_path,
            view_name=view_name
        )
    return None


def full_inspection(grid_intersections: List[Tuple[str, str]] = None,
                    element_ids: List[int] = None,
                    pipe_name: str = "RevitMCPBridge2026") -> InspectionResult:
    """
    Perform full multi-level inspection.

    1. Capture overview
    2. Zoom to each grid intersection
    3. Zoom to specific elements
    4. Return all captures for analysis
    """
    captures = []

    # Step 1: Overview
    print("[Inspector] Capturing overview...")
    overview = inspect_overview(pipe_name)
    if overview:
        captures.append(overview)

    # Step 2: Grid intersections
    if grid_intersections:
        for grid_h, grid_v in grid_intersections:
            print(f"[Inspector] Inspecting grid {grid_h}/{grid_v}...")
            capture = inspect_grid_area(grid_h, grid_v, pipe_name=pipe_name)
            if capture:
                captures.append(capture)

    # Step 3: Specific elements
    if element_ids:
        for elem_id in element_ids:
            print(f"[Inspector] Inspecting element {elem_id}...")
            capture = inspect_element(elem_id, pipe_name)
            if capture:
                captures.append(capture)

    # Step 4: Return to overview
    zoom_to_fit(pipe_name)

    return InspectionResult(
        captures=captures,
        findings=[],
        summary=f"Inspection complete: {len(captures)} captures"
    )


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Visual Inspector for Revit")
    parser.add_argument("--overview", "-o", action="store_true", help="Capture overview")
    parser.add_argument("--element", "-e", type=int, help="Zoom to element ID")
    parser.add_argument("--grid", "-g", nargs=2, help="Zoom to grid intersection (H V)")
    parser.add_argument("--pipe", "-p", default="RevitMCPBridge2026", help="Pipe name")

    args = parser.parse_args()

    if args.overview:
        capture = inspect_overview(args.pipe)
        if capture:
            print(f"Captured: {capture.image_path}")
        else:
            print("Failed to capture overview")

    elif args.element:
        capture = inspect_element(args.element, args.pipe)
        if capture:
            print(f"Captured element {args.element}: {capture.image_path}")
        else:
            print(f"Failed to capture element {args.element}")

    elif args.grid:
        capture = inspect_grid_area(args.grid[0], args.grid[1], pipe_name=args.pipe)
        if capture:
            print(f"Captured grid {args.grid[0]}/{args.grid[1]}: {capture.image_path}")
        else:
            print(f"Grid zoom not available - needs MCP method")
    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())
