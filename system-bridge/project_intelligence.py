#!/usr/bin/env python3
"""
Project Intelligence Engine
Provides proactive intelligence by:
1. Correlating open files/apps to known projects
2. Detecting project context switches
3. Predicting user intent based on patterns
4. Alerting to mismatches and anomalies

This is Claude's "brain" for understanding what you're working on.
"""

import json
import sqlite3
import re
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

# Paths
MEMORY_DB = Path(r"D:\_CLAUDE-TOOLS\claude-memory-server\data\memories.db")
STATE_FILE = Path(r"D:\_CLAUDE-TOOLS\system-bridge\live_state.json")
INTELLIGENCE_FILE = Path(r"D:\_CLAUDE-TOOLS\system-bridge\intelligence.json")
PATTERNS_FILE = Path(r"D:\_CLAUDE-TOOLS\system-bridge\learned_patterns.json")


@dataclass
class ProjectContext:
    """Represents the current project context."""
    project_name: str
    confidence: float  # 0-1
    sources: List[str]  # What indicated this project
    related_files: List[str]
    last_memories: List[Dict]
    unfinished_tasks: List[str]
    corrections: List[str]
    suggested_actions: List[str]
    mismatches: List[str]


@dataclass
class WorkflowPattern:
    """A learned pattern of user behavior."""
    trigger: str  # What triggers this pattern
    typical_sequence: List[str]  # What usually follows
    frequency: int  # How often seen
    last_seen: str


class ProjectCorrelator:
    """Correlates files and applications to projects."""

    def __init__(self):
        self.project_patterns = self._load_project_patterns()

    def _load_project_patterns(self) -> Dict:
        """Load known project name patterns."""
        # These patterns help identify projects from file/window names
        # Auto-populated from D:\001 - PROJECTS\01 - CLIENT PROJECTS\01 - ARKY\
        return {
            # Pattern: (regex, project_name, confidence_boost)
            "south_golf_cove": {
                "patterns": [r"south.?golf.?cove", r"sgc[_\-\s]", r"golf.?cove.?residence"],
                "aliases": ["SGC", "South Golf Cove", "Golf Cove"],
                "revit_models": ["South Golf Cove"],
                "typical_files": ["Interior Design Package", "CD Set"],
                "path": None,
            },
            "ap_builder": {
                "patterns": [r"ap.?builder", r"avon.?park"],
                "aliases": ["AP Builder", "Avon Park", "AP"],
                "revit_models": ["AP Builder Residence"],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\012-Avon Park Single Family",
            },
            "512_clematis": {
                "patterns": [r"512.?clematis", r"clematis.?512"],
                "aliases": ["512 Clematis", "Clematis"],
                "revit_models": ["512_CLEMATIS"],
                "typical_files": [],
                "path": None,
            },
            # ARKY Client Projects - populated from actual directory structure
            "pierr_torres": {
                "patterns": [r"pierr.?torres", r"torres.?addition"],
                "aliases": ["Pierr Torres", "Torres Addition"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\003-Pierr Torres Addition",
            },
            "ne_137th_north_miami": {
                "patterns": [r"851.*137th", r"137th.*street.*north.?miami"],
                "aliases": ["851 NE 137th", "North Miami"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\004-851 N.E. 137th Street North Miami FL 33161",
            },
            "church_project": {
                "patterns": [r"church.?project", r"005.?church"],
                "aliases": ["Church Project", "Church"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\005-Church Project",
            },
            "dania_beach": {
                "patterns": [r"114.*5th.*ct.*dania", r"dania.?beach"],
                "aliases": ["114 SW 5th Ct", "Dania Beach"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\006-114 SW 5th Ct Dania Bch",
            },
            "west_park": {
                "patterns": [r"3821.*32.*ave.*west.?park", r"west.?park"],
                "aliases": ["3821 SW 32 Ave", "West Park"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\007-3821 SW 32 Ave West Park FL",
            },
            "lehigh_acres": {
                "patterns": [r"lehigh.?acres", r"model.?4a1"],
                "aliases": ["Lehigh Acres", "Model 4a1"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\008-Lehigh Acres Model 4a1- SF",
            },
            "allen_street": {
                "patterns": [r"6761.*allen", r"allen.?st"],
                "aliases": ["6761 Allen St", "Allen Street"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\009-6761 Allen St",
            },
            "nw_76th_miami_4story": {
                "patterns": [r"20.*nw.*76.*street", r"76th.*4.*story", r"miami.*4.*story"],
                "aliases": ["20 NW 76 Street", "4 Story Building Miami"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\010-20 NW 76 Street Miami - New 4 Story Building",
            },
            "atlanta_street_hollywood": {
                "patterns": [r"2222.*atlanta", r"atlanta.*hollywood"],
                "aliases": ["2222 Atlanta Street", "Hollywood"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\011-2222 Atlanta Street Hollywood FL",
            },
            "north_lauderdale": {
                "patterns": [r"6851.*7.*ct.*north.*lauderdale", r"north.?lauderdale"],
                "aliases": ["6851 SW 7Ct", "North Lauderdale"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\013-6851 S.W. 7Ct. North Lauderdale FL",
            },
            "okeechobee_hotel": {
                "patterns": [r"699.*okeechobee", r"hialeah.*hotel"],
                "aliases": ["699 Okeechobee", "Hialeah Hotel"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\014-699 Okeechobee Road Hialeah FL - Hotel",
            },
            "nw_33rd_miami": {
                "patterns": [r"1501.*nw.*33", r"33.*street.*miami.*33142"],
                "aliases": ["1501 NW 33 Street", "Miami 33142"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\016-1501 NW 33 Street Miami FL 33142",
            },
            "site_plan_design": {
                "patterns": [r"site.?plan.?design", r"017.*site"],
                "aliases": ["Site Plan Design"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\017- Site Plan Design",
            },
            "ft_lauderdale_carport": {
                "patterns": [r"1455.*18.*terr.*fort.?lauderdale", r"carport.*enclosure"],
                "aliases": ["1455 SW 18th Terr", "Fort Lauderdale Carport"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\1455 SW 18th Terr. Fort Lauderdale FL - Carport enclosure",
            },
            "pompano_wood_frame": {
                "patterns": [r"1584.*31.*st.*pompano", r"pompano.*wood.?frame"],
                "aliases": ["1584 NE 31st St", "Pompano Beach Wood Frame"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\001 - PROJECTS\\01 - CLIENT PROJECTS\\01 - ARKY\\1584 NE 31st St. Pompano Beach FL - Wood Frame",
            },
            # General projects
            "revitmcpbridge": {
                "patterns": [r"revitmcpbridge", r"mcp.?bridge"],
                "aliases": ["RevitMCPBridge", "MCP Bridge", "Revit MCP"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\RevitMCPBridge2026",
            },
            "bim_ops_studio": {
                "patterns": [r"bim.?ops", r"bimops"],
                "aliases": ["BIM Ops Studio", "BIM Ops"],
                "revit_models": [],
                "typical_files": [],
                "path": "D:\\BIM_Ops_Studio",
            },
        }

    def identify_project(self, text: str) -> Tuple[Optional[str], float]:
        """Identify project from text (filename, window title, etc.)."""
        text_lower = text.lower()

        for project_id, config in self.project_patterns.items():
            for pattern in config["patterns"]:
                if re.search(pattern, text_lower):
                    return project_id, 0.9

            for alias in config.get("aliases", []):
                if alias.lower() in text_lower:
                    return project_id, 0.8

        return None, 0.0

    def correlate_from_state(self, state: Dict) -> Dict[str, List[Tuple[str, float]]]:
        """Analyze system state and identify projects from all sources."""
        findings = defaultdict(list)

        # Check Revit
        revit = state.get("revit", {})
        if revit.get("connected"):
            doc = revit.get("document", "")
            project, conf = self.identify_project(doc)
            if project:
                findings[project].append(("revit", conf))

        # Check Bluebeam
        bluebeam = state.get("bluebeam", {})
        if bluebeam.get("running"):
            doc = bluebeam.get("document", "")
            project, conf = self.identify_project(doc)
            if project:
                findings[project].append(("bluebeam", conf))

        # Check all open applications
        for app in state.get("applications", []):
            title = app.get("MainWindowTitle", "")
            process = app.get("ProcessName", "")

            # Skip system apps
            if process.lower() in ["explorer", "applicationframehost", "systemsettings"]:
                continue

            project, conf = self.identify_project(title)
            if project:
                findings[project].append((f"{process}:{title[:50]}", conf))

        return dict(findings)


class MemoryLoader:
    """Loads relevant memories for a project context."""

    def __init__(self):
        self.db_path = MEMORY_DB

    def get_project_context(self, project_name: str) -> Dict:
        """Get all relevant context for a project."""
        if not self.db_path.exists():
            return {}

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        context = {
            "recent_memories": [],
            "corrections": [],
            "unfinished_tasks": [],
            "decisions": [],
        }

        # Map project_id to database project names
        project_mappings = {
            "south_golf_cove": ["South Golf Cove", "SGC"],
            "ap_builder": ["AP Builder", "RevitMCPBridge2026"],  # Often tested with this
            "512_clematis": ["512 Clematis", "Clematis"],
        }

        search_names = project_mappings.get(project_name, [project_name])

        for name in search_names:
            # Recent memories
            cursor.execute("""
                SELECT content, memory_type, importance, created_at
                FROM memories
                WHERE project = ? OR content LIKE ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (name, f"%{name}%"))

            for row in cursor.fetchall():
                context["recent_memories"].append({
                    "content": row["content"][:300],
                    "type": row["memory_type"],
                    "importance": row["importance"],
                    "created": row["created_at"]
                })

            # Corrections
            cursor.execute("""
                SELECT content FROM memories
                WHERE memory_type = 'error'
                AND tags LIKE '%correction%'
                AND (project = ? OR content LIKE ?)
                ORDER BY created_at DESC
                LIMIT 5
            """, (name, f"%{name}%"))

            for row in cursor.fetchall():
                # Extract the "Correct Approach" section
                content = row["content"]
                if "### Correct Approach:" in content:
                    approach = content.split("### Correct Approach:")[1]
                    approach = approach.split("**Category**")[0].strip()
                    context["corrections"].append(approach[:200])

            # Unfinished tasks (from session summaries)
            cursor.execute("""
                SELECT content FROM memories
                WHERE tags LIKE '%session-summary%'
                AND content LIKE '%### Next Steps%'
                AND (project = ? OR content LIKE ?)
                ORDER BY created_at DESC
                LIMIT 3
            """, (name, f"%{name}%"))

            for row in cursor.fetchall():
                content = row["content"]
                if "### Next Steps" in content:
                    steps_section = content.split("### Next Steps")[1]
                    steps = [s.strip() for s in steps_section.split('\n')
                            if s.strip().startswith('-')]
                    context["unfinished_tasks"].extend(steps[:3])

            # Recent decisions
            cursor.execute("""
                SELECT content FROM memories
                WHERE memory_type = 'decision'
                AND (project = ? OR content LIKE ?)
                ORDER BY created_at DESC
                LIMIT 5
            """, (name, f"%{name}%"))

            for row in cursor.fetchall():
                context["decisions"].append(row["content"][:150])

        conn.close()
        return context


class IntentPredictor:
    """Predicts user intent based on current state and learned patterns."""

    def __init__(self):
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> Dict:
        """Load learned workflow patterns."""
        if PATTERNS_FILE.exists():
            with open(PATTERNS_FILE) as f:
                return json.load(f)
        return {"workflows": [], "sequences": {}}

    def _save_patterns(self):
        """Save learned patterns."""
        with open(PATTERNS_FILE, 'w') as f:
            json.dump(self.patterns, f, indent=2)

    def learn_sequence(self, actions: List[str]):
        """Learn from a sequence of actions."""
        if len(actions) < 2:
            return

        for i in range(len(actions) - 1):
            trigger = actions[i]
            followup = actions[i + 1]

            if trigger not in self.patterns["sequences"]:
                self.patterns["sequences"][trigger] = {}

            if followup not in self.patterns["sequences"][trigger]:
                self.patterns["sequences"][trigger][followup] = 0

            self.patterns["sequences"][trigger][followup] += 1

        self._save_patterns()

    def predict_next_actions(self, current_state: Dict, project: str) -> List[str]:
        """Predict likely next actions based on current state."""
        predictions = []

        # Check Revit state
        revit = current_state.get("revit", {})
        if revit.get("connected"):
            view_type = revit.get("viewType", "")
            view_name = revit.get("viewName", "")

            if "FloorPlan" in view_type:
                predictions.append("User may want to: Add dimensions, place doors/windows, or tag rooms")
            elif "Elevation" in view_type:
                predictions.append("User may want to: Add annotations, check heights, review materials")
            elif "Section" in view_type:
                predictions.append("User may want to: Detail wall assemblies, add dimensions")
            elif "Schedule" in view_type:
                predictions.append("User may want to: Export data, verify counts, update parameters")

            if "SECOND FLOOR" in view_name.upper():
                predictions.append("Working on upper level - may need to check stair alignment")

        # Check Bluebeam state
        bluebeam = current_state.get("bluebeam", {})
        if bluebeam.get("running"):
            doc = bluebeam.get("document", "").lower()
            if "interior" in doc:
                predictions.append("Reviewing interior design - may need to update Revit finishes")
            elif "cd" in doc or "construction" in doc:
                predictions.append("Reviewing CDs - may need to make corrections in Revit")

        # Check for project mismatch
        # This is handled separately in detect_mismatches

        return predictions

    def detect_mismatches(self, correlations: Dict) -> List[str]:
        """Detect when user might be working on wrong project."""
        mismatches = []

        if len(correlations) > 1:
            projects = list(correlations.keys())
            sources_by_project = {p: [s[0] for s in sources]
                                  for p, sources in correlations.items()}

            # Check if Revit and Bluebeam show different projects
            revit_projects = [p for p, sources in sources_by_project.items()
                            if any("revit" in s for s in sources)]
            bluebeam_projects = [p for p, sources in sources_by_project.items()
                                if any("bluebeam" in s for s in sources)]

            if revit_projects and bluebeam_projects:
                if set(revit_projects) != set(bluebeam_projects):
                    mismatches.append(
                        f"PROJECT MISMATCH: Revit has {revit_projects[0]} open, "
                        f"but Bluebeam shows {bluebeam_projects[0]}. "
                        f"Are you working on the right model?"
                    )

        return mismatches


class ActionSuggester:
    """Suggests actions based on context."""

    def suggest_actions(self, context: ProjectContext) -> List[str]:
        """Generate suggested actions for current context."""
        suggestions = []

        # If there are unfinished tasks, suggest continuing them
        if context.unfinished_tasks:
            suggestions.append(f"CONTINUE: {context.unfinished_tasks[0]}")

        # If there are corrections, remind about them
        if context.corrections:
            suggestions.append(f"REMEMBER: {context.corrections[0][:100]}...")

        # If there are mismatches, prioritize fixing them
        if context.mismatches:
            suggestions.insert(0, f"FIX: {context.mismatches[0]}")

        return suggestions


class ProjectIntelligence:
    """Main intelligence engine that ties everything together."""

    def __init__(self):
        self.correlator = ProjectCorrelator()
        self.memory_loader = MemoryLoader()
        self.predictor = IntentPredictor()
        self.suggester = ActionSuggester()

    def analyze(self, state: Dict = None) -> ProjectContext:
        """Analyze current state and return full project context."""
        # Load state if not provided
        if state is None:
            if STATE_FILE.exists():
                with open(STATE_FILE) as f:
                    state = json.load(f)
            else:
                state = {}

        # Correlate to projects
        correlations = self.correlator.correlate_from_state(state)

        # Determine primary project
        if correlations:
            # Pick project with most sources and highest confidence
            primary = max(correlations.items(),
                         key=lambda x: sum(c for _, c in x[1]))
            project_name = primary[0]
            confidence = sum(c for _, c in primary[1]) / len(primary[1])
            sources = [s for s, _ in primary[1]]
        else:
            project_name = "unknown"
            confidence = 0.0
            sources = []

        # Load memory context
        memory_context = self.memory_loader.get_project_context(project_name)

        # Detect mismatches
        mismatches = self.predictor.detect_mismatches(correlations)

        # Predict intent
        predictions = self.predictor.predict_next_actions(state, project_name)

        # Build context object
        context = ProjectContext(
            project_name=project_name,
            confidence=confidence,
            sources=sources,
            related_files=[],
            last_memories=memory_context.get("recent_memories", []),
            unfinished_tasks=memory_context.get("unfinished_tasks", []),
            corrections=memory_context.get("corrections", []),
            suggested_actions=predictions,
            mismatches=mismatches,
        )

        # Generate action suggestions
        context.suggested_actions.extend(self.suggester.suggest_actions(context))

        # Save intelligence output
        self._save_intelligence(context)

        return context

    def _save_intelligence(self, context: ProjectContext):
        """Save intelligence output to file."""
        output = asdict(context)
        output["generated_at"] = datetime.now().isoformat()

        with open(INTELLIGENCE_FILE, 'w') as f:
            json.dump(output, f, indent=2)

    def get_briefing(self) -> str:
        """Generate a human-readable briefing."""
        context = self.analyze()

        lines = []
        lines.append("=" * 60)
        lines.append(" PROJECT INTELLIGENCE BRIEFING")
        lines.append("=" * 60)
        lines.append(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Primary project
        lines.append(f"## DETECTED PROJECT: {context.project_name.upper()}")
        lines.append(f"   Confidence: {context.confidence:.0%}")
        lines.append(f"   Sources: {', '.join(context.sources)}")
        lines.append("")

        # Mismatches (HIGH PRIORITY)
        if context.mismatches:
            lines.append("## [!] MISMATCHES DETECTED")
            for mismatch in context.mismatches:
                lines.append(f"   {mismatch}")
            lines.append("")

        # Corrections to remember
        if context.corrections:
            lines.append("## CORRECTIONS TO REMEMBER")
            for corr in context.corrections[:3]:
                lines.append(f"   > {corr}")
            lines.append("")

        # Unfinished work
        if context.unfinished_tasks:
            lines.append("## UNFINISHED TASKS")
            for task in context.unfinished_tasks[:5]:
                lines.append(f"   {task}")
            lines.append("")

        # Suggested actions
        if context.suggested_actions:
            lines.append("## SUGGESTED ACTIONS")
            for action in context.suggested_actions[:5]:
                lines.append(f"   - {action}")
            lines.append("")

        # Recent context
        if context.last_memories:
            lines.append("## RECENT CONTEXT")
            for mem in context.last_memories[:3]:
                lines.append(f"   [{mem['type']}] {mem['content'][:100]}...")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)


def main():
    """CLI interface."""
    import sys

    intel = ProjectIntelligence()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "analyze":
            context = intel.analyze()
            print(json.dumps(asdict(context), indent=2))

        elif cmd == "briefing":
            print(intel.get_briefing())

        elif cmd == "project":
            context = intel.analyze()
            print(f"Detected: {context.project_name} ({context.confidence:.0%})")

        elif cmd == "mismatches":
            context = intel.analyze()
            if context.mismatches:
                for m in context.mismatches:
                    print(m)
            else:
                print("No mismatches detected")

        else:
            print(f"Unknown command: {cmd}")
            print("Commands: analyze, briefing, project, mismatches")
    else:
        # Default: print briefing
        print(intel.get_briefing())


if __name__ == "__main__":
    main()
