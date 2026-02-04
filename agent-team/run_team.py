#!/usr/bin/env python3
"""
Run Team - CLI wrapper for AutonomousTeam with execution support
================================================================
Provides command-line interface for running agent team sessions
with optional real execution mode.
"""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Run the Agent Team")
    parser.add_argument("--mode", "-m", default="work",
                       choices=["work", "discuss", "parallel"],
                       help="Session mode: work, discuss, or parallel")
    parser.add_argument("--task", "-t", required=True,
                       help="Task or topic for the team to work on")
    parser.add_argument("--workspace", "-w", default=None,
                       help="Workspace directory for file operations")
    parser.add_argument("--execute", action="store_true",
                       help="Enable real execution (files, commands, git)")
    parser.add_argument("--simulate", action="store_true",
                       help="Simulation mode - no real execution (default)")

    args = parser.parse_args()

    # Determine execution mode
    enable_execution = args.execute and not args.simulate

    # Set workspace
    workspace = Path(args.workspace) if args.workspace else Path.cwd() / "projects"

    print(f"\n{'='*60}")
    print(f"  AGENT TEAM SESSION")
    print(f"{'='*60}")
    print(f"  Mode: {args.mode}")
    print(f"  Task: {args.task}")
    print(f"  Workspace: {workspace}")
    print(f"  Execution: {'ENABLED' if enable_execution else 'SIMULATION'}")
    print(f"{'='*60}\n")

    # Import and create team
    from autonomous_agents import AutonomousTeam

    team = AutonomousTeam(
        workspace=workspace,
        enable_execution=enable_execution
    )

    # Run based on mode
    if args.mode == "work":
        team.work_on_task(args.task)
    elif args.mode == "discuss":
        team.discuss(args.task)
    elif args.mode == "parallel":
        # Split task into builder-specific parts
        tasks = {
            "builder": f"Backend implementation for: {args.task}",
            "builder-frontend": f"Frontend UI for: {args.task}",
            "builder-infra": f"Deployment setup for: {args.task}"
        }
        results = team.parallel_build(tasks)

        # Have narrator summarize
        team.narrator.respond(
            f"Summarize the parallel build results for: {args.task}",
            team.team_history
        )

    print(f"\n{'='*60}")
    print(f"  SESSION COMPLETE")
    print(f"{'='*60}\n")

    # Print audit log if execution was enabled
    if enable_execution and team.execution_bridge:
        audit_log = team.execution_bridge.get_audit_log(limit=10)
        if audit_log:
            print("\nExecution Audit Log:")
            print("-" * 40)
            for entry in audit_log:
                status = "OK" if entry["success"] else "FAIL"
                print(f"  [{status}] {entry['action_type']}: {entry['content'][:50]}...")


if __name__ == "__main__":
    main()
