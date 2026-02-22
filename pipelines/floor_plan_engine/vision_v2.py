"""
Vision Pipeline v2: Image/PDF → WallPlan extraction.

Two-stage extraction using Claude vision with wall-first prompt.
Produces a WallPlan (not FloorPlan) — walls are primary, rooms are labels.

Pipeline:
  Image/PDF → [Pre-process] → [Claude Vision w/ wall-first prompt] → [Validate] → WallPlan

Modes:
  - "vision": Claude vision only (works with any image quality)
  - "hybrid": OpenCV wall detection + Claude for labels/openings

Reuses:
  - floorplan-rebuild/vision_prompt.md — wall-first extraction prompt
  - floorplan-rebuild/schema.json — output format
"""

import json
import base64
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from .wall_model import WallPlan, Wall, Opening, RoomLabel


# ── Vision Prompt ──

WALL_FIRST_VISION_PROMPT = """You are analyzing a floor plan image to extract EXACT architectural data.

## ABSOLUTE RULES - ZERO GUESSING

1. **ONLY describe what you can SEE.** If a dimension is not written on the plan, do NOT invent it.
2. **If you cannot read a number clearly, mark it as "UNCLEAR" in the notes.** Do not guess.
3. **If a wall's exact position cannot be determined from visible dimensions, say so.** Do not approximate.
4. **Every coordinate you output must be traceable to a visible dimension or calculable from visible dimensions.**
5. **If the drawing doesn't show enough dimensions to fully reconstruct the plan, list what's missing.**

## COORDINATE SYSTEM
- Origin (0,0) at bottom-left exterior corner
- X increases to the right, Y increases upward
- All coordinates in FEET (convert: 12'-6" = 12.5')
- Wall coordinates are CENTERLINES

## EXTRACTION ORDER

### 1. Overall Dimensions
- Total width and depth if dimensioned
- Scale if noted
- Floor-to-ceiling height if noted (default 9')

### 2. Walls
For each wall:
- Wall ID (W1, W2, ...)
- Start (x, y) and End (x, y) — CENTERLINE coordinates in feet
- Type: "exterior" or "interior"
- Thickness in inches (exterior typically 6-8, interior 4-6, default 6)

### 3. Doors
For each door:
- Door ID (D1, D2, ...)
- wall_id: which wall it's on
- offset_ft: distance from wall START to near edge of door
- width_ft: door width (standard 3.0 unless dimensioned)
- swing: left/right/double/sliding (visible from arc on plan)
- is_entry: true if this is the main entry door

### 4. Windows
For each window:
- Window ID (WIN1, WIN2, ...)
- wall_id: which wall it's on
- offset_ft: distance from wall START to near edge
- width_ft: window width (standard 3.0 unless dimensioned)

### 5. Rooms
For each labeled room:
- name: room name exactly as shown
- label_position: approximate center (x, y) in feet
- area_sqft: if noted on plan
- dimensions: if noted on plan

### 6. Missing Information
List everything that could NOT be determined:
- "Wall W3 position: only one dimension visible"
- "Door D2 offset: no dimension shown"

## OUTPUT FORMAT
Output valid JSON:
```json
{
  "metadata": {
    "units": "feet",
    "overall_width_ft": <number or null>,
    "overall_depth_ft": <number or null>,
    "floor_to_ceiling_ft": 9.0,
    "notes": ["list every assumption or unclear reading"]
  },
  "walls": [
    {"id": "W1", "start": {"x": 0, "y": 0}, "end": {"x": 30, "y": 0}, "type": "exterior", "thickness_in": 8}
  ],
  "doors": [
    {"id": "D1", "wall_id": "W1", "offset_ft": 5.0, "width_ft": 3.0, "swing": "left", "is_entry": true}
  ],
  "windows": [
    {"id": "WIN1", "wall_id": "W2", "offset_ft": 4.0, "width_ft": 3.0}
  ],
  "rooms": [
    {"name": "Living Room", "label_position": {"x": 15, "y": 10}, "area_sqft": 200}
  ]
}
```

## CRITICAL REMINDERS
- Feet-inches: 5'-4" = 5.333', 3'-6" = 3.5', 10'-0" = 10.0'
- Wall CENTERLINE = wall face ± half thickness
- Output ONLY what the drawing shows. Missing data goes in notes[].
"""


def extract_wall_plan(
    image_path: str,
    known_width_ft: Optional[float] = None,
    known_depth_ft: Optional[float] = None,
    mode: str = "vision",
    api_key: Optional[str] = None,
) -> WallPlan:
    """Extract a WallPlan from a floor plan image or PDF.

    Args:
        image_path: Path to image file (PNG, JPG) or PDF
        known_width_ft: Override overall width if known
        known_depth_ft: Override overall depth if known
        mode: "vision" (Claude only) or "hybrid" (OpenCV + Claude)
        api_key: Anthropic API key (reads ANTHROPIC_API_KEY env var if None)

    Returns:
        WallPlan extracted from the image

    Raises:
        ValueError: If extraction fails or image is unreadable
        FileNotFoundError: If image_path doesn't exist
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Pre-process: load and encode image
    image_data, media_type = _load_image(path)

    # Build prompt with optional known dimensions
    prompt = WALL_FIRST_VISION_PROMPT
    if known_width_ft:
        prompt += f"\n\nKNOWN: Overall building width is {known_width_ft} feet."
    if known_depth_ft:
        prompt += f"\n\nKNOWN: Overall building depth is {known_depth_ft} feet."

    # Call Claude vision API
    response_json = _call_claude_vision(image_data, media_type, prompt, api_key)

    # Parse response into WallPlan
    plan = _parse_vision_response(response_json)

    # Apply known dimensions if provided
    if known_width_ft:
        plan.overall_width_ft = known_width_ft
    if known_depth_ft:
        plan.overall_depth_ft = known_depth_ft

    # Validate
    issues = validate_wall_plan(plan)
    if issues:
        plan.notes.extend([f"VALIDATION: {issue}" for issue in issues])

    return plan


def _load_image(path: Path) -> Tuple[str, str]:
    """Load and base64-encode an image file.

    Returns (base64_data, media_type).
    """
    suffix = path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }

    media_type = media_types.get(suffix)
    if not media_type:
        raise ValueError(f"Unsupported image format: {suffix}")

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    return data, media_type


def _call_claude_vision(
    image_data: str,
    media_type: str,
    prompt: str,
    api_key: Optional[str] = None,
) -> dict:
    """Call Claude vision API with image and prompt.

    Returns parsed JSON response.
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package required: pip install anthropic")

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": prompt,
                },
            ],
        }],
    )

    # Extract JSON from response
    text = message.content[0].text
    return parse_json_response(text)


def parse_json_response(text: str) -> dict:
    """Parse JSON from Claude's response text.

    Handles JSON in code blocks, raw JSON, or JSON surrounded by text.
    """
    import re

    # Try code block first
    code_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if code_match:
        return json.loads(code_match.group(1).strip())

    # Try raw JSON (starts with {)
    brace_match = re.search(r'\{.*\}', text, re.DOTALL)
    if brace_match:
        return json.loads(brace_match.group(0))

    raise ValueError(f"No valid JSON found in response: {text[:200]}...")


def _parse_vision_response(data: dict) -> WallPlan:
    """Convert parsed JSON into a WallPlan."""
    return WallPlan.from_dict(data)


# ── Validation ──

def validate_wall_plan(plan: WallPlan) -> List[str]:
    """Validate a WallPlan for geometric consistency.

    Returns list of issue descriptions. Empty = valid.
    """
    issues = []

    # Check: at least some walls exist
    if not plan.walls:
        issues.append("No walls found")
        return issues

    # Check: exterior walls form a closed polygon
    ext = plan.exterior_walls
    if ext:
        issues.extend(_check_exterior_closure(ext))

    # Check: interior walls connect at endpoints
    issues.extend(_check_interior_connections(plan))

    # Check: openings reference valid walls
    issues.extend(_check_opening_references(plan))

    # Check: openings have valid offsets
    issues.extend(_check_opening_offsets(plan))

    return issues


def _check_exterior_closure(ext_walls: List[Wall]) -> List[str]:
    """Check if exterior walls form a closed polygon."""
    issues = []
    if len(ext_walls) < 3:
        issues.append(f"Only {len(ext_walls)} exterior walls — need at least 3 for closure")
        return issues

    # Check that each wall's end connects to the next wall's start
    for i in range(len(ext_walls)):
        w1 = ext_walls[i]
        w2 = ext_walls[(i + 1) % len(ext_walls)]
        dx = abs(w1.end[0] - w2.start[0])
        dy = abs(w1.end[1] - w2.start[1])
        if dx > 0.5 or dy > 0.5:
            issues.append(
                f"Exterior wall gap: {w1.id} end ({w1.end[0]},{w1.end[1]}) "
                f"→ {w2.id} start ({w2.start[0]},{w2.start[1]})"
            )

    return issues


def _check_interior_connections(plan: WallPlan) -> List[str]:
    """Check that interior wall endpoints touch other walls."""
    issues = []
    all_walls = plan.walls

    for w in plan.interior_walls:
        # Check start point
        if not _endpoint_touches_wall(w.start, w, all_walls):
            issues.append(
                f"Interior wall {w.id} start ({w.start[0]},{w.start[1]}) "
                f"doesn't connect to any wall"
            )
        # Check end point
        if not _endpoint_touches_wall(w.end, w, all_walls):
            issues.append(
                f"Interior wall {w.id} end ({w.end[0]},{w.end[1]}) "
                f"doesn't connect to any wall"
            )

    return issues


def _endpoint_touches_wall(point, exclude_wall, all_walls, tol=0.5) -> bool:
    """Check if a point touches any wall (not the excluded one)."""
    px, py = point
    for w in all_walls:
        if w.id == exclude_wall.id:
            continue

        # Check if point is on or near this wall segment
        x1, y1, x2, y2 = w.x1, w.y1, w.x2, w.y2
        dx, dy = x2 - x1, y2 - y1
        seg_len_sq = dx * dx + dy * dy

        if seg_len_sq < 0.01:
            dist = ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        else:
            t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / seg_len_sq))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            dist = ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5

        if dist <= tol:
            return True

    return False


def _check_opening_references(plan: WallPlan) -> List[str]:
    """Check that all openings reference existing walls."""
    issues = []
    wall_ids = {w.id for w in plan.walls}

    for door in plan.doors:
        if door.wall_id not in wall_ids:
            issues.append(f"Door {door.id} references non-existent wall {door.wall_id}")

    for win in plan.windows:
        if win.wall_id not in wall_ids:
            issues.append(f"Window {win.id} references non-existent wall {win.wall_id}")

    return issues


def _check_opening_offsets(plan: WallPlan) -> List[str]:
    """Check that opening offsets are within wall length."""
    issues = []

    for opening in plan.doors + plan.windows:
        wall = plan.wall_by_id(opening.wall_id)
        if wall is None:
            continue  # Already caught by reference check

        max_offset = wall.length - opening.width_ft
        if opening.offset_ft < -0.1:
            issues.append(
                f"{opening.opening_type.title()} {opening.id}: "
                f"negative offset {opening.offset_ft}"
            )
        elif opening.offset_ft > max_offset + 0.5:
            issues.append(
                f"{opening.opening_type.title()} {opening.id}: "
                f"offset {opening.offset_ft} + width {opening.width_ft} "
                f"exceeds wall {opening.wall_id} length {wall.length:.1f}"
            )

    return issues


# ── Scale Detection ──

def detect_scale(plan: WallPlan, known_features: Optional[dict] = None) -> float:
    """Detect or verify scale of a wall plan.

    Uses dimension strings, known features, or standard heuristics.

    Args:
        plan: The WallPlan to check
        known_features: Optional dict of known dimensions, e.g.
            {"door_width_ft": 3.0, "counter_depth_ft": 2.0}

    Returns:
        Scale factor (1.0 = correct, >1 = plan is too small, <1 = too big)
    """
    # If we have overall dimensions, trust them
    if plan.overall_width_ft and plan.overall_depth_ft:
        return 1.0

    # Use standard heuristics
    if plan.doors:
        # Standard door is ~3 feet wide
        avg_door_width = sum(d.width_ft for d in plan.doors) / len(plan.doors)
        expected = 3.0
        if avg_door_width > 0.1:
            return expected / avg_door_width

    return 1.0
