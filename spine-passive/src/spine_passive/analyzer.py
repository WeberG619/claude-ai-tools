"""
Analyzer module for Spine Passive Learner.
Detects patterns from extracted Revit project data.
"""

import json
import logging
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional, Tuple
from statistics import mean, stdev

from .database import Database

logger = logging.getLogger(__name__)


class PatternAnalyzer:
    """Analyze extracted project data to learn patterns."""

    def __init__(self, db: Database):
        self.db = db

    def analyze_all(self) -> Dict[str, Any]:
        """Run all pattern analyses."""
        results = {}

        # Sheet organization patterns
        results["sheet_patterns"] = self.analyze_sheet_patterns()

        # Project size correlations
        results["size_patterns"] = self.analyze_size_patterns()

        # Family usage patterns
        results["family_patterns"] = self.analyze_family_usage()

        # View naming patterns
        results["view_patterns"] = self.analyze_view_patterns()

        # Room naming patterns
        results["room_patterns"] = self.analyze_room_patterns()

        # Wall type patterns
        results["wall_patterns"] = self.analyze_wall_patterns()

        return results

    def analyze_sheet_patterns(self) -> Dict:
        """Analyze sheet organization patterns across projects."""
        logger.info("Analyzing sheet organization patterns...")

        with self.db.connection() as conn:
            # Get all sheets with project info
            rows = conn.execute("""
                SELECT s.sheet_number, s.sheet_name, s.discipline, s.sheet_series,
                       p.filename, p.sheet_count
                FROM sheets s
                JOIN projects p ON s.project_id = p.id
                WHERE p.extraction_status = 'complete'
            """).fetchall()

        if not rows:
            return {"error": "No sheet data available"}

        # Analyze by discipline
        discipline_counts = Counter()
        discipline_sheets = defaultdict(list)

        # Analyze by series (what's typically in A100, A200, etc.)
        series_names = defaultdict(list)

        for row in rows:
            sheet_num = row["sheet_number"]
            sheet_name = row["sheet_name"]
            discipline = row["discipline"]
            series = row["sheet_series"]

            discipline_counts[discipline] += 1
            discipline_sheets[discipline].append(sheet_num)
            series_names[f"{discipline}{series}"].append(sheet_name)

        # Find common sheet name patterns per series
        series_patterns = {}
        for series_key, names in series_names.items():
            # Find most common words in sheet names for this series
            word_counts = Counter()
            for name in names:
                words = name.upper().split()
                word_counts.update(words)

            # Get top keywords
            common_words = [word for word, count in word_counts.most_common(5)
                           if count > len(names) * 0.3]  # Appears in 30%+ of sheets

            if common_words:
                series_patterns[series_key] = {
                    "typical_content": common_words,
                    "count": len(names),
                    "examples": names[:3]
                }

                # Store pattern in database
                self.db.upsert_pattern(
                    pattern_type="sheet_series",
                    pattern_key=series_key,
                    pattern_value={
                        "typical_content": common_words,
                        "example_names": names[:5]
                    },
                    confidence=min(1.0, len(names) / 10)  # More examples = higher confidence
                )

        # Overall discipline distribution
        discipline_dist = {d: c for d, c in discipline_counts.most_common()}

        return {
            "discipline_distribution": discipline_dist,
            "series_patterns": series_patterns,
            "total_sheets_analyzed": len(rows)
        }

    def analyze_size_patterns(self) -> Dict:
        """Analyze project size correlations (levels, sheets, rooms)."""
        logger.info("Analyzing project size patterns...")

        with self.db.connection() as conn:
            rows = conn.execute("""
                SELECT level_count, sheet_count, view_count, room_count,
                       project_name, building_type
                FROM projects
                WHERE extraction_status = 'complete'
                  AND sheet_count > 0
            """).fetchall()

        if len(rows) < 2:
            return {"error": "Not enough projects for size analysis"}

        # Categorize projects by size
        small = []    # 1-2 levels, <30 sheets
        medium = []   # 2-3 levels, 30-60 sheets
        large = []    # 3+ levels, 60+ sheets

        for row in rows:
            levels = row["level_count"] or 1
            sheets = row["sheet_count"] or 0

            project_data = {
                "levels": levels,
                "sheets": sheets,
                "views": row["view_count"] or 0,
                "rooms": row["room_count"] or 0,
                "name": row["project_name"]
            }

            if levels <= 2 and sheets < 30:
                small.append(project_data)
            elif levels <= 3 and sheets < 60:
                medium.append(project_data)
            else:
                large.append(project_data)

        def summarize_category(projects: List[Dict]) -> Dict:
            if not projects:
                return {}
            return {
                "count": len(projects),
                "avg_levels": round(mean(p["levels"] for p in projects), 1),
                "avg_sheets": round(mean(p["sheets"] for p in projects), 1),
                "avg_views": round(mean(p["views"] for p in projects), 1),
                "avg_rooms": round(mean(p["rooms"] for p in projects), 1),
                "sheet_range": (min(p["sheets"] for p in projects),
                               max(p["sheets"] for p in projects))
            }

        patterns = {
            "small_projects": summarize_category(small),
            "medium_projects": summarize_category(medium),
            "large_projects": summarize_category(large)
        }

        # Store patterns
        for size, data in patterns.items():
            if data:
                self.db.upsert_pattern(
                    pattern_type="project_size",
                    pattern_key=size,
                    pattern_value=data,
                    confidence=min(1.0, data["count"] / 5)
                )

        return {
            "size_categories": patterns,
            "total_analyzed": len(rows)
        }

    def analyze_family_usage(self) -> Dict:
        """Analyze which families are most commonly used."""
        logger.info("Analyzing family usage patterns...")

        families = self.db.get_all_families()
        if not families:
            return {"error": "No family data available"}

        # Get completed project count
        with self.db.connection() as conn:
            total_projects = conn.execute("""
                SELECT COUNT(*) FROM projects WHERE extraction_status = 'complete'
            """).fetchone()[0]

        # Categorize families
        standard = []  # Used in 60%+ of projects
        common = []    # Used in 30-60% of projects
        rare = []      # Used in <30% of projects

        for fam in families:
            name = fam["family_name"]
            category = fam["family_category"]
            project_count = fam["project_count"]
            usage_pct = (project_count / total_projects * 100) if total_projects > 0 else 0

            family_info = {
                "name": name,
                "category": category,
                "usage_percent": round(usage_pct, 1),
                "total_instances": fam["total_instances"]
            }

            if usage_pct >= 60:
                standard.append(family_info)
            elif usage_pct >= 30:
                common.append(family_info)
            else:
                rare.append(family_info)

        # Store standard families pattern
        if standard:
            self.db.upsert_pattern(
                pattern_type="family_usage",
                pattern_key="standard_families",
                pattern_value=[f["name"] for f in standard[:20]],
                confidence=0.9
            )

        # Group by category
        by_category = defaultdict(list)
        for fam in families:
            by_category[fam["family_category"]].append(fam["family_name"])

        return {
            "standard_families": standard[:20],  # Top 20
            "common_families": common[:20],
            "rare_family_count": len(rare),
            "by_category": {k: len(v) for k, v in by_category.items()},
            "total_unique_families": len(families)
        }

    def analyze_view_patterns(self) -> Dict:
        """Analyze view naming and organization patterns."""
        logger.info("Analyzing view patterns...")

        with self.db.connection() as conn:
            rows = conn.execute("""
                SELECT view_name, view_type, level_name, is_on_sheet
                FROM views v
                JOIN projects p ON v.project_id = p.id
                WHERE p.extraction_status = 'complete'
            """).fetchall()

        if not rows:
            return {"error": "No view data available"}

        # Count by type
        type_counts = Counter()
        on_sheet_by_type = defaultdict(lambda: {"on_sheet": 0, "not_on_sheet": 0})

        for row in rows:
            view_type = row["view_type"]
            type_counts[view_type] += 1

            if row["is_on_sheet"]:
                on_sheet_by_type[view_type]["on_sheet"] += 1
            else:
                on_sheet_by_type[view_type]["not_on_sheet"] += 1

        # Calculate typical views on sheets
        sheet_rates = {}
        for vtype, counts in on_sheet_by_type.items():
            total = counts["on_sheet"] + counts["not_on_sheet"]
            if total > 0:
                sheet_rates[vtype] = round(counts["on_sheet"] / total * 100, 1)

        # Store view type distribution
        self.db.upsert_pattern(
            pattern_type="view_distribution",
            pattern_key="by_type",
            pattern_value=dict(type_counts.most_common()),
            confidence=0.8
        )

        return {
            "view_type_distribution": dict(type_counts.most_common()),
            "sheet_placement_rates": sheet_rates,
            "total_views_analyzed": len(rows)
        }

    def analyze_room_patterns(self) -> Dict:
        """Analyze common room names and sizes."""
        logger.info("Analyzing room patterns...")

        with self.db.connection() as conn:
            rows = conn.execute("""
                SELECT room_name, area_sqft
                FROM rooms r
                JOIN projects p ON r.project_id = p.id
                WHERE p.extraction_status = 'complete'
                  AND room_name IS NOT NULL
                  AND room_name != ''
            """).fetchall()

        if not rows:
            return {"error": "No room data available"}

        # Count room names (normalized)
        room_counts = Counter()
        room_areas = defaultdict(list)

        for row in rows:
            name = row["room_name"].upper().strip()
            area = row["area_sqft"] or 0

            room_counts[name] += 1
            if area > 0:
                room_areas[name].append(area)

        # Calculate typical sizes for common rooms
        typical_sizes = {}
        for name, areas in room_areas.items():
            if len(areas) >= 3:  # Need at least 3 samples
                typical_sizes[name] = {
                    "avg_sqft": round(mean(areas), 0),
                    "min_sqft": round(min(areas), 0),
                    "max_sqft": round(max(areas), 0),
                    "count": len(areas)
                }

        # Store common room names
        common_rooms = [name for name, count in room_counts.most_common(30)]
        self.db.upsert_pattern(
            pattern_type="room_names",
            pattern_key="common_rooms",
            pattern_value=common_rooms,
            confidence=0.8
        )

        return {
            "common_room_names": dict(room_counts.most_common(20)),
            "typical_room_sizes": dict(sorted(
                typical_sizes.items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:15]),
            "total_rooms_analyzed": len(rows)
        }

    def analyze_wall_patterns(self) -> Dict:
        """Analyze wall type usage patterns."""
        logger.info("Analyzing wall type patterns...")

        with self.db.connection() as conn:
            rows = conn.execute("""
                SELECT wt.type_name, wt.wall_function, wt.width_inches, wt.instance_count
                FROM wall_types wt
                JOIN projects p ON wt.project_id = p.id
                WHERE p.extraction_status = 'complete'
            """).fetchall()

        if not rows:
            return {"error": "No wall type data available"}

        # Aggregate by type name
        type_usage = defaultdict(lambda: {"count": 0, "instances": 0, "widths": []})

        for row in rows:
            name = row["type_name"]
            type_usage[name]["count"] += 1
            type_usage[name]["instances"] += row["instance_count"] or 0
            if row["width_inches"]:
                type_usage[name]["widths"].append(row["width_inches"])

        # Most common wall types
        common_types = sorted(
            type_usage.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:20]

        # Store pattern
        self.db.upsert_pattern(
            pattern_type="wall_types",
            pattern_key="common_types",
            pattern_value=[t[0] for t in common_types],
            confidence=0.8
        )

        return {
            "common_wall_types": [
                {
                    "name": name,
                    "project_count": data["count"],
                    "total_instances": data["instances"]
                }
                for name, data in common_types
            ],
            "total_types_analyzed": len(type_usage)
        }

    def get_pattern_summary(self) -> str:
        """Generate a human-readable summary of learned patterns."""
        patterns = self.db.get_patterns()
        if not patterns:
            return "No patterns learned yet. Run extraction first."

        lines = ["# Spine Passive Learner - Pattern Summary\n"]

        # Group by type
        by_type = defaultdict(list)
        for p in patterns:
            by_type[p["pattern_type"]].append(p)

        # Sheet patterns
        if "sheet_series" in by_type:
            lines.append("## Sheet Organization")
            for p in by_type["sheet_series"][:10]:
                value = json.loads(p["pattern_value"]) if isinstance(p["pattern_value"], str) else p["pattern_value"]
                content = value.get("typical_content", [])
                lines.append(f"- **{p['pattern_key']}**: {', '.join(content[:3])}")
            lines.append("")

        # Project sizes
        if "project_size" in by_type:
            lines.append("## Project Size Patterns")
            for p in by_type["project_size"]:
                value = json.loads(p["pattern_value"]) if isinstance(p["pattern_value"], str) else p["pattern_value"]
                if isinstance(value, dict) and "avg_sheets" in value:
                    lines.append(f"- **{p['pattern_key'].replace('_', ' ').title()}**: "
                               f"~{value['avg_sheets']} sheets, {value['avg_levels']} levels")
            lines.append("")

        # Common families
        if "family_usage" in by_type:
            lines.append("## Standard Families (used in 60%+ of projects)")
            for p in by_type["family_usage"]:
                if p["pattern_key"] == "standard_families":
                    value = json.loads(p["pattern_value"]) if isinstance(p["pattern_value"], str) else p["pattern_value"]
                    for fam in value[:10]:
                        lines.append(f"- {fam}")
            lines.append("")

        # Common room names
        if "room_names" in by_type:
            lines.append("## Common Room Names")
            for p in by_type["room_names"]:
                value = json.loads(p["pattern_value"]) if isinstance(p["pattern_value"], str) else p["pattern_value"]
                lines.append(f"- {', '.join(value[:10])}")
            lines.append("")

        return "\n".join(lines)
