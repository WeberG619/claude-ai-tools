#!/usr/bin/env python3
"""
PDF/Image to DXF Converter
===========================
Converts PDF floor plans or images into DXF files that can be imported into Revit.

Two modes:
  1. VECTOR mode (default for PDFs with vector graphics):
     - Extracts lines, rectangles, curves directly from PDF paths
     - Preserves exact geometry — best quality
     - Uses pymupdf (fitz)

  2. IMAGE mode (for scanned PDFs, PNG, JPG):
     - Converts to grayscale, detects edges
     - Uses OpenCV HoughLinesP for line detection
     - Lower quality but works on any image

Scale handling:
  - Auto-detect from drawing extent vs expected building size
  - Manual override with --scale (e.g., "1/8" for 1/8"=1'-0")
  - Output DXF is in real-world inches

Usage:
    python pdf_to_dxf.py input.pdf -o output.dxf
    python pdf_to_dxf.py input.pdf --scale "1/8" -o output.dxf
    python pdf_to_dxf.py floorplan.png --mode image --scale "1/4" -o output.dxf
    python pdf_to_dxf.py input.pdf --page 1 --auto-scale --building-width 55

Dependencies:
    pip install pymupdf ezdxf opencv-python numpy pdf2image

Author: Weber Gouin / BD Architect + Claude
"""

import argparse
import json
import math
import os
import sys
from typing import List, Dict, Tuple, Optional

# Block torch/easyocr from loading (crashes on some WSL systems with old CUDA drivers).
# Tesseract OCR is used instead — lighter, faster, no torch dependency.
import importlib

class _TorchBlocker:
    """Prevent accidental torch imports that crash on incompatible CUDA setups."""
    def find_module(self, name, path=None):
        if name == 'torch' or name.startswith('torch.'):
            return self
    def load_module(self, name):
        raise ImportError(f"torch blocked by pdf_to_dxf (use tesseract for OCR)")

sys.meta_path.insert(0, _TorchBlocker())

import ezdxf
import numpy as np

try:
    import fitz  # pymupdf
except ImportError:
    fitz = None

try:
    import cv2
except ImportError:
    cv2 = None

# OCR imports are lazy to avoid torch crashes on some systems
easyocr = None
_ocr_reader = None

try:
    import pytesseract
except ImportError:
    pytesseract = None


# ============================================================================
# SCALE DEFINITIONS
# ============================================================================

# Common architectural scales: name → (inches on paper per foot in reality)
# Scale factor = 12 / inches_per_foot (converts paper inches to real inches)
ARCH_SCALES = {
    "1/16":  {"paper_per_foot": 1/16, "factor": 192, "label": '1/16" = 1\'-0"'},
    "1/8":   {"paper_per_foot": 1/8,  "factor": 96,  "label": '1/8" = 1\'-0"'},
    "3/16":  {"paper_per_foot": 3/16, "factor": 64,  "label": '3/16" = 1\'-0"'},
    "1/4":   {"paper_per_foot": 1/4,  "factor": 48,  "label": '1/4" = 1\'-0"'},
    "3/8":   {"paper_per_foot": 3/8,  "factor": 32,  "label": '3/8" = 1\'-0"'},
    "1/2":   {"paper_per_foot": 1/2,  "factor": 24,  "label": '1/2" = 1\'-0"'},
    "3/4":   {"paper_per_foot": 3/4,  "factor": 16,  "label": '3/4" = 1\'-0"'},
    "1":     {"paper_per_foot": 1,    "factor": 12,  "label": '1" = 1\'-0"'},
    "1.5":   {"paper_per_foot": 1.5,  "factor": 8,   "label": '1-1/2" = 1\'-0"'},
    "3":     {"paper_per_foot": 3,    "factor": 4,   "label": '3" = 1\'-0"'},
}


def parse_scale(scale_str: str) -> float:
    """
    Parse a scale string and return the multiplication factor (paper inches → real inches).

    Accepts:
      "1/8"          → 96  (1/8" = 1'-0")
      "1/4"          → 48
      "96"           → 96  (direct factor)
      "1:96"         → 96
    """
    scale_str = scale_str.strip()

    # Direct lookup
    if scale_str in ARCH_SCALES:
        return ARCH_SCALES[scale_str]["factor"]

    # Ratio format "1:96"
    if ":" in scale_str:
        parts = scale_str.split(":")
        return float(parts[1]) / float(parts[0])

    # Try as direct number
    try:
        return float(scale_str)
    except ValueError:
        pass

    # Try as fraction
    if "/" in scale_str:
        parts = scale_str.split("/")
        paper_per_foot = float(parts[0]) / float(parts[1])
        return 12.0 / paper_per_foot

    raise ValueError(f"Cannot parse scale: {scale_str}")


def auto_detect_scale(drawing_width_pts: float, drawing_height_pts: float,
                      expected_width_ft: float = 55.0,
                      expected_range_ft: Tuple[float, float] = (20, 120)) -> str:
    """
    Auto-detect architectural scale from drawing extent.

    Args:
        drawing_width_pts: Drawing width in PDF points
        drawing_height_pts: Drawing height in PDF points
        expected_width_ft: Expected building width (helps refine guess)
        expected_range_ft: Valid building width range

    Returns:
        Best matching scale name (e.g., "1/8")
    """
    drawing_width_in = drawing_width_pts / 72.0
    drawing_height_in = drawing_height_pts / 72.0

    # Use the larger dimension
    drawing_size_in = max(drawing_width_in, drawing_height_in)

    best_scale = None
    best_error = float('inf')

    for name, info in ARCH_SCALES.items():
        building_ft = drawing_size_in * info["factor"] / 12.0

        # Check if result is in reasonable range
        if expected_range_ft[0] <= building_ft <= expected_range_ft[1]:
            error = abs(building_ft - expected_width_ft)
            if error < best_error:
                best_error = error
                best_scale = name

    if best_scale is None:
        # Default to 1/8" = 1'-0" if no good match
        best_scale = "1/8"

    return best_scale


# ============================================================================
# VECTOR EXTRACTION (from PDF)
# ============================================================================

def extract_vectors_from_pdf(pdf_path: str, page_num: int = 0,
                             min_line_pts: float = 2.0) -> Dict:
    """
    Extract vector geometry from a PDF page.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)
        min_line_pts: Minimum line length in PDF points to include

    Returns:
        Dict with lines, rectangles, curves, and metadata
    """
    if fitz is None:
        raise ImportError("pymupdf (fitz) is required for vector extraction. Install: pip install pymupdf")

    doc = fitz.open(pdf_path)
    if page_num >= len(doc):
        raise ValueError(f"Page {page_num} not found (PDF has {len(doc)} pages)")

    page = doc[page_num]
    drawings = page.get_drawings()

    lines = []
    rectangles = []
    curves = []
    all_x = []
    all_y = []

    for d in drawings:
        color = d.get("color")
        fill = d.get("fill")
        width = d.get("width", 0)

        for item in d["items"]:
            if item[0] == "l":  # line segment
                p1, p2 = item[1], item[2]
                length = math.hypot(p2.x - p1.x, p2.y - p1.y)
                if length >= min_line_pts:
                    lines.append({
                        "x1": p1.x, "y1": p1.y,
                        "x2": p2.x, "y2": p2.y,
                        "length": length,
                        "width": width,
                    })
                    all_x.extend([p1.x, p2.x])
                    all_y.extend([p1.y, p2.y])

            elif item[0] == "re":  # rectangle
                rect = item[1]
                w = abs(rect.x1 - rect.x0)
                h = abs(rect.y1 - rect.y0)
                if max(w, h) >= min_line_pts:
                    rectangles.append({
                        "x0": rect.x0, "y0": rect.y0,
                        "x1": rect.x1, "y1": rect.y1,
                        "width": w, "height": h,
                        "fill": fill,
                    })
                    all_x.extend([rect.x0, rect.x1])
                    all_y.extend([rect.y0, rect.y1])

            elif item[0] == "c":  # cubic bezier curve
                # item[1..4] are the 4 control points
                pts = [item[i] for i in range(1, min(5, len(item))) if hasattr(item[i], 'x')]
                if len(pts) >= 2:
                    curves.append({
                        "points": [{"x": p.x, "y": p.y} for p in pts],
                    })
                    for p in pts:
                        all_x.append(p.x)
                        all_y.append(p.y)

            elif item[0] == "qu":  # quad (4-point polygon)
                # Convert quad to 4 line segments
                quad = item[1]
                pts = [(quad.ul.x, quad.ul.y), (quad.ur.x, quad.ur.y),
                       (quad.lr.x, quad.lr.y), (quad.ll.x, quad.ll.y)]
                for i in range(4):
                    x1, y1 = pts[i]
                    x2, y2 = pts[(i + 1) % 4]
                    length = math.hypot(x2 - x1, y2 - y1)
                    if length >= min_line_pts:
                        lines.append({
                            "x1": x1, "y1": y1,
                            "x2": x2, "y2": y2,
                            "length": length,
                            "width": width,
                        })
                all_x.extend([p[0] for p in pts])
                all_y.extend([p[1] for p in pts])

    # Capture page dimensions before closing document
    page_width = page.rect.width
    page_height = page.rect.height
    total_paths = len(drawings)

    doc.close()

    # Compute bounds
    if all_x and all_y:
        bounds = {
            "min_x": min(all_x), "max_x": max(all_x),
            "min_y": min(all_y), "max_y": max(all_y),
            "width": max(all_x) - min(all_x),
            "height": max(all_y) - min(all_y),
        }
    else:
        bounds = {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0, "width": 0, "height": 0}

    return {
        "mode": "vector",
        "page_width": page_width,
        "page_height": page_height,
        "lines": lines,
        "rectangles": rectangles,
        "curves": curves,
        "bounds": bounds,
        "total_paths": total_paths,
    }


# ============================================================================
# OCR TEXT EXTRACTION
# ============================================================================

def _get_ocr_reader():
    """Lazy-init the easyocr reader (heavy on first call, imports torch)."""
    global _ocr_reader, easyocr
    if _ocr_reader is None:
        if easyocr is None:
            try:
                import easyocr as _easyocr
                easyocr = _easyocr
            except (ImportError, Exception):
                return None
        try:
            _ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        except Exception:
            _ocr_reader = None
    return _ocr_reader


def _extract_text_with_tesseract(img: np.ndarray) -> List[Dict]:
    """
    Extract text using tesseract OCR. Handles WSL→Windows path conversion.
    Upscales small images 3x for better OCR accuracy on floor plan text.
    """
    import subprocess

    tess_cmd = "/mnt/c/Program Files/Tesseract-OCR/tesseract.exe"
    if not os.path.exists(tess_cmd):
        import shutil
        tess_cmd = shutil.which("tesseract")
        if not tess_cmd:
            return []

    is_windows_exe = tess_cmd.endswith(".exe")

    try:
        # Upscale small images for better OCR accuracy
        h, w = img.shape[:2]
        scale = 1
        if max(w, h) < 1500:
            scale = 3
            ocr_img = cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
        else:
            ocr_img = img

        tmp_dir = "/mnt/d/_CLAUDE-TOOLS"
        input_path = os.path.join(tmp_dir, "_ocr_temp_input.png")
        output_base = os.path.join(tmp_dir, "_ocr_temp_output")
        output_tsv = output_base + ".tsv"

        cv2.imwrite(input_path, ocr_img)

        if is_windows_exe:
            win_input = input_path.replace("/mnt/d/", "D:\\\\").replace("/", "\\\\")
            win_output = output_base.replace("/mnt/d/", "D:\\\\").replace("/", "\\\\")
            # PSM 11 = sparse text — best for floor plans with scattered labels
            cmd = [tess_cmd, win_input, win_output, "--psm", "11", "tsv"]
        else:
            cmd = [tess_cmd, input_path, output_base, "--psm", "11", "tsv"]

        subprocess.run(cmd, capture_output=True, timeout=30)

        if not os.path.exists(output_tsv):
            return []

        texts = []
        with open(output_tsv, 'r', encoding='utf-8', errors='ignore') as f:
            f.readline()  # skip header
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) < 12:
                    continue
                conf_str = parts[10].strip()
                conf = float(conf_str) if conf_str.replace('-', '').replace('.', '').isdigit() else -1
                text = parts[11].strip()
                if not text or conf < 25:
                    continue
                x, y, bw, bh = int(parts[6]), int(parts[7]), int(parts[8]), int(parts[9])
                # Scale coordinates back to original image size
                texts.append({
                    "text": text,
                    "confidence": conf / 100.0,
                    "x_min": float(x) / scale, "y_min": float(y) / scale,
                    "x_max": float(x + bw) / scale, "y_max": float(y + bh) / scale,
                    "center_x": float(x + bw / 2) / scale,
                    "center_y": float(y + bh / 2) / scale,
                })

        # Cleanup temp files
        for fp in [input_path, output_tsv]:
            if os.path.exists(fp):
                os.remove(fp)

        return texts
    except Exception as e:
        print(f"  tesseract OCR failed: {e}")
        return []


def _extract_text_regions(img: np.ndarray) -> List[Dict]:
    """
    Extract text from image using best available OCR engine.
    Tries pytesseract first (lighter), falls back to easyocr.
    Works on pure raster images.
    """
    # Try direct tesseract first (lighter weight, no torch dependency)
    texts = _extract_text_with_tesseract(img)
    if texts:
        return texts

    # Fall back to easyocr (heavy — imports torch)
    reader = _get_ocr_reader()
    if reader is not None:
        try:
            results = reader.readtext(img, paragraph=False)
            texts = []
            for (bbox, text, conf) in results:
                if conf < 0.3:
                    continue
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                texts.append({
                    "text": text,
                    "confidence": conf,
                    "x_min": min(xs), "y_min": min(ys),
                    "x_max": max(xs), "y_max": max(ys),
                    "center_x": sum(xs) / 4.0,
                    "center_y": sum(ys) / 4.0,
                })
            return texts
        except Exception as e:
            print(f"  easyocr failed: {e}")

    return []


def _mask_text_regions(edges: np.ndarray, text_regions: List[Dict],
                       padding: int = 3) -> np.ndarray:
    """
    Black out text regions in the edge image so Hough doesn't pick up
    text character edges as wall lines.
    """
    masked = edges.copy()
    for t in text_regions:
        x1 = max(0, int(t["x_min"]) - padding)
        y1 = max(0, int(t["y_min"]) - padding)
        x2 = min(masked.shape[1], int(t["x_max"]) + padding)
        y2 = min(masked.shape[0], int(t["y_max"]) + padding)
        masked[y1:y2, x1:x2] = 0
    return masked


def _parse_room_dimensions(texts: List[Dict]) -> List[Dict]:
    """
    Find room dimension labels like "10'1\" x 11'1\"" or "11'-7\" x 15'-7\"".
    Returns parsed dimensions with pixel positions.
    """
    import re
    dims = []
    # Patterns: 10'1" x 11'1", 11'-7" x 15'-7", 10'1 x 11'1
    # Match: 10'1" x 11'1", 11'-7" x 15'-7", 10'1 x 11'1
    pattern = re.compile(
        r"(\d+)['\u2019]\-?\s*(\d+)[\"|\u201C\u201D]?\s*[xX\u00d7]\s*(\d+)['\u2019]\-?\s*(\d+)[\"|\u201C\u201D]?"
    )
    for t in texts:
        m = pattern.search(t["text"])
        if m:
            w_ft, w_in, h_ft, h_in = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            dims.append({
                "width_inches": w_ft * 12 + w_in,
                "height_inches": h_ft * 12 + h_in,
                "text": t["text"],
                "center_x": t["center_x"],
                "center_y": t["center_y"],
                "bbox": t,
            })
    return dims


# ============================================================================
# WALL-PAIR DETECTION
# ============================================================================

def _classify_wall_vs_floor_lines(lines: List[Dict],
                                   wall_thickness_range: Tuple[float, float] = (2.0, 15.0)
                                   ) -> Tuple[List[Dict], List[Dict]]:
    """
    Separate wall lines (paired parallel lines) from floor/other lines (singles).

    Walls are output with both edge lines + thickness info so they can be drawn
    as two parallel lines with solid fill (like the original floor plan).
    Single unpaired lines go to floor/other layer.

    Returns:
        (wall_pairs, floor_lines) — wall_pairs have edge1, edge2, thickness, direction
    """
    min_t, max_t = wall_thickness_range

    h_lines = []
    v_lines = []
    diag_lines = []

    for ln in lines:
        x1, y1, x2, y2 = ln["x1"], ln["y1"], ln["x2"], ln["y2"]
        if y1 == y2:
            h_lines.append((y1, min(x1, x2), max(x1, x2), ln))
        elif x1 == x2:
            v_lines.append((x1, min(y1, y2), max(y1, y2), ln))
        else:
            diag_lines.append(ln)

    walls = []
    floor = []
    h_paired = set()
    v_paired = set()

    # Find horizontal wall pairs
    h_lines.sort(key=lambda x: x[0])
    for i in range(len(h_lines)):
        if i in h_paired:
            continue
        y_i, xmin_i, xmax_i, _ = h_lines[i]
        best_j = None
        best_overlap = 0
        for j in range(i + 1, len(h_lines)):
            if j in h_paired:
                continue
            y_j, xmin_j, xmax_j, _ = h_lines[j]
            gap = y_j - y_i
            if gap > max_t:
                break
            if gap < min_t:
                continue
            overlap = min(xmax_i, xmax_j) - max(xmin_i, xmin_j)
            if overlap > 0 and overlap > best_overlap:
                best_j = j
                best_overlap = overlap
        if best_j is not None:
            y_j, xmin_j, xmax_j, _ = h_lines[best_j]
            x_start = min(xmin_i, xmin_j)
            x_end = max(xmax_i, xmax_j)
            thickness = abs(y_j - y_i)
            walls.append({
                "direction": "H",
                "thickness": thickness,
                "length": x_end - x_start,
                # Edge 1 (top)
                "e1_x1": x_start, "e1_y1": y_i, "e1_x2": x_end, "e1_y2": y_i,
                # Edge 2 (bottom)
                "e2_x1": x_start, "e2_y1": y_j, "e2_x2": x_end, "e2_y2": y_j,
                # Centerline for reference
                "x1": x_start, "y1": (y_i + y_j) / 2.0,
                "x2": x_end, "y2": (y_i + y_j) / 2.0,
                "width": thickness,
            })
            h_paired.add(i)
            h_paired.add(best_j)

    for i, (y, xmin, xmax, ln) in enumerate(h_lines):
        if i not in h_paired:
            floor.append(ln)

    # Find vertical wall pairs
    v_lines.sort(key=lambda x: x[0])
    for i in range(len(v_lines)):
        if i in v_paired:
            continue
        x_i, ymin_i, ymax_i, _ = v_lines[i]
        best_j = None
        best_overlap = 0
        for j in range(i + 1, len(v_lines)):
            if j in v_paired:
                continue
            x_j, ymin_j, ymax_j, _ = v_lines[j]
            gap = x_j - x_i
            if gap > max_t:
                break
            if gap < min_t:
                continue
            overlap = min(ymax_i, ymax_j) - max(ymin_i, ymin_j)
            if overlap > 0 and overlap > best_overlap:
                best_j = j
                best_overlap = overlap
        if best_j is not None:
            x_j, ymin_j, ymax_j, _ = v_lines[best_j]
            y_start = min(ymin_i, ymin_j)
            y_end = max(ymax_i, ymax_j)
            thickness = abs(x_j - x_i)
            walls.append({
                "direction": "V",
                "thickness": thickness,
                "length": y_end - y_start,
                "e1_x1": x_i, "e1_y1": y_start, "e1_x2": x_i, "e1_y2": y_end,
                "e2_x1": x_j, "e2_y1": y_start, "e2_x2": x_j, "e2_y2": y_end,
                "x1": (x_i + x_j) / 2.0, "y1": y_start,
                "x2": (x_i + x_j) / 2.0, "y2": y_end,
                "width": thickness,
            })
            v_paired.add(i)
            v_paired.add(best_j)

    for i, (x, ymin, ymax, ln) in enumerate(v_lines):
        if i not in v_paired:
            floor.append(ln)

    floor.extend(diag_lines)
    return walls, floor


def _detect_door_arcs(gray: np.ndarray, walls: List[Dict],
                       min_radius: int = 10, max_radius: int = 80) -> List[Dict]:
    """
    Detect quarter-circle door swings in the image.
    Door arcs appear as curved lines near wall endpoints.

    Strategy: Use HoughCircles to find circular arcs, then strictly filter to
    those whose center is very close to a wall endpoint (hinge point).
    """
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Scale radius range for image size
    h, w = gray.shape[:2]
    size_ratio = max(w, h) / 2000.0
    min_r = max(5, int(min_radius * size_ratio))
    max_r = max(20, int(max_radius * size_ratio))

    circles = cv2.HoughCircles(
        binary, cv2.HOUGH_GRADIENT, dp=1.5,
        minDist=max_r,  # doors don't overlap
        param1=100, param2=25,
        minRadius=min_r, maxRadius=max_r
    )

    # Collect wall endpoints for proximity check
    wall_pts = []
    for wall in walls:
        wall_pts.append((wall["e1_x1"], wall["e1_y1"]))
        wall_pts.append((wall["e1_x2"], wall["e1_y2"]))
        wall_pts.append((wall["e2_x1"], wall["e2_y1"]))
        wall_pts.append((wall["e2_x2"], wall["e2_y2"]))

    doors = []
    if circles is not None:
        for c in circles[0]:
            cx, cy, r = float(c[0]), float(c[1]), float(c[2])
            # Door arc center MUST be near a wall endpoint (the hinge point)
            # Use tight tolerance: center within wall thickness distance
            best_dist = float("inf")
            best_pt = None
            for wx, wy in wall_pts:
                d = math.hypot(cx - wx, cy - wy)
                if d < best_dist:
                    best_dist = d
                    best_pt = (wx, wy)

            # Only accept if center is within ~1 radius of a wall endpoint
            # (the hinge point is at a wall end, arc center is at hinge)
            max_hinge_dist = max(r * 1.0, 10.0)
            if best_dist > max_hinge_dist:
                continue

            # Determine quadrant: arc sweeps away from the wall
            # Use vector from hinge point toward center to pick start angle
            if best_pt:
                dx = cx - best_pt[0]
                dy = cy - best_pt[1]
                base_angle = math.degrees(math.atan2(-dy, dx))  # -dy for image coords
                start_angle = base_angle
                end_angle = base_angle + 90.0
            else:
                start_angle, end_angle = 0.0, 90.0

            doors.append({
                "center_x": cx, "center_y": cy,
                "radius": r,
                "start_angle": start_angle,
                "end_angle": end_angle,
                "type": "door_swing",
            })

    # Deduplicate: remove doors whose centers are very close
    filtered = []
    for door in doors:
        duplicate = False
        for kept in filtered:
            if math.hypot(door["center_x"] - kept["center_x"],
                          door["center_y"] - kept["center_y"]) < min_r:
                duplicate = True
                break
        if not duplicate:
            filtered.append(door)

    return filtered


def _detect_windows(lines: List[Dict], walls: List[Dict],
                    spacing_range: Tuple[float, float] = (1.0, 8.0)) -> Tuple[List[Dict], List[Dict]]:
    """
    Detect window patterns: 3 parallel lines close together within a wall gap.

    In floor plans, windows appear as 2-3 short parallel lines crossing a wall
    opening (perpendicular to the wall direction). They're typically:
    - Short segments spanning the wall thickness
    - Evenly spaced within a wall opening
    - Perpendicular or parallel to the wall

    Args:
        lines: Floor/other lines (singles not paired as walls)
        walls: Detected wall pairs
        spacing_range: (min, max) pixel distance between window lines

    Returns:
        (windows, remaining_lines) — windows are dicts with center/size info
    """
    min_sp, max_sp = spacing_range

    # Group lines by direction and position
    h_lines = []  # (y, xmin, xmax, idx)
    v_lines = []  # (x, ymin, ymax, idx)

    for i, ln in enumerate(lines):
        x1, y1, x2, y2 = ln["x1"], ln["y1"], ln["x2"], ln["y2"]
        if y1 == y2:
            h_lines.append((y1, min(x1, x2), max(x1, x2), i))
        elif x1 == x2:
            v_lines.append((x1, min(y1, y2), max(y1, y2), i))

    windows = []
    used_indices = set()

    # Find groups of 3 horizontal lines at similar X range, spaced evenly
    h_lines.sort(key=lambda x: (x[1], x[0]))  # sort by xmin then y
    for i in range(len(h_lines)):
        if h_lines[i][3] in used_indices:
            continue
        y_i, xmin_i, xmax_i, idx_i = h_lines[i]
        group = [(y_i, xmin_i, xmax_i, idx_i)]

        for j in range(i + 1, len(h_lines)):
            if h_lines[j][3] in used_indices:
                continue
            y_j, xmin_j, xmax_j, idx_j = h_lines[j]
            # Check: similar X range (overlap > 50% of shorter line)
            overlap = min(xmax_i, xmax_j) - max(xmin_i, xmin_j)
            shorter = min(xmax_i - xmin_i, xmax_j - xmin_j)
            if shorter > 0 and overlap / shorter < 0.5:
                continue
            # Check: spacing from last line in group
            last_y = group[-1][0]
            gap = abs(y_j - last_y)
            if gap < min_sp:
                continue
            if gap > max_sp:
                break
            group.append((y_j, xmin_j, xmax_j, idx_j))
            if len(group) >= 3:
                break

        if len(group) >= 3:
            # This looks like a window (3+ parallel lines, evenly spaced)
            ys = [g[0] for g in group]
            xs_min = min(g[1] for g in group)
            xs_max = max(g[2] for g in group)
            windows.append({
                "type": "window",
                "direction": "H",  # horizontal lines = window in vertical wall
                "center_x": (xs_min + xs_max) / 2.0,
                "center_y": (min(ys) + max(ys)) / 2.0,
                "width": xs_max - xs_min,
                "height": max(ys) - min(ys),
                "x_min": xs_min, "x_max": xs_max,
                "y_min": min(ys), "y_max": max(ys),
                "line_count": len(group),
            })
            for g in group:
                used_indices.add(g[3])

    # Find groups of 3 vertical lines at similar Y range, spaced evenly
    v_lines.sort(key=lambda x: (x[1], x[0]))  # sort by ymin then x
    for i in range(len(v_lines)):
        if v_lines[i][3] in used_indices:
            continue
        x_i, ymin_i, ymax_i, idx_i = v_lines[i]
        group = [(x_i, ymin_i, ymax_i, idx_i)]

        for j in range(i + 1, len(v_lines)):
            if v_lines[j][3] in used_indices:
                continue
            x_j, ymin_j, ymax_j, idx_j = v_lines[j]
            overlap = min(ymax_i, ymax_j) - max(ymin_i, ymin_j)
            shorter = min(ymax_i - ymin_i, ymax_j - ymin_j)
            if shorter > 0 and overlap / shorter < 0.5:
                continue
            last_x = group[-1][0]
            gap = abs(x_j - last_x)
            if gap < min_sp:
                continue
            if gap > max_sp:
                break
            group.append((x_j, ymin_j, ymax_j, idx_j))
            if len(group) >= 3:
                break

        if len(group) >= 3:
            xs = [g[0] for g in group]
            ys_min = min(g[1] for g in group)
            ys_max = max(g[2] for g in group)
            windows.append({
                "type": "window",
                "direction": "V",  # vertical lines = window in horizontal wall
                "center_x": (min(xs) + max(xs)) / 2.0,
                "center_y": (ys_min + ys_max) / 2.0,
                "width": max(xs) - min(xs),
                "height": ys_max - ys_min,
                "x_min": min(xs), "x_max": max(xs),
                "y_min": ys_min, "y_max": ys_max,
                "line_count": len(group),
            })
            for g in group:
                used_indices.add(g[3])

    remaining = [ln for i, ln in enumerate(lines) if i not in used_indices]
    return windows, remaining


# ============================================================================
# TWO-LAYER DECOMPOSITION (thick walls vs thin features)
# ============================================================================

def _auto_detect_wall_thickness(binary: np.ndarray) -> int:
    """
    Auto-detect wall thickness by measuring consecutive white-pixel run lengths.
    Samples rows and columns, returns mode of runs in 3-20px range.
    """
    from collections import Counter
    h, w = binary.shape
    run_lengths = []

    # Sample 20 evenly-spaced rows
    for row_idx in np.linspace(0, h - 1, 20, dtype=int):
        row = binary[row_idx]
        run_len = 0
        for px in row:
            if px > 0:
                run_len += 1
            else:
                if 3 <= run_len <= 20:
                    run_lengths.append(run_len)
                run_len = 0
        if 3 <= run_len <= 20:
            run_lengths.append(run_len)

    # Sample 20 evenly-spaced columns
    for col_idx in np.linspace(0, w - 1, 20, dtype=int):
        col = binary[:, col_idx]
        run_len = 0
        for px in col:
            if px > 0:
                run_len += 1
            else:
                if 3 <= run_len <= 20:
                    run_lengths.append(run_len)
                run_len = 0
        if 3 <= run_len <= 20:
            run_lengths.append(run_len)

    if not run_lengths:
        return 7  # default fallback

    counts = Counter(run_lengths)
    return counts.most_common(1)[0][0]


def _create_thick_thin_masks(gray: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Two-layer pixel decomposition for bold-wall floor plans.
    Separates thick walls from thin features (doors, windows, fixtures).

    Returns:
        (binary, thick_mask, thin_mask)
    """
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Close small gaps in walls
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_kernel, iterations=1)

    wall_thickness = _auto_detect_wall_thickness(binary)
    print(f"  Auto-detected wall thickness: {wall_thickness}px")

    # Erode to remove thin features, keeping only thick walls
    erode_size = max(2, wall_thickness // 2)
    erode_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (erode_size, erode_size))
    eroded = cv2.erode(binary, erode_kernel, iterations=2)

    # Dilate back to restore wall dimensions
    thick_mask = cv2.dilate(eroded, erode_kernel, iterations=2)

    # Thin features = binary minus thick walls
    thin_mask = cv2.subtract(binary, thick_mask)

    # Clean noise from thin mask
    open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    thin_mask = cv2.morphologyEx(thin_mask, cv2.MORPH_OPEN, open_kernel)

    return binary, thick_mask, thin_mask


def _extract_walls_from_thick_mask(thick_mask: np.ndarray) -> Tuple[List[Dict], List[Tuple]]:
    """
    Extract wall pairs from thick_mask via edge detection + HoughLinesP + pairing.
    Connected wall regions are decomposed into individual wall segments by
    extracting edges, detecting lines, and pairing parallel edge lines.

    Returns:
        (wall_pairs, wall_endpoints)
    """
    # Extract edges of thick wall regions
    grad_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    edges = cv2.morphologyEx(thick_mask, cv2.MORPH_GRADIENT, grad_kernel)

    # Detect lines on wall edges
    h, w = edges.shape
    size_ratio = max(w, h) / 2000.0
    min_len = max(10, int(50 * size_ratio))
    threshold = max(25, int(80 * size_ratio))
    gap = max(5, int(5 * max(1.0, size_ratio)))
    if max(w, h) < 1000:
        gap = max(gap, 10)

    hough_lines = cv2.HoughLinesP(
        edges, rho=1, theta=np.pi / 180,
        threshold=threshold, minLineLength=min_len, maxLineGap=gap
    )

    lines = []
    if hough_lines is not None:
        for hl in hough_lines:
            x1, y1, x2, y2 = hl[0]
            length = math.hypot(x2 - x1, y2 - y1)
            lines.append({
                "x1": float(x1), "y1": float(y1),
                "x2": float(x2), "y2": float(y2),
                "length": length, "width": 0,
            })

    # Process: snap to H/V, merge collinear (small gap to preserve door openings),
    # deduplicate, filter short
    lines = _snap_lines_to_hv(lines)
    # Use small merge gap (8px) so wall segments stay split at door/window openings
    # (doors are 18-45px gaps, so gap_tol=8 won't bridge them)
    lines = _merge_collinear_segments(lines, gap_tol=8.0)
    lines = _deduplicate_lines(lines)
    lines = _filter_short_lines(lines, min_len)

    # Pair parallel edge lines into wall pairs
    walls, _unpaired = _classify_wall_vs_floor_lines(lines)

    # Collect wall endpoints for door detection
    wall_endpoints = []
    for wall in walls:
        wall_endpoints.append((wall['x1'], wall['y1']))
        wall_endpoints.append((wall['x2'], wall['y2']))

    return walls, wall_endpoints


def _clean_wall_corners(walls: List[Dict], snap_tol: float = 3.0) -> List[Dict]:
    """
    Clean up wall corners by snapping nearby edge endpoints to shared positions.
    This produces clean 90-degree joints at exterior corners and T-junctions.
    """
    # Collect all edge endpoints with references back to walls
    points = []  # (x, y, wall_idx, key_x, key_y)
    for i, w in enumerate(walls):
        for edge in ('e1', 'e2'):
            for end in ('1', '2'):
                kx = f'{edge}_x{end}'
                ky = f'{edge}_y{end}'
                points.append((w[kx], w[ky], i, kx, ky))

    # Snap close endpoints to shared positions
    n = len(points)
    for i in range(n):
        for j in range(i + 1, n):
            if points[i][2] == points[j][2]:
                continue  # same wall
            x1, y1 = points[i][0], points[i][1]
            x2, y2 = points[j][0], points[j][1]
            if abs(x1 - x2) < snap_tol and abs(y1 - y2) < snap_tol:
                mx = (x1 + x2) / 2.0
                my = (y1 + y2) / 2.0
                walls[points[i][2]][points[i][3]] = mx
                walls[points[i][2]][points[i][4]] = my
                walls[points[j][2]][points[j][3]] = mx
                walls[points[j][2]][points[j][4]] = my

    return walls


def _detect_doors_from_thin_mask(thin_mask: np.ndarray, thick_mask: np.ndarray,
                                  walls: List[Dict]) -> List[Dict]:
    """
    Detect door arcs from thin_mask by finding arc-shaped contours near wall gaps.
    Also records door leaf line endpoints (hinge to arc end).
    """
    doors = []

    # 1. Find wall gaps (collinear walls with 18-45px opening)
    gaps = []
    for i, w1 in enumerate(walls):
        for j, w2 in enumerate(walls):
            if i >= j or w1['direction'] != w2['direction']:
                continue
            d = w1['direction']
            if d == 'H':
                if abs(w1['y1'] - w2['y1']) > 5:
                    continue
                g1 = w2['x1'] - w1['x2']
                g2 = w1['x1'] - w2['x2']
                if 18 <= g1 <= 45:
                    gaps.append({
                        'dir': 'H', 'hinge': (w1['x2'], w1['y1']),
                        'opposite': (w2['x1'], w2['y1']),
                    })
                elif 18 <= g2 <= 45:
                    gaps.append({
                        'dir': 'H', 'hinge': (w2['x2'], w2['y1']),
                        'opposite': (w1['x1'], w1['y1']),
                    })
            else:  # V
                if abs(w1['x1'] - w2['x1']) > 5:
                    continue
                g1 = w2['y1'] - w1['y2']
                g2 = w1['y1'] - w2['y2']
                if 18 <= g1 <= 45:
                    gaps.append({
                        'dir': 'V', 'hinge': (w1['x1'], w1['y2']),
                        'opposite': (w2['x1'], w2['y1']),
                    })
                elif 18 <= g2 <= 45:
                    gaps.append({
                        'dir': 'V', 'hinge': (w2['x1'], w2['y2']),
                        'opposite': (w1['x1'], w1['y1']),
                    })

    # 2. For each gap, search thin_mask ROI for arc contours
    img_h, img_w = thin_mask.shape
    for gap in gaps:
        hx, hy = gap['hinge']
        ox, oy = gap['opposite']
        gap_width = math.hypot(ox - hx, oy - hy)
        radius_est = gap_width * 0.9

        # ROI around the gap
        pad = int(gap_width * 1.5)
        cx, cy = (hx + ox) / 2, (hy + oy) / 2
        rx1 = max(0, int(cx - pad))
        ry1 = max(0, int(cy - pad))
        rx2 = min(img_w, int(cx + pad))
        ry2 = min(img_h, int(cy + pad))
        roi = thin_mask[ry1:ry2, rx1:rx2]
        if roi.size == 0:
            continue

        contours, _ = cv2.findContours(roi, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        best_arc = None
        best_score = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            peri = cv2.arcLength(cnt, True)
            if peri < 5 or area < 5:
                continue
            circularity = 4 * math.pi * area / (peri * peri)
            if 0.05 <= circularity <= 0.60:
                (cx_c, cy_c), rad = cv2.minEnclosingCircle(cnt)
                if 8 <= rad <= 40 and abs(rad - radius_est) < radius_est * 0.5:
                    score = area * (1.0 - abs(rad - radius_est) / radius_est)
                    if score > best_score:
                        best_score = score
                        best_arc = (cx_c + rx1, cy_c + ry1, rad)

        if best_arc:
            arc_cx, arc_cy, arc_r = best_arc
            # Determine start/end angles from wall direction
            if gap['dir'] == 'H':
                if arc_cy < hy:
                    start_angle, end_angle = 0.0, 90.0
                else:
                    start_angle, end_angle = 270.0, 360.0
            else:
                if arc_cx < hx:
                    start_angle, end_angle = 90.0, 180.0
                else:
                    start_angle, end_angle = 0.0, 90.0

            doors.append({
                'center_x': hx, 'center_y': hy,
                'radius': arc_r,
                'start_angle': start_angle,
                'end_angle': end_angle,
                'type': 'door_swing',
                'leaf_end_x': hx + arc_r * math.cos(math.radians(start_angle)),
                'leaf_end_y': hy - arc_r * math.sin(math.radians(start_angle)),
            })
        else:
            # Fallback: HoughCircles on ROI
            if roi.size > 0:
                roi_blur = cv2.GaussianBlur(roi, (3, 3), 0)
                circles = cv2.HoughCircles(
                    roi_blur, cv2.HOUGH_GRADIENT, dp=1.5,
                    minDist=20, param1=80, param2=20,
                    minRadius=8, maxRadius=40
                )
                if circles is not None and len(circles[0]) > 0:
                    c = circles[0][0]
                    arc_r = float(c[2])
                    dx = float(c[0]) + rx1 - hx
                    dy = float(c[1]) + ry1 - hy
                    base_angle = math.degrees(math.atan2(-dy, dx))
                    doors.append({
                        'center_x': hx, 'center_y': hy,
                        'radius': arc_r,
                        'start_angle': base_angle,
                        'end_angle': base_angle + 90.0,
                        'type': 'door_swing',
                        'leaf_end_x': hx + arc_r * math.cos(math.radians(base_angle)),
                        'leaf_end_y': hy - arc_r * math.sin(math.radians(base_angle)),
                    })

    # 3. Fallback: HoughCircles on full thin_mask for arcs not near detected gaps
    circles = cv2.HoughCircles(
        thin_mask, cv2.HOUGH_GRADIENT, dp=1.5,
        minDist=15, param1=80, param2=15,
        minRadius=8, maxRadius=40
    )
    if circles is not None:
        # Collect wall edge endpoints for proximity check
        all_endpoints = []
        for w in walls:
            for edge in ('e1', 'e2'):
                for end in ('1', '2'):
                    all_endpoints.append((w[f'{edge}_x{end}'], w[f'{edge}_y{end}']))

        for c in circles[0]:
            cx, cy, r = float(c[0]), float(c[1]), float(c[2])
            # Must be near a wall endpoint (hinge point)
            best_dist = float('inf')
            best_pt = None
            for wx, wy in all_endpoints:
                d = math.hypot(cx - wx, cy - wy)
                if d < best_dist:
                    best_dist = d
                    best_pt = (wx, wy)
            max_hinge_dist = max(r * 1.0, 10.0)
            if best_dist > max_hinge_dist:
                continue
            # Determine angles from position relative to hinge
            if best_pt:
                dx = cx - best_pt[0]
                dy = cy - best_pt[1]
                base_angle = math.degrees(math.atan2(-dy, dx))
            else:
                base_angle = 0.0
            doors.append({
                'center_x': cx, 'center_y': cy,
                'radius': r,
                'start_angle': base_angle,
                'end_angle': base_angle + 90.0,
                'type': 'door_swing',
            })

    # Deduplicate
    filtered = []
    for door in doors:
        dup = False
        for kept in filtered:
            if math.hypot(door['center_x'] - kept['center_x'],
                          door['center_y'] - kept['center_y']) < 15:
                dup = True
                break
        if not dup:
            filtered.append(door)

    return filtered


def _detect_windows_from_thin_mask(thin_mask: np.ndarray,
                                    walls: List[Dict]) -> List[Dict]:
    """
    Detect windows from thin_mask using HoughLinesP with low thresholds.
    Windows are groups of 2-3 parallel short lines crossing wall positions.
    """
    hough_lines = cv2.HoughLinesP(
        thin_mask, rho=1, theta=np.pi / 180,
        threshold=10, minLineLength=3, maxLineGap=3
    )
    if hough_lines is None:
        return []

    # Snap to H/V and collect short lines only
    h_lines = []  # (y, xmin, xmax)
    v_lines = []  # (x, ymin, ymax)
    tol_rad = math.radians(8.0)

    for hl in hough_lines:
        x1, y1, x2, y2 = float(hl[0][0]), float(hl[0][1]), float(hl[0][2]), float(hl[0][3])
        length = math.hypot(x2 - x1, y2 - y1)
        if length < 3 or length > 30:
            continue
        dx, dy = x2 - x1, y2 - y1
        angle = math.atan2(abs(dy), abs(dx))
        if angle < tol_rad:
            avg_y = (y1 + y2) / 2.0
            h_lines.append((avg_y, min(x1, x2), max(x1, x2)))
        elif angle > (math.pi / 2 - tol_rad):
            avg_x = (x1 + x2) / 2.0
            v_lines.append((avg_x, min(y1, y2), max(y1, y2)))

    windows = []

    # Group parallel H lines with spacing 1-5px
    h_lines.sort(key=lambda x: (round(x[1] / 5) * 5, x[0]))
    used_h = set()
    for i in range(len(h_lines)):
        if i in used_h:
            continue
        group = [h_lines[i]]
        for j in range(i + 1, len(h_lines)):
            if j in used_h:
                continue
            # Similar X range
            overlap = min(group[-1][2], h_lines[j][2]) - max(group[-1][1], h_lines[j][1])
            shorter = min(group[-1][2] - group[-1][1], h_lines[j][2] - h_lines[j][1])
            if shorter > 0 and overlap / shorter < 0.4:
                continue
            gap = abs(h_lines[j][0] - group[-1][0])
            if 1 <= gap <= 5:
                group.append(h_lines[j])
                used_h.add(j)
                if len(group) >= 3:
                    break

        if len(group) >= 2:
            ys = [g[0] for g in group]
            xs_min = min(g[1] for g in group)
            xs_max = max(g[2] for g in group)
            cy = sum(ys) / len(ys)
            # Validate: must be near a wall
            near_wall = any(
                abs(cy - w['y1']) < w.get('thickness', 10) * 2
                for w in walls if w['direction'] == 'V'
                and w['y1'] <= cy <= w['y2']
            )
            if near_wall or len(group) >= 3:
                used_h.add(i)
                windows.append({
                    'type': 'window', 'direction': 'H',
                    'center_x': (xs_min + xs_max) / 2.0,
                    'center_y': (min(ys) + max(ys)) / 2.0,
                    'width': xs_max - xs_min,
                    'height': max(ys) - min(ys),
                    'x_min': xs_min, 'x_max': xs_max,
                    'y_min': min(ys), 'y_max': max(ys),
                    'line_count': len(group),
                })

    # Group parallel V lines with spacing 1-5px
    v_lines.sort(key=lambda x: (round(x[1] / 5) * 5, x[0]))
    used_v = set()
    for i in range(len(v_lines)):
        if i in used_v:
            continue
        group = [v_lines[i]]
        for j in range(i + 1, len(v_lines)):
            if j in used_v:
                continue
            overlap = min(group[-1][2], v_lines[j][2]) - max(group[-1][1], v_lines[j][1])
            shorter = min(group[-1][2] - group[-1][1], v_lines[j][2] - v_lines[j][1])
            if shorter > 0 and overlap / shorter < 0.4:
                continue
            gap = abs(v_lines[j][0] - group[-1][0])
            if 1 <= gap <= 5:
                group.append(v_lines[j])
                used_v.add(j)
                if len(group) >= 3:
                    break

        if len(group) >= 2:
            xs = [g[0] for g in group]
            ys_min = min(g[1] for g in group)
            ys_max = max(g[2] for g in group)
            cx = sum(xs) / len(xs)
            near_wall = any(
                abs(cx - w['x1']) < w.get('thickness', 10) * 2
                for w in walls if w['direction'] == 'H'
                and w['x1'] <= cx <= w['x2']
            )
            if near_wall or len(group) >= 3:
                used_v.add(i)
                windows.append({
                    'type': 'window', 'direction': 'V',
                    'center_x': (min(xs) + max(xs)) / 2.0,
                    'center_y': (ys_min + ys_max) / 2.0,
                    'width': max(xs) - min(xs),
                    'height': ys_max - ys_min,
                    'x_min': min(xs), 'x_max': max(xs),
                    'y_min': ys_min, 'y_max': ys_max,
                    'line_count': len(group),
                })

    return windows


def _detect_fixtures_from_thin_mask(thin_mask: np.ndarray, thick_mask: np.ndarray,
                                     walls: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Detect bathroom fixtures and kitchen casework from thin_mask contours.
    Classifies by shape metrics (area, aspect ratio, solidity, vertex count).

    Returns:
        (fixtures, casework)
    """
    contours, _ = cv2.findContours(thin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    fixtures = []
    casework = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 20 or area > 5000:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        aspect = max(w, h) / max(1, min(w, h))
        hull = cv2.convexHull(cnt)
        hull_area = cv2.contourArea(hull)
        solidity = area / max(1, hull_area)

        epsilon = 0.02 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        vertices = len(approx)

        item = {
            'x': float(x), 'y': float(y),
            'width': float(w), 'height': float(h),
            'area': float(area),
            'vertices': [(float(p[0][0]), float(p[0][1])) for p in approx],
        }

        if 200 <= area <= 600 and 1.5 <= aspect <= 2.5 and solidity > 0.85:
            item['type'] = 'bathtub'
            fixtures.append(item)
        elif 50 <= area <= 200 and solidity > 0.70:
            item['type'] = 'toilet'
            fixtures.append(item)
        elif 20 <= area <= 80 and solidity > 0.60:
            item['type'] = 'sink'
            fixtures.append(item)
        elif 150 <= area <= 800 and 0.50 <= solidity <= 0.85 and 5 <= vertices <= 8:
            item['type'] = 'kitchen_counter'
            casework.append(item)
        elif 100 <= area <= 500 and aspect > 2.0 and solidity > 0.70:
            item['type'] = 'closet'
            casework.append(item)

    return fixtures, casework


# ============================================================================
# IMAGE-BASED LINE DETECTION
# ============================================================================

def _preprocess_floor_plan(gray: np.ndarray) -> Tuple:
    """
    Choose preprocessing strategy based on image characteristics.

    Returns:
        For bold-wall plans: (binary, thick_mask, thin_mask)
        For fine-line plans: (edges, None, None)
    """
    mean_brightness = np.mean(gray)
    dark_ratio = np.sum(gray < 128) / gray.size

    if mean_brightness > 200 and 0.03 < dark_ratio < 0.20:
        # Bold-wall floor plan — use two-layer decomposition
        binary, thick_mask, thin_mask = _create_thick_thin_masks(gray)
        return binary, thick_mask, thin_mask
    else:
        # Fine-line or complex image: use standard Canny pipeline
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        kernel = np.ones((2, 2), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        return edges, None, None


def _snap_lines_to_hv(lines: List[Dict], angle_tol_deg: float = 5.0) -> List[Dict]:
    """
    Snap near-horizontal and near-vertical lines to exact H/V.
    Lines beyond the tolerance are discarded — floor plans are H/V dominant,
    and diagonal fragments are almost always noise.
    """
    snapped = []
    tol_rad = math.radians(angle_tol_deg)
    for ln in lines:
        x1, y1, x2, y2 = ln["x1"], ln["y1"], ln["x2"], ln["y2"]
        dx, dy = x2 - x1, y2 - y1
        angle = math.atan2(abs(dy), abs(dx))

        if angle < tol_rad:
            # Near-horizontal → average Y
            avg_y = (y1 + y2) / 2.0
            snapped.append({**ln, "y1": avg_y, "y2": avg_y})
        elif angle > (math.pi / 2 - tol_rad):
            # Near-vertical → average X
            avg_x = (x1 + x2) / 2.0
            snapped.append({**ln, "x1": avg_x, "x2": avg_x})
        # else: discard diagonal lines (noise in floor plans)
    return snapped


def _merge_collinear_segments(lines: List[Dict], pos_tol: float = 3.0,
                               gap_tol: float = 20.0) -> List[Dict]:
    """
    Merge collinear H/V segments that are close together or overlapping.

    Uses aggressive gap bridging (20px) so wall fragments across door openings
    and detection gaps become single continuous lines.
    """
    h_lines = {}  # y_bucket -> list of (x_min, x_max)
    v_lines = {}  # x_bucket -> list of (y_min, y_max)
    diag = []

    for ln in lines:
        x1, y1, x2, y2 = ln["x1"], ln["y1"], ln["x2"], ln["y2"]
        if y1 == y2:
            # Horizontal
            bucket = round(y1 / pos_tol) * pos_tol
            h_lines.setdefault(bucket, []).append((min(x1, x2), max(x1, x2)))
        elif x1 == x2:
            # Vertical
            bucket = round(x1 / pos_tol) * pos_tol
            v_lines.setdefault(bucket, []).append((min(y1, y2), max(y1, y2)))
        else:
            diag.append(ln)

    merged = []

    for y_bucket, segs in h_lines.items():
        segs.sort()
        merged_segs = [segs[0]]
        for s_min, s_max in segs[1:]:
            prev_min, prev_max = merged_segs[-1]
            if s_min <= prev_max + gap_tol:
                merged_segs[-1] = (prev_min, max(prev_max, s_max))
            else:
                merged_segs.append((s_min, s_max))
        for s_min, s_max in merged_segs:
            length = s_max - s_min
            merged.append({
                "x1": s_min, "y1": y_bucket, "x2": s_max, "y2": y_bucket,
                "length": length, "width": 0,
            })

    for x_bucket, segs in v_lines.items():
        segs.sort()
        merged_segs = [segs[0]]
        for s_min, s_max in segs[1:]:
            prev_min, prev_max = merged_segs[-1]
            if s_min <= prev_max + gap_tol:
                merged_segs[-1] = (prev_min, max(prev_max, s_max))
            else:
                merged_segs.append((s_min, s_max))
        for s_min, s_max in merged_segs:
            length = s_max - s_min
            merged.append({
                "x1": x_bucket, "y1": s_min, "x2": x_bucket, "y2": s_max,
                "length": length, "width": 0,
            })

    merged.extend(diag)
    return merged


def _deduplicate_lines(lines: List[Dict], tol: float = 5.0) -> List[Dict]:
    """Remove lines where both endpoints are within tol pixels of another kept line."""
    keep = []
    for ln in lines:
        duplicate = False
        for other in keep:
            d1 = math.hypot(ln["x1"] - other["x1"], ln["y1"] - other["y1"])
            d2 = math.hypot(ln["x2"] - other["x2"], ln["y2"] - other["y2"])
            d3 = math.hypot(ln["x1"] - other["x2"], ln["y1"] - other["y2"])
            d4 = math.hypot(ln["x2"] - other["x1"], ln["y2"] - other["y1"])
            if (d1 < tol and d2 < tol) or (d3 < tol and d4 < tol):
                duplicate = True
                break
        if not duplicate:
            keep.append(ln)
    return keep


def _filter_short_lines(lines: List[Dict], min_length: float) -> List[Dict]:
    """Remove lines shorter than min_length pixels."""
    return [ln for ln in lines if ln["length"] >= min_length]


def extract_lines_from_image(image_path: str,
                             min_line_length: int = 50,
                             max_line_gap: int = 5,
                             canny_low: int = 50,
                             canny_high: int = 150,
                             hough_threshold: int = 80,
                             dpi: int = 300) -> Dict:
    """
    Detect lines from an image using OpenCV.

    Uses two-layer decomposition for bold-wall plans (thick walls separated from
    thin features like doors, windows, fixtures).
    Falls back to HoughLinesP for fine-line plans.

    Args:
        image_path: Path to image or PDF
        min_line_length: Minimum line length in pixels
        max_line_gap: Maximum gap between line segments to merge
        canny_low: Canny edge detection low threshold
        canny_high: Canny edge detection high threshold
        hough_threshold: Hough line detection threshold
        dpi: DPI for PDF-to-image conversion

    Returns:
        Dict with detected lines, walls, doors, windows, fixtures, casework
    """
    if cv2 is None:
        raise ImportError("opencv-python is required for image mode. Install: pip install opencv-python")

    ext = os.path.splitext(image_path)[1].lower()

    if ext == ".pdf":
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(image_path, dpi=dpi, first_page=1, last_page=1)
            img = np.array(images[0])
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        except ImportError:
            raise ImportError("pdf2image is required for PDF image mode. Install: pip install pdf2image")
    else:
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Cannot load image: {image_path}")

    img_height, img_width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # --- OCR: extract text ---
    print("  Running OCR text extraction...")
    text_regions = _extract_text_regions(img)
    room_dims = []
    if text_regions:
        print(f"  OCR found {len(text_regions)} text regions")
        room_dims = _parse_room_dimensions(text_regions)
        if room_dims:
            print(f"  Found {len(room_dims)} room dimension labels: "
                  f"{[d['text'] for d in room_dims]}")

    # --- Preprocessing: two-layer decomposition ---
    binary_or_edges, thick_mask, thin_mask = _preprocess_floor_plan(gray)

    if thick_mask is not None:
        # ============================================
        # BOLD-WALL PIPELINE (two-layer decomposition)
        # ============================================
        print("  Using two-layer wall/feature decomposition")

        # Mask text regions in both masks
        if text_regions:
            thick_mask = _mask_text_regions(thick_mask, text_regions, padding=5)
            thin_mask = _mask_text_regions(thin_mask, text_regions, padding=5)

        # Extract walls from thick mask
        wall_lines, wall_endpoints = _extract_walls_from_thick_mask(thick_mask)
        print(f"  Walls from thick mask: {len(wall_lines)}")

        # Clean wall corners
        wall_lines = _clean_wall_corners(wall_lines)
        print(f"  Walls after corner cleanup: {len(wall_lines)}")

        # Detect doors: thin mask first, then supplement with HoughCircles on gray
        doors = _detect_doors_from_thin_mask(thin_mask, thick_mask, wall_lines)
        # Supplement with HoughCircles on original gray image (catches arcs
        # that span both thick and thin masks)
        gray_doors = _detect_door_arcs(gray, wall_lines)
        # Merge, deduplicating by proximity
        for gd in gray_doors:
            dup = False
            for existing in doors:
                if math.hypot(gd['center_x'] - existing['center_x'],
                              gd['center_y'] - existing['center_y']) < 15:
                    dup = True
                    break
            if not dup:
                doors.append(gd)
        print(f"  Doors detected: {len(doors)}")

        # Detect windows from thin mask
        windows = _detect_windows_from_thin_mask(thin_mask, wall_lines)
        print(f"  Windows detected: {len(windows)}")

        # Detect fixtures and casework from thin mask
        fixtures, casework = _detect_fixtures_from_thin_mask(thin_mask, thick_mask, wall_lines)
        print(f"  Fixtures detected: {len(fixtures)}, Casework: {len(casework)}")

        # Remaining thin lines → floor_lines via HoughLinesP on thin_mask
        size_ratio = max(img_width, img_height) / 2000.0
        thin_min_len = max(8, int(min_line_length * size_ratio * 0.5))
        thin_thresh = max(15, int(hough_threshold * size_ratio * 0.5))
        hough_lines = cv2.HoughLinesP(
            thin_mask, rho=1, theta=np.pi / 180,
            threshold=thin_thresh, minLineLength=thin_min_len, maxLineGap=5
        )
        floor_lines = []
        if hough_lines is not None:
            for hl in hough_lines:
                x1, y1, x2, y2 = hl[0]
                length = math.hypot(x2 - x1, y2 - y1)
                floor_lines.append({
                    "x1": float(x1), "y1": float(y1),
                    "x2": float(x2), "y2": float(y2),
                    "length": length, "width": 0,
                })
        floor_lines = _snap_lines_to_hv(floor_lines)
        floor_lines = _merge_collinear_segments(floor_lines)
        floor_lines = _deduplicate_lines(floor_lines)
        print(f"  Floor lines from thin mask: {len(floor_lines)}")

    else:
        # ============================================
        # FINE-LINE PIPELINE (original HoughLinesP)
        # ============================================
        print("  Using fine-line (Canny + HoughLinesP) pipeline")
        edges = binary_or_edges

        # Mask text regions
        if text_regions:
            edges = _mask_text_regions(edges, text_regions)

        # Adapt thresholds to image resolution
        size_ratio = max(img_width, img_height) / 2000.0
        adj_min_len = max(10, int(min_line_length * size_ratio))
        adj_thresh = max(25, int(hough_threshold * size_ratio))
        adj_gap = max(5, int(max_line_gap * max(1.0, size_ratio)))
        if max(img_width, img_height) < 1000:
            adj_gap = max(adj_gap, 10)
        print(f"  Image: {img_width}x{img_height}px → adaptive params: "
              f"minLen={adj_min_len}, thresh={adj_thresh}, gap={adj_gap}")

        hough_lines = cv2.HoughLinesP(
            edges, rho=1, theta=np.pi / 180,
            threshold=adj_thresh, minLineLength=adj_min_len, maxLineGap=adj_gap
        )
        lines = []
        if hough_lines is not None:
            for hl in hough_lines:
                x1, y1, x2, y2 = hl[0]
                length = math.hypot(x2 - x1, y2 - y1)
                lines.append({
                    "x1": float(x1), "y1": float(y1),
                    "x2": float(x2), "y2": float(y2),
                    "length": length, "width": 0,
                })

        raw_count = len(lines)
        lines = _snap_lines_to_hv(lines)
        lines = _merge_collinear_segments(lines)
        lines = _deduplicate_lines(lines)
        lines = _filter_short_lines(lines, adj_min_len)
        print(f"  Line cleanup: {raw_count} raw → {len(lines)} after snap/merge/dedupe/filter")

        wall_lines, floor_lines = _classify_wall_vs_floor_lines(lines)
        print(f"  Wall classification: {len(wall_lines)} wall pairs, "
              f"{len(floor_lines)} floor/other lines")

        windows, floor_lines = _detect_windows(floor_lines, wall_lines)
        print(f"  Windows detected: {len(windows)}")

        doors = _detect_door_arcs(gray, wall_lines)
        print(f"  Door arcs detected: {len(doors)}")

        fixtures = []
        casework = []

    # Compute line extent (building footprint)
    all_lines = wall_lines + floor_lines
    if all_lines:
        all_lx = [ln["x1"] for ln in all_lines] + [ln["x2"] for ln in all_lines]
        all_ly = [ln["y1"] for ln in all_lines] + [ln["y2"] for ln in all_lines]
        line_min_x, line_max_x = min(all_lx), max(all_lx)
        line_min_y, line_max_y = min(all_ly), max(all_ly)
        line_extent_w = line_max_x - line_min_x
        line_extent_h = line_max_y - line_min_y
    else:
        line_min_x = line_min_y = 0
        line_max_x, line_max_y = float(img_width), float(img_height)
        line_extent_w, line_extent_h = float(img_width), float(img_height)

    bounds = {
        "min_x": line_min_x, "max_x": line_max_x,
        "min_y": line_min_y, "max_y": line_max_y,
        "width": line_extent_w, "height": line_extent_h,
    }

    print(f"  Line extent: {line_extent_w:.0f}x{line_extent_h:.0f}px "
          f"(image: {img_width}x{img_height}px, "
          f"footprint covers {line_extent_w/img_width*100:.0f}% of width)")

    return {
        "mode": "image",
        "page_width": float(img_width),
        "page_height": float(img_height),
        "dpi": dpi,
        "lines": wall_lines,
        "floor_lines": floor_lines,
        "doors": doors,
        "windows": windows,
        "fixtures": fixtures,
        "casework": casework,
        "text_regions": text_regions,
        "room_dimensions": room_dims,
        "rectangles": [],
        "curves": [],
        "bounds": bounds,
        "total_paths": len(wall_lines) + len(floor_lines),
    }


# ============================================================================
# DXF WRITING
# ============================================================================

def write_dxf(geometry: Dict, output_path: str,
              scale_factor: float, scale_name: str,
              flip_y: bool = True,
              min_length_inches: float = 1.0) -> Dict:
    """
    Write extracted geometry to a DXF file in real-world inches.

    Args:
        geometry: Extracted geometry from vector or image extraction
        output_path: Output DXF file path
        scale_factor: Multiplication factor (paper dimension × factor = real inches)
        scale_name: Scale name for metadata
        flip_y: Flip Y axis (PDF Y goes down, DXF Y goes up)
        min_length_inches: Minimum line length in real inches to include

    Returns:
        Summary dict with counts
    """
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Set units to inches
    doc.header["$INSUNITS"] = 1  # inches

    page_height = geometry["page_height"]
    mode = geometry["mode"]

    # Conversion factor: source units to real inches
    if mode == "vector":
        # PDF points to real inches: pts / 72 * scale_factor
        to_inches = scale_factor / 72.0
    else:
        # Image pixels to real inches: pixels / dpi * scale_factor
        dpi = geometry.get("dpi", 300)
        to_inches = scale_factor / dpi

    def convert_point(x, y):
        """Convert source coordinates to DXF real-world inches."""
        real_x = x * to_inches
        if flip_y:
            real_y = (page_height - y) * to_inches
        else:
            real_y = y * to_inches
        return (round(real_x, 4), round(real_y, 4))

    line_count = 0
    rect_count = 0
    curve_count = 0
    skipped = 0

    # Create layers
    doc.layers.new("WALLS", dxfattribs={"color": 7})  # white — wall edges + fill
    doc.layers.new("WALLS-RECT", dxfattribs={"color": 3})  # green — vector rectangles
    doc.layers.new("FLOOR-LINES", dxfattribs={"color": 8})  # gray — single/floor lines
    doc.layers.new("CURVES", dxfattribs={"color": 1})  # red
    doc.layers.new("TEXT", dxfattribs={"color": 2})  # yellow — OCR text
    doc.layers.new("DOORS", dxfattribs={"color": 5})  # blue — door arcs
    doc.layers.new("WINDOWS", dxfattribs={"color": 4})  # cyan — window lines
    doc.layers.new("CASEWORK", dxfattribs={"color": 6})  # magenta — kitchen counter, closets
    doc.layers.new("FIXTURES", dxfattribs={"color": 30})  # orange — bathtub, toilet, sink

    # Write wall pairs as two edge lines + solid hatch fill between them
    for wall in geometry["lines"]:
        # Wall pairs have e1_*/e2_* edge coordinates
        if "e1_x1" in wall:
            real_length = wall["length"] * to_inches
            if real_length < min_length_inches:
                skipped += 1
                continue

            # Draw edge 1
            e1_p1 = convert_point(wall["e1_x1"], wall["e1_y1"])
            e1_p2 = convert_point(wall["e1_x2"], wall["e1_y2"])
            msp.add_line(e1_p1, e1_p2, dxfattribs={"layer": "WALLS"})

            # Draw edge 2
            e2_p1 = convert_point(wall["e2_x1"], wall["e2_y1"])
            e2_p2 = convert_point(wall["e2_x2"], wall["e2_y2"])
            msp.add_line(e2_p1, e2_p2, dxfattribs={"layer": "WALLS"})

            # Solid hatch fill between the two edges (rectangle path)
            hatch = msp.add_hatch(dxfattribs={"layer": "WALLS"})
            hatch.set_solid_fill(color=7)  # white fill (matches WALLS layer color)
            # Path goes: e1_p1 → e1_p2 → e2_p2 → e2_p1 → close
            hatch.paths.add_polyline_path([
                e1_p1, e1_p2, e2_p2, e2_p1
            ], is_closed=True)

            line_count += 1
        else:
            # Legacy single-line wall (from vector mode or old format)
            real_length = wall.get("length", 0) * to_inches
            if real_length < min_length_inches:
                skipped += 1
                continue
            p1 = convert_point(wall["x1"], wall["y1"])
            p2 = convert_point(wall["x2"], wall["y2"])
            msp.add_line(p1, p2, dxfattribs={"layer": "WALLS"})
            line_count += 1

    # Write floor/other lines (unpaired singles)
    floor_count = 0
    for line in geometry.get("floor_lines", []):
        real_length = line["length"] * to_inches
        if real_length < min_length_inches:
            skipped += 1
            continue

        p1 = convert_point(line["x1"], line["y1"])
        p2 = convert_point(line["x2"], line["y2"])

        msp.add_line(p1, p2, dxfattribs={"layer": "FLOOR-LINES"})
        floor_count += 1

    # Write OCR text as DXF TEXT entities
    text_count = 0
    for t in geometry.get("text_regions", []):
        p = convert_point(t["center_x"], t["center_y"])
        # Scale text height: roughly proportional to bbox height
        bbox_h_inches = (t["y_max"] - t["y_min"]) * to_inches
        text_height = max(2.0, bbox_h_inches * 0.8)  # min 2" for readability
        msp.add_text(
            t["text"],
            dxfattribs={
                "layer": "TEXT",
                "height": text_height,
                "insert": p,
            }
        )
        text_count += 1

    # Write door arcs (quarter-circle door swings)
    door_count = 0
    for door in geometry.get("doors", []):
        center_pt = convert_point(door["center_x"], door["center_y"])
        # Convert radius from pixels to inches
        radius_inches = door["radius"] * to_inches
        if radius_inches < 2.0:  # skip tiny arcs
            continue
        start_deg = door.get("start_angle", 0.0)
        end_deg = door.get("end_angle", 90.0)
        # Since we flip Y, mirror angles across X axis
        if flip_y:
            start_deg, end_deg = -end_deg, -start_deg
        msp.add_arc(
            center=(center_pt[0], center_pt[1], 0),
            radius=radius_inches,
            start_angle=start_deg,
            end_angle=end_deg,
            dxfattribs={"layer": "DOORS"}
        )
        # Door leaf line (straight line from hinge to arc end)
        if "leaf_end_x" in door:
            leaf_pt = convert_point(door["leaf_end_x"], door["leaf_end_y"])
            msp.add_line(center_pt, leaf_pt, dxfattribs={"layer": "DOORS"})
        door_count += 1

    # Write windows (groups of parallel lines)
    window_count = 0
    for win in geometry.get("windows", []):
        # Draw window as 3 parallel lines spanning the opening
        cx = win["center_x"]
        cy = win["center_y"]
        w = win["width"]
        h = win["height"]

        if win["direction"] == "H":
            # 3 horizontal lines (window in vertical wall)
            # Top, middle, bottom
            for offset in [-h / 2, 0, h / 2]:
                p1 = convert_point(win["x_min"], cy + offset)
                p2 = convert_point(win["x_max"], cy + offset)
                msp.add_line(p1, p2, dxfattribs={"layer": "WINDOWS"})
        else:
            # 3 vertical lines (window in horizontal wall)
            for offset in [-w / 2, 0, w / 2]:
                p1 = convert_point(cx + offset, win["y_min"])
                p2 = convert_point(cx + offset, win["y_max"])
                msp.add_line(p1, p2, dxfattribs={"layer": "WINDOWS"})
        window_count += 1

    # Write fixtures (bathtub, toilet, sink) as closed polylines
    fixture_count = 0
    for fix in geometry.get("fixtures", []):
        verts = fix.get("vertices", [])
        if len(verts) < 3:
            continue
        dxf_pts = [convert_point(v[0], v[1]) for v in verts]
        pline = msp.add_lwpolyline(dxf_pts, dxfattribs={"layer": "FIXTURES"})
        pline.close()
        fixture_count += 1

    # Write casework (kitchen counter, closets) as closed polylines
    casework_count = 0
    for cw in geometry.get("casework", []):
        verts = cw.get("vertices", [])
        if len(verts) < 3:
            continue
        dxf_pts = [convert_point(v[0], v[1]) for v in verts]
        pline = msp.add_lwpolyline(dxf_pts, dxfattribs={"layer": "CASEWORK"})
        pline.close()
        casework_count += 1

    # Write rectangles as 4 lines
    for rect in geometry["rectangles"]:
        x0, y0 = rect["x0"], rect["y0"]
        x1, y1 = rect["x1"], rect["y1"]

        # Rectangle width/height in real inches
        real_w = abs(x1 - x0) * to_inches
        real_h = abs(y1 - y0) * to_inches

        if max(real_w, real_h) < min_length_inches:
            skipped += 1
            continue

        p_tl = convert_point(x0, y0)
        p_tr = convert_point(x1, y0)
        p_br = convert_point(x1, y1)
        p_bl = convert_point(x0, y1)

        # Thin rectangles (likely wall segments) → write as individual lines
        # Wide rectangles → write as 4-sided polyline
        if min(real_w, real_h) < 2.0:
            # Thin rectangle — likely a filled wall segment
            # Write the two long edges (the useful geometry)
            if real_w > real_h:
                # Horizontal rectangle
                msp.add_line(p_tl, p_tr, dxfattribs={"layer": "WALLS-RECT"})
                msp.add_line(p_bl, p_br, dxfattribs={"layer": "WALLS-RECT"})
            else:
                # Vertical rectangle
                msp.add_line(p_tl, p_bl, dxfattribs={"layer": "WALLS-RECT"})
                msp.add_line(p_tr, p_br, dxfattribs={"layer": "WALLS-RECT"})
            rect_count += 1
        else:
            # Regular rectangle — write all 4 edges
            msp.add_line(p_tl, p_tr, dxfattribs={"layer": "WALLS-RECT"})
            msp.add_line(p_tr, p_br, dxfattribs={"layer": "WALLS-RECT"})
            msp.add_line(p_br, p_bl, dxfattribs={"layer": "WALLS-RECT"})
            msp.add_line(p_bl, p_tl, dxfattribs={"layer": "WALLS-RECT"})
            rect_count += 1

    # Write curves as approximated polylines
    for curve in geometry["curves"]:
        pts = curve["points"]
        if len(pts) >= 2:
            dxf_pts = [convert_point(p["x"], p["y"]) for p in pts]
            # For cubic bezier with 4 points, approximate with line segments
            if len(dxf_pts) == 4:
                # Simple cubic bezier approximation: sample 8 points
                p0 = np.array(dxf_pts[0])
                p1 = np.array(dxf_pts[1])
                p2 = np.array(dxf_pts[2])
                p3 = np.array(dxf_pts[3])
                sampled = []
                for t_i in range(9):
                    t = t_i / 8.0
                    pt = ((1-t)**3 * p0 + 3*(1-t)**2*t * p1 +
                          3*(1-t)*t**2 * p2 + t**3 * p3)
                    sampled.append(tuple(pt))
                for i in range(len(sampled) - 1):
                    msp.add_line(sampled[i], sampled[i+1],
                                 dxfattribs={"layer": "CURVES"})
                curve_count += 1
            else:
                # Just connect the points
                for i in range(len(dxf_pts) - 1):
                    msp.add_line(dxf_pts[i], dxf_pts[i+1],
                                 dxfattribs={"layer": "CURVES"})
                curve_count += 1

    doc.saveas(output_path)

    # Calculate output bounds from all line types
    all_x = []
    all_y = []
    for line in list(geometry["lines"]) + list(geometry.get("floor_lines", [])):
        p1 = convert_point(line["x1"], line["y1"])
        p2 = convert_point(line["x2"], line["y2"])
        all_x.extend([p1[0], p2[0]])
        all_y.extend([p1[1], p2[1]])

    output_bounds = {}
    if all_x:
        output_bounds = {
            "min_x": min(all_x), "max_x": max(all_x),
            "min_y": min(all_y), "max_y": max(all_y),
            "width_inches": max(all_x) - min(all_x),
            "height_inches": max(all_y) - min(all_y),
            "width_feet": (max(all_x) - min(all_x)) / 12.0,
            "height_feet": (max(all_y) - min(all_y)) / 12.0,
        }

    total = (line_count + floor_count + rect_count + curve_count +
             text_count + door_count + window_count + fixture_count + casework_count)
    return {
        "output_path": output_path,
        "scale": scale_name,
        "scale_factor": scale_factor,
        "walls_written": line_count,
        "floor_lines_written": floor_count,
        "doors_written": door_count,
        "windows_written": window_count,
        "fixtures_written": fixture_count,
        "casework_written": casework_count,
        "rectangles_written": rect_count,
        "curves_written": curve_count,
        "texts_written": text_count,
        "total_entities": total,
        "skipped_short": skipped,
        "output_bounds": output_bounds,
    }


# ============================================================================
# MAIN CONVERTER
# ============================================================================

def convert(input_path: str, output_path: str,
            mode: Optional[str] = None,
            scale: Optional[str] = None,
            page: int = 1,
            building_width_ft: float = 55.0,
            min_length_inches: float = 1.0,
            dpi: int = 300,
            min_line_pixels: int = 50,
            hough_threshold: int = 80) -> Dict:
    """
    Convert PDF or image to DXF.

    Args:
        input_path: Path to PDF or image file
        output_path: Path for output DXF file
        mode: "vector" or "image" (auto-detect if None)
        scale: Scale string (e.g., "1/8") or None for auto-detect
        page: Page number (1-indexed, for PDFs)
        building_width_ft: Expected building width for auto-scale
        min_length_inches: Minimum line length in real inches
        dpi: DPI for image conversion
        min_line_pixels: Minimum line length for image mode
        hough_threshold: Hough threshold for image mode

    Returns:
        Summary dict
    """
    ext = os.path.splitext(input_path)[1].lower()
    is_pdf = ext == ".pdf"
    is_image = ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp")

    if not is_pdf and not is_image:
        raise ValueError(f"Unsupported file type: {ext}. Use .pdf, .png, .jpg, .tiff, or .bmp")

    # Auto-detect mode
    if mode is None:
        if is_image:
            mode = "image"
        elif is_pdf:
            # Check if PDF has vector content
            if fitz is not None:
                doc = fitz.open(input_path)
                page_obj = doc[page - 1]
                drawings = page_obj.get_drawings()
                images = page_obj.get_images()
                doc.close()

                if len(drawings) > 50:
                    mode = "vector"
                    print(f"[AUTO] PDF has {len(drawings)} vector paths → using vector mode")
                elif len(images) > 0:
                    mode = "image"
                    print(f"[AUTO] PDF has {len(images)} images, {len(drawings)} paths → using image mode")
                else:
                    mode = "vector"
                    print(f"[AUTO] PDF has {len(drawings)} paths → using vector mode")
            else:
                mode = "image"
                print("[AUTO] pymupdf not available → using image mode")

    print(f"\n{'=' * 60}")
    print(f"PDF/Image to DXF Converter")
    print(f"{'=' * 60}")
    print(f"  Input:  {input_path}")
    print(f"  Output: {output_path}")
    print(f"  Mode:   {mode}")

    # Extract geometry
    if mode == "vector":
        geometry = extract_vectors_from_pdf(input_path, page_num=page - 1)
        print(f"  Extracted: {len(geometry['lines'])} lines, "
              f"{len(geometry['rectangles'])} rects, {len(geometry['curves'])} curves")
    else:
        geometry = extract_lines_from_image(
            input_path,
            min_line_length=min_line_pixels,
            hough_threshold=hough_threshold,
            dpi=dpi
        )
        print(f"  Detected: {len(geometry['lines'])} walls, "
              f"{len(geometry.get('floor_lines', []))} floor lines, "
              f"{len(geometry.get('doors', []))} doors, "
              f"{len(geometry.get('windows', []))} windows, "
              f"{len(geometry.get('fixtures', []))} fixtures, "
              f"{len(geometry.get('casework', []))} casework")

    # Determine scale
    if scale is not None:
        scale_factor = parse_scale(scale)
        scale_name = scale
        print(f"  Scale:  {scale} (factor: {scale_factor})")
    elif mode == "image":
        img_width_px = geometry["bounds"]["width"]
        img_dpi = geometry.get("dpi", 300)

        # Try OCR-based scale calibration first (most accurate)
        room_dims = geometry.get("room_dimensions", [])
        if room_dims:
            # Use the largest room dimension to calibrate scale
            # The room label position tells us roughly where the room is,
            # and the dimension text tells us the real size
            best = max(room_dims, key=lambda d: d["width_inches"] * d["height_inches"])
            # Use the room's larger dimension (likely width of building)
            room_real_in = max(best["width_inches"], best["height_inches"])
            # Estimate: this room's real dimension / building's pixel extent
            # gives us a rough inches-per-pixel, which we refine
            scale_factor = (room_real_in * img_dpi) / (img_width_px * 0.35)
            # 0.35 = rough estimate that largest room is ~35% of building width
            # Refine: use building_width_ft as sanity check
            alt_factor = (building_width_ft * 12.0 * img_dpi) / img_width_px
            # Blend: prefer OCR if in reasonable range (within 2x of building-width estimate)
            if 0.5 * alt_factor < scale_factor < 2.0 * alt_factor:
                scale_name = f"ocr:{best['text']}"
                print(f"  Scale:  calibrated from OCR room label \"{best['text']}\" "
                      f"(factor: {scale_factor:.2f})")
            else:
                scale_factor = alt_factor
                scale_name = f"auto:{building_width_ft:.0f}ft"
                print(f"  Scale:  {scale_name} (OCR scale out of range, using building-width, "
                      f"factor: {scale_factor:.2f})")
        else:
            scale_factor = (building_width_ft * 12.0 * img_dpi) / img_width_px
            scale_name = f"auto:{building_width_ft:.0f}ft"
            print(f"  Scale:  {scale_name} (factor: {scale_factor:.2f}, "
                  f"{img_width_px:.0f}px @ {img_dpi}dpi → {building_width_ft:.0f}ft)")
    else:
        # Auto-detect from architectural scales (vector mode)
        bounds = geometry["bounds"]
        scale_name = auto_detect_scale(
            bounds["width"], bounds["height"],
            expected_width_ft=building_width_ft
        )
        scale_factor = ARCH_SCALES[scale_name]["factor"]
        label = ARCH_SCALES[scale_name]["label"]
        print(f"  Scale:  {label} (auto-detected, factor: {scale_factor})")

    # Show what the output dimensions will be
    bounds = geometry["bounds"]
    if mode == "vector":
        to_inches = scale_factor / 72.0
    else:
        to_inches = scale_factor / geometry.get("dpi", 300)

    out_width = bounds["width"] * to_inches
    out_height = bounds["height"] * to_inches
    print(f"  Output size: {out_width / 12:.1f}ft x {out_height / 12:.1f}ft "
          f"({out_width:.0f}\" x {out_height:.0f}\")")

    # Write DXF
    result = write_dxf(
        geometry, output_path,
        scale_factor=scale_factor,
        scale_name=scale_name,
        min_length_inches=min_length_inches
    )

    print(f"\n  Walls written:      {result.get('walls_written', 0)}")
    print(f"  Floor lines:        {result.get('floor_lines_written', 0)}")
    print(f"  Doors written:      {result.get('doors_written', 0)}")
    print(f"  Windows written:    {result.get('windows_written', 0)}")
    print(f"  Fixtures written:   {result.get('fixtures_written', 0)}")
    print(f"  Casework written:   {result.get('casework_written', 0)}")
    print(f"  Rectangles written: {result['rectangles_written']}")
    print(f"  Curves written:     {result['curves_written']}")
    print(f"  Texts written:      {result.get('texts_written', 0)}")
    print(f"  Total entities:     {result['total_entities']}")
    print(f"  Skipped (too short):{result['skipped_short']}")

    ob = result.get("output_bounds", {})
    if ob:
        print(f"\n  DXF bounds: {ob.get('width_feet', 0):.1f}ft x {ob.get('height_feet', 0):.1f}ft")

    print(f"\n  Saved: {output_path}")
    print(f"{'=' * 60}")

    return result


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF floor plans or images to DXF files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scale options:
  "1/8"     →  1/8" = 1'-0"  (common for floor plans)
  "1/4"     →  1/4" = 1'-0"  (common for details)
  "3/16"    →  3/16" = 1'-0"
  "1/2"     →  1/2" = 1'-0"
  "96"      →  direct factor (96x = 1/8" scale)
  (omit)    →  auto-detect from drawing size

Examples:
  # Auto-detect everything
  python pdf_to_dxf.py floorplan.pdf -o floorplan.dxf

  # Specify scale
  python pdf_to_dxf.py floorplan.pdf --scale "1/8" -o floorplan.dxf

  # Image input
  python pdf_to_dxf.py floorplan.png --mode image --scale "1/4" -o floorplan.dxf

  # Scanned PDF (force image mode)
  python pdf_to_dxf.py scanned.pdf --mode image --dpi 300 -o output.dxf

  # Custom building size for auto-scale
  python pdf_to_dxf.py plan.pdf --building-width 80 -o plan.dxf
        """
    )

    parser.add_argument("input", help="Input PDF or image file")
    parser.add_argument("-o", "--output", help="Output DXF file (default: input name + .dxf)")
    parser.add_argument("--mode", choices=["vector", "image"],
                        help="Extraction mode (default: auto-detect)")
    parser.add_argument("--scale",
                        help='Drawing scale (e.g., "1/8" for 1/8"=1\'-0")')
    parser.add_argument("--page", type=int, default=1,
                        help="PDF page number, 1-indexed (default: 1)")
    parser.add_argument("--building-width", type=float, default=55.0,
                        help="Expected building width in feet for auto-scale (default: 55)")
    parser.add_argument("--min-length", type=float, default=1.0,
                        help="Minimum line length in real inches (default: 1.0)")
    parser.add_argument("--dpi", type=int, default=300,
                        help="DPI for PDF-to-image conversion (default: 300)")
    parser.add_argument("--min-line-pixels", type=int, default=50,
                        help="Minimum line length in pixels for image mode (default: 50)")
    parser.add_argument("--hough-threshold", type=int, default=80,
                        help="Hough transform threshold for image mode (default: 80)")
    parser.add_argument("--json", metavar="FILE",
                        help="Save extraction results to JSON")

    args = parser.parse_args()

    # Default output path
    if args.output is None:
        base = os.path.splitext(args.input)[0]
        args.output = base + ".dxf"

    result = convert(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode,
        scale=args.scale,
        page=args.page,
        building_width_ft=args.building_width,
        min_length_inches=args.min_length,
        dpi=args.dpi,
        min_line_pixels=args.min_line_pixels,
        hough_threshold=args.hough_threshold,
    )

    if args.json:
        with open(args.json, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nResults saved to: {args.json}")

    if result["total_entities"] == 0:
        print("\nWARNING: No entities written. Try adjusting --scale or --min-length.")
        sys.exit(1)


if __name__ == "__main__":
    main()
