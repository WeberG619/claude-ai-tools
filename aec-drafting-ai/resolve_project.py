#!/usr/bin/env python3
"""
AEC Drafting AI - Project Name Resolver

Resolves friendly project names to full file paths.
Usage: python resolve_project.py "avon park"
       python resolve_project.py --list
       python resolve_project.py --add "New Project" "D:\\path\\to\\project.rvt"
"""

import json
import sys
from pathlib import Path
from difflib import SequenceMatcher

REGISTRY_PATH = Path(__file__).parent / "project_registry.json"

def load_registry():
    """Load the project registry."""
    if not REGISTRY_PATH.exists():
        return {"projects": {}}
    with open(REGISTRY_PATH, 'r') as f:
        return json.load(f)

def save_registry(registry):
    """Save the project registry."""
    registry["last_updated"] = __import__('datetime').datetime.now().strftime("%Y-%m-%d")
    with open(REGISTRY_PATH, 'w') as f:
        json.dump(registry, f, indent=2)

def similarity(a, b):
    """Calculate string similarity."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_project(query):
    """Find a project by name or alias."""
    registry = load_registry()
    query_lower = query.lower()

    best_match = None
    best_score = 0

    for name, info in registry.get("projects", {}).items():
        # Check exact name match
        if query_lower == name.lower():
            return {"name": name, "path": info["path"], "info": info, "score": 1.0}

        # Check aliases
        for alias in info.get("aliases", []):
            if query_lower == alias.lower():
                return {"name": name, "path": info["path"], "info": info, "score": 1.0}

            # Check partial match in alias
            if query_lower in alias.lower() or alias.lower() in query_lower:
                score = similarity(query_lower, alias.lower())
                if score > best_score:
                    best_score = score
                    best_match = {"name": name, "path": info["path"], "info": info, "score": score}

        # Check partial match in name
        if query_lower in name.lower() or name.lower() in query_lower:
            score = similarity(query_lower, name.lower())
            if score > best_score:
                best_score = score
                best_match = {"name": name, "path": info["path"], "info": info, "score": score}

    # Return best match if score is good enough
    if best_score >= 0.4:
        return best_match

    return None

def list_projects():
    """List all registered projects."""
    registry = load_registry()
    projects = []
    for name, info in registry.get("projects", {}).items():
        projects.append({
            "name": name,
            "type": info.get("type", "unknown"),
            "path": info["path"],
            "aliases": info.get("aliases", [])
        })
    return projects

def add_project(name, path, project_type="unknown", aliases=None, description=""):
    """Add a new project to the registry."""
    registry = load_registry()
    registry["projects"][name] = {
        "path": path,
        "aliases": aliases or [],
        "type": project_type,
        "description": description
    }
    save_registry(registry)
    return {"success": True, "name": name, "path": path}

def main():
    if len(sys.argv) < 2:
        print("Usage: python resolve_project.py <query>")
        print("       python resolve_project.py --list")
        print("       python resolve_project.py --add <name> <path>")
        sys.exit(1)

    if sys.argv[1] == "--list":
        projects = list_projects()
        print(json.dumps(projects, indent=2))
    elif sys.argv[1] == "--add" and len(sys.argv) >= 4:
        result = add_project(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))
    else:
        query = " ".join(sys.argv[1:])
        result = find_project(query)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps({"error": f"No project found matching '{query}'", "suggestions": [p["name"] for p in list_projects()[:5]]}))

if __name__ == "__main__":
    main()
