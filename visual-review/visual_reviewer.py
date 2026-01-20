#!/usr/bin/env python3
"""
Visual Review Layer
Catches spatial/logical errors that parameter validation cannot.

Uses Revit view exports + Claude vision to detect:
- Bathroom with no sink/toilet
- Doors that will collide when opened
- Blocked egress paths
- Missing fixtures in rooms
- Unjoined walls
- Spatial logic issues

This is the genuine gap that rules structurally cannot fill.
"""

import json
import base64
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import tempfile


class IssueSeverity(Enum):
    CRITICAL = "critical"  # Code violation, must fix
    WARNING = "warning"    # Likely problem, should review
    INFO = "info"          # Observation, optional


@dataclass
class SpatialIssue:
    """A spatial/logical issue detected in the view."""
    category: str
    description: str
    severity: IssueSeverity
    location: Optional[str] = None
    suggestion: Optional[str] = None


# =============================================================================
# SPATIAL LOGIC PROMPTS
# =============================================================================

FLOOR_PLAN_REVIEW_PROMPT = """You are an expert architectural reviewer analyzing a floor plan view from Revit.

Look for these SPECIFIC issues:

## ROOM LOGIC
- Bathroom/restroom missing toilet, sink, or required fixtures
- Kitchen missing sink or required appliances
- Bedroom with no closet (residential)
- Room with no door/access
- Extremely small rooms that can't function

## DOOR ISSUES
- Two doors that will collide when both open (swing interference)
- Door swinging into toilet/fixture
- Door blocking corridor when open
- Door at end of corridor with no landing space

## EGRESS/SAFETY
- Dead-end corridors exceeding 20 feet
- Blocked exit paths (furniture, walls)
- Exit door swinging wrong direction (should swing out for egress)
- Missing second exit in large rooms

## WALL ISSUES
- Walls that appear unjoined (gaps at corners)
- Walls that don't meet at corners
- Floating wall segments

## SPATIAL LOGIC
- Room inside another room with no access
- Stairs leading nowhere
- Windows in interior walls
- Toilet room opening directly to dining/kitchen

For each issue found, provide:
1. Category (room_logic, door_issue, egress, wall_issue, spatial_logic)
2. Location description
3. Severity (critical, warning, info)
4. Specific suggestion to fix

Respond in JSON format:
{
  "issues": [
    {
      "category": "room_logic",
      "description": "Bathroom in northwest corner has no sink",
      "location": "Northwest bathroom",
      "severity": "critical",
      "suggestion": "Add lavatory fixture"
    }
  ],
  "summary": "Found X issues: Y critical, Z warnings",
  "overall_assessment": "Brief overall assessment"
}

If no issues found, return empty issues array with positive assessment.
Be specific about locations using compass directions or room labels visible in the plan.
"""

DETAIL_REVIEW_PROMPT = """You are an expert architectural detail reviewer.

Analyze this construction detail for:
- Missing components (flashing, vapor barrier, insulation, etc.)
- Incorrect layer order
- Thermal bridges
- Water intrusion paths
- Missing dimensions or callouts
- Components that don't connect properly

Respond in JSON format with issues array."""


# =============================================================================
# REVIT MCP INTEGRATION
# =============================================================================

def capture_view_from_revit(view_id: Optional[int] = None, pipe_name: str = "RevitMCPBridge2026") -> Optional[str]:
    """
    Capture current or specified view from Revit via MCP.

    Returns: Path to exported image file, or None on failure.
    """
    # Build MCP request
    request = {
        "method": "captureViewport",
        "params": {}
    }

    if view_id:
        request["params"]["viewId"] = view_id

    # Create temp output path
    output_path = Path(tempfile.gettempdir()) / "revit_visual_review.png"
    request["params"]["filePath"] = str(output_path)
    request["params"]["width"] = 1920
    request["params"]["height"] = 1080

    try:
        # Call MCP via PowerShell pipe
        ps_script = f'''
$pipeName = "{pipe_name}"
$pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
$pipe.Connect(5000)
$writer = New-Object System.IO.StreamWriter($pipe)
$reader = New-Object System.IO.StreamReader($pipe)
$writer.WriteLine('{json.dumps(request)}')
$writer.Flush()
$response = $reader.ReadLine()
$pipe.Close()
Write-Output $response
'''
        result = subprocess.run(
            ["powershell.exe", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0 and output_path.exists():
            return str(output_path)
        else:
            print(f"Capture failed: {result.stderr}", file=sys.stderr)
            return None

    except Exception as e:
        print(f"Error capturing view: {e}", file=sys.stderr)
        return None


def capture_view_to_base64(view_id: Optional[int] = None, pipe_name: str = "RevitMCPBridge2026") -> Optional[str]:
    """Capture view and return as base64 string."""
    request = {
        "method": "captureViewportToBase64",
        "params": {}
    }

    if view_id:
        request["params"]["viewId"] = view_id

    try:
        ps_script = f'''
$pipeName = "{pipe_name}"
$pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
$pipe.Connect(5000)
$writer = New-Object System.IO.StreamWriter($pipe)
$reader = New-Object System.IO.StreamReader($pipe)
$writer.WriteLine('{json.dumps(request)}')
$writer.Flush()
$response = $reader.ReadLine()
$pipe.Close()
Write-Output $response
'''
        result = subprocess.run(
            ["powershell.exe", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            response = json.loads(result.stdout.strip())
            if response.get("success"):
                return response.get("result", {}).get("base64Image")

        return None

    except Exception as e:
        print(f"Error capturing view: {e}", file=sys.stderr)
        return None


# =============================================================================
# CLAUDE VISION ANALYSIS
# =============================================================================

def analyze_with_claude(image_path: str, prompt: str) -> Optional[dict]:
    """
    Analyze an image using Claude's vision capability.
    Uses the Read tool internally to view the image.

    Returns: Parsed JSON response with issues, or None on failure.
    """
    try:
        # Read the image file and convert to base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        # For now, return a placeholder - in production, this would call Claude API
        # The actual analysis happens when Claude Code reads the image
        return {
            "image_path": image_path,
            "prompt": prompt,
            "status": "ready_for_analysis",
            "note": "Use Claude Code Read tool on this image with the provided prompt"
        }

    except Exception as e:
        print(f"Error preparing image for analysis: {e}", file=sys.stderr)
        return None


# =============================================================================
# REVIEW FUNCTIONS
# =============================================================================

def review_floor_plan(image_path: Optional[str] = None, view_id: Optional[int] = None) -> dict:
    """
    Review a floor plan for spatial/logical issues.

    Args:
        image_path: Path to existing image, OR
        view_id: Revit view ID to capture

    Returns:
        Analysis result dict
    """
    # Get image
    if not image_path:
        image_path = capture_view_from_revit(view_id)

    if not image_path or not Path(image_path).exists():
        return {
            "success": False,
            "error": "Could not capture or find floor plan image"
        }

    return {
        "success": True,
        "image_path": image_path,
        "review_type": "floor_plan",
        "prompt": FLOOR_PLAN_REVIEW_PROMPT,
        "instructions": "Use Claude Code to read this image and apply the floor plan review prompt"
    }


def review_detail(image_path: Optional[str] = None, view_id: Optional[int] = None) -> dict:
    """Review a construction detail for issues."""
    if not image_path:
        image_path = capture_view_from_revit(view_id)

    if not image_path or not Path(image_path).exists():
        return {
            "success": False,
            "error": "Could not capture or find detail image"
        }

    return {
        "success": True,
        "image_path": image_path,
        "review_type": "detail",
        "prompt": DETAIL_REVIEW_PROMPT,
        "instructions": "Use Claude Code to read this image and apply the detail review prompt"
    }


def quick_check(description: str = "general") -> str:
    """
    Return the appropriate review prompt for quick checking.
    Can be used inline in Claude Code conversations.
    """
    prompts = {
        "floor_plan": FLOOR_PLAN_REVIEW_PROMPT,
        "detail": DETAIL_REVIEW_PROMPT,
        "general": FLOOR_PLAN_REVIEW_PROMPT
    }
    return prompts.get(description, FLOOR_PLAN_REVIEW_PROMPT)


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Visual Review Layer for Revit")
    parser.add_argument("--image", "-i", help="Path to image file to review")
    parser.add_argument("--view-id", "-v", type=int, help="Revit view ID to capture and review")
    parser.add_argument("--type", "-t", choices=["floor_plan", "detail"], default="floor_plan",
                       help="Type of review to perform")
    parser.add_argument("--prompt-only", "-p", action="store_true",
                       help="Just output the review prompt (for use in Claude Code)")

    args = parser.parse_args()

    if args.prompt_only:
        print(quick_check(args.type))
        return 0

    if args.type == "floor_plan":
        result = review_floor_plan(args.image, args.view_id)
    else:
        result = review_detail(args.image, args.view_id)

    print(json.dumps(result, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
