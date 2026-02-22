"""
Explicit floor plan builder — define every element manually.

Fluent API for creating floor plans by specifying exact room positions,
walls, doors, and windows. No guessing, no auto-generation.
This is what we need for accurate floor plan replication.
"""

from typing import List, Set, Tuple, Optional

from .models import (
    FloorPlan, RoomRect, WallSegment, DoorPlacement, WindowPlacement,
    RoomType, Zone,
)
from .knowledge import ZONE_MAP, OPEN_PLAN_GROUPS, get_door_spec


class FloorPlanBuilder:
    """Build a floor plan by specifying exact room positions, walls, doors, and windows."""

    def __init__(self, name: str = "Custom Plan"):
        self.name = name
        self._rooms: List[RoomRect] = []
        self._walls: List[WallSegment] = []
        self._pending_doors: List[dict] = []
        self._pending_windows: List[dict] = []
        self._open_connections: Set[Tuple[str, str]] = set()
        self._footprint_width: float = 0.0
        self._footprint_height: float = 0.0
        self._footprint_polygon: List[Tuple[float, float]] = []

    # -----------------------------------------------------------------
    # Room placement
    # -----------------------------------------------------------------

    def add_room(self, name: str, room_type: RoomType, x: float, y: float,
                 w: float, h: float) -> 'FloorPlanBuilder':
        """Add a room at exact coordinates (feet). Origin is bottom-left."""
        zone = ZONE_MAP.get(room_type, Zone.PUBLIC)
        self._rooms.append(RoomRect(
            name=name, room_type=room_type, zone=zone,
            x=float(x), y=float(y), w=float(w), h=float(h),
        ))
        return self

    # -----------------------------------------------------------------
    # Walls
    # -----------------------------------------------------------------

    def add_exterior_walls_rect(self, width: float,
                                height: float) -> 'FloorPlanBuilder':
        """Add 4 exterior walls forming a rectangle."""
        self._footprint_width = width
        self._footprint_height = height
        self._footprint_polygon = [
            (0, 0), (width, 0), (width, height), (0, height),
        ]
        self._walls.append(
            WallSegment(0, 0, width, 0, is_exterior=True))       # south
        self._walls.append(
            WallSegment(width, 0, width, height, is_exterior=True))  # east
        self._walls.append(
            WallSegment(0, height, width, height, is_exterior=True))  # north
        self._walls.append(
            WallSegment(0, 0, 0, height, is_exterior=True))       # west
        return self

    def add_exterior_walls_L(
        self, points: List[Tuple[float, float]]
    ) -> 'FloorPlanBuilder':
        """Add exterior walls forming an L-shape or custom polygon."""
        self._footprint_polygon = list(points)
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            self._walls.append(WallSegment(
                p1[0], p1[1], p2[0], p2[1], is_exterior=True,
            ))
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        self._footprint_width = max(xs)
        self._footprint_height = max(ys)
        return self

    def add_interior_wall(self, x1: float, y1: float,
                          x2: float, y2: float) -> 'FloorPlanBuilder':
        """Add a single interior wall segment."""
        self._walls.append(WallSegment(
            float(x1), float(y1), float(x2), float(y2), is_exterior=False,
        ))
        return self

    def auto_interior_walls(self) -> 'FloorPlanBuilder':
        """Derive interior walls from room boundaries.

        For each pair of rooms sharing an edge, creates a wall segment
        unless they're open-plan connected. Also adds exterior walls
        if none exist yet.
        """
        # Compute footprint from room extents if not set
        w = self._footprint_width
        h = self._footprint_height
        if (not w or not h) and self._rooms:
            w = max(r.right for r in self._rooms)
            h = max(r.top for r in self._rooms)
            self._footprint_width = w
            self._footprint_height = h

        # Add exterior walls if none exist
        has_exterior = any(ws.is_exterior for ws in self._walls)
        if not has_exterior and w > 0 and h > 0:
            self.add_exterior_walls_rect(w, h)

        # Interior walls from shared edges
        seen_edges: Set[Tuple[float, float, float, float]] = set()
        tol = 0.25

        for i, ra in enumerate(self._rooms):
            for rb in self._rooms[i + 1:]:
                # Skip open-plan pairs
                pair = tuple(sorted([ra.name, rb.name]))
                if pair in self._open_connections:
                    continue

                seg = ra.shared_edge_segment(rb)
                if seg is None:
                    continue

                (x1, y1), (x2, y2) = seg
                edge_key = (round(x1, 2), round(y1, 2),
                            round(x2, 2), round(y2, 2))
                rev_key = (round(x2, 2), round(y2, 2),
                           round(x1, 2), round(y1, 2))

                if edge_key in seen_edges or rev_key in seen_edges:
                    continue

                # Skip edges on the exterior boundary
                on_exterior = self._is_on_exterior_boundary(
                    x1, y1, x2, y2, tol)

                if not on_exterior:
                    seen_edges.add(edge_key)
                    self._walls.append(WallSegment(
                        x1, y1, x2, y2, is_exterior=False,
                    ))

        # Merge collinear interior segments into continuous walls
        from .wall_utils import merge_collinear_walls
        self._walls = merge_collinear_walls(self._walls)

        return self

    def merge_collinear_walls(self) -> 'FloorPlanBuilder':
        """Merge collinear, overlapping wall segments into continuous walls."""
        from .wall_utils import merge_collinear_walls
        self._walls = merge_collinear_walls(self._walls)
        return self

    def auto_boundary_walls(self) -> 'FloorPlanBuilder':
        """Add interior walls for room edges facing circulation voids.

        For each room edge that is:
        - NOT on the exterior boundary, AND
        - NOT shared with another room, AND
        - Within the footprint polygon (faces interior space)
        create an interior wall segment.

        Requires a footprint polygon to determine what's "inside".
        """
        tol = 0.25
        existing_edges = set()

        # Collect existing interior wall segments
        for w in self._walls:
            if not w.is_exterior:
                key = (round(min(w.x1, w.x2), 2), round(min(w.y1, w.y2), 2),
                       round(max(w.x1, w.x2), 2), round(max(w.y1, w.y2), 2))
                existing_edges.add(key)

        new_walls = []
        for room in self._rooms:
            # Check all 4 edges
            edges = [
                (room.x, room.y, room.right, room.y),       # south
                (room.right, room.y, room.right, room.top),  # east
                (room.x, room.top, room.right, room.top),    # north
                (room.x, room.y, room.x, room.top),          # west
            ]

            for x1, y1, x2, y2 in edges:
                # Skip exterior boundary edges
                if self._is_on_exterior_boundary(x1, y1, x2, y2, tol):
                    continue

                # Skip edges shared with another room
                shared = False
                for other in self._rooms:
                    if other.name == room.name:
                        continue
                    seg = room.shared_edge_segment(other, tol)
                    if seg is None:
                        continue
                    (sx1, sy1), (sx2, sy2) = seg
                    # Check if this shared segment covers our edge
                    if self._segments_overlap(
                        x1, y1, x2, y2, sx1, sy1, sx2, sy2, tol
                    ):
                        shared = True
                        break

                if shared:
                    continue

                # Check if edge already exists as a wall
                key = (round(min(x1, x2), 2), round(min(y1, y2), 2),
                       round(max(x1, x2), 2), round(max(y1, y2), 2))
                if key in existing_edges:
                    continue

                # This edge faces interior space with no room — add wall
                existing_edges.add(key)
                new_walls.append(WallSegment(
                    x1, y1, x2, y2, is_exterior=False,
                ))

        self._walls.extend(new_walls)

        # Re-merge to consolidate
        if new_walls:
            from .wall_utils import merge_collinear_walls
            self._walls = merge_collinear_walls(self._walls)

        return self

    @staticmethod
    def _segments_overlap(ax1: float, ay1: float, ax2: float, ay2: float,
                          bx1: float, by1: float, bx2: float, by2: float,
                          tol: float) -> bool:
        """Check if two segments are collinear and overlap significantly."""
        # Both horizontal
        if abs(ay1 - ay2) < tol and abs(by1 - by2) < tol and abs(ay1 - by1) < tol:
            a_lo, a_hi = min(ax1, ax2), max(ax1, ax2)
            b_lo, b_hi = min(bx1, bx2), max(bx1, bx2)
            overlap = min(a_hi, b_hi) - max(a_lo, b_lo)
            return overlap > tol

        # Both vertical
        if abs(ax1 - ax2) < tol and abs(bx1 - bx2) < tol and abs(ax1 - bx1) < tol:
            a_lo, a_hi = min(ay1, ay2), max(ay1, ay2)
            b_lo, b_hi = min(by1, by2), max(by1, by2)
            overlap = min(a_hi, b_hi) - max(a_lo, b_lo)
            return overlap > tol

        return False

    # -----------------------------------------------------------------
    # Doors
    # -----------------------------------------------------------------

    def add_door(self, x: float, y: float, room_a: str = "",
                 room_b: str = "", is_entry: bool = False,
                 width_inches: float = 0,
                 height_inches: float = 0) -> 'FloorPlanBuilder':
        """Add a door at exact coordinates."""
        self._pending_doors.append({
            "x": float(x), "y": float(y),
            "room_a": room_a, "room_b": room_b,
            "is_entry": is_entry,
            "width_inches": width_inches,
            "height_inches": height_inches,
        })
        return self

    def add_entry_door(self, wall_side: str = "",
                       position: float = 0, *,
                       at: tuple = None) -> 'FloorPlanBuilder':
        """Add the main entry door on an exterior wall.

        Args:
            wall_side: 'south', 'north', 'east', 'west'
            position: distance along the wall for door center (feet)
            at: Optional (x, y) tuple for exact coordinate placement.
                When provided, wall_side and position are ignored.
        """
        if at is not None:
            x, y = float(at[0]), float(at[1])
        else:
            w = self._footprint_width or max(
                (r.right for r in self._rooms), default=0)
            h = self._footprint_height or max(
                (r.top for r in self._rooms), default=0)

            coords = {
                "south": (position, 0.0),
                "north": (position, h),
                "east":  (w, position),
                "west":  (0.0, position),
            }
            x, y = coords.get(wall_side, (position, 0.0))

        room_name = self._find_room_at_boundary(x, y)

        self._pending_doors.append({
            "x": x, "y": y,
            "room_a": room_name,
            "room_b": "exterior",
            "is_entry": True,
            "width_inches": 36, "height_inches": 84,
        })
        return self

    # -----------------------------------------------------------------
    # Windows
    # -----------------------------------------------------------------

    def add_window(self, x: float, y: float, room_name: str = "",
                   width_inches: float = 36, height_inches: float = 48,
                   sill_height_inches: float = 36) -> 'FloorPlanBuilder':
        """Add a window at exact coordinates on an exterior wall."""
        self._pending_windows.append({
            "x": float(x), "y": float(y),
            "room_name": room_name,
            "width_inches": width_inches,
            "height_inches": height_inches,
            "sill_height_inches": sill_height_inches,
        })
        return self

    # -----------------------------------------------------------------
    # Open plan
    # -----------------------------------------------------------------

    def connect_open_plan(self, room_a: str,
                          room_b: str) -> 'FloorPlanBuilder':
        """Mark two rooms as open-plan connected (no wall between them)."""
        self._open_connections.add(tuple(sorted([room_a, room_b])))
        return self

    # -----------------------------------------------------------------
    # Build
    # -----------------------------------------------------------------

    def build(self) -> FloorPlan:
        """Assemble the final FloorPlan from all specified elements."""
        # Compute footprint if needed
        if not self._footprint_width and self._rooms:
            self._footprint_width = max(r.right for r in self._rooms)
        if not self._footprint_height and self._rooms:
            self._footprint_height = max(r.top for r in self._rooms)

        # Resolve doors: match each to nearest wall segment
        doors = []
        for pd in self._pending_doors:
            wall = self._find_nearest_wall(pd["x"], pd["y"])
            if wall is None:
                wall = WallSegment(pd["x"], pd["y"], pd["x"], pd["y"])

            w_in = pd["width_inches"]
            h_in = pd["height_inches"]
            if not w_in or not h_in:
                if pd["is_entry"]:
                    w_in, h_in = 36, 84
                else:
                    room = (self._room_by_name(pd["room_a"])
                            or self._room_by_name(pd["room_b"]))
                    if room:
                        w_in, h_in = get_door_spec(
                            room.room_type, pd["is_entry"])
                    else:
                        w_in, h_in = 30, 80

            doors.append(DoorPlacement(
                location=(pd["x"], pd["y"]),
                wall_segment=wall,
                width_inches=w_in,
                height_inches=h_in,
                room_a=pd["room_a"],
                room_b=pd["room_b"],
            ))

        # Resolve windows: match each to nearest wall segment
        windows = []
        for pw in self._pending_windows:
            wall = self._find_nearest_wall(pw["x"], pw["y"])
            if wall is None:
                wall = WallSegment(pw["x"], pw["y"], pw["x"], pw["y"])

            windows.append(WindowPlacement(
                location=(pw["x"], pw["y"]),
                wall_segment=wall,
                width_inches=pw["width_inches"],
                height_inches=pw["height_inches"],
                sill_height_inches=pw["sill_height_inches"],
                room_name=pw["room_name"],
            ))

        # Count bedrooms/bathrooms
        bed_types = {RoomType.MASTER_BEDROOM, RoomType.BEDROOM}
        bath_types = {RoomType.MASTER_BATH, RoomType.BATHROOM,
                      RoomType.HALF_BATH}

        return FloorPlan(
            rooms=list(self._rooms),
            walls=list(self._walls),
            doors=doors,
            windows=windows,
            footprint_width=self._footprint_width,
            footprint_height=self._footprint_height,
            footprint_polygon=list(self._footprint_polygon),
            total_area=sum(r.area for r in self._rooms),
            bedrooms=sum(1 for r in self._rooms
                         if r.room_type in bed_types),
            bathrooms=sum(1 for r in self._rooms
                          if r.room_type in bath_types),
        )

    # -----------------------------------------------------------------
    # From structured data
    # -----------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict) -> 'FloorPlanBuilder':
        """Create builder from a structured dictionary.

        Expected format:
        {
            "name": "Plan Name",
            "rooms": [
                {"name": "Living", "type": "living_room",
                 "x": 0, "y": 0, "w": 15, "h": 12}
            ],
            "doors": [
                {"x": 10, "y": 0, "room_a": "Living",
                 "room_b": "exterior", "is_entry": true}
            ],
            "windows": [
                {"x": 5, "y": 0, "room_name": "Living"}
            ],
            "open_connections": [["Living", "Kitchen"]],
            "footprint": {"width": 44, "height": 30}
        }
        """
        builder = cls(data.get("name", "Custom Plan"))

        # Room type lookup
        type_map = {rt.value: rt for rt in RoomType}

        # Rooms
        for rd in data.get("rooms", []):
            rt = type_map.get(rd["type"], RoomType.LIVING)
            builder.add_room(
                rd["name"], rt, rd["x"], rd["y"], rd["w"], rd["h"])

        # Open connections (before auto walls)
        for conn in data.get("open_connections", []):
            if len(conn) == 2:
                builder.connect_open_plan(conn[0], conn[1])

        # Footprint
        fp = data.get("footprint", {})
        if fp:
            builder._footprint_width = fp.get("width", 0)
            builder._footprint_height = fp.get("height", 0)
            polygon = fp.get("polygon")
            if polygon:
                builder._footprint_polygon = [
                    (p[0], p[1]) for p in polygon
                ]

        # Auto walls unless disabled
        if data.get("auto_walls", True):
            builder.auto_interior_walls()

        # Doors
        for dd in data.get("doors", []):
            if dd.get("is_entry"):
                builder._pending_doors.append({
                    "x": dd["x"], "y": dd["y"],
                    "room_a": dd.get("room_a",
                                     builder._find_room_at_boundary(
                                         dd["x"], dd["y"])),
                    "room_b": "exterior",
                    "is_entry": True,
                    "width_inches": dd.get("width_inches", 36),
                    "height_inches": dd.get("height_inches", 84),
                })
            else:
                builder.add_door(
                    dd["x"], dd["y"],
                    room_a=dd.get("room_a", ""),
                    room_b=dd.get("room_b", ""),
                    is_entry=False,
                    width_inches=dd.get("width_inches", 0),
                    height_inches=dd.get("height_inches", 0),
                )

        # Windows
        for wd in data.get("windows", []):
            builder.add_window(
                wd["x"], wd["y"],
                room_name=wd.get("room_name", ""),
                width_inches=wd.get("width_inches", 36),
                height_inches=wd.get("height_inches", 48),
                sill_height_inches=wd.get("sill_height_inches", 36),
            )

        return builder

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    def _is_on_exterior_boundary(self, x1: float, y1: float,
                                  x2: float, y2: float,
                                  tol: float = 0.25) -> bool:
        """Check if a segment lies on any edge of the footprint polygon."""
        polygon = self._footprint_polygon
        if not polygon:
            # Fall back to bounding box check
            w = self._footprint_width
            h = self._footprint_height
            if abs(y1) < tol and abs(y2) < tol:
                return True
            if abs(y1 - h) < tol and abs(y2 - h) < tol:
                return True
            if abs(x1) < tol and abs(x2) < tol:
                return True
            if abs(x1 - w) < tol and abs(x2 - w) < tol:
                return True
            return False

        from .wall_utils import is_on_polygon_edge
        return is_on_polygon_edge(x1, y1, x2, y2, polygon, tol)

    def _find_nearest_wall(self, x: float, y: float,
                           max_dist: float = 1.0) -> Optional[WallSegment]:
        """Find the wall segment closest to a point."""
        best_wall = None
        best_dist = max_dist
        for wall in self._walls:
            dist = self._point_to_segment_dist(x, y, wall)
            if dist < best_dist:
                best_dist = dist
                best_wall = wall
        return best_wall

    @staticmethod
    def _point_to_segment_dist(px: float, py: float,
                               wall: WallSegment) -> float:
        """Distance from point to wall line segment."""
        x1, y1, x2, y2 = wall.x1, wall.y1, wall.x2, wall.y2
        dx, dy = x2 - x1, y2 - y1
        length_sq = dx * dx + dy * dy

        if length_sq < 0.001:
            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5

        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / length_sq))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy

        return ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5

    def _find_room_at_boundary(self, x: float, y: float,
                               tol: float = 0.5) -> str:
        """Find which room has this point on or near its boundary."""
        for r in self._rooms:
            on_edge = (
                (abs(x - r.x) < tol and r.y - tol <= y <= r.top + tol)
                or (abs(x - r.right) < tol and r.y - tol <= y <= r.top + tol)
                or (abs(y - r.y) < tol and r.x - tol <= x <= r.right + tol)
                or (abs(y - r.top) < tol and r.x - tol <= x <= r.right + tol)
            )
            inside = (r.x - tol <= x <= r.right + tol
                      and r.y - tol <= y <= r.top + tol)
            if on_edge or inside:
                return r.name
        return ""

    def _room_by_name(self, name: str) -> Optional[RoomRect]:
        """Lookup room by name."""
        for r in self._rooms:
            if r.name == name:
                return r
        return None
