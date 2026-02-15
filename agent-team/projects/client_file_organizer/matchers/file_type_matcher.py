"""
File Type Matcher - Categorizes files by type and purpose.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileTypeMatch:
    category: str
    subcategory: str
    suggested_folder: str
    confidence: float


class FileTypeMatcher:
    """Categorizes files based on extension and naming patterns."""

    # File type categories for architecture/engineering
    CATEGORIES = {
        "drawings": {
            "extensions": [".dwg", ".dxf", ".dgn"],
            "subcategories": {
                "cad": [".dwg", ".dxf"],
                "microstation": [".dgn"],
            },
            "folder": "01 - CAD"
        },
        "models": {
            "extensions": [".rvt", ".rfa", ".rte", ".ifc", ".nwd", ".nwc"],
            "subcategories": {
                "revit": [".rvt", ".rfa", ".rte"],
                "navisworks": [".nwd", ".nwc"],
                "ifc": [".ifc"],
            },
            "folder": "02 - Models"
        },
        "documents": {
            "extensions": [".pdf", ".doc", ".docx", ".txt", ".rtf"],
            "subcategories": {
                "pdf": [".pdf"],
                "word": [".doc", ".docx"],
                "text": [".txt", ".rtf"],
            },
            "folder": "03 - Documents"
        },
        "images": {
            "extensions": [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"],
            "subcategories": {
                "photo": [".jpg", ".jpeg"],
                "render": [".png", ".tif", ".tiff"],
                "other": [".bmp", ".gif"],
            },
            "folder": "04 - Images"
        },
        "spreadsheets": {
            "extensions": [".xlsx", ".xls", ".csv"],
            "subcategories": {
                "excel": [".xlsx", ".xls"],
                "csv": [".csv"],
            },
            "folder": "05 - Spreadsheets"
        },
        "specifications": {
            "extensions": [".docx", ".pdf"],
            "patterns": ["spec", "specification", "div"],
            "folder": "06 - Specifications"
        },
        "correspondence": {
            "extensions": [".pdf", ".msg", ".eml"],
            "patterns": ["letter", "email", "memo", "rfi", "submittal"],
            "folder": "07 - Correspondence"
        },
        "photos": {
            "extensions": [".jpg", ".jpeg", ".png", ".heic"],
            "patterns": ["photo", "site", "progress", "img_", "dsc_"],
            "folder": "08 - Photos"
        }
    }

    def __init__(self, custom_categories: Dict = None):
        """Initialize with optional custom categories."""
        self.categories = {**self.CATEGORIES}
        if custom_categories:
            self.categories.update(custom_categories)

    def match_file(self, filepath: str) -> Optional[FileTypeMatch]:
        """Match file to category based on extension and name patterns."""
        path = Path(filepath)
        ext = path.suffix.lower()
        name = path.stem.lower()

        matches = []

        for category, config in self.categories.items():
            confidence = 0.0
            subcategory = "general"

            # Check extension
            if ext in config.get("extensions", []):
                confidence = 0.7

                # Find subcategory
                for subcat, exts in config.get("subcategories", {}).items():
                    if ext in exts:
                        subcategory = subcat
                        confidence += 0.1
                        break

            # Check name patterns
            for pattern in config.get("patterns", []):
                if pattern in name:
                    confidence += 0.2

            if confidence > 0:
                matches.append(FileTypeMatch(
                    category=category,
                    subcategory=subcategory,
                    suggested_folder=config.get("folder", category),
                    confidence=min(confidence, 1.0)
                ))

        if not matches:
            return None

        # Return highest confidence match
        return max(matches, key=lambda m: m.confidence)

    def get_folder_structure(self) -> List[str]:
        """Get standard folder structure."""
        folders = []
        for config in self.categories.values():
            if folder := config.get("folder"):
                folders.append(folder)
        return sorted(set(folders))

    def add_category(self, name: str, extensions: List[str],
                     patterns: List[str] = None, folder: str = None):
        """Add a custom file category."""
        self.categories[name] = {
            "extensions": extensions,
            "patterns": patterns or [],
            "folder": folder or name
        }
