"""
PyMuPDF-based annotation extractor for PDF files.

Extracts all annotation types including:
- Text annotations (highlights, underlines, strikeouts)
- Markup annotations (circles, rectangles, polygons, lines)
- Text comments and notes
- Stamps and ink annotations
- Free text annotations
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


@dataclass
class Markup:
    """Represents a single markup/annotation from a PDF."""
    id: str
    page: int
    type: str
    subtype: str
    content: str
    author: str
    created: Optional[str]
    modified: Optional[str]
    color: Optional[str]
    rect: Dict[str, float]  # x0, y0, x1, y1
    reply_to: Optional[str]
    subject: Optional[str]
    label: Optional[str]
    source_file: str
    raw_data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PyMuPDFExtractor:
    """Extract annotations from PDF files using PyMuPDF."""

    # Annotation type mapping
    ANNOT_TYPES = {
        0: "Text",
        1: "Link",
        2: "FreeText",
        3: "Line",
        4: "Square",
        5: "Circle",
        6: "Polygon",
        7: "PolyLine",
        8: "Highlight",
        9: "Underline",
        10: "Squiggly",
        11: "StrikeOut",
        12: "Stamp",
        13: "Caret",
        14: "Ink",
        15: "Popup",
        16: "FileAttachment",
        17: "Sound",
        18: "Movie",
        19: "Widget",
        20: "Screen",
        21: "PrinterMark",
        22: "TrapNet",
        23: "Watermark",
        24: "3D",
        25: "Redact",
    }

    def __init__(self):
        if not PYMUPDF_AVAILABLE:
            raise ImportError(
                "PyMuPDF is not installed. Install with: pip install PyMuPDF"
            )

    def extract(self, pdf_path: str) -> List[Markup]:
        """
        Extract all annotations from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of Markup objects
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        markups = []
        doc = fitz.open(str(pdf_path))

        try:
            for page_num, page in enumerate(doc, start=1):
                annotations = page.annots()
                if annotations:
                    for annot in annotations:
                        markup = self._extract_annotation(
                            annot, page_num, str(pdf_path)
                        )
                        if markup:
                            markups.append(markup)
        finally:
            doc.close()

        return markups

    def _extract_annotation(
        self, annot, page_num: int, source_file: str
    ) -> Optional[Markup]:
        """Extract data from a single annotation."""
        try:
            annot_type = annot.type[0]
            annot_subtype = annot.type[1] if len(annot.type) > 1 else ""

            # Skip popup annotations (they're part of other annotations)
            if annot_type == 15:  # Popup
                return None

            # Get annotation rectangle
            rect = annot.rect
            rect_dict = {
                "x0": rect.x0,
                "y0": rect.y0,
                "x1": rect.x1,
                "y1": rect.y1,
                "width": rect.width,
                "height": rect.height,
            }

            # Get color as hex string
            color = None
            colors = annot.colors
            if colors and "stroke" in colors and colors["stroke"]:
                rgb = colors["stroke"]
                if len(rgb) >= 3:
                    color = "#{:02x}{:02x}{:02x}".format(
                        int(rgb[0] * 255),
                        int(rgb[1] * 255),
                        int(rgb[2] * 255)
                    )

            # Get dates
            created = None
            modified = None
            info = annot.info
            if info.get("creationDate"):
                created = self._parse_pdf_date(info["creationDate"])
            if info.get("modDate"):
                modified = self._parse_pdf_date(info["modDate"])

            # Build raw data dictionary
            raw_data = {
                "type_code": annot_type,
                "flags": annot.flags,
                "opacity": annot.opacity,
                "border": annot.border,
                "info": info,
            }

            # Get text content from different sources
            content = ""
            if info.get("content"):
                content = info["content"]
            elif hasattr(annot, "get_text") and annot_type in [8, 9, 10, 11]:
                # For highlight/underline/strikeout, get the underlying text
                try:
                    content = annot.get_text()
                except:
                    pass

            return Markup(
                id=f"p{page_num}_a{hash(str(rect_dict)) % 10000:04d}",
                page=page_num,
                type=self.ANNOT_TYPES.get(annot_type, f"Unknown({annot_type})"),
                subtype=annot_subtype,
                content=content.strip() if content else "",
                author=info.get("title", ""),
                created=created,
                modified=modified,
                color=color,
                rect=rect_dict,
                reply_to=info.get("irt"),  # In reply to
                subject=info.get("subject", ""),
                label=info.get("name", ""),
                source_file=source_file,
                raw_data=raw_data,
            )

        except Exception as e:
            # Log error but don't fail entire extraction
            print(f"Warning: Failed to extract annotation: {e}")
            return None

    def _parse_pdf_date(self, pdf_date: str) -> Optional[str]:
        """Parse PDF date format (D:YYYYMMDDHHmmSS) to ISO format."""
        try:
            if pdf_date.startswith("D:"):
                pdf_date = pdf_date[2:]

            # Handle various lengths
            if len(pdf_date) >= 14:
                dt = datetime.strptime(pdf_date[:14], "%Y%m%d%H%M%S")
                return dt.isoformat()
            elif len(pdf_date) >= 8:
                dt = datetime.strptime(pdf_date[:8], "%Y%m%d")
                return dt.isoformat()
        except:
            pass
        return pdf_date

    def extract_to_dict(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract annotations and return as list of dictionaries."""
        markups = self.extract(pdf_path)
        return [m.to_dict() for m in markups]

    def get_summary(self, pdf_path: str) -> Dict[str, Any]:
        """Get a summary of annotations in a PDF."""
        markups = self.extract(pdf_path)

        # Count by type
        type_counts = {}
        author_counts = {}
        page_counts = {}

        for m in markups:
            type_counts[m.type] = type_counts.get(m.type, 0) + 1
            if m.author:
                author_counts[m.author] = author_counts.get(m.author, 0) + 1
            page_counts[m.page] = page_counts.get(m.page, 0) + 1

        return {
            "file": pdf_path,
            "total_markups": len(markups),
            "by_type": type_counts,
            "by_author": author_counts,
            "by_page": page_counts,
            "pages_with_markups": len(page_counts),
        }


# Convenience function
def extract_pdf_markups(pdf_path: str) -> List[Markup]:
    """Extract all markups from a PDF file."""
    extractor = PyMuPDFExtractor()
    return extractor.extract(pdf_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <pdf_file>")
        sys.exit(1)

    pdf_file = sys.argv[1]
    extractor = PyMuPDFExtractor()

    print(f"Extracting markups from: {pdf_file}\n")

    summary = extractor.get_summary(pdf_file)
    print(f"Total markups: {summary['total_markups']}")
    print(f"By type: {json.dumps(summary['by_type'], indent=2)}")
    print(f"By author: {json.dumps(summary['by_author'], indent=2)}")

    print("\n--- All Markups ---")
    markups = extractor.extract(pdf_file)
    for m in markups:
        print(f"\nPage {m.page} | {m.type} | {m.author}")
        if m.content:
            print(f"  Content: {m.content[:100]}...")
