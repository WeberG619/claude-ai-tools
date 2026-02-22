"""
Critical thinking engine for floor plan analysis.

Analyzes any FloorPlan and produces structured architectural understanding:
connectivity, circulation, zoning, door/window logic, and natural language narrative.

This is what makes the engine "understand" floor plans — not just generate them.
"""

from collections import deque
from typing import Dict, List, Set, Tuple, Optional

from .models import FloorPlan, RoomRect, RoomType, Zone
from .knowledge import ZONE_MAP, WINDOW_RULES, OPEN_PLAN_GROUPS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_entry_room(plan: FloorPlan) -> str:
    """Identify the entry room from the plan."""
    # 1. Room typed as ENTRY
    for r in plan.rooms:
        if r.room_type == RoomType.ENTRY:
            return r.name
    # 2. Room connected to an entry door (room_b == "exterior")
    for d in plan.doors:
        if d.room_b == "exterior" and d.room_a:
            return d.room_a
        if not d.room_b and d.room_a:
            return d.room_a
    # 3. Entry door exists but room_a is empty — find nearest room
    for d in plan.doors:
        if d.room_b == "exterior" and not d.room_a:
            # Find nearest room to the entry door location
            best = None
            best_dist = float('inf')
            for r in plan.rooms:
                # Distance from door to room center
                dist = ((d.location[0] - r.cx) ** 2
                        + (d.location[1] - r.cy) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best = r
            if best:
                return best.name
    # 4. Fallback: room closest to south wall (y=0)
    if plan.rooms:
        return min(plan.rooms, key=lambda r: r.y).name
    return ""


def _room_by_name(plan: FloorPlan, name: str) -> Optional[RoomRect]:
    """Get room by name."""
    for r in plan.rooms:
        if r.name == name:
            return r
    return None


def _room_has_exterior_wall(room: RoomRect, fp_w: float, fp_h: float,
                            tol: float = 0.5,
                            polygon: List[Tuple[float, float]] = None) -> List[str]:
    """Return list of sides ('south','north','east','west') on the exterior.

    When a polygon is provided, checks each room edge against the polygon
    edges rather than just the bounding box.
    """
    if polygon:
        from .wall_utils import is_on_polygon_edge
        sides = []
        # south edge
        if is_on_polygon_edge(room.x, room.y, room.right, room.y, polygon, tol):
            sides.append("south")
        # north edge
        if is_on_polygon_edge(room.x, room.top, room.right, room.top, polygon, tol):
            sides.append("north")
        # west edge
        if is_on_polygon_edge(room.x, room.y, room.x, room.top, polygon, tol):
            sides.append("west")
        # east edge
        if is_on_polygon_edge(room.right, room.y, room.right, room.top, polygon, tol):
            sides.append("east")
        return sides

    sides = []
    if room.y <= tol:
        sides.append("south")
    if abs(room.top - fp_h) <= tol:
        sides.append("north")
    if room.x <= tol:
        sides.append("west")
    if abs(room.right - fp_w) <= tol:
        sides.append("east")
    return sides


def _relative_direction(from_room: RoomRect, to_room: RoomRect) -> str:
    """Describe spatial direction from one room to another."""
    dx = to_room.cx - from_room.cx
    dy = to_room.cy - from_room.cy
    if abs(dx) > abs(dy):
        return "to the east" if dx > 0 else "to the west"
    else:
        return "to the north" if dy > 0 else "to the south"


def _find_path(graph: Dict[str, List[str]], start: str,
               end: str) -> Optional[List[str]]:
    """BFS shortest path between two rooms."""
    if start == end:
        return [start]
    if start not in graph:
        return None
    visited = {start}
    queue = deque([(start, [start])])
    while queue:
        node, path = queue.popleft()
        for nb in graph.get(node, []):
            if nb == end:
                return path + [nb]
            if nb not in visited:
                visited.add(nb)
                queue.append((nb, path + [nb]))
    return None


# ---------------------------------------------------------------------------
# Core Analysis Functions
# ---------------------------------------------------------------------------

def build_connectivity_graph(plan: FloorPlan) -> Dict[str, List[str]]:
    """Build room connectivity graph from doors and open-plan connections.

    Two rooms are connected if:
    - A door exists between them (room_a ↔ room_b), OR
    - They are open-plan connected (same OPEN_PLAN_GROUP and share an edge)

    Returns adjacency list: {room_name: [connected_room_names]}
    """
    graph: Dict[str, List[str]] = {r.name: [] for r in plan.rooms}
    connected: Set[Tuple[str, str]] = set()

    # Connections from doors
    for door in plan.doors:
        a, b = door.room_a, door.room_b
        if a and b and b != "exterior" and a in graph and b in graph:
            pair = tuple(sorted([a, b]))
            if pair not in connected:
                connected.add(pair)
                graph[a].append(b)
                graph[b].append(a)

    # Open-plan connections (rooms in same group that share a wall)
    for i, ra in enumerate(plan.rooms):
        for rb in plan.rooms[i + 1:]:
            pair = tuple(sorted([ra.name, rb.name]))
            if pair in connected:
                continue
            for group in OPEN_PLAN_GROUPS:
                if ra.room_type in group and rb.room_type in group:
                    if ra.shares_edge_with(rb):
                        connected.add(pair)
                        graph[ra.name].append(rb.name)
                        graph[rb.name].append(ra.name)
                    break

    return graph


def analyze_circulation(plan: FloorPlan,
                        graph: Dict[str, List[str]]) -> dict:
    """BFS from entry room through connectivity graph.

    Returns dict with:
        entry_room, reachable, unreachable, room_depth, dead_ends,
        pass_through_rooms, circulation_area, circulation_ratio
    """
    entry = _find_entry_room(plan)
    all_names = {r.name for r in plan.rooms}

    # BFS from entry
    depth: Dict[str, int] = {}
    visited: Set[str] = set()
    queue: deque = deque()

    if entry and entry in graph:
        queue.append((entry, 0))
        visited.add(entry)
        while queue:
            room, d = queue.popleft()
            depth[room] = d
            for neighbor in graph.get(room, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, d + 1))

    reachable = sorted(visited)
    unreachable = sorted(all_names - visited)

    # Dead ends: rooms with only 1 connection
    dead_ends = [name for name in graph if len(graph[name]) == 1]

    # Pass-through rooms (articulation points):
    # Removing the room disconnects the reachable subgraph
    pass_through = []
    for candidate in reachable:
        if candidate == entry:
            continue
        remaining = {n for n in reachable if n != candidate}
        if not remaining:
            continue
        start = entry if entry in remaining else next(iter(remaining))
        test_visited = {start}
        test_queue = deque([start])
        while test_queue:
            node = test_queue.popleft()
            for nb in graph.get(node, []):
                if nb not in test_visited and nb in remaining:
                    test_visited.add(nb)
                    test_queue.append(nb)
        if len(test_visited) < len(remaining):
            pass_through.append(candidate)

    # Circulation area (hallways + entry)
    circ_area = sum(
        r.area for r in plan.rooms
        if r.room_type in (RoomType.HALLWAY, RoomType.ENTRY)
    )
    total_area = sum(r.area for r in plan.rooms) or 1.0
    circ_ratio = circ_area / total_area

    return {
        "entry_room": entry,
        "reachable": reachable,
        "unreachable": unreachable,
        "room_depth": depth,
        "dead_ends": dead_ends,
        "pass_through_rooms": pass_through,
        "circulation_area": circ_area,
        "circulation_ratio": circ_ratio,
    }


def analyze_zoning(plan: FloorPlan, graph: Dict[str, List[str]],
                   depths: Dict[str, int]) -> dict:
    """Check zone separation: public rooms near entry, private rooms deeper.

    Returns:
        zone_separation_score (0-100), zone_violations, privacy_gradient
    """
    if not depths:
        return {
            "zone_separation_score": 0.0,
            "zone_violations": ["No room depths available (disconnected plan?)"],
            "privacy_gradient": [],
        }

    violations = []

    # Classify rooms by zone
    public_rooms = []
    private_rooms = []
    for r in plan.rooms:
        zone = ZONE_MAP.get(r.room_type, Zone.PUBLIC)
        if zone == Zone.PUBLIC:
            public_rooms.append(r)
        elif zone == Zone.PRIVATE:
            private_rooms.append(r)

    # Average depths
    pub_depths = [depths.get(r.name, 99) for r in public_rooms]
    priv_depths = [depths.get(r.name, 99) for r in private_rooms]

    avg_pub = sum(pub_depths) / len(pub_depths) if pub_depths else 0
    avg_priv = sum(priv_depths) / len(priv_depths) if priv_depths else 0

    if avg_pub > avg_priv and private_rooms and public_rooms:
        violations.append(
            f"Public rooms (avg depth {avg_pub:.1f}) are farther from entry "
            f"than private rooms (avg depth {avg_priv:.1f})"
        )

    # Path violations: must you walk through private space to reach public?
    entry = _find_entry_room(plan)
    for pub in public_rooms:
        if pub.name == entry or pub.name not in depths:
            continue
        path = _find_path(graph, entry, pub.name)
        if path:
            for room_name in path[1:-1]:  # skip start and end
                intermediate = _room_by_name(plan, room_name)
                if intermediate:
                    zone = ZONE_MAP.get(intermediate.room_type, Zone.PUBLIC)
                    if zone == Zone.PRIVATE:
                        violations.append(
                            f"Must pass through {room_name} (private) "
                            f"to reach {pub.name} (public)"
                        )
                        break

    # Privacy gradient: rooms ordered public → private by depth
    gradient = sorted(
        [r.name for r in plan.rooms if r.name in depths],
        key=lambda n: depths[n]
    )

    score = max(0.0, 100.0 - len(violations) * 20)

    return {
        "zone_separation_score": score,
        "zone_violations": violations,
        "privacy_gradient": gradient,
    }


def analyze_doors(plan: FloorPlan) -> dict:
    """Check door placement logic.

    Returns:
        door_issues, rooms_without_doors, door_score
    """
    issues = []

    # Which rooms have doors?
    rooms_with_doors: Set[str] = set()
    for d in plan.doors:
        if d.room_a and d.room_a != "exterior":
            rooms_with_doors.add(d.room_a)
        if d.room_b and d.room_b != "exterior":
            rooms_with_doors.add(d.room_b)

    # Open-plan rooms don't need doors between them
    open_plan_rooms: Set[str] = set()
    for i, ra in enumerate(plan.rooms):
        for rb in plan.rooms[i + 1:]:
            for group in OPEN_PLAN_GROUPS:
                if ra.room_type in group and rb.room_type in group:
                    if ra.shares_edge_with(rb):
                        open_plan_rooms.add(ra.name)
                        open_plan_rooms.add(rb.name)

    # Rooms that need doors but don't have them
    rooms_without = []
    for r in plan.rooms:
        if r.name not in rooms_with_doors and r.name not in open_plan_rooms:
            rooms_without.append(r.name)
            issues.append(f"{r.name} has no door — it's inaccessible")

    # Check bathroom doors facing living spaces
    bath_types = {RoomType.BATHROOM, RoomType.MASTER_BATH, RoomType.HALF_BATH}
    living_types = {RoomType.LIVING, RoomType.DINING, RoomType.FAMILY_ROOM}
    for d in plan.doors:
        a_room = _room_by_name(plan, d.room_a)
        b_room = _room_by_name(plan, d.room_b)
        if a_room and b_room:
            if (a_room.room_type in bath_types
                    and b_room.room_type in living_types):
                issues.append(
                    f"{a_room.name} door opens to {b_room.name} — "
                    f"bathroom doors should face hallways, not living spaces"
                )
            elif (b_room.room_type in bath_types
                  and a_room.room_type in living_types):
                issues.append(
                    f"{b_room.name} door opens to {a_room.name} — "
                    f"bathroom doors should face hallways, not living spaces"
                )

    # Score
    total_rooms = len(plan.rooms)
    if total_rooms == 0:
        score = 100.0
    else:
        accessible = total_rooms - len(rooms_without)
        score = max(0.0, (accessible / total_rooms) * 100 - len(issues) * 5)

    return {
        "door_issues": issues,
        "rooms_without_doors": rooms_without,
        "door_score": score,
    }


def analyze_windows(plan: FloorPlan) -> dict:
    """Check window placement against building code requirements.

    Returns:
        window_issues, rooms_without_windows, window_score
    """
    issues = []

    # Which rooms have windows?
    rooms_with_windows: Set[str] = set()
    for w in plan.windows:
        if w.room_name:
            rooms_with_windows.add(w.room_name)

    rooms_needing_windows = []
    for r in plan.rooms:
        rule = WINDOW_RULES.get(r.room_type)
        if not rule:
            continue

        ext_sides = _room_has_exterior_wall(
            r, plan.footprint_width, plan.footprint_height,
            polygon=plan.footprint_polygon or None,
        )

        if rule.get("needs_egress") and r.name not in rooms_with_windows:
            issues.append(
                f"{r.name} needs an egress window (code requirement) but has none"
            )
            rooms_needing_windows.append(r.name)
        elif rule.get("glazing_ratio", 0) > 0 and r.name not in rooms_with_windows:
            if ext_sides:
                issues.append(
                    f"{r.name} has exterior wall access ({', '.join(ext_sides)}) "
                    f"but no window"
                )
                rooms_needing_windows.append(r.name)
            elif r.room_type not in (
                RoomType.BATHROOM, RoomType.MASTER_BATH, RoomType.HALF_BATH
            ):
                issues.append(
                    f"{r.name} has no exterior wall — cannot have windows "
                    f"for natural light"
                )

    # Score: egress compliance is 60%, general windows 40%
    egress_rooms = [
        r for r in plan.rooms
        if WINDOW_RULES.get(r.room_type, {}).get("needs_egress")
    ]
    egress_with_windows = [
        r for r in egress_rooms if r.name in rooms_with_windows
    ]

    if egress_rooms:
        egress_score = (len(egress_with_windows) / len(egress_rooms)) * 60
    else:
        egress_score = 60.0

    non_egress_issues = len([i for i in issues if "egress" not in i])
    other_penalty = min(40.0, non_egress_issues * 10)
    score = max(0.0, egress_score + (40.0 - other_penalty))

    return {
        "window_issues": issues,
        "rooms_without_windows": rooms_needing_windows,
        "window_score": score,
    }


# ---------------------------------------------------------------------------
# Narrative
# ---------------------------------------------------------------------------

def narrate_walkthrough(plan: FloorPlan, graph: Dict[str, List[str]],
                        depths: Dict[str, int]) -> str:
    """Generate natural language walkthrough following BFS from entry."""
    if not plan.rooms:
        return "Empty floor plan — no rooms to walk through."

    entry = _find_entry_room(plan)
    room_map = {r.name: r for r in plan.rooms}

    if entry not in room_map:
        return "Could not identify entry point."

    # BFS traversal order
    visited_order = []
    visited = {entry}
    queue = deque([entry])
    while queue:
        name = queue.popleft()
        visited_order.append(name)
        for nb in graph.get(name, []):
            if nb not in visited:
                visited.add(nb)
                queue.append(nb)

    # Build narrative
    parts = []
    entry_room = room_map[entry]
    ext_sides = _room_has_exterior_wall(
        entry_room, plan.footprint_width, plan.footprint_height,
        polygon=plan.footprint_polygon or None,
    )
    entry_side = ext_sides[0] if ext_sides else "south"

    parts.append(
        f"You enter through the {entry} on the {entry_side} side of the house."
    )

    for i, name in enumerate(visited_order):
        room = room_map.get(name)
        if not room:
            continue

        if i == 0:
            # Describe connections from entry
            neighbors = graph.get(name, [])
            if neighbors:
                descs = []
                for nb in neighbors:
                    nb_room = room_map.get(nb)
                    if nb_room:
                        direction = _relative_direction(room, nb_room)
                        descs.append(f"the {nb} {direction}")
                if len(descs) == 1:
                    parts.append(f"From here you can reach {descs[0]}.")
                elif descs:
                    parts.append(
                        f"From here you can reach "
                        f"{', '.join(descs[:-1])}, and {descs[-1]}."
                    )
        else:
            # Find which previously-visited room we came from
            parent = None
            for prev in visited_order[:i]:
                if name in graph.get(prev, []):
                    parent = prev
                    break

            parent_room = room_map.get(parent) if parent else None
            area_str = f"{room.area:.0f} SF"
            type_desc = room.room_type.value.replace("_", " ")

            if parent_room:
                direction = _relative_direction(parent_room, room)
                parts.append(
                    f"Moving {direction}, the {name} ({area_str}) "
                    f"is a {type_desc}."
                )
            else:
                parts.append(f"The {name} ({area_str}) is a {type_desc}.")

            # Mention onward connections (not back to parent)
            connections = [
                nb for nb in graph.get(name, [])
                if nb != parent and nb not in set(visited_order[:i])
            ]
            if connections:
                conn_names = [f"the {c}" for c in connections]
                parts.append(f"  It connects to {', '.join(conn_names)}.")

    # Mention unreachable rooms
    all_names = {r.name for r in plan.rooms}
    unreachable = all_names - visited
    if unreachable:
        parts.append(
            f"\nNote: {', '.join(sorted(unreachable))} cannot be reached "
            f"from the entry — they have no door connections."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------

def critique(plan: FloorPlan) -> str:
    """Generate a synthesized architectural critique of the floor plan."""
    graph = build_connectivity_graph(plan)
    circ = analyze_circulation(plan, graph)
    zoning = analyze_zoning(plan, graph, circ["room_depth"])
    doors = analyze_doors(plan)
    windows = analyze_windows(plan)

    parts = []
    total_area = sum(r.area for r in plan.rooms)
    parts.append(
        f"This {total_area:.0f} SF plan has {len(plan.rooms)} rooms, "
        f"{len(plan.doors)} doors, and {len(plan.windows)} windows."
    )

    # Connectivity
    if circ["unreachable"]:
        parts.append(
            f"CRITICAL: {', '.join(circ['unreachable'])} cannot be reached "
            f"from the entry. These rooms need door connections."
        )
    else:
        parts.append(
            "All rooms are reachable from the entry — good connectivity."
        )

    # Circulation efficiency
    ratio_pct = circ["circulation_ratio"] * 100
    if ratio_pct > 25:
        parts.append(
            f"Circulation uses {ratio_pct:.0f}% of floor area — high. "
            f"Consider reducing hallway space."
        )
    elif ratio_pct < 5 and any(
        r.room_type == RoomType.HALLWAY for r in plan.rooms
    ):
        parts.append(
            f"Circulation uses only {ratio_pct:.0f}% — "
            f"hallways may be too cramped."
        )

    if circ["pass_through_rooms"]:
        parts.append(
            f"Traffic bottleneck: {', '.join(circ['pass_through_rooms'])} "
            f"must be passed through to reach other rooms."
        )

    # Zoning
    if zoning["zone_violations"]:
        parts.append("Zone separation issues:")
        for v in zoning["zone_violations"]:
            parts.append(f"  - {v}")
    else:
        parts.append(
            "Zone separation is good — public and private spaces "
            "are properly divided."
        )

    # Doors
    if doors["door_issues"]:
        parts.append("Door issues:")
        for issue in doors["door_issues"]:
            parts.append(f"  - {issue}")

    # Windows
    if windows["window_issues"]:
        parts.append("Window issues:")
        for issue in windows["window_issues"]:
            parts.append(f"  - {issue}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def think_through(plan: FloorPlan) -> 'FloorPlanAnalysis':
    """Run full critical thinking analysis on a floor plan.

    This is the main entry point — what Weber asked for: "think things through."
    Runs all analyses, builds narrative, computes scores, returns everything.
    """
    from .models import FloorPlanAnalysis

    graph = build_connectivity_graph(plan)
    circ = analyze_circulation(plan, graph)
    zoning = analyze_zoning(plan, graph, circ["room_depth"])
    doors = analyze_doors(plan)
    windows = analyze_windows(plan)
    walkthrough_text = narrate_walkthrough(plan, graph, circ["room_depth"])
    critique_text = critique(plan)

    # --- Scoring ---

    # Connectivity: % of rooms reachable from entry
    total = len(plan.rooms)
    reachable_count = len(circ["reachable"])
    connectivity_score = (reachable_count / total * 100) if total else 100.0

    # Circulation: ideal hallway ratio is 10-20%
    ratio = circ["circulation_ratio"]
    if 0.10 <= ratio <= 0.20:
        circ_score = 100.0
    elif ratio < 0.05:
        circ_score = 60.0
    elif ratio > 0.30:
        circ_score = 50.0
    else:
        circ_score = 80.0
    circ_score -= len(circ["pass_through_rooms"]) * 10
    circ_score = max(0.0, circ_score)

    # Composite: weighted average
    scores = {
        "connectivity": connectivity_score,
        "circulation": circ_score,
        "zoning": zoning["zone_separation_score"],
        "doors": doors["door_score"],
        "windows": windows["window_score"],
    }
    weights = {
        "connectivity": 0.30,
        "circulation": 0.15,
        "zoning": 0.20,
        "doors": 0.20,
        "windows": 0.15,
    }
    composite = sum(scores[k] * weights[k] for k in scores)

    if composite >= 80:
        verdict = "GOOD"
    elif composite >= 50:
        verdict = "NEEDS WORK"
    else:
        verdict = "FUNDAMENTALLY FLAWED"

    return FloorPlanAnalysis(
        connectivity_graph=graph,
        entry_room=circ["entry_room"],
        reachable_rooms=circ["reachable"],
        unreachable_rooms=circ["unreachable"],
        room_depth=circ["room_depth"],
        circulation_area=circ["circulation_area"],
        circulation_ratio=circ["circulation_ratio"],
        dead_ends=circ["dead_ends"],
        pass_through_rooms=circ["pass_through_rooms"],
        zone_separation_score=zoning["zone_separation_score"],
        zone_violations=zoning["zone_violations"],
        privacy_gradient=zoning["privacy_gradient"],
        door_issues=doors["door_issues"],
        rooms_without_doors=doors["rooms_without_doors"],
        window_issues=windows["window_issues"],
        rooms_without_windows=windows["rooms_without_windows"],
        walkthrough=walkthrough_text,
        critique=critique_text,
        connectivity_score=connectivity_score,
        circulation_score=circ_score,
        zoning_score=zoning["zone_separation_score"],
        door_score=doors["door_score"],
        window_score=windows["window_score"],
        score=composite,
        verdict=verdict,
    )
