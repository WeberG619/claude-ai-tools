#!/usr/bin/env python3
"""
Intelligent Operation Cache

Caches successful operation patterns for reuse.
Learns viewport layouts, wall placement patterns, and other repeatable operations.

Features:
1. Pattern matching for similar operations
2. Template storage and retrieval
3. Similarity scoring
4. Auto-apply for high-confidence matches
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

CACHE_DIR = Path("/mnt/d/_CLAUDE-TOOLS/operation-cache/cache")
TEMPLATES_FILE = CACHE_DIR / "templates.json"


class OperationCache:
    """Caches and retrieves operation patterns."""

    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict:
        """Load saved templates."""
        if TEMPLATES_FILE.exists():
            try:
                with open(TEMPLATES_FILE) as f:
                    return json.load(f)
            except:
                pass
        return {"viewport_layouts": [], "wall_patterns": [], "element_placements": []}

    def _save_templates(self):
        """Save templates to file."""
        with open(TEMPLATES_FILE, 'w') as f:
            json.dump(self.templates, f, indent=2)

    def _compute_hash(self, data: Dict) -> str:
        """Compute hash for data comparison."""
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]

    # =========================================================================
    # Viewport Layout Caching
    # =========================================================================

    def cache_viewport_layout(self, layout: Dict, name: str = None):
        """
        Cache a successful viewport layout.

        layout: {
            "sheet_size": [width, height],
            "viewports": [{"view_name": str, "x": float, "y": float, "width": float, "height": float}]
        }
        """
        template = {
            "id": self._compute_hash(layout),
            "name": name or f"Layout_{len(self.templates['viewport_layouts'])+1}",
            "created_at": datetime.now().isoformat(),
            "use_count": 0,
            "layout": layout
        }

        # Check for duplicates
        existing_ids = {t["id"] for t in self.templates["viewport_layouts"]}
        if template["id"] not in existing_ids:
            self.templates["viewport_layouts"].append(template)
            self._save_templates()
            return template
        return None

    def find_similar_layout(self, target: Dict, threshold: float = 0.8) -> Optional[Dict]:
        """Find a cached layout similar to target."""
        target_count = len(target.get("viewports", []))
        target_size = target.get("sheet_size", [2.83, 2.17])  # Default arch D

        for template in self.templates["viewport_layouts"]:
            layout = template["layout"]
            layout_count = len(layout.get("viewports", []))
            layout_size = layout.get("sheet_size", [2.83, 2.17])

            # Simple similarity: viewport count and sheet size
            count_sim = 1 - abs(target_count - layout_count) / max(target_count, layout_count, 1)
            size_sim = 1 - (abs(target_size[0] - layout_size[0]) + abs(target_size[1] - layout_size[1])) / 10

            similarity = (count_sim + size_sim) / 2

            if similarity >= threshold:
                return {
                    "template": template,
                    "similarity": similarity
                }

        return None

    def apply_layout_template(self, template_id: str) -> Optional[Dict]:
        """Get a layout template by ID for application."""
        for template in self.templates["viewport_layouts"]:
            if template["id"] == template_id:
                template["use_count"] += 1
                self._save_templates()
                return template["layout"]
        return None

    # =========================================================================
    # Wall Pattern Caching
    # =========================================================================

    def cache_wall_pattern(self, walls: List[Dict], name: str = None):
        """
        Cache a successful wall placement pattern.

        walls: [{"start": [x,y,z], "end": [x,y,z], "type": str}]
        """
        # Normalize to relative coordinates
        if not walls:
            return None

        min_x = min(min(w["start"][0], w["end"][0]) for w in walls)
        min_y = min(min(w["start"][1], w["end"][1]) for w in walls)

        normalized = []
        for wall in walls:
            normalized.append({
                "start": [wall["start"][0] - min_x, wall["start"][1] - min_y],
                "end": [wall["end"][0] - min_x, wall["end"][1] - min_y],
                "type": wall.get("type", "default")
            })

        template = {
            "id": self._compute_hash({"walls": normalized}),
            "name": name or f"WallPattern_{len(self.templates['wall_patterns'])+1}",
            "created_at": datetime.now().isoformat(),
            "use_count": 0,
            "wall_count": len(walls),
            "normalized_walls": normalized
        }

        existing_ids = {t["id"] for t in self.templates["wall_patterns"]}
        if template["id"] not in existing_ids:
            self.templates["wall_patterns"].append(template)
            self._save_templates()
            return template
        return None

    # =========================================================================
    # Generic Operation Caching
    # =========================================================================

    def cache_operation(self, category: str, operation: Dict, name: str = None):
        """Cache any successful operation."""
        if category not in self.templates:
            self.templates[category] = []

        template = {
            "id": self._compute_hash(operation),
            "name": name or f"{category}_{len(self.templates[category])+1}",
            "created_at": datetime.now().isoformat(),
            "use_count": 0,
            "operation": operation
        }

        existing_ids = {t["id"] for t in self.templates[category]}
        if template["id"] not in existing_ids:
            self.templates[category].append(template)
            self._save_templates()
            return template
        return None

    def list_templates(self, category: str = None) -> Dict:
        """List all cached templates."""
        if category:
            return {category: self.templates.get(category, [])}
        return self.templates

    def get_most_used(self, category: str, limit: int = 5) -> List[Dict]:
        """Get most frequently used templates in a category."""
        templates = self.templates.get(category, [])
        sorted_templates = sorted(templates, key=lambda x: x.get("use_count", 0), reverse=True)
        return sorted_templates[:limit]


def main():
    """CLI entry point."""
    import sys

    cache = OperationCache()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            category = sys.argv[2] if len(sys.argv) > 2 else None
            templates = cache.list_templates(category)
            print(json.dumps(templates, indent=2, default=str))

        elif sys.argv[1] == "--popular":
            category = sys.argv[2] if len(sys.argv) > 2 else "viewport_layouts"
            popular = cache.get_most_used(category)
            for t in popular:
                print(f"{t['name']} (used {t['use_count']} times)")
    else:
        print("Usage:")
        print("  operation_cache.py --list [category]    # List templates")
        print("  operation_cache.py --popular [category] # Most used templates")


if __name__ == "__main__":
    main()
