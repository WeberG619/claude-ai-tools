#!/usr/bin/env python3
"""
Generate methods-index.json from RevitMCPBridge source code.
Parses MCPServer.cs to extract all registered methods and categorizes them by task.
"""
import re
import json
from pathlib import Path
from collections import defaultdict

# Task categorization rules
TASK_CATEGORIES = {
    "wall_creation": {
        "patterns": ["createWall", "Wall"],
        "exclude": ["getWall", "deleteWall"],
        "description": "Creating walls and wall-related geometry"
    },
    "wall_query": {
        "patterns": ["getWall", "Wall"],
        "include_only": ["getWall", "getWallTypes"],
        "description": "Querying wall information"
    },
    "element_deletion": {
        "patterns": ["delete", "Delete"],
        "description": "Deleting elements from the model"
    },
    "room_operations": {
        "patterns": ["Room", "room", "Area", "area"],
        "description": "Room and area creation, tagging, and queries"
    },
    "door_window": {
        "patterns": ["Door", "door", "Window", "window"],
        "description": "Door and window placement and queries"
    },
    "view_creation": {
        "patterns": ["createFloorPlan", "createCeilingPlan", "createSection",
                     "createElevation", "create3DView", "createDraftingView",
                     "createLegend", "createAreaPlan"],
        "description": "Creating new views"
    },
    "view_management": {
        "patterns": ["View", "view"],
        "exclude": ["createFloorPlan", "createCeilingPlan", "createSection",
                   "createElevation", "create3DView", "createDraftingView",
                   "Viewport", "viewport"],
        "description": "Managing and querying views"
    },
    "sheet_creation": {
        "patterns": ["createSheet", "Sheet"],
        "include_only": ["createSheet"],
        "description": "Creating sheets"
    },
    "viewport_placement": {
        "patterns": ["placeView", "Viewport", "viewport"],
        "description": "Placing views on sheets"
    },
    "sheet_management": {
        "patterns": ["Sheet", "sheet", "TitleBlock"],
        "exclude": ["createSheet", "placeView"],
        "description": "Sheet queries and title block operations"
    },
    "annotation": {
        "patterns": ["Tag", "tag", "Text", "text", "Dimension", "dimension",
                    "Keynote", "keynote", "Note"],
        "description": "Annotations, tags, text, and dimensions"
    },
    "scheduling": {
        "patterns": ["Schedule", "schedule"],
        "description": "Creating and managing schedules"
    },
    "family_operations": {
        "patterns": ["Family", "family", "loadFamily", "placeFamilyInstance"],
        "description": "Family loading, editing, and instance placement"
    },
    "parameter_operations": {
        "patterns": ["Parameter", "parameter"],
        "description": "Parameter creation and value manipulation"
    },
    "mep_operations": {
        "patterns": ["Duct", "duct", "Pipe", "pipe", "Electrical", "electrical",
                    "MEP", "mep", "Conduit", "conduit", "CableTray"],
        "description": "MEP system creation and management"
    },
    "structural": {
        "patterns": ["Structural", "structural", "Column", "column", "Beam", "beam",
                    "Foundation", "Rebar", "Load"],
        "description": "Structural elements and analysis"
    },
    "floor_ceiling_roof": {
        "patterns": ["Floor", "floor", "Ceiling", "ceiling", "Roof", "roof"],
        "exclude": ["FloorPlan", "CeilingPlan"],
        "description": "Floor, ceiling, and roof creation/editing"
    },
    "document_management": {
        "patterns": ["Document", "document", "save", "Save", "open", "Open",
                    "export", "Export", "sync", "Sync", "purge", "Purge"],
        "description": "Document operations, saving, exporting"
    },
    "revision_tracking": {
        "patterns": ["Revision", "revision", "Cloud", "cloud"],
        "description": "Revisions and revision clouds"
    },
    "selection": {
        "patterns": ["Selection", "selection", "select", "Select", "pick", "Pick"],
        "description": "Element selection and picking"
    },
    "verification": {
        "patterns": ["verify", "Verify", "validate", "Validate", "check", "Check"],
        "description": "Element and model verification"
    },
    "system_health": {
        "patterns": ["health", "Health", "stats", "Stats", "version", "Version",
                    "config", "Config", "getMethods"],
        "description": "System health, stats, and configuration"
    },
    "transaction_control": {
        "patterns": ["Transaction", "transaction", "undo", "Undo", "rollback", "Rollback"],
        "description": "Transaction management and undo operations"
    },
    "link_management": {
        "patterns": ["Link", "link", "CAD", "cad", "DWG", "dwg", "IFC", "ifc"],
        "description": "Linked models and CAD imports"
    },
    "workset_phase": {
        "patterns": ["Workset", "workset", "Phase", "phase"],
        "description": "Workset and phase management"
    },
    "grid_level": {
        "patterns": ["Grid", "grid", "Level", "level"],
        "description": "Grids and levels"
    },
    "material_operations": {
        "patterns": ["Material", "material"],
        "description": "Material assignment and queries"
    },
    "filter_operations": {
        "patterns": ["Filter", "filter"],
        "description": "View filters and element filtering"
    },
    "group_operations": {
        "patterns": ["Group", "group"],
        "description": "Element grouping operations"
    },
    "site_operations": {
        "patterns": ["Site", "site", "Topo", "topo", "Building", "building"],
        "description": "Site and topography operations"
    },
    "stair_railing": {
        "patterns": ["Stair", "stair", "Railing", "railing"],
        "description": "Stair and railing creation"
    },
    "render_capture": {
        "patterns": ["Render", "render", "Capture", "capture", "Image", "image",
                    "Screenshot", "screenshot", "Camera", "camera"],
        "description": "Rendering and image capture"
    },
    "intelligence": {
        "patterns": ["Intelligence", "intelligence", "Learning", "learning",
                    "Correction", "correction", "Workflow", "workflow",
                    "SelfHeal", "selfHeal", "Orchestrat"],
        "description": "AI intelligence and workflow automation"
    },
    "compliance": {
        "patterns": ["Compliance", "compliance", "Code", "code", "Standards", "standards"],
        "description": "Code compliance and standards checking"
    }
}

def parse_method_registry(filepath: Path) -> list:
    """Parse MCPServer.cs and extract all method registrations."""
    content = filepath.read_text(encoding='utf-8')

    # Pattern to match: _methodRegistry["methodName"] = ClassName.MethodName;
    pattern = r'_methodRegistry\["([^"]+)"\]\s*=\s*([^;]+);'

    methods = []
    for match in re.finditer(pattern, content):
        method_name = match.group(1)
        handler = match.group(2).strip()

        # Parse handler to get class name
        if '.' in handler:
            parts = handler.split('.')
            class_name = parts[-2] if len(parts) > 1 else parts[0]
        else:
            class_name = "Unknown"

        methods.append({
            "name": method_name,
            "handler": handler,
            "class": class_name.replace("RevitMCPBridge2026.", "")
        })

    return methods

def categorize_method(method_name: str) -> list:
    """Determine which task categories a method belongs to."""
    categories = []

    for category, rules in TASK_CATEGORIES.items():
        # Check include_only first (most restrictive)
        if "include_only" in rules:
            if method_name in rules["include_only"]:
                categories.append(category)
            continue

        # Check patterns
        matches_pattern = any(p in method_name for p in rules["patterns"])

        # Check exclusions
        excluded = False
        if "exclude" in rules:
            excluded = any(e in method_name for e in rules["exclude"])

        if matches_pattern and not excluded:
            categories.append(category)

    # If no category found, mark as "general"
    if not categories:
        categories = ["general"]

    return categories

def parse_verifiable_methods(filepath: Path) -> set:
    """Extract the list of verifiable methods from MCPServer.cs."""
    content = filepath.read_text(encoding='utf-8')

    # Find the _verifiableMethods HashSet
    pattern = r'_verifiableMethods\s*=\s*new\s+HashSet<string>[^{]*\{([^}]+)\}'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return set()

    # Extract method names
    methods_block = match.group(1)
    method_pattern = r'"([^"]+)"'
    return set(re.findall(method_pattern, methods_block))

def parse_correction_check_methods(filepath: Path) -> set:
    """Extract methods that benefit from pre-execution correction checking."""
    content = filepath.read_text(encoding='utf-8')

    pattern = r'_correctionCheckMethods\s*=\s*new\s+HashSet<string>[^{]*\{([^}]+)\}'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return set()

    methods_block = match.group(1)
    method_pattern = r'"([^"]+)"'
    return set(re.findall(method_pattern, methods_block))

def generate_index(source_path: Path, output_path: Path):
    """Generate the complete methods index."""

    # Parse the source
    methods = parse_method_registry(source_path)
    verifiable = parse_verifiable_methods(source_path)
    correction_check = parse_correction_check_methods(source_path)

    # Build task-to-methods mapping
    tasks = defaultdict(list)

    # Build methods dictionary
    methods_dict = {}

    for method in methods:
        name = method["name"]
        categories = categorize_method(name)

        # Add to each category
        for cat in categories:
            if name not in tasks[cat]:
                tasks[cat].append(name)

        # Build method entry
        methods_dict[name] = {
            "categories": categories,
            "handler_class": method["class"],
            "verifiable": name in verifiable,
            "correction_check": name in correction_check
        }

    # Build final index
    index = {
        "version": "1.0",
        "generated_from": str(source_path),
        "total_methods": len(methods),
        "task_descriptions": {k: v["description"] for k, v in TASK_CATEGORIES.items()},
        "tasks": dict(tasks),
        "methods": methods_dict
    }

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=2), encoding='utf-8')

    print(f"Generated index with {len(methods)} methods across {len(tasks)} task categories")
    print(f"Output: {output_path}")

    # Print summary
    print("\nTask Categories:")
    for task, method_list in sorted(tasks.items(), key=lambda x: -len(x[1])):
        print(f"  {task}: {len(method_list)} methods")

if __name__ == "__main__":
    source = Path("/mnt/d/RevitMCPBridge2026/src/MCPServer.cs")
    output = Path("/mnt/d/_CLAUDE-TOOLS/orchestration/methods-index.json")

    if not source.exists():
        print(f"Error: Source file not found: {source}")
        exit(1)

    generate_index(source, output)
