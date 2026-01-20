#!/usr/bin/env python3
"""
Floor Plan Perimeter Tracer
Extracts exterior wall perimeter from floor plan images using OpenCV.
No interpretation, no assumptions - just traces thick black lines.
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


def isolate_thick_lines(img: np.ndarray, thickness_threshold: int = 5) -> np.ndarray:
    """
    Isolate thick black lines (exterior walls) from the image.

    Args:
        img: Input BGR image
        thickness_threshold: Minimum line thickness to keep (in pixels)

    Returns:
        Binary mask of thick lines only
    """
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Threshold to get black lines (invert so lines are white)
    # Use a higher threshold to catch dark gray lines too
    _, binary = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)

    # Morphological operations to keep only thick lines
    # Erode to remove thin lines
    kernel_erode = np.ones((thickness_threshold, thickness_threshold), np.uint8)
    eroded = cv2.erode(binary, kernel_erode, iterations=1)

    # Dilate back to restore thick lines - dilate more to close gaps
    kernel_dilate = np.ones((thickness_threshold + 2, thickness_threshold + 2), np.uint8)
    dilated = cv2.dilate(eroded, kernel_dilate, iterations=2)

    # Fill holes to make solid regions
    # Find contours and fill them
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(dilated)
    cv2.drawContours(filled, contours, -1, 255, -1)  # -1 thickness = fill

    return filled


def find_exterior_contour(binary: np.ndarray) -> np.ndarray:
    """
    Find the outermost (exterior) contour.

    Args:
        binary: Binary image with walls as white

    Returns:
        Contour points of exterior perimeter
    """
    # Find all contours
    contours, hierarchy = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,  # Only external contours
        cv2.CHAIN_APPROX_SIMPLE  # Compress to corner points
    )

    if not contours:
        raise ValueError("No contours found in image")

    # Get the largest contour (exterior walls)
    largest = max(contours, key=cv2.contourArea)

    return largest


def simplify_to_polygon(contour: np.ndarray, epsilon_factor: float = 0.01) -> np.ndarray:
    """
    Simplify contour to a polygon with corners only.

    Args:
        contour: Raw contour points
        epsilon_factor: Approximation accuracy (lower = more points)

    Returns:
        Simplified polygon corners
    """
    # Calculate perimeter
    perimeter = cv2.arcLength(contour, True)

    # Approximate to polygon
    epsilon = epsilon_factor * perimeter
    polygon = cv2.approxPolyDP(contour, epsilon, True)

    return polygon


def order_corners_clockwise(corners: np.ndarray) -> np.ndarray:
    """
    Order corners clockwise starting from top-left.

    Args:
        corners: Unordered corner points

    Returns:
        Corners ordered clockwise from top-left
    """
    # Reshape to (N, 2)
    points = corners.reshape(-1, 2)

    # Find centroid
    center = points.mean(axis=0)

    # Calculate angles from center
    angles = np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0])

    # Sort by angle (clockwise from top)
    # Adjust so top-left is first
    sorted_indices = np.argsort(angles)

    # Find the top-left point (minimum x + y)
    sums = points[:, 0] + points[:, 1]
    top_left_idx = np.argmin(sums)

    # Rotate to start from top-left
    sorted_points = points[sorted_indices]
    start_pos = np.where(sorted_indices == top_left_idx)[0][0]
    ordered = np.roll(sorted_points, -start_pos, axis=0)

    return ordered


def pixels_to_feet(corners: np.ndarray, img_width: int, img_height: int,
                   real_width_ft: float, real_height_ft: float) -> list:
    """
    Convert pixel coordinates to feet.

    Args:
        corners: Corner points in pixels
        img_width, img_height: Image dimensions in pixels
        real_width_ft, real_height_ft: Real-world dimensions in feet

    Returns:
        List of (x, y) tuples in feet
    """
    scale_x = real_width_ft / img_width
    scale_y = real_height_ft / img_height

    result = []
    for point in corners:
        x_ft = round(point[0] * scale_x, 2)
        # Flip Y because image Y is top-down, but we want bottom-up
        y_ft = round((img_height - point[1]) * scale_y, 2)
        result.append({"x": x_ft, "y": y_ft})

    return result


def generate_wall_segments(corners: list) -> list:
    """
    Generate wall segments from ordered corners.

    Args:
        corners: Ordered list of corner coordinates

    Returns:
        List of wall segments with start/end points
    """
    walls = []
    n = len(corners)

    for i in range(n):
        start = corners[i]
        end = corners[(i + 1) % n]  # Wrap to first point

        walls.append({
            "wall_id": i + 1,
            "start": start,
            "end": end
        })

    return walls


def trace_perimeter(image_path: str,
                    thickness_threshold: int = 5,
                    real_width_ft: float = None,
                    real_height_ft: float = None,
                    epsilon_factor: float = 0.005) -> dict:
    """
    Main function to trace floor plan perimeter.

    Args:
        image_path: Path to floor plan image
        thickness_threshold: Minimum line thickness to detect
        real_width_ft: Real width in feet (for scaling)
        real_height_ft: Real height in feet (for scaling)
        epsilon_factor: Polygon simplification factor

    Returns:
        Dictionary with corners, walls, and metadata
    """
    # Load image
    img = load_image(image_path)
    height, width = img.shape[:2]

    # Isolate thick lines
    thick_lines = isolate_thick_lines(img, thickness_threshold)

    # Find exterior contour
    contour = find_exterior_contour(thick_lines)

    # Simplify to polygon
    polygon = simplify_to_polygon(contour, epsilon_factor)

    # Order corners clockwise from top-left
    ordered = order_corners_clockwise(polygon)

    # Convert to output format
    if real_width_ft and real_height_ft:
        corners = pixels_to_feet(ordered, width, height, real_width_ft, real_height_ft)
    else:
        corners = [{"x": int(p[0]), "y": int(p[1]), "unit": "pixels"} for p in ordered]

    # Generate wall segments
    walls = generate_wall_segments(corners)

    return {
        "image_path": str(image_path),
        "image_size": {"width": width, "height": height},
        "scale": {
            "width_ft": real_width_ft,
            "height_ft": real_height_ft
        } if real_width_ft else None,
        "corner_count": len(corners),
        "wall_count": len(walls),
        "corners": corners,
        "walls": walls
    }


def visualize_result(image_path: str, result: dict, output_path: str = None):
    """
    Draw the detected perimeter on the image for verification.

    Args:
        image_path: Original image path
        result: Trace result dictionary
        output_path: Where to save visualization (optional)
    """
    img = load_image(image_path)

    # Draw corners
    for i, corner in enumerate(result["corners"]):
        if "unit" in corner and corner["unit"] == "pixels":
            pt = (corner["x"], corner["y"])
        else:
            # Convert feet back to pixels for drawing
            scale = result["image_size"]
            pt = (int(corner["x"] / result["scale"]["width_ft"] * scale["width"]),
                  int((result["scale"]["height_ft"] - corner["y"]) / result["scale"]["height_ft"] * scale["height"]))

        cv2.circle(img, pt, 10, (0, 0, 255), -1)
        cv2.putText(img, str(i + 1), (pt[0] + 15, pt[1] + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Draw walls
    corners = result["corners"]
    n = len(corners)
    for i in range(n):
        if "unit" in corners[0] and corners[0]["unit"] == "pixels":
            pt1 = (corners[i]["x"], corners[i]["y"])
            pt2 = (corners[(i+1) % n]["x"], corners[(i+1) % n]["y"])
        else:
            scale = result["image_size"]
            pt1 = (int(corners[i]["x"] / result["scale"]["width_ft"] * scale["width"]),
                   int((result["scale"]["height_ft"] - corners[i]["y"]) / result["scale"]["height_ft"] * scale["height"]))
            pt2 = (int(corners[(i+1) % n]["x"] / result["scale"]["width_ft"] * scale["width"]),
                   int((result["scale"]["height_ft"] - corners[(i+1) % n]["y"]) / result["scale"]["height_ft"] * scale["height"]))

        cv2.line(img, pt1, pt2, (0, 255, 0), 3)

    if output_path:
        cv2.imwrite(output_path, img)
        print(f"Visualization saved to: {output_path}")

    return img


def main():
    parser = argparse.ArgumentParser(description="Trace floor plan perimeter")
    parser.add_argument("image", help="Path to floor plan image")
    parser.add_argument("--width", type=float, help="Real width in feet")
    parser.add_argument("--height", type=float, help="Real height in feet")
    parser.add_argument("--thickness", type=int, default=5,
                        help="Minimum line thickness to detect (pixels)")
    parser.add_argument("--epsilon", type=float, default=0.005,
                        help="Polygon simplification factor (lower = more detail)")
    parser.add_argument("--visualize", "-v", action="store_true",
                        help="Generate visualization image")
    parser.add_argument("--output", "-o", help="Output JSON file path")

    args = parser.parse_args()

    # Trace perimeter
    result = trace_perimeter(
        args.image,
        thickness_threshold=args.thickness,
        real_width_ft=args.width,
        real_height_ft=args.height,
        epsilon_factor=args.epsilon
    )

    # Output JSON
    output_json = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"Result saved to: {args.output}")
    else:
        print(output_json)

    # Visualize if requested
    if args.visualize:
        viz_path = Path(args.image).stem + "_traced.png"
        visualize_result(args.image, result, viz_path)

    print(f"\nFound {result['corner_count']} corners, {result['wall_count']} walls")


if __name__ == "__main__":
    main()
