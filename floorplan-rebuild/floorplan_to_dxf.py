#!/usr/bin/env python3
"""
Floor Plan to DXF - Exact Geometric Reconstruction

Converts a structured JSON floor plan model into a perfect DXF file.
NO guessing, NO approximation - only draws what's explicitly defined.

Pipeline: Image/PDF → [AI Vision → JSON] → THIS PROGRAM → Perfect DXF → Revit

Usage:
    python floorplan_to_dxf.py input.json [output.dxf]
    python floorplan_to_dxf.py input.json --validate-only
"""

import json
import math
import sys
import os
from dataclasses import dataclass, field
from typing import Optional

try:
    import ezdxf
    from ezdxf.math import Vec2
except ImportError:
    print("ERROR: ezdxf not installed. Run: pip install ezdxf")
    sys.exit(1)


# ─────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────

@dataclass
class Point:
    x: float
    y: float

    def to_tuple(self):
        return (self.x, self.y)

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        return Point(self.x * scalar, self.y * scalar)

    def length(self):
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalized(self):
        ln = self.length()
        if ln < 1e-10:
            return Point(0, 0)
        return Point(self.x / ln, self.y / ln)

    def perpendicular(self):
        """Returns the left-hand perpendicular (CCW 90 degrees)."""
        return Point(-self.y, self.x)


@dataclass
class WallDef:
    id: str
    start: Point
    end: Point
    thickness_in: float = 6.0
    wall_type: str = "interior"
    height_ft: float = 9.0

    @property
    def thickness_ft(self):
        return self.thickness_in / 12.0

    @property
    def direction(self):
        return (self.end - self.start).normalized()

    @property
    def perpendicular(self):
        return self.direction.perpendicular()

    @property
    def length_ft(self):
        return (self.end - self.start).length()


@dataclass
class DoorDef:
    id: str
    wall_id: str
    offset_ft: float
    width_ft: float = 3.0
    swing: str = "left"
    swing_side: str = "positive"


@dataclass
class WindowDef:
    id: str
    wall_id: str
    offset_ft: float
    width_ft: float = 3.0
    sill_height_ft: float = 3.0
    head_height_ft: float = 7.0


@dataclass
class RoomDef:
    name: str
    label_position: Point
    dimensions: str = ""
    area_sqft: float = 0.0


@dataclass
class DimDef:
    start: Point
    end: Point
    text: str
    offset_ft: float = 2.0


@dataclass
class Opening:
    """Represents an opening (door or window) cut into a wall."""
    offset_ft: float
    width_ft: float
    obj_type: str  # "door" or "window"
    definition: object  # DoorDef or WindowDef


# ─────────────────────────────────────────────
# Layer Configuration
# ─────────────────────────────────────────────

LAYERS = {
    "A-WALL": {"color": 7, "description": "Walls"},
    "A-WALL-EXTR": {"color": 3, "description": "Exterior walls"},
    "A-DOOR": {"color": 1, "description": "Doors"},
    "A-GLAZ": {"color": 5, "description": "Windows/Glazing"},
    "A-AREA-IDEN": {"color": 2, "description": "Room labels"},
    "A-ANNO-DIMS": {"color": 4, "description": "Dimensions"},
    "A-ANNO-NOTE": {"color": 8, "description": "Notes"},
}


# ─────────────────────────────────────────────
# JSON Loader
# ─────────────────────────────────────────────

def load_floorplan(json_path: str) -> dict:
    """Load and validate the floor plan JSON."""
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Basic validation
    if "walls" not in data or len(data["walls"]) == 0:
        raise ValueError("Floor plan must have at least one wall")

    if "metadata" not in data:
        raise ValueError("Floor plan must have metadata section")

    return data


def parse_walls(data: dict, default_height: float) -> list:
    """Parse wall definitions from JSON."""
    walls = []
    for w in data.get("walls", []):
        wall = WallDef(
            id=w["id"],
            start=Point(w["start"]["x"], w["start"]["y"]),
            end=Point(w["end"]["x"], w["end"]["y"]),
            thickness_in=w.get("thickness_in", 6.0),
            wall_type=w.get("type", "interior"),
            height_ft=w.get("height_ft", default_height),
        )
        walls.append(wall)
    return walls


def parse_doors(data: dict) -> list:
    """Parse door definitions from JSON."""
    doors = []
    for d in data.get("doors", []):
        door = DoorDef(
            id=d["id"],
            wall_id=d["wall_id"],
            offset_ft=d["offset_ft"],
            width_ft=d.get("width_ft", 3.0),
            swing=d.get("swing", "left"),
            swing_side=d.get("swing_side", "positive"),
        )
        doors.append(door)
    return doors


def parse_windows(data: dict) -> list:
    """Parse window definitions from JSON."""
    windows = []
    for w in data.get("windows", []):
        win = WindowDef(
            id=w["id"],
            wall_id=w["wall_id"],
            offset_ft=w["offset_ft"],
            width_ft=w.get("width_ft", 3.0),
            sill_height_ft=w.get("sill_height_ft", 3.0),
            head_height_ft=w.get("head_height_ft", 7.0),
        )
        windows.append(win)
    return windows


def parse_rooms(data: dict) -> list:
    """Parse room definitions from JSON."""
    rooms = []
    for r in data.get("rooms", []):
        room = RoomDef(
            name=r["name"],
            label_position=Point(r["label_position"]["x"], r["label_position"]["y"]),
            dimensions=r.get("dimensions", ""),
            area_sqft=r.get("area_sqft", 0.0),
        )
        rooms.append(room)
    return rooms


def parse_dimensions(data: dict) -> list:
    """Parse dimension definitions from JSON."""
    dims = []
    for d in data.get("dimensions", []):
        dim = DimDef(
            start=Point(d["start"]["x"], d["start"]["y"]),
            end=Point(d["end"]["x"], d["end"]["y"]),
            text=d["text"],
            offset_ft=d.get("offset_ft", 2.0),
        )
        dims.append(dim)
    return dims


# ─────────────────────────────────────────────
# Geometric Construction
# ─────────────────────────────────────────────

def compute_wall_faces(wall: WallDef):
    """
    Compute the two face lines (inner and outer) of a wall
    from its centerline and thickness.

    Returns: (left_face_start, left_face_end, right_face_start, right_face_end)
    All as Point objects.
    """
    half_t = wall.thickness_ft / 2.0
    perp = wall.perpendicular

    offset = perp * half_t

    left_start = wall.start + offset
    left_end = wall.end + offset
    right_start = wall.start - offset
    right_end = wall.end - offset

    return left_start, left_end, right_start, right_end


def compute_openings_for_wall(wall: WallDef, doors: list, windows: list) -> list:
    """
    Collect all openings (doors and windows) on a given wall,
    sorted by offset along the wall.
    """
    openings = []

    for door in doors:
        if door.wall_id == wall.id:
            openings.append(Opening(
                offset_ft=door.offset_ft,
                width_ft=door.width_ft,
                obj_type="door",
                definition=door,
            ))

    for win in windows:
        if win.wall_id == wall.id:
            openings.append(Opening(
                offset_ft=win.offset_ft,
                width_ft=win.width_ft,
                obj_type="window",
                definition=win,
            ))

    openings.sort(key=lambda o: o.offset_ft)
    return openings


def split_line_at_openings(line_start: Point, line_end: Point,
                           wall_start: Point, wall_dir: Point,
                           openings: list) -> list:
    """
    Split a face line into segments, creating gaps where openings are.

    Returns a list of (start_point, end_point) tuples for the visible
    wall segments.
    """
    if not openings:
        return [(line_start, line_end)]

    # Compute the perpendicular offset of this face line from the wall centerline
    # We need to project the face line points back along the wall direction
    # to figure out where to cut.

    segments = []
    wall_length = (wall_dir).length()

    # Work in parameter space along the wall direction
    # The face line is parallel to the wall, so we just need the
    # offsets along the wall direction
    dir_normalized = wall_dir.normalized() if wall_length > 0 else Point(1, 0)

    # Perpendicular offset from centerline to this face
    perp_offset = line_start - wall_start
    # This offset should be purely perpendicular to the wall direction
    # We just need it to reconstruct points

    current_param = 0.0  # start of wall

    for opening in openings:
        gap_start = opening.offset_ft
        gap_end = opening.offset_ft + opening.width_ft

        # Add wall segment from current position to gap start
        if gap_start > current_param + 0.001:
            seg_start = wall_start + dir_normalized * current_param + perp_offset
            seg_end = wall_start + dir_normalized * gap_start + perp_offset
            segments.append((seg_start, seg_end))

        current_param = gap_end

    # Add remaining wall segment after last opening
    total_length = (line_end - line_start).length()
    # Use the actual wall length from start to end
    wall_total = wall_length if wall_length > 0 else total_length

    if current_param < wall_total - 0.001:
        seg_start = wall_start + dir_normalized * current_param + perp_offset
        seg_end = wall_start + dir_normalized * wall_total + perp_offset
        segments.append((seg_start, seg_end))

    return segments


def compute_door_geometry(wall: WallDef, door: DoorDef):
    """
    Compute door swing arc geometry.

    Returns: (hinge_point, arc_end_point, arc_center, arc_radius, start_angle, end_angle)
    """
    d = wall.direction
    perp = wall.perpendicular

    # Door opening along the wall
    opening_start = wall.start + d * door.offset_ft
    opening_end = wall.start + d * (door.offset_ft + door.width_ft)

    # Determine hinge and swing
    if door.swing == "left":
        hinge = opening_start
        free_end = opening_end
    elif door.swing == "right":
        hinge = opening_end
        free_end = opening_start
    else:
        # For sliding, pocket, bi-fold, double - just mark the opening, no arc
        return None

    # Swing direction (which side of the wall)
    swing_mult = 1.0 if door.swing_side == "positive" else -1.0
    swing_perp = perp * swing_mult

    # Arc from free_end position swinging 90 degrees perpendicular to wall
    arc_end = hinge + swing_perp * door.width_ft

    # Calculate angles for the arc
    # The arc goes from the direction of free_end relative to hinge
    # to the direction of arc_end relative to hinge
    dx1 = free_end.x - hinge.x
    dy1 = free_end.y - hinge.y
    dx2 = arc_end.x - hinge.x
    dy2 = arc_end.y - hinge.y

    angle1 = math.degrees(math.atan2(dy1, dx1))
    angle2 = math.degrees(math.atan2(dy2, dx2))

    # Ensure we draw the shorter arc (90 degrees)
    # Normalize angles
    if angle1 < 0:
        angle1 += 360
    if angle2 < 0:
        angle2 += 360

    # The arc should be 90 degrees. Determine direction.
    diff = (angle2 - angle1) % 360
    if diff > 180:
        # Swap to get the short arc
        angle1, angle2 = angle2, angle1

    return {
        "hinge": hinge,
        "free_end": free_end,
        "arc_end": arc_end,
        "radius": door.width_ft,
        "start_angle": angle1,
        "end_angle": angle2,
        "door_line_start": hinge,
        "door_line_end": arc_end,
    }


def compute_window_geometry(wall: WallDef, window: WindowDef):
    """
    Compute window plan representation (3 parallel lines in the opening).

    Returns dict with line positions for the window symbol.
    """
    d = wall.direction
    perp = wall.perpendicular
    half_t = wall.thickness_ft / 2.0

    # Window position along wall
    win_start_along = window.offset_ft
    win_end_along = window.offset_ft + window.width_ft

    p_start = wall.start + d * win_start_along
    p_end = wall.start + d * win_end_along

    # Three lines across the wall thickness representing the window
    # Center line (glass)
    glass_start = p_start
    glass_end = p_end

    # Frame lines offset from center
    frame_offset = half_t * 0.6  # frame lines at 60% of half-thickness
    frame1_start = p_start + perp * frame_offset
    frame1_end = p_end + perp * frame_offset
    frame2_start = p_start - perp * frame_offset
    frame2_end = p_end - perp * frame_offset

    # End caps connecting the frame lines
    cap1_inner = p_start + perp * half_t
    cap1_outer = p_start - perp * half_t
    cap2_inner = p_end + perp * half_t
    cap2_outer = p_end - perp * half_t

    return {
        "glass": (glass_start, glass_end),
        "frame1": (frame1_start, frame1_end),
        "frame2": (frame2_start, frame2_end),
        "cap1": (cap1_inner, cap1_outer),
        "cap2": (cap2_inner, cap2_outer),
    }


# ─────────────────────────────────────────────
# DXF Writer
# ─────────────────────────────────────────────

def create_dxf(walls: list, doors: list, windows: list,
               rooms: list, dims: list, metadata: dict) -> ezdxf.document.Drawing:
    """
    Create a complete DXF document from the floor plan model.
    """
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Set up units (decimal feet)
    doc.header["$INSUNITS"] = 2  # Feet
    doc.header["$LUNITS"] = 2   # Decimal
    doc.header["$LUPREC"] = 4   # 4 decimal places

    # Create layers
    for layer_name, props in LAYERS.items():
        doc.layers.add(layer_name, color=props["color"])

    # Index walls by ID for quick lookup
    wall_map = {w.id: w for w in walls}

    # ── Draw Walls ──
    for wall in walls:
        layer = "A-WALL-EXTR" if wall.wall_type == "exterior" else "A-WALL"

        # Get all openings on this wall
        openings = compute_openings_for_wall(wall, doors, windows)

        # Validate openings don't exceed wall length
        for op in openings:
            if op.offset_ft + op.width_ft > wall.length_ft + 0.01:
                print(f"  WARNING: Opening at offset {op.offset_ft}' + width {op.width_ft}' "
                      f"exceeds wall {wall.id} length {wall.length_ft:.2f}'")

        # Compute wall faces
        left_start, left_end, right_start, right_end = compute_wall_faces(wall)

        # Perpendicular offset from wall start to left face start
        perp_offset_left = left_start - wall.start
        perp_offset_right = right_start - wall.start
        wall_dir = wall.direction

        # Split face lines at openings
        left_segments = split_face_line(wall, perp_offset_left, openings)
        right_segments = split_face_line(wall, perp_offset_right, openings)

        # Draw wall face segments
        for seg_start, seg_end in left_segments:
            msp.add_line(seg_start.to_tuple(), seg_end.to_tuple(), dxfattribs={"layer": layer})

        for seg_start, seg_end in right_segments:
            msp.add_line(seg_start.to_tuple(), seg_end.to_tuple(), dxfattribs={"layer": layer})

        # Draw wall end caps (connect left face to right face at each end)
        # Only draw caps where there's no opening at the very start/end
        has_opening_at_start = any(op.offset_ft < 0.01 for op in openings)
        has_opening_at_end = any(
            abs(op.offset_ft + op.width_ft - wall.length_ft) < 0.01 for op in openings
        )

        if not has_opening_at_start:
            msp.add_line(left_start.to_tuple(), right_start.to_tuple(),
                         dxfattribs={"layer": layer})
        if not has_opening_at_end:
            msp.add_line(left_end.to_tuple(), right_end.to_tuple(),
                         dxfattribs={"layer": layer})

    # ── Draw Doors ──
    for door in doors:
        if door.wall_id not in wall_map:
            print(f"  WARNING: Door {door.id} references unknown wall {door.wall_id}")
            continue

        wall = wall_map[door.wall_id]
        geom = compute_door_geometry(wall, door)

        if geom is None:
            # Sliding/pocket/etc - just mark the opening (already handled by wall gaps)
            continue

        # Draw door leaf line (closed position representation)
        msp.add_line(
            geom["door_line_start"].to_tuple(),
            geom["door_line_end"].to_tuple(),
            dxfattribs={"layer": "A-DOOR"}
        )

        # Draw swing arc
        msp.add_arc(
            center=geom["hinge"].to_tuple(),
            radius=geom["radius"],
            start_angle=geom["start_angle"],
            end_angle=geom["end_angle"],
            dxfattribs={"layer": "A-DOOR"}
        )

    # ── Draw Windows ──
    for window in windows:
        if window.wall_id not in wall_map:
            print(f"  WARNING: Window {window.id} references unknown wall {window.wall_id}")
            continue

        wall = wall_map[window.wall_id]
        geom = compute_window_geometry(wall, window)

        # Glass line (center)
        msp.add_line(
            geom["glass"][0].to_tuple(),
            geom["glass"][1].to_tuple(),
            dxfattribs={"layer": "A-GLAZ"}
        )

        # Frame lines
        msp.add_line(
            geom["frame1"][0].to_tuple(),
            geom["frame1"][1].to_tuple(),
            dxfattribs={"layer": "A-GLAZ"}
        )
        msp.add_line(
            geom["frame2"][0].to_tuple(),
            geom["frame2"][1].to_tuple(),
            dxfattribs={"layer": "A-GLAZ"}
        )

        # End caps
        msp.add_line(
            geom["cap1"][0].to_tuple(),
            geom["cap1"][1].to_tuple(),
            dxfattribs={"layer": "A-GLAZ"}
        )
        msp.add_line(
            geom["cap2"][0].to_tuple(),
            geom["cap2"][1].to_tuple(),
            dxfattribs={"layer": "A-GLAZ"}
        )

    # ── Draw Room Labels ──
    for room in rooms:
        text_height = 0.5  # 6 inches in feet
        label = room.name
        if room.dimensions:
            label += f"\n{room.dimensions}"

        msp.add_text(
            room.name,
            dxfattribs={
                "layer": "A-AREA-IDEN",
                "height": text_height,
                "halign": 1,  # center
            }
        ).set_placement(room.label_position.to_tuple(), align=ezdxf.enums.TextEntityAlignment.CENTER)

        # Add dimensions below room name if present
        if room.dimensions:
            dim_pos = Point(room.label_position.x, room.label_position.y - text_height * 1.5)
            msp.add_text(
                room.dimensions,
                dxfattribs={
                    "layer": "A-AREA-IDEN",
                    "height": text_height * 0.7,
                    "halign": 1,
                }
            ).set_placement(dim_pos.to_tuple(), align=ezdxf.enums.TextEntityAlignment.CENTER)

    # ── Draw Dimensions ──
    for dim in dims:
        # Compute dimension direction and perpendicular
        d = (dim.end - dim.start)
        d_norm = d.normalized()
        perp = d_norm.perpendicular()

        offset_vec = perp * dim.offset_ft

        # Dimension line endpoints (offset from the measured points)
        dim_start = dim.start + offset_vec
        dim_end = dim.end + offset_vec

        # Extension lines
        msp.add_line(dim.start.to_tuple(), dim_start.to_tuple(),
                      dxfattribs={"layer": "A-ANNO-DIMS"})
        msp.add_line(dim.end.to_tuple(), dim_end.to_tuple(),
                      dxfattribs={"layer": "A-ANNO-DIMS"})

        # Dimension line
        msp.add_line(dim_start.to_tuple(), dim_end.to_tuple(),
                      dxfattribs={"layer": "A-ANNO-DIMS"})

        # Dimension text at midpoint
        mid = Point((dim_start.x + dim_end.x) / 2,
                     (dim_start.y + dim_end.y) / 2)

        # Calculate text angle to align with dimension line
        angle = math.degrees(math.atan2(d.y, d.x))
        if angle > 90 or angle < -90:
            angle += 180  # Keep text readable

        text_offset = perp * 0.3
        text_pos = mid + text_offset

        msp.add_text(
            dim.text,
            dxfattribs={
                "layer": "A-ANNO-DIMS",
                "height": 0.25,
                "rotation": angle,
                "halign": 1,
            }
        ).set_placement(text_pos.to_tuple(), align=ezdxf.enums.TextEntityAlignment.CENTER)

    # ── Add metadata as notes ──
    notes = metadata.get("notes", [])
    if notes:
        note_y = -3.0  # Below the plan
        for note in notes:
            msp.add_text(
                f"NOTE: {note}",
                dxfattribs={
                    "layer": "A-ANNO-NOTE",
                    "height": 0.25,
                }
            ).set_placement((0, note_y))
            note_y -= 0.5

    return doc


def split_face_line(wall: WallDef, perp_offset: Point, openings: list) -> list:
    """
    Split a wall face line at opening locations.

    Args:
        wall: The wall definition
        perp_offset: Perpendicular offset from wall start to this face line start
        openings: List of openings on this wall, sorted by offset

    Returns:
        List of (start_point, end_point) for visible wall segments
    """
    d = wall.direction
    segments = []
    current_pos = 0.0

    for opening in openings:
        gap_start = opening.offset_ft
        gap_end = opening.offset_ft + opening.width_ft

        # Wall segment before this opening
        if gap_start > current_pos + 0.001:
            seg_start = wall.start + d * current_pos + perp_offset
            seg_end = wall.start + d * gap_start + perp_offset
            segments.append((seg_start, seg_end))

        current_pos = gap_end

    # Wall segment after last opening
    if current_pos < wall.length_ft - 0.001:
        seg_start = wall.start + d * current_pos + perp_offset
        seg_end = wall.start + d * wall.length_ft + perp_offset
        segments.append((seg_start, seg_end))

    return segments


# ─────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────

def validate_model(data: dict) -> list:
    """
    Validate the floor plan model for consistency.
    Returns a list of issues found.
    """
    issues = []

    walls = data.get("walls", [])
    doors = data.get("doors", [])
    windows = data.get("windows", [])

    wall_ids = {w["id"] for w in walls}

    # Check wall lengths
    for w in walls:
        dx = w["end"]["x"] - w["start"]["x"]
        dy = w["end"]["y"] - w["start"]["y"]
        length = math.sqrt(dx * dx + dy * dy)
        if length < 0.5:
            issues.append(f"Wall {w['id']}: very short ({length:.2f} ft)")
        if length > 200:
            issues.append(f"Wall {w['id']}: suspiciously long ({length:.2f} ft)")

    # Check doors reference valid walls
    for d in doors:
        if d["wall_id"] not in wall_ids:
            issues.append(f"Door {d['id']}: references non-existent wall {d['wall_id']}")
        else:
            # Check door fits within wall
            wall = next(w for w in walls if w["id"] == d["wall_id"])
            dx = wall["end"]["x"] - wall["start"]["x"]
            dy = wall["end"]["y"] - wall["start"]["y"]
            wall_len = math.sqrt(dx * dx + dy * dy)
            if d["offset_ft"] + d.get("width_ft", 3.0) > wall_len + 0.01:
                issues.append(
                    f"Door {d['id']}: offset {d['offset_ft']}' + width {d.get('width_ft', 3.0)}' "
                    f"exceeds wall {d['wall_id']} length {wall_len:.2f}'"
                )
            if d["offset_ft"] < 0:
                issues.append(f"Door {d['id']}: negative offset {d['offset_ft']}'")

    # Check windows reference valid walls
    for w in windows:
        if w["wall_id"] not in wall_ids:
            issues.append(f"Window {w['id']}: references non-existent wall {w['wall_id']}")
        else:
            wall = next(wl for wl in walls if wl["id"] == w["wall_id"])
            dx = wall["end"]["x"] - wall["start"]["x"]
            dy = wall["end"]["y"] - wall["start"]["y"]
            wall_len = math.sqrt(dx * dx + dy * dy)
            if w["offset_ft"] + w.get("width_ft", 3.0) > wall_len + 0.01:
                issues.append(
                    f"Window {w['id']}: offset {w['offset_ft']}' + width {w.get('width_ft', 3.0)}' "
                    f"exceeds wall {w['wall_id']} length {wall_len:.2f}'"
                )

    # Check for duplicate IDs
    all_wall_ids = [w["id"] for w in walls]
    if len(all_wall_ids) != len(set(all_wall_ids)):
        issues.append("Duplicate wall IDs found")

    all_door_ids = [d["id"] for d in doors]
    if len(all_door_ids) != len(set(all_door_ids)):
        issues.append("Duplicate door IDs found")

    all_win_ids = [w["id"] for w in windows]
    if len(all_win_ids) != len(set(all_win_ids)):
        issues.append("Duplicate window IDs found")

    # Check for overlapping openings on same wall
    for wall_id in wall_ids:
        wall_openings = []
        for d in doors:
            if d["wall_id"] == wall_id:
                wall_openings.append((d["offset_ft"], d["offset_ft"] + d.get("width_ft", 3.0), f"Door {d['id']}"))
        for w in windows:
            if w["wall_id"] == wall_id:
                wall_openings.append((w["offset_ft"], w["offset_ft"] + w.get("width_ft", 3.0), f"Window {w['id']}"))

        wall_openings.sort(key=lambda x: x[0])
        for i in range(len(wall_openings) - 1):
            if wall_openings[i][1] > wall_openings[i + 1][0] + 0.01:
                issues.append(
                    f"Overlapping openings on wall {wall_id}: "
                    f"{wall_openings[i][2]} and {wall_openings[i+1][2]}"
                )

    return issues


# ─────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────

def print_report(walls, doors, windows, rooms, dims, metadata):
    """Print a summary of what will be drawn."""
    print("\n" + "=" * 60)
    print("  FLOOR PLAN TO DXF - Exact Geometric Reconstruction")
    print("=" * 60)

    if metadata.get("source_file"):
        print(f"  Source: {metadata['source_file']}")
    if metadata.get("scale"):
        print(f"  Scale:  {metadata['scale']}")
    if metadata.get("overall_width_ft") and metadata.get("overall_depth_ft"):
        print(f"  Size:   {metadata['overall_width_ft']}' x {metadata['overall_depth_ft']}'")
    print(f"  Height: {metadata.get('floor_to_ceiling_ft', 9.0)}'")

    print(f"\n  Walls:      {len(walls)}")
    for w in walls:
        print(f"    {w.id}: ({w.start.x:.2f}, {w.start.y:.2f}) → ({w.end.x:.2f}, {w.end.y:.2f}) "
              f"[{w.length_ft:.2f}' {w.wall_type} {w.thickness_in}\" thick]")

    print(f"\n  Doors:      {len(doors)}")
    for d in doors:
        print(f"    {d.id}: on {d.wall_id}, offset {d.offset_ft}', width {d.width_ft}', swing {d.swing}")

    print(f"\n  Windows:    {len(windows)}")
    for w in windows:
        print(f"    {w.id}: on {w.wall_id}, offset {w.offset_ft}', width {w.width_ft}'")

    print(f"\n  Rooms:      {len(rooms)}")
    for r in rooms:
        print(f"    {r.name} at ({r.label_position.x:.1f}, {r.label_position.y:.1f})")

    print(f"  Dimensions: {len(dims)}")

    notes = metadata.get("notes", [])
    if notes:
        print(f"\n  NOTES (require verification):")
        for note in notes:
            print(f"    ! {note}")

    print("=" * 60)


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def build_dxf(json_path: str, output_path: str = None, validate_only: bool = False):
    """
    Main entry point: load JSON, validate, build DXF.
    """
    # Load
    print(f"\nLoading: {json_path}")
    data = load_floorplan(json_path)
    metadata = data.get("metadata", {})
    default_height = metadata.get("floor_to_ceiling_ft", 9.0)

    # Parse
    walls = parse_walls(data, default_height)
    doors = parse_doors(data)
    windows = parse_windows(data)
    rooms = parse_rooms(data)
    dims = parse_dimensions(data)

    # Report
    print_report(walls, doors, windows, rooms, dims, metadata)

    # Validate
    issues = validate_model(data)
    if issues:
        print(f"\n  VALIDATION ISSUES:")
        for issue in issues:
            print(f"    ✗ {issue}")
        print()

    if validate_only:
        if issues:
            print("  Validation FAILED - fix issues before generating DXF")
            return False
        else:
            print("  Validation PASSED")
            return True

    if issues:
        print("  Proceeding despite warnings...")

    # Build DXF
    if output_path is None:
        base = os.path.splitext(json_path)[0]
        output_path = base + ".dxf"

    print(f"\n  Generating DXF: {output_path}")
    doc = create_dxf(walls, doors, windows, rooms, dims, metadata)
    doc.saveas(output_path)

    # Summary
    entity_count = len(list(doc.modelspace()))
    print(f"  Done! {entity_count} entities written.")
    print(f"  Output: {output_path}")
    print(f"  Units: feet (ready for Revit import)\n")

    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    json_path = sys.argv[1]
    validate_only = "--validate-only" in sys.argv

    output_path = None
    for arg in sys.argv[2:]:
        if not arg.startswith("--") and arg.endswith(".dxf"):
            output_path = arg

    success = build_dxf(json_path, output_path, validate_only)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
