"""
Wall-first data model for FloorPlanEngine v4.

The WallPlan replaces FloorPlan as the primary representation.
Walls are defined explicitly (not derived from rooms), eliminating
double walls, gaps, and fragments.

Compatible with floorplan-rebuild/schema.json format.

All coordinates are wall CENTERLINES in feet. Origin (0,0) at bottom-left.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
import math


@dataclass
class Wall:
    """A wall segment with explicit start/end coordinates."""
    id: str                          # "W1", "W2", etc.
    start: Tuple[float, float]       # (x, y) in feet
    end: Tuple[float, float]         # (x, y) in feet
    wall_type: str = "interior"      # "exterior", "interior", "partition"
    thickness_in: float = 6.0        # inches
    height_ft: Optional[float] = None  # None = use plan default

    @property
    def x1(self) -> float:
        return self.start[0]

    @property
    def y1(self) -> float:
        return self.start[1]

    @property
    def x2(self) -> float:
        return self.end[0]

    @property
    def y2(self) -> float:
        return self.end[1]

    @property
    def length(self) -> float:
        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        return math.sqrt(dx * dx + dy * dy)

    @property
    def is_horizontal(self) -> bool:
        return abs(self.y2 - self.y1) < 0.01

    @property
    def is_vertical(self) -> bool:
        return abs(self.x2 - self.x1) < 0.01

    @property
    def is_exterior(self) -> bool:
        return self.wall_type == "exterior"

    @property
    def midpoint(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def point_at_offset(self, offset_ft: float) -> Tuple[float, float]:
        """Get (x, y) at a distance along the wall from its start."""
        L = self.length
        if L < 0.001:
            return self.start
        ratio = offset_ft / L
        x = self.x1 + ratio * (self.x2 - self.x1)
        y = self.y1 + ratio * (self.y2 - self.y1)
        return (x, y)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "start": {"x": self.start[0], "y": self.start[1]},
            "end": {"x": self.end[0], "y": self.end[1]},
            "type": self.wall_type,
            "thickness_in": self.thickness_in,
        }
        if self.height_ft is not None:
            d["height_ft"] = self.height_ft
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Wall':
        return cls(
            id=d["id"],
            start=(d["start"]["x"], d["start"]["y"]),
            end=(d["end"]["x"], d["end"]["y"]),
            wall_type=d.get("type", "interior"),
            thickness_in=d.get("thickness_in", 6.0),
            height_ft=d.get("height_ft"),
        )


@dataclass
class Opening:
    """A door or window positioned by offset along a wall."""
    id: str                          # "D1", "WIN1", etc.
    wall_id: str                     # which Wall this is on
    offset_ft: float                 # distance from wall START to near edge
    width_ft: float = 3.0            # opening width
    opening_type: str = "door"       # "door" or "window"
    # Door-specific
    swing: str = "left"              # left/right/double/sliding/pocket/bi-fold/none
    swing_side: str = "positive"     # positive/negative (which side of wall)
    is_entry: bool = False           # entry door flag
    # Window-specific
    sill_height_ft: float = 3.0
    head_height_ft: float = 7.0

    def resolve_position(self, wall: Wall) -> Tuple[float, float]:
        """Compute absolute (x, y) from wall + offset.

        Returns the center point of the opening along the wall.
        """
        center_offset = self.offset_ft + self.width_ft / 2
        return wall.point_at_offset(center_offset)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "wall_id": self.wall_id,
            "offset_ft": self.offset_ft,
            "width_ft": self.width_ft,
        }
        if self.opening_type == "door":
            d["swing"] = self.swing
            d["swing_side"] = self.swing_side
            if self.is_entry:
                d["is_entry"] = True
        else:
            d["sill_height_ft"] = self.sill_height_ft
            d["head_height_ft"] = self.head_height_ft
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any], opening_type: str = "door") -> 'Opening':
        return cls(
            id=d["id"],
            wall_id=d["wall_id"],
            offset_ft=d["offset_ft"],
            width_ft=d.get("width_ft", 3.0),
            opening_type=opening_type,
            swing=d.get("swing", "left"),
            swing_side=d.get("swing_side", "positive"),
            is_entry=d.get("is_entry", False),
            sill_height_ft=d.get("sill_height_ft", 3.0),
            head_height_ft=d.get("head_height_ft", 7.0),
        )


@dataclass
class RoomLabel:
    """A named enclosed space — NOT a geometric rect.

    The room boundary is inferred from surrounding walls.
    """
    name: str
    center: Tuple[float, float]      # (x, y) approximate center
    room_type: str = ""              # maps to RoomType.value if known
    dimensions: str = ""             # "12'-6\" x 14'-0\"" if known
    area_sqft: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "name": self.name,
            "label_position": {"x": self.center[0], "y": self.center[1]},
        }
        if self.room_type:
            d["room_type"] = self.room_type
        if self.dimensions:
            d["dimensions"] = self.dimensions
        if self.area_sqft is not None:
            d["area_sqft"] = self.area_sqft
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'RoomLabel':
        pos = d["label_position"]
        return cls(
            name=d["name"],
            center=(pos["x"], pos["y"]),
            room_type=d.get("room_type", ""),
            dimensions=d.get("dimensions", ""),
            area_sqft=d.get("area_sqft"),
        )


@dataclass
class WallPlan:
    """Wall-first floor plan container.

    Walls are the primary geometric entities.
    Doors/windows reference walls by ID.
    Rooms are labels at center points.
    """
    walls: List[Wall] = field(default_factory=list)
    doors: List[Opening] = field(default_factory=list)
    windows: List[Opening] = field(default_factory=list)
    rooms: List[RoomLabel] = field(default_factory=list)

    # Metadata
    footprint_polygon: List[Tuple[float, float]] = field(default_factory=list)
    overall_width_ft: Optional[float] = None
    overall_depth_ft: Optional[float] = None
    floor_to_ceiling_ft: float = 9.0
    wall_height_ft: float = 10.0
    notes: List[str] = field(default_factory=list)

    # --- Wall lookup ---

    def wall_by_id(self, wall_id: str) -> Optional[Wall]:
        """Get wall by its ID."""
        for w in self.walls:
            if w.id == wall_id:
                return w
        return None

    @property
    def exterior_walls(self) -> List[Wall]:
        return [w for w in self.walls if w.is_exterior]

    @property
    def interior_walls(self) -> List[Wall]:
        return [w for w in self.walls if not w.is_exterior]

    # --- Opening resolution ---

    def resolve_openings(self) -> List[Dict[str, Any]]:
        """Compute absolute (x, y) for all doors and windows.

        Returns list of dicts with 'id', 'type', 'x', 'y', 'wall_id',
        'width_ft', and type-specific fields.
        """
        resolved = []
        for opening in self.doors + self.windows:
            wall = self.wall_by_id(opening.wall_id)
            if wall is None:
                continue
            x, y = opening.resolve_position(wall)
            entry = {
                "id": opening.id,
                "type": opening.opening_type,
                "x": x,
                "y": y,
                "wall_id": opening.wall_id,
                "width_ft": opening.width_ft,
            }
            if opening.opening_type == "door":
                entry["is_entry"] = opening.is_entry
                entry["swing"] = opening.swing
            else:
                entry["sill_height_ft"] = opening.sill_height_ft
                entry["head_height_ft"] = opening.head_height_ft
            resolved.append(entry)
        return resolved

    # --- Serialization (schema.json compatible) ---

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict matching floorplan-rebuild/schema.json."""
        metadata = {
            "units": "feet",
            "floor_to_ceiling_ft": self.floor_to_ceiling_ft,
        }
        if self.overall_width_ft is not None:
            metadata["overall_width_ft"] = self.overall_width_ft
        if self.overall_depth_ft is not None:
            metadata["overall_depth_ft"] = self.overall_depth_ft
        if self.notes:
            metadata["notes"] = list(self.notes)

        d = {
            "metadata": metadata,
            "walls": [w.to_dict() for w in self.walls],
        }
        if self.doors:
            d["doors"] = [door.to_dict() for door in self.doors]
        if self.windows:
            d["windows"] = [win.to_dict() for win in self.windows]
        if self.rooms:
            d["rooms"] = [r.to_dict() for r in self.rooms]
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'WallPlan':
        """Deserialize from schema.json-compatible dict."""
        meta = d.get("metadata", {})

        walls = [Wall.from_dict(w) for w in d.get("walls", [])]
        doors = [Opening.from_dict(dr, "door") for dr in d.get("doors", [])]
        windows = [Opening.from_dict(wn, "window") for wn in d.get("windows", [])]
        rooms = [RoomLabel.from_dict(r) for r in d.get("rooms", [])]

        plan = cls(
            walls=walls,
            doors=doors,
            windows=windows,
            rooms=rooms,
            overall_width_ft=meta.get("overall_width_ft"),
            overall_depth_ft=meta.get("overall_depth_ft"),
            floor_to_ceiling_ft=meta.get("floor_to_ceiling_ft", 9.0),
            notes=meta.get("notes", []),
        )

        # Compute footprint from exterior walls if not provided
        plan.footprint_polygon = plan._compute_footprint()
        return plan

    # --- Bridge to existing FloorPlan ---

    def to_floor_plan(self) -> 'FloorPlan':
        """Convert to existing FloorPlan for reasoning/analysis reuse.

        Creates RoomRects by finding enclosing walls for each room label,
        converts walls to WallSegments, and maps openings to coordinate-based
        door/window placements.
        """
        from .models import (
            FloorPlan, RoomRect, WallSegment, DoorPlacement,
            WindowPlacement, RoomType, Zone
        )
        from .knowledge import ZONE_MAP

        # Convert walls
        wall_segments = []
        for w in self.walls:
            height = w.height_ft if w.height_ft else self.wall_height_ft
            wall_segments.append(WallSegment(
                x1=w.x1, y1=w.y1, x2=w.x2, y2=w.y2,
                is_exterior=w.is_exterior,
                height=height,
            ))

        # Convert room labels to RoomRects by finding enclosing walls
        room_rects = []
        for rl in self.rooms:
            rect = self._find_enclosing_rect(rl)
            if rect is None:
                continue
            x, y, w, h = rect

            # Map room_type string to RoomType enum
            room_type = self._guess_room_type(rl.name, rl.room_type)
            zone = ZONE_MAP.get(room_type, Zone.PUBLIC)

            room_rects.append(RoomRect(
                name=rl.name,
                room_type=room_type,
                zone=zone,
                x=x, y=y, w=w, h=h,
            ))

        # Subdivide overlapping rooms (open-plan rooms that share enclosure)
        self._subdivide_overlapping_rooms(room_rects)

        # Convert openings to coordinate-based placements
        door_placements = []
        window_placements = []

        for opening in self.doors + self.windows:
            wall = self.wall_by_id(opening.wall_id)
            if wall is None:
                continue
            pos = opening.resolve_position(wall)

            # Find the WallSegment this corresponds to
            ws = self._find_matching_wall_segment(wall_segments, wall)

            if opening.opening_type == "door":
                # Find rooms on either side
                room_a, room_b = self._find_rooms_at_door(pos, room_rects)
                door_placements.append(DoorPlacement(
                    location=pos,
                    wall_segment=ws,
                    width_inches=opening.width_ft * 12,
                    height_inches=80.0,
                    room_a=room_a,
                    room_b="exterior" if opening.is_entry else room_b,
                ))
            else:
                room_name = self._find_room_at_point(pos, room_rects)
                window_placements.append(WindowPlacement(
                    location=pos,
                    wall_segment=ws,
                    width_inches=opening.width_ft * 12,
                    height_inches=(opening.head_height_ft - opening.sill_height_ft) * 12,
                    sill_height_inches=opening.sill_height_ft * 12,
                    room_name=room_name,
                ))

        # Compute dimensions
        fp_w = self.overall_width_ft or 0
        fp_h = self.overall_depth_ft or 0
        if not fp_w or not fp_h:
            if self.walls:
                all_x = [w.x1 for w in self.walls] + [w.x2 for w in self.walls]
                all_y = [w.y1 for w in self.walls] + [w.y2 for w in self.walls]
                fp_w = max(all_x) - min(all_x)
                fp_h = max(all_y) - min(all_y)

        total_area = sum(r.area for r in room_rects) if room_rects else fp_w * fp_h
        bedrooms = sum(1 for r in room_rects if r.room_type in (
            RoomType.BEDROOM, RoomType.MASTER_BEDROOM))
        bathrooms = sum(1 for r in room_rects if r.room_type in (
            RoomType.BATHROOM, RoomType.MASTER_BATH, RoomType.HALF_BATH))

        return FloorPlan(
            rooms=room_rects,
            walls=wall_segments,
            doors=door_placements,
            windows=window_placements,
            footprint_width=fp_w,
            footprint_height=fp_h,
            footprint_polygon=list(self.footprint_polygon),
            total_area=total_area,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
        )

    # --- Internal helpers ---

    def _compute_footprint(self) -> List[Tuple[float, float]]:
        """Compute footprint polygon from exterior wall endpoints."""
        ext = self.exterior_walls
        if not ext:
            return []

        # Collect all exterior wall endpoints in order
        # For a simple perimeter, the exterior walls should form a closed loop
        # Just chain start→end for each wall in order
        points = []
        for w in ext:
            points.append(w.start)
        # Close the loop
        if ext:
            points.append(ext[-1].end)
        # Remove duplicate closing point if first == last
        if len(points) > 1 and points[0] == points[-1]:
            points = points[:-1]
        return points

    def _find_enclosing_rect(self, room: RoomLabel) -> Optional[Tuple[float, float, float, float]]:
        """Find bounding rect for a room label by ray-casting to walls.

        Casts rays in 4 cardinal directions from the room center
        and finds the nearest wall in each direction.

        Returns (x, y, width, height) or None.
        """
        cx, cy = room.center

        # Find nearest wall in each direction
        left = self._ray_cast_to_wall(cx, cy, -1, 0)    # -x
        right = self._ray_cast_to_wall(cx, cy, +1, 0)   # +x
        down = self._ray_cast_to_wall(cx, cy, 0, -1)    # -y
        up = self._ray_cast_to_wall(cx, cy, 0, +1)      # +y

        if None in (left, right, down, up):
            # Fallback: use area if available
            if room.area_sqft:
                side = math.sqrt(room.area_sqft)
                return (cx - side / 2, cy - side / 2, side, side)
            return None

        return (left, down, right - left, up - down)

    def _ray_cast_to_wall(self, cx: float, cy: float,
                          dx: int, dy: int) -> Optional[float]:
        """Cast a ray from (cx, cy) in direction (dx, dy) and find nearest wall intersection.

        dx, dy should be -1, 0, or +1 (cardinal directions only).
        Returns the coordinate of the nearest wall (x for horizontal rays, y for vertical rays).
        """
        best = None

        for w in self.walls:
            if dx != 0 and dy == 0:
                # Horizontal ray — looking for vertical walls
                if not w.is_vertical:
                    continue
                wall_x = w.x1
                wall_y_lo = min(w.y1, w.y2)
                wall_y_hi = max(w.y1, w.y2)
                # Wall must span our y position
                if cy < wall_y_lo - 0.1 or cy > wall_y_hi + 0.1:
                    continue
                # Wall must be in the right direction
                if dx > 0 and wall_x <= cx + 0.1:
                    continue
                if dx < 0 and wall_x >= cx - 0.1:
                    continue
                dist = abs(wall_x - cx)
                if best is None or dist < abs(best - cx):
                    best = wall_x

            elif dy != 0 and dx == 0:
                # Vertical ray — looking for horizontal walls
                if not w.is_horizontal:
                    continue
                wall_y = w.y1
                wall_x_lo = min(w.x1, w.x2)
                wall_x_hi = max(w.x1, w.x2)
                # Wall must span our x position
                if cx < wall_x_lo - 0.1 or cx > wall_x_hi + 0.1:
                    continue
                # Wall must be in the right direction
                if dy > 0 and wall_y <= cy + 0.1:
                    continue
                if dy < 0 and wall_y >= cy - 0.1:
                    continue
                dist = abs(wall_y - cy)
                if best is None or dist < abs(best - cy):
                    best = wall_y

        return best

    def _subdivide_overlapping_rooms(self, room_rects) -> None:
        """Subdivide rooms that got identical bounds from ray-casting.

        This happens with open-plan rooms (Living/Kitchen/Dining) that share
        the same enclosed space with no interior walls between them.
        Splits the shared rect proportionally based on label positions and areas.
        """
        from collections import defaultdict

        # Group by bounds (rounded to 0.1ft)
        groups = defaultdict(list)
        for i, r in enumerate(room_rects):
            key = (round(r.x, 1), round(r.y, 1), round(r.w, 1), round(r.h, 1))
            groups[key].append(i)

        # Build label lookup for original centers and areas
        label_map = {rl.name: rl for rl in self.rooms}

        for key, indices in groups.items():
            if len(indices) <= 1:
                continue

            x, y, w, h = key
            rooms = [(idx, room_rects[idx]) for idx in indices]

            # Get areas from original labels (or equal split)
            areas = []
            for idx, r in rooms:
                rl = label_map.get(r.name)
                areas.append(rl.area_sqft if rl and rl.area_sqft else w * h / len(rooms))
            total_a = sum(areas) or 1.0

            if w >= h:
                # Subdivide horizontally — sort by label x position
                rooms.sort(key=lambda pair: label_map.get(pair[1].name, pair[1]).center[0]
                           if label_map.get(pair[1].name) else pair[1].cx)
                cursor = x
                for j, (idx, r) in enumerate(rooms):
                    if j == len(rooms) - 1:
                        sub_w = (x + w) - cursor
                    else:
                        sub_w = w * areas[j] / total_a
                    room_rects[idx] = type(r)(
                        name=r.name, room_type=r.room_type, zone=r.zone,
                        x=cursor, y=y, w=sub_w, h=h)
                    cursor += sub_w
            else:
                # Subdivide vertically — sort by label y position
                rooms.sort(key=lambda pair: label_map.get(pair[1].name, pair[1]).center[1]
                           if label_map.get(pair[1].name) else pair[1].cy)
                cursor = y
                for j, (idx, r) in enumerate(rooms):
                    if j == len(rooms) - 1:
                        sub_h = (y + h) - cursor
                    else:
                        sub_h = h * areas[j] / total_a
                    room_rects[idx] = type(r)(
                        name=r.name, room_type=r.room_type, zone=r.zone,
                        x=x, y=cursor, w=w, h=sub_h)
                    cursor += sub_h

    def _find_matching_wall_segment(self, segments, wall: Wall):
        """Find the WallSegment that matches a Wall's coordinates."""
        for ws in segments:
            if (abs(ws.x1 - wall.x1) < 0.1 and abs(ws.y1 - wall.y1) < 0.1 and
                    abs(ws.x2 - wall.x2) < 0.1 and abs(ws.y2 - wall.y2) < 0.1):
                return ws
        # Fallback: return first segment (won't crash, just imprecise)
        from .models import WallSegment
        return WallSegment(wall.x1, wall.y1, wall.x2, wall.y2,
                           is_exterior=wall.is_exterior)

    def _find_rooms_at_door(self, pos, room_rects) -> Tuple[str, str]:
        """Find the two rooms on either side of a door position."""
        nearby = []
        px, py = pos
        for r in room_rects:
            if r.x - 0.5 <= px <= r.right + 0.5 and r.y - 0.5 <= py <= r.top + 0.5:
                dist = abs(px - r.cx) + abs(py - r.cy)
                nearby.append((dist, r.name))
        nearby.sort()
        if len(nearby) >= 2:
            return nearby[0][1], nearby[1][1]
        elif len(nearby) == 1:
            return nearby[0][1], ""
        return "", ""

    def _find_room_at_point(self, pos, room_rects) -> str:
        """Find which room contains a point."""
        px, py = pos
        best_dist = float('inf')
        best_name = ""
        for r in room_rects:
            dist = abs(px - r.cx) + abs(py - r.cy)
            if dist < best_dist:
                best_dist = dist
                best_name = r.name
        return best_name

    @staticmethod
    def _guess_room_type(name: str, room_type_str: str = "") -> 'RoomType':
        """Guess RoomType from name or explicit type string."""
        from .models import RoomType

        # Try explicit type string first
        if room_type_str:
            for rt in RoomType:
                if rt.value == room_type_str:
                    return rt

        # Guess from name
        name_lower = name.lower()
        mapping = [
            ("master bed", RoomType.MASTER_BEDROOM),
            ("master bath", RoomType.MASTER_BATH),
            ("half bath", RoomType.HALF_BATH),
            ("walk-in closet", RoomType.WALK_IN_CLOSET),
            ("walk in closet", RoomType.WALK_IN_CLOSET),
            ("wardrobe", RoomType.WALK_IN_CLOSET),
            ("family room", RoomType.FAMILY_ROOM),
            ("family", RoomType.FAMILY_ROOM),
            ("great room", RoomType.LIVING),
            ("living", RoomType.LIVING),
            ("kitchen", RoomType.KITCHEN),
            ("dining", RoomType.DINING),
            ("entry", RoomType.ENTRY),
            ("foyer", RoomType.ENTRY),
            ("bedroom", RoomType.BEDROOM),
            ("bath", RoomType.BATHROOM),
            ("laundry", RoomType.LAUNDRY),
            ("hallway", RoomType.HALLWAY),
            ("hall", RoomType.HALLWAY),
            ("corridor", RoomType.HALLWAY),
            ("closet", RoomType.CLOSET),
            ("pantry", RoomType.PANTRY),
            ("office", RoomType.OFFICE),
            ("study", RoomType.OFFICE),
            ("garage", RoomType.GARAGE),
        ]
        for keyword, rtype in mapping:
            if keyword in name_lower:
                return rtype

        return RoomType.LIVING  # fallback
