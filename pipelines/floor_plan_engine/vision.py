"""
Image → FloorPlanBuilder pipeline.

Analyzes a floor plan image using Claude's vision and extracts
structured room/door/window data to feed into FloorPlanBuilder.

Usage:
    from floor_plan_engine.vision import extract_from_image
    builder = extract_from_image("floorplan.png")
    plan = builder.build()
    analysis = plan.analyze()
"""

import base64
import json
import re
from pathlib import Path
from typing import Optional

from .builder import FloorPlanBuilder


EXTRACTION_PROMPT = """\
You are an architectural floor plan analyzer. Examine this floor plan image carefully and extract ALL elements into a structured JSON format.

IMPORTANT RULES:
1. Set up a coordinate system: origin (0,0) at the BOTTOM-LEFT of the plan
2. All measurements in FEET
3. X goes right (east), Y goes up (north)
4. Estimate dimensions from the image — use room labels, dimensions shown, or proportions
5. Every room must have a name, type, and exact x/y/w/h
6. Every door must have x/y coordinates on a wall, with room_a and room_b names
7. Every window must have x/y coordinates on an exterior wall
8. Mark which rooms are open-plan connected (no wall between them)

ROOM TYPES (use exactly these strings):
living_room, kitchen, dining_room, entry, master_bedroom, bedroom,
master_bath, bathroom, half_bath, laundry, hallway, closet,
walk_in_closet, pantry, office, family_room, garage

OUTPUT FORMAT — return ONLY this JSON, no other text:
```json
{
    "name": "Plan Name",
    "footprint": {"width": <total_width_ft>, "height": <total_height_ft>},
    "rooms": [
        {"name": "Living Room", "type": "living_room", "x": 0, "y": 0, "w": 15, "h": 12},
        ...
    ],
    "doors": [
        {"x": 10, "y": 0, "room_a": "Living Room", "room_b": "exterior", "is_entry": true},
        {"x": 15, "y": 6, "room_a": "Living Room", "room_b": "Kitchen"},
        ...
    ],
    "windows": [
        {"x": 7, "y": 0, "room_name": "Living Room"},
        ...
    ],
    "open_connections": [
        ["Living Room", "Kitchen"],
        ...
    ]
}
```

Be precise with coordinates. Doors and windows must sit ON wall lines (room boundaries or footprint edges). If you see dimension labels in the image, use those exact numbers.
"""


def extract_from_image(
    image_path: str,
    model: str = "claude-sonnet-4-20250514",
    api_key: Optional[str] = None,
    verbose: bool = False,
) -> FloorPlanBuilder:
    """Extract a floor plan from an image and return a FloorPlanBuilder.

    Args:
        image_path: Path to floor plan image (PNG, JPG, etc.)
        model: Claude model to use for vision analysis
        api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if None)
        verbose: Print extraction progress

    Returns:
        FloorPlanBuilder ready to .build()
    """
    import anthropic

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Read and encode image
    image_data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    media_type = _guess_media_type(path.suffix)

    if verbose:
        print(f"Analyzing {path.name} ({path.stat().st_size // 1024} KB)...")

    # Call Claude vision
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    message = client.messages.create(
        model=model,
        max_tokens=4096,
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
                    "text": EXTRACTION_PROMPT,
                },
            ],
        }],
    )

    # Extract JSON from response
    response_text = message.content[0].text
    data = _parse_json_response(response_text)

    if verbose:
        print(f"Extracted: {len(data.get('rooms', []))} rooms, "
              f"{len(data.get('doors', []))} doors, "
              f"{len(data.get('windows', []))} windows")
        if data.get("open_connections"):
            print(f"Open-plan: {data['open_connections']}")

    # Build via FloorPlanBuilder.from_dict()
    builder = FloorPlanBuilder.from_dict(data)

    if verbose:
        plan = builder.build()
        analysis = plan.analyze()
        print(f"Analysis: {analysis.score:.0f}/100 — {analysis.verdict}")

    return builder


def generate_prompt(image_path: str) -> str:
    """Generate the extraction prompt for manual use (without API call).

    Use this if you want to paste the image + prompt into Claude manually.
    Returns the prompt text.
    """
    return EXTRACTION_PROMPT


def parse_response(response_text: str) -> FloorPlanBuilder:
    """Parse a Claude vision response into a FloorPlanBuilder.

    Use this if you called the API yourself and have the response text.
    """
    data = _parse_json_response(response_text)
    return FloorPlanBuilder.from_dict(data)


def _parse_json_response(text: str) -> dict:
    """Extract JSON from Claude's response, handling code blocks."""
    # Try to find JSON in code block
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
    else:
        # Try raw JSON
        json_str = text.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Try to find any JSON object in the text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(
            f"Could not parse JSON from response:\n{text[:500]}")


def _guess_media_type(suffix: str) -> str:
    """Guess MIME type from file extension."""
    types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return types.get(suffix.lower(), "image/png")
