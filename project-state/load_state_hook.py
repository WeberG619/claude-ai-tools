#!/usr/bin/env python3
"""
Startup hook to load project state.
Detects current project and loads/displays its state.
"""

import sys
sys.path.insert(0, '/mnt/d/_CLAUDE-TOOLS/project-state')

from state_manager import (
    detect_project_from_system,
    load_state,
    get_or_create_state,
    format_state_summary
)


def main():
    # Detect project from system state
    detected = detect_project_from_system()

    if not detected:
        print("No active project detected.")
        return

    project_name = detected["name"]
    source = detected["source"]

    # Try to load existing state
    state = load_state(project_name)

    if state:
        # Existing state found
        wf = state["workflow"]

        print(f"# Project State Loaded")
        print(f"**Project**: {project_name} (from {source})")
        print("")

        if wf["current_pipeline"] and wf["status"] in ["in_progress", "paused"]:
            print(f"## Active Workflow")
            print(f"- **Pipeline**: {wf['current_pipeline']}")
            print(f"- **Phase**: {wf['current_phase']}")
            print(f"- **Status**: {wf['status'].upper()}")
            print("")

            # Show current checkpoint if paused
            cp = state["checkpoints"]
            if cp["current"]:
                print(f"## Waiting at Checkpoint")
                print(f"**{cp['current']['name']}**")
                print(f"_Waiting since {cp['current']['waiting_since'][:16]}_")
                print("")

            # Show passed checkpoints
            if cp["passed"]:
                print(f"## Checkpoints Passed: {len(cp['passed'])}")
                for p in cp["passed"][-3:]:
                    print(f"- [x] {p['name']}")
                print("")

            # Show next actions
            if state["next_actions"]:
                print("## Next Actions")
                for i, action in enumerate(state["next_actions"][:3], 1):
                    print(f"{i}. {action}")
                print("")

            print("_Use `/resume` to continue or start fresh._")

        else:
            # No active pipeline
            print(f"**Status**: No active workflow")
            if state["last_session"]["summary"]:
                print(f"**Last session**: {state['last_session']['summary'][:100]}")
            print("")
            print("_Ready to start a new pipeline._")

    else:
        # No state exists
        print(f"# New Project Detected")
        print(f"**Project**: {project_name} (from {source})")
        print("")
        print("No previous state found. This is a fresh start.")
        print("")
        print("_To track workflow state, start a pipeline:_")
        print("- `cd-set-assembly` - Construction document production")
        print("- `markup-to-model` - PDF/CAD to Revit conversion")


if __name__ == "__main__":
    main()
