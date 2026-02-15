# Floor Plan Vision Analysis Prompt

Use this prompt when analyzing a floor plan image to produce the structured JSON
that `floorplan_to_dxf.py` consumes.

---

## THE PROMPT (copy and use when analyzing an image)

```
You are analyzing a floor plan image to extract EXACT architectural data.

## ABSOLUTE RULES - ZERO GUESSING

1. **ONLY describe what you can SEE.** If a dimension is not written on the plan, do NOT invent it.
2. **If you cannot read a number clearly, mark it as "UNCLEAR" in the notes.** Do not guess.
3. **If a wall's exact position cannot be determined from visible dimensions, say so.** Do not approximate.
4. **Every coordinate you output must be traceable to a visible dimension or calculable from visible dimensions.**
5. **If the drawing doesn't show enough dimensions to fully reconstruct the plan, list what's missing.** The user will provide the missing information.

## WHAT TO EXTRACT

### Step 1: Scale and Overall Dimensions
- Is there a scale noted? (e.g., "1/4" = 1'-0"")
- Are overall building dimensions shown?
- What is the unit system? (typically feet-inches for US architectural)

### Step 2: Establish Coordinate System
- Place origin (0,0) at the bottom-left exterior corner of the building
- X increases to the right, Y increases upward
- All coordinates in FEET (convert feet-inches: 12'-6" = 12.5')

### Step 3: Wall Layout
For each wall, provide:
- Wall ID (W1, W2, etc.)
- Start coordinate (x, y) in feet
- End coordinate (x, y) in feet
- These are CENTERLINE coordinates
- Thickness in inches (if shown, otherwise note as assumed)
- Type: exterior or interior

HOW TO DETERMINE WALL COORDINATES:
- Use dimensioned measurements to calculate positions
- Chain dimensions: if Room A is 12' wide and Room B starts at the right side of Room A, Room B's left wall x = 12' (plus wall thicknesses if dimensioned to face)
- If a dimension says "12'-6" from left wall to right wall", that's 12.5 feet
- Account for wall thickness: dimensions to wall FACE vs wall CENTER differ by half the wall thickness

### Step 4: Doors
For each visible door:
- Door ID (D1, D2, etc.)
- Which wall it's on (wall ID)
- Offset from wall START to the near edge of the door opening, in feet
- Door width (standard 3'-0" unless dimensioned otherwise)
- Swing direction (visible from the arc on the plan)
- Swing side (which side of the wall it swings to)

HOW TO DETERMINE DOOR OFFSET:
- If the door is dimensioned from a corner, use that dimension
- If the plan shows the door position but no dimension to it, state this in notes and provide your best reading, flagged as "MEASURED FROM DRAWING - verify"
- Do NOT guess door positions that aren't visible

### Step 5: Windows
For each visible window:
- Window ID (WIN1, WIN2, etc.)
- Which wall it's on (wall ID)
- Offset from wall START to near edge of window, in feet
- Window width (if dimensioned, otherwise note as assumed)

### Step 6: Rooms
For each labeled room:
- Room name (exactly as shown)
- Center position (x, y) in feet
- Dimensions (if shown)

### Step 7: Missing Information
List everything that could NOT be determined from the drawing:
- "Wall W3 position: only one dimension visible, need distance from [reference]"
- "Door D2 offset: no dimension shown, approximate position only"
- "Window WIN1 width: not dimensioned"

## OUTPUT FORMAT

Output valid JSON matching this structure:

{
  "metadata": {
    "source_file": "<filename>",
    "scale": "<if visible>",
    "units": "feet",
    "overall_width_ft": <number or null if not dimensioned>,
    "overall_depth_ft": <number or null if not dimensioned>,
    "floor_to_ceiling_ft": <number, default 9.0>,
    "notes": [
      "List every assumption, unclear reading, or missing dimension here",
      "User must verify these before generating DXF"
    ]
  },
  "walls": [...],
  "doors": [...],
  "windows": [...],
  "rooms": [...]
}

## CRITICAL REMINDERS
- Feet-inches conversion: 5'-4" = 5.333', 3'-6" = 3.5', 10'-0" = 10.0'
- Wall centerline = wall face position ± half wall thickness
- Dimensions to "face of stud" vs "face of finish" vs "centerline" matter
- If the plan has a dimension string, read it EXACTLY - do not round
- Output ONLY what the drawing shows. Missing data goes in notes[].
```

---

## USAGE

1. Show Claude the floor plan image
2. Paste the prompt above
3. Claude produces the JSON
4. Review the "notes" section - fill in any missing data
5. Run: `python floorplan_to_dxf.py output.json`
6. Import DXF into Revit or use dxf_to_revit_walls.py
