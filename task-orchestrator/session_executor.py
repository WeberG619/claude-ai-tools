#!/usr/bin/env python3
"""
Session Executor - For running tasks within current Claude Code session

Instead of spawning new Claude processes (slow, no context), this generates
instructions for the current session to work through the queue using the
Task tool to spawn sub-agents.

Usage:
    python3 session_executor.py --project "Project Name" --mode instructions
    python3 session_executor.py --project "Project Name" --mode next
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from task_queue import (
    get_queue_status, list_tasks, get_next_task, start_task,
    complete_task, verify_task
)

def generate_execution_instructions(project: str) -> str:
    """Generate instructions for Claude to execute the queue."""
    status = get_queue_status(project)
    tasks = [t for t in list_tasks(project) if t["status"] == "pending"]

    if not tasks:
        return f"No pending tasks for project: {project}"

    instructions = f"""## Task Queue Execution for: {project}

**Status:** {status['pending']} pending, {status['completed']} completed

### Tasks to Execute:

"""
    for i, task in enumerate(tasks, 1):
        deps = task.get('depends_on', [])
        dep_str = f" (depends on: {', '.join(deps)})" if deps else ""
        instructions += f"""
**Task {i}: {task['title']}** [{task['id']}]{dep_str}
- Agent: `{task['agent']}`
- Priority: {task['priority']}
- Description: {task['description']}
"""

    instructions += """
### Execution Protocol:

For each task:
1. Mark it started: `python3 queue_cli.py start "<project>" --task-id "<id>"`
2. Use Task tool to spawn the appropriate sub-agent
3. When complete, mark it done: `python3 queue_cli.py complete "<project>" --task-id "<id>" --result "summary"`
4. Run verification if needed
5. Move to next task

You have all the tools needed. Begin execution.
"""
    return instructions


def get_next_task_instructions(project: str) -> dict:
    """Get the next task with execution instructions."""
    task = get_next_task(project)
    if not task:
        return {"status": "empty", "message": "No pending tasks"}

    return {
        "status": "ready",
        "task": task,
        "instructions": f"""
Execute this task now:

**{task['title']}** [{task['id']}]
Agent: {task['agent']}
Description: {task['description']}

Steps:
1. Run: python3 queue_cli.py start "{project}" --task-id "{task['id']}"
2. Use Task tool with subagent_type="{task['agent']}" to complete it
3. Run: python3 queue_cli.py complete "{project}" --task-id "{task['id']}" --result "<your summary>"
"""
    }


def mark_started(project: str, task_id: str) -> dict:
    """Mark a task as started."""
    task = start_task(project, task_id)
    return {"status": "started", "task": task}


def mark_completed(project: str, task_id: str, result: str = None, error: str = None) -> dict:
    """Mark a task as completed."""
    task = complete_task(project, task_id, result, error)
    return {"status": "completed" if not error else "failed", "task": task}


def mark_verified(project: str, task_id: str, passed: bool, notes: str = "") -> dict:
    """Mark a task as verified."""
    task = verify_task(project, task_id, notes, passed)
    return {"status": "verified" if passed else "failed", "task": task}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Session Task Executor")
    parser.add_argument("--project", "-p", required=True, help="Project name")
    parser.add_argument("--mode", "-m", default="instructions",
                       choices=["instructions", "next", "start", "complete", "verify"],
                       help="Execution mode")
    parser.add_argument("--task-id", "-i", help="Task ID (for start/complete/verify)")
    parser.add_argument("--result", "-r", help="Result message")
    parser.add_argument("--error", "-e", help="Error message")
    parser.add_argument("--passed", action="store_true", help="Verification passed")

    args = parser.parse_args()

    if args.mode == "instructions":
        print(generate_execution_instructions(args.project))

    elif args.mode == "next":
        result = get_next_task_instructions(args.project)
        print(json.dumps(result, indent=2))

    elif args.mode == "start":
        if not args.task_id:
            print("Error: --task-id required")
            sys.exit(1)
        result = mark_started(args.project, args.task_id)
        print(json.dumps(result, indent=2))

    elif args.mode == "complete":
        if not args.task_id:
            print("Error: --task-id required")
            sys.exit(1)
        result = mark_completed(args.project, args.task_id, args.result, args.error)
        print(json.dumps(result, indent=2))

    elif args.mode == "verify":
        if not args.task_id:
            print("Error: --task-id required")
            sys.exit(1)
        result = mark_verified(args.project, args.task_id, args.passed, args.result or "")
        print(json.dumps(result, indent=2))
