#!/usr/bin/env python3
"""
Context Loader - Auto-load knowledge and methods based on project type.
Called by session_start.py to inject relevant context.
"""
import json
import re
from pathlib import Path
from typing import Optional

# Paths - support both Windows and WSL
import os
if os.name == 'nt':
    # Windows paths
    ORCHESTRATION_DIR = Path(r"D:\_CLAUDE-TOOLS\orchestration")
    KNOWLEDGE_BASE = Path(r"D:\RevitMCPBridge2026\knowledge")
    LIVE_STATE = Path(r"D:\_CLAUDE-TOOLS\system-bridge\live_state.json")
else:
    # WSL paths
    ORCHESTRATION_DIR = Path("/mnt/d/_CLAUDE-TOOLS/orchestration")
    KNOWLEDGE_BASE = Path("/mnt/d/RevitMCPBridge2026/knowledge")
    LIVE_STATE = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")

METHODS_INDEX = ORCHESTRATION_DIR / "methods-index.json"
KNOWLEDGE_TRIGGERS = ORCHESTRATION_DIR / "knowledge-triggers.yaml"


def load_yaml_simple(path: Path) -> dict:
    """Simple YAML loader without external dependencies."""
    if not path.exists():
        return {}

    content = path.read_text(encoding='utf-8')
    result = {"project_patterns": [], "task_patterns": [], "defaults": []}

    current_section = None
    current_item = None

    for line in content.split('\n'):
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue

        # Detect section headers
        if stripped.startswith('project_patterns:'):
            current_section = 'project_patterns'
            continue
        elif stripped.startswith('task_patterns:'):
            current_section = 'task_patterns'
            continue
        elif stripped.startswith('defaults:'):
            current_section = 'defaults'
            continue
        elif stripped.startswith('memory:'):
            current_section = 'memory'
            continue

        # Parse items
        if current_section == 'defaults':
            if stripped.startswith('- '):
                result['defaults'].append(stripped[2:].strip())
        elif current_section in ['project_patterns', 'task_patterns']:
            if stripped.startswith('- pattern:'):
                # New pattern entry
                pattern = stripped.split(':', 1)[1].strip().strip('"').strip("'")
                current_item = {"pattern": pattern, "load": [], "context": "", "priority": 1}
                result[current_section].append(current_item)
            elif current_item:
                if stripped.startswith('priority:'):
                    current_item['priority'] = int(stripped.split(':', 1)[1].strip())
                elif stripped.startswith('context:'):
                    current_item['context'] = stripped.split(':', 1)[1].strip().strip('"').strip("'")
                elif stripped.startswith('- ') and not stripped.startswith('- pattern'):
                    # Load item
                    current_item['load'].append(stripped[2:].strip())

    return result


def detect_project_type(live_state: dict) -> Optional[str]:
    """Extract project name from Revit window title."""
    apps = live_state.get("applications", [])

    for app in apps:
        if app.get("ProcessName") == "Revit":
            title = app.get("MainWindowTitle", "")
            # Pattern: "Autodesk Revit 2026.2 - [PROJECT NAME - View: ...]"
            match = re.search(r'\[([^\]]+)\s*-', title)
            if match:
                return match.group(1).strip()

    return None


def match_patterns(project_name: str, triggers: dict) -> dict:
    """Match project name against patterns and return relevant files."""
    result = {
        "knowledge_files": list(triggers.get("defaults", [])),
        "context_hints": [],
        "matched_patterns": []
    }

    if not project_name:
        return result

    project_upper = project_name.upper()

    # Check project patterns
    for pattern_info in triggers.get("project_patterns", []):
        pattern = pattern_info.get("pattern", "")
        if re.search(pattern, project_upper):
            result["matched_patterns"].append(pattern)
            result["knowledge_files"].extend(pattern_info.get("load", []))
            if pattern_info.get("context"):
                result["context_hints"].append(pattern_info["context"])

    # Dedupe
    result["knowledge_files"] = list(dict.fromkeys(result["knowledge_files"]))

    return result


def get_relevant_methods(task_keywords: list, methods_index: dict) -> dict:
    """Find relevant methods based on task keywords."""
    if not methods_index:
        return {"suggested_categories": [], "method_count": 0}

    tasks = methods_index.get("tasks", {})
    descriptions = methods_index.get("task_descriptions", {})

    suggested = []
    for keyword in task_keywords:
        keyword_lower = keyword.lower()
        for task_name, methods in tasks.items():
            if keyword_lower in task_name.lower():
                suggested.append({
                    "task": task_name,
                    "description": descriptions.get(task_name, ""),
                    "method_count": len(methods),
                    "sample_methods": methods[:5]
                })
                break

    return {
        "suggested_categories": suggested,
        "total_methods": methods_index.get("total_methods", 0)
    }


def load_context() -> dict:
    """Main function - load all context for current session."""
    result = {
        "project_name": None,
        "revit_version": None,
        "knowledge_files": [],
        "context_hints": [],
        "method_suggestions": {},
        "errors": []
    }

    # Load live state
    try:
        if LIVE_STATE.exists():
            live_state = json.loads(LIVE_STATE.read_text(encoding='utf-8'))
        else:
            result["errors"].append("Live state file not found")
            live_state = {}
    except Exception as e:
        result["errors"].append(f"Error loading live state: {e}")
        live_state = {}

    # Detect project
    project_name = detect_project_type(live_state)
    result["project_name"] = project_name

    # Detect Revit version
    for app in live_state.get("applications", []):
        if app.get("ProcessName") == "Revit":
            title = app.get("MainWindowTitle", "")
            if "2026" in title:
                result["revit_version"] = "2026"
            elif "2025" in title:
                result["revit_version"] = "2025"
            break

    # Load triggers
    triggers = load_yaml_simple(KNOWLEDGE_TRIGGERS)

    # Match patterns
    if project_name:
        pattern_result = match_patterns(project_name, triggers)
        result["knowledge_files"] = pattern_result["knowledge_files"]
        result["context_hints"] = pattern_result["context_hints"]

    # Load methods index
    try:
        if METHODS_INDEX.exists():
            methods_index = json.loads(METHODS_INDEX.read_text(encoding='utf-8'))
        else:
            methods_index = {}
    except Exception as e:
        result["errors"].append(f"Error loading methods index: {e}")
        methods_index = {}

    # Suggest methods based on context
    if project_name:
        # Extract keywords from project name
        keywords = re.findall(r'\w+', project_name.lower())
        result["method_suggestions"] = get_relevant_methods(keywords, methods_index)

    return result


def format_output(context: dict) -> str:
    """Format context for Claude Code output."""
    lines = []

    if context.get("project_name"):
        lines.append(f"**Detected Project:** {context['project_name']}")

    if context.get("revit_version"):
        lines.append(f"**Revit Version:** {context['revit_version']}")

    if context.get("knowledge_files"):
        lines.append(f"\n**Relevant Knowledge:** {', '.join(context['knowledge_files'][:5])}")

    if context.get("context_hints"):
        lines.append(f"\n**Context:** {context['context_hints'][0]}")

    if context.get("method_suggestions", {}).get("suggested_categories"):
        cats = context["method_suggestions"]["suggested_categories"]
        lines.append(f"\n**Suggested Method Categories:**")
        for cat in cats[:3]:
            lines.append(f"  - {cat['task']}: {cat['method_count']} methods")

    return '\n'.join(lines)


if __name__ == "__main__":
    context = load_context()
    print(format_output(context))
