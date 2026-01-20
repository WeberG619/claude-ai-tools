# FLOOR PLAN READING PROCEDURE
## Deterministic System for DXF to Revit Wall Conversion

**Version:** 1.0
**Purpose:** Extract walls from AutoCAD DXF files and place them in Revit with 95%+ accuracy
**Author:** Built collaboratively with Bruce Davis, BD Architect

---

## OVERVIEW

This procedure defines explicit steps for converting DXF floor plans to Revit walls.
It is NOT based on memory or interpretation - it follows deterministic rules every time.

---

## PREREQUISITES

- Python 3 with `ezdxf` library installed
- DXF file exported from AutoCAD (File > Export > DXF)
- RevitMCPBridge running in Revit
- Wall type IDs mapped for target Revit project

---

## STEP 1: LOAD DXF FILE

```python
import ezdxf
doc = ezdxf.readfile("path/to/file.dxf")
msp = doc.modelspace()
```

---

## STEP 2: IDENTIFY WALL LAYERS

### 2a. List all layers and entity counts
```python
from collections import Counter
entities_by_layer = Counter(e.dxf.layer for e in msp)
for layer, count in entities_by_layer.most_common(30):
    print(f"{layer}: {count}")
```

### 2b. Select wall layers using these keywords (case-insensitive)
```
PRIMARY KEYWORDS (most likely walls):
- "A-WALL" (architectural wall)
- "WALL-EXIST" (existing walls)
- "I-WALL" (interior wall)
- "WALL"

SECONDARY KEYWORDS (possible walls):
- "PARTITION"
- "1HRWALL", "2HRWALL" (fire-rated)
- "CMU"
- "STUD"
```

### 2c. Layer selection priority
1. Layers containing "A-WALL-EXIST" - highest priority (existing architectural walls)
2. Layers containing "A-WALL" - architectural walls
3. Layers containing "I-WALL" - interior walls
4. Layers containing "WALL" alone - generic walls

---

## STEP 3: EXTRACT LINE ENTITIES FROM WALL LAYERS

```python
wall_layers = ['A-WALL-EXIST', 'A-WALL', 'I-WALL', ...]  # From Step 2

wall_lines = []
for entity in msp:
    if entity.dxf.layer in wall_layers and entity.dxftype() == 'LINE':
        start = entity.dxf.start
        end = entity.dxf.end
        length = ((end.x - start.x)**2 + (end.y - start.y)**2)**0.5

        # RULE: Discard lines shorter than 0.5 ft (6 inches)
        if length >= 0.5:
            wall_lines.append({
                'startX': start.x,
                'startY': start.y,
                'endX': end.x,
                'endY': end.y,
                'length': length
            })
```

---

## STEP 4: CLASSIFY LINES AS HORIZONTAL OR VERTICAL

```python
def is_horizontal(line, tolerance=0.1):
    """Line is horizontal if Y values are within tolerance"""
    return abs(line['startY'] - line['endY']) < tolerance

def is_vertical(line, tolerance=0.1):
    """Line is vertical if X values are within tolerance"""
    return abs(line['startX'] - line['endX']) < tolerance

horizontal_lines = [l for l in wall_lines if is_horizontal(l)]
vertical_lines = [l for l in wall_lines if is_vertical(l)]
```

---

## STEP 5: FIND PARALLEL LINE PAIRS (WALL DETECTION)

**RULE:** A wall is represented by TWO parallel lines (the wall faces).
The distance between them is the wall thickness.

### 5a. For horizontal line pairs (creates VERTICAL walls)
```python
# Sort horizontal lines by Y coordinate
sorted_by_y = sorted(horizontal_lines, key=lambda l: l['startY'])

for each line L1:
    for each nearby line L2 (within next 50 lines):
        distance = abs(L2['startY'] - L1['startY'])

        # RULE: Wall thickness must be 3-14 inches (0.25 - 1.17 ft)
        if distance < 0.25 or distance > 1.17:
            continue

        # RULE: Lines must overlap in X direction by at least 2 ft
        x_overlap = calculate_overlap(L1, L2, 'X')
        if x_overlap < 2.0:
            continue

        # FOUND WALL PAIR!
        wall = {
            'type': 'VERTICAL',
            'centerline_Y': (L1['startY'] + L2['startY']) / 2,
            'start_X': overlap_start,
            'end_X': overlap_end,
            'thickness_inches': round(distance * 12)
        }
```

### 5b. For vertical line pairs (creates HORIZONTAL walls)
```python
# Sort vertical lines by X coordinate
sorted_by_x = sorted(vertical_lines, key=lambda l: l['startX'])

for each line L1:
    for each nearby line L2 (within next 50 lines):
        distance = abs(L2['startX'] - L1['startX'])

        # RULE: Wall thickness must be 3-14 inches
        if distance < 0.25 or distance > 1.17:
            continue

        # RULE: Lines must overlap in Y direction by at least 2 ft
        y_overlap = calculate_overlap(L1, L2, 'Y')
        if y_overlap < 2.0:
            continue

        # FOUND WALL PAIR!
        wall = {
            'type': 'HORIZONTAL',
            'centerline_X': (L1['startX'] + L2['startX']) / 2,
            'start_Y': overlap_start,
            'end_Y': overlap_end,
            'thickness_inches': round(distance * 12)
        }
```

---

## STEP 6: MAP THICKNESS TO REVIT WALL TYPE

```python
WALL_TYPE_MAP = {
    # thickness_inches: revit_wall_type_id
    4: 26564,      # Generic - 4"
    5: 533588,     # Generic - 5"
    6: 1693,       # Generic - 6"
    8: 1698,       # Generic - 8"
    9: 790343,     # Generic - 9"
    10: 1214289,   # Generic - 10"
    12: 1219224,   # Generic - 12"
}

def get_wall_type_id(thickness_inches):
    # Find closest match
    available = sorted(WALL_TYPE_MAP.keys())
    closest = min(available, key=lambda x: abs(x - thickness_inches))
    return WALL_TYPE_MAP[closest]
```

---

## STEP 7: GENERATE REVIT WALL COMMANDS

```python
for wall in detected_walls:
    if wall['type'] == 'HORIZONTAL':
        start_point = [wall['centerline_X'], wall['start_Y'], 0]
        end_point = [wall['centerline_X'], wall['end_Y'], 0]
    else:  # VERTICAL
        start_point = [wall['start_X'], wall['centerline_Y'], 0]
        end_point = [wall['end_X'], wall['centerline_Y'], 0]

    wall_type_id = get_wall_type_id(wall['thickness_inches'])

    command = {
        "method": "createWall",
        "params": {
            "startPoint": start_point,
            "endPoint": end_point,
            "levelId": LEVEL_ID,
            "wallTypeId": wall_type_id,
            "height": 10
        }
    }
```

---

## STEP 8: SEND TO REVIT VIA MCP BRIDGE

```python
import socket

pipe_name = "RevitMCPBridge2025"  # or 2026

for command in wall_commands:
    # Send JSON command
    writer.write(json.dumps(command))

    # Wait for response
    response = reader.readline()
    result = json.loads(response)

    if result['success']:
        placed_count += 1
    else:
        failed_count += 1
        log_error(result['error'])
```

---

## VALIDATION RULES

After placement, verify:
1. **Wall count**: Number of walls placed vs detected
2. **Coverage**: Visual check that major walls are present
3. **No duplicates**: No overlapping walls at same location
4. **Thickness consistency**: Wall thickness matches CAD

---

## SPECIAL CASES

### Doors and Openings
- Walls should be CONTINUOUS through door locations
- Doors are inserted INTO walls after walls are placed
- If CAD shows broken wall lines at doors, extend walls to connect

### Curved Walls
- Currently not supported by this procedure
- Flag ARC entities on wall layers for manual placement

### Multi-story
- Process each floor's DXF separately
- Use appropriate Level ID for each floor

---

## THICKNESS REFERENCE TABLE

| Inches | Feet | Typical Use |
|--------|------|-------------|
| 4" | 0.333 | Light partition |
| 5" | 0.417 | Interior partition |
| 6" | 0.500 | Standard interior |
| 8" | 0.667 | Structural/CMU |
| 10" | 0.833 | Exterior |
| 12" | 1.000 | Structural exterior |

---

## ERROR HANDLING

| Error | Cause | Solution |
|-------|-------|----------|
| No wall layers found | Non-standard layer naming | Search for layers with most LINE entities |
| Few walls detected | Tolerance too strict | Widen thickness range |
| Duplicate walls | Lines paired multiple times | Track paired lines, skip already-paired |
| Wrong thickness | Rounding error | Use closest available wall type |

---

## COMPLETE PYTHON SCRIPT

See: `/mnt/d/_CLAUDE-TOOLS/dxf_to_revit_walls.py`

---

## VERSION HISTORY

- v1.0 (2026-01-04): Initial procedure created with Bruce Davis
