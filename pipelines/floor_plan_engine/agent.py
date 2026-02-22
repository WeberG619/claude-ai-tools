"""
Floor Plan Engine v4 — Agent Orchestrator.

Routes any input type to the appropriate pipeline, produces a WallPlan,
optionally analyzes it, and executes in Revit.

Three input pipelines → one intermediate format → one output target:

  IMAGE/PDF ──→ [Vision v2]    ──→ WallPlan JSON ──→ [Revit Bridge] ──→ Revit Model
  TEXT DESC ──→ [Wall Layout]  ──→ WallPlan JSON
  MANUAL    ──→ [Direct JSON]  ──→ WallPlan JSON
                                       |
                                 [Analysis Engine]
                                 (reasoning, scoring)
"""

from typing import Dict, Any, Optional, List

from .wall_model import WallPlan


def build_floor_plan(
    image_path: str = None,
    description: str = None,
    wall_plan_json: dict = None,
    # Generation parameters (for text pipeline)
    total_area: float = 1200,
    bedrooms: int = 3,
    bathrooms: Optional[int] = None,
    shape: str = "rectangle",
    # Execution options
    execute_revit: bool = True,
    analyze: bool = True,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Main entry point for the floor plan engine.

    Accepts any input type, produces WallPlan, optionally analyzes
    and executes in Revit.

    Args:
        image_path: Path to floor plan image/PDF (vision pipeline)
        description: Text description of desired plan (text pipeline)
        wall_plan_json: Direct WallPlan JSON dict (bypass pipeline)
        total_area: Total area in sq ft (text pipeline)
        bedrooms: Number of bedrooms (text pipeline)
        bathrooms: Number of bathrooms (text pipeline)
        shape: Building shape: "rectangle", "L", "T", "U" (text pipeline)
        execute_revit: Whether to send to Revit
        analyze: Whether to run reasoning analysis
        verbose: Print progress

    Returns:
        Dict with keys:
            wall_plan: WallPlan object
            wall_plan_json: Serialized dict
            analysis: FloorPlanAnalysis or None
            revit_result: Revit execution result or None
            errors: List of error strings
    """
    result = {
        "wall_plan": None,
        "wall_plan_json": None,
        "analysis": None,
        "revit_result": None,
        "errors": [],
    }

    # ── Step 1: Produce WallPlan ──
    plan = None

    if wall_plan_json is not None:
        # Direct JSON input
        if verbose:
            print("[AGENT] Using direct WallPlan JSON input")
        try:
            plan = WallPlan.from_dict(wall_plan_json)
        except Exception as e:
            result["errors"].append(f"Invalid WallPlan JSON: {e}")
            return result

    elif image_path is not None:
        # Vision pipeline
        if verbose:
            print(f"[AGENT] Extracting WallPlan from image: {image_path}")
        try:
            from .vision_v2 import extract_wall_plan
            plan = extract_wall_plan(image_path)
        except FileNotFoundError as e:
            result["errors"].append(str(e))
            return result
        except ImportError as e:
            result["errors"].append(f"Vision pipeline requires anthropic package: {e}")
            return result
        except Exception as e:
            result["errors"].append(f"Vision extraction failed: {e}")
            return result

    elif description is not None:
        # Text pipeline — parse description for parameters
        if verbose:
            print(f"[AGENT] Generating WallPlan from description")
        params = _parse_description(description)
        total_area = params.get("total_area", total_area)
        bedrooms = params.get("bedrooms", bedrooms)
        bathrooms = params.get("bathrooms", bathrooms)
        shape = params.get("shape", shape)

        from .wall_layout import generate_wall_plan
        plan = generate_wall_plan(
            total_area=total_area,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            shape=shape,
        )

    else:
        # Default: generate from parameters
        if verbose:
            print(f"[AGENT] Generating WallPlan: {bedrooms}BR, {total_area}SF, {shape}")
        from .wall_layout import generate_wall_plan
        plan = generate_wall_plan(
            total_area=total_area,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            shape=shape,
        )

    if plan is None:
        result["errors"].append("Failed to produce WallPlan")
        return result

    result["wall_plan"] = plan
    result["wall_plan_json"] = plan.to_dict()

    # ── Step 2: Validate geometry ──
    if verbose:
        print(f"[AGENT] Validating geometry...")
    from .vision_v2 import validate_wall_plan
    issues = validate_wall_plan(plan)
    if issues:
        if verbose:
            for issue in issues:
                print(f"  [WARN] {issue}")
        # Try auto-fix for closable gaps
        plan = _auto_fix_geometry(plan, issues, verbose)
        result["wall_plan"] = plan
        result["wall_plan_json"] = plan.to_dict()

    # ── Step 3: Analysis (optional) ──
    if analyze:
        if verbose:
            print(f"[AGENT] Running architectural analysis...")
        try:
            fp = plan.to_floor_plan()
            analysis = fp.analyze()
            result["analysis"] = analysis
            if verbose:
                print(f"  Score: {analysis.score:.0f}/100 ({analysis.verdict})")
                if analysis.unreachable_rooms:
                    print(f"  Unreachable: {', '.join(analysis.unreachable_rooms)}")
        except Exception as e:
            result["errors"].append(f"Analysis failed: {e}")

    # ── Step 4: Execute in Revit (optional) ──
    if execute_revit:
        if verbose:
            print(f"[AGENT] Executing in Revit...")
        try:
            from .wall_revit_bridge import execute_wall_plan
            revit_result = execute_wall_plan(plan, verbose=verbose)
            result["revit_result"] = revit_result
        except Exception as e:
            result["errors"].append(f"Revit execution failed: {e}")

    # ── Summary ──
    if verbose:
        _print_summary(result)

    return result


def _parse_description(description: str) -> Dict[str, Any]:
    """Parse natural language description into plan parameters.

    Extracts: total_area, bedrooms, bathrooms, shape from text like
    "3-bed, 2-bath, L-shaped, 1200sf"
    """
    import re
    params = {}
    text = description.lower()

    # Area
    area_match = re.search(r'(\d{3,4})\s*(?:sq\s*ft|sf|square\s*feet)', text)
    if area_match:
        params["total_area"] = float(area_match.group(1))

    # Bedrooms
    bed_match = re.search(r'(\d)\s*(?:-?\s*bed|br|bedroom)', text)
    if bed_match:
        params["bedrooms"] = int(bed_match.group(1))

    # Bathrooms
    bath_match = re.search(r'(\d)\s*(?:-?\s*bath|ba|bathroom)', text)
    if bath_match:
        params["bathrooms"] = int(bath_match.group(1))

    # Shape
    if "l-shape" in text or "l shape" in text:
        params["shape"] = "L"
    elif "t-shape" in text or "t shape" in text:
        params["shape"] = "T"
    elif "u-shape" in text or "u shape" in text:
        params["shape"] = "U"

    return params


def _auto_fix_geometry(plan: WallPlan, issues: List[str], verbose: bool) -> WallPlan:
    """Attempt to auto-fix geometry issues.

    Currently handles:
    - Snapping wall endpoints that are close but not touching
    """
    # Snap exterior wall endpoints
    ext = plan.exterior_walls
    if len(ext) >= 3:
        for i in range(len(ext)):
            w1 = ext[i]
            w2 = ext[(i + 1) % len(ext)]
            dx = abs(w1.end[0] - w2.start[0])
            dy = abs(w1.end[1] - w2.start[1])
            if 0 < (dx + dy) <= 1.0:
                # Snap w2's start to w1's end
                w2_idx = plan.walls.index(w2)
                plan.walls[w2_idx] = type(w2)(
                    w2.id, w1.end, w2.end,
                    w2.wall_type, w2.thickness_in, w2.height_ft)
                if verbose:
                    print(f"  [FIX] Snapped {w2.id} start to {w1.end}")

    return plan


def _print_summary(result: Dict[str, Any]):
    """Print a summary of the build result."""
    plan = result["wall_plan"]
    if plan is None:
        print("\n[AGENT] FAILED — no plan produced")
        for e in result["errors"]:
            print(f"  ERROR: {e}")
        return

    print(f"\n{'='*50}")
    print(f"FLOOR PLAN ENGINE v4 — COMPLETE")
    if plan.overall_width_ft and plan.overall_depth_ft:
        print(f"  Size: {plan.overall_width_ft}' x {plan.overall_depth_ft}'")
    print(f"  Walls: {len(plan.exterior_walls)} ext + {len(plan.interior_walls)} int")
    print(f"  Doors: {len(plan.doors)}")
    print(f"  Windows: {len(plan.windows)}")
    print(f"  Rooms: {len(plan.rooms)}")

    if result["analysis"]:
        a = result["analysis"]
        print(f"  Analysis: {a.score:.0f}/100 ({a.verdict})")

    if result["revit_result"]:
        r = result["revit_result"]
        if r.get("success"):
            total = (len(r.get('exterior_walls', [])) +
                     len(r.get('interior_walls', [])) +
                     len(r.get('doors', [])) +
                     len(r.get('windows', [])) +
                     len(r.get('rooms', [])))
            print(f"  Revit: {total} elements created")
        else:
            print(f"  Revit: FAILED — {r.get('error', 'unknown')}")

    if result["errors"]:
        for e in result["errors"]:
            print(f"  ERROR: {e}")

    print(f"{'='*50}")
