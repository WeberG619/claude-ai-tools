#!/usr/bin/env python3
"""
Floor Plan Vision MCP Server

Exposes FloorPlanTracer functionality via MCP protocol for Claude Code integration.
This is the missing piece that connects pdf-to-revit pipelines to actual extraction logic.

Tools:
- analyze_floor_plan: Full extraction from image
- detect_scale: Detect drawing scale
- detect_walls: Extract wall segments
- detect_openings: Find doors/windows
- detect_rooms: Find enclosed spaces
- get_pdf_info: Get PDF metadata
"""

import asyncio
import sys
import os
import json
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

# Add FloorPlanTracer to path
FLOORPLAN_TRACER_PATH = Path("/mnt/d/FloorPlanTracer")
sys.path.insert(0, str(FLOORPLAN_TRACER_PATH))

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    from mcp.server.stdio import stdio_server
except ImportError:
    print("MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# LAZY IMPORTS - Import heavy libraries only when needed
# =============================================================================
_tracer = None
_cv2 = None
_fitz = None  # PyMuPDF for PDF handling
_annotator = None  # Annotation module for reference-based tools
_showui = None  # ShowUI semantic grounder

# Session storage for annotated floor plans
_active_sessions: dict = {}
_hybrid_grounders: dict = {}  # Session -> HybridGrounder mapping


def get_cv2():
    """Lazy load OpenCV."""
    global _cv2
    if _cv2 is None:
        import cv2
        _cv2 = cv2
    return _cv2


def get_fitz():
    """Lazy load PyMuPDF."""
    global _fitz
    if _fitz is None:
        try:
            import fitz
            _fitz = fitz
        except ImportError:
            return None
    return _fitz


def get_tracer():
    """Lazy load FloorPlanTracer."""
    global _tracer
    if _tracer is None:
        try:
            from src.pipeline import FloorPlanTracer
            from src.models.data_types import ProcessingConfig
            _tracer = {
                'FloorPlanTracer': FloorPlanTracer,
                'ProcessingConfig': ProcessingConfig
            }
        except ImportError as e:
            logger.error(f"Failed to import FloorPlanTracer: {e}")
            return None
    return _tracer


def get_annotator():
    """Lazy load annotation module."""
    global _annotator
    if _annotator is None:
        try:
            from src.annotation import AnnotatedFloorPlan, ReferenceTools
            _annotator = {
                'AnnotatedFloorPlan': AnnotatedFloorPlan,
                'ReferenceTools': ReferenceTools
            }
        except ImportError as e:
            logger.error(f"Failed to import annotation module: {e}")
            return None
    return _annotator


def get_showui():
    """Lazy load ShowUI semantic grounder."""
    global _showui
    if _showui is None:
        try:
            from src.annotation import ShowUIGrounder, HybridGrounder
            _showui = {
                'ShowUIGrounder': ShowUIGrounder,
                'HybridGrounder': HybridGrounder
            }
        except ImportError as e:
            logger.error(f"Failed to import ShowUI grounder: {e}")
            return None
    return _showui


# =============================================================================
# UTILITIES
# =============================================================================

def convert_path(path: str) -> str:
    """Convert Windows/WSL paths to usable format."""
    if path.startswith("D:") or path.startswith("d:"):
        return path.replace("D:", "/mnt/d").replace("d:", "/mnt/d").replace("\\", "/")
    return path


def pdf_to_image(pdf_path: str, page_num: int = 0, dpi: int = 300) -> str:
    """Convert PDF page to image, return temp image path."""
    fitz = get_fitz()
    if fitz is None:
        raise ImportError("PyMuPDF not installed. Run: pip install pymupdf")

    doc = fitz.open(pdf_path)
    if page_num >= len(doc):
        page_num = 0

    page = doc[page_num]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)

    # Save to temp file
    temp_dir = Path(tempfile.gettempdir()) / "floor-plan-vision"
    temp_dir.mkdir(exist_ok=True)

    base_name = Path(pdf_path).stem
    temp_path = temp_dir / f"{base_name}_page{page_num}.png"
    pix.save(str(temp_path))

    doc.close()
    return str(temp_path)


def serialize_floor_plan(floor_plan) -> Dict[str, Any]:
    """Serialize FloorPlan object to JSON-compatible dict."""
    return floor_plan.to_dict()


def format_walls_for_revit(walls: list, scale: float, level_id: int = None) -> List[Dict]:
    """Format wall segments for Revit MCP consumption."""
    revit_walls = []
    for wall in walls:
        wall_dict = wall.to_dict() if hasattr(wall, 'to_dict') else wall

        # Convert pixel coordinates to feet
        start = wall_dict.get('start', [0, 0])
        end = wall_dict.get('end', [0, 0])

        revit_wall = {
            'id': wall_dict.get('id', ''),
            'startPoint': [start[0] * scale, start[1] * scale, 0],
            'endPoint': [end[0] * scale, end[1] * scale, 0],
            'thickness': wall_dict.get('thickness', 6) * scale,
            'wallType': wall_dict.get('wall_type', 'unknown'),
            'confidence': wall_dict.get('confidence', 1.0)
        }

        if level_id:
            revit_wall['levelId'] = level_id

        revit_walls.append(revit_wall)

    return revit_walls


# =============================================================================
# MCP SERVER
# =============================================================================

server = Server("floor-plan-vision")


@server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="analyze_floor_plan",
            description="Full analysis of a floor plan image or PDF. Extracts walls, junctions, scale, and optionally rooms/openings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to floor plan image (PNG, JPG) or PDF"
                    },
                    "page_num": {
                        "type": "integer",
                        "description": "PDF page number (0-indexed)",
                        "default": 0
                    },
                    "known_width_ft": {
                        "type": "number",
                        "description": "Known real-world width in feet (for scale calculation)"
                    },
                    "scale_ft_per_px": {
                        "type": "number",
                        "description": "Known scale in feet per pixel (if already calculated)"
                    },
                    "detect_rooms": {
                        "type": "boolean",
                        "description": "Whether to detect rooms",
                        "default": False
                    },
                    "detect_openings": {
                        "type": "boolean",
                        "description": "Whether to detect doors/windows",
                        "default": False
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="detect_scale",
            description="Detect the drawing scale from a floor plan image. Returns feet per pixel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to floor plan image or PDF"
                    },
                    "page_num": {
                        "type": "integer",
                        "description": "PDF page number (0-indexed)",
                        "default": 0
                    },
                    "hint_width_ft": {
                        "type": "number",
                        "description": "Approximate expected width in feet (helps calibration)"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="detect_walls",
            description="Extract wall segments from a floor plan. Returns coordinates ready for Revit.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to floor plan image or PDF"
                    },
                    "page_num": {
                        "type": "integer",
                        "description": "PDF page number (0-indexed)",
                        "default": 0
                    },
                    "scale_ft_per_px": {
                        "type": "number",
                        "description": "Scale in feet per pixel"
                    },
                    "known_width_ft": {
                        "type": "number",
                        "description": "Known real-world width in feet"
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["pixels", "feet", "revit"],
                        "description": "Output coordinate format",
                        "default": "feet"
                    },
                    "level_id": {
                        "type": "integer",
                        "description": "Revit level ID (for revit format)"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="detect_openings",
            description="Detect doors and windows in a floor plan.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to floor plan image or PDF"
                    },
                    "page_num": {
                        "type": "integer",
                        "description": "PDF page number",
                        "default": 0
                    },
                    "scale_ft_per_px": {
                        "type": "number",
                        "description": "Scale in feet per pixel"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="detect_rooms",
            description="Detect enclosed rooms/spaces in a floor plan.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to floor plan image or PDF"
                    },
                    "page_num": {
                        "type": "integer",
                        "description": "PDF page number",
                        "default": 0
                    },
                    "scale_ft_per_px": {
                        "type": "number",
                        "description": "Scale in feet per pixel"
                    },
                    "classify": {
                        "type": "boolean",
                        "description": "Whether to classify room types",
                        "default": True
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="get_pdf_info",
            description="Get metadata about a PDF file (pages, size, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to PDF file"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="export_to_revit_json",
            description="Export floor plan analysis to Revit-ready JSON commands",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to floor plan image or PDF"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to save Revit commands JSON"
                    },
                    "scale_ft_per_px": {
                        "type": "number",
                        "description": "Scale in feet per pixel"
                    },
                    "known_width_ft": {
                        "type": "number",
                        "description": "Known width in feet"
                    },
                    "level_id": {
                        "type": "integer",
                        "description": "Revit level element ID"
                    },
                    "wall_height": {
                        "type": "number",
                        "description": "Wall height in feet",
                        "default": 10.0
                    }
                },
                "required": ["file_path", "output_path"]
            }
        ),
        # =====================================================================
        # ANNOTATION TOOLS - Reference-based coordinate translation
        # =====================================================================
        Tool(
            name="annotate_floor_plan",
            description="Create annotated floor plan with labeled elements (C1, L1, T1). Returns session_id for subsequent operations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to floor plan image or PDF"
                    },
                    "page_num": {
                        "type": "integer",
                        "description": "PDF page number (0-indexed)",
                        "default": 0
                    },
                    "extract_text": {
                        "type": "boolean",
                        "description": "Run OCR to extract dimension text",
                        "default": True
                    },
                    "save_annotated_image": {
                        "type": "string",
                        "description": "Path to save annotated image with labels"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="get_coordinate",
            description="Get coordinate of a labeled element (C1, L5, T3, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID from annotate_floor_plan"
                    },
                    "label": {
                        "type": "string",
                        "description": "Element label (e.g., C1, L5, T3)"
                    }
                },
                "required": ["session_id", "label"]
            }
        ),
        Tool(
            name="get_line",
            description="Get start/end points and length of a line segment",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID from annotate_floor_plan"
                    },
                    "label": {
                        "type": "string",
                        "description": "Line label (e.g., L5)"
                    }
                },
                "required": ["session_id", "label"]
            }
        ),
        Tool(
            name="get_text",
            description="Get content and parsed dimension from text element",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID from annotate_floor_plan"
                    },
                    "label": {
                        "type": "string",
                        "description": "Text label (e.g., T1)"
                    }
                },
                "required": ["session_id", "label"]
            }
        ),
        Tool(
            name="set_scale",
            description="Set scale using a dimension text and the line it measures. Critical for coordinate translation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID from annotate_floor_plan"
                    },
                    "text_label": {
                        "type": "string",
                        "description": "Label of dimension text (e.g., T1 showing '25'-0\"')"
                    },
                    "line_label": {
                        "type": "string",
                        "description": "Label of line being measured (e.g., L5)"
                    }
                },
                "required": ["session_id", "text_label", "line_label"]
            }
        ),
        Tool(
            name="verify_scale",
            description="Verify the current scale using another dimension-line pair",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID from annotate_floor_plan"
                    },
                    "text_label": {
                        "type": "string",
                        "description": "Label of dimension text for verification"
                    },
                    "line_label": {
                        "type": "string",
                        "description": "Label of line to verify against"
                    }
                },
                "required": ["session_id", "text_label", "line_label"]
            }
        ),
        Tool(
            name="verify_length",
            description="Verify that a line matches an expected length in feet",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID from annotate_floor_plan"
                    },
                    "line_label": {
                        "type": "string",
                        "description": "Label of line to verify"
                    },
                    "expected_ft": {
                        "type": "number",
                        "description": "Expected length in feet"
                    }
                },
                "required": ["session_id", "line_label", "expected_ft"]
            }
        ),
        Tool(
            name="add_wall",
            description="Add a wall between two labeled corners",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID from annotate_floor_plan"
                    },
                    "start_corner": {
                        "type": "string",
                        "description": "Label of start corner (e.g., C1)"
                    },
                    "end_corner": {
                        "type": "string",
                        "description": "Label of end corner (e.g., C5)"
                    },
                    "wall_type": {
                        "type": "string",
                        "enum": ["exterior", "interior", "partition"],
                        "description": "Type of wall",
                        "default": "interior"
                    }
                },
                "required": ["session_id", "start_corner", "end_corner"]
            }
        ),
        Tool(
            name="get_model",
            description="Get all placed walls ready for Revit export",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID from annotate_floor_plan"
                    }
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="list_elements",
            description="List all labeled elements in the annotated floor plan",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID from annotate_floor_plan"
                    },
                    "element_type": {
                        "type": "string",
                        "enum": ["C", "L", "T", "R", "O"],
                        "description": "Filter by type: C=corners, L=lines, T=text, R=rooms, O=openings"
                    }
                },
                "required": ["session_id"]
            }
        ),
        # =====================================================================
        # SHOWUI SEMANTIC GROUNDING TOOLS - Find elements by description
        # =====================================================================
        Tool(
            name="find_element_semantic",
            description="Find a floor plan element by natural language description using ShowUI vision model. Returns pixel coordinates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language description of what to find (e.g., 'upper left corner of master bedroom', 'main entrance door')"
                    },
                    "image_path": {
                        "type": "string",
                        "description": "Path to floor plan image"
                    },
                    "iterations": {
                        "type": "integer",
                        "description": "Refinement iterations (1-3, higher = more accurate)",
                        "default": 1
                    }
                },
                "required": ["query", "image_path"]
            }
        ),
        Tool(
            name="find_corner_semantic",
            description="Find a specific corner of a room by description",
            inputSchema={
                "type": "object",
                "properties": {
                    "room_description": {
                        "type": "string",
                        "description": "Name/description of the room (e.g., 'master bedroom', 'kitchen')"
                    },
                    "corner_position": {
                        "type": "string",
                        "enum": ["upper left", "upper right", "lower left", "lower right"],
                        "description": "Which corner to find"
                    },
                    "image_path": {
                        "type": "string",
                        "description": "Path to floor plan image"
                    }
                },
                "required": ["room_description", "corner_position", "image_path"]
            }
        ),
        Tool(
            name="find_opening_semantic",
            description="Find a door or window by description",
            inputSchema={
                "type": "object",
                "properties": {
                    "opening_type": {
                        "type": "string",
                        "enum": ["door", "window"],
                        "description": "Type of opening to find"
                    },
                    "location_hint": {
                        "type": "string",
                        "description": "Description of where it is (e.g., 'main entrance', 'between kitchen and dining room')"
                    },
                    "image_path": {
                        "type": "string",
                        "description": "Path to floor plan image"
                    }
                },
                "required": ["opening_type", "location_hint", "image_path"]
            }
        ),
        Tool(
            name="semantic_to_label",
            description="Convert a semantic description to a pre-detected label (C1, L5, etc). Uses ShowUI to find element, then maps to nearest pre-detected label.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID from annotate_floor_plan (must have run annotation first)"
                    },
                    "query": {
                        "type": "string",
                        "description": "Natural language description of element to find"
                    },
                    "label_type": {
                        "type": "string",
                        "enum": ["C", "L", "T", "R", "O"],
                        "description": "Filter to specific type: C=corners, L=lines, T=text"
                    },
                    "max_distance": {
                        "type": "number",
                        "description": "Maximum pixel distance to consider a match",
                        "default": 50.0
                    }
                },
                "required": ["session_id", "query"]
            }
        ),
        Tool(
            name="add_wall_semantic",
            description="Add a wall using semantic descriptions for start and end points (e.g., 'upper left corner of kitchen' to 'upper right corner of kitchen')",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID from annotate_floor_plan"
                    },
                    "start_description": {
                        "type": "string",
                        "description": "Description of start point (e.g., 'upper left corner of master bedroom')"
                    },
                    "end_description": {
                        "type": "string",
                        "description": "Description of end point (e.g., 'upper right corner of master bedroom')"
                    },
                    "wall_type": {
                        "type": "string",
                        "enum": ["exterior", "interior", "partition"],
                        "description": "Type of wall",
                        "default": "interior"
                    }
                },
                "required": ["session_id", "start_description", "end_description"]
            }
        ),
        # =====================================================================
        # TRAJECTORY TOOLS - Generate smooth mouse movement paths
        # =====================================================================
        Tool(
            name="generate_trajectory",
            description="Generate a smooth mouse trajectory between two points. Returns array of coordinates for mouse movement.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Starting point [x, y]"
                    },
                    "end": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Ending point [x, y]"
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Number of points in trajectory",
                        "default": 20
                    },
                    "easing": {
                        "type": "string",
                        "enum": ["linear", "ease_in", "ease_out", "ease_in_out"],
                        "description": "Easing function for natural movement",
                        "default": "ease_in_out"
                    },
                    "trajectory_type": {
                        "type": "string",
                        "enum": ["linear", "drag"],
                        "description": "Type of trajectory (drag adds overshoot)",
                        "default": "linear"
                    }
                },
                "required": ["start", "end"]
            }
        ),
        Tool(
            name="generate_trajectory_curved",
            description="Generate a curved (Bezier) trajectory. Good for natural-looking movements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Starting point [x, y]"
                    },
                    "end": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Ending point [x, y]"
                    },
                    "control": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Control point for curve shape [x, y]. If not provided, auto-calculated."
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Number of points",
                        "default": 25
                    },
                    "easing": {
                        "type": "string",
                        "enum": ["linear", "ease_in", "ease_out", "ease_in_out"],
                        "default": "ease_in_out"
                    }
                },
                "required": ["start", "end"]
            }
        ),
        Tool(
            name="generate_trajectory_semantic",
            description="Generate trajectory using semantic descriptions for endpoints. Combines ShowUI grounding with trajectory generation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_description": {
                        "type": "string",
                        "description": "Natural language description of start point"
                    },
                    "end_description": {
                        "type": "string",
                        "description": "Natural language description of end point"
                    },
                    "image_path": {
                        "type": "string",
                        "description": "Path to image for ShowUI grounding"
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Number of points",
                        "default": 20
                    },
                    "easing": {
                        "type": "string",
                        "enum": ["linear", "ease_in", "ease_out", "ease_in_out"],
                        "default": "ease_in_out"
                    }
                },
                "required": ["start_description", "end_description", "image_path"]
            }
        ),
        Tool(
            name="generate_trajectory_labels",
            description="Generate trajectory between two labeled elements (C1 to C5, etc). Uses session from annotate_floor_plan.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID from annotate_floor_plan"
                    },
                    "start_label": {
                        "type": "string",
                        "description": "Label of start element (e.g., C1)"
                    },
                    "end_label": {
                        "type": "string",
                        "description": "Label of end element (e.g., C5)"
                    },
                    "steps": {
                        "type": "integer",
                        "default": 20
                    },
                    "easing": {
                        "type": "string",
                        "enum": ["linear", "ease_in", "ease_out", "ease_in_out"],
                        "default": "ease_in_out"
                    }
                },
                "required": ["session_id", "start_label", "end_label"]
            }
        ),
        Tool(
            name="execute_trajectory",
            description="Execute a trajectory as actual mouse movement. WARNING: This will move your mouse!",
            inputSchema={
                "type": "object",
                "properties": {
                    "points": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"}
                        },
                        "description": "Array of [x, y] points to move through"
                    },
                    "delay_ms": {
                        "type": "integer",
                        "description": "Delay between points in milliseconds",
                        "default": 10
                    },
                    "click_at_end": {
                        "type": "boolean",
                        "description": "Whether to click at the end position",
                        "default": False
                    },
                    "drag": {
                        "type": "boolean",
                        "description": "Hold mouse button during movement (drag operation)",
                        "default": False
                    }
                },
                "required": ["points"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "analyze_floor_plan":
            return await handle_analyze_floor_plan(arguments)
        elif name == "detect_scale":
            return await handle_detect_scale(arguments)
        elif name == "detect_walls":
            return await handle_detect_walls(arguments)
        elif name == "detect_openings":
            return await handle_detect_openings(arguments)
        elif name == "detect_rooms":
            return await handle_detect_rooms(arguments)
        elif name == "get_pdf_info":
            return await handle_get_pdf_info(arguments)
        elif name == "export_to_revit_json":
            return await handle_export_to_revit(arguments)
        # Annotation tools
        elif name == "annotate_floor_plan":
            return await handle_annotate_floor_plan(arguments)
        elif name == "get_coordinate":
            return await handle_get_coordinate(arguments)
        elif name == "get_line":
            return await handle_get_line(arguments)
        elif name == "get_text":
            return await handle_get_text(arguments)
        elif name == "set_scale":
            return await handle_set_scale(arguments)
        elif name == "verify_scale":
            return await handle_verify_scale(arguments)
        elif name == "verify_length":
            return await handle_verify_length(arguments)
        elif name == "add_wall":
            return await handle_add_wall(arguments)
        elif name == "get_model":
            return await handle_get_model(arguments)
        elif name == "list_elements":
            return await handle_list_elements(arguments)
        # ShowUI semantic grounding tools
        elif name == "find_element_semantic":
            return await handle_find_element_semantic(arguments)
        elif name == "find_corner_semantic":
            return await handle_find_corner_semantic(arguments)
        elif name == "find_opening_semantic":
            return await handle_find_opening_semantic(arguments)
        elif name == "semantic_to_label":
            return await handle_semantic_to_label(arguments)
        elif name == "add_wall_semantic":
            return await handle_add_wall_semantic(arguments)
        # Trajectory tools
        elif name == "generate_trajectory":
            return await handle_generate_trajectory(arguments)
        elif name == "generate_trajectory_curved":
            return await handle_generate_trajectory_curved(arguments)
        elif name == "generate_trajectory_semantic":
            return await handle_generate_trajectory_semantic(arguments)
        elif name == "generate_trajectory_labels":
            return await handle_generate_trajectory_labels(arguments)
        elif name == "execute_trajectory":
            return await handle_execute_trajectory(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        logger.exception(f"Error in {name}")
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e),
            "tool": name
        }))]


# =============================================================================
# TOOL HANDLERS
# =============================================================================

async def handle_analyze_floor_plan(args: dict):
    """Full floor plan analysis."""
    tracer_module = get_tracer()
    if not tracer_module:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "FloorPlanTracer not available"
        }))]

    file_path = convert_path(args["file_path"])

    # Handle PDF
    if file_path.lower().endswith('.pdf'):
        page_num = args.get("page_num", 0)
        file_path = pdf_to_image(file_path, page_num)

    # Check file exists
    if not os.path.exists(file_path):
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"File not found: {file_path}"
        }))]

    # Create tracer and process
    FloorPlanTracer = tracer_module['FloorPlanTracer']
    tracer = FloorPlanTracer(verbose=False)

    result = tracer.process(
        file_path,
        scale_ft_per_px=args.get("scale_ft_per_px"),
        known_width_ft=args.get("known_width_ft"),
        refine=True,
        detect_rooms=args.get("detect_rooms", False),
        detect_openings=args.get("detect_openings", False)
    )

    # Serialize result
    output = {
        "success": True,
        "source": file_path,
        "analysis": serialize_floor_plan(result),
        "summary": {
            "walls": len(result.walls),
            "junctions": len(result.junctions),
            "openings": len(result.openings),
            "rooms": len(result.rooms),
            "scale_ft_per_px": result.scale_ft_per_px,
            "real_size_ft": [result.real_width_ft, result.real_height_ft]
        }
    }

    return [TextContent(type="text", text=json.dumps(output))]


async def handle_detect_scale(args: dict):
    """Scale detection only."""
    tracer_module = get_tracer()
    if not tracer_module:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "FloorPlanTracer not available"
        }))]

    file_path = convert_path(args["file_path"])

    # Handle PDF
    if file_path.lower().endswith('.pdf'):
        page_num = args.get("page_num", 0)
        file_path = pdf_to_image(file_path, page_num)

    # Import and run scale detector
    try:
        from src.intake import ScaleDetector, BoundsDetector, ImageLoader

        loader = ImageLoader()
        image = loader.load(file_path)

        bounds_detector = BoundsDetector()
        bounds = bounds_detector.detect(image)

        scale_detector = ScaleDetector()
        scale = scale_detector.detect_scale(image)

        # If hint provided, use it to calibrate
        if args.get("hint_width_ft"):
            scale = args["hint_width_ft"] / bounds.width

        output = {
            "success": True,
            "scale_ft_per_px": scale,
            "pixels_per_ft": 1 / scale if scale > 0 else 0,
            "image_size_px": [image.shape[1], image.shape[0]],
            "content_bounds_px": {
                "x_min": bounds.x_min,
                "y_min": bounds.y_min,
                "x_max": bounds.x_max,
                "y_max": bounds.y_max,
                "width": bounds.width,
                "height": bounds.height
            },
            "estimated_size_ft": [bounds.width * scale, bounds.height * scale]
        }

        return [TextContent(type="text", text=json.dumps(output))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }))]


async def handle_detect_walls(args: dict):
    """Wall detection with output format options."""
    tracer_module = get_tracer()
    if not tracer_module:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "FloorPlanTracer not available"
        }))]

    file_path = convert_path(args["file_path"])

    # Handle PDF
    if file_path.lower().endswith('.pdf'):
        page_num = args.get("page_num", 0)
        file_path = pdf_to_image(file_path, page_num)

    # Process
    FloorPlanTracer = tracer_module['FloorPlanTracer']
    tracer = FloorPlanTracer(verbose=False)

    result = tracer.process(
        file_path,
        scale_ft_per_px=args.get("scale_ft_per_px"),
        known_width_ft=args.get("known_width_ft"),
        refine=True,
        detect_rooms=False,
        detect_openings=False
    )

    output_format = args.get("output_format", "feet")
    scale = result.scale_ft_per_px

    if output_format == "pixels":
        walls = [w.to_dict() for w in result.walls]
    elif output_format == "revit":
        walls = format_walls_for_revit(
            result.walls,
            scale,
            level_id=args.get("level_id")
        )
    else:  # feet
        walls = []
        for w in result.walls:
            wall_dict = w.to_dict()
            wall_dict['start_ft'] = [w.start.x * scale, w.start.y * scale]
            wall_dict['end_ft'] = [w.end.x * scale, w.end.y * scale]
            wall_dict['length_ft'] = w.length * scale
            walls.append(wall_dict)

    output = {
        "success": True,
        "wall_count": len(walls),
        "scale_ft_per_px": scale,
        "output_format": output_format,
        "walls": walls
    }

    return [TextContent(type="text", text=json.dumps(output))]


async def handle_detect_openings(args: dict):
    """Detect doors and windows."""
    tracer_module = get_tracer()
    if not tracer_module:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "FloorPlanTracer not available"
        }))]

    file_path = convert_path(args["file_path"])

    # Handle PDF
    if file_path.lower().endswith('.pdf'):
        page_num = args.get("page_num", 0)
        file_path = pdf_to_image(file_path, page_num)

    # Process with openings
    FloorPlanTracer = tracer_module['FloorPlanTracer']
    tracer = FloorPlanTracer(verbose=False)

    result = tracer.process(
        file_path,
        scale_ft_per_px=args.get("scale_ft_per_px"),
        refine=True,
        detect_rooms=False,
        detect_openings=True
    )

    openings = [o.to_dict() for o in result.openings]

    output = {
        "success": True,
        "opening_count": len(openings),
        "openings": openings,
        "by_type": {}
    }

    # Group by type
    for o in openings:
        o_type = o.get('type', 'unknown')
        if o_type not in output["by_type"]:
            output["by_type"][o_type] = 0
        output["by_type"][o_type] += 1

    return [TextContent(type="text", text=json.dumps(output))]


async def handle_detect_rooms(args: dict):
    """Detect enclosed rooms."""
    tracer_module = get_tracer()
    if not tracer_module:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "FloorPlanTracer not available"
        }))]

    file_path = convert_path(args["file_path"])

    # Handle PDF
    if file_path.lower().endswith('.pdf'):
        page_num = args.get("page_num", 0)
        file_path = pdf_to_image(file_path, page_num)

    # Process with rooms
    FloorPlanTracer = tracer_module['FloorPlanTracer']
    tracer = FloorPlanTracer(verbose=False)

    result = tracer.process(
        file_path,
        scale_ft_per_px=args.get("scale_ft_per_px"),
        refine=True,
        detect_rooms=True,
        detect_openings=False
    )

    rooms = [r.to_dict() for r in result.rooms]

    output = {
        "success": True,
        "room_count": len(rooms),
        "rooms": rooms,
        "total_area_sqft": sum(r.get('area', 0) * (result.scale_ft_per_px ** 2) for r in rooms)
    }

    return [TextContent(type="text", text=json.dumps(output))]


async def handle_get_pdf_info(args: dict):
    """Get PDF metadata."""
    file_path = convert_path(args["file_path"])

    fitz = get_fitz()
    if fitz is None:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "PyMuPDF not installed"
        }))]

    try:
        doc = fitz.open(file_path)

        pages_info = []
        for i, page in enumerate(doc):
            rect = page.rect
            pages_info.append({
                "page_num": i,
                "width_pt": rect.width,
                "height_pt": rect.height,
                "width_in": rect.width / 72,
                "height_in": rect.height / 72
            })

        output = {
            "success": True,
            "file_path": file_path,
            "page_count": len(doc),
            "pages": pages_info,
            "metadata": dict(doc.metadata) if doc.metadata else {}
        }

        doc.close()
        return [TextContent(type="text", text=json.dumps(output))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }))]


async def handle_export_to_revit(args: dict):
    """Export to Revit-ready JSON."""
    tracer_module = get_tracer()
    if not tracer_module:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "FloorPlanTracer not available"
        }))]

    file_path = convert_path(args["file_path"])
    output_path = convert_path(args["output_path"])

    # Handle PDF
    if file_path.lower().endswith('.pdf'):
        file_path = pdf_to_image(file_path, 0)

    # Process
    FloorPlanTracer = tracer_module['FloorPlanTracer']
    tracer = FloorPlanTracer(verbose=False)

    result = tracer.process(
        file_path,
        scale_ft_per_px=args.get("scale_ft_per_px"),
        known_width_ft=args.get("known_width_ft"),
        refine=True,
        detect_rooms=False,
        detect_openings=False
    )

    # Export to Revit format
    level_id = args.get("level_id", 1959)
    wall_height = args.get("wall_height", 10.0)

    tracer.export_to_revit(
        result,
        output_path,
        level_id=level_id,
        default_height=wall_height
    )

    output = {
        "success": True,
        "output_path": output_path,
        "wall_count": len(result.walls),
        "scale_ft_per_px": result.scale_ft_per_px,
        "level_id": level_id,
        "wall_height": wall_height
    }

    return [TextContent(type="text", text=json.dumps(output))]


# =============================================================================
# ANNOTATION TOOL HANDLERS - Reference-based coordinate translation
# =============================================================================

def generate_session_id() -> str:
    """Generate unique session ID."""
    import uuid
    return str(uuid.uuid4())[:8]


async def handle_annotate_floor_plan(args: dict):
    """Create annotated floor plan with labeled elements."""
    tracer_module = get_tracer()
    annotator_module = get_annotator()

    if not tracer_module:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "FloorPlanTracer not available"
        }))]

    if not annotator_module:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "Annotation module not available"
        }))]

    file_path = convert_path(args["file_path"])

    # Handle PDF
    if file_path.lower().endswith('.pdf'):
        page_num = args.get("page_num", 0)
        file_path = pdf_to_image(file_path, page_num)

    if not os.path.exists(file_path):
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"File not found: {file_path}"
        }))]

    # Process with FloorPlanTracer first
    FloorPlanTracer = tracer_module['FloorPlanTracer']
    tracer = FloorPlanTracer(verbose=False)

    floor_plan = tracer.process(
        file_path,
        refine=True,
        detect_rooms=False,
        detect_openings=False
    )

    # Create annotated version
    AnnotatedFloorPlan = annotator_module['AnnotatedFloorPlan']
    annotated = AnnotatedFloorPlan.from_floor_plan(
        floor_plan,
        image_path=file_path,
        extract_text=args.get("extract_text", True)
    )

    # Generate session ID and store
    session_id = generate_session_id()
    _active_sessions[session_id] = annotated

    # Save annotated image if requested
    annotated_image_path = None
    if args.get("save_annotated_image"):
        annotated_image_path = convert_path(args["save_annotated_image"])
        annotated.save_annotated_image(annotated_image_path)

    # Get element counts
    element_counts = {
        'corners': len(annotated.labeler.by_type.get(annotated.labeler.by_type.__class__.__bases__[0], [])),
        'lines': 0,
        'text': 0
    }

    # Count by type
    from src.annotation.labeler import LabelType
    for t in LabelType:
        key = t.name.lower() + 's'
        if key == 'corners':
            key = 'corners'
        elif key == 'lines':
            key = 'lines'
        elif key == 'texts':
            key = 'text'
        element_counts[t.value] = len(annotated.labeler.by_type.get(t, []))

    output = {
        "success": True,
        "session_id": session_id,
        "source": file_path,
        "image_size": [annotated.image_width, annotated.image_height],
        "element_counts": element_counts,
        "total_elements": len(annotated.elements),
        "elements_summary": {
            t.value: [e.label for e in annotated.labeler.by_type.get(t, [])]
            for t in LabelType
        },
        "annotated_image": annotated_image_path
    }

    return [TextContent(type="text", text=json.dumps(output))]


async def handle_get_coordinate(args: dict):
    """Get coordinate of a labeled element."""
    session_id = args.get("session_id")
    label = args.get("label")

    if session_id not in _active_sessions:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Session {session_id} not found. Call annotate_floor_plan first."
        }))]

    plan = _active_sessions[session_id]
    result = plan.get_coordinate(label)

    if result is None:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Element {label} not found"
        }))]

    return [TextContent(type="text", text=json.dumps({
        "success": True,
        "label": label,
        **result
    }))]


async def handle_get_line(args: dict):
    """Get start/end points and length of a line."""
    session_id = args.get("session_id")
    label = args.get("label")

    if session_id not in _active_sessions:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Session {session_id} not found"
        }))]

    plan = _active_sessions[session_id]
    result = plan.get_line(label)

    if result is None:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Line {label} not found"
        }))]

    return [TextContent(type="text", text=json.dumps({
        "success": True,
        "label": label,
        **result
    }))]


async def handle_get_text(args: dict):
    """Get content and parsed dimension from text element."""
    session_id = args.get("session_id")
    label = args.get("label")

    if session_id not in _active_sessions:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Session {session_id} not found"
        }))]

    plan = _active_sessions[session_id]
    result = plan.get_text(label)

    if result is None:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Text element {label} not found"
        }))]

    return [TextContent(type="text", text=json.dumps({
        "success": True,
        **result
    }))]


async def handle_set_scale(args: dict):
    """Set scale using dimension text and measured line."""
    session_id = args.get("session_id")
    text_label = args.get("text_label")
    line_label = args.get("line_label")

    if session_id not in _active_sessions:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Session {session_id} not found"
        }))]

    plan = _active_sessions[session_id]
    result = plan.set_scale(text_label, line_label)

    return [TextContent(type="text", text=json.dumps(result))]


async def handle_verify_scale(args: dict):
    """Verify scale with another dimension-line pair."""
    session_id = args.get("session_id")
    text_label = args.get("text_label")
    line_label = args.get("line_label")

    if session_id not in _active_sessions:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Session {session_id} not found"
        }))]

    plan = _active_sessions[session_id]
    result = plan.verify_scale(text_label, line_label)

    return [TextContent(type="text", text=json.dumps(result))]


async def handle_verify_length(args: dict):
    """Verify line matches expected length."""
    session_id = args.get("session_id")
    line_label = args.get("line_label")
    expected_ft = args.get("expected_ft")

    if session_id not in _active_sessions:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Session {session_id} not found"
        }))]

    plan = _active_sessions[session_id]
    result = plan.verify_length(line_label, expected_ft)

    return [TextContent(type="text", text=json.dumps(result))]


async def handle_add_wall(args: dict):
    """Add a wall between two corners."""
    session_id = args.get("session_id")
    start_corner = args.get("start_corner")
    end_corner = args.get("end_corner")
    wall_type = args.get("wall_type", "interior")

    if session_id not in _active_sessions:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Session {session_id} not found"
        }))]

    plan = _active_sessions[session_id]
    result = plan.add_wall(start_corner, end_corner, wall_type)

    return [TextContent(type="text", text=json.dumps(result))]


async def handle_get_model(args: dict):
    """Get all placed walls ready for Revit export."""
    session_id = args.get("session_id")

    if session_id not in _active_sessions:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Session {session_id} not found"
        }))]

    plan = _active_sessions[session_id]
    result = plan.get_model()

    return [TextContent(type="text", text=json.dumps({
        "success": True,
        **result
    }))]


async def handle_list_elements(args: dict):
    """List all labeled elements."""
    session_id = args.get("session_id")
    element_type = args.get("element_type")

    if session_id not in _active_sessions:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Session {session_id} not found"
        }))]

    plan = _active_sessions[session_id]
    elements = plan.list_elements(element_type)

    return [TextContent(type="text", text=json.dumps({
        "success": True,
        "element_type": element_type or "all",
        "count": len(elements),
        "elements": elements
    }))]


# =============================================================================
# SHOWUI SEMANTIC GROUNDING HANDLERS
# =============================================================================

def get_or_create_hybrid_grounder(session_id: str):
    """Get or create a HybridGrounder for a session."""
    if session_id not in _hybrid_grounders:
        showui_module = get_showui()
        if not showui_module:
            return None

        if session_id in _active_sessions:
            plan = _active_sessions[session_id]
            grounder = showui_module['HybridGrounder'](plan)
        else:
            grounder = showui_module['HybridGrounder']()

        _hybrid_grounders[session_id] = grounder

    return _hybrid_grounders[session_id]


async def handle_find_element_semantic(args: dict):
    """Find element by natural language description using ShowUI."""
    showui_module = get_showui()
    if not showui_module:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "ShowUI module not available. Ensure gradio_client is installed."
        }))]

    query = args.get("query")
    image_path = convert_path(args.get("image_path"))
    iterations = args.get("iterations", 1)

    if not os.path.exists(image_path):
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Image not found: {image_path}"
        }))]

    try:
        ShowUIGrounder = showui_module['ShowUIGrounder']
        grounder = ShowUIGrounder()

        result = grounder.find_element(query, image_path, iterations)

        if result:
            return [TextContent(type="text", text=json.dumps({
                "success": True,
                "query": query,
                "x": result.x,
                "y": result.y,
                "norm_x": result.norm_x,
                "norm_y": result.norm_y,
                "annotated_image": result.annotated_image_url
            }))]
        else:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": f"Could not find element matching: {query}"
            }))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }))]


async def handle_find_corner_semantic(args: dict):
    """Find a specific corner of a room."""
    showui_module = get_showui()
    if not showui_module:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "ShowUI module not available"
        }))]

    room_description = args.get("room_description")
    corner_position = args.get("corner_position")
    image_path = convert_path(args.get("image_path"))

    if not os.path.exists(image_path):
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Image not found: {image_path}"
        }))]

    try:
        ShowUIGrounder = showui_module['ShowUIGrounder']
        grounder = ShowUIGrounder()

        result = grounder.find_corner(room_description, corner_position, image_path)

        if result:
            return [TextContent(type="text", text=json.dumps({
                "success": True,
                "room": room_description,
                "corner": corner_position,
                "x": result.x,
                "y": result.y,
                "norm_x": result.norm_x,
                "norm_y": result.norm_y
            }))]
        else:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": f"Could not find {corner_position} corner of {room_description}"
            }))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }))]


async def handle_find_opening_semantic(args: dict):
    """Find a door or window by description."""
    showui_module = get_showui()
    if not showui_module:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "ShowUI module not available"
        }))]

    opening_type = args.get("opening_type")
    location_hint = args.get("location_hint")
    image_path = convert_path(args.get("image_path"))

    if not os.path.exists(image_path):
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Image not found: {image_path}"
        }))]

    try:
        ShowUIGrounder = showui_module['ShowUIGrounder']
        grounder = ShowUIGrounder()

        result = grounder.find_opening(opening_type, location_hint, image_path)

        if result:
            return [TextContent(type="text", text=json.dumps({
                "success": True,
                "opening_type": opening_type,
                "location": location_hint,
                "x": result.x,
                "y": result.y,
                "norm_x": result.norm_x,
                "norm_y": result.norm_y
            }))]
        else:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": f"Could not find {location_hint} {opening_type}"
            }))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }))]


async def handle_semantic_to_label(args: dict):
    """Convert semantic description to pre-detected label."""
    session_id = args.get("session_id")
    query = args.get("query")
    label_type = args.get("label_type")
    max_distance = args.get("max_distance", 50.0)

    if session_id not in _active_sessions:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Session {session_id} not found. Call annotate_floor_plan first."
        }))]

    plan = _active_sessions[session_id]
    grounder = get_or_create_hybrid_grounder(session_id)

    if not grounder:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "ShowUI module not available"
        }))]

    # Get the image path from the plan
    image_path = plan.image_path

    if not image_path or not os.path.exists(image_path):
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "Image path not available in session"
        }))]

    try:
        grounder.set_annotated_plan(plan)
        label = grounder.semantic_to_label(query, image_path, label_type, max_distance)

        if label:
            # Get the coordinate of the label for verification
            coord = plan.get_coordinate(label)
            return [TextContent(type="text", text=json.dumps({
                "success": True,
                "query": query,
                "matched_label": label,
                "coordinate": coord
            }))]
        else:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": f"Could not map '{query}' to any pre-detected label within {max_distance}px"
            }))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }))]


async def handle_add_wall_semantic(args: dict):
    """Add wall using semantic descriptions for endpoints."""
    session_id = args.get("session_id")
    start_description = args.get("start_description")
    end_description = args.get("end_description")
    wall_type = args.get("wall_type", "interior")

    if session_id not in _active_sessions:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Session {session_id} not found. Call annotate_floor_plan first."
        }))]

    plan = _active_sessions[session_id]
    grounder = get_or_create_hybrid_grounder(session_id)

    if not grounder:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "ShowUI module not available"
        }))]

    image_path = plan.image_path

    if not image_path or not os.path.exists(image_path):
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "Image path not available in session"
        }))]

    try:
        grounder.set_annotated_plan(plan)
        wall = grounder.build_wall_semantic(start_description, end_description, image_path, wall_type)

        if wall:
            return [TextContent(type="text", text=json.dumps({
                "success": True,
                "wall": wall,
                "start_description": start_description,
                "end_description": end_description
            }))]
        else:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": f"Could not create wall from '{start_description}' to '{end_description}'. Endpoints may not have been found or mapped."
            }))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }))]


# =============================================================================
# TRAJECTORY TOOL HANDLERS
# =============================================================================

_trajectory_generator = None


def get_trajectory_generator():
    """Lazy load trajectory generator."""
    global _trajectory_generator
    if _trajectory_generator is None:
        try:
            from src.annotation import TrajectoryGenerator
            _trajectory_generator = TrajectoryGenerator()
        except ImportError as e:
            logger.error(f"Failed to import TrajectoryGenerator: {e}")
            return None
    return _trajectory_generator


async def handle_generate_trajectory(args: dict):
    """Generate linear or drag trajectory between two points."""
    gen = get_trajectory_generator()
    if not gen:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "TrajectoryGenerator not available"
        }))]

    start = tuple(args.get("start"))
    end = tuple(args.get("end"))
    steps = args.get("steps", 20)
    easing = args.get("easing", "ease_in_out")
    traj_type = args.get("trajectory_type", "linear")

    try:
        if traj_type == "drag":
            trajectory = gen.drag(start, end, steps, overshoot=0.1)
        else:
            trajectory = gen.linear(start, end, steps, easing)

        return [TextContent(type="text", text=json.dumps({
            "success": True,
            "trajectory_type": trajectory.trajectory_type,
            "point_count": len(trajectory.points),
            "total_distance": trajectory.total_distance,
            "easing": trajectory.easing,
            "points": trajectory.to_tuples()
        }))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }))]


async def handle_generate_trajectory_curved(args: dict):
    """Generate curved Bezier trajectory."""
    gen = get_trajectory_generator()
    if not gen:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "TrajectoryGenerator not available"
        }))]

    start = tuple(args.get("start"))
    end = tuple(args.get("end"))
    steps = args.get("steps", 25)
    easing = args.get("easing", "ease_in_out")

    # Auto-calculate control point if not provided
    control = args.get("control")
    if control:
        control = tuple(control)
    else:
        # Create a control point perpendicular to the line, offset by 20% of distance
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dist = (dx ** 2 + dy ** 2) ** 0.5
        # Perpendicular offset
        offset = dist * 0.2
        control = (mid_x - dy / dist * offset, mid_y + dx / dist * offset)

    try:
        trajectory = gen.bezier_quadratic(start, control, end, steps, easing)

        return [TextContent(type="text", text=json.dumps({
            "success": True,
            "trajectory_type": trajectory.trajectory_type,
            "point_count": len(trajectory.points),
            "total_distance": trajectory.total_distance,
            "control_point": control,
            "points": trajectory.to_tuples()
        }))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }))]


async def handle_generate_trajectory_semantic(args: dict):
    """Generate trajectory using semantic descriptions for endpoints."""
    gen = get_trajectory_generator()
    showui_module = get_showui()

    if not gen:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "TrajectoryGenerator not available"
        }))]

    if not showui_module:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "ShowUI module not available"
        }))]

    start_desc = args.get("start_description")
    end_desc = args.get("end_description")
    image_path = convert_path(args.get("image_path"))
    steps = args.get("steps", 20)
    easing = args.get("easing", "ease_in_out")

    if not os.path.exists(image_path):
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Image not found: {image_path}"
        }))]

    try:
        ShowUIGrounder = showui_module['ShowUIGrounder']
        grounder = ShowUIGrounder()

        # Find start point
        start_result = grounder.find_element(start_desc, image_path)
        if not start_result:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": f"Could not find start: {start_desc}"
            }))]

        # Find end point
        end_result = grounder.find_element(end_desc, image_path)
        if not end_result:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": f"Could not find end: {end_desc}"
            }))]

        # Generate trajectory
        start = (start_result.x, start_result.y)
        end = (end_result.x, end_result.y)
        trajectory = gen.linear(start, end, steps, easing)

        return [TextContent(type="text", text=json.dumps({
            "success": True,
            "start_description": start_desc,
            "end_description": end_desc,
            "start_coord": start,
            "end_coord": end,
            "trajectory_type": trajectory.trajectory_type,
            "point_count": len(trajectory.points),
            "total_distance": trajectory.total_distance,
            "points": trajectory.to_tuples()
        }))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }))]


async def handle_generate_trajectory_labels(args: dict):
    """Generate trajectory between two labeled elements."""
    gen = get_trajectory_generator()
    if not gen:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "TrajectoryGenerator not available"
        }))]

    session_id = args.get("session_id")
    start_label = args.get("start_label")
    end_label = args.get("end_label")
    steps = args.get("steps", 20)
    easing = args.get("easing", "ease_in_out")

    if session_id not in _active_sessions:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Session {session_id} not found"
        }))]

    plan = _active_sessions[session_id]

    try:
        # Get coordinates for labels
        start_coord = plan.get_coordinate(start_label)
        if not start_coord:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": f"Label {start_label} not found"
            }))]

        end_coord = plan.get_coordinate(end_label)
        if not end_coord:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": f"Label {end_label} not found"
            }))]

        # Generate trajectory
        start = (start_coord['x'], start_coord['y'])
        end = (end_coord['x'], end_coord['y'])
        trajectory = gen.linear(start, end, steps, easing)

        return [TextContent(type="text", text=json.dumps({
            "success": True,
            "start_label": start_label,
            "end_label": end_label,
            "start_coord": start,
            "end_coord": end,
            "trajectory_type": trajectory.trajectory_type,
            "point_count": len(trajectory.points),
            "total_distance": trajectory.total_distance,
            "points": trajectory.to_tuples()
        }))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }))]


async def handle_execute_trajectory(args: dict):
    """Execute trajectory as actual mouse movement."""
    points = args.get("points", [])
    delay_ms = args.get("delay_ms", 10)
    click_at_end = args.get("click_at_end", False)
    drag = args.get("drag", False)

    if not points or len(points) < 2:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "Need at least 2 points"
        }))]

    try:
        # Try to use pyautogui
        import pyautogui
        import time

        pyautogui.PAUSE = delay_ms / 1000

        if drag:
            # Drag operation
            start = points[0]
            pyautogui.moveTo(int(start[0]), int(start[1]))
            pyautogui.mouseDown()

            for point in points[1:]:
                pyautogui.moveTo(int(point[0]), int(point[1]))

            pyautogui.mouseUp()
        else:
            # Regular movement
            for point in points:
                pyautogui.moveTo(int(point[0]), int(point[1]))

            if click_at_end:
                pyautogui.click()

        return [TextContent(type="text", text=json.dumps({
            "success": True,
            "points_executed": len(points),
            "drag": drag,
            "clicked": click_at_end
        }))]

    except ImportError:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "pyautogui not installed. Run: pip install pyautogui"
        }))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }))]


# =============================================================================
# MAIN
# =============================================================================

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
