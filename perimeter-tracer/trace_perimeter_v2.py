#!/usr/bin/env python3
"""
Floor Plan Perimeter Tracer V2
Uses flood-fill from outside to find the TRUE exterior boundary.
"""

import cv2
import numpy as np
import json
import argparse
from pathlib import Path


def load_image(image_path: str) -> np.ndarray:
    """Load image from path."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not load image: {image_path}")
    return img


def find_building_boundary(img: np.ndarray, margin: int = 20) -> np.ndarray:
    """
    Find building boundary using flood fill from outside.

    Strategy:
    1. Convert to grayscale and threshold to get walls
    2. Flood fill from corner (guaranteed outside)
    3. Invert to get building interior
    4. Find contour of building shape
    """
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Threshold - anything dark is a wall (white in binary)
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    # binary: white = empty space, black = walls/lines
    # We want to flood fill from outside (white area) to find what's outside the building

    # Create a mask with 2-pixel border (required by floodFill)
    h, w = binary.shape
    mask = np.zeros((h + 2, w + 2), np.uint8)

    # Flood fill from top-left corner (definitely outside the building)
    flood = binary.copy()
    cv2.floodFill(flood, mask, (0, 0), 128)  # Fill outside with gray (128)

    # Now: 128 = outside, 255 = inside building (white rooms), 0 = walls
    # Create building mask: everything that's NOT outside
    building_mask = np.where(flood == 128, 0, 255).astype(np.uint8)

    # Close small gaps in walls (doors, windows) but preserve notches
    # Use very small kernel to only close door/window gaps, not architectural features
    kernel = np.ones((5, 5), np.uint8)
    closed = cv2.morphologyEx(building_mask, cv2.MORPH_CLOSE, kernel)

    # Find exterior contour
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        raise ValueError("No building boundary found")

    # Get largest contour (the building)
    largest = max(contours, key=cv2.contourArea)

    return largest, closed


def simplify_to_corners(contour: np.ndarray, epsilon_factor: float = 0.005) -> np.ndarray:
    """
    Simplify contour to corner points only.
    Uses Douglas-Peucker algorithm.
    """
    perimeter = cv2.arcLength(contour, True)
    epsilon = epsilon_factor * perimeter
    simplified = cv2.approxPolyDP(contour, epsilon, True)
    return simplified


def merge_close_corners(corners: list, threshold: int = 20) -> list:
    """
    Merge corners that are close together on the same axis.
    This removes zigzag patterns from window/door gaps.
    """
    if len(corners) < 4:
        return corners

    # Group corners that are on roughly the same horizontal or vertical line
    merged = []
    skip_next = set()

    for i, corner in enumerate(corners):
        if i in skip_next:
            continue

        # Check if next corner is very close (small deviation)
        next_i = (i + 1) % len(corners)
        prev_i = (i - 1) % len(corners)

        curr = corner
        next_c = corners[next_i]

        # If current and next are very close together (zigzag pattern)
        dist = np.sqrt((curr[0] - next_c[0])**2 + (curr[1] - next_c[1])**2)

        if dist < threshold:
            # Skip this pair - they represent a small notch
            # Use the midpoint
            mid_x = (curr[0] + next_c[0]) // 2
            mid_y = (curr[1] + next_c[1]) // 2
            merged.append([mid_x, mid_y])
            skip_next.add(next_i)
        else:
            merged.append(list(corner))

    return merged


def straighten_walls(corners: list, angle_threshold: float = 10.0) -> list:
    """
    Snap nearly-horizontal walls to horizontal and nearly-vertical walls to vertical.
    """
    n = len(corners)
    straightened = [list(c) for c in corners]

    for i in range(n):
        curr = straightened[i]
        next_c = straightened[(i + 1) % n]

        dx = abs(next_c[0] - curr[0])
        dy = abs(next_c[1] - curr[1])

        # If mostly horizontal (dy is small compared to dx)
        if dx > 0 and dy / dx < 0.1:  # Less than ~6 degree angle
            # Align to same Y
            avg_y = (curr[1] + next_c[1]) // 2
            curr[1] = avg_y
            next_c[1] = avg_y

        # If mostly vertical (dx is small compared to dy)
        elif dy > 0 and dx / dy < 0.1:
            # Align to same X
            avg_x = (curr[0] + next_c[0]) // 2
            curr[0] = avg_x
            next_c[0] = avg_x

    return straightened


def remove_collinear_corners(corners: list, tolerance: float = 5.0) -> list:
    """
    Remove corners that lie on a straight line between their neighbors.
    This cleans up redundant points on straight walls.
    """
    if len(corners) < 4:
        return corners

    result = []
    n = len(corners)

    for i in range(n):
        prev_c = corners[(i - 1) % n]
        curr = corners[i]
        next_c = corners[(i + 1) % n]

        # Check if current point is on the line between prev and next
        # Using cross product to measure perpendicular distance
        v1 = (next_c[0] - prev_c[0], next_c[1] - prev_c[1])
        v2 = (curr[0] - prev_c[0], curr[1] - prev_c[1])

        # Cross product gives area of parallelogram
        cross = abs(v1[0] * v2[1] - v1[1] * v2[0])
        # Length of base
        base = np.sqrt(v1[0]**2 + v1[1]**2)

        if base > 0:
            # Perpendicular distance from curr to line prev-next
            dist = cross / base
        else:
            dist = 0

        # Keep corner if it's not collinear (distance from line > tolerance)
        if dist > tolerance:
            result.append(curr)

    return result if len(result) >= 3 else corners


def order_corners_clockwise(corners: np.ndarray) -> list:
    """Order corners clockwise starting from top-left."""
    points = corners.reshape(-1, 2)

    # Find centroid
    center = points.mean(axis=0)

    # Sort by angle from center
    def angle_from_center(p):
        return np.arctan2(p[1] - center[1], p[0] - center[0])

    sorted_points = sorted(points, key=angle_from_center)

    # Find top-left (min x + y)
    top_left_idx = min(range(len(sorted_points)),
                       key=lambda i: sorted_points[i][0] + sorted_points[i][1])

    # Rotate to start from top-left
    ordered = sorted_points[top_left_idx:] + sorted_points[:top_left_idx]

    return ordered


def generate_walls(corners: list) -> list:
    """Generate wall segments from corners."""
    walls = []
    n = len(corners)

    for i in range(n):
        start = corners[i]
        end = corners[(i + 1) % n]

        walls.append({
            "wall_id": i + 1,
            "start": {"x": int(start[0]), "y": int(start[1])},
            "end": {"x": int(end[0]), "y": int(end[1])}
        })

    return walls


def trace_building(image_path: str, epsilon_factor: float = 0.008, clean: bool = True) -> dict:
    """Main function to trace building perimeter."""
    img = load_image(image_path)
    h, w = img.shape[:2]

    # Find building boundary
    contour, mask = find_building_boundary(img)

    # Simplify to corners
    simplified = simplify_to_corners(contour, epsilon_factor)

    # Order clockwise
    corners = order_corners_clockwise(simplified)

    # Clean up zigzag patterns from windows/doors
    if clean:
        # Multiple passes to collapse window notches
        for _ in range(3):
            corners = merge_close_corners(corners, threshold=30)
        corners = straighten_walls(corners)
        # Remove redundant collinear corners
        corners = remove_collinear_corners(corners)

    # Generate walls
    walls = generate_walls(corners)

    # Convert corners to output format
    corner_list = [{"x": int(c[0]), "y": int(c[1]), "unit": "pixels"} for c in corners]

    return {
        "image_path": str(image_path),
        "image_size": {"width": w, "height": h},
        "corner_count": len(corner_list),
        "wall_count": len(walls),
        "corners": corner_list,
        "walls": walls,
        "_debug_mask": mask  # For visualization
    }


def visualize(image_path: str, result: dict, output_path: str = None):
    """Draw detected perimeter on image."""
    img = load_image(image_path)

    corners = result["corners"]
    n = len(corners)

    # Draw walls (green lines)
    for i in range(n):
        pt1 = (corners[i]["x"], corners[i]["y"])
        pt2 = (corners[(i+1) % n]["x"], corners[(i+1) % n]["y"])
        cv2.line(img, pt1, pt2, (0, 255, 0), 3)

    # Draw corners (red circles with numbers)
    for i, corner in enumerate(corners):
        pt = (corner["x"], corner["y"])
        cv2.circle(img, pt, 10, (0, 0, 255), -1)
        cv2.putText(img, str(i + 1), (pt[0] + 12, pt[1] + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    if output_path:
        cv2.imwrite(output_path, img)
        print(f"Visualization saved to: {output_path}")

    # Also save the debug mask
    if "_debug_mask" in result:
        mask_path = str(Path(output_path).stem) + "_mask.png" if output_path else "debug_mask.png"
        cv2.imwrite(mask_path, result["_debug_mask"])
        print(f"Debug mask saved to: {mask_path}")

    return img


def main():
    parser = argparse.ArgumentParser(description="Trace floor plan perimeter V2")
    parser.add_argument("image", help="Path to floor plan image")
    parser.add_argument("--epsilon", type=float, default=0.008,
                        help="Polygon simplification factor")
    parser.add_argument("--visualize", "-v", action="store_true",
                        help="Generate visualization image")
    parser.add_argument("--output", "-o", help="Output JSON file path")

    args = parser.parse_args()

    # Trace
    result = trace_building(args.image, epsilon_factor=args.epsilon)

    # Remove debug data from JSON output
    output_result = {k: v for k, v in result.items() if not k.startswith("_")}

    # Output JSON
    output_json = json.dumps(output_result, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"Result saved to: {args.output}")
    else:
        print(output_json)

    # Visualize
    if args.visualize:
        viz_path = Path(args.image).stem + "_traced_v2.png"
        visualize(args.image, result, viz_path)

    print(f"\nFound {result['corner_count']} corners, {result['wall_count']} walls")


if __name__ == "__main__":
    main()
