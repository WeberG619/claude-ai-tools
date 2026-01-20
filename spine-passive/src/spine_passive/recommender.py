"""
Recommender module for Spine Passive Learner.
Provides recommendations based on learned patterns.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from statistics import mean

from .database import Database
from .extractor import RevitExtractor

logger = logging.getLogger(__name__)


class ProjectRecommender:
    """Provide recommendations for new projects based on learned patterns."""

    def __init__(self, db: Database):
        self.db = db

    def analyze_new_project(self, project_data: Dict) -> Dict:
        """
        Analyze a new project and provide recommendations.

        Args:
            project_data: Dict with sheets, views, levels, rooms from current project

        Returns:
            Dict with analysis and recommendations
        """
        recommendations = {
            "phase_estimate": self._estimate_phase(project_data),
            "completion_estimate": self._estimate_completion(project_data),
            "similar_projects": self._find_similar_projects(project_data),
            "missing_sheets": self._identify_missing_sheets(project_data),
            "suggestions": []
        }

        # Add actionable suggestions
        self._add_suggestions(recommendations, project_data)

        return recommendations

    def _estimate_phase(self, project_data: Dict) -> Dict:
        """Estimate project phase based on sheet count and content."""
        sheet_count = project_data.get("sheet_count", 0)
        level_count = project_data.get("level_count", 1)

        # Get learned patterns
        size_patterns = self.db.get_patterns("project_size")
        if not size_patterns:
            return {"phase": "Unknown", "confidence": 0}

        # Simple heuristic based on sheet count
        if sheet_count == 0:
            return {"phase": "Pre-Design", "confidence": 0.8}
        elif sheet_count < 10:
            return {"phase": "Schematic Design (SD)", "confidence": 0.7}
        elif sheet_count < 25:
            return {"phase": "Design Development (DD)", "confidence": 0.7}
        elif sheet_count < 50:
            return {"phase": "Construction Documents (CD) - Early", "confidence": 0.6}
        else:
            return {"phase": "Construction Documents (CD) - Complete", "confidence": 0.7}

    def _estimate_completion(self, project_data: Dict) -> Dict:
        """Estimate completion percentage based on typical CD set size."""
        sheet_count = project_data.get("sheet_count", 0)
        level_count = project_data.get("level_count", 1)

        # Get typical sheet counts from learned patterns
        size_patterns = {
            p["pattern_key"]: json.loads(p["pattern_value"]) if isinstance(p["pattern_value"], str) else p["pattern_value"]
            for p in self.db.get_patterns("project_size")
        }

        # Estimate target based on levels
        if level_count <= 2:
            target_key = "small_projects"
        elif level_count <= 3:
            target_key = "medium_projects"
        else:
            target_key = "large_projects"

        target_data = size_patterns.get(target_key, {})
        target_sheets = target_data.get("avg_sheets", 40)  # Default

        if target_sheets > 0:
            completion_pct = min(100, round(sheet_count / target_sheets * 100, 1))
        else:
            completion_pct = 0

        return {
            "completion_percent": completion_pct,
            "current_sheets": sheet_count,
            "typical_sheets": target_sheets,
            "sheets_remaining": max(0, target_sheets - sheet_count)
        }

    def _find_similar_projects(self, project_data: Dict) -> List[Dict]:
        """Find similar completed projects for reference."""
        level_count = project_data.get("level_count", 1)
        sheet_count = project_data.get("sheet_count", 0)

        with self.db.connection() as conn:
            # Find projects with similar level count
            rows = conn.execute("""
                SELECT project_name, filename, level_count, sheet_count,
                       view_count, room_count
                FROM projects
                WHERE extraction_status = 'complete'
                  AND level_count BETWEEN ? AND ?
                ORDER BY ABS(sheet_count - ?) ASC
                LIMIT 5
            """, (max(1, level_count - 1), level_count + 1, sheet_count)).fetchall()

        return [
            {
                "name": row["project_name"] or row["filename"],
                "levels": row["level_count"],
                "sheets": row["sheet_count"],
                "views": row["view_count"],
                "rooms": row["room_count"]
            }
            for row in rows
        ]

    def _identify_missing_sheets(self, project_data: Dict) -> List[Dict]:
        """Identify potentially missing sheet series based on patterns."""
        current_sheets = project_data.get("sheets", [])
        if not current_sheets:
            return []

        # Get current disciplines and series
        current_series = set()
        for sheet in current_sheets:
            num = sheet.get("sheet_number", "")
            if len(num) >= 2:
                # Get first letter and first digit
                disc = num[0].upper() if num[0].isalpha() else ""
                for char in num:
                    if char.isdigit():
                        series = f"{disc}{char}00"
                        current_series.add(series)
                        break

        # Get typical series from patterns
        series_patterns = self.db.get_patterns("sheet_series")
        typical_series = set()
        for p in series_patterns:
            if p["occurrence_count"] >= 3:  # Appears in at least 3 projects
                typical_series.add(p["pattern_key"])

        # Find missing
        missing = typical_series - current_series

        # Get descriptions for missing
        missing_info = []
        for series in sorted(missing):
            pattern = next((p for p in series_patterns if p["pattern_key"] == series), None)
            if pattern:
                value = json.loads(pattern["pattern_value"]) if isinstance(pattern["pattern_value"], str) else pattern["pattern_value"]
                missing_info.append({
                    "series": series,
                    "typical_content": value.get("typical_content", []),
                    "common_in_projects": pattern["occurrence_count"]
                })

        return missing_info

    def _add_suggestions(self, recommendations: Dict, project_data: Dict) -> None:
        """Add actionable suggestions based on analysis."""
        suggestions = []

        # Phase-based suggestions
        phase = recommendations["phase_estimate"].get("phase", "")
        if "SD" in phase:
            suggestions.append("Consider adding more floor plans and basic elevations for DD phase")
        elif "DD" in phase:
            suggestions.append("Start adding detail sheets and enlarged plans for CD phase")
            suggestions.append("Consider adding door/window schedules if not present")

        # Completion-based suggestions
        completion = recommendations["completion_estimate"]
        remaining = completion.get("sheets_remaining", 0)
        if remaining > 0:
            suggestions.append(f"Approximately {remaining} more sheets typical for complete CD set")

        # Missing sheets suggestions
        missing = recommendations["missing_sheets"]
        if missing:
            for m in missing[:3]:  # Top 3
                content = ", ".join(m["typical_content"][:2]) if m["typical_content"] else "various content"
                suggestions.append(f"Consider adding {m['series']} series ({content})")

        # Similar project insights
        similar = recommendations["similar_projects"]
        if similar:
            avg_sheets = mean([p["sheets"] for p in similar])
            suggestions.append(f"Similar projects average {round(avg_sheets)} sheets")

        recommendations["suggestions"] = suggestions

    def get_quick_summary(self, project_data: Dict) -> str:
        """Generate a quick one-paragraph summary."""
        analysis = self.analyze_new_project(project_data)

        phase = analysis["phase_estimate"]["phase"]
        completion = analysis["completion_estimate"]["completion_percent"]
        remaining = analysis["completion_estimate"]["sheets_remaining"]

        summary = f"This project appears to be in **{phase}** phase, "
        summary += f"approximately **{completion}%** complete. "

        if remaining > 0:
            summary += f"Typically need ~{remaining} more sheets for a complete CD set. "

        similar = analysis["similar_projects"]
        if similar:
            best_match = similar[0]
            summary += f"Most similar completed project: {best_match['name']} ({best_match['sheets']} sheets)."

        return summary


def export_to_json(db: Database, output_path: str) -> Dict:
    """Export all patterns to a JSON file."""
    patterns = db.get_patterns()
    stats = db.get_stats()

    export_data = {
        "generated_at": str(datetime.now()),
        "stats": stats,
        "patterns": {}
    }

    # Group patterns by type
    for p in patterns:
        ptype = p["pattern_type"]
        if ptype not in export_data["patterns"]:
            export_data["patterns"][ptype] = []

        value = p["pattern_value"]
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass

        export_data["patterns"][ptype].append({
            "key": p["pattern_key"],
            "value": value,
            "occurrences": p["occurrence_count"],
            "confidence": p["confidence"]
        })

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(export_data, f, indent=2, default=str)

    return {"success": True, "path": str(output), "pattern_count": len(patterns)}


# Import for export_to_json
from datetime import datetime
