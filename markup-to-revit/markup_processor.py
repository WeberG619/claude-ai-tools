#!/usr/bin/env python3
"""
Markup-to-Revit Processor

Extracts markups from PDFs, maps them to Revit model coordinates,
and generates structured change lists for execution via RevitMCPBridge.

Usage:
    python markup_processor.py <pdf_path> [--page N] [--scale SCALE] [--output JSON]

Integration:
    from markup_processor import MarkupProcessor
    mp = MarkupProcessor(pdf_path)
    changes = mp.extract_and_map(view_info)
"""

import json
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple

# Add pdf_markup_analyzer to path
sys.path.insert(0, str(Path(__file__).parent.parent / "_CLAUDE-TOOLS" / "agent-team" / "projects" / "pdf_markup_analyzer"))
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/agent-team/projects/pdf_markup_analyzer")

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class MarkupChange:
    """A single interpreted change from a markup."""
    id: int
    page: int
    change_type: str          # "edit", "add", "delete", "move", "dimension", "comment"
    category: str             # "door", "wall", "window", "text", "dimension", "room", "general"
    description: str          # Human-readable description of the change
    markup_text: str          # Raw text from the markup
    pdf_location: Dict        # {x0, y0, x1, y1} in PDF coordinates
    revit_location: Optional[Dict] = None  # {x, y} in Revit feet after coordinate transform
    matched_elements: List[Dict] = field(default_factory=list)  # Elements found near this location
    confidence: float = 0.0   # 0-1 confidence in interpretation
    status: str = "pending"   # "pending", "approved", "applied", "skipped", "failed"

    def to_dict(self):
        return asdict(self)


@dataclass
class CoordinateTransform:
    """Maps PDF page coordinates to Revit model coordinates."""
    # PDF page dimensions (in points, 72 per inch)
    pdf_width: float
    pdf_height: float
    # Revit view bounds (in feet)
    revit_min_x: float
    revit_min_y: float
    revit_max_x: float
    revit_max_y: float
    # Drawing scale (e.g., 48 for 1/4" = 1'-0")
    scale: int = 48
    # PDF has origin at bottom-left, Revit at model origin
    # The transform maps the drawing area within the PDF page to Revit coordinates

    def pdf_to_revit(self, pdf_x: float, pdf_y: float) -> Tuple[float, float]:
        """Convert PDF point coordinates to Revit feet coordinates."""
        # Normalize to 0-1 range within PDF page
        norm_x = pdf_x / self.pdf_width
        norm_y = pdf_y / self.pdf_height  # PDF y=0 is top in PyMuPDF

        # Map to Revit coordinate range
        # Note: PDF y increases downward in PyMuPDF, Revit y increases upward
        revit_x = self.revit_min_x + norm_x * (self.revit_max_x - self.revit_min_x)
        revit_y = self.revit_max_y - norm_y * (self.revit_max_y - self.revit_min_y)

        return (round(revit_x, 3), round(revit_y, 3))


# =============================================================================
# MARKUP CLASSIFICATION
# =============================================================================

# Keywords that indicate change types
CHANGE_KEYWORDS = {
    "edit": ["change", "revise", "modify", "correct", "update", "should be", "change to",
             "replace", "was", "is now", "new", "revised"],
    "add": ["add", "new", "provide", "install", "include", "need", "missing",
            "insert", "place", "create"],
    "delete": ["delete", "remove", "eliminate", "omit", "not required", "n/r",
               "void", "strike", "cancel"],
    "move": ["move", "relocate", "shift", "reposition", "align", "center"],
    "dimension": ["dim", "dimension", "ft", "feet", "inches", "'", '"',
                  "width", "height", "length", "clear", "min", "max"],
    "comment": ["verify", "confirm", "check", "note", "see", "refer", "per",
                "question", "?", "clarify", "coordinate", "rfi"],
}

# Keywords that indicate element categories
CATEGORY_KEYWORDS = {
    "door": ["door", "dr", "swing", "hinge", "closer", "threshold", "frame",
             "hardware", "panic", "lever"],
    "window": ["window", "wdw", "glazing", "glass", "sill", "head", "mullion"],
    "wall": ["wall", "partition", "demising", "furring", "gypsum", "drywall",
             "gyp", "stud", "cmu", "masonry"],
    "room": ["room", "space", "area", "closet", "bathroom", "kitchen", "office",
             "corridor", "hallway"],
    "dimension": ["dim", "dimension", "string", "chain", "reference"],
    "text": ["note", "text", "label", "tag", "keynote", "callout"],
}


def classify_change_type(text: str) -> str:
    """Determine the type of change from markup text."""
    text_lower = text.lower()
    scores = {}
    for change_type, keywords in CHANGE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[change_type] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "comment"


def classify_category(text: str) -> str:
    """Determine what category of element the markup refers to."""
    text_lower = text.lower()
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[category] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


# =============================================================================
# MAIN PROCESSOR
# =============================================================================

class MarkupProcessor:
    """Extract and interpret markups from a PDF for Revit implementation."""

    def __init__(self, pdf_path: str):
        if not HAS_PYMUPDF:
            raise ImportError("PyMuPDF required. Install: pip install PyMuPDF")
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        self.doc = fitz.open(str(self.pdf_path))
        self.changes: List[MarkupChange] = []

    def close(self):
        self.doc.close()

    def get_page_info(self, page_num: int = 1) -> Dict:
        """Get page dimensions and metadata."""
        page = self.doc[page_num - 1]
        rect = page.rect
        return {
            "page": page_num,
            "width_pts": rect.width,
            "height_pts": rect.height,
            "width_inches": rect.width / 72,
            "height_inches": rect.height / 72,
            "rotation": page.rotation,
            "annotation_count": len(list(page.annots() or []))
        }

    def extract_markups(self, page_num: int = None) -> List[MarkupChange]:
        """Extract all markups from the PDF and classify them."""
        changes = []
        change_id = 0

        pages = range(len(self.doc)) if page_num is None else [page_num - 1]

        for pg_idx in pages:
            page = self.doc[pg_idx]
            annotations = page.annots()
            if not annotations:
                continue

            for annot in annotations:
                annot_type = annot.type[0]

                # Skip popups, links, and widgets
                if annot_type in [1, 15, 19]:
                    continue

                # Get annotation info
                rect = annot.rect
                info = annot.info
                content = info.get("content", "")

                # For highlights/strikeouts, get the underlying text
                if annot_type in [8, 9, 10, 11]:
                    try:
                        underlying = page.get_text("text", clip=rect).strip()
                        if underlying:
                            content = f"[{['', '', 'FreeText', 'Line', 'Square', 'Circle', 'Polygon', 'PolyLine', 'Highlight', 'Underline', 'Squiggly', 'StrikeOut'][annot_type]}] {underlying}: {content}"
                    except:
                        pass

                # For FreeText (callouts), get the text
                if annot_type == 2:
                    try:
                        content = annot.get_text() or content
                    except:
                        pass

                if not content.strip():
                    # Try to get text near the annotation
                    expanded = fitz.Rect(rect.x0 - 20, rect.y0 - 20,
                                        rect.x1 + 20, rect.y1 + 20)
                    nearby_text = page.get_text("text", clip=expanded).strip()
                    if nearby_text:
                        content = f"[Near annotation] {nearby_text}"

                if not content.strip():
                    continue

                change_id += 1
                change_type = classify_change_type(content)
                category = classify_category(content)

                # Build description
                annot_type_name = {
                    0: "Note", 2: "Callout", 3: "Line", 4: "Rectangle",
                    5: "Circle/Cloud", 6: "Polygon", 7: "Polyline",
                    8: "Highlight", 11: "Strikeout", 12: "Stamp", 14: "Ink"
                }.get(annot_type, f"Type-{annot_type}")

                description = f"{annot_type_name}: {content[:200]}"

                change = MarkupChange(
                    id=change_id,
                    page=pg_idx + 1,
                    change_type=change_type,
                    category=category,
                    description=description,
                    markup_text=content.strip(),
                    pdf_location={
                        "x0": round(rect.x0, 1),
                        "y0": round(rect.y0, 1),
                        "x1": round(rect.x1, 1),
                        "y1": round(rect.y1, 1),
                        "center_x": round((rect.x0 + rect.x1) / 2, 1),
                        "center_y": round((rect.y0 + rect.y1) / 2, 1),
                    },
                    confidence=0.7 if change_type != "comment" else 0.5,
                )
                changes.append(change)

        self.changes = changes
        return changes

    def apply_coordinate_transform(self, transform: CoordinateTransform):
        """Map PDF locations to Revit coordinates for all changes."""
        for change in self.changes:
            center_x = change.pdf_location["center_x"]
            center_y = change.pdf_location["center_y"]
            rx, ry = transform.pdf_to_revit(center_x, center_y)
            change.revit_location = {"x": rx, "y": ry}

    def export_json(self, output_path: str = None) -> str:
        """Export changes as JSON."""
        data = {
            "source": str(self.pdf_path),
            "total_markups": len(self.changes),
            "by_type": {},
            "by_category": {},
            "changes": [c.to_dict() for c in self.changes],
        }

        # Summarize
        for c in self.changes:
            data["by_type"][c.change_type] = data["by_type"].get(c.change_type, 0) + 1
            data["by_category"][c.category] = data["by_category"].get(c.category, 0) + 1

        result = json.dumps(data, indent=2)

        if output_path:
            Path(output_path).write_text(result)

        return result

    def generate_revit_commands(self) -> List[Dict]:
        """Generate MCP method calls for each actionable change."""
        commands = []

        for change in self.changes:
            if change.change_type == "comment":
                continue  # Comments are informational only
            if change.status != "approved":
                continue  # Only process approved changes

            cmd = {
                "change_id": change.id,
                "description": change.description,
            }

            if change.change_type == "delete" and change.matched_elements:
                cmd["method"] = "deleteElements"
                cmd["params"] = {
                    "elementIds": [e["id"] for e in change.matched_elements]
                }

            elif change.change_type == "edit" and change.matched_elements:
                # Determine what parameter to edit based on context
                cmd["method"] = "setParameterValue"
                cmd["params"] = {
                    "elementId": change.matched_elements[0]["id"],
                    "note": f"Manual review needed: {change.markup_text}"
                }

            elif change.change_type == "move" and change.matched_elements:
                cmd["method"] = "moveElement"
                cmd["params"] = {
                    "elementId": change.matched_elements[0]["id"],
                    "note": f"Manual review needed: {change.markup_text}"
                }

            elif change.change_type == "add":
                cmd["method"] = "MANUAL"
                cmd["params"] = {
                    "note": f"Add element: {change.markup_text}",
                    "location": change.revit_location
                }

            else:
                cmd["method"] = "MANUAL"
                cmd["params"] = {"note": change.markup_text}

            commands.append(cmd)

        return commands


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Extract PDF markups for Revit implementation")
    parser.add_argument("pdf_path", help="Path to markup PDF")
    parser.add_argument("--page", type=int, default=None, help="Specific page number")
    parser.add_argument("--output", "-o", help="Output JSON path")
    parser.add_argument("--summary", action="store_true", help="Print summary only")
    args = parser.parse_args()

    processor = MarkupProcessor(args.pdf_path)
    try:
        changes = processor.extract_markups(page_num=args.page)

        if args.summary:
            print(f"File: {args.pdf_path}")
            print(f"Total markups: {len(changes)}")
            by_type = {}
            for c in changes:
                by_type[c.change_type] = by_type.get(c.change_type, 0) + 1
            for t, count in sorted(by_type.items()):
                print(f"  {t}: {count}")
            print()
            for c in changes:
                status = "ACTION" if c.change_type != "comment" else "INFO"
                print(f"  [{status}] #{c.id} ({c.change_type}/{c.category}): {c.markup_text[:100]}")
        else:
            result = processor.export_json(args.output)
            if not args.output:
                print(result)
            else:
                print(f"Exported {len(changes)} markups to {args.output}")
    finally:
        processor.close()


if __name__ == "__main__":
    main()
