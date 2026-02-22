"""
Data models for FloorPlanEngine.

All coordinates are in feet. Origin (0,0) is bottom-left of footprint.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple


class Zone(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    SERVICE = "service"
    CIRCULATION = "circulation"


class RoomType(Enum):
    LIVING = "living_room"
    KITCHEN = "kitchen"
    DINING = "dining_room"
    ENTRY = "entry"
    MASTER_BEDROOM = "master_bedroom"
    BEDROOM = "bedroom"
    MASTER_BATH = "master_bath"
    BATHROOM = "bathroom"
    HALF_BATH = "half_bath"
    LAUNDRY = "laundry"
    HALLWAY = "hallway"
    CLOSET = "closet"
    WALK_IN_CLOSET = "walk_in_closet"
    PANTRY = "pantry"
    OFFICE = "office"
    FAMILY_ROOM = "family_room"
    GARAGE = "garage"


@dataclass
class RoomSpec:
    """A room in the building program (pre-layout)."""
    name: str
    room_type: RoomType
    target_area: float  # sq ft
    zone: Zone
    min_width: float = 0.0  # ft, 0 = use default from knowledge
    max_aspect: float = 0.0  # 0 = use default from knowledge


@dataclass
class RoomRect:
    """A room with exact XY coordinates (post-layout)."""
    name: str
    room_type: RoomType
    zone: Zone
    x: float  # left edge, ft
    y: float  # bottom edge, ft
    w: float  # width, ft
    h: float  # height (depth), ft

    @property
    def area(self) -> float:
        return self.w * self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def aspect_ratio(self) -> float:
        return max(self.w, self.h) / max(min(self.w, self.h), 0.1)

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def top(self) -> float:
        return self.y + self.h

    def shares_edge_with(self, other: 'RoomRect', tol: float = 0.25) -> Optional[str]:
        """Check if two rooms share an edge. Returns edge direction or None."""
        # Shared vertical edge (side by side)
        if abs(self.right - other.x) < tol or abs(other.right - self.x) < tol:
            overlap_y = min(self.top, other.top) - max(self.y, other.y)
            if overlap_y > tol:
                return "vertical"
        # Shared horizontal edge (stacked)
        if abs(self.top - other.y) < tol or abs(other.top - self.y) < tol:
            overlap_x = min(self.right, other.right) - max(self.x, other.x)
            if overlap_x > tol:
                return "horizontal"
        return None

    def shared_edge_segment(self, other: 'RoomRect', tol: float = 0.25):
        """Return the shared edge segment as ((x1,y1),(x2,y2)) or None."""
        # Vertical shared edge
        if abs(self.right - other.x) < tol:
            edge_x = self.right
            y_lo = max(self.y, other.y)
            y_hi = min(self.top, other.top)
            if y_hi - y_lo > tol:
                return ((edge_x, y_lo), (edge_x, y_hi))
        if abs(other.right - self.x) < tol:
            edge_x = self.x
            y_lo = max(self.y, other.y)
            y_hi = min(self.top, other.top)
            if y_hi - y_lo > tol:
                return ((edge_x, y_lo), (edge_x, y_hi))
        # Horizontal shared edge
        if abs(self.top - other.y) < tol:
            edge_y = self.top
            x_lo = max(self.x, other.x)
            x_hi = min(self.right, other.right)
            if x_hi - x_lo > tol:
                return ((x_lo, edge_y), (x_hi, edge_y))
        if abs(other.top - self.y) < tol:
            edge_y = self.y
            x_lo = max(self.x, other.x)
            x_hi = min(self.right, other.right)
            if x_hi - x_lo > tol:
                return ((x_lo, edge_y), (x_hi, edge_y))
        return None


@dataclass
class WallSegment:
    """A wall segment with start/end points."""
    x1: float
    y1: float
    x2: float
    y2: float
    is_exterior: bool = False
    height: float = 10.0  # ft

    @property
    def length(self) -> float:
        return ((self.x2 - self.x1) ** 2 + (self.y2 - self.y1) ** 2) ** 0.5

    @property
    def midpoint(self) -> tuple:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def is_horizontal(self) -> bool:
        return abs(self.y2 - self.y1) < 0.01

    @property
    def is_vertical(self) -> bool:
        return abs(self.x2 - self.x1) < 0.01


@dataclass
class DoorPlacement:
    """A door to be placed on a wall."""
    location: tuple  # (x, y)
    wall_segment: WallSegment
    width_inches: float = 30.0
    height_inches: float = 80.0
    room_a: str = ""
    room_b: str = ""


@dataclass
class WindowPlacement:
    """A window to be placed on an exterior wall."""
    location: tuple  # (x, y)
    wall_segment: WallSegment
    width_inches: float = 36.0
    height_inches: float = 48.0
    sill_height_inches: float = 36.0
    room_name: str = ""


@dataclass
class FloorPlanAnalysis:
    """Complete architectural analysis of a floor plan.

    Produced by the reasoning engine's think_through() function.
    Contains connectivity, circulation, zoning, door/window analysis,
    natural language narrative, and scoring.
    """
    # Connectivity
    connectivity_graph: Dict[str, List[str]] = field(default_factory=dict)
    entry_room: str = ""
    reachable_rooms: List[str] = field(default_factory=list)
    unreachable_rooms: List[str] = field(default_factory=list)
    room_depth: Dict[str, int] = field(default_factory=dict)

    # Circulation
    circulation_area: float = 0.0
    circulation_ratio: float = 0.0
    dead_ends: List[str] = field(default_factory=list)
    pass_through_rooms: List[str] = field(default_factory=list)

    # Zoning
    zone_separation_score: float = 0.0
    zone_violations: List[str] = field(default_factory=list)
    privacy_gradient: List[str] = field(default_factory=list)

    # Door analysis
    door_issues: List[str] = field(default_factory=list)
    rooms_without_doors: List[str] = field(default_factory=list)

    # Window analysis
    window_issues: List[str] = field(default_factory=list)
    rooms_without_windows: List[str] = field(default_factory=list)

    # Narrative
    walkthrough: str = ""
    critique: str = ""

    # Scores (0-100 each)
    connectivity_score: float = 0.0
    circulation_score: float = 0.0
    zoning_score: float = 0.0
    door_score: float = 0.0
    window_score: float = 0.0
    score: float = 0.0  # composite
    verdict: str = ""   # "GOOD" / "NEEDS WORK" / "FUNDAMENTALLY FLAWED"


@dataclass
class FloorPlan:
    """Complete floor plan ready for Revit execution."""
    rooms: List[RoomRect] = field(default_factory=list)
    walls: List[WallSegment] = field(default_factory=list)
    doors: List[DoorPlacement] = field(default_factory=list)
    windows: List[WindowPlacement] = field(default_factory=list)
    footprint_width: float = 0.0
    footprint_height: float = 0.0
    footprint_polygon: List[Tuple[float, float]] = field(default_factory=list)
    total_area: float = 0.0
    bedrooms: int = 0
    bathrooms: int = 0

    def to_building_program(self) -> Dict[str, Any]:
        """Export as JSON matching C# BuildingProgram class."""
        if self.footprint_polygon:
            footprint = [{"x": p[0], "y": p[1]} for p in self.footprint_polygon]
        else:
            footprint = [
                {"x": 0, "y": 0},
                {"x": self.footprint_width, "y": 0},
                {"x": self.footprint_width, "y": self.footprint_height},
                {"x": 0, "y": self.footprint_height},
            ]
        return {
            "buildingType": "SingleFamilyResidential",
            "numberOfStories": 1,
            "floorToFloorHeight": 10.0,
            "totalBuildingArea": self.total_area,
            "footprintWidth": self.footprint_width,
            "footprintLength": self.footprint_height,
            "buildingFootprint": footprint,
            "rooms": [
                {
                    "name": r.name,
                    "roomType": r.room_type.value,
                    "area": r.area,
                    "minWidth": r.w,
                    "minLength": r.h,
                    "location": {"x": r.cx, "y": r.cy},
                    "boundaries": [
                        {"x": r.x, "y": r.y},
                        {"x": r.right, "y": r.y},
                        {"x": r.right, "y": r.top},
                        {"x": r.x, "y": r.top},
                    ],
                }
                for r in self.rooms
            ],
            "doors": [
                {
                    "location": {"x": d.location[0], "y": d.location[1]},
                    "width": d.width_inches,
                    "height": d.height_inches,
                }
                for d in self.doors
            ],
            "windows": [
                {
                    "location": {"x": w.location[0], "y": w.location[1]},
                    "width": w.width_inches,
                    "height": w.height_inches,
                    "sillHeight": w.sill_height_inches,
                }
                for w in self.windows
            ],
        }

    def ascii_preview(self, scale: float = 1.0) -> str:
        """Generate an ASCII visualization of the floor plan."""
        cols = int(self.footprint_width * scale * 2)
        rows = int(self.footprint_height * scale)
        if cols < 10 or rows < 5:
            scale = max(20 / self.footprint_width, 10 / self.footprint_height)
            cols = int(self.footprint_width * scale * 2)
            rows = int(self.footprint_height * scale)

        grid = [[' ' for _ in range(cols)] for _ in range(rows)]

        for room in self.rooms:
            rx1 = int(room.x * scale * 2)
            ry1 = int(room.y * scale)
            rx2 = int(room.right * scale * 2)
            ry2 = int(room.top * scale)
            rx1 = max(0, min(rx1, cols - 1))
            ry1 = max(0, min(ry1, rows - 1))
            rx2 = max(0, min(rx2, cols - 1))
            ry2 = max(0, min(ry2, rows - 1))

            # Draw borders
            for c in range(rx1, rx2 + 1):
                if ry1 < rows:
                    grid[ry1][min(c, cols - 1)] = '-'
                if ry2 < rows:
                    grid[ry2][min(c, cols - 1)] = '-'
            for r in range(ry1, ry2 + 1):
                if r < rows:
                    grid[r][rx1] = '|'
                    grid[r][min(rx2, cols - 1)] = '|'

            # Label
            label = room.name[:12]
            mid_r = (ry1 + ry2) // 2
            mid_c = (rx1 + rx2) // 2 - len(label) // 2
            if 0 <= mid_r < rows:
                for i, ch in enumerate(label):
                    ci = mid_c + i
                    if 0 <= ci < cols:
                        grid[mid_r][ci] = ch

        lines = []
        for r in reversed(range(rows)):
            lines.append(''.join(grid[r]))
        return '\n'.join(lines)

    def analyze(self) -> 'FloorPlanAnalysis':
        """Run critical thinking analysis on this floor plan."""
        from .reasoning import think_through
        return think_through(self)

    def narrate(self) -> str:
        """Generate natural language walkthrough."""
        from .reasoning import narrate_walkthrough, build_connectivity_graph
        from .reasoning import analyze_circulation
        graph = build_connectivity_graph(self)
        circ = analyze_circulation(self, graph)
        return narrate_walkthrough(self, graph, circ["room_depth"])

    def critique(self) -> str:
        """Get architectural critique."""
        from .reasoning import critique
        return critique(self)
